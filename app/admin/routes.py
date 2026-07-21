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
