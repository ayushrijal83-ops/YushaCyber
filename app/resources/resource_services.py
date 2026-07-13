"""Cyber Resources service layer.

All library queries live here; routes and templates never touch the ORM.
Read-only: no writes, no user-generated content.
"""

from __future__ import annotations

from typing import Any, Optional

from app.extensions import db
from app.resources.models import Resource, ResourceCategory


def get_categories() -> list[ResourceCategory]:
    """All active categories in display order."""
    return (
        ResourceCategory.query
        .filter_by(is_active=True)
        .order_by(ResourceCategory.display_order)
        .all()
    )


def get_category(slug: str) -> Optional[ResourceCategory]:
    """One active category by slug, or None."""
    if not slug:
        return None
    return ResourceCategory.query.filter_by(slug=slug, is_active=True).first()


def get_resources(limit: Optional[int] = None) -> list[Resource]:
    """All active resources in (category, display) order."""
    q = (
        Resource.query
        .filter_by(is_active=True)
        .order_by(Resource.category_id, Resource.display_order)
    )
    if limit:
        q = q.limit(limit)
    return q.all()


def get_category_resources(slug: str) -> list[Resource]:
    """Active resources in a category (by slug), in display order."""
    category = get_category(slug)
    if category is None:
        return []
    return (
        Resource.query
        .filter_by(category_id=category.id, is_active=True)
        .order_by(Resource.display_order)
        .all()
    )


def get_resource(slug: str) -> Optional[Resource]:
    """One active resource by slug, or None."""
    if not slug:
        return None
    return Resource.query.filter_by(slug=slug, is_active=True).first()


def search_resources(query: str) -> list[Resource]:
    """Server-side search across title, summary and category name.

    Case-insensitive substring match. An empty query returns an empty list
    rather than the whole library.
    """
    term = (query or "").strip()
    if not term:
        return []

    like = f"%{term}%"
    return (
        Resource.query
        .join(ResourceCategory, Resource.category_id == ResourceCategory.id)
        .filter(
            Resource.is_active.is_(True),
            ResourceCategory.is_active.is_(True),
            db.or_(
                Resource.title.ilike(like),
                Resource.summary.ilike(like),
                ResourceCategory.name.ilike(like),
            ),
        )
        .order_by(Resource.category_id, Resource.display_order)
        .all()
    )


def featured_resources(limit: int = 6) -> list[Resource]:
    """Featured resources for the hub landing page."""
    return (
        Resource.query
        .filter_by(is_active=True, is_featured=True)
        .order_by(Resource.category_id, Resource.display_order)
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# Page contexts (preformatted — no ORM leaks to templates)
# ---------------------------------------------------------------------------
def _card(resource: Resource) -> dict[str, Any]:
    """A resource as a plain dict for rendering."""
    return {
        "title": resource.title,
        "slug": resource.slug,
        "summary": resource.summary,
        "difficulty": resource.difficulty,
        "read_minutes": resource.estimated_read_minutes,
        "featured": resource.is_featured,
        "category_name": resource.category.name if resource.category else "—",
        "category_slug": resource.category.slug if resource.category else "",
    }


def get_hub_context(query: str = "") -> dict[str, Any]:
    """Context for the hub landing page (with optional search)."""
    categories = [
        {
            "name": c.name, "slug": c.slug, "icon": c.icon,
            "description": c.description,
            "count": len([r for r in c.resources if r.is_active]),
        }
        for c in get_categories()
    ]

    term = (query or "").strip()
    results = [_card(r) for r in search_resources(term)] if term else []

    return {
        "categories": categories,
        "featured": [_card(r) for r in featured_resources()],
        "popular": [_card(r) for r in get_resources(limit=6)],
        "query": term,
        "results": results,
        "has_query": bool(term),
        "total": Resource.query.filter_by(is_active=True).count(),
    }


def get_category_context(slug: str) -> Optional[dict[str, Any]]:
    """Context for a category page, or None if it doesn't exist."""
    category = get_category(slug)
    if category is None:
        return None
    return {
        "category": {
            "name": category.name, "slug": category.slug,
            "description": category.description, "icon": category.icon,
        },
        "resources": [_card(r) for r in get_category_resources(slug)],
        "categories": [
            {"name": c.name, "slug": c.slug, "icon": c.icon,
             "count": len([r for r in c.resources if r.is_active]),
             "active": c.slug == slug}
            for c in get_categories()
        ],
    }


def get_resource_context(category_slug: str,
                         resource_slug: str) -> Optional[dict[str, Any]]:
    """Context for a single resource page, or None if not found."""
    category = get_category(category_slug)
    if category is None:
        return None
    resource = get_resource(resource_slug)
    if resource is None or resource.category_id != category.id:
        return None

    siblings = [
        _card(r) for r in get_category_resources(category_slug)
        if r.slug != resource_slug
    ][:4]

    return {
        "category": {"name": category.name, "slug": category.slug},
        "resource": {
            "title": resource.title,
            "slug": resource.slug,
            "summary": resource.summary,
            "content": resource.content,
            "difficulty": resource.difficulty,
            "read_minutes": resource.estimated_read_minutes,
        },
        "related": siblings,
    }
