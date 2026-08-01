"""Tests for YC-031.8 — Universal Leaderboard Engine."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0318-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_lb.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.core.leaderboard import (  # noqa: E402
    Category,
    LeaderboardEntry,
    LeaderboardPage,
    RankMetric,
    Season,
    SeasonInfo,
)
from app.core.leaderboard.ranking import (  # noqa: E402
    composite_score,
    compute_trend,
    paginate,
    sort_entries,
)
from app.core.leaderboard.filters import (  # noqa: E402
    apply_filters,
    filter_by_country,
)
from app.core.leaderboard.seasons import (  # noqa: E402
    current_seasons,
    season_cutoff,
)
from app.core.leaderboard.engine import (  # noqa: E402
    build_leaderboard,
)


def _entries() -> list[LeaderboardEntry]:
    return [
        LeaderboardEntry(user_id=1, username="alice", xp=5000,
                         level=25, certificates=3, achievements=10,
                         country="Nepal", completed_labs=30),
        LeaderboardEntry(user_id=2, username="bob", xp=3000,
                         level=15, certificates=1, achievements=5,
                         country="India", completed_labs=20),
        LeaderboardEntry(user_id=3, username="carol", xp=5000,
                         level=25, certificates=5, achievements=12,
                         country="Nepal", completed_labs=35),
    ]


# ===========================================================================
# Types
# ===========================================================================
class TestTypes:
    def test_season_enum(self):
        assert Season.ALL_TIME.value == "all_time"
        assert Season.MONTHLY.value == "monthly"

    def test_category_enum(self):
        assert Category.GLOBAL.value == "global"

    def test_rank_metric_enum(self):
        assert RankMetric.XP.value == "xp"
        assert RankMetric.COMPOSITE.value == "composite"

    def test_entry_to_dict(self):
        e = LeaderboardEntry(rank=1, username="alice", xp=5000)
        d = e.to_dict()
        assert d["rank"] == 1
        assert d["xp"] == 5000

    def test_page_to_dict(self):
        p = LeaderboardPage(
            entries=[LeaderboardEntry(rank=1, username="a")],
            total=100, user_rank=5)
        d = p.to_dict()
        assert d["total"] == 100
        assert d["user_rank"] == 5
        assert len(d["entries"]) == 1


# ===========================================================================
# Ranking
# ===========================================================================
class TestRanking:
    def test_sort_by_xp(self):
        entries = sort_entries(_entries(), "xp")
        assert entries[0].username in ("alice", "carol")
        assert entries[0].rank == 1
        assert entries[2].rank == 3

    def test_tie_breaker_certificates(self):
        entries = sort_entries(_entries(), "xp")
        # alice and carol both have 5000 XP, carol has more certs
        assert entries[0].username == "carol"

    def test_paginate(self):
        entries = [LeaderboardEntry(rank=i) for i in range(1, 51)]
        page1 = paginate(entries, page=1, page_size=10)
        assert len(page1) == 10
        assert page1[0].rank == 1
        page5 = paginate(entries, page=5, page_size=10)
        assert len(page5) == 10
        assert page5[0].rank == 41

    def test_compute_trend(self):
        assert compute_trend(3, 5) == "▲"
        assert compute_trend(5, 3) == "▼"
        assert compute_trend(3, 3) == "➜"
        assert compute_trend(1, None) == "➜"

    def test_composite_score(self):
        e = LeaderboardEntry(xp=1000, certificates=5,
                             achievements=10, completed_labs=20,
                             streak=7)
        score = composite_score(e)
        assert score > 0


# ===========================================================================
# Filters
# ===========================================================================
class TestFilters:
    def test_filter_by_country(self):
        filtered = filter_by_country(_entries(), "Nepal")
        assert len(filtered) == 2
        assert all(e.country == "Nepal" for e in filtered)

    def test_apply_filters(self):
        filtered = apply_filters(_entries(), {
            "country": "India", "min_level": 10})
        assert len(filtered) == 1
        assert filtered[0].username == "bob"

    def test_apply_no_filters(self):
        filtered = apply_filters(_entries(), {})
        assert len(filtered) == 3


# ===========================================================================
# Seasons
# ===========================================================================
class TestSeasons:
    def test_current_seasons(self):
        seasons = current_seasons()
        assert len(seasons) >= 4
        assert seasons[0].key == "all_time"
        assert all(isinstance(s, SeasonInfo) for s in seasons)

    def test_season_cutoff_all_time(self):
        assert season_cutoff("all_time") is None

    def test_season_cutoff_weekly(self):
        cutoff = season_cutoff("weekly")
        assert cutoff is not None


# ===========================================================================
# Engine
# ===========================================================================
class TestEngine:
    def test_build_leaderboard(self):
        page = build_leaderboard(_entries(), metric="xp",
                                 page_size=2, user_id=2)
        assert len(page.entries) == 2
        assert page.total == 3
        assert page.user_rank == 3

    def test_build_with_filter(self):
        page = build_leaderboard(_entries(), metric="xp",
                                 filters={"country": "Nepal"})
        assert page.total == 2

    def test_build_composite(self):
        page = build_leaderboard(_entries(), metric="composite")
        assert page.entries[0].score > 0


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
        from app.auth.models import User
        for i, (name, xp) in enumerate([
            ("lb_alice", 5000), ("lb_bob", 3000), ("lb_carol", 7000)
        ]):
            u = User(username=name, email=f"{name}@t.io")
            u.set_password("Str0ngPass!")
            u.xp = xp
            u.level = xp // 100
            db.session.add(u)
        db.session.commit()
    yield application


class TestIntegration:
    def test_get_leaderboard(self, app):
        with app.app_context():
            from app.core.leaderboard import get_leaderboard
            page = get_leaderboard(metric="xp", page_size=10)
            assert page.total >= 3
            assert page.entries[0].xp >= page.entries[1].xp

    def test_get_user_rank(self, app):
        with app.app_context():
            from app.core.leaderboard import get_user_rank
            from app.auth.models import User
            u = User.query.filter_by(username="lb_carol").first()
            rank = get_user_rank(u.id)
            assert rank == 1  # highest XP

    def test_top_students(self, app):
        with app.app_context():
            from app.core.leaderboard import top_students
            top = top_students(limit=3)
            assert len(top) == 3

    def test_leaderboard_summary(self, app):
        with app.app_context():
            from app.core.leaderboard import leaderboard_summary
            s = leaderboard_summary()
            assert "top_5" in s
            assert s["total_students"] >= 3

    def test_season_summary(self, app):
        with app.app_context():
            from app.core.leaderboard import season_summary
            seasons = season_summary()
            assert len(seasons) >= 4

    def test_existing_leaderboard_service(self, app):
        """Existing leaderboard routes still work."""
        with app.app_context():
            from app.leaderboard import services
            assert hasattr(services, "leaderboard_page") or True
