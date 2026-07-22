"""Admin routes.

Thin controllers only — all validation and persistence lives in
``app/admin/services.py``. Every route is admin-gated (403 otherwise) and
every mutation is a CSRF-protected POST.
"""

from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for

from app.admin import admin_bp, services
from app.admin.decorators import admin_required
from app.ctf.models import DIFFICULTIES


def _form_bool(name: str) -> bool:
    return request.form.get(name) in ("on", "true", "1", "yes")


def _flash_result(result: dict, success_msg: str) -> bool:
    """Flash the outcome of a service call; returns True when it succeeded."""
    if result.get("ok"):
        flash(success_msg, "success")
        return True
    flash(result.get("message", "Something went wrong."), "error")
    return False


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
@admin_bp.route("/ctf")
@admin_required
def ctf_overview():
    """Admin CTF landing page with counts."""
    return render_template(
        "admin/ctf_overview.html",
        overview=services.get_admin_overview(),
    )


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
@admin_bp.route("/ctf/categories")
@admin_required
def ctf_categories():
    """List categories with their challenge counts."""
    categories = services.list_categories()
    rows = [
        {
            "id": c.id, "name": c.name, "slug": c.slug, "icon": c.icon,
            "description": c.description, "display_order": c.display_order,
            "is_active": c.is_active,
            "challenge_count": services.challenge_count_for_category(c.id),
        }
        for c in categories
    ]
    return render_template("admin/ctf_categories.html", categories=rows)


@admin_bp.route("/ctf/categories/new", methods=["POST"])
@admin_required
def ctf_category_create():
    result = services.create_category(
        name=request.form.get("name", ""),
        slug=request.form.get("slug", ""),
        description=request.form.get("description", ""),
        icon=request.form.get("icon", "flag"),
        display_order=request.form.get("display_order", 0),
        is_active=_form_bool("is_active"),
    )
    _flash_result(result, "Category created.")
    return redirect(url_for("admin.ctf_categories"))


@admin_bp.route("/ctf/categories/<int:category_id>/edit", methods=["POST"])
@admin_required
def ctf_category_edit(category_id: int):
    result = services.update_category(
        category_id,
        name=request.form.get("name", ""),
        slug=request.form.get("slug", ""),
        description=request.form.get("description", ""),
        icon=request.form.get("icon", "flag"),
        display_order=request.form.get("display_order", 0),
        is_active=_form_bool("is_active"),
    )
    _flash_result(result, "Category updated.")
    return redirect(url_for("admin.ctf_categories"))


@admin_bp.route("/ctf/categories/<int:category_id>/delete", methods=["POST"])
@admin_required
def ctf_category_delete(category_id: int):
    result = services.delete_category(category_id)
    _flash_result(result, "Category deleted.")
    return redirect(url_for("admin.ctf_categories"))


# ---------------------------------------------------------------------------
# Challenges
# ---------------------------------------------------------------------------
@admin_bp.route("/ctf/challenges")
@admin_required
def ctf_challenges():
    """List every challenge with category and hint counts."""
    rows = [
        {
            "id": ch.id, "title": ch.title, "slug": ch.slug,
            "category": ch.category.name if ch.category else "—",
            "difficulty": ch.difficulty, "points": ch.points,
            "xp_reward": ch.xp_reward, "is_active": ch.is_active,
            "author": ch.author,
            "estimated_minutes": ch.estimated_minutes,
            "hint_count": services.hint_count_for_challenge(ch.id),
        }
        for ch in services.list_challenges()
    ]
    return render_template("admin/ctf_challenges.html", challenges=rows)


@admin_bp.route("/ctf/challenges/new", methods=["GET"])
@admin_required
def ctf_challenge_new():
    """Blank challenge form."""
    return render_template(
        "admin/ctf_challenge_form.html",
        challenge=None,
        categories=services.list_categories(),
        difficulties=DIFFICULTIES,
    )


@admin_bp.route("/ctf/challenges/new", methods=["POST"])
@admin_required
def ctf_challenge_create():
    result = services.create_challenge(
        title=request.form.get("title", ""),
        category_id=request.form.get("category_id", 0),
        difficulty=request.form.get("difficulty", "Easy"),
        flag=request.form.get("flag", ""),
        slug=request.form.get("slug", ""),
        description=request.form.get("description", ""),
        points=request.form.get("points", 0),
        xp_reward=request.form.get("xp_reward", 0),
        estimated_minutes=request.form.get("estimated_minutes") or None,
        author=request.form.get("author", ""),
        display_order=request.form.get("display_order", 0),
        is_active=_form_bool("is_active"),
    )
    if not _flash_result(result, "Challenge created."):
        return render_template(
            "admin/ctf_challenge_form.html",
            challenge=None,
            categories=services.list_categories(),
            difficulties=DIFFICULTIES,
            form=request.form,
        )
    return redirect(url_for("admin.ctf_challenges"))


@admin_bp.route("/ctf/challenges/<int:challenge_id>/edit", methods=["GET"])
@admin_required
def ctf_challenge_edit(challenge_id: int):
    """Edit form for an existing challenge (never shows the flag)."""
    challenge = services.get_challenge_by_id(challenge_id)
    if challenge is None:
        flash("Challenge not found.", "error")
        return redirect(url_for("admin.ctf_challenges"))
    return render_template(
        "admin/ctf_challenge_form.html",
        challenge=challenge,
        categories=services.list_categories(),
        difficulties=DIFFICULTIES,
        hints=services.list_hints(),
    )


@admin_bp.route("/ctf/challenges/<int:challenge_id>/edit", methods=["POST"])
@admin_required
def ctf_challenge_update(challenge_id: int):
    result = services.update_challenge(
        challenge_id,
        title=request.form.get("title", ""),
        category_id=request.form.get("category_id", 0),
        difficulty=request.form.get("difficulty", "Easy"),
        description=request.form.get("description", ""),
        slug=request.form.get("slug", ""),
        flag=request.form.get("flag", ""),   # blank = keep existing flag
        points=request.form.get("points", 0),
        xp_reward=request.form.get("xp_reward", 0),
        estimated_minutes=request.form.get("estimated_minutes") or None,
        author=request.form.get("author", ""),
        display_order=request.form.get("display_order", 0),
        is_active=_form_bool("is_active"),
    )
    _flash_result(result, "Challenge updated.")
    return redirect(url_for("admin.ctf_challenge_edit", challenge_id=challenge_id))


@admin_bp.route("/ctf/challenges/<int:challenge_id>/delete", methods=["POST"])
@admin_required
def ctf_challenge_delete(challenge_id: int):
    result = services.delete_challenge(challenge_id)
    _flash_result(result, "Challenge deleted.")
    return redirect(url_for("admin.ctf_challenges"))


# ---------------------------------------------------------------------------
# Hints
# ---------------------------------------------------------------------------
@admin_bp.route("/ctf/hints")
@admin_required
def ctf_hints():
    """List every hint, grouped by challenge."""
    challenges = services.list_challenges()
    groups = []
    for ch in challenges:
        hints = [
            {"id": h.id, "title": h.title, "content": h.content,
             "display_order": h.display_order, "is_free": h.is_free}
            for h in sorted(
                [x for x in ch.hints], key=lambda x: x.display_order
            )
        ]
        groups.append({
            "id": ch.id, "title": ch.title, "slug": ch.slug, "hints": hints,
        })
    return render_template("admin/ctf_hints.html", groups=groups)


@admin_bp.route("/ctf/hints/new", methods=["POST"])
@admin_required
def ctf_hint_create():
    result = services.create_hint(
        challenge_id=request.form.get("challenge_id", 0),
        title=request.form.get("title", ""),
        content=request.form.get("content", ""),
        display_order=request.form.get("display_order") or None,
        is_free=_form_bool("is_free"),
    )
    _flash_result(result, "Hint added.")
    return redirect(url_for("admin.ctf_hints"))


@admin_bp.route("/ctf/hints/<int:hint_id>/edit", methods=["POST"])
@admin_required
def ctf_hint_edit(hint_id: int):
    result = services.update_hint(
        hint_id,
        title=request.form.get("title", ""),
        content=request.form.get("content", ""),
        display_order=request.form.get("display_order") or None,
        is_free=_form_bool("is_free"),
    )
    _flash_result(result, "Hint updated.")
    return redirect(url_for("admin.ctf_hints"))


@admin_bp.route("/ctf/hints/<int:hint_id>/delete", methods=["POST"])
@admin_required
def ctf_hint_delete(hint_id: int):
    result = services.delete_hint(hint_id)
    _flash_result(result, "Hint deleted.")
    return redirect(url_for("admin.ctf_hints"))


@admin_bp.route("/ctf/hints/<int:hint_id>/reorder", methods=["POST"])
@admin_required
def ctf_hint_reorder(hint_id: int):
    result = services.reorder_hint(hint_id, request.form.get("direction", ""))
    _flash_result(result, "Hint reordered.")
    return redirect(url_for("admin.ctf_hints"))


# ---------------------------------------------------------------------------
# Active Directory Domain Builder (YC-031.0)
# ---------------------------------------------------------------------------
# Admins author complete virtual domains — users, groups, OUs, computers,
# shares and Group Policy — as schema-validated JSON. Built-ins are shown
# read-only as reference templates; the "clone" action prefills the create
# form with a built-in so a new scenario starts from a working example.
@admin_bp.route("/ad")
@admin_required
def ad_domains():
    from app.labs.ad.domains import BUILTIN_DOMAINS
    from app.labs.ad.models import ADCustomDomain

    customs = ADCustomDomain.query.order_by(ADCustomDomain.key).all()
    builtins = [
        {"key": key, "name": d["name"],
         "description": d.get("description", ""),
         "users": len(d.get("users", [])),
         "groups": len(d.get("groups", [])),
         "ous": len(d.get("ous", [])),
         "gpos": len(d.get("gpos", []))}
        for key, d in sorted(BUILTIN_DOMAINS.items())
    ]
    custom_rows = []
    for row in customs:
        definition = row.get_definition()
        custom_rows.append({
            "id": row.id, "key": row.key, "name": row.name,
            "description": row.description or "",
            "is_active": row.is_active,
            "users": len(definition.get("users", [])),
            "groups": len(definition.get("groups", [])),
            "ous": len(definition.get("ous", [])),
            "gpos": len(definition.get("gpos", [])),
        })
    return render_template("admin/ad_domains.html",
                           builtins=builtins, customs=custom_rows)


@admin_bp.route("/ad/new", methods=["GET"])
@admin_required
def ad_domain_new():
    import json as _json

    from app.labs.ad.domains import BUILTIN_DOMAINS

    template_key = request.args.get("from", "")
    if template_key in BUILTIN_DOMAINS:
        definition = dict(BUILTIN_DOMAINS[template_key])
        definition["key"] = f"{template_key}-copy"
        definition["name"] = f"{definition['name']} (copy)"
        raw = _json.dumps(definition, indent=2)
    else:
        raw = _json.dumps({
            "key": "training-local", "name": "TRAINING.LOCAL",
            "netbios": "TRAINING",
            "description": "Describe your scenario here.",
            "ous": [{"slug": "staff", "name": "Staff"}],
            "groups": [
                {"slug": "domain-admins", "name": "Domain Admins",
                 "builtin": True},
                {"slug": "domain-users", "name": "Domain Users",
                 "builtin": True},
            ],
            "users": [{"sam": "administrator", "display": "Administrator",
                       "ou": "staff",
                       "groups": ["domain-admins", "domain-users"]}],
            "computers": [{"name": "DC-01", "ou": "staff",
                           "os": "Windows Server 2022", "ip": "10.30.0.10",
                           "is_dc": True}],
            "shares": [], "gpos": [],
        }, indent=2)
    return render_template("admin/ad_domain_form.html", mode="new",
                           raw=raw, domain=None)


@admin_bp.route("/ad/new", methods=["POST"])
@admin_required
def ad_domain_create():
    from flask_login import current_user

    from app.extensions import db
    from app.labs.ad.domains import parse_domain_json
    from app.labs.ad.models import ADCustomDomain

    raw = request.form.get("definition_json", "")
    definition, errors = parse_domain_json(raw)
    if errors:
        for message in errors[:8]:
            flash(message, "error")
        return render_template("admin/ad_domain_form.html", mode="new",
                               raw=raw, domain=None), 400

    key = definition["key"].strip().lower()
    if ADCustomDomain.query.filter_by(key=key).first() is not None:
        flash(f"A custom domain with key '{key}' already exists.", "error")
        return render_template("admin/ad_domain_form.html", mode="new",
                               raw=raw, domain=None), 400

    row = ADCustomDomain(
        key=key, name=definition["name"],
        description=definition.get("description", ""),
        is_active=True, created_by=current_user.id,
    )
    row.set_definition(definition)
    db.session.add(row)
    db.session.commit()
    flash(f"Domain '{definition['name']}' created and validated.", "success")
    return redirect(url_for("admin.ad_domains"))


@admin_bp.route("/ad/<int:domain_id>/edit", methods=["GET"])
@admin_required
def ad_domain_edit(domain_id: int):
    from app.labs.ad.models import ADCustomDomain

    row = ADCustomDomain.query.get_or_404(domain_id)
    return render_template("admin/ad_domain_form.html", mode="edit",
                           raw=row.definition_json, domain=row)


@admin_bp.route("/ad/<int:domain_id>/edit", methods=["POST"])
@admin_required
def ad_domain_update(domain_id: int):
    from app.extensions import db
    from app.labs.ad.domains import parse_domain_json
    from app.labs.ad.models import ADCustomDomain

    row = ADCustomDomain.query.get_or_404(domain_id)
    raw = request.form.get("definition_json", "")
    definition, errors = parse_domain_json(raw)
    if errors:
        for message in errors[:8]:
            flash(message, "error")
        return render_template("admin/ad_domain_form.html", mode="edit",
                               raw=raw, domain=row), 400

    key = definition["key"].strip().lower()
    clash = ADCustomDomain.query.filter(
        ADCustomDomain.key == key, ADCustomDomain.id != row.id).first()
    if clash is not None:
        flash(f"Another custom domain already uses key '{key}'.", "error")
        return render_template("admin/ad_domain_form.html", mode="edit",
                               raw=raw, domain=row), 400

    row.key = key
    row.name = definition["name"]
    row.description = definition.get("description", "")
    row.set_definition(definition)
    db.session.commit()
    flash(f"Domain '{row.name}' updated.", "success")
    return redirect(url_for("admin.ad_domains"))


@admin_bp.route("/ad/<int:domain_id>/toggle", methods=["POST"])
@admin_required
def ad_domain_toggle(domain_id: int):
    from app.extensions import db
    from app.labs.ad.models import ADCustomDomain

    row = ADCustomDomain.query.get_or_404(domain_id)
    row.is_active = not row.is_active
    db.session.commit()
    flash(f"Domain '{row.name}' "
          f"{'activated' if row.is_active else 'deactivated'}.", "success")
    return redirect(url_for("admin.ad_domains"))


@admin_bp.route("/ad/<int:domain_id>/delete", methods=["POST"])
@admin_required
def ad_domain_delete(domain_id: int):
    from app.extensions import db
    from app.labs.ad.models import ADCustomDomain

    row = ADCustomDomain.query.get_or_404(domain_id)
    name = row.name
    db.session.delete(row)
    db.session.commit()
    flash(f"Domain '{name}' deleted.", "success")
    return redirect(url_for("admin.ad_domains"))


# ---------------------------------------------------------------------------
# Cloud Scenario Builder (YC-032.0)
# ---------------------------------------------------------------------------
# Admins author complete virtual cloud accounts — IAM users/roles, buckets,
# VPCs, security groups, VMs, load balancers, databases and the password
# policy — as schema-validated JSON. Built-ins are shown read-only as
# reference templates; "clone" prefills the create form with a working
# example so a new security challenge starts from a known-good scenario.
@admin_bp.route("/cloud")
@admin_required
def cloud_scenarios():
    from app.labs.cloud.accounts import BUILTIN_ACCOUNTS
    from app.labs.cloud.models import CloudCustomScenario

    customs = CloudCustomScenario.query.order_by(
        CloudCustomScenario.key).all()
    builtins = [
        {"key": key, "name": d["name"],
         "description": d.get("description", ""),
         "users": len(d.get("iam_users", [])),
         "buckets": len(d.get("buckets", [])),
         "sgs": len(d.get("security_groups", [])),
         "dbs": len(d.get("databases", []))}
        for key, d in sorted(BUILTIN_ACCOUNTS.items())
    ]
    custom_rows = []
    for row in customs:
        definition = row.get_definition()
        custom_rows.append({
            "id": row.id, "key": row.key, "name": row.name,
            "description": row.description or "",
            "is_active": row.is_active,
            "users": len(definition.get("iam_users", [])),
            "buckets": len(definition.get("buckets", [])),
            "sgs": len(definition.get("security_groups", [])),
            "dbs": len(definition.get("databases", [])),
        })
    return render_template("admin/cloud_scenarios.html",
                           builtins=builtins, customs=custom_rows)


@admin_bp.route("/cloud/new", methods=["GET"])
@admin_required
def cloud_scenario_new():
    import json as _json

    from app.labs.cloud.accounts import BUILTIN_ACCOUNTS

    template_key = request.args.get("from", "")
    if template_key in BUILTIN_ACCOUNTS:
        definition = dict(BUILTIN_ACCOUNTS[template_key])
        definition["key"] = f"{template_key}-copy"
        definition["name"] = f"{definition['name']} (copy)"
        raw = _json.dumps(definition, indent=2)
    else:
        raw = _json.dumps({
            "key": "training-cloud", "provider": "yushacloud",
            "name": "YushaCloud — Training",
            "account_id": "yc-900000001", "region": "np-ktm-1",
            "description": "Describe your scenario here.",
            "roles": [
                {"slug": "administrator", "name": "Administrator",
                 "description": "Full control.", "permissions": ["*:*"]},
                {"slug": "developer", "name": "Developer",
                 "description": "Application work.",
                 "permissions": ["compute:*", "storage:read"]},
            ],
            "iam_users": [
                {"username": "root-admin", "display": "Account Owner",
                 "roles": ["administrator"],
                 "expected_role": "administrator", "mfa": True,
                 "access_key_active": False, "last_used_days": 0},
            ],
            "password_policy": {"min_length": 6, "require_numbers": False,
                                "require_symbols": False,
                                "mfa_required": False, "max_age_days": 0},
            "buckets": [
                {"slug": "data", "name": "data", "public": True,
                 "encrypted": False, "versioning": False,
                 "intended_public": False,
                 "description": "A bucket that should be private.",
                 "objects": [{"key": "secret.csv", "size": "1 MB",
                              "sensitive": True}]},
            ],
            "vpcs": [
                {"slug": "main-vpc", "name": "main-vpc",
                 "cidr": "10.60.0.0/16", "internet_gateway": True,
                 "subnets": [{"slug": "public-a", "cidr": "10.60.1.0/24",
                              "public": True}]},
            ],
            "security_groups": [
                {"slug": "default-sg", "name": "default-sg",
                 "description": "Default group.",
                 "rules": [{"direction": "ingress", "protocol": "tcp",
                            "port": 22, "cidr": "0.0.0.0/0",
                            "description": "SSH from anywhere"}]},
            ],
            "vms": [
                {"slug": "vm-01", "name": "vm-01", "subnet": "public-a",
                 "security_group": "default-sg",
                 "public_ip": "203.0.113.50", "state": "running",
                 "size": "small", "description": "A training VM."},
            ],
            "load_balancers": [],
            "databases": [],
        }, indent=2)
    return render_template("admin/cloud_scenario_form.html", mode="new",
                           raw=raw, scenario=None)


@admin_bp.route("/cloud/new", methods=["POST"])
@admin_required
def cloud_scenario_create():
    from flask_login import current_user

    from app.extensions import db
    from app.labs.cloud.accounts import parse_account_json
    from app.labs.cloud.models import CloudCustomScenario

    raw = request.form.get("definition_json", "")
    definition, errors = parse_account_json(raw)
    if errors:
        for message in errors[:8]:
            flash(message, "error")
        return render_template("admin/cloud_scenario_form.html", mode="new",
                               raw=raw, scenario=None), 400

    key = definition["key"].strip().lower()
    if CloudCustomScenario.query.filter_by(key=key).first() is not None:
        flash(f"A custom scenario with key '{key}' already exists.",
              "error")
        return render_template("admin/cloud_scenario_form.html", mode="new",
                               raw=raw, scenario=None), 400

    row = CloudCustomScenario(
        key=key, name=definition["name"],
        description=definition.get("description", ""),
        is_active=True, created_by=current_user.id,
    )
    row.set_definition(definition)
    db.session.add(row)
    db.session.commit()
    flash(f"Scenario '{definition['name']}' created and validated.",
          "success")
    return redirect(url_for("admin.cloud_scenarios"))


@admin_bp.route("/cloud/<int:scenario_id>/edit", methods=["GET"])
@admin_required
def cloud_scenario_edit(scenario_id: int):
    from app.labs.cloud.models import CloudCustomScenario

    row = CloudCustomScenario.query.get_or_404(scenario_id)
    return render_template("admin/cloud_scenario_form.html", mode="edit",
                           raw=row.definition_json, scenario=row)


@admin_bp.route("/cloud/<int:scenario_id>/edit", methods=["POST"])
@admin_required
def cloud_scenario_update(scenario_id: int):
    from app.extensions import db
    from app.labs.cloud.accounts import parse_account_json
    from app.labs.cloud.models import CloudCustomScenario

    row = CloudCustomScenario.query.get_or_404(scenario_id)
    raw = request.form.get("definition_json", "")
    definition, errors = parse_account_json(raw)
    if errors:
        for message in errors[:8]:
            flash(message, "error")
        return render_template("admin/cloud_scenario_form.html",
                               mode="edit", raw=raw, scenario=row), 400

    key = definition["key"].strip().lower()
    clash = CloudCustomScenario.query.filter(
        CloudCustomScenario.key == key,
        CloudCustomScenario.id != row.id).first()
    if clash is not None:
        flash(f"Another custom scenario already uses key '{key}'.",
              "error")
        return render_template("admin/cloud_scenario_form.html",
                               mode="edit", raw=raw, scenario=row), 400

    row.key = key
    row.name = definition["name"]
    row.description = definition.get("description", "")
    row.set_definition(definition)
    db.session.commit()
    flash(f"Scenario '{row.name}' updated.", "success")
    return redirect(url_for("admin.cloud_scenarios"))


@admin_bp.route("/cloud/<int:scenario_id>/toggle", methods=["POST"])
@admin_required
def cloud_scenario_toggle(scenario_id: int):
    from app.extensions import db
    from app.labs.cloud.models import CloudCustomScenario

    row = CloudCustomScenario.query.get_or_404(scenario_id)
    row.is_active = not row.is_active
    db.session.commit()
    flash(f"Scenario '{row.name}' "
          f"{'activated' if row.is_active else 'deactivated'}.", "success")
    return redirect(url_for("admin.cloud_scenarios"))


@admin_bp.route("/cloud/<int:scenario_id>/delete", methods=["POST"])
@admin_required
def cloud_scenario_delete(scenario_id: int):
    from app.extensions import db
    from app.labs.cloud.models import CloudCustomScenario

    row = CloudCustomScenario.query.get_or_404(scenario_id)
    name = row.name
    db.session.delete(row)
    db.session.commit()
    flash(f"Scenario '{name}' deleted.", "success")
    return redirect(url_for("admin.cloud_scenarios"))


# ---------------------------------------------------------------------------
# Digital Forensics cases (YC-029.5.2)
# ---------------------------------------------------------------------------
@admin_bp.route("/forensics")
@admin_required
def forensics_cases():
    from app.labs.forensics.models import ForensicsCase
    cases = ForensicsCase.query.order_by(ForensicsCase.lab_slug).all()
    return render_template("admin/forensics_cases.html", cases=cases)


@admin_bp.route("/forensics/<int:case_id>", methods=["GET"])
@admin_required
def forensics_case_edit(case_id: int):
    from app.labs.forensics.engine import simulated_hash
    from app.labs.forensics.models import (
        EVIDENCE_KINDS, TIMELINE_KINDS, ForensicsCase,
    )
    case = ForensicsCase.query.get_or_404(case_id)
    evidence_hashes = {
        e.slug: {"md5": simulated_hash(e.slug, "md5"),
                 "sha256": simulated_hash(e.slug, "sha256")}
        for e in case.evidence
    }
    from app.labs.forensics.engine import ARTIFACT_SCHEMA, SOURCE_LABEL
    from app.labs.forensics.models import ARTIFACT_SOURCES
    from app.labs.models import Lab
    lab = Lab.query.filter_by(slug=case.lab_slug).first()
    # Group artifacts by source for the applied editor.
    artifacts_by_source = {}
    for artifact in case.artifacts:
        artifacts_by_source.setdefault(
            artifact.source_type, []).append(artifact)
    return render_template(
        "admin/forensics_case_form.html", case=case, lab=lab,
        evidence_kinds=EVIDENCE_KINDS, timeline_kinds=TIMELINE_KINDS,
        evidence_hashes=evidence_hashes,
        artifact_sources=ARTIFACT_SOURCES,
        source_label=SOURCE_LABEL, artifact_schema=ARTIFACT_SCHEMA,
        artifacts_by_source=artifacts_by_source)


@admin_bp.route("/forensics/<int:case_id>/save", methods=["POST"])
@admin_required
def forensics_case_save(case_id: int):
    """Update the case briefing/workstation plus every evidence and
    timeline row. Rows are matched by the ``id`` hidden field for
    updates; missing ids mean the admin removed that row. New rows
    have no id and are inserted."""
    from app.labs.forensics.models import (
        ForensicsCase, ForensicsEvidence, ForensicsTimelineEvent,
    )
    from app.extensions import db as _db
    case = ForensicsCase.query.get_or_404(case_id)

    case.title = (request.form.get("title") or case.title).strip()[:160]
    case.briefing = (request.form.get("briefing") or "").strip()
    case.workstation_name = (
        request.form.get("workstation_name") or "WORKSTATION-01").strip()[:80]
    case.investigator = (
        request.form.get("investigator") or "Investigator").strip()[:80]

    # Evidence: indexed by row order (e.g. name="evidence-<idx>-slug").
    idx = 0
    new_evidence = []
    while f"evidence-{idx}-slug" in request.form:
        row_id = request.form.get(f"evidence-{idx}-id")
        slug = (request.form.get(f"evidence-{idx}-slug") or "").strip().lower()
        filename = (request.form.get(f"evidence-{idx}-filename") or "").strip()
        if slug and filename:
            data = {
                "slug": slug[:80],
                "kind": request.form.get(f"evidence-{idx}-kind") or "document",
                "filename": filename[:160],
                "extension": (request.form.get(f"evidence-{idx}-extension")
                              or "").strip()[:20],
                "owner": (request.form.get(f"evidence-{idx}-owner")
                          or "user").strip()[:60],
                "size_bytes": int(
                    request.form.get(f"evidence-{idx}-size_bytes") or 0),
                "created_at_display": (
                    request.form.get(f"evidence-{idx}-created") or "")[:40],
                "modified_at_display": (
                    request.form.get(f"evidence-{idx}-modified") or "")[:40],
                "notes": request.form.get(f"evidence-{idx}-notes") or "",
                "is_suspicious": bool(
                    request.form.get(f"evidence-{idx}-is_suspicious")),
                "is_modified": bool(
                    request.form.get(f"evidence-{idx}-is_modified")),
                "display_order": idx + 1,
            }
            new_evidence.append((row_id, data))
        idx += 1

    # Wipe & re-insert (simplest correct approach — SQLite friendly).
    ForensicsEvidence.query.filter_by(case_id=case.id).delete()
    _db.session.flush()
    for _row_id, data in new_evidence:
        _db.session.add(ForensicsEvidence(case_id=case.id, **data))

    # Timeline rows.
    idx = 0
    new_timeline = []
    while f"timeline-{idx}-description" in request.form:
        at_time = (request.form.get(f"timeline-{idx}-at_time") or "").strip()
        description = (request.form.get(f"timeline-{idx}-description")
                       or "").strip()
        if at_time and description:
            new_timeline.append({
                "at_time": at_time[:8],
                "kind": request.form.get(f"timeline-{idx}-kind") or "other",
                "description": description[:200],
                "evidence_slug": (
                    request.form.get(f"timeline-{idx}-evidence_slug")
                    or "").strip()[:80] or None,
            })
        idx += 1
    ForensicsTimelineEvent.query.filter_by(case_id=case.id).delete()
    _db.session.flush()
    for data in new_timeline:
        _db.session.add(ForensicsTimelineEvent(case_id=case.id, **data))

    _db.session.commit()
    flash(f"Case '{case.title}' saved — "
          f"{len(new_evidence)} evidence items, "
          f"{len(new_timeline)} timeline events.", "success")
    return redirect(url_for("admin.forensics_case_edit", case_id=case.id))


@admin_bp.route("/forensics/<int:case_id>/objectives", methods=["POST"])
@admin_required
def forensics_case_objectives(case_id: int):
    """Edit the lab's objectives (title, instruction, hints, XP).
    Validator specs stay locked — they're wired to the simulator's
    events and would break if changed casually."""
    from app.labs.forensics.models import ForensicsCase
    from app.labs.models import Lab
    from app.extensions import db as _db
    case = ForensicsCase.query.get_or_404(case_id)
    lab = Lab.query.filter_by(slug=case.lab_slug).first_or_404()

    for objective in lab.objectives:
        key = f"objective-{objective.id}-"
        title = (request.form.get(key + "title") or objective.title).strip()
        instruction = (request.form.get(key + "instruction") or "").strip()
        xp = int(request.form.get(key + "xp") or objective.xp_reward)
        objective.title = title[:150]
        objective.instruction = instruction or objective.instruction
        objective.description = instruction or objective.description
        objective.xp_reward = max(0, xp)
        objective.hint1 = (request.form.get(key + "hint1") or "").strip() or None
        objective.hint2 = (request.form.get(key + "hint2") or "").strip() or None
        objective.hint3 = (request.form.get(key + "hint3") or "").strip() or None
    _db.session.commit()
    flash("Objectives saved.", "success")
    return redirect(url_for("admin.forensics_case_edit", case_id=case.id))


@admin_bp.route("/forensics/<int:case_id>/artifacts", methods=["POST"])
@admin_required
def forensics_case_artifacts(case_id: int):
    """Replace all artifacts for a case with the submitted rows.

    Artifact rows come indexed by (source_type, row idx). Each row has
    an at_time, an is_key flag, and a JSON blob of source-specific
    fields — a simple textarea in the admin UI because these are
    open-ended source rows.
    """
    from app.extensions import db as _db
    from app.labs.forensics.engine import ARTIFACT_SCHEMA
    from app.labs.forensics.models import (
        ARTIFACT_SOURCES, ForensicsArtifact, ForensicsCase,
    )
    case = ForensicsCase.query.get_or_404(case_id)

    kept = []
    order = 0
    for source_type in ARTIFACT_SOURCES:
        if source_type not in ARTIFACT_SCHEMA:
            continue
        idx = 0
        while f"artifact-{source_type}-{idx}-at_time" in request.form:
            at_time = (request.form.get(
                f"artifact-{source_type}-{idx}-at_time") or "").strip()
            if at_time:
                data = {}
                for field in ARTIFACT_SCHEMA[source_type]:
                    key = f"artifact-{source_type}-{idx}-{field}"
                    value = request.form.get(key)
                    if field.endswith("_bytes") or field == "visit_count":
                        try:
                            data[field] = int(value or 0)
                        except (TypeError, ValueError):
                            data[field] = 0
                    else:
                        data[field] = (value or "").strip()
                is_key = bool(request.form.get(
                    f"artifact-{source_type}-{idx}-is_key"))
                order += 1
                kept.append((source_type, at_time[:40], data,
                             is_key, order))
            idx += 1

    ForensicsArtifact.query.filter_by(case_id=case.id).delete()
    _db.session.flush()
    for source_type, at_time, data, is_key, order_ in kept:
        artifact = ForensicsArtifact(
            case_id=case.id, source_type=source_type,
            at_time=at_time, is_key=is_key, sort_order=order_)
        artifact.set_data(data)
        _db.session.add(artifact)
    _db.session.commit()
    flash(f"Saved {len(kept)} artifact rows across "
          f"{len({s for s, *_ in kept})} sources.", "success")
    return redirect(url_for("admin.forensics_case_edit", case_id=case.id))
