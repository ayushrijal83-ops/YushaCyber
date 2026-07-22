"""Cyber Labs routes.

Thin controllers ONLY. Every route delegates to lab_services and returns
plain data. No route knows which simulator drives a lab — that is the whole
point of the engine. Adding Nmap/Wireshark/Burp requires ZERO route changes.
"""

from __future__ import annotations

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.labs import labs_bp, lab_services


@labs_bp.route("/")
@login_required
def index():
    """Labs catalogue with Linux track progression."""
    # Every category that has interactive labs renders as a learning track.
    # Data-driven: seeding a new track (Networking today, Nmap tomorrow)
    # requires no route change beyond this generic loop.
    tracks = []
    for category in lab_services.get_categories():
        ctx = lab_services.get_track_context(current_user, category.slug)
        if ctx.get("total"):
            ctx["icon"] = category.icon
            tracks.append(ctx)
    return render_template(
        "labs/index.html",
        user=current_user,
        categories=lab_services.get_categories(),
        labs=lab_services.get_labs(),
        tracks=tracks,
        track_slugs=[t["category"]["slug"] for t in tracks],
    )


@labs_bp.route("/<slug>")
@login_required
def detail(slug: str):
    """A lab: interactive workspace when it has a simulator, else read-only."""
    lab = lab_services.get_lab(slug)
    if lab is None:
        abort(404)

    # Sequential progression: a locked lab redirects back to the catalogue.
    if lab.is_interactive and not lab_services.is_lab_unlocked(current_user, lab):
        flash("Complete the previous lab to unlock this one.", "error")
        return redirect(url_for("labs.index"))

    context = {}
    if lab.is_interactive:
        context = lab_services.get_workspace_context(current_user, lab)

    return render_template(
        "labs/detail.html", user=current_user, lab=lab, **context
    )


@labs_bp.route("/<slug>/action", methods=["POST"])
@login_required
def action(slug: str):
    """Run one action against the lab's simulator (JSON in, JSON out).

    Capability-agnostic: `type` may be "command" today, "select"/"flag"/
    "submit" for future inspector, packet-viewer, browser or editor labs —
    the route does not change.
    """
    lab = lab_services.get_lab(slug)
    if lab is None:
        abort(404)

    data = request.get_json(silent=True) or {}
    action_type = str(data.get("type") or "command")
    payload = data.get("payload") or {}

    result = lab_services.execute_action(current_user, lab, action_type, payload)
    if not result.get("ok"):
        return jsonify(result), 400
    return jsonify(result)


@labs_bp.route("/<slug>/reset", methods=["POST"])
@login_required
def reset(slug: str):
    """Reset the simulated session state (objective/XP history is kept)."""
    lab = lab_services.get_lab(slug)
    if lab is None:
        abort(404)
    result = lab_services.reset_lab_session(current_user, lab)
    return jsonify(result), (200 if result.get("ok") else 400)


# ---------------------------------------------------------------------------
# Topology engine HTTP surface (YC-026.1)
# ---------------------------------------------------------------------------
# One catalogue endpoint + one payload endpoint per topology + one
# per-device detail endpoint. All read-only, all login-required so we
# don't hand random network diagrams to anonymous crawlers, all
# capability-agnostic (any future frontend consumes the same JSON).


@labs_bp.route("/topology/")
@login_required
def topology_index():
    """List every available topology."""
    from app.labs.topology import engine as topology_engine
    return jsonify({
        "topologies": topology_engine.list_topologies(),
        "device_types": topology_engine.DEVICE_TYPES,
    })


@labs_bp.route("/topology/<name>")
@login_required
def topology_show(name: str):
    """Full renderer payload for one topology."""
    from app.labs.topology import engine as topology_engine
    try:
        engine = topology_engine.load_topology(name)
    except topology_engine.TopologyNotFound:
        abort(404)
    except topology_engine.TopologySchemaError as exc:
        return jsonify({"error": "schema", "detail": str(exc)}), 500
    return jsonify(engine.render_payload())


@labs_bp.route("/topology/<name>/device/<hostname>")
@login_required
def topology_device(name: str, hostname: str):
    """Detail panel payload for a clicked device."""
    from app.labs.topology import engine as topology_engine
    try:
        engine = topology_engine.load_topology(name)
    except topology_engine.TopologyNotFound:
        abort(404)
    payload = engine.describe_device(hostname)
    if payload is None:
        abort(404)
    return jsonify(payload)


@labs_bp.route("/topology/<name>/view")
@login_required
def topology_view(name: str):
    """Interactive HTML view of a topology (visual sanity + demo).

    Used by lab authors while shaping a JSON; also the default renderer
    template that future simulators embed via ``{% include %}``.
    """
    from app.labs.topology import engine as topology_engine
    try:
        topology_engine.load_topology(name)  # validate before rendering
    except topology_engine.TopologyNotFound:
        abort(404)
    except topology_engine.TopologySchemaError as exc:
        return (f"Topology schema error: {exc}", 500)
    return render_template("labs/topology_view.html", topology_name=name)


# ---------------------------------------------------------------------------
# Connectivity engine HTTP surface (YC-026.3)
# ---------------------------------------------------------------------------
# A read-only probe endpoint so any future frontend (a live network-map
# with green/red status dots, an Nmap console, a Wireshark feed) can ask
# the shared engine "what happens if X talks to Y?" without re-deriving
# reachability client-side. Everything routes through the ONE engine —
# no duplicated networking logic.

@labs_bp.route("/topology/<name>/status")
@login_required
def topology_status(name: str):
    """Per-host online/offline + service snapshot for the network map.

    Accepts an optional ?offline=host1,host2 query so a caller can preview
    connectivity with certain hosts downed without persisting anything.
    """
    from app.labs import net_engine
    from app.labs.topology import engine as topology_engine
    try:
        engine_topo = topology_engine.load_topology(name)
    except topology_engine.TopologyNotFound:
        abort(404)
    offline = tuple(
        h for h in request.args.get("offline", "").split(",") if h
    )
    engine = net_engine.make_engine(engine_topo, offline=offline)
    return jsonify(engine.status_snapshot())


@labs_bp.route("/topology/<name>/probe")
@login_required
def topology_probe(name: str):
    """Simulated connectivity probe between two devices.

    Query params: ?src=<host>&dst=<host>[&proto=icmp|tcp|udp][&port=N]
                  [&offline=hostA,hostB]
    Returns ping replies (icmp) or a single packet result (tcp/udp),
    plus traceroute hops. Pure simulation — no real network access.
    """
    from app.labs import net_engine
    from app.labs.topology import engine as topology_engine
    try:
        engine_topo = topology_engine.load_topology(name)
    except topology_engine.TopologyNotFound:
        abort(404)

    src = request.args.get("src", "")
    dst = request.args.get("dst", "")
    proto = request.args.get("proto", "icmp").lower()
    port = request.args.get("port", type=int)
    offline = tuple(h for h in request.args.get("offline", "").split(",") if h)

    engine = net_engine.make_engine(engine_topo, offline=offline)
    if engine.host(src) is None or engine.host(dst) is None:
        return jsonify({"error": "unknown-host",
                        "detail": "src and dst must be known devices"}), 400

    result = {
        "src": src, "dst": dst, "protocol": proto,
        "reachable": engine.reachable(src, dst),
    }
    if proto == "icmp":
        replies = engine.ping(src, dst, count=4)
        result["ping"] = [
            {"seq": r.sequence, "status": r.status.value,
             "ttl": r.ttl, "latency_ms": r.latency_ms}
            for r in replies
        ]
        trace = engine.traceroute(src, dst)
        result["traceroute"] = [
            {"hop": h.hop, "hostname": h.hostname, "ip": h.ip,
             "latency_ms": h.latency_ms}
            for h in trace.hops
        ]
    else:
        pkt = engine.send_packet(src, dst, protocol=proto, port=port)
        result["packet"] = pkt.to_dict()
        if port is not None:
            result["port_state"] = engine.scan_port(src, dst, port,
                                                     protocol=proto).value
    return jsonify(result)


# ---------------------------------------------------------------------------
# Active Directory explorer surface (YC-031.0)
# ---------------------------------------------------------------------------
@labs_bp.route("/<slug>/ad/state")
@login_required
def ad_state(slug: str):
    """The AD object-explorer tree for this user's current lab session.

    Read-only, additive, login-required. The frontend refreshes the
    tree after every action so moves/disables/removals appear live —
    the server's session state stays the single source of truth.
    """
    lab = lab_services.get_lab(slug)
    if lab is None or lab.simulator_key != "ad":
        abort(404)

    from app.labs import session_manager
    from app.labs.ad import engine as ad_engine

    simulator = session_manager.get_simulator(lab)
    session = session_manager.start_session(current_user, lab)
    state = session_manager.load_state(session, simulator, lab)
    return jsonify({
        "tree": ad_engine.explorer_tree(state.get("directory", {})),
        "selected": state.get("selected", ""),
    })


@labs_bp.route("/<slug>/cloud/state")
@login_required
def cloud_state(slug: str):
    """The cloud console resource tree for this user's current session.

    Read-only, additive, login-required. The frontend refreshes the
    tree after every action so remediations (private buckets, revoked
    rules, disabled users) appear live — the server's session state
    stays the single source of truth.
    """
    lab = lab_services.get_lab(slug)
    if lab is None or lab.simulator_key != "cloud":
        abort(404)

    from app.labs import session_manager
    from app.labs.cloud import engine as cloud_engine

    simulator = session_manager.get_simulator(lab)
    session = session_manager.start_session(current_user, lab)
    state = session_manager.load_state(session, simulator, lab)
    return jsonify({
        "tree": cloud_engine.explorer_tree(state.get("deployment", {})),
        "selected": state.get("selected", ""),
    })


# ---------------------------------------------------------------------------
# Digital Forensics workstation surface (YC-029.5.2)
# ---------------------------------------------------------------------------
@labs_bp.route("/<slug>/forensics/state")
@login_required
def forensics_state(slug: str):
    """Session state for the forensics workstation UI.

    Read-only; returns the case view (evidence grouped by kind + the
    timeline), the currently selected slug, the sets of inspected /
    flagged evidence and the last submitted findings + check results.
    Everything the client needs to render metadata, hash and findings
    panels without a page reload.
    """
    lab = lab_services.get_lab(slug)
    if lab is None or lab.simulator_key != "forensics":
        abort(404)

    from app.labs import session_manager
    from app.labs.forensics import engine as forensics_engine

    simulator = session_manager.get_simulator(lab)
    session = session_manager.start_session(current_user, lab)
    state = session_manager.load_state(session, simulator, lab)
    case = state.get("case") or {}
    view = forensics_engine.build_view(case)
    view["metadata"] = {
        item["slug"]:
            forensics_engine.evidence_metadata(item).__dict__
        for item in case.get("evidence") or []
    }
    view["mode"] = case.get("mode") or "fundamentals"
    # Applied-lab extras — cheap to compute, harmless in fundamentals mode.
    view["sources"] = forensics_engine.all_sources(case)
    view["unified_timeline"] = forensics_engine.unified_timeline(case)
    view["artifacts_by_source"] = {
        source["source_type"]:
            forensics_engine.artifacts_by_source(case,
                                                  source["source_type"])
        for source in view["sources"]
    }
    view["schema"] = forensics_engine.ARTIFACT_SCHEMA
    view["suspects"] = case.get("suspects") or []
    view["network_summary"] = forensics_engine.network_summary(case)
    correlation = forensics_engine.correlation_score(
        case, state.get("links") or [])
    return jsonify({
        "view": view,
        "selected": state.get("selected") or "",
        "inspected": list(state.get("inspected") or []),
        "flagged": list(state.get("flagged") or []),
        "findings": state.get("findings") or {},
        "checks": state.get("checks") or {},
        "active_source": state.get("active_source") or "",
        "opened_sources": list(state.get("opened_sources") or []),
        "seen_artifacts": list(state.get("seen_artifacts") or []),
        "notes": list(state.get("notes") or []),
        "links": list(state.get("links") or []),
        "named_suspect": state.get("named_suspect") or "",
        "correlation": correlation,
    })
