"""Quiz service layer.

The single place quiz data is read and written. Routes and templates go
through these functions and never touch the ORM directly. Pure
data/logic: no XP awards, no module unlocking, no completion side
effects (those are later tickets).

Naming and shapes follow YC-007.2:
    get_module_quiz / get_quiz / get_quiz_questions / get_question
    get_user_attempts / get_latest_attempt / get_best_attempt
    has_passed_quiz / can_take_quiz
    calculate_score / submit_quiz
    get_quiz_statistics / get_quiz_context
"""

from __future__ import annotations

from typing import Any, Optional

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.auth.models import User
from app.extensions import db
from app.roadmap.models import (
    Quiz,
    QuizQuestion,
    RoadmapModule,
    UserQuizAttempt,
)
from app.roadmap.services import (
    _utcnow,
    get_lessons,
    get_module,
    lesson_completed,
)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
def get_module_quiz(module_slug: str) -> Optional[Quiz]:
    """The active quiz for a module (by slug), or None.

    A module owns at most one quiz; if several exist (data anomaly), the
    lowest-id active quiz is returned deterministically.
    """
    module = get_module(module_slug)
    if module is None:
        return None
    return (
        Quiz.query
        .filter_by(module_id=module.id, is_active=True)
        .order_by(Quiz.id)
        .first()
    )


def get_quiz(quiz_id: int) -> Optional[Quiz]:
    """One active quiz by id, or None."""
    return Quiz.query.filter_by(id=quiz_id, is_active=True).first()


def get_quiz_questions(quiz: Quiz) -> list[QuizQuestion]:
    """A quiz's questions in display order.

    Each question's ``options`` relationship is already ordered by
    display_order at the model level, so callers get ordered options for
    free. Returns an empty list for a missing quiz rather than raising.
    """
    if quiz is None:
        return []
    return (
        QuizQuestion.query
        .filter_by(quiz_id=quiz.id)
        .order_by(QuizQuestion.display_order)
        .all()
    )


def get_question(question_id: int) -> Optional[QuizQuestion]:
    """One question by id, or None."""
    return QuizQuestion.query.filter_by(id=question_id).first()


# ---------------------------------------------------------------------------
# Attempt history
# ---------------------------------------------------------------------------
def get_user_attempts(user: User, quiz: Quiz) -> list[UserQuizAttempt]:
    """All of a user's attempts at a quiz, newest first."""
    if user is None or quiz is None:
        return []
    return (
        UserQuizAttempt.query
        .filter_by(user_id=user.id, quiz_id=quiz.id)
        .order_by(UserQuizAttempt.created_at.desc())
        .all()
    )


def get_latest_attempt(user: User, quiz: Quiz) -> Optional[UserQuizAttempt]:
    """The user's most recent attempt, or None."""
    if user is None or quiz is None:
        return None
    return (
        UserQuizAttempt.query
        .filter_by(user_id=user.id, quiz_id=quiz.id)
        .order_by(UserQuizAttempt.created_at.desc())
        .first()
    )


def get_best_attempt(user: User, quiz: Quiz) -> Optional[UserQuizAttempt]:
    """The user's highest-percentage attempt (ties broken by most recent)."""
    if user is None or quiz is None:
        return None
    return (
        UserQuizAttempt.query
        .filter_by(user_id=user.id, quiz_id=quiz.id)
        .order_by(
            UserQuizAttempt.percentage.desc(),
            UserQuizAttempt.created_at.desc(),
        )
        .first()
    )


# ---------------------------------------------------------------------------
# Progress checks
# ---------------------------------------------------------------------------
def has_passed_quiz(user: User, quiz: Quiz) -> bool:
    """Whether the user has any passing attempt at this quiz."""
    if user is None or quiz is None:
        return False
    return (
        UserQuizAttempt.query
        .filter_by(user_id=user.id, quiz_id=quiz.id, passed=True)
        .first()
        is not None
    )


def can_take_quiz(user: User, module_slug: str) -> bool:
    """Whether a user may take a module's quiz.

    Rule (YC-007.2): the user must have completed EVERY lesson in the
    module first, and the module must have an active quiz with at least
    one question. Uses the existing lesson-completion system.
    """
    if user is None:
        return False
    module = get_module(module_slug)
    if module is None:
        return False
    quiz = get_module_quiz(module_slug)
    if quiz is None or not get_quiz_questions(quiz):
        return False

    lessons = get_lessons(module.id)
    if not lessons:
        return False
    return all(lesson_completed(user, lesson) for lesson in lessons)


# ---------------------------------------------------------------------------
# Scoring + submission
# ---------------------------------------------------------------------------
def calculate_score(quiz: Quiz, submitted_answers: dict) -> dict[str, Any]:
    """Grade answers against a quiz.

    ``submitted_answers`` maps question_id -> option_id (keys/values may
    be strings or ints; they are coerced, malformed entries skipped). A
    question counts correct only when the chosen option is its correct
    option. Returns {correct, total, percentage, passed} where passed is
    measured against ``quiz.pass_percentage``.
    """
    questions = get_quiz_questions(quiz)
    total = len(questions)
    if total == 0:
        return {"correct": 0, "total": 0, "percentage": 0, "passed": False}

    normalised: dict[int, int] = {}
    if isinstance(submitted_answers, dict):
        for q_id, opt_id in submitted_answers.items():
            try:
                normalised[int(q_id)] = int(opt_id)
            except (TypeError, ValueError):
                continue

    correct = 0
    for question in questions:
        chosen = normalised.get(question.id)
        if chosen is None:
            continue
        correct_option = next((o for o in question.options if o.is_correct), None)
        if correct_option is not None and correct_option.id == chosen:
            correct += 1

    percentage = int(correct / total * 100)
    passed = percentage >= quiz.pass_percentage
    return {"correct": correct, "total": total,
            "percentage": percentage, "passed": passed}


def submit_quiz(user: User, quiz: Quiz, submitted_answers: dict) -> dict[str, Any]:
    """Score a submission and persist a UserQuizAttempt.

    Validates the quiz, scores via calculate_score, records the attempt,
    and commits (rolling back on failure). Does NOT award XP, unlock
    modules, or mark the module completed — those are later tickets.

    Returns {success, error, attempt, correct, total, percentage, passed}.
    """
    result = {
        "success": False, "error": None, "attempt": None,
        "correct": 0, "total": 0, "percentage": 0, "passed": False,
    }

    if quiz is None or not quiz.is_active:
        result["error"] = "quiz_not_found"
        return result

    score = calculate_score(quiz, submitted_answers)
    if score["total"] == 0:
        result["error"] = "quiz_has_no_questions"
        return result

    try:
        attempt = UserQuizAttempt(
            user_id=user.id,
            quiz_id=quiz.id,
            score=score["correct"],
            percentage=score["percentage"],
            passed=score["passed"],
            completed_at=_utcnow(),
        )
        db.session.add(attempt)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Failed to record quiz attempt: user %s quiz %s", user.id, quiz.id
        )
        result["error"] = "persist_failed"
        return result

    result.update({
        "success": True, "attempt": attempt,
        "correct": score["correct"], "total": score["total"],
        "percentage": score["percentage"], "passed": score["passed"],
    })
    return result


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def get_quiz_statistics(user: User) -> dict[str, Any]:
    """Aggregate quiz stats for a user across all their attempts.

    Returns quizzes_completed (distinct quizzes attempted), quizzes_passed
    (distinct quizzes with a passing attempt), average_percentage (mean of
    each attempted quiz's best percentage), and best_percentage (single
    highest across all attempts).
    """
    empty = {"quizzes_completed": 0, "quizzes_passed": 0,
             "average_percentage": 0, "best_percentage": 0}
    if user is None:
        return empty

    attempts = (
        UserQuizAttempt.query
        .filter_by(user_id=user.id)
        .all()
    )
    if not attempts:
        return empty

    # Best percentage per quiz.
    best_per_quiz: dict[int, int] = {}
    passed_quizzes: set[int] = set()
    for a in attempts:
        if a.quiz_id not in best_per_quiz or a.percentage > best_per_quiz[a.quiz_id]:
            best_per_quiz[a.quiz_id] = a.percentage
        if a.passed:
            passed_quizzes.add(a.quiz_id)

    bests = list(best_per_quiz.values())
    return {
        "quizzes_completed": len(best_per_quiz),
        "quizzes_passed": len(passed_quizzes),
        "average_percentage": int(sum(bests) / len(bests)) if bests else 0,
        "best_percentage": max(bests) if bests else 0,
    }


# ---------------------------------------------------------------------------
# Context helper (data assembly for future routes/templates)
# ---------------------------------------------------------------------------
def get_quiz_context(user: User, module_slug: str) -> Optional[dict[str, Any]]:
    """Everything a quiz page needs, or None if the module/quiz is missing."""
    module = get_module(module_slug)
    if module is None:
        return None
    quiz = get_module_quiz(module_slug)
    if quiz is None:
        return None

    return {
        "quiz": quiz,
        "questions": get_quiz_questions(quiz),
        "can_take": can_take_quiz(user, module_slug),
        "passed_before": has_passed_quiz(user, quiz),
        "best_attempt": get_best_attempt(user, quiz),
        "latest_attempt": get_latest_attempt(user, quiz),
    }
