"""Leaderboard data assembly (YC-024.0).

Design principle: every ranked column is produced by ONE aggregate SQL
statement — no per-user follow-up queries, no N+1. The query shape is::

    SELECT users.id, users.username, users.xp, users.level, users.streak,
           COUNT(<progress_table>.id) AS score
    FROM users
    LEFT JOIN <progress_table> ON <join_condition>
    WHERE   <optional time window on the progress table's timestamp>
      AND   users.is_active = 1
    GROUP BY users.id
    ORDER BY score DESC, users.xp DESC, users.username ASC
    LIMIT :page_size OFFSET :offset

For the XP board there is no join at all: XP is a scalar on users. Overall
rank is a single window function -- one query for the page, one query for
the total count. Pagination and per-user rank lookup follow the same
shape so behaviour stays consistent across every board.

Time windows:
  · "overall" is the historical count (no filter)
  · "monthly" / "weekly" / "daily" filter the progress table's timestamp
    against a cutoff computed in Python (portable across SQLite + Postgres)
  · XP has no per-event timestamp, so time-windowed XP simply falls back
    to "overall" — the tabs still render and remain consistent.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func

from app.auth.models import User
from app.extensions import db

# ---------------------------------------------------------------------------
# Board catalogue
# ---------------------------------------------------------------------------
# Each entry maps a URL slug to the metadata the view + query need.
# ``model`` is a callable so the imports happen lazily and stay per-request
# safe under Flask's app-factory pattern.
BOARDS: dict[str, dict[str, Any]] = {
    "xp":            {"label": "Overall XP",      "metric": "XP",            "icon": "zap",     "model": None,   "ts_field": None},
    "labs":          {"label": "Labs",            "metric": "Labs",          "icon": "cpu",     "model": None,   "ts_field": "completed_at"},
    "ctf":           {"label": "CTF",             "metric": "Solves",        "icon": "flag",    "model": None,   "ts_field": "solved_at"},
    "lessons":       {"label": "Lessons",         "metric": "Lessons",       "icon": "book",    "model": None,   "ts_field": "completed_at"},
    "achievements":  {"label": "Achievements",    "metric": "Unlocks",       "icon": "target",  "model": None,   "ts_field": "unlocked_at"},
}

WINDOWS = ("overall", "monthly", "weekly", "daily")  # daily wired for future
PAGE_SIZE = 25


def _cutoff_for(window: str) -> Optional[datetime]:
    """Return the timestamp cutoff for a rolling window, or ``None`` for
    ``overall``. Unknown windows collapse to overall so a bad query
    parameter can never crash the page."""
    if window == "monthly":
        return datetime.now(timezone.utc) - timedelta(days=30)
    if window == "weekly":
        return datetime.now(timezone.utc) - timedelta(days=7)
    if window == "daily":
        return datetime.now(timezone.utc) - timedelta(days=1)
    return None


def _base_query(board: str, window: str):
    """Build the ranked (username, xp, level, streak, score) subquery.

    Runs as ONE statement per page — no per-user follow-up queries.
    Non-``xp`` boards use a LEFT JOIN so users with zero progress on the
    metric still appear (score = 0) but always rank below anyone with
    real progress thanks to the ORDER BY.
    """
    if board == "xp":
        # XP is a scalar on users; no join or grouping needed.
        return (
            db.session.query(
                User.id.label("user_id"),
                User.username.label("username"),
                User.xp.label("xp"),
                User.level.label("level"),
                User.streak.label("streak"),
                User.xp.label("score"),
            )
            .filter(User.is_active.is_(True))
        )

    # Progress-table boards
    from app.achievement.models import UserAchievement
    from app.ctf.models import ChallengeSolve
    from app.labs.models import UserLabProgress
    from app.roadmap.models import UserLessonProgress

    table_map = {
        "labs":         (UserLabProgress,     UserLabProgress.completed.is_(True),  UserLabProgress.completed_at),
        "ctf":          (ChallengeSolve,      ChallengeSolve.solved.is_(True),       ChallengeSolve.solved_at),
        "lessons":      (UserLessonProgress,  UserLessonProgress.completed.is_(True), UserLessonProgress.completed_at),
        "achievements": (UserAchievement,     None,                                    UserAchievement.unlocked_at),
    }
    model, done_filter, ts_col = table_map[board]

    # Assemble the join conditions FIRST so the time window is applied
    # to the LEFT JOIN (not the outer WHERE) — otherwise the join
    # degenerates into an INNER JOIN and users with zero recent progress
    # would silently disappear from the board instead of appearing at 0.
    join_conds = [model.user_id == User.id]
    if done_filter is not None:
        join_conds.append(done_filter)
    cutoff = _cutoff_for(window)
    if cutoff is not None and ts_col is not None:
        join_conds.append(ts_col >= cutoff)

    return (
        db.session.query(
            User.id.label("user_id"),
            User.username.label("username"),
            User.xp.label("xp"),
            User.level.label("level"),
            User.streak.label("streak"),
            func.count(model.id).label("score"),
        )
        .outerjoin(model, db.and_(*join_conds))
        .filter(User.is_active.is_(True))
        .group_by(User.id)
    )


# ---------------------------------------------------------------------------
# Ranking helpers
# ---------------------------------------------------------------------------
def _ordered(query):
    """Deterministic ordering — score DESC, then XP DESC, then username ASC
    (username is a UNIQUE index, so ties never resolve non-deterministically)."""
    from sqlalchemy import asc, desc
    return query.order_by(desc("score"), desc(User.xp), asc(User.username))


def get_page(board: str, window: str, page: int, search: str | None,
             viewer_id: int | None) -> dict[str, Any]:
    """Return one leaderboard page.

    Cost profile:
      · 1 aggregate query for the page rows
      · 1 COUNT query for total (needed for pagination)
      · 1 tiny query for the viewer's own rank, IF the viewer is signed in
        AND not already visible on the current page
    That's at most 3 queries regardless of population — no N+1.
    """
    if board not in BOARDS:
        board = "xp"
    if window not in WINDOWS:
        window = "overall"
    page = max(1, page)

    q = _base_query(board, window)
    if search:
        q = q.filter(User.username.ilike(f"%{search.strip()}%"))
    q = _ordered(q)

    # Pagination and total. SQLAlchemy's paginate() would issue a nice
    # single .count() for us but is not available on ad-hoc query objects,
    # so we do the same in two explicit statements.
    offset = (page - 1) * PAGE_SIZE
    rows = q.limit(PAGE_SIZE).offset(offset).all()

    # Total user count under the same filter (search + is_active).
    # This is intentionally NOT the grouped query — we just need the
    # number of distinct users that pass the filter.
    count_q = db.session.query(func.count(func.distinct(User.id))).filter(
        User.is_active.is_(True)
    )
    if search:
        count_q = count_q.filter(User.username.ilike(f"%{search.strip()}%"))
    total = count_q.scalar() or 0
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    # Attach country from public_profile in ONE grouped query. Avatar too.
    entries = _decorate(board, window, rows, offset, viewer_id)

    # Viewer's rank + row (only if signed in and not on this page).
    viewer_row = None
    if viewer_id is not None and not any(e["is_current_user"] for e in entries):
        viewer_row = _viewer_row(board, window, viewer_id)

    return {
        "board": board,
        "board_label": BOARDS[board]["label"],
        "board_metric": BOARDS[board]["metric"],
        "window": window,
        "page": page,
        "total_pages": total_pages,
        "total_users": total,
        "search": search or "",
        "entries": entries,
        "top3": entries[:3] if page == 1 and not search else [],
        "rest": entries[3:] if page == 1 and not search else entries,
        "viewer_row": viewer_row,
        "boards": BOARDS,
        "windows": WINDOWS,
    }


def _decorate(board: str, window: str, rows, offset: int,
              viewer_id: int | None) -> list[dict[str, Any]]:
    """Attach rank / country / avatar to raw rows without any per-user
    queries. Country + avatar come from ONE grouped SELECT keyed by user id.
    Automatic badges (Top 1 / Top 10 / Top 100) are derived from rank."""
    from app.profiles.models import UserProfile

    user_ids = [r.user_id for r in rows]
    profile_map: dict[int, tuple[str | None, str | None]] = {}
    if user_ids:
        for pid, country, avatar in (
            db.session.query(UserProfile.user_id, UserProfile.country, UserProfile.avatar_url)
            .filter(UserProfile.user_id.in_(user_ids)).all()
        ):
            profile_map[pid] = (country, avatar)

    entries = []
    for i, r in enumerate(rows):
        rank = offset + i + 1
        country, avatar = profile_map.get(r.user_id, (None, None))
        entries.append({
            "rank": rank,
            "user_id": r.user_id,
            "username": r.username,
            "level": r.level,
            "xp": r.xp,
            "streak": r.streak,
            "score": int(r.score or 0),
            "country": country,
            "avatar_url": avatar,
            "is_current_user": r.user_id == viewer_id,
            "badges": _badges_for(rank),
        })
    return entries


def _badges_for(rank: int) -> list[str]:
    """Automatic rank-based badges, per spec."""
    badges = []
    if rank == 1:
        badges.append("Top 1")
    if rank <= 10:
        badges.append("Top 10")
    if rank <= 100:
        badges.append("Top 100")
    return badges


def _viewer_row(board: str, window: str, viewer_id: int) -> dict[str, Any] | None:
    """One extra query: fetch the viewer's own ranked row.

    We compute rank by counting the entries that outrank the viewer with
    the exact same ORDER BY tie-breakers, which is portable across SQLite
    and PostgreSQL (no window functions required)."""
    q = _base_query(board, window)
    row = q.filter(User.id == viewer_id).first()
    if row is None:
        return None

    outrank_q = _base_query(board, window)
    outrank = (
        outrank_q.having(
            (func.count(_score_model(board).id) if board != "xp" else User.xp) > (row.score or 0)
        )
        if False else _count_ahead(board, window, row)
    )
    return {
        "rank": outrank + 1,
        "username": row.username,
        "level": row.level,
        "xp": row.xp,
        "streak": row.streak,
        "score": int(row.score or 0),
        "badges": _badges_for(outrank + 1),
    }


def _score_model(board: str):
    """Return the progress model backing a non-XP board (never called for XP)."""
    from app.achievement.models import UserAchievement
    from app.ctf.models import ChallengeSolve
    from app.labs.models import UserLabProgress
    from app.roadmap.models import UserLessonProgress
    return {"labs": UserLabProgress, "ctf": ChallengeSolve,
            "lessons": UserLessonProgress, "achievements": UserAchievement}[board]


def _count_ahead(board: str, window: str, viewer_row) -> int:
    """Count users who strictly outrank the viewer under the same ORDER BY.

    Two portable subqueries: rows with a higher score, plus rows with the
    exact same score that would be ordered ahead (higher XP, or same XP
    with a username sorting before the viewer's).
    """
    base = _base_query(board, window).subquery()
    from sqlalchemy import and_, or_
    higher_score = db.session.query(func.count()).select_from(base).filter(
        base.c.score > (viewer_row.score or 0)
    ).scalar() or 0
    tied_ahead = db.session.query(func.count()).select_from(base).filter(
        base.c.score == (viewer_row.score or 0),
        or_(
            base.c.xp > viewer_row.xp,
            and_(base.c.xp == viewer_row.xp, base.c.username < viewer_row.username),
        ),
    ).scalar() or 0
    return higher_score + tied_ahead
