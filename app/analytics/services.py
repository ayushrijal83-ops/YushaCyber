"""Learning-analytics services (YC-033.0).

Every number the dashboard shows is computed HERE, with aggregate SQL
(counts, sums, group-bys) — never in templates, never per-row in
Python where the database can do it. Date bucketing for the 30-day
charts happens in Python over pre-filtered rows, bounded by the window.

Nothing in this module writes to existing systems; the only write path
is `record_event` into the analytics-owned event table.

XP history is not stored by the platform, so the XP-growth series is a
*reconstruction*: each completion/solve/unlock is re-priced with its
reward at query time and bucketed by its completion date. It tracks
real awards closely (same sources the XP engine pays) and is labelled
as reconstructed in the UI.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_

from app.achievement.models import Achievement, UserAchievement
from app.analytics.models import AnalyticsEvent
from app.auth.models import User
from app.certificates.models import Certificate, UserCertificate
from app.ctf.models import Challenge, ChallengeSolve
from app.extensions import db
from app.labs.models import (
    Lab,
    LabObjective,
    UserLabProgress,
    UserLabSession,
    UserObjectiveProgress,
)
from app.roadmap.models import (
    Lesson,
    Quiz,
    RoadmapCategory,
    RoadmapModule,
    UserLessonProgress,
    UserModuleProgress,
    UserQuizAttempt,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _day(value: datetime | None) -> str | None:
    """ISO date for a (possibly naive) datetime; None-safe."""
    if value is None:
        return None
    return value.date().isoformat()


def _window(days: int) -> tuple[datetime, list[str]]:
    """(cutoff datetime, ordered ISO labels for the last `days` days)."""
    today = _utcnow().date()
    labels = [(today - timedelta(days=i)).isoformat()
              for i in range(days - 1, -1, -1)]
    cutoff = datetime.combine(today - timedelta(days=days - 1),
                              datetime.min.time(), tzinfo=timezone.utc)
    return cutoff, labels


def _students():
    return User.query.filter_by(is_admin=False)


# ===========================================================================
# Overview
# ===========================================================================
def overview_stats() -> dict[str, Any]:
    """The eight headline cards. A fixed, small number of aggregate
    queries — independent of how many students exist."""
    total_students = _students().count()
    averages = db.session.query(
        func.avg(User.xp), func.avg(User.level)).filter(
        User.is_admin.is_(False)).one()

    return {
        "total_students": total_students,
        "active_students_7d": len(active_user_ids(days=7)),
        "completed_lessons": UserLessonProgress.query.filter_by(
            completed=True).count(),
        "completed_labs": UserLabProgress.query.filter_by(
            completed=True).count(),
        "completed_ctfs": ChallengeSolve.query.filter_by(
            solved=True).count(),
        "certificates_issued": UserCertificate.query.count(),
        "avg_xp": round(float(averages[0] or 0)),
        "avg_level": round(float(averages[1] or 0), 1),
    }


def active_user_ids(days: int = 7) -> set[int]:
    """Users with ANY learning activity inside the window — derived
    from the progress tables (the platform stores no last-login)."""
    cutoff = _utcnow() - timedelta(days=days)
    sources = [
        db.session.query(UserLabSession.user_id).filter(
            UserLabSession.last_activity_at >= cutoff),
        db.session.query(UserLabProgress.user_id).filter(
            UserLabProgress.updated_at >= cutoff),
        db.session.query(UserObjectiveProgress.user_id).filter(
            UserObjectiveProgress.completed_at >= cutoff),
        db.session.query(UserLessonProgress.user_id).filter(
            UserLessonProgress.updated_at >= cutoff),
        db.session.query(UserQuizAttempt.user_id).filter(
            UserQuizAttempt.completed_at >= cutoff),
        db.session.query(ChallengeSolve.user_id).filter(
            ChallengeSolve.updated_at >= cutoff),
        db.session.query(UserAchievement.user_id).filter(
            UserAchievement.unlocked_at >= cutoff),
        db.session.query(AnalyticsEvent.user_id).filter(
            AnalyticsEvent.created_at >= cutoff),
    ]
    ids: set[int] = set()
    for query in sources:
        ids.update(row[0] for row in query.distinct().all())
    return ids


# ===========================================================================
# Time series — the six charts
# ===========================================================================
def _bucket(rows, labels) -> list[int]:
    counts: dict[str, int] = defaultdict(int)
    for stamp in rows:
        day = _day(stamp)
        if day:
            counts[day] += 1
    return [counts.get(label, 0) for label in labels]


def timeseries(days: int = 30) -> dict[str, Any]:
    """All chart series for the last `days` days, one payload."""
    cutoff, labels = _window(days)

    # Daily active users: distinct (day, user) across activity sources.
    active: dict[str, set[int]] = defaultdict(set)
    activity_sources = [
        db.session.query(UserLabSession.last_activity_at,
                         UserLabSession.user_id).filter(
            UserLabSession.last_activity_at >= cutoff),
        db.session.query(UserLessonProgress.updated_at,
                         UserLessonProgress.user_id).filter(
            UserLessonProgress.updated_at >= cutoff),
        db.session.query(UserQuizAttempt.completed_at,
                         UserQuizAttempt.user_id).filter(
            UserQuizAttempt.completed_at >= cutoff),
        db.session.query(ChallengeSolve.updated_at,
                         ChallengeSolve.user_id).filter(
            ChallengeSolve.updated_at >= cutoff),
        db.session.query(UserObjectiveProgress.completed_at,
                         UserObjectiveProgress.user_id).filter(
            UserObjectiveProgress.completed_at >= cutoff),
        db.session.query(AnalyticsEvent.created_at,
                         AnalyticsEvent.user_id).filter(
            AnalyticsEvent.created_at >= cutoff),
    ]
    for query in activity_sources:
        for stamp, user_id in query.all():
            day = _day(stamp)
            if day:
                active[day].add(user_id)
    daily_active = [len(active.get(label, ())) for label in labels]

    # Completions.
    lesson_days = [r[0] for r in db.session.query(
        UserLessonProgress.completed_at).filter(
        UserLessonProgress.completed.is_(True),
        UserLessonProgress.completed_at >= cutoff).all()]
    lab_days = [r[0] for r in db.session.query(
        UserLabProgress.completed_at).filter(
        UserLabProgress.completed.is_(True),
        UserLabProgress.completed_at >= cutoff).all()]
    ctf_days = [r[0] for r in db.session.query(
        ChallengeSolve.solved_at).filter(
        ChallengeSolve.solved.is_(True),
        ChallengeSolve.solved_at >= cutoff).all()]

    # Quiz attempts and pass rate.
    attempts: dict[str, int] = defaultdict(int)
    passes: dict[str, int] = defaultdict(int)
    for stamp, passed in db.session.query(
            UserQuizAttempt.completed_at, UserQuizAttempt.passed).filter(
            UserQuizAttempt.completed_at >= cutoff).all():
        day = _day(stamp)
        if day:
            attempts[day] += 1
            if passed:
                passes[day] += 1
    quiz_attempts = [attempts.get(label, 0) for label in labels]
    quiz_pass_rate = [
        round(100 * passes.get(label, 0) / attempts[label])
        if attempts.get(label) else None
        for label in labels]

    # XP growth (reconstructed) — cumulative across the window.
    xp_daily: dict[str, int] = defaultdict(int)
    for stamp, xp in _xp_events(cutoff):
        day = _day(stamp)
        if day:
            xp_daily[day] += xp
    xp_series = []
    running = 0
    for label in labels:
        running += xp_daily.get(label, 0)
        xp_series.append(running)

    return {
        "labels": labels,
        "daily_active": daily_active,
        "xp_growth": xp_series,
        "lessons": _bucket(lesson_days, labels),
        "labs": _bucket(lab_days, labels),
        "ctf": _bucket(ctf_days, labels),
        "quiz_attempts": quiz_attempts,
        "quiz_pass_rate": quiz_pass_rate,
    }


def _after(stamp: datetime | None, cutoff: datetime) -> bool:
    """None-safe, naive/aware-safe 'stamp >= cutoff'."""
    if stamp is None:
        return False
    if stamp.tzinfo is None:
        return stamp >= cutoff.replace(tzinfo=None)
    return stamp >= cutoff


def _xp_events(cutoff: datetime,
               user_id: int | None = None) -> list[tuple[datetime, int]]:
    """(timestamp, xp) pairs reconstructed from every reward source the
    XP engine pays: lessons, module bonuses, first-passed quizzes,
    labs, objectives, CTF solves, achievement bonuses."""
    def _maybe_user(query, column):
        return query.filter(column == user_id) if user_id else query

    events: list[tuple[datetime, int]] = []

    rows = _maybe_user(
        db.session.query(UserLessonProgress.completed_at, Lesson.xp_reward)
        .join(Lesson, Lesson.id == UserLessonProgress.lesson_id)
        .filter(UserLessonProgress.completed.is_(True),
                UserLessonProgress.completed_at >= cutoff),
        UserLessonProgress.user_id).all()
    events.extend((stamp, xp or 0) for stamp, xp in rows)

    rows = _maybe_user(
        db.session.query(UserModuleProgress.completed_at,
                         RoadmapModule.xp_reward)
        .join(RoadmapModule,
              RoadmapModule.id == UserModuleProgress.module_id)
        .filter(UserModuleProgress.bonus_awarded.is_(True),
                UserModuleProgress.completed_at >= cutoff),
        UserModuleProgress.user_id).all()
    events.extend((stamp, xp or 0) for stamp, xp in rows)

    # Quizzes: only the FIRST passed attempt per (user, quiz) pays XP.
    first_pass = db.session.query(
        UserQuizAttempt.user_id, UserQuizAttempt.quiz_id,
        func.min(UserQuizAttempt.completed_at).label("first_at")) \
        .filter(UserQuizAttempt.passed.is_(True)) \
        .group_by(UserQuizAttempt.user_id, UserQuizAttempt.quiz_id)
    if user_id:
        first_pass = first_pass.filter(UserQuizAttempt.user_id == user_id)
    quiz_xp = {q.id: q.xp_reward or 0 for q in
               db.session.query(Quiz.id, Quiz.xp_reward).all()}
    for _uid, quiz_id, first_at in first_pass.all():
        if _after(first_at, cutoff):
            events.append((first_at, quiz_xp.get(quiz_id, 0)))

    rows = _maybe_user(
        db.session.query(UserLabProgress.completed_at, Lab.xp_reward)
        .join(Lab, Lab.id == UserLabProgress.lab_id)
        .filter(UserLabProgress.completed.is_(True),
                UserLabProgress.completed_at >= cutoff),
        UserLabProgress.user_id).all()
    events.extend((stamp, xp or 0) for stamp, xp in rows)

    rows = _maybe_user(
        db.session.query(UserObjectiveProgress.completed_at,
                         LabObjective.xp_reward)
        .join(LabObjective,
              LabObjective.id == UserObjectiveProgress.objective_id)
        .filter(UserObjectiveProgress.completed.is_(True),
                UserObjectiveProgress.completed_at >= cutoff),
        UserObjectiveProgress.user_id).all()
    events.extend((stamp, xp or 0) for stamp, xp in rows)

    rows = _maybe_user(
        db.session.query(ChallengeSolve.solved_at, Challenge.xp_reward)
        .join(Challenge, Challenge.id == ChallengeSolve.challenge_id)
        .filter(ChallengeSolve.solved.is_(True),
                ChallengeSolve.solved_at >= cutoff),
        ChallengeSolve.user_id).all()
    events.extend((stamp, xp or 0) for stamp, xp in rows)

    rows = _maybe_user(
        db.session.query(UserAchievement.unlocked_at, Achievement.bonus_xp)
        .join(Achievement,
              Achievement.id == UserAchievement.achievement_id)
        .filter(UserAchievement.unlocked_at >= cutoff),
        UserAchievement.user_id).all()
    events.extend((stamp, xp or 0) for stamp, xp in rows)

    return [(stamp, xp) for stamp, xp in events if stamp is not None]


# ===========================================================================
# Student search + per-student analytics
# ===========================================================================
def search_students(q: str = "", level: int | None = None,
                    min_xp: int | None = None,
                    sort: str = "xp") -> list[User]:
    query = _students()
    q = (q or "").strip()
    if q:
        like = f"%{q}%"
        query = query.filter(or_(User.username.ilike(like),
                                 User.email.ilike(like)))
    if level is not None:
        query = query.filter(User.level == level)
    if min_xp is not None:
        query = query.filter(User.xp >= min_xp)
    order = {"xp": User.xp.desc(), "level": User.level.desc(),
             "username": User.username.asc(),
             "newest": User.created_at.desc()}.get(sort, User.xp.desc())
    return query.order_by(order).limit(200).all()


def student_analytics(user: User) -> dict[str, Any]:
    """Everything the per-student page shows, precomputed."""
    lessons_total = Lesson.query.count()
    labs_total = Lab.query.filter_by(is_active=True).count()
    ctf_total = Challenge.query.filter_by(is_active=True).count()

    lessons_done = UserLessonProgress.query.filter_by(
        user_id=user.id, completed=True).count()
    labs_done = UserLabProgress.query.filter_by(
        user_id=user.id, completed=True).count()
    ctf_done = ChallengeSolve.query.filter_by(
        user_id=user.id, solved=True).count()

    def _pct(done, total):
        return round(100 * done / total) if total else 0

    quiz_stats = db.session.query(
        func.avg(UserQuizAttempt.percentage),
        func.count(UserQuizAttempt.id)).filter(
        UserQuizAttempt.user_id == user.id).one()

    time_spent = (
        (db.session.query(func.sum(UserLessonProgress.time_spent))
         .filter_by(user_id=user.id).scalar() or 0)
        + (db.session.query(func.sum(UserLabProgress.time_spent_seconds))
           .filter_by(user_id=user.id).scalar() or 0)
        + (db.session.query(func.sum(UserQuizAttempt.time_taken_seconds))
           .filter_by(user_id=user.id).scalar() or 0)
        + (db.session.query(func.sum(ChallengeSolve.time_taken_seconds))
           .filter_by(user_id=user.id).scalar() or 0)
    )

    # Personal XP trend, last 30 days (cumulative reconstruction).
    cutoff, labels = _window(30)
    xp_daily: dict[str, int] = defaultdict(int)
    for stamp, xp in _xp_events(cutoff, user_id=user.id):
        day = _day(stamp)
        if day:
            xp_daily[day] += xp
    running, xp_trend = 0, []
    for label in labels:
        running += xp_daily.get(label, 0)
        xp_trend.append(running)

    certificates = (db.session.query(UserCertificate, Certificate)
                    .join(Certificate)
                    .filter(UserCertificate.user_id == user.id)
                    .order_by(UserCertificate.issued_at.desc()).all())
    achievements = (db.session.query(UserAchievement, Achievement)
                    .join(Achievement)
                    .filter(UserAchievement.user_id == user.id)
                    .order_by(UserAchievement.unlocked_at.desc()).all())

    return {
        "streak": user.streak or 0,
        "xp_labels": labels,
        "xp_trend": xp_trend,
        "completion": {
            "lessons": {"done": lessons_done, "total": lessons_total,
                        "pct": _pct(lessons_done, lessons_total)},
            "labs": {"done": labs_done, "total": labs_total,
                     "pct": _pct(labs_done, labs_total)},
            "ctf": {"done": ctf_done, "total": ctf_total,
                    "pct": _pct(ctf_done, ctf_total)},
        },
        "avg_quiz_score": round(float(quiz_stats[0] or 0), 1),
        "quiz_attempts": int(quiz_stats[1] or 0),
        "time_spent_seconds": int(time_spent),
        "certificates": certificates,
        "achievements": achievements,
        "recent_activity": recent_activity(user.id, limit=15),
    }


def recent_activity(user_id: int, limit: int = 15) -> list[dict[str, Any]]:
    """The student's latest learning events, merged across systems."""
    items: list[dict[str, Any]] = []

    for progress, lesson in (
            db.session.query(UserLessonProgress, Lesson).join(Lesson)
            .filter(UserLessonProgress.user_id == user_id,
                    UserLessonProgress.completed.is_(True))
            .order_by(UserLessonProgress.completed_at.desc())
            .limit(limit).all()):
        items.append({"when": progress.completed_at, "kind": "lesson",
                      "label": f"Completed lesson “{lesson.title}”"})

    for progress, lab in (
            db.session.query(UserLabProgress, Lab).join(Lab)
            .filter(UserLabProgress.user_id == user_id,
                    UserLabProgress.completed.is_(True))
            .order_by(UserLabProgress.completed_at.desc())
            .limit(limit).all()):
        items.append({"when": progress.completed_at, "kind": "lab",
                      "label": f"Completed lab “{lab.title}”"})

    for solve, challenge in (
            db.session.query(ChallengeSolve, Challenge).join(Challenge)
            .filter(ChallengeSolve.user_id == user_id,
                    ChallengeSolve.solved.is_(True))
            .order_by(ChallengeSolve.solved_at.desc())
            .limit(limit).all()):
        items.append({"when": solve.solved_at, "kind": "ctf",
                      "label": f"Solved challenge “{challenge.title}”"})

    for attempt, quiz in (
            db.session.query(UserQuizAttempt, Quiz).join(Quiz)
            .filter(UserQuizAttempt.user_id == user_id)
            .order_by(UserQuizAttempt.completed_at.desc())
            .limit(limit).all()):
        verdict = "passed" if attempt.passed else "attempted"
        items.append({"when": attempt.completed_at, "kind": "quiz",
                      "label": f"{verdict.capitalize()} quiz "
                               f"“{quiz.title}” "
                               f"({round(attempt.percentage or 0)}%)"})

    for unlock, achievement in (
            db.session.query(UserAchievement, Achievement)
            .join(Achievement)
            .filter(UserAchievement.user_id == user_id)
            .order_by(UserAchievement.unlocked_at.desc())
            .limit(limit).all()):
        items.append({"when": unlock.unlocked_at, "kind": "achievement",
                      "label": f"Unlocked “{achievement.title}”"})

    for issued, certificate in (
            db.session.query(UserCertificate, Certificate)
            .join(Certificate)
            .filter(UserCertificate.user_id == user_id)
            .order_by(UserCertificate.issued_at.desc())
            .limit(limit).all()):
        items.append({"when": issued.issued_at, "kind": "certificate",
                      "label": f"Earned certificate “{certificate.title}”"})

    def _key(item):
        when = item["when"]
        if when is None:
            return datetime.min
        return when.replace(tzinfo=None) if when.tzinfo else when

    items.sort(key=_key, reverse=True)
    return items[:limit]


# ===========================================================================
# Roadmap / Lab / CTF analytics
# ===========================================================================
def roadmap_analytics() -> dict[str, Any]:
    """Per-roadmap completion rates, average times, and the drop-off
    funnel per category (module → module attrition)."""
    categories = (RoadmapCategory.query
                  .order_by(RoadmapCategory.display_order).all())
    lessons_per_category = dict(
        db.session.query(RoadmapModule.category_id, func.count(Lesson.id))
        .join(Lesson, Lesson.module_id == RoadmapModule.id)
        .group_by(RoadmapModule.category_id).all())
    # completed lesson-progress rows per category
    completed_per_category = dict(
        db.session.query(RoadmapModule.category_id,
                         func.count(UserLessonProgress.id))
        .join(Lesson, Lesson.module_id == RoadmapModule.id)
        .join(UserLessonProgress,
              UserLessonProgress.lesson_id == Lesson.id)
        .filter(UserLessonProgress.completed.is_(True))
        .group_by(RoadmapModule.category_id).all())
    enrolled_per_category = dict(
        db.session.query(RoadmapModule.category_id,
                         func.count(func.distinct(
                             UserLessonProgress.user_id)))
        .join(Lesson, Lesson.module_id == RoadmapModule.id)
        .join(UserLessonProgress,
              UserLessonProgress.lesson_id == Lesson.id)
        .group_by(RoadmapModule.category_id).all())
    avg_time_per_category = dict(
        db.session.query(RoadmapModule.category_id,
                         func.avg(UserLessonProgress.time_spent))
        .join(Lesson, Lesson.module_id == RoadmapModule.id)
        .join(UserLessonProgress,
              UserLessonProgress.lesson_id == Lesson.id)
        .filter(UserLessonProgress.completed.is_(True))
        .group_by(RoadmapModule.category_id).all())
    module_completers = dict(
        db.session.query(UserModuleProgress.module_id,
                         func.count(func.distinct(
                             UserModuleProgress.user_id)))
        .filter(UserModuleProgress.completed.is_(True))
        .group_by(UserModuleProgress.module_id).all())

    rows = []
    for category in categories:
        lessons_total = lessons_per_category.get(category.id, 0)
        enrolled = enrolled_per_category.get(category.id, 0)
        completed = completed_per_category.get(category.id, 0)
        possible = lessons_total * enrolled
        rate = round(100 * completed / possible) if possible else 0

        funnel = []
        previous = None
        drop_off = None
        for module in sorted(category.modules,
                             key=lambda m: m.display_order):
            completers = module_completers.get(module.id, 0)
            step = {"module": module.title, "completers": completers}
            if previous is not None and previous["completers"] > 0:
                lost = previous["completers"] - completers
                step["lost"] = max(lost, 0)
                if drop_off is None or step["lost"] > drop_off["lost"]:
                    drop_off = {"after": previous["module"],
                                "before": module.title,
                                "lost": step["lost"]}
            funnel.append(step)
            previous = step

        rows.append({
            "category": category.title,
            "lessons": lessons_total,
            "enrolled": enrolled,
            "completion_rate": rate,
            "avg_lesson_seconds": round(
                float(avg_time_per_category.get(category.id) or 0)),
            "funnel": funnel,
            "drop_off": drop_off if drop_off and drop_off["lost"] > 0
            else None,
        })

    ranked = [r for r in rows if r["enrolled"] > 0]
    ranked.sort(key=lambda r: r["completion_rate"], reverse=True)
    return {
        "rows": rows,
        "most_completed": ranked[0] if ranked else None,
        "least_completed": ranked[-1] if len(ranked) > 1
        else (ranked[0] if ranked else None),
    }


def lab_analytics() -> dict[str, Any]:
    """Attempt/completion/failure/time/hint metrics per lab."""
    started = dict(
        db.session.query(UserLabProgress.lab_id,
                         func.count(UserLabProgress.id))
        .filter(UserLabProgress.started.is_(True))
        .group_by(UserLabProgress.lab_id).all())
    completed = dict(
        db.session.query(UserLabProgress.lab_id,
                         func.count(UserLabProgress.id))
        .filter(UserLabProgress.completed.is_(True))
        .group_by(UserLabProgress.lab_id).all())
    tracked_time = dict(
        db.session.query(UserLabProgress.lab_id,
                         func.avg(UserLabProgress.time_spent_seconds))
        .filter(UserLabProgress.completed.is_(True),
                UserLabProgress.time_spent_seconds > 0)
        .group_by(UserLabProgress.lab_id).all())

    # Hint usage: analytics events joined to objectives -> labs.
    hints = dict(
        db.session.query(LabObjective.lab_id,
                         func.count(AnalyticsEvent.id))
        .join(AnalyticsEvent,
              (AnalyticsEvent.subject_id == LabObjective.id)
              & (AnalyticsEvent.subject_type == "objective")
              & (AnalyticsEvent.event_type == "hint_used"))
        .group_by(LabObjective.lab_id).all())

    rows = []
    for lab in Lab.query.filter_by(is_active=True).all():
        attempts = started.get(lab.id, 0)
        done = completed.get(lab.id, 0)
        failure = round(100 * (attempts - done) / attempts) \
            if attempts else 0
        rows.append({
            "lab": lab.title, "slug": lab.slug,
            "difficulty": lab.difficulty,
            "attempts": attempts, "completed": done,
            "failure_rate": failure,
            "avg_seconds": round(float(tracked_time.get(lab.id) or 0)),
            "hints_used": hints.get(lab.id, 0),
        })

    attempted = [r for r in rows if r["attempts"] > 0]
    return {
        "rows": sorted(rows, key=lambda r: r["attempts"], reverse=True),
        "most_attempted": max(attempted, key=lambda r: r["attempts"])
        if attempted else None,
        "highest_failure": max(attempted, key=lambda r: r["failure_rate"])
        if attempted else None,
        "total_hints_used": sum(r["hints_used"] for r in rows),
    }


def ctf_analytics() -> dict[str, Any]:
    """Solve counts, attempt averages, difficulty distribution."""
    solves = dict(
        db.session.query(ChallengeSolve.challenge_id,
                         func.count(ChallengeSolve.id))
        .filter(ChallengeSolve.solved.is_(True))
        .group_by(ChallengeSolve.challenge_id).all())
    avg_attempts = dict(
        db.session.query(ChallengeSolve.challenge_id,
                         func.avg(ChallengeSolve.attempts))
        .group_by(ChallengeSolve.challenge_id).all())

    rows = []
    for challenge in Challenge.query.filter_by(is_active=True).all():
        rows.append({
            "challenge": challenge.title,
            "difficulty": challenge.difficulty,
            "solves": solves.get(challenge.id, 0),
            "avg_attempts": round(
                float(avg_attempts.get(challenge.id) or 0), 1),
        })

    difficulty: dict[str, dict[str, int]] = defaultdict(
        lambda: {"challenges": 0, "solves": 0})
    for row in rows:
        bucket = difficulty[row["difficulty"] or "unrated"]
        bucket["challenges"] += 1
        bucket["solves"] += row["solves"]

    attempted = [r for r in rows]
    overall_attempts = db.session.query(
        func.avg(ChallengeSolve.attempts)).scalar()
    return {
        "rows": sorted(rows, key=lambda r: r["solves"], reverse=True),
        "most_solved": max(attempted, key=lambda r: r["solves"])
        if attempted else None,
        "least_solved": min(attempted, key=lambda r: r["solves"])
        if attempted else None,
        "avg_attempts": round(float(overall_attempts or 0), 1),
        "difficulty_distribution": dict(difficulty),
    }


# ===========================================================================
# Event recording (the only write path)
# ===========================================================================
def record_event(user_id: int, event_type: str, subject_type: str = "",
                 subject_id: int | None = None,
                 meta: dict | None = None) -> AnalyticsEvent:
    event = AnalyticsEvent(user_id=user_id, event_type=event_type,
                           subject_type=subject_type or "",
                           subject_id=subject_id)
    event.set_meta(meta or {})
    db.session.add(event)
    db.session.commit()
    return event
