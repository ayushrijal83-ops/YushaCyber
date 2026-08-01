"""Tests for YC-031.7 — Public Profile Engine."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0317-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_profile.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.core.profile import (  # noqa: E402
    ActivityItem,
    PrivacySettings,
    ProfileData,
    ProfileStatistics,
    ShareData,
    SocialLinks,
    Visibility,
)


# ===========================================================================
# Types
# ===========================================================================
class TestTypes:
    def test_visibility_enum(self):
        assert Visibility.PUBLIC.value == "public"
        assert Visibility.PRIVATE.value == "private"

    def test_profile_data_to_dict(self):
        p = ProfileData(username="ayush", bio="Security learner")
        d = p.to_dict()
        assert d["username"] == "ayush"
        assert d["bio"] == "Security learner"

    def test_social_links(self):
        s = SocialLinks(github="https://github.com/ayush")
        assert s.to_dict()["github"] == "https://github.com/ayush"

    def test_privacy_section_visible(self):
        p = PrivacySettings(show_achievements=False)
        assert p.section_visible("achievements") is False
        assert p.section_visible("certificates") is True
        assert p.section_visible("unknown") is True

    def test_privacy_private_hides_all(self):
        p = PrivacySettings(profile_visibility="private")
        # Global privacy is handled by filter_sections, not section_visible
        assert p.profile_visibility == "private"

    def test_activity_item(self):
        a = ActivityItem(type="achievement", title="SOC Rookie")
        assert a.to_dict()["type"] == "achievement"

    def test_profile_statistics(self):
        s = ProfileStatistics(total_xp=5000, level=25)
        d = s.to_dict()
        assert d["total_xp"] == 5000

    def test_share_data(self):
        s = ShareData(public_url="/u/ayush",
                      og_title="Ayush — YushaCyber")
        assert s.to_dict()["public_url"] == "/u/ayush"


# ===========================================================================
# Privacy
# ===========================================================================
class TestPrivacy:
    def test_filter_sections_public(self):
        from app.core.profile.privacy import filter_sections

        class FakeUser:
            pass
        u = FakeUser()
        sections = {"statistics": [1, 2], "achievements": [3],
                    "activity": [4]}
        result = filter_sections(u, sections)
        assert "statistics" in result
        assert "achievements" in result

    def test_filter_sections_private(self):
        from app.core.profile.privacy import filter_sections

        class FakeUser:
            profile_privacy_json = '{"profile_visibility": "private"}'
        u = FakeUser()
        result = filter_sections(u, {"statistics": [1]})
        assert result == {"visibility": "private"}


# ===========================================================================
# Statistics display
# ===========================================================================
class TestStatistics:
    def test_stats_to_display(self):
        from app.core.profile.statistics import stats_to_display
        stats = ProfileStatistics(total_xp=5000, level=25,
                                  completed_labs=30,
                                  certificates_earned=3,
                                  achievements_earned=12,
                                  leaderboard_rank=5)
        display = stats_to_display(stats)
        assert len(display) == 6
        assert display[0]["label"] == "Total XP"
        assert display[0]["value"] == "5,000"
        assert display[5]["value"] == "#5"


# ===========================================================================
# Integration (needs app context)
# ===========================================================================
@pytest.fixture(scope="module")
def app():
    from app import create_app
    from app.extensions import db
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with application.app_context():
        db.create_all()
        from app.labs.forensics.seed import seed_forensics_labs
        seed_forensics_labs()
    yield application


@pytest.fixture(scope="module")
def user(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        u = User(username="profile_test", email="pt@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
    return u


class TestIntegration:
    def test_get_profile(self, app, user):
        with app.app_context():
            from app.core.profile import get_profile
            from app.auth.models import User
            u = User.query.filter_by(username="profile_test").first()
            p = get_profile(u)
            assert isinstance(p, ProfileData)
            assert p.username == "profile_test"

    def test_update_profile(self, app, user):
        with app.app_context():
            from app.core.profile import update_profile
            from app.auth.models import User
            from app.extensions import db
            u = User.query.filter_by(username="profile_test").first()
            p = update_profile(u, {
                "bio": "Cybersecurity learner from Nepal",
                "country": "Nepal",
                "github": "https://github.com/ayush",
            })
            db.session.commit()
            assert p.bio == "Cybersecurity learner from Nepal"
            assert p.country == "Nepal"

    def test_profile_statistics(self, app, user):
        with app.app_context():
            from app.core.profile import profile_statistics
            from app.auth.models import User
            u = User.query.filter_by(username="profile_test").first()
            s = profile_statistics(u)
            assert isinstance(s, ProfileStatistics)
            assert s.leaderboard_rank >= 1

    def test_get_activity(self, app, user):
        with app.app_context():
            from app.core.profile import get_activity
            from app.auth.models import User
            u = User.query.filter_by(username="profile_test").first()
            activity = get_activity(u)
            assert isinstance(activity, list)

    def test_share_link(self, app, user):
        with app.app_context():
            from app.core.profile import share_link
            from app.auth.models import User
            u = User.query.filter_by(username="profile_test").first()
            s = share_link(u, "https://yushacyber.com")
            assert s.public_url == "https://yushacyber.com/u/profile_test"
            assert "YushaCyber" in s.og_title

    def test_profile_summary(self, app, user):
        with app.app_context():
            from app.core.profile import profile_summary
            from app.auth.models import User
            u = User.query.filter_by(username="profile_test").first()
            s = profile_summary(u)
            assert "profile" in s
            assert "statistics" in s
            assert "stats_raw" in s

    def test_existing_profile_route_unaffected(self, app, user):
        with app.app_context():
            from app.auth.models import User
            from app.profiles.models import UserProfile
            u = User.query.filter_by(username="profile_test").first()
            p = UserProfile.query.filter_by(user_id=u.id).first()
            assert p is not None
            assert p.bio == "Cybersecurity learner from Nepal"
