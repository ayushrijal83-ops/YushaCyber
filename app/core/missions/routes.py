"""Interactive Missions UI — discovery + detail pages (YC-034.3).

Thin presentation layer over the existing mission engine
(app.core.missions.mission_services) and terminal (app.core.terminal).
No new mission mechanics, validation, or XP logic live here — starting
a mission still hands off to the existing /terminal/mission/<slug> page.
"""

from __future__ import annotations

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from app.core.missions.mission_loader import get_mission
from app.core.missions.mission_services import (
    dashboard_stats,
    list_missions_with_status,
)

missions_ui_bp = Blueprint("missions_ui", __name__)


@missions_ui_bp.route("/interactive-labs")
@login_required
def discover():
    """Mission discovery — cards for every mission plus header stats."""
    missions = list_missions_with_status(current_user.id)
    stats = dashboard_stats(current_user.id)
    return render_template("missions/discover.html",
                           missions=missions, stats=stats, user=current_user)


@missions_ui_bp.route("/interactive-labs/<slug>")
@login_required
def detail(slug: str):
    """Mission detail — objectives, what you'll learn, Start/Continue/Review."""
    mission = get_mission(slug)
    if mission is None:
        abort(404)
    missions = list_missions_with_status(current_user.id)
    card = next((m for m in missions if m["id"] == slug), None)
    return render_template("missions/detail.html",
                           mission=mission, card=card, user=current_user)
