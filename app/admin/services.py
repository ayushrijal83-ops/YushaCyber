"""Admin CTF management services.

All admin write-logic for the CTF platform lives here so the routes stay
thin. Reuses the existing CTF models; no CTF business logic (solving,
scoring, XP) is duplicated or touched — this module only manages content.

Every mutator returns a structured result:
    {"ok": True,  "obj": <model>}
    {"ok": False, "error": "<code>", "message": "<human text>"}
"""

from __future__ import annotations

import re
from typing import Any, Optional

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.ctf.models import (
    DIFFICULTIES,
    Challenge,
    ChallengeCategory,
    ChallengeHint,
    ChallengeSolve,
)
from app.extensions import db

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slugify(value: str) -> str:
    """Turn a title into a URL-safe slug."""
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    value = re.sub(r"[\s_-]+", "-", value)
    return value.strip("-")


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": code, "message": message}


# ---------------------------------------------------------------------------
# Read helpers (admin views — include inactive rows, unlike the public services)
# ---------------------------------------------------------------------------
def list_categories() -> list[ChallengeCategory]:
    """Every category (active and inactive) in display order."""
    return ChallengeCategory.query.order_by(
        ChallengeCategory.display_order, ChallengeCategory.id
    ).all()


def list_challenges() -> list[Challenge]:
    """Every challenge (active and inactive), grouped by category order."""
    return Challenge.query.order_by(
        Challenge.category_id, Challenge.display_order, Challenge.id
    ).all()


def list_hints() -> list[ChallengeHint]:
    """Every hint, ordered by challenge then position."""
    return ChallengeHint.query.order_by(
        ChallengeHint.challenge_id, ChallengeHint.display_order
    ).all()


def get_category_by_id(category_id: int) -> Optional[ChallengeCategory]:
    return ChallengeCategory.query.filter_by(id=category_id).first()


def get_challenge_by_id(challenge_id: int) -> Optional[Challenge]:
    return Challenge.query.filter_by(id=challenge_id).first()


def get_hint_by_id(hint_id: int) -> Optional[ChallengeHint]:
    return ChallengeHint.query.filter_by(id=hint_id).first()


def challenge_count_for_category(category_id: int) -> int:
    return Challenge.query.filter_by(category_id=category_id).count()


def hint_count_for_challenge(challenge_id: int) -> int:
    return ChallengeHint.query.filter_by(challenge_id=challenge_id).count()


def get_admin_overview() -> dict[str, int]:
    """Counts for the admin CTF landing page."""
    return {
        "categories": ChallengeCategory.query.count(),
        "challenges": Challenge.query.count(),
        "hints": ChallengeHint.query.count(),
        "solves": ChallengeSolve.query.filter_by(solved=True).count(),
        "difficulties": list(DIFFICULTIES),
    }


# ---------------------------------------------------------------------------
# Category CRUD
# ---------------------------------------------------------------------------
def create_category(name: str, slug: str = "", description: str = "",
                    icon: str = "flag", display_order: int = 0,
                    is_active: bool = True) -> dict[str, Any]:
    """Create a category. Slug must be unique (auto-derived if blank)."""
    name = (name or "").strip()
    if not name:
        return _fail("name_required", "Name is required.")

    slug = slugify(slug or name)
    if not slug or not _SLUG_RE.match(slug):
        return _fail("bad_slug", "Slug must be lowercase letters, numbers and hyphens.")
    if ChallengeCategory.query.filter_by(slug=slug).first():
        return _fail("slug_taken", f"A category with slug '{slug}' already exists.")

    try:
        category = ChallengeCategory(
            name=name, slug=slug, description=(description or "").strip() or None,
            icon=(icon or "flag").strip(), display_order=int(display_order or 0),
            is_active=bool(is_active),
        )
        db.session.add(category)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to create category")
        return _fail("persist_failed", "Could not save the category.")

    return {"ok": True, "obj": category}


def update_category(category_id: int, name: str, slug: str, description: str,
                    icon: str, display_order: int,
                    is_active: bool) -> dict[str, Any]:
    """Update a category; slug stays unique."""
    category = get_category_by_id(category_id)
    if category is None:
        return _fail("not_found", "Category not found.")

    name = (name or "").strip()
    if not name:
        return _fail("name_required", "Name is required.")

    slug = slugify(slug or name)
    if not slug or not _SLUG_RE.match(slug):
        return _fail("bad_slug", "Slug must be lowercase letters, numbers and hyphens.")
    clash = ChallengeCategory.query.filter(
        ChallengeCategory.slug == slug, ChallengeCategory.id != category.id
    ).first()
    if clash:
        return _fail("slug_taken", f"A category with slug '{slug}' already exists.")

    try:
        category.name = name
        category.slug = slug
        category.description = (description or "").strip() or None
        category.icon = (icon or "flag").strip()
        category.display_order = int(display_order or 0)
        category.is_active = bool(is_active)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to update category %s", category_id)
        return _fail("persist_failed", "Could not save the category.")

    return {"ok": True, "obj": category}


def delete_category(category_id: int) -> dict[str, Any]:
    """Delete a category ONLY if it has no challenges."""
    category = get_category_by_id(category_id)
    if category is None:
        return _fail("not_found", "Category not found.")

    used = challenge_count_for_category(category.id)
    if used:
        return _fail(
            "category_in_use",
            f"Cannot delete '{category.name}': it still has {used} challenge(s).",
        )

    try:
        db.session.delete(category)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to delete category %s", category_id)
        return _fail("persist_failed", "Could not delete the category.")

    return {"ok": True, "obj": None}


# ---------------------------------------------------------------------------
# Challenge CRUD
# ---------------------------------------------------------------------------
def _validate_challenge_fields(title: str, difficulty: str,
                               category_id: int) -> Optional[dict[str, Any]]:
    if not (title or "").strip():
        return _fail("title_required", "Title is required.")
    if difficulty not in DIFFICULTIES:
        return _fail(
            "bad_difficulty",
            f"Difficulty must be one of: {', '.join(DIFFICULTIES)}.",
        )
    if get_category_by_id(category_id) is None:
        return _fail("bad_category", "Select a valid category.")
    return None


def create_challenge(title: str, category_id: int, difficulty: str, flag: str,
                     slug: str = "", description: str = "", points: int = 0,
                     xp_reward: int = 0, estimated_minutes: Optional[int] = None,
                     author: str = "", display_order: int = 0,
                     is_active: bool = True) -> dict[str, Any]:
    """Create a challenge. Slug unique; flag required and stored hashed."""
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        return _fail("bad_category", "Select a valid category.")

    problem = _validate_challenge_fields(title, difficulty, category_id)
    if problem:
        return problem

    if not (flag or "").strip():
        return _fail("flag_required", "Flag is required.")

    slug = slugify(slug or title)
    if not slug or not _SLUG_RE.match(slug):
        return _fail("bad_slug", "Slug must be lowercase letters, numbers and hyphens.")
    if Challenge.query.filter_by(slug=slug).first():
        return _fail("slug_taken", f"A challenge with slug '{slug}' already exists.")

    try:
        challenge = Challenge(
            category_id=category_id,
            title=title.strip(),
            slug=slug,
            description=(description or "").strip() or None,
            difficulty=difficulty,
            points=int(points or 0),
            xp_reward=int(xp_reward or 0),
            estimated_minutes=int(estimated_minutes) if estimated_minutes else None,
            author=(author or "").strip() or None,
            display_order=int(display_order or 0),
            is_active=bool(is_active),
        )
        challenge.set_flag(flag.strip())  # hashed — raw flag never stored
        db.session.add(challenge)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to create challenge")
        return _fail("persist_failed", "Could not save the challenge.")

    current_app.logger.info("Admin created challenge %s", challenge.slug)
    return {"ok": True, "obj": challenge}


def update_challenge(challenge_id: int, title: str, category_id: int,
                     difficulty: str, description: str = "", slug: str = "",
                     flag: str = "", points: int = 0, xp_reward: int = 0,
                     estimated_minutes: Optional[int] = None, author: str = "",
                     display_order: int = 0,
                     is_active: bool = True) -> dict[str, Any]:
    """Update a challenge. A blank flag leaves the existing one unchanged."""
    challenge = get_challenge_by_id(challenge_id)
    if challenge is None:
        return _fail("not_found", "Challenge not found.")

    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        return _fail("bad_category", "Select a valid category.")

    problem = _validate_challenge_fields(title, difficulty, category_id)
    if problem:
        return problem

    slug = slugify(slug or title)
    if not slug or not _SLUG_RE.match(slug):
        return _fail("bad_slug", "Slug must be lowercase letters, numbers and hyphens.")
    clash = Challenge.query.filter(
        Challenge.slug == slug, Challenge.id != challenge.id
    ).first()
    if clash:
        return _fail("slug_taken", f"A challenge with slug '{slug}' already exists.")

    try:
        challenge.title = title.strip()
        challenge.slug = slug
        challenge.category_id = category_id
        challenge.difficulty = difficulty
        challenge.description = (description or "").strip() or None
        challenge.points = int(points or 0)
        challenge.xp_reward = int(xp_reward or 0)
        challenge.estimated_minutes = (
            int(estimated_minutes) if estimated_minutes else None
        )
        challenge.author = (author or "").strip() or None
        challenge.display_order = int(display_order or 0)
        challenge.is_active = bool(is_active)

        # Only rotate the flag when a new one is supplied.
        if (flag or "").strip():
            challenge.set_flag(flag.strip())

        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to update challenge %s", challenge_id)
        return _fail("persist_failed", "Could not save the challenge.")

    current_app.logger.info("Admin updated challenge %s", challenge.slug)
    return {"ok": True, "obj": challenge}


def delete_challenge(challenge_id: int) -> dict[str, Any]:
    """Delete a challenge (its hints and solve records cascade)."""
    challenge = get_challenge_by_id(challenge_id)
    if challenge is None:
        return _fail("not_found", "Challenge not found.")

    try:
        slug = challenge.slug
        db.session.delete(challenge)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to delete challenge %s", challenge_id)
        return _fail("persist_failed", "Could not delete the challenge.")

    current_app.logger.info("Admin deleted challenge %s", slug)
    return {"ok": True, "obj": None}


# ---------------------------------------------------------------------------
# Hint CRUD
# ---------------------------------------------------------------------------
def create_hint(challenge_id: int, content: str, title: str = "",
                display_order: Optional[int] = None,
                is_free: bool = True) -> dict[str, Any]:
    """Add a hint to a challenge. Duplicate content on the same challenge
    is rejected, and display_order stays unique per challenge."""
    challenge = get_challenge_by_id(challenge_id)
    if challenge is None:
        return _fail("bad_challenge", "Select a valid challenge.")

    content = (content or "").strip()
    if not content:
        return _fail("content_required", "Hint content is required.")

    # Prevent duplicate hints (same text on the same challenge).
    dup = ChallengeHint.query.filter_by(
        challenge_id=challenge.id, content=content
    ).first()
    if dup:
        return _fail("duplicate_hint", "That hint already exists for this challenge.")

    if display_order in (None, "", 0):
        display_order = hint_count_for_challenge(challenge.id) + 1
    display_order = int(display_order)

    # Keep positions unique within a challenge.
    if ChallengeHint.query.filter_by(
        challenge_id=challenge.id, display_order=display_order
    ).first():
        display_order = hint_count_for_challenge(challenge.id) + 1

    try:
        hint = ChallengeHint(
            challenge_id=challenge.id,
            title=(title or "").strip() or f"Hint #{display_order}",
            content=content,
            display_order=display_order,
            is_free=bool(is_free),
        )
        db.session.add(hint)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to create hint")
        return _fail("persist_failed", "Could not save the hint.")

    return {"ok": True, "obj": hint}


def update_hint(hint_id: int, content: str, title: str = "",
                display_order: Optional[int] = None,
                is_free: bool = True) -> dict[str, Any]:
    """Edit a hint (content, title, position, free flag)."""
    hint = get_hint_by_id(hint_id)
    if hint is None:
        return _fail("not_found", "Hint not found.")

    content = (content or "").strip()
    if not content:
        return _fail("content_required", "Hint content is required.")

    dup = ChallengeHint.query.filter(
        ChallengeHint.challenge_id == hint.challenge_id,
        ChallengeHint.content == content,
        ChallengeHint.id != hint.id,
    ).first()
    if dup:
        return _fail("duplicate_hint", "That hint already exists for this challenge.")

    try:
        hint.content = content
        hint.title = (title or "").strip() or hint.title
        if display_order not in (None, ""):
            hint.display_order = int(display_order)
        hint.is_free = bool(is_free)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to update hint %s", hint_id)
        return _fail("persist_failed", "Could not save the hint.")

    return {"ok": True, "obj": hint}


def delete_hint(hint_id: int) -> dict[str, Any]:
    """Delete a hint."""
    hint = get_hint_by_id(hint_id)
    if hint is None:
        return _fail("not_found", "Hint not found.")

    try:
        db.session.delete(hint)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to delete hint %s", hint_id)
        return _fail("persist_failed", "Could not delete the hint.")

    return {"ok": True, "obj": None}


def reorder_hint(hint_id: int, direction: str) -> dict[str, Any]:
    """Move a hint up or down within its challenge by swapping positions."""
    hint = get_hint_by_id(hint_id)
    if hint is None:
        return _fail("not_found", "Hint not found.")
    if direction not in ("up", "down"):
        return _fail("bad_direction", "Direction must be 'up' or 'down'.")

    siblings = (
        ChallengeHint.query
        .filter_by(challenge_id=hint.challenge_id)
        .order_by(ChallengeHint.display_order)
        .all()
    )
    idx = next((i for i, h in enumerate(siblings) if h.id == hint.id), None)
    if idx is None:
        return _fail("not_found", "Hint not found.")

    swap_idx = idx - 1 if direction == "up" else idx + 1
    if swap_idx < 0 or swap_idx >= len(siblings):
        return {"ok": True, "obj": hint}  # already at the edge — no-op

    other = siblings[swap_idx]
    try:
        hint.display_order, other.display_order = (
            other.display_order, hint.display_order
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to reorder hint %s", hint_id)
        return _fail("persist_failed", "Could not reorder the hint.")

    return {"ok": True, "obj": hint}
