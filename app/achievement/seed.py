"""Achievement seed.

Inserts the initial achievement definitions using SQLAlchemy models only.
Idempotent: if any achievement already exists the seeder does nothing, so
re-running never duplicates.

Run via the Flask CLI (registered in the app factory):

    flask --app app seed-achievements
"""

from __future__ import annotations

from app.achievement.models import Achievement
from app.extensions import db

# (title, description, icon, category, condition_type, condition_value, bonus_xp)
ACHIEVEMENTS: list[tuple] = [
    ("First Lesson", "Complete your first lesson.", "book",
     "lessons", "lessons_completed", 1, 25),
    ("Lesson Master", "Complete 10 lessons.", "layers",
     "lessons", "lessons_completed", 10, 100),
    ("Quiz Beginner", "Pass your first quiz.", "help",
     "quizzes", "quizzes_passed", 1, 25),
    ("Quiz Master", "Pass 10 quizzes.", "award",
     "quizzes", "quizzes_passed", 10, 150),
    ("Level 5", "Reach Level 5.", "zap",
     "progression", "level_reached", 5, 100),
    ("1000 XP", "Earn 1000 XP.", "zap",
     "progression", "xp_earned", 1000, 100),
    ("Perfect Score", "Score 100% on a quiz.", "target",
     "quizzes", "perfect_quiz", 1, 50),
    ("Roadmap Explorer", "Complete your first module.", "map",
     "progression", "modules_completed", 1, 75),
]


def seed_achievements() -> dict[str, int]:
    """Insert achievement definitions if none exist. Returns a summary.

    Idempotent: if any achievement already exists the function makes no
    changes and reports the existing count.
    """
    if Achievement.query.first() is not None:
        return {"created": 0, "achievements": Achievement.query.count()}

    for order, (title, desc, icon, category, ctype, cvalue, xp) in enumerate(
        ACHIEVEMENTS, start=1
    ):
        db.session.add(Achievement(
            title=title,
            description=desc,
            icon=icon,
            category=category,
            condition_type=ctype,
            condition_value=cvalue,
            bonus_xp=xp,
            is_active=True,
            display_order=order,
        ))

    db.session.commit()
    return {"created": 1, "achievements": len(ACHIEVEMENTS)}
