"""Leaderboard routes (YC-024.0)."""

from __future__ import annotations

from flask import render_template, request
from flask_login import current_user

from app.leaderboard import leaderboard_bp, services


@leaderboard_bp.route("/leaderboard")
def index():
    """Public global leaderboard. Anonymous viewers see the board with
    no 'you' highlight; signed-in viewers get their rank card below the
    table if they aren't visible on the current page."""
    board = request.args.get("board", "xp")
    window = request.args.get("window", "overall")
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip() or None

    viewer_id = current_user.id if current_user.is_authenticated else None
    context = services.get_page(board, window, page, search, viewer_id)
    return render_template("leaderboard/index.html", **context)
