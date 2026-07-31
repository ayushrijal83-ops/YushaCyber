"""Tests for YC-031.4 — Universal Achievement Framework."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0314-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_ach.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.core.achievement import (  # noqa: E402
    AchievementDef,
    Badge,
    Rarity,
    RARITY_COLORS,
    UnlockCondition,
    achievement_from_dict,
    achievement_summary,
    available_rules,
    check_unlock_for_user,
    evaluate_rule,
    generate_badge,
    generate_badges,
    register_achievement,
    get_registered,
    all_registered,
)


# ===========================================================================
# Types
# ===========================================================================
class TestTypes:
    def test_rarity_enum(self):
        assert Rarity.COMMON.value == "common"
        assert Rarity.MYTHIC.value == "mythic"
        assert len(list(Rarity)) == 5

    def test_rarity_colors(self):
        assert RARITY_COLORS["common"] == "#8b95a5"
        assert RARITY_COLORS["mythic"] == "#ef4444"

    def test_unlock_condition_enum(self):
        assert UnlockCondition.PERFECT_SCORE.value == "perfect_score"
        assert UnlockCondition.CUSTOM.value == "custom"

    def test_achievement_def_to_dict(self):
        a = AchievementDef(slug="test", title="Test",
                           rarity="epic", xp_reward=100)
        d = a.to_dict()
        assert d["slug"] == "test"
        assert d["rarity"] == "epic"
        assert d["badge_color"] == RARITY_COLORS["epic"]

    def test_badge_to_dict(self):
        b = Badge(title="B", rarity="rare", icon="🎯")
        assert b.to_dict()["rarity"] == "rare"


# ===========================================================================
# Models
# ===========================================================================
class TestModels:
    def test_from_dict(self):
        a = achievement_from_dict({
            "slug": "test-ach", "title": "Test Achievement",
            "category": "soc", "xp_reward": 50,
            "requirements": [{"type": "lab_completed", "value": 3}],
        })
        assert a.slug == "test-ach"
        assert a.xp_reward == 50
        assert len(a.requirements) == 1


# ===========================================================================
# Rules
# ===========================================================================
class TestRules:
    def test_available_rules(self):
        rules = available_rules()
        assert "lab_completed" in rules
        assert "xp_milestone" in rules
        assert "perfect_score" in rules
        assert len(rules) >= 10

    def test_evaluate_lab_completed(self):
        assert evaluate_rule(
            {"type": "lab_completed", "value": 3},
            {"lab_completed": 5}) is True
        assert evaluate_rule(
            {"type": "lab_completed", "value": 3},
            {"lab_completed": 2}) is False

    def test_evaluate_xp_milestone(self):
        assert evaluate_rule(
            {"type": "xp_milestone", "value": 1000},
            {"total_xp": 1500}) is True
        assert evaluate_rule(
            {"type": "xp_milestone", "value": 1000},
            {"total_xp": 500}) is False

    def test_evaluate_level_milestone(self):
        assert evaluate_rule(
            {"type": "level_milestone", "value": 10},
            {"level": 15}) is True

    def test_evaluate_perfect_score(self):
        assert evaluate_rule(
            {"type": "perfect_score", "value": 1},
            {"perfect_scores": 1}) is True

    def test_evaluate_speed_run(self):
        assert evaluate_rule(
            {"type": "speed_run", "value": 300},
            {"best_time_seconds": 200}) is True
        assert evaluate_rule(
            {"type": "speed_run", "value": 300},
            {"best_time_seconds": 400}) is False

    def test_evaluate_unknown_rule(self):
        assert evaluate_rule(
            {"type": "nonexistent", "value": 1},
            {}) is False


# ===========================================================================
# Engine — check_unlock
# ===========================================================================
class TestEngine:
    def test_check_unlock_single_req(self):
        ach = AchievementDef(
            slug="test", title="T",
            requirements=[{"type": "lab_completed", "value": 5}])
        assert check_unlock_for_user(
            ach, {"lab_completed": 5}).unlocked is True
        assert check_unlock_for_user(
            ach, {"lab_completed": 3}).unlocked is False

    def test_check_unlock_multiple_reqs(self):
        ach = AchievementDef(
            slug="multi", title="Multi",
            requirements=[
                {"type": "lab_completed", "value": 3},
                {"type": "xp_milestone", "value": 500},
            ])
        assert check_unlock_for_user(
            ach, {"lab_completed": 5, "total_xp": 600}).unlocked is True
        assert check_unlock_for_user(
            ach, {"lab_completed": 5, "total_xp": 400}).unlocked is False

    def test_check_unlock_empty_reqs(self):
        ach = AchievementDef(slug="empty", title="E")
        assert check_unlock_for_user(ach, {}).unlocked is True


# ===========================================================================
# Badges
# ===========================================================================
class TestBadges:
    def test_generate_badge(self):
        ach = AchievementDef(slug="b1", title="Badge One",
                             rarity="legendary", icon="🔥")
        badge = generate_badge(ach, "2026-07-28")
        assert badge.title == "Badge One"
        assert badge.rarity == "legendary"
        assert badge.color == RARITY_COLORS["legendary"]
        assert badge.unlocked_at == "2026-07-28"

    def test_generate_badges_locked(self):
        achs = [
            AchievementDef(slug="a1", title="A1", rarity="common"),
            AchievementDef(slug="a2", title="A2", rarity="rare"),
        ]
        badges = generate_badges(achs, unlocked_slugs={"a1"})
        assert badges[0].icon != "🔒"
        assert badges[1].icon == "🔒"

    def test_generate_badges_hidden(self):
        achs = [AchievementDef(slug="h1", title="Hidden",
                                hidden=True)]
        badges = generate_badges(achs, unlocked_slugs=set())
        assert badges[0].icon == "❓"
        assert badges[0].description == "???"


# ===========================================================================
# Registry
# ===========================================================================
class TestRegistry:
    def test_register_and_get(self):
        ach = AchievementDef(slug="reg-test", title="Reg Test")
        register_achievement(ach)
        assert get_registered("reg-test") is not None
        assert get_registered("reg-test").title == "Reg Test"

    def test_all_registered(self):
        ach = AchievementDef(slug="reg-test-2", title="RT2")
        register_achievement(ach)
        all_achs = all_registered()
        slugs = {a.slug for a in all_achs}
        assert "reg-test-2" in slugs


# ===========================================================================
# Summary
# ===========================================================================
class TestSummary:
    def test_achievement_summary(self):
        achs = [
            AchievementDef(slug="s1", title="Ach1", rarity="common",
                           xp_reward=10, category="lab"),
            AchievementDef(slug="s2", title="Ach2", rarity="epic",
                           xp_reward=50, category="soc"),
            AchievementDef(slug="s3", title="Ach3", rarity="common",
                           xp_reward=25, category="lab"),
        ]
        # Engine uses titles for matching
        summary = achievement_summary(achs,
                                      unlocked_slugs={"Ach1", "Ach3"})
        assert summary["total"] == 3
        assert summary["unlocked"] == 2
        assert summary["locked"] == 1


# ===========================================================================
# Backward compatibility
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


class TestBackwardCompat:
    def test_existing_orm_achievements_still_work(self, app):
        with app.app_context():
            from app.achievement.models import Achievement
            achs = Achievement.query.all()
            assert len(achs) >= 5

    def test_existing_check_and_unlock(self, app):
        with app.app_context():
            from app.achievement.services import check_and_unlock_achievements
            from app.auth.models import User
            from app.extensions import db
            user = User(username="ach_test_314", email="ach314@t.io")
            user.set_password("Str0ngPass!")
            db.session.add(user)
            db.session.commit()
            result = check_and_unlock_achievements(user)
            assert "unlocked" in result

    def test_achievement_from_orm(self, app):
        with app.app_context():
            from app.achievement.models import Achievement
            from app.core.achievement import achievement_from_orm
            orm = Achievement.query.first()
            ach_def = achievement_from_orm(orm)
            assert ach_def.title == orm.title
            assert ach_def.xp_reward == orm.bonus_xp
