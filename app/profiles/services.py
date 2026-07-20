"""Profile data assembly (YC-023.0).

Everything here is READ-ONLY against the existing engines — small indexed
queries only. The single write path is ``get_or_create_profile`` /
``update_profile`` for the owner's own row in ``user_profiles``.
"""

from __future__ import annotations

from typing import Any, Optional

from app.auth.models import User
from app.extensions import db
from app.profiles.models import UserProfile


# ---------------------------------------------------------------------------
# Profile row helpers
# ---------------------------------------------------------------------------
def get_or_create_profile(user: User) -> UserProfile:
    """Return the user's profile row, creating an empty one on first use."""
    profile = UserProfile.query.filter_by(user_id=user.id).first()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    return profile


def update_profile(user: User, form) -> UserProfile:
    """Persist the owner's edits. Empty strings are stored as NULL."""
    profile = get_or_create_profile(user)
    for field in ("avatar_url", "bio", "country",
                  "github_url", "linkedin_url", "website_url"):
        value = (getattr(form, field).data or "").strip()
        setattr(profile, field, value or None)
    db.session.commit()
    return profile


# ---------------------------------------------------------------------------
# Statistics — one cheap COUNT per engine.
# ---------------------------------------------------------------------------
def _statistics(user: User) -> list[dict[str, Any]]:
    from app.achievement.models import UserAchievement
    from app.certificates.models import UserCertificate
    from app.ctf.models import ChallengeSolve
    from app.labs.models import UserLabProgress
    from app.roadmap.models import UserLessonProgress, UserQuizAttempt
    from app.roadmap.services import get_category_progress

    progress = get_category_progress(user)
    roadmaps_completed = sum(1 for pct in progress.values() if pct >= 100)

    quizzes_passed = (
        db.session.query(UserQuizAttempt.quiz_id)
        .filter_by(user_id=user.id, passed=True)
        .distinct().count()
    )

    return [
        {"icon": "map", "label": "Roadmaps Completed", "value": roadmaps_completed},
        {"icon": "book", "label": "Lessons Completed",
         "value": UserLessonProgress.query.filter_by(
             user_id=user.id, completed=True).count()},
        {"icon": "help", "label": "Quizzes Passed", "value": quizzes_passed},
        {"icon": "cpu", "label": "Labs Completed",
         "value": UserLabProgress.query.filter_by(
             user_id=user.id, completed=True).count()},
        {"icon": "flag", "label": "CTFs Solved",
         "value": ChallengeSolve.query.filter_by(
             user_id=user.id, solved=True).count()},
        {"icon": "target", "label": "Achievements",
         "value": UserAchievement.query.filter_by(user_id=user.id).count()},
        {"icon": "award", "label": "Certificates",
         "value": UserCertificate.query.filter_by(user_id=user.id).count()},
        {"icon": "flame", "label": "Current Streak", "value": user.streak},
    ]


# ---------------------------------------------------------------------------
# Showcase — earned achievements & certificates, newest first.
# ---------------------------------------------------------------------------
def _showcase(user: User) -> dict[str, Any]:
    from app.achievement.models import Achievement, UserAchievement
    from app.certificates.models import Certificate, UserCertificate

    achievements = (
        db.session.query(Achievement, UserAchievement.unlocked_at)
        .join(UserAchievement,
              UserAchievement.achievement_id == Achievement.id)
        .filter(UserAchievement.user_id == user.id)
        .order_by(UserAchievement.unlocked_at.desc().nullslast())
        .all()
    )
    certificates = (
        db.session.query(Certificate, UserCertificate)
        .join(UserCertificate,
              UserCertificate.certificate_id == Certificate.id)
        .filter(UserCertificate.user_id == user.id)
        .order_by(UserCertificate.issued_at.desc().nullslast())
        .all()
    )
    return {
        "achievements": [
            {"icon": a.icon or "award", "title": a.title,
             "description": a.description,
             "when": ts.strftime("%b %d, %Y") if ts else None}
            for a, ts in achievements
        ],
        "certificates": [
            {"title": c.title, "code": uc.certificate_code,
             "when": uc.issued_at.strftime("%b %d, %Y") if uc.issued_at else None}
            for c, uc in certificates
        ],
        # "Recent badges" strip = the six newest unlocks.
        "recent_badges": [
            {"icon": a.icon or "award", "title": a.title}
            for a, _ts in achievements[:6]
        ],
    }


# ---------------------------------------------------------------------------
# Activity timeline — six event sources merged newest-first.
# ---------------------------------------------------------------------------
def _timeline(user: User, limit: int = 12) -> list[dict[str, Any]]:
    from app.achievement.models import Achievement, UserAchievement
    from app.certificates.models import Certificate, UserCertificate
    from app.ctf.models import Challenge, ChallengeSolve
    from app.labs.models import Lab, UserLabProgress
    from app.roadmap.models import (
        Lesson, Quiz, UserLessonProgress, UserQuizAttempt,
    )

    per_source = 8
    events: list[tuple] = []

    rows = (
        db.session.query(UserLessonProgress.completed_at, Lesson.title)
        .join(Lesson, Lesson.id == UserLessonProgress.lesson_id)
        .filter(UserLessonProgress.user_id == user.id,
                UserLessonProgress.completed.is_(True),
                UserLessonProgress.completed_at.isnot(None))
        .order_by(UserLessonProgress.completed_at.desc())
        .limit(per_source).all()
    )
    events += [(ts, "book", "Completed lesson", t) for ts, t in rows]

    rows = (
        db.session.query(UserQuizAttempt.completed_at, Quiz.title)
        .join(Quiz, Quiz.id == UserQuizAttempt.quiz_id)
        .filter(UserQuizAttempt.user_id == user.id,
                UserQuizAttempt.passed.is_(True),
                UserQuizAttempt.completed_at.isnot(None))
        .order_by(UserQuizAttempt.completed_at.desc())
        .limit(per_source).all()
    )
    events += [(ts, "help", "Passed quiz", t) for ts, t in rows]

    rows = (
        db.session.query(UserLabProgress.completed_at, Lab.title)
        .join(Lab, Lab.id == UserLabProgress.lab_id)
        .filter(UserLabProgress.user_id == user.id,
                UserLabProgress.completed.is_(True),
                UserLabProgress.completed_at.isnot(None))
        .order_by(UserLabProgress.completed_at.desc())
        .limit(per_source).all()
    )
    events += [(ts, "cpu", "Completed lab", t) for ts, t in rows]

    rows = (
        db.session.query(ChallengeSolve.solved_at, Challenge.title)
        .join(Challenge, Challenge.id == ChallengeSolve.challenge_id)
        .filter(ChallengeSolve.user_id == user.id,
                ChallengeSolve.solved.is_(True),
                ChallengeSolve.solved_at.isnot(None))
        .order_by(ChallengeSolve.solved_at.desc())
        .limit(per_source).all()
    )
    events += [(ts, "flag", "Solved CTF challenge", t) for ts, t in rows]

    rows = (
        db.session.query(UserAchievement.unlocked_at, Achievement.title)
        .join(Achievement, Achievement.id == UserAchievement.achievement_id)
        .filter(UserAchievement.user_id == user.id,
                UserAchievement.unlocked_at.isnot(None))
        .order_by(UserAchievement.unlocked_at.desc())
        .limit(per_source).all()
    )
    events += [(ts, "target", "Earned achievement", t) for ts, t in rows]

    rows = (
        db.session.query(UserCertificate.issued_at, Certificate.title)
        .join(Certificate, Certificate.id == UserCertificate.certificate_id)
        .filter(UserCertificate.user_id == user.id,
                UserCertificate.issued_at.isnot(None))
        .order_by(UserCertificate.issued_at.desc())
        .limit(per_source).all()
    )
    events += [(ts, "award", "Earned certificate", t) for ts, t in rows]

    events.sort(key=lambda e: e[0], reverse=True)
    return [
        {"icon": icon, "action": action, "title": title,
         "when": ts.strftime("%b %d, %Y")}
        for ts, icon, action, title in events[:limit]
    ]


# ---------------------------------------------------------------------------
# Page context
# ---------------------------------------------------------------------------
def get_profile_page_context(profile_user: User,
                             viewer: Optional[User]) -> dict[str, Any]:
    """Everything the profile template needs for ``profile_user``.

    ``viewer`` decides ownership (Edit button) — nothing else differs
    between the public and owner views, keeping the page truly read-only.
    """
    from app.dashboard.services import get_xp_info

    profile = UserProfile.query.filter_by(user_id=profile_user.id).first()
    is_owner = viewer is not None and viewer.id == profile_user.id

    return {
        "profile_user": profile_user,
        "profile": profile,
        "is_owner": is_owner,
        "xp_info": get_xp_info(profile_user),
        "joined": (profile_user.created_at.strftime("%B %Y")
                   if profile_user.created_at else "—"),
        "statistics": _statistics(profile_user),
        "showcase": _showcase(profile_user),
        "timeline": _timeline(profile_user),
    }
