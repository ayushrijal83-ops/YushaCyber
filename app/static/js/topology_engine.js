/* ===========================================================================
   Virtual Network Topology Renderer (YC-026.1)

   Consumes /labs/topology/<name> (payload) and /labs/topology/<name>/
   device/<hostname> (detail). No topology data is hardcoded here — the
   engine on the server is the single source of truth.

   Feature set:
     · SVG rendering with icon-per-device-type + label + IP
     · Auto layered layout (BFS from Internet or Router if present)
     · Animated link "traffic" pulse (SMIL, respects reduced-motion)
     · Selected node glow + highlighted incident links (CSS-only, no
       re-render — so the map never "moves" when you click)
     · Zoom controls (buttons + Ctrl-wheel) with a proper transform-origin
     · Keyboard support (Enter/Space) + ARIA
     · Detail panel populated from the /device/ endpoint (defensive
       against missing fields; catches every fetch error visibly)
   =========================================================================== */

(function () {
    "use strict";

    var root = document.querySelector(".topo");
    if (!root) return;

    var payloadUrl    = root.dataset.topologyUrl;
    var deviceUrlTpl  = root.dataset.topologyDeviceUrl;
    var svg           = root.querySelector("#topo-svg");
    var viewport      = root.querySelector("#topo-viewport");
    var linksG        = root.querySelector("#topo-links");
    var nodesG        = root.querySelector("#topo-nodes");
    var titleEl       = root.querySelector("#topo-title");
    var descEl        = root.querySelector("#topo-desc");
    var panelEmpty    = root.querySelector("#topo-panel-empty");
    var panelBody     = root.querySelector("#topo-panel-body");
    var panelLabel    = root.querySelector("#topo-panel-label");
    var panelStatus   = root.querySelector("#topo-panel-status");
    var panelFacts    = root.querySelector("#topo-panel-facts");
    var panelPorts    = root.querySelector("#topo-panel-ports");
    var panelConns    = root.querySelector("#topo-panel-conns");
    var zoomVal       = root.querySelector("#topo-zoom");

    var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var deviceGlyph = {
        router:          "\uD83D\uDCE1",
        switch:          "\u26A1",
        pc:              "\uD83D\uDCBB",
        "linux-server":  "\uD83D\uDC27",
        "windows-server":"\uD83D\uDDA5",
        firewall:        "\uD83D\uDD25",
        ids:             "\uD83D\uDC41",
        siem:            "\uD83D\uDCCA",
        internet:        "\uD83C\uDF10"
    };

    var payload = null;
    var positions = {};
    var nodeElements = {};    /* hostname -> <g> element */
    var linkElements = [];    /* [{a, b, line, pulse}] */
    var selected = null;
    var zoom = 1;

    /* ----------------------------------------------------------------
       1. Load the topology payload (single fetch on boot).
    ----------------------------------------------------------------- */
    fetch(payloadUrl, {credentials: "same-origin"})
        .then(function (r) {
            if (!r.ok) throw new Error("Failed to load topology (" + r.status + ")");
            return r.json();
        })
        .then(function (data) {
            payload = data;
            if (titleEl && data.title) titleEl.textContent = data.title;
            if (descEl)  descEl.textContent  = data.description || "";
            layout();
            drawInitial();
            applyZoom();
            loadStatus();
        })
        .catch(function (err) {
            if (descEl) descEl.textContent = "Could not load topology: " + err.message;
        });

    /* Fetch per-host online/offline status and paint the map (YC-026.3).
       The status endpoint runs through the shared connectivity engine,
       so the green/red dots reflect real reachability, not a guess. */
    function loadStatus() {
        var statusUrl = root.dataset.topologyStatusUrl;
        if (!statusUrl) return;
        fetch(statusUrl, {credentials: "same-origin"})
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (status) {
                if (!status) return;
                Object.keys(nodeElements).forEach(function (h) {
                    var online = !status[h] || status[h].online !== false;
                    nodeElements[h].classList.toggle("is-offline", !online);
                });
            })
            .catch(function () { /* status is best-effort decoration */ });
    }

    /* ----------------------------------------------------------------
       2. Auto-layout — a lightweight layered/BFS placement.
    ----------------------------------------------------------------- */
    function layout() {
        var W = 900, H = 460;
        var nodes = payload.nodes;

        var adj = {};
        nodes.forEach(function (n) { adj[n.hostname] = []; });
        payload.links.forEach(function (l) {
            adj[l.a].push(l.b); adj[l.b].push(l.a);
        });

        var anchor = nodes.filter(function (n) { return n.device_type === "internet"; })[0];
        if (!anchor) anchor = nodes.filter(function (n) { return n.device_type === "router"; })[0];
        if (!anchor) anchor = nodes[0];

        var row = {};
        row[anchor.hostname] = 0;
        var q = [anchor.hostname];
        while (q.length) {
            var cur = q.shift();
            adj[cur].forEach(function (n) {
                if (row[n] === undefined) {
                    row[n] = row[cur] + 1;
                    q.push(n);
                }
            });
        }
        var maxRow = 0;
        nodes.forEach(function (n) {
            if (row[n.hostname] === undefined) row[n.hostname] = -1;
            if (row[n.hostname] > maxRow) maxRow = row[n.hostname];
        });
        nodes.forEach(function (n) { if (row[n.hostname] === -1) row[n.hostname] = maxRow + 1; });

        var buckets = {};
        nodes.forEach(function (n) {
            var r = row[n.hostname];
            (buckets[r] = buckets[r] || []).push(n);
        });

        Object.keys(buckets).forEach(function (r) {
            var arr = buckets[r];
            arr.sort(function (a, b) { return a.hostname.localeCompare(b.hostname); });
            var y = 60 + Number(r) * ((H - 120) / Math.max(1, maxRow + 1));
            arr.forEach(function (n, i) {
                var pad = 90;
                var span = W - 2 * pad;
                var x = arr.length === 1 ? W / 2
                                          : pad + (span * (i / (arr.length - 1)));
                positions[n.hostname] = {
                    x: (n.x !== null && n.x !== undefined) ? n.x : x,
                    y: (n.y !== null && n.y !== undefined) ? n.y : y
                };
            });
        });
    }

    /* ----------------------------------------------------------------
       3. Draw ONCE. Selection updates classes only, never re-creates
          DOM — that's what was causing the map to jump on every click.
    ----------------------------------------------------------------- */
    var NS = "http://www.w3.org/2000/svg";

    function drawInitial() {
        linksG.innerHTML = "";
        nodesG.innerHTML = "";
        linkElements = [];
        nodeElements = {};

        payload.links.forEach(function (l) {
            var a = positions[l.a], b = positions[l.b];
            if (!a || !b) return;

            var line = document.createElementNS(NS, "line");
            line.setAttribute("x1", a.x); line.setAttribute("y1", a.y);
            line.setAttribute("x2", b.x); line.setAttribute("y2", b.y);
            line.setAttribute("class", "topo__link"
                + (l.kind === "wan" ? " topo__link--wan" : ""));
            linksG.appendChild(line);

            var pulse = null;
            if (!reducedMotion) {
                pulse = document.createElementNS(NS, "circle");
                pulse.setAttribute("r", "3");
                pulse.setAttribute("class", "topo__pulse");
                var anim1 = document.createElementNS(NS, "animate");
                anim1.setAttribute("attributeName", "cx");
                anim1.setAttribute("from", a.x); anim1.setAttribute("to", b.x);
                anim1.setAttribute("dur", "3.4s"); anim1.setAttribute("repeatCount", "indefinite");
                var anim2 = document.createElementNS(NS, "animate");
                anim2.setAttribute("attributeName", "cy");
                anim2.setAttribute("from", a.y); anim2.setAttribute("to", b.y);
                anim2.setAttribute("dur", "3.4s"); anim2.setAttribute("repeatCount", "indefinite");
                pulse.appendChild(anim1); pulse.appendChild(anim2);
                linksG.appendChild(pulse);
            }

            linkElements.push({a: l.a, b: l.b, line: line, pulse: pulse});
        });

        payload.nodes.forEach(function (node) {
            var p = positions[node.hostname]; if (!p) return;

            var g = document.createElementNS(NS, "g");
            g.setAttribute("transform", "translate(" + p.x + "," + p.y + ")");
            g.setAttribute("class",
                "topo__node topo__node--" + node.device_type
                + (node.future_ready ? " is-future" : ""));
            g.setAttribute("data-hostname", node.hostname);
            g.setAttribute("tabindex", "0");
            g.setAttribute("role", "button");
            g.setAttribute("aria-label", node.label + " (" + node.device_type + ")");

            var ring = document.createElementNS(NS, "circle");
            ring.setAttribute("class", "topo__ring");
            ring.setAttribute("r", "30");
            g.appendChild(ring);

            var glyph = document.createElementNS(NS, "text");
            glyph.setAttribute("class", "topo__glyph");
            glyph.setAttribute("text-anchor", "middle");
            glyph.setAttribute("dominant-baseline", "central");
            glyph.textContent = deviceGlyph[node.device_type] || "\u2022";
            g.appendChild(glyph);

            var label = document.createElementNS(NS, "text");
            label.setAttribute("class", "topo__label");
            label.setAttribute("text-anchor", "middle");
            label.setAttribute("y", "52");
            label.textContent = node.label;
            g.appendChild(label);

            if (node.ip) {
                var ip = document.createElementNS(NS, "text");
                ip.setAttribute("class", "topo__ip");
                ip.setAttribute("text-anchor", "middle");
                ip.setAttribute("y", "68");
                ip.textContent = node.ip;
                g.appendChild(ip);
            }

            g.addEventListener("click", function () { selectDevice(node.hostname); });
            g.addEventListener("keydown", function (e) {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault(); selectDevice(node.hostname);
                }
            });
            nodesG.appendChild(g);
            nodeElements[node.hostname] = g;
        });
    }

    /* Update selection classes only — no DOM churn. */
    function updateSelection() {
        Object.keys(nodeElements).forEach(function (h) {
            var g = nodeElements[h];
            g.classList.toggle("is-selected", h === selected);
        });
        linkElements.forEach(function (le) {
            var incident = selected && (le.a === selected || le.b === selected);
            le.line.classList.toggle("topo__link--active", !!incident);
            if (le.pulse) le.pulse.classList.toggle("topo__pulse--active", !!incident);
        });
    }

    /* ----------------------------------------------------------------
       4. Selection & detail panel — defensive against missing fields
          and surfaces every error to the user.
    ----------------------------------------------------------------- */
    function selectDevice(hostname) {
        selected = hostname;
        updateSelection();

        var url = deviceUrlTpl.replace("__hostname__", encodeURIComponent(hostname));
        fetch(url, {credentials: "same-origin"})
            .then(function (r) {
                if (!r.ok) throw new Error("Server returned " + r.status);
                return r.json();
            })
            .then(function (d) { renderPanel(d); })
            .catch(function (err) {
                renderPanelError(hostname, err.message);
            });
    }

    function textDetail(v) {
        return (v === null || v === undefined || v === "") ? "—" : String(v);
    }

    function renderPanel(d) {
        try {
            panelEmpty.hidden = true;
            panelBody.hidden = false;
            panelLabel.textContent = d.label || d.hostname || "Device";
            panelStatus.textContent = d.status || "Online";

            panelFacts.innerHTML = "";
            [
                ["Hostname",    d.hostname],
                ["Device Type", d.device_type],
                ["OS",          d.os],
                ["IP Address",  d.ip],
                ["MAC Address", d.mac],
                ["Gateway",     d.gateway]
            ].forEach(function (row) {
                var dt = document.createElement("dt"); dt.textContent = row[0];
                var dd = document.createElement("dd"); dd.textContent = textDetail(row[1]);
                panelFacts.appendChild(dt); panelFacts.appendChild(dd);
            });

            panelPorts.innerHTML = "";
            var ports = Array.isArray(d.open_ports) ? d.open_ports : [];
            if (ports.length === 0) {
                var li = document.createElement("li");
                li.className = "topo__ports-empty";
                li.textContent = "No listening ports (simulated).";
                panelPorts.appendChild(li);
            } else {
                ports.forEach(function (p) {
                    var li = document.createElement("li");
                    var badge = document.createElement("span");
                    badge.className = "ui-badge ui-badge--primary";
                    badge.textContent = p.port;
                    li.appendChild(badge);
                    li.appendChild(document.createTextNode(" " + (p.service || "—")));
                    panelPorts.appendChild(li);
                });
            }

            panelConns.innerHTML = "";
            var conns = Array.isArray(d.connected) ? d.connected : [];
            if (conns.length === 0) {
                var li2 = document.createElement("li");
                li2.textContent = "No direct neighbours.";
                panelConns.appendChild(li2);
            } else {
                conns.forEach(function (c) {
                    var li = document.createElement("li");
                    var a = document.createElement("a");
                    a.href = "#";
                    a.textContent = (c.label || c.hostname) + " (" + c.device_type + ")";
                    a.addEventListener("click", function (e) {
                        e.preventDefault(); selectDevice(c.hostname);
                    });
                    li.appendChild(a);
                    panelConns.appendChild(li);
                });
            }
        } catch (err) {
            renderPanelError(d && d.hostname, err.message);
        }
    }

    function renderPanelError(hostname, message) {
        panelEmpty.hidden = true;
        panelBody.hidden = false;
        panelLabel.textContent = hostname || "Device";
        panelStatus.textContent = "Error";
        panelFacts.innerHTML = "";
        var dt = document.createElement("dt"); dt.textContent = "Error";
        var dd = document.createElement("dd"); dd.textContent = message;
        panelFacts.appendChild(dt); panelFacts.appendChild(dd);
        panelPorts.innerHTML = "";
        panelConns.innerHTML = "";
    }

    /* ----------------------------------------------------------------
       5. Zoom (buttons + Ctrl-wheel). Uses viewBox scaling — the SVG
          coordinate system is 900×460 and we scale around its centre
          via the transform-origin CSS variable so the map never
          shifts unexpectedly.
    ----------------------------------------------------------------- */
    function applyZoom() {
        viewport.style.transformOrigin = "450px 230px";
        viewport.style.transform = "scale(" + zoom + ")";
        zoomVal.textContent = Math.round(zoom * 100) + "%";
    }
    root.querySelectorAll("[data-zoom]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var dir = btn.getAttribute("data-zoom");
            if (dir === "in")    zoom = Math.min(2.4, zoom + 0.15);
            if (dir === "out")   zoom = Math.max(0.55, zoom - 0.15);
            if (dir === "reset") zoom = 1;
            applyZoom();
        });
    });
    svg.addEventListener("wheel", function (e) {
        if (!e.ctrlKey && !e.metaKey) return;
        e.preventDefault();
        zoom = Math.max(0.55, Math.min(2.4, zoom - e.deltaY * 0.001));
        applyZoom();
    }, {passive: false});
}());
