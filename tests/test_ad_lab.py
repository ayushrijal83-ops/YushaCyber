"""Active Directory Security Lab tests (YC-031.0).

Two layers, mirroring the architecture:

  · Pure engine tests — no app, no DB: domain schema validation, the
    directory build, every account/group/policy/permission operation
    and the Kerberos flow branches.
  · Integration tests — a throwaway SQLite app: seed shape, the five
    lab flows end-to-end through the real Lab Engine (objectives, XP,
    achievements, certificate), the explorer HTTP surface, and the
    admin Domain Builder.

Run:  python -m pytest tests/test_ad_lab.py -q
"""

from __future__ import annotations

import json
import os
import tempfile

# The database override MUST precede any `app` import: config.py resolves
# DATABASE_URL at import time, and the project tree may carry a real
# instance/yushacyber.db that tests must never touch.
_TMPDIR = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_ad.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.labs.ad import (  # noqa: E402
    domains,
    engine,
    group_engine,
    permission_engine,
    policy_engine,
    user_engine,
)
from app.labs.ad.simulator import ADSimulator  # noqa: E402
from app.labs.simulator_base import Action  # noqa: E402


# ===========================================================================
# Pure engine tests
# ===========================================================================
def _fresh_state():
    return ADSimulator().bootstrap(None, {})


def _run(sim, state, cmd):
    result = sim.handle(state, Action(type="command",
                                      payload={"command": cmd}))
    return result, result.new_state


class TestDomainDefinition:
    def test_builtin_domain_passes_own_schema(self):
        assert domains.validate_domain_def(domains.YUSHA_LOCAL) == []

    def test_validation_catches_unknown_references(self):
        bad = {"key": "x", "name": "X",
               "ous": [{"slug": "a", "name": "A"}],
               "groups": [],
               "users": [{"sam": "u1", "display": "U", "ou": "nope",
                          "groups": ["ghost"]}],
               "computers": [], "shares": [], "gpos": []}
        errors = domains.validate_domain_def(bad)
        assert any("unknown OU" in e for e in errors)
        assert any("unknown group" in e for e in errors)

    def test_validation_catches_duplicates_and_bad_slugs(self):
        bad = {"key": "Bad Key!", "name": "X",
               "ous": [{"slug": "a", "name": "A"}, {"slug": "a", "name": "B"}],
               "groups": [], "users": [], "computers": [],
               "shares": [], "gpos": []}
        errors = domains.validate_domain_def(bad)
        assert any("lowercase slug" in e for e in errors)
        assert any("duplicate slug" in e for e in errors)

    def test_parse_domain_json_round_trip(self):
        definition, errors = domains.parse_domain_json(
            json.dumps(domains.YUSHA_LOCAL))
        assert errors == [] and definition["key"] == "yusha-local"
        definition, errors = domains.parse_domain_json("{not json")
        assert definition is None and errors


class TestDirectory:
    def test_build_directory_shape(self):
        directory = engine.build_directory(domains.YUSHA_LOCAL)
        assert len(directory["users"]) == 10
        assert len(directory["groups"]) == 6
        assert len(directory["ous"]) == 9
        assert len(directory["computers"]) == 5
        assert len(directory["shares"]) == 3
        assert len(directory["gpos"]) == 3
        # membership is two-way consistent
        for slug, group in directory["groups"].items():
            for sam in group["members"]:
                assert slug in directory["users"][sam]["groups"]

    def test_lookups_by_slug_and_display_name(self):
        directory = engine.build_directory(domains.YUSHA_LOCAL)
        assert engine.find_user(directory, "MRAI")["sam"] == "mrai"
        assert engine.find_user(directory, "Manisha Rai")["sam"] == "mrai"
        assert engine.find_group(directory, "Domain Admins")["slug"] == \
            "domain-admins"
        assert engine.find_ou(directory, "Disabled Accounts")["slug"] == \
            "disabled-accounts"
        assert engine.find_share(directory, "HR-Confidential")["slug"] == \
            "hr-confidential"

    def test_explorer_tree(self):
        directory = engine.build_directory(domains.YUSHA_LOCAL)
        tree = engine.explorer_tree(directory)
        assert len(tree["ous"]) == 9 and len(tree["groups"]) == 6
        it_ou = next(o for o in tree["ous"] if o["slug"] == "it")
        assert any(u["sam"] == "skhadka" for u in it_ou["users"])
        dc_ou = next(o for o in tree["ous"] if o["slug"] == "domain-controllers")
        assert dc_ou["computers"][0]["is_dc"] is True


class TestPolicyEngine:
    def setup_method(self):
        self.directory = engine.build_directory(domains.YUSHA_LOCAL)

    def test_effective_policies_come_from_gpo(self):
        assert policy_engine.get_password_policy(self.directory)["min_length"] == 12
        assert policy_engine.get_lockout_policy(self.directory)["threshold"] == 5

    def test_password_rules(self):
        ok, problems = policy_engine.check_password(self.directory, "mrai", "short")
        assert not ok and any("too short" in p for p in problems)
        ok, problems = policy_engine.check_password(
            self.directory, "mrai", "alllowercaseletters")
        assert not ok and any("complex" in p for p in problems)
        ok, problems = policy_engine.check_password(
            self.directory, "mrai", "Contains-mrai-2026!")
        assert not ok and any("account name" in p for p in problems)
        ok, problems = policy_engine.check_password(
            self.directory, "mrai", "Str0ng-Autumn26!")
        assert ok and problems == []


class TestUserAndGroupEngines:
    def setup_method(self):
        self.directory = engine.build_directory(domains.YUSHA_LOCAL)

    def test_reset_password_enforces_policy(self):
        result = user_engine.reset_password(self.directory, "mrai", "weak")
        assert not result.ok
        assert result.events[0]["policy_ok"] is False
        result = user_engine.reset_password(self.directory, "mrai",
                                            "Str0ng-Autumn26!")
        assert result.ok and result.events[0]["policy_ok"] is True

    def test_unlock_enable_disable_move(self):
        assert user_engine.unlock_account(self.directory, "mrai").events[0][
            "was_locked"] is True
        assert self.directory["users"]["mrai"]["failed_attempts"] == 0
        result = user_engine.set_enabled(self.directory, "kshrestha", False)
        assert result.events[0]["type"] == "account_disabled"
        result = user_engine.move_user(self.directory, "kshrestha",
                                       "Disabled Accounts")
        assert result.events[0]["ou"] == "disabled-accounts"
        assert self.directory["users"]["kshrestha"]["ou"] == "disabled-accounts"

    def test_group_membership_operations(self):
        result = group_engine.remove_member(self.directory, "Domain Admins",
                                            "intern01")
        assert result.ok and result.events[0]["privileged"] is True
        assert "intern01" not in \
            self.directory["groups"]["domain-admins"]["members"]
        assert "domain-admins" not in \
            self.directory["users"]["intern01"]["groups"]
        # primary group is protected
        result = group_engine.remove_member(self.directory, "Domain Users",
                                            "intern01")
        assert not result.ok

    def test_overprivileged_analysis_flags_the_intern(self):
        flagged = group_engine.overprivileged_members(self.directory)
        assert any(f["sam"] == "intern01" for f in flagged)


class TestPermissionEngine:
    def setup_method(self):
        self.directory = engine.build_directory(domains.YUSHA_LOCAL)

    def test_hr_confidential_audit_finding(self):
        result = permission_engine.check_access(self.directory, "dtamang",
                                                "hr-confidential")
        event = result.events[0]
        assert event["allowed"] and event["via_domain_users"]
        assert "AUDIT FINDING" in result.message

    def test_revoke_restores_least_privilege(self):
        permission_engine.revoke_access(self.directory, "hr-confidential",
                                        "Domain Users")
        denied = permission_engine.check_access(self.directory, "dtamang",
                                                "hr-confidential")
        assert denied.events[0]["allowed"] is False
        kept = permission_engine.check_access(self.directory, "lbasnet",
                                              "hr-confidential")
        assert kept.events[0]["allowed"] is True

    def test_locked_and_disabled_accounts_cannot_authenticate(self):
        locked = permission_engine.check_access(self.directory, "mrai",
                                                "public")
        assert locked.events[0]["allowed"] is False
        flow = permission_engine.kerberos_flow(self.directory, "mrai")
        assert "KDC_ERR_CLIENT_REVOKED" in flow.message
        assert flow.events[0]["reason"] == "locked"
        user_engine.set_enabled(self.directory, "dtamang", False)
        flow = permission_engine.kerberos_flow(self.directory, "dtamang")
        assert flow.events[0]["reason"] == "disabled"

    def test_healthy_kerberos_flow(self):
        flow = permission_engine.kerberos_flow(self.directory, "skhadka")
        assert flow.events[0]["ok"] is True
        for marker in ("AS-REQ", "TGT", "TGS-REQ", "AP-REQ"):
            assert marker in flow.message


class TestSimulator:
    def test_bootstrap_and_ui_contract(self):
        sim = ADSimulator()
        state = sim.bootstrap(None, {})
        assert state["sim"] == "ad" and "directory" in state
        assert sim.prompt(state) == "PS YUSHA\\admin> "
        assert sim.describe_ui()["ad"] is True
        assert len(sim.status_panel(state)) == 6

    def test_command_events_and_state_mutation(self):
        sim = ADSimulator()
        state = sim.bootstrap(None, {})
        result, state = _run(sim, state, "get-users")
        assert any(e["type"] == "users_viewed" for e in result.events)
        result, state = _run(sim, state, "disable kshrestha")
        assert not state["directory"]["users"]["kshrestha"]["enabled"]
        result, state = _run(sim, state, "nonsense-verb")
        assert "not recognized" in result.output
        result, state = _run(sim, state, 'members "Domain Admins"')
        assert any(e["type"] == "group_members_viewed"
                   and e["member_count"] == 2 for e in result.events)

    def test_select_action_mirrors_get_commands(self):
        sim = ADSimulator()
        state = sim.bootstrap(None, {})
        result = sim.handle(state, Action(
            type="select", payload={"object": "user:mrai"}))
        assert "Manisha Rai" in result.output
        assert any(e["type"] == "object_selected" for e in result.events)
        assert result.new_state["selected"] == "user:mrai"

    def test_not_contains_validator(self):
        from app.labs.validator import ValidationContext, validate
        sim = ADSimulator()
        state = sim.bootstrap(None, {})
        _, state = _run(sim, state, 'remove-member "Domain Admins" intern01')
        ctx = ValidationContext(action=Action(type="command"), state=state)
        spec = {"path": "directory.groups.domain-admins.members",
                "not_contains": "intern01"}
        assert validate("state_flag", spec, ctx)
        spec["not_contains"] = "administrator"
        assert not validate("state_flag", spec, ctx)


# ===========================================================================
# Integration tests (throwaway SQLite app)
# ===========================================================================
@pytest.fixture(scope="module")
def app():
    from app import create_app
    from app.extensions import db
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with application.app_context():
        db.create_all()
        from app.labs.seed import seed_labs
        seed_labs()
        seed_labs()  # idempotency
    # Context is CLOSED before yielding — a context held open across tests
    # would pin one session whose identity map serves stale rows to every
    # request the test client makes.
    yield application


@pytest.fixture(scope="module")
def student(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        user = User(username="ad_tester", email="ad@test.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "ad_tester"  # a handle, not a live ORM object


FLOWS = {
    "ad-orientation": ["get-users", "get-groups", "get-ous",
                       "get-computer dc-01", "get-shares",
                       "kerberos skhadka"],
    "ad-inactive-account": ["get-users", "get-user kshrestha",
                            "disable kshrestha",
                            'move kshrestha "Disabled Accounts"',
                            "kerberos kshrestha"],
    "ad-compromised-password": ["policy", "get-user mrai",
                                "reset-password mrai Str0ng-Autumn26!",
                                "unlock mrai", "kerberos mrai"],
    "ad-overprivileged": ['members "Domain Admins"', "get-user intern01",
                          'remove-member "Domain Admins" intern01',
                          'members "Domain Admins"'],
    "ad-least-privilege": ["get-shares", "access dtamang hr-confidential",
                           'revoke-access hr-confidential "Domain Users"',
                           "access dtamang hr-confidential", "gpos"],
}


class TestSeedShape:
    def test_track_shape(self, app):
        with app.app_context():
            from app.achievement.models import Achievement
            from app.certificates.models import Certificate
            from app.labs.models import Lab, LabCategory, LabObjective
            category = LabCategory.query.filter_by(
                slug="active-directory").first()
            assert category is not None
            labs = (Lab.query.filter_by(category_id=category.id)
                    .order_by(Lab.display_order).all())
            assert [lab.slug for lab in labs] == list(FLOWS)
            assert LabObjective.query.join(Lab).filter(
                Lab.category_id == category.id).count() == 25
            assert labs[0].prerequisite_lab_id is None
            for previous, lab in zip(labs, labs[1:]):
                assert lab.prerequisite_lab_id == previous.id
            assert Achievement.query.filter_by(
                condition_type="ad_labs_completed").count() == 3
            certificate = Certificate.query.filter_by(
                slug="ad-security-fundamentals").first()
            assert certificate is not None
            assert certificate.required_labs.split(",") == list(FLOWS)


class TestFullTrack:
    def test_five_labs_xp_achievements_certificate(self, app, student):
        with app.app_context(), app.test_request_context():
            from app.achievement.models import UserAchievement
            from app.auth.models import User
            from app.certificates.models import Certificate, UserCertificate
            from app.labs import lab_services
            from app.labs.models import Lab

            user = User.query.filter_by(username="ad_tester").first()
            xp_before = user.xp or 0
            for slug, commands in FLOWS.items():
                lab = Lab.query.filter_by(slug=slug).first()
                for i, command in enumerate(commands):
                    result = lab_services.execute_action(
                        user, lab, "command", {"command": command})
                    assert result["ok"], (slug, command, result)
                    if i < len(commands) - 1:
                        assert not result["lab_completed"], (slug, command)
                assert result["lab_completed"], slug

            user = User.query.filter_by(username="ad_tester").first()
            assert (user.xp or 0) - xp_before > 1500

            titles = {ua.achievement.title for ua in
                      UserAchievement.query.filter_by(user_id=user.id)}
            assert {"Domain Explorer", "Identity Defender",
                    "Least Privilege Champion"} <= titles

            issued = (UserCertificate.query.filter_by(user_id=user.id)
                      .join(Certificate)
                      .filter(Certificate.slug == "ad-security-fundamentals")
                      .first())
            assert issued is not None


class TestHTTPSurface:
    def _login(self, app):
        client = app.test_client()
        client.post("/auth/login",
                    data={"identifier": "ad_tester",
                          "password": "Str0ngPass!"},
                    follow_redirects=True)
        return client

    def test_workspace_renders_explorer(self, app, student):
        client = self._login(app)
        response = client.get("/labs/ad-orientation")
        assert response.status_code == 200
        assert b'id="adx"' in response.data
        assert b"ad_explorer.js" in response.data
        assert b"ad_explorer.css" in response.data

    def test_ad_state_endpoint(self, app, student):
        client = self._login(app)
        data = client.get("/labs/ad-orientation/ad/state").get_json()
        assert len(data["tree"]["ous"]) == 9
        # 404s for non-AD labs
        with app.app_context():
            from app.labs.models import Lab
            other = Lab.query.filter(Lab.simulator_key != "ad",
                                     Lab.is_interactive.is_(True)).first()
            slug = other.slug
        assert client.get(f"/labs/{slug}/ad/state").status_code == 404

    def test_admin_domain_builder(self, app, student):
        with app.app_context():
            from app.auth.models import User
            from app.extensions import db
            user = User.query.filter_by(username="ad_tester").first()
            user.is_admin = True
            db.session.commit()
        client = self._login(app)
        assert b"YUSHA.LOCAL" in client.get("/admin/ad").data
        assert b"yusha-local-copy" in \
            client.get("/admin/ad/new?from=yusha-local").data
        # invalid definition rejected with 400
        bad = client.post("/admin/ad/new",
                          data={"definition_json": '{"key": "x!", "name": ""}'})
        assert bad.status_code == 400
        # valid definition persists and resolves through the loader
        definition = {"key": "corp-local", "name": "CORP.LOCAL",
                      "netbios": "CORP",
                      "ous": [{"slug": "staff", "name": "Staff"}],
                      "groups": [{"slug": "domain-users",
                                  "name": "Domain Users", "builtin": True}],
                      "users": [{"sam": "alice", "display": "Alice",
                                 "ou": "staff", "groups": ["domain-users"]}],
                      "computers": [{"name": "DC-01", "ou": "staff",
                                     "os": "WS2022", "ip": "10.1.1.1",
                                     "is_dc": True}],
                      "shares": [], "gpos": []}
        response = client.post(
            "/admin/ad/new",
            data={"definition_json": json.dumps(definition)},
            follow_redirects=True)
        assert response.status_code == 200 and b"CORP.LOCAL" in response.data
        with app.app_context():
            from app.labs.ad.domains import get_domain
            assert get_domain("corp-local")["name"] == "CORP.LOCAL"
