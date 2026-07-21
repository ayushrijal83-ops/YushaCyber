"""Tests for YC-034.0 — Teams, Classrooms & Community Platform.

Covers the five engines (team, classroom, assignment, discussion,
notification), the ORM listeners that turn achievement/certificate
inserts into notifications, and the HTTP surface with role-based
access. Uses an isolated on-disk SQLite database via the config-class
swap pattern (Flask-SQLAlchemy 3 builds engines eagerly, so the URI
must be set before create_app runs).
"""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

_TMPDIR = tempfile.mkdtemp(prefix="yc034-test-")
_DB_PATH = os.path.join(_TMPDIR, "test_community.db")

import config as app_config  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402

_config_class = app_config.get_config()
_ORIGINAL_URI = _config_class.SQLALCHEMY_DATABASE_URI


def _make_app():
    _config_class.SQLALCHEMY_DATABASE_URI = f"sqlite:///{_DB_PATH}"
    _config_class.WTF_CSRF_ENABLED = False
    try:
        app = create_app()
    finally:
        _config_class.SQLALCHEMY_DATABASE_URI = _ORIGINAL_URI
    return app


app = _make_app()

from app.auth.models import User  # noqa: E402
from app.community import (  # noqa: E402
    assignment_engine,
    classroom_engine,
    discussion_engine,
    notification_engine,
    team_engine,
)
from app.community.models import (  # noqa: E402
    Announcement,
    Classroom,
    DiscussionThread,
    Notification,
    Team,
    TeamInvite,
)
from app.labs.models import Lab, UserLabProgress  # noqa: E402
from app.roadmap.models import (  # noqa: E402
    Lesson,
    Quiz,
    RoadmapCategory,
    RoadmapModule,
    UserLessonProgress,
    UserQuizAttempt,
)

PASSWORD = "Str0ngPass!"


def _lab(title: str, slug: str) -> Lab:
    from app.labs.models import LabCategory
    category = LabCategory.query.filter_by(slug="test-cat").first()
    if category is None:
        category = LabCategory(name="Test Cat", slug="test-cat")
        db.session.add(category)
        db.session.flush()
    lab = Lab(category_id=category.id, title=title, slug=slug)
    db.session.add(lab)
    db.session.flush()
    return lab


def _user(username: str, **kwargs) -> User:
    user = User(username=username, email=f"{username}@test.io", **kwargs)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


class CommunityTestBase(unittest.TestCase):
    """Fresh schema per test class; per-test users."""

    @classmethod
    def setUpClass(cls):
        cls.ctx = app.app_context()
        cls.ctx.push()
        db.session.remove()
        db.drop_all()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.ctx.pop()

    def setUp(self):
        # The scoped session is global across test modules; in a full-
        # suite run it can hold identity-map state from OTHER modules'
        # apps/databases. Start every test from a pristine session.
        db.session.remove()
        # Wipe rows between tests, keep schema.
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


# ===========================================================================
# Teams
# ===========================================================================
class TestTeams(CommunityTestBase):
    def test_create_makes_captain_and_member(self):
        alice = _user("alice")
        team = team_engine.create_team(alice, "Red Rivals", logo="🔥")
        self.assertEqual(team.captain_id, alice.id)
        self.assertEqual(team.slug, "red-rivals")
        member = team_engine.membership_of(alice.id)
        self.assertIsNotNone(member)
        self.assertEqual(member.team_id, team.id)

    def test_one_team_per_user(self):
        alice = _user("alice")
        team_engine.create_team(alice, "Team One")
        with self.assertRaises(team_engine.TeamError):
            team_engine.create_team(alice, "Team Two")

    def test_join_open_team(self):
        alice, bob = _user("alice"), _user("bob")
        team = team_engine.create_team(alice, "Open Crew", is_open=True)
        team_engine.join_team(bob, team)
        self.assertEqual(len(team.members), 2)
        # Captain got a "joined" notification.
        self.assertTrue(Notification.query.filter_by(
            user_id=alice.id, type="team_joined").first())

    def test_closed_team_requires_invite(self):
        alice, bob = _user("alice"), _user("bob")
        team = team_engine.create_team(alice, "Closed Cell",
                                       is_open=False)
        with self.assertRaises(team_engine.TeamError):
            team_engine.join_team(bob, team)

    def test_invite_flow_accept(self):
        alice, bob = _user("alice"), _user("bob")
        team = team_engine.create_team(alice, "Invite Only",
                                       is_open=False)
        team_engine.invite(team, alice, "bob")
        notif = Notification.query.filter_by(
            user_id=bob.id, type="team_invite").first()
        self.assertIsNotNone(notif)
        invite = TeamInvite.query.filter_by(invitee_id=bob.id).first()
        team_engine.accept_invite(bob, invite)
        self.assertEqual(team_engine.membership_of(bob.id).team_id,
                         team.id)
        # Invite consumed.
        self.assertIsNone(TeamInvite.query.filter_by(
            invitee_id=bob.id).first())

    def test_invite_decline_deletes(self):
        alice, bob = _user("alice"), _user("bob")
        team = team_engine.create_team(alice, "Declined")
        team_engine.invite(team, alice, "bob")
        invite = TeamInvite.query.filter_by(invitee_id=bob.id).first()
        team_engine.decline_invite(bob, invite)
        self.assertIsNone(TeamInvite.query.filter_by(
            invitee_id=bob.id).first())
        self.assertIsNone(team_engine.membership_of(bob.id))

    def test_only_captain_invites(self):
        alice, bob = _user("alice"), _user("bob")
        _user("carol")
        team = team_engine.create_team(alice, "Strict Ship")
        team_engine.join_team(bob, team)
        with self.assertRaises(team_engine.TeamError):
            team_engine.invite(team, bob, "carol")

    def test_captain_leaves_transfers_captaincy(self):
        alice, bob = _user("alice"), _user("bob")
        team = team_engine.create_team(alice, "Handover")
        team_engine.join_team(bob, team)
        team_engine.leave_team(alice)
        db.session.refresh(team)
        self.assertEqual(team.captain_id, bob.id)

    def test_last_member_leaving_deletes_team(self):
        alice = _user("alice")
        team = team_engine.create_team(alice, "Ghost Town")
        team_id = team.id
        team_engine.leave_team(alice)
        self.assertIsNone(db.session.get(Team, team_id))

    def test_assign_captain(self):
        alice, bob = _user("alice"), _user("bob")
        team = team_engine.create_team(alice, "Rotation")
        team_engine.join_team(bob, team)
        team_engine.assign_captain(team, alice, bob.id)
        self.assertEqual(team.captain_id, bob.id)
        with self.assertRaises(team_engine.TeamError):
            team_engine.assign_captain(team, alice, alice.id)

    def test_team_stats_aggregate(self):
        alice = _user("alice", xp=500, level=5)
        bob = _user("bob", xp=300, level=3)
        team = team_engine.create_team(alice, "Statisticians")
        team_engine.join_team(bob, team)
        lab = _lab("Stats Lab", "stats-lab")
        db.session.add(UserLabProgress(
            user_id=alice.id, lab_id=lab.id, completed=True,
            completed_at=datetime.now(timezone.utc)))
        db.session.commit()
        stats = team_engine.team_stats(team)
        self.assertEqual(stats["total_xp"], 800)
        self.assertEqual(stats["avg_level"], 4.0)
        self.assertEqual(stats["members"], 2)
        self.assertEqual(stats["completed_labs"], 1)

    def test_leaderboard_rankings(self):
        alice = _user("alice", xp=1000)
        bob = _user("bob", xp=100)
        team_engine.create_team(alice, "Alpha")
        team_engine.create_team(bob, "Beta")
        rows = team_engine.leaderboard("xp")
        self.assertEqual(rows[0]["team"].name, "Alpha")
        self.assertEqual(rows[0]["rank"], 1)
        self.assertEqual(rows[1]["team"].name, "Beta")
        self.assertEqual(rows[0]["xp"], 1000)


# ===========================================================================
# Classrooms
# ===========================================================================
class TestClassrooms(CommunityTestBase):
    def test_mentor_creates_student_cannot(self):
        mentor = _user("mentor1", role="mentor")
        student = _user("student1")
        classroom = classroom_engine.create_classroom(mentor, "Web 101")
        self.assertEqual(len(classroom.join_code), 8)
        with self.assertRaises(classroom_engine.ClassroomError):
            classroom_engine.create_classroom(student, "Nope")

    def test_join_by_code(self):
        mentor = _user("mentor1", role="mentor")
        student = _user("student1")
        classroom = classroom_engine.create_classroom(mentor, "Web 101")
        joined = classroom_engine.join_by_code(student,
                                              classroom.join_code.lower())
        self.assertEqual(joined.id, classroom.id)
        self.assertTrue(classroom_engine.can_view(student, classroom))
        with self.assertRaises(classroom_engine.ClassroomError):
            classroom_engine.join_by_code(student, "WRONGCOD")

    def test_add_student_by_username_notifies(self):
        mentor = _user("mentor1", role="mentor")
        student = _user("student1")
        classroom = classroom_engine.create_classroom(mentor, "Web 101")
        classroom_engine.add_student(classroom, mentor, "STUDENT1")
        self.assertTrue(Notification.query.filter_by(
            user_id=student.id, type="classroom_added").first())
        with self.assertRaises(classroom_engine.ClassroomError):
            classroom_engine.add_student(classroom, mentor, "student1")

    def test_teacher_not_enrollable_and_stranger_cannot_manage(self):
        mentor = _user("mentor1", role="mentor")
        stranger = _user("stranger")
        classroom = classroom_engine.create_classroom(mentor, "Web 101")
        with self.assertRaises(classroom_engine.ClassroomError):
            classroom_engine.join_by_code(mentor, classroom.join_code)
        self.assertFalse(classroom_engine.can_manage(stranger, classroom))
        self.assertFalse(classroom_engine.can_view(stranger, classroom))


# ===========================================================================
# Assignments — live completion resolution
# ===========================================================================
class TestAssignments(CommunityTestBase):
    def _classroom_with_student(self):
        mentor = _user("teacher", role="mentor")
        student = _user("pupil")
        classroom = classroom_engine.create_classroom(mentor, "Sec Ops")
        classroom_engine.join_by_code(student, classroom.join_code)
        return mentor, student, classroom

    def test_create_lab_assignment_notifies(self):
        mentor, student, classroom = self._classroom_with_student()
        lab = _lab("Nmap Lab", "nmap-lab")
        db.session.commit()
        assignment = assignment_engine.create_assignment(
            classroom, mentor.id, "lab", lab.id)
        self.assertEqual(assignment.title, "Nmap Lab")
        self.assertTrue(Notification.query.filter_by(
            user_id=student.id, type="assignment_new").first())

    def test_preexisting_progress_counts_done(self):
        mentor, student, classroom = self._classroom_with_student()
        lab = _lab("Old Lab", "old-lab")
        db.session.add(UserLabProgress(
            user_id=student.id, lab_id=lab.id, completed=True,
            completed_at=datetime.now(timezone.utc)))
        db.session.commit()
        assignment = assignment_engine.create_assignment(
            classroom, mentor.id, "lab", lab.id)
        status = assignment_engine.status_for(
            assignment, [student.id])[student.id]
        self.assertTrue(status["done"])
        self.assertFalse(status["late"])

    def test_late_and_overdue(self):
        mentor, student, classroom = self._classroom_with_student()
        lab = _lab("Late Lab", "late-lab")
        due = datetime.now(timezone.utc) - timedelta(days=2)
        assignment = assignment_engine.create_assignment(
            classroom, mentor.id, "lab", lab.id, due_at=due)
        # Not done + past due -> overdue.
        status = assignment_engine.status_for(
            assignment, [student.id])[student.id]
        self.assertFalse(status["done"])
        self.assertTrue(status["overdue"])
        # Complete AFTER the due date -> done but late.
        db.session.add(UserLabProgress(
            user_id=student.id, lab_id=lab.id, completed=True,
            completed_at=datetime.now(timezone.utc)))
        db.session.commit()
        status = assignment_engine.status_for(
            assignment, [student.id])[student.id]
        self.assertTrue(status["done"])
        self.assertTrue(status["late"])
        self.assertFalse(status["overdue"])

    def test_quiz_assignment_first_pass(self):
        mentor, student, classroom = self._classroom_with_student()
        category = RoadmapCategory(title="Cat", display_order=1)
        db.session.add(category)
        db.session.flush()
        module = RoadmapModule(category_id=category.id, title="Mod",
                               slug="mod", display_order=1)
        db.session.add(module)
        db.session.flush()
        quiz = Quiz(module_id=module.id, title="Quiz 1",
                    is_active=True)
        db.session.add(quiz)
        db.session.flush()
        assignment = assignment_engine.create_assignment(
            classroom, mentor.id, "quiz", quiz.id)
        status = assignment_engine.status_for(
            assignment, [student.id])[student.id]
        self.assertFalse(status["done"])
        db.session.add(UserQuizAttempt(
            user_id=student.id, quiz_id=quiz.id, score=9,
            percentage=90.0, passed=True,
            completed_at=datetime.now(timezone.utc)))
        db.session.commit()
        status = assignment_engine.status_for(
            assignment, [student.id])[student.id]
        self.assertTrue(status["done"])

    def test_roadmap_assignment_requires_all_lessons(self):
        mentor, student, classroom = self._classroom_with_student()
        category = RoadmapCategory(title="Linux",
                                   display_order=1)
        db.session.add(category)
        db.session.flush()
        module = RoadmapModule(category_id=category.id, title="Basics",
                               slug="basics", display_order=1)
        db.session.add(module)
        db.session.flush()
        lessons = [Lesson(module_id=module.id, title=f"L{i}",
                          slug=f"l{i}", display_order=i)
                   for i in (1, 2)]
        db.session.add_all(lessons)
        db.session.commit()
        assignment = assignment_engine.create_assignment(
            classroom, mentor.id, "roadmap", category.id)

        db.session.add(UserLessonProgress(
            user_id=student.id, lesson_id=lessons[0].id, completed=True,
            completed_at=datetime.now(timezone.utc)))
        db.session.commit()
        status = assignment_engine.status_for(
            assignment, [student.id])[student.id]
        self.assertFalse(status["done"])  # only 1 of 2

        db.session.add(UserLessonProgress(
            user_id=student.id, lesson_id=lessons[1].id, completed=True,
            completed_at=datetime.now(timezone.utc)))
        db.session.commit()
        status = assignment_engine.status_for(
            assignment, [student.id])[student.id]
        self.assertTrue(status["done"])

    def test_unknown_subject_rejected(self):
        mentor, _, classroom = self._classroom_with_student()
        with self.assertRaises(assignment_engine.AssignmentError):
            assignment_engine.create_assignment(
                classroom, mentor.id, "podcast", 1)
        with self.assertRaises(assignment_engine.AssignmentError):
            assignment_engine.create_assignment(
                classroom, mentor.id, "lab", 99999)

    def test_progress_board(self):
        mentor, student, classroom = self._classroom_with_student()
        lab = _lab("Board Lab", "board-lab")
        db.session.add(UserLabProgress(
            user_id=student.id, lab_id=lab.id, completed=True,
            completed_at=datetime.now(timezone.utc),
            time_spent_seconds=600))
        db.session.commit()
        assignment_engine.create_assignment(
            classroom, mentor.id, "lab", lab.id)
        board = classroom_engine.progress_board(classroom)
        self.assertEqual(len(board), 1)
        row = board[0]
        self.assertEqual(row["user"].id, student.id)
        self.assertEqual(row["assignments_done"], 1)
        self.assertEqual(row["completion_pct"], 100)
        self.assertGreaterEqual(row["time_spent_seconds"], 600)


# ===========================================================================
# Discussions
# ===========================================================================
class TestDiscussions(CommunityTestBase):
    def test_thread_reply_and_pin_toggle(self):
        alice, bob = _user("alice"), _user("bob")
        thread = discussion_engine.create_thread(
            alice.id, "lab", 1, "How do I escalate?", is_question=True)
        reply = discussion_engine.add_reply(thread, bob.id,
                                            "Check sudo -l first.")
        discussion_engine.pin_reply(thread, alice, reply.id)
        self.assertEqual(thread.pinned_reply_id, reply.id)
        # Toggle un-pins.
        discussion_engine.pin_reply(thread, alice, reply.id)
        self.assertIsNone(thread.pinned_reply_id)

    def test_stranger_cannot_pin_mentor_can(self):
        alice, stranger = _user("alice"), _user("stranger")
        mentor = _user("mentor1", role="mentor")
        thread = discussion_engine.create_thread(
            alice.id, "lesson", 7, "Notes on XSS")
        reply = discussion_engine.add_reply(thread, stranger.id, "tip")
        with self.assertRaises(discussion_engine.DiscussionError):
            discussion_engine.pin_reply(thread, stranger, reply.id)
        discussion_engine.pin_reply(thread, mentor, reply.id)
        self.assertEqual(thread.pinned_reply_id, reply.id)

    def test_subject_whitelist_and_listing(self):
        alice = _user("alice")
        with self.assertRaises(discussion_engine.DiscussionError):
            discussion_engine.create_thread(alice.id, "ctf", 1, "nope")
        discussion_engine.create_thread(alice.id, "lab", 3, "Lab 3 talk")
        discussion_engine.create_thread(alice.id, "lab", 4, "Lab 4 talk")
        self.assertEqual(len(discussion_engine.threads_for("lab", 3)), 1)
        self.assertEqual(len(discussion_engine.threads_for("lab", 9)), 0)


# ===========================================================================
# Notifications + announcements
# ===========================================================================
class TestNotifications(CommunityTestBase):
    def test_notify_dedupe_unread_and_read_all(self):
        alice = _user("alice")
        sent = notification_engine.notify(
            [alice.id, alice.id, None], "announcement", "Hello")
        db.session.commit()
        self.assertEqual(sent, 1)
        self.assertEqual(notification_engine.unread_count(alice.id), 1)
        notification_engine.mark_all_read(alice.id)
        self.assertEqual(notification_engine.unread_count(alice.id), 0)

    def test_achievement_insert_creates_notification(self):
        from app.achievement.models import Achievement, UserAchievement
        alice = _user("alice")
        achievement = Achievement(
            title="First Blood", description="d", icon="🩸",
            category="ctf", condition_type="ctf_solves",
            condition_value=1)
        db.session.add(achievement)
        db.session.flush()
        db.session.add(UserAchievement(user_id=alice.id,
                                       achievement_id=achievement.id))
        db.session.commit()
        notif = Notification.query.filter_by(
            user_id=alice.id, type="achievement").first()
        self.assertIsNotNone(notif)
        self.assertIn("First Blood", notif.body)

    def test_certificate_insert_creates_notification(self):
        from app.certificates.models import Certificate, UserCertificate
        alice = _user("alice")
        certificate = Certificate(
            title="Linux Fundamentals", slug="linux-fund",
            description="d")
        db.session.add(certificate)
        db.session.flush()
        db.session.add(UserCertificate(
            user_id=alice.id, certificate_id=certificate.id,
            certificate_code="YC-TEST-0001"))
        db.session.commit()
        notif = Notification.query.filter_by(
            user_id=alice.id, type="certificate").first()
        self.assertIsNotNone(notif)
        self.assertIn("Linux Fundamentals", notif.body)

    def test_global_announcement_admin_only_and_fans_out(self):
        admin = _user("boss", is_admin=True)
        alice, bob = _user("alice"), _user("bob")
        with self.assertRaises(classroom_engine.ClassroomError):
            classroom_engine.post_announcement(alice, "Hi", "Nope")
        classroom_engine.post_announcement(admin, "Maintenance",
                                           "Down at midnight.")
        self.assertEqual(Announcement.query.count(), 1)
        for user in (alice, bob):
            self.assertTrue(Notification.query.filter_by(
                user_id=user.id, type="announcement").first())

    def test_classroom_announcement_by_teacher_only(self):
        mentor = _user("mentor1", role="mentor")
        student = _user("student1")
        classroom = classroom_engine.create_classroom(mentor, "Web 101")
        classroom_engine.join_by_code(student, classroom.join_code)
        with self.assertRaises(classroom_engine.ClassroomError):
            classroom_engine.post_announcement(
                student, "Hi", "class", classroom=classroom)
        classroom_engine.post_announcement(
            mentor, "Quiz Friday", "Prepare!", classroom=classroom)
        self.assertTrue(Notification.query.filter_by(
            user_id=student.id, type="announcement").first())


# ===========================================================================
# HTTP surface
# ===========================================================================
class TestHTTPSurface(CommunityTestBase):
    """HTTP tests run inside the class-level app context, which Flask
    reuses for test requests — so Flask-Login's per-app-context cache
    (``g._login_user``) would leak between clients. ``_fresh`` clears
    it whenever we switch identity."""

    @staticmethod
    def _fresh():
        from flask import g
        g.pop("_login_user", None)

    def _login(self, client, username: str):
        self._fresh()
        return client.post("/auth/login", data={
            "identifier": username, "password": PASSWORD},
            follow_redirects=True)

    def test_pages_render_and_flows_work(self):
        _user("alice")
        _user("mentor1", role="mentor")
        with app.test_client() as client:
            self._login(client, "alice")
            for path in ("/teams", "/teams/leaderboard",
                         "/classrooms", "/notifications",
                         "/announcements"):
                response = client.get(path)
                self.assertEqual(response.status_code, 200, path)

            # Create team via HTTP.
            response = client.post("/teams/create", data={
                "name": "HTTP Heroes", "logo": "🚀", "is_open": "on"},
                follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"HTTP Heroes", response.data)

        with app.test_client() as client:
            self._login(client, "mentor1")
            response = client.post("/classrooms/create", data={
                "name": "HTTP Class"}, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"HTTP Class", response.data)
            classroom = Classroom.query.filter_by(
                name="HTTP Class").first()
            # Stranger blocked from the classroom page.
        with app.test_client() as client:
            self._login(client, "alice")
            response = client.get(f"/classrooms/{classroom.id}")
            self._fresh()
            self.assertEqual(response.status_code, 403)

    def test_anonymous_redirected(self):
        self._fresh()
        with app.test_client() as client:
            for path in ("/teams", "/classrooms", "/notifications"):
                response = client.get(path)
                self.assertEqual(response.status_code, 302, path)

    def test_discussion_post_via_http_and_lab_page_renders(self):
        _user("alice")
        lab = _lab("Disc Lab", "disc-lab")
        db.session.commit()
        with app.test_client() as client:
            self._login(client, "alice")
            response = client.post("/discussions/create", data={
                "subject_type": "lab", "subject_id": lab.id,
                "title": "Stuck on step 2",
                "next": f"/labs/{lab.slug}#discussion"},
                follow_redirects=False)
            self.assertEqual(response.status_code, 302)
            thread = DiscussionThread.query.filter_by(
                subject_type="lab", subject_id=lab.id).first()
            self.assertIsNotNone(thread)
            # The lab page renders with the discussion embedded.
            response = client.get(f"/labs/{lab.slug}")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Stuck on step 2", response.data)

    def test_discussion_on_lesson_page(self):
        _user("alice")
        from app.roadmap.models import Lesson, RoadmapCategory, RoadmapModule
        category = RoadmapCategory(title="Cat", display_order=1)
        db.session.add(category)
        db.session.flush()
        module = RoadmapModule(category_id=category.id, title="Mod",
                               slug="mod", display_order=1)
        db.session.add(module)
        db.session.flush()
        lesson = Lesson(module_id=module.id, title="Intro", slug="intro",
                        display_order=1)
        db.session.add(lesson)
        db.session.commit()
        with app.test_client() as client:
            self._login(client, "alice")
            response = client.get("/roadmap/mod/intro/")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'id="discussion"', response.data)
            client.post("/discussions/create", data={
                "subject_type": "lesson", "subject_id": lesson.id,
                "title": "Lesson question here"})
            response = client.get("/roadmap/mod/intro/")
            self.assertIn(b"Lesson question here", response.data)


if __name__ == "__main__":
    unittest.main()
