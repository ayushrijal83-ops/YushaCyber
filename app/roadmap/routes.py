"""Roadmap routes.

Thin controllers only — data assembly lives in ``services.py`` so the
placeholder tiers can be swapped for real roadmap content (YC-006.2+)
without touching this module.
"""

from __future__ import annotations

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.roadmap import roadmap_bp, services


@roadmap_bp.route("/")
@login_required
def index():
    """Render the roadmap page."""
    context = services.get_roadmap_context(current_user)
    return render_template("roadmap/roadmap.html", user=current_user, **context)


@roadmap_bp.route("/<module_slug>/")
@login_required
def module_detail(module_slug: str):
    """Render a single module and its lessons, or 404 if not found."""
    context = services.get_module_detail_context(current_user, module_slug)
    if context is None:
        abort(404)
    return render_template("roadmap/module.html", user=current_user, **context)


@roadmap_bp.route("/<module_slug>/<lesson_slug>/")
@login_required
def lesson_view(module_slug: str, lesson_slug: str):
    """Render a single lesson's content, or 404 if module/lesson missing."""
    context = services.get_lesson_view_context(current_user, module_slug, lesson_slug)
    if context is None:
        abort(404)
    return render_template("roadmap/lesson.html", user=current_user, **context)


@roadmap_bp.route("/<module_slug>/<lesson_slug>/complete", methods=["POST"])
@login_required
def complete_lesson(module_slug: str, lesson_slug: str):
    """Mark a lesson complete (POST, CSRF-protected), then return to it."""
    result = services.complete_lesson(current_user, module_slug, lesson_slug)

    if result["lesson"] is None:
        abort(404)

    if result["already_completed"]:
        flash("You have already completed this lesson.", "error")
    elif result["success"]:
        flash(
            f"Lesson completed successfully! +{result['xp_awarded']} XP awarded.",
            "success",
        )
        # Module-completion + unlock feedback (YC-007.0).
        if result["module_completed"]:
            flash(
                f"🎉 Module Completed! +{result['module_xp_awarded']} Bonus XP",
                "success",
            )
            if result["unlocked_module_title"]:
                flash(
                    f"🔓 New Module Unlocked! {result['unlocked_module_title']}",
                    "success",
                )
    else:
        flash("Unable to complete lesson.", "error")

    return redirect(
        url_for("roadmap.lesson_view", module_slug=module_slug, lesson_slug=lesson_slug)
    )


@roadmap_bp.route("/quizzes/")
@login_required
def quiz_index():
    """List every module's quiz with the current user's status."""
    context = services.get_quiz_index_context(current_user)
    return render_template("roadmap/quiz_index.html", user=current_user, **context)


@roadmap_bp.route("/<module_slug>/quiz/")
@login_required
def quiz_view(module_slug: str):
    """Render a module's quiz, or 404 if the module/quiz is missing."""
    context = services.get_quiz_page_context(current_user, module_slug)
    if context is None:
        abort(404)
    return render_template("roadmap/quiz.html", user=current_user, **context)


@roadmap_bp.route("/<module_slug>/quiz/submit", methods=["POST"])
@login_required
def quiz_submit(module_slug: str):
    """Grade a quiz submission (POST, CSRF), then show the result page."""
    quiz = services.get_quiz(module_slug)
    if quiz is None:
        abort(404)

    # Collect answers from the form: question_<id> -> option id.
    answers: dict[int, int] = {}
    for key, value in request.form.items():
        if key.startswith("question_"):
            try:
                answers[int(key.split("_", 1)[1])] = int(value)
            except (ValueError, IndexError):
                continue

    result = services.submit_quiz(current_user, quiz, answers)

    if not result["success"]:
        flash("Unable to submit quiz. Please try again.", "error")
        return redirect(url_for("roadmap.quiz_view", module_slug=module_slug))

    if result["passed"]:
        flash(
            f"✅ Passed! You scored {result['percentage']}% "
            f"({result['score']}/{result['total']}).",
            "success",
        )
    else:
        flash(
            f"❌ Not passed. You scored {result['percentage']}% "
            f"({result['score']}/{result['total']}). "
            f"Need {quiz.pass_percentage}% to pass — try again!",
            "error",
        )

    return redirect(url_for("roadmap.quiz_view", module_slug=module_slug))
