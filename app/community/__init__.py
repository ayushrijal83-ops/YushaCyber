"""Teams, Classrooms & Community Platform (YC-034.0).

Five reusable engines over the existing systems — none of them are
rewritten, only read and extended:

  · team_engine.py         — teams, membership, invites, leaderboard
  · classroom_engine.py    — classrooms, enrollment, progress board,
                             announcements
  · assignment_engine.py   — assignments resolved live against the
                             existing progress tables
  · discussion_engine.py   — threads/replies/pinned answers on every
                             lab and lesson
  · notification_engine.py — the single notification write path, plus
                             ORM listeners that turn achievement and
                             certificate inserts into notifications
"""

from app.community.routes import community_bp  # noqa: F401
from app.community.notification_engine import install_listeners

install_listeners()
