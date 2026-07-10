"""Quiz seed.

Creates exactly one quiz per roadmap module, each with 10 questions and
4 options per question (one correct). Uses SQLAlchemy models only — no
raw SQL. Idempotent: if any quiz already exists the seeder does nothing,
so re-running never duplicates data.

Run via the Flask CLI (registered in the app factory):

    flask --app app seed-quizzes

The question content is generated from per-module templates. It is
placeholder-quality (structurally valid, one correct answer each) so the
quiz system has real data to exercise; swap in authored questions later
without touching this seeder's shape.
"""

from __future__ import annotations

from app.extensions import db
from app.roadmap.models import (
    Quiz,
    QuizOption,
    QuizQuestion,
    RoadmapModule,
)

QUIZ_XP_REWARD = 100
QUIZ_PASS_PERCENTAGE = 70
QUIZ_TIME_LIMIT_MINUTES = 15
QUESTIONS_PER_QUIZ = 10
OPTIONS_PER_QUESTION = 4


def _build_questions(module_title: str) -> list[QuizQuestion]:
    """Build 10 placeholder questions for a module, each with 4 options.

    Each question has exactly one correct option. The correct option's
    position is rotated across questions (deterministic) so answers are
    not all in the same slot.
    """
    questions: list[QuizQuestion] = []
    for i in range(1, QUESTIONS_PER_QUIZ + 1):
        q = QuizQuestion(
            question_text=(
                f"{module_title} — question {i}: which option is correct?"
            ),
            explanation=(
                f"Review the {module_title} material to understand why "
                f"option {((i - 1) % OPTIONS_PER_QUESTION) + 1} is correct "
                f"for question {i}."
            ),
            display_order=i,
        )
        # Rotate which option index is correct (0-based) across questions.
        correct_index = (i - 1) % OPTIONS_PER_QUESTION
        for j in range(OPTIONS_PER_QUESTION):
            q.options.append(QuizOption(
                option_text=f"Option {j + 1} for question {i}",
                is_correct=(j == correct_index),
                display_order=j + 1,
            ))
        questions.append(q)
    return questions


def seed_quizzes() -> dict[str, int]:
    """Create one quiz per module if no quizzes exist. Returns a summary.

    Idempotent: if any quiz already exists the function makes no changes
    and reports existing counts.
    """
    if Quiz.query.first() is not None:
        return {
            "created": 0,
            "quizzes": Quiz.query.count(),
            "questions": QuizQuestion.query.count(),
            "options": QuizOption.query.count(),
        }

    modules = RoadmapModule.query.order_by(RoadmapModule.id).all()
    quizzes = questions = options = 0

    for module in modules:
        quiz = Quiz(
            module_id=module.id,
            title=f"{module.title} Quiz",
            description=f"Test your knowledge of {module.title}.",
            xp_reward=QUIZ_XP_REWARD,
            pass_percentage=QUIZ_PASS_PERCENTAGE,
            time_limit_minutes=QUIZ_TIME_LIMIT_MINUTES,
            is_active=True,
        )
        quiz.questions.extend(_build_questions(module.title))
        db.session.add(quiz)

        quizzes += 1
        questions += QUESTIONS_PER_QUIZ
        options += QUESTIONS_PER_QUIZ * OPTIONS_PER_QUESTION

    db.session.commit()
    return {"created": 1, "quizzes": quizzes,
            "questions": questions, "options": options}
