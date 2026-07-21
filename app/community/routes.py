"""Community routes (YC-034.0).

Pages and form endpoints for teams, classrooms, assignments,
discussions, notifications and announcements. All business rules live
in the engines — routes translate HTTP to engine calls and flash the
outcome.
"""

from __future__ import annotations

from datetime import datetime

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.community import (
    assignment_engine,
    classroom_engine,
    discussion_engine,
    notification_engine,
    team_engine,
)
from app.community.models import (
    Announcement,
    Assignment,
    Classroom,
    DiscussionThread,
    Team,
    TeamInvite,
)

community_bp = Blueprint("community", __name__)


def _back(fallback: str):
    target = request.form.get("next") or request.referrer
    return redirect(target or fallback)


def _parse_due(raw: str | None) -> datetime | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


# ===========================================================================
# Teams
# ===========================================================================
@community_bp.route("/teams")
@login_required
def teams():
    membership = team_engine.membership_of(current_user.id)
    invites = (TeamInvite.query
               .filter_by(invitee_id=current_user.id).all())
    all_teams = Team.query.order_by(Team.created_at.desc()).all()
    return render_template(
        "community/teams.html", membership=membership,
        invites=invites, all_teams=all_teams,
        member_counts={t.id: len(t.members) for t in all_teams})


@community_bp.route("/teams/create", methods=["POST"])
@login_required
def team_create():
    try:
        team = team_engine.create_team(
            current_user,
            name=request.form.get("name", ""),
            description=request.form.get("description", ""),
            logo=request.form.get("logo", "🛡️"),
            is_open=request.form.get("is_open") == "on")
    except team_engine.TeamError as exc:
        flash(str(exc), "error")
        return redirect(url_for("community.teams"))
    flash(f"Team “{team.name}” created — you are the captain.", "success")
    return redirect(url_for("community.team_detail", slug=team.slug))


@community_bp.route("/teams/leaderboard")
@login_required
def team_leaderboard():
    metric = request.args.get("metric", "xp")
    if metric not in team_engine.LEADERBOARD_METRICS:
        metric = "xp"
    return render_template("community/team_leaderboard.html",
                           rows=team_engine.leaderboard(metric),
                           metric=metric,
                           metrics=team_engine.LEADERBOARD_METRICS)


@community_bp.route("/teams/<slug>")
@login_required
def team_detail(slug: str):
    team = Team.query.filter_by(slug=slug).first_or_404()
    membership = team_engine.membership_of(current_user.id)
    return render_template(
        "community/team_detail.html", team=team,
        stats=team_engine.team_stats(team),
        membership=membership,
        is_member=bool(membership and membership.team_id == team.id),
        is_captain=team.captain_id == current_user.id)


@community_bp.route("/teams/<slug>/join", methods=["POST"])
@login_required
def team_join(slug: str):
    team = Team.query.filter_by(slug=slug).first_or_404()
    try:
        team_engine.join_team(current_user, team)
        flash(f"Welcome to {team.name}!", "success")
    except team_engine.TeamError as exc:
        flash(str(exc), "error")
    return redirect(url_for("community.team_detail", slug=slug))


@community_bp.route("/teams/leave", methods=["POST"])
@login_required
def team_leave():
    try:
        team_engine.leave_team(current_user)
        flash("You left the team.", "success")
    except team_engine.TeamError as exc:
        flash(str(exc), "error")
    return redirect(url_for("community.teams"))


@community_bp.route("/teams/<slug>/invite", methods=["POST"])
@login_required
def team_invite(slug: str):
    team = Team.query.filter_by(slug=slug).first_or_404()
    try:
        team_engine.invite(team, current_user,
                           request.form.get("username", ""))
        flash("Invite sent.", "success")
    except team_engine.TeamError as exc:
        flash(str(exc), "error")
    return redirect(url_for("community.team_detail", slug=slug))


@community_bp.route("/teams/invites/<int:invite_id>/<action>",
                    methods=["POST"])
@login_required
def team_invite_action(invite_id: int, action: str):
    invite = TeamInvite.query.get_or_404(invite_id)
    try:
        if action == "accept":
            team = team_engine.accept_invite(current_user, invite)
            flash(f"You joined {team.name}!", "success")
            return redirect(url_for("community.team_detail",
                                    slug=team.slug))
        if action == "decline":
            team_engine.decline_invite(current_user, invite)
            flash("Invite declined.", "success")
        else:
            abort(404)
    except team_engine.TeamError as exc:
        flash(str(exc), "error")
    return redirect(url_for("community.teams"))


@community_bp.route("/teams/<slug>/captain", methods=["POST"])
@login_required
def team_captain(slug: str):
    team = Team.query.filter_by(slug=slug).first_or_404()
    try:
        team_engine.assign_captain(
            team, current_user, int(request.form.get("user_id", 0)))
        flash("Captaincy transferred.", "success")
    except (team_engine.TeamError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("community.team_detail", slug=slug))


@community_bp.route("/teams/<slug>/edit", methods=["POST"])
@login_required
def team_edit(slug: str):
    team = Team.query.filter_by(slug=slug).first_or_404()
    try:
        team_engine.update_team(
            team, current_user,
            description=request.form.get("description"),
            logo=request.form.get("logo"),
            is_open=request.form.get("is_open") == "on")
        flash("Team updated.", "success")
    except team_engine.TeamError as exc:
        flash(str(exc), "error")
    return redirect(url_for("community.team_detail", slug=slug))


# ===========================================================================
# Classrooms
# ===========================================================================
@community_bp.route("/classrooms")
@login_required
def classrooms():
    teaching = Classroom.query.filter_by(
        teacher_id=current_user.id).all() \
        if classroom_engine.is_teacher(current_user) else []
    enrolled = (Classroom.query
                .join(Classroom.members)
                .filter_by(user_id=current_user.id).all())
    return render_template(
        "community/classrooms.html", teaching=teaching,
        enrolled=enrolled,
        is_teacher=classroom_engine.is_teacher(current_user))


@community_bp.route("/classrooms/create", methods=["POST"])
@login_required
def classroom_create():
    try:
        classroom = classroom_engine.create_classroom(
            current_user, request.form.get("name", ""),
            request.form.get("description", ""))
    except classroom_engine.ClassroomError as exc:
        flash(str(exc), "error")
        return redirect(url_for("community.classrooms"))
    flash(f"Classroom “{classroom.name}” created — share join code "
          f"{classroom.join_code} with your students.", "success")
    return redirect(url_for("community.classroom_detail",
                            classroom_id=classroom.id))


@community_bp.route("/classrooms/join", methods=["POST"])
@login_required
def classroom_join():
    try:
        classroom = classroom_engine.join_by_code(
            current_user, request.form.get("code", ""))
        flash(f"You joined “{classroom.name}”.", "success")
        return redirect(url_for("community.classroom_detail",
                                classroom_id=classroom.id))
    except classroom_engine.ClassroomError as exc:
        flash(str(exc), "error")
        return redirect(url_for("community.classrooms"))


@community_bp.route("/classrooms/<int:classroom_id>")
@login_required
def classroom_detail(classroom_id: int):
    classroom = Classroom.query.get_or_404(classroom_id)
    if not classroom_engine.can_view(current_user, classroom):
        abort(403)
    manage = classroom_engine.can_manage(current_user, classroom)
    student_ids = [m.user_id for m in classroom.members]
    assignment_status = {
        a.id: assignment_engine.status_for(a, student_ids)
        for a in classroom.assignments}
    my_status = {
        a.id: assignment_status[a.id].get(current_user.id)
        for a in classroom.assignments} if not manage else {}
    announcements = (Announcement.query
                     .filter_by(classroom_id=classroom.id)
                     .order_by(Announcement.created_at.desc()).all())
    return render_template(
        "community/classroom_detail.html", classroom=classroom,
        manage=manage,
        board=classroom_engine.progress_board(classroom) if manage
        else [],
        assignment_status=assignment_status, my_status=my_status,
        announcements=announcements,
        catalog=assignment_engine.subject_catalog() if manage else {})


@community_bp.route("/classrooms/<int:classroom_id>/add-student",
                    methods=["POST"])
@login_required
def classroom_add_student(classroom_id: int):
    classroom = Classroom.query.get_or_404(classroom_id)
    try:
        student = classroom_engine.add_student(
            classroom, current_user, request.form.get("username", ""))
        flash(f"{student.username} added to the classroom.", "success")
    except classroom_engine.ClassroomError as exc:
        flash(str(exc), "error")
    return redirect(url_for("community.classroom_detail",
                            classroom_id=classroom_id))


@community_bp.route("/classrooms/<int:classroom_id>/leave",
                    methods=["POST"])
@login_required
def classroom_leave(classroom_id: int):
    classroom = Classroom.query.get_or_404(classroom_id)
    try:
        classroom_engine.leave(classroom, current_user)
        flash(f"You left “{classroom.name}”.", "success")
    except classroom_engine.ClassroomError as exc:
        flash(str(exc), "error")
    return redirect(url_for("community.classrooms"))


@community_bp.route("/classrooms/<int:classroom_id>/assignments/create",
                    methods=["POST"])
@login_required
def assignment_create(classroom_id: int):
    classroom = Classroom.query.get_or_404(classroom_id)
    if not classroom_engine.can_manage(current_user, classroom):
        abort(403)
    try:
        assignment_engine.create_assignment(
            classroom, current_user.id,
            subject_type=request.form.get("subject_type", ""),
            subject_id=int(request.form.get("subject_id", 0)),
            instructions=request.form.get("instructions", ""),
            due_at=_parse_due(request.form.get("due_at")))
        flash("Assignment created — students have been notified.",
              "success")
    except (assignment_engine.AssignmentError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("community.classroom_detail",
                            classroom_id=classroom_id))


@community_bp.route(
    "/classrooms/<int:classroom_id>/assignments/<int:assignment_id>")
@login_required
def assignment_detail(classroom_id: int, assignment_id: int):
    classroom = Classroom.query.get_or_404(classroom_id)
    assignment = Assignment.query.filter_by(
        id=assignment_id, classroom_id=classroom.id).first_or_404()
    if not classroom_engine.can_view(current_user, classroom):
        abort(403)
    student_ids = [m.user_id for m in classroom.members]
    statuses = assignment_engine.status_for(assignment, student_ids)
    return render_template(
        "community/assignment_detail.html", classroom=classroom,
        assignment=assignment, statuses=statuses,
        members=classroom.members,
        manage=classroom_engine.can_manage(current_user, classroom))


@community_bp.route("/classrooms/<int:classroom_id>/announce",
                    methods=["POST"])
@login_required
def classroom_announce(classroom_id: int):
    classroom = Classroom.query.get_or_404(classroom_id)
    try:
        classroom_engine.post_announcement(
            current_user, request.form.get("title", ""),
            request.form.get("body", ""), classroom=classroom)
        flash("Announcement posted.", "success")
    except classroom_engine.ClassroomError as exc:
        flash(str(exc), "error")
    return redirect(url_for("community.classroom_detail",
                            classroom_id=classroom_id))


# ===========================================================================
# Announcements (global)
# ===========================================================================
@community_bp.route("/announcements")
@login_required
def announcements():
    items = (Announcement.query.filter_by(classroom_id=None)
             .order_by(Announcement.created_at.desc()).all())
    return render_template("community/announcements.html", items=items)


@community_bp.route("/announcements/create", methods=["POST"])
@login_required
def announcement_create():
    try:
        classroom_engine.post_announcement(
            current_user, request.form.get("title", ""),
            request.form.get("body", ""), classroom=None)
        flash("Announcement published to everyone.", "success")
    except classroom_engine.ClassroomError as exc:
        flash(str(exc), "error")
    return redirect(url_for("community.announcements"))


# ===========================================================================
# Notifications
# ===========================================================================
@community_bp.route("/notifications")
@login_required
def notifications():
    items = notification_engine.recent(current_user.id, limit=50)
    return render_template("community/notifications.html", items=items)


@community_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def notifications_read_all():
    notification_engine.mark_all_read(current_user.id)
    flash("All notifications marked as read.", "success")
    return redirect(url_for("community.notifications"))


# ===========================================================================
# Discussions (posted from lab/lesson pages)
# ===========================================================================
@community_bp.route("/discussions/create", methods=["POST"])
@login_required
def discussion_create():
    try:
        discussion_engine.create_thread(
            current_user.id,
            subject_type=request.form.get("subject_type", ""),
            subject_id=int(request.form.get("subject_id", 0)),
            title=request.form.get("title", ""),
            body=request.form.get("body", ""),
            is_question=request.form.get("is_question") == "on")
        flash("Thread posted.", "success")
    except (discussion_engine.DiscussionError, ValueError) as exc:
        flash(str(exc), "error")
    return _back(url_for("dashboard.index"))


@community_bp.route("/discussions/<int:thread_id>/reply",
                    methods=["POST"])
@login_required
def discussion_reply(thread_id: int):
    thread = DiscussionThread.query.get_or_404(thread_id)
    try:
        discussion_engine.add_reply(thread, current_user.id,
                                    request.form.get("body", ""))
        flash("Reply posted.", "success")
    except discussion_engine.DiscussionError as exc:
        flash(str(exc), "error")
    return _back(url_for("dashboard.index"))


@community_bp.route("/discussions/<int:thread_id>/pin",
                    methods=["POST"])
@login_required
def discussion_pin(thread_id: int):
    thread = DiscussionThread.query.get_or_404(thread_id)
    try:
        discussion_engine.pin_reply(
            thread, current_user,
            int(request.form.get("reply_id", 0)))
        flash("Pinned answer updated.", "success")
    except (discussion_engine.DiscussionError, ValueError) as exc:
        flash(str(exc), "error")
    return _back(url_for("dashboard.index"))


@community_bp.app_template_global("discussion_threads_for")
def discussion_threads_for(subject_type: str, subject_id: int):
    """Template global — lets the discussion partial fetch its own
    threads, so lab/lesson routes need zero changes."""
    return discussion_engine.threads_for(subject_type, int(subject_id))


# ===========================================================================
# Context processor — the live notification bell.
# ===========================================================================
@community_bp.app_context_processor
def inject_notifications():
    if not current_user.is_authenticated:
        return {"notif_unread": 0, "notif_recent": []}
    return {
        "notif_unread": notification_engine.unread_count(current_user.id),
        "notif_recent": notification_engine.recent(current_user.id,
                                                   limit=5),
    }
