"""Cloud Security Lab tests (YC-032.0).

Two layers, mirroring the architecture:

  · Pure engine tests — no app, no DB: account schema validation, the
    deployment build, the audit, and every IAM / storage / networking /
    policy operation the labs rely on.
  · Integration tests — a throwaway SQLite app: seed shape, the six
    lab flows end-to-end through the real Lab Engine (objectives, XP,
    achievements, certificate), the console HTTP surface, and the
    admin Scenario Builder.

Run:  python -m pytest tests/test_cloud_lab.py -q
"""

from __future__ import annotations

import json
import os
import tempfile

# The database override MUST precede any `app` import: config.py resolves
# DATABASE_URL at import time, and the project tree may carry a real
# instance/yushacyber.db that tests must never touch.
_TMPDIR = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_cloud.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from app.labs.cloud import (  # noqa: E402
    accounts,
    engine,
    iam_engine,
    network_engine,
    policy_engine,
    storage_engine,
)
from app.labs.cloud.simulator import CloudSimulator  # noqa: E402
from app.labs.simulator_base import Action  # noqa: E402


# ===========================================================================
# Pure engine tests
# ===========================================================================
def _fresh_state():
    return CloudSimulator().bootstrap(None, {})


def _deployment():
    return engine.build_deployment(accounts.YUSHACLOUD_PROD)


def _run(sim, state, cmd):
    result = sim.handle(state, Action(type="command",
                                      payload={"command": cmd}))
    return result, result.new_state


class TestAccountDefinition:
    def test_builtin_account_passes_own_schema(self):
        assert accounts.validate_account_def(accounts.YUSHACLOUD_PROD) == []

    def test_validation_catches_unknown_references(self):
        bad = {"key": "x", "name": "X",
               "roles": [{"slug": "dev", "name": "Dev",
                          "permissions": ["compute:read"]}],
               "iam_users": [{"username": "u1", "roles": ["ghost"]}],
               "buckets": [],
               "vpcs": [{"slug": "v", "name": "v", "subnets":
                         [{"slug": "s1", "cidr": "10.0.1.0/24"}]}],
               "security_groups": [{"slug": "g1", "name": "g1",
                                    "rules": []}],
               "vms": [{"slug": "m1", "subnet": "nope",
                        "security_group": "ghost-sg"}],
               "load_balancers": [{"slug": "lb1", "targets": ["ghost-vm"]}],
               "databases": [{"slug": "d1", "subnet": "nope",
                              "security_group": "ghost-sg"}]}
        errors = accounts.validate_account_def(bad)
        assert any("unknown role" in e for e in errors)
        assert any("unknown subnet" in e for e in errors)
        assert any("unknown security group" in e for e in errors)
        assert any("unknown target" in e for e in errors)

    def test_validation_catches_duplicates_bad_slugs_and_permissions(self):
        bad = {"key": "Bad Key!", "name": "X",
               "roles": [{"slug": "r1", "permissions": ["nonsense"]},
                         {"slug": "r1", "permissions": []}],
               "iam_users": [], "buckets": [], "vpcs": [],
               "security_groups": [{"slug": "g1", "rules":
                                    [{"direction": "sideways",
                                      "port": "eighty"}]}],
               "vms": [], "load_balancers": [], "databases": []}
        errors = accounts.validate_account_def(bad)
        assert any("lowercase slug" in e for e in errors)
        assert any("duplicate slug" in e for e in errors)
        assert any("bad permission" in e for e in errors)
        assert any("ingress or egress" in e for e in errors)
        assert any("integer" in e for e in errors)

    def test_parse_account_json_round_trip(self):
        raw = json.dumps(accounts.YUSHACLOUD_PROD)
        definition, errors = accounts.parse_account_json(raw)
        assert errors == []
        assert definition["key"] == "yushacloud-prod"
        definition, errors = accounts.parse_account_json("{not json")
        assert definition is None
        assert any("Invalid JSON" in e for e in errors)


class TestDeploymentAndAudit:
    def test_build_deployment_shape(self):
        deployment = _deployment()
        assert len(deployment["users"]) == 7
        assert len(deployment["buckets"]) == 3
        assert len(deployment["security_groups"]) == 3
        assert len(deployment["databases"]) == 2
        assert deployment["account"]["region"] == "np-ktm-1"

    def test_audit_finds_all_six_planted_findings(self):
        findings = engine.audit_findings(_deployment())
        assert len(findings["public_buckets"]) == 1     # customer-backups
        assert len(findings["excessive_iam"]) == 1      # dev-sita
        assert len(findings["open_ssh"]) == 1           # web-sg
        assert len(findings["public_dbs"]) == 1         # customers-db
        assert len(findings["weak_policy"]) == 1
        assert len(findings["unused_admins"]) == 1      # old-admin

    def test_intended_public_bucket_is_not_a_finding(self):
        deployment = _deployment()
        assert deployment["buckets"]["web-assets"]["public"]
        names = " ".join(engine.audit_findings(deployment)["public_buckets"])
        assert "web-assets" not in names

    def test_lookup_by_slug_and_name_case_insensitive(self):
        deployment = _deployment()
        assert engine.find_user(deployment, "DEV-SITA") is not None
        assert engine.find_bucket(deployment, "Customer-Backups") is not None
        assert engine.find_db(deployment, "customers-db") is not None
        assert engine.find_vm(deployment, "no-such") is None


class TestIAMEngine:
    def test_detach_admin_clears_excessive_finding(self):
        deployment = _deployment()
        result = iam_engine.detach_role(deployment, "dev-sita",
                                        "administrator")
        assert result.ok
        assert engine.audit_findings(deployment)["excessive_iam"] == []
        assert deployment["users"]["dev-sita"]["roles"] == ["developer"]

    def test_detach_refuses_removing_last_role(self):
        deployment = _deployment()
        result = iam_engine.detach_role(deployment, "old-admin",
                                        "administrator")
        assert not result.ok
        assert "at least one role" in result.message

    def test_create_attach_and_duplicate_guards(self):
        deployment = _deployment()
        assert iam_engine.create_user(deployment, "new-dev",
                                      "developer").ok
        assert not iam_engine.create_user(deployment, "new-dev",
                                          "developer").ok
        result = iam_engine.attach_role(deployment, "new-dev", "auditor")
        assert result.ok
        assert not iam_engine.attach_role(deployment, "new-dev",
                                          "auditor").ok

    def test_simulate_permission_wildcards_and_disabled(self):
        deployment = _deployment()
        allowed = iam_engine.simulate_permission(
            deployment, "dev-sita", "iam:delete-user")
        assert allowed.events[0]["allowed"] is True         # admin pre-fix
        iam_engine.detach_role(deployment, "dev-sita", "administrator")
        denied = iam_engine.simulate_permission(
            deployment, "dev-sita", "iam:delete-user")
        assert denied.events[0]["allowed"] is False
        still = iam_engine.simulate_permission(
            deployment, "dev-sita", "compute:start")
        assert still.events[0]["allowed"] is True           # developer role
        iam_engine.set_user_enabled(deployment, "dev-sita", False)
        blocked = iam_engine.simulate_permission(
            deployment, "dev-sita", "compute:start")
        assert blocked.events[0]["allowed"] is False

    def test_disable_and_key_deactivation_clear_unused_admin(self):
        deployment = _deployment()
        assert iam_engine.set_user_enabled(deployment, "old-admin",
                                           False).ok
        assert iam_engine.deactivate_access_key(deployment,
                                                "old-admin").ok
        assert not iam_engine.deactivate_access_key(deployment,
                                                    "old-admin").ok
        assert engine.audit_findings(deployment)["unused_admins"] == []


class TestStorageEngine:
    def test_secured_event_only_on_inspection(self):
        deployment = _deployment()
        made_private = storage_engine.set_public(deployment,
                                                 "customer-backups", False)
        assert made_private.ok
        assert not any(e["type"] == "bucket_secured"
                       for e in made_private.events)
        encrypted = storage_engine.enable_encryption(deployment,
                                                     "customer-backups")
        assert encrypted.ok
        assert not any(e["type"] == "bucket_secured"
                       for e in encrypted.events)
        events = storage_engine.bucket_events(
            deployment["buckets"]["customer-backups"])
        assert any(e["type"] == "bucket_secured"
                   and e["bucket"] == "customer-backups" for e in events)

    def test_half_remediated_bucket_is_not_secured(self):
        deployment = _deployment()
        storage_engine.set_public(deployment, "customer-backups", False)
        events = storage_engine.bucket_events(
            deployment["buckets"]["customer-backups"])
        assert not any(e["type"] == "bucket_secured" for e in events)

    def test_versioning_and_public_guard(self):
        deployment = _deployment()
        assert storage_engine.enable_versioning(deployment,
                                                "customer-backups").ok
        assert not storage_engine.enable_versioning(deployment,
                                                    "app-releases").ok
        warned = storage_engine.set_public(deployment, "app-releases", True)
        assert warned.ok and "PUBLIC" in warned.message


class TestNetworkEngine:
    def test_revoke_ssh_clears_open_ssh_finding(self):
        deployment = _deployment()
        result = network_engine.revoke_ingress(deployment, "web-sg", 22)
        assert result.ok
        assert engine.audit_findings(deployment)["open_ssh"] == []
        assert not network_engine.revoke_ingress(deployment,
                                                 "web-sg", 22).ok

    def test_db_needs_both_paths_closed(self):
        deployment = _deployment()
        network_engine.set_db_public(deployment, "customers-db", False)
        assert engine.audit_findings(deployment)["public_dbs"]  # SG open
        revoked = network_engine.revoke_ingress(deployment, "db-sg", 5432)
        assert engine.audit_findings(deployment)["public_dbs"] == []
        assert any(e["type"] == "db_secured" and e["db"] == "customers-db"
                   for e in revoked.events)

    def test_allow_ingress_warns_on_world_open(self):
        deployment = _deployment()
        result = network_engine.allow_ingress(deployment, "app-sg", 3389,
                                              "0.0.0.0/0")
        assert result.ok and "ENTIRE INTERNET" in result.message
        assert result.events[0]["world_open"] is True


class TestPolicyEngine:
    def test_strong_requires_length_and_mfa(self):
        policy = {"min_length": 6, "mfa_required": False}
        assert not policy_engine.policy_strong(policy)
        policy_engine.update_policy(policy, "min-length", "14")
        assert not policy_engine.policy_strong(policy)
        result = policy_engine.update_policy(policy, "require-mfa", "on")
        assert policy_engine.policy_strong(policy)
        assert result.events[0]["strong"] is True

    def test_update_policy_rejects_garbage(self):
        policy = {"min_length": 6}
        assert not policy_engine.update_policy(policy, "min-length",
                                               "tall").ok
        assert not policy_engine.update_policy(policy, "require-mfa",
                                               "maybe").ok
        assert not policy_engine.update_policy(policy, "colour",
                                               "green").ok

    def test_risk_library_covers_all_six_scenarios(self):
        for topic in ("public-bucket", "over-permissive-iam", "open-ssh",
                      "public-database", "weak-password-policy",
                      "unused-admin"):
            result = policy_engine.format_risk(topic)
            assert result.ok
            assert result.events[0] == {"type": "risk_reviewed",
                                        "topic": topic}
        assert not policy_engine.format_risk("meteor-strike").ok


class TestSimulator:
    def test_unknown_command_and_parse_error(self):
        sim = CloudSimulator()
        state = _fresh_state()
        result, state = _run(sim, state, "terraform apply")
        assert "not recognized" in result.output
        result, _ = _run(sim, state, 'get-user "unclosed')
        assert "Parse error" in result.output

    def test_audit_event_carries_per_class_counts(self):
        sim = CloudSimulator()
        state = _fresh_state()
        result, _ = _run(sim, state, "audit")
        event = next(e for e in result.events if e["type"] == "audit_run")
        assert event["total"] == 6
        assert event["excessive_iam"] == 1
        assert event["hardening_findings"] == 2

    def test_select_action_mirrors_command(self):
        sim = CloudSimulator()
        state = _fresh_state()
        result = sim.handle(state, Action(
            type="select", payload={"object": "bucket:customer-backups"}))
        assert "customer-backups" in result.output
        assert any(e["type"] == "resource_selected" for e in result.events)
        assert any(e["type"] == "bucket_inspected" for e in result.events)
        assert result.new_state["selected"] == "bucket:customer-backups"

    def test_status_panel_tracks_findings(self):
        sim = CloudSimulator()
        state = _fresh_state()
        rows = {r["label"]: r["value"] for r in sim.status_panel(state)}
        assert rows["Open findings"] == "6"
        assert rows["IAM users"] == "7"
        _, state = _run(sim, state, "revoke-ingress web-sg 22")
        rows = {r["label"]: r["value"] for r in sim.status_panel(state)}
        assert rows["Open findings"] == "5"

    def test_describe_ui_flags_cloud_console(self):
        assert CloudSimulator().describe_ui()["cloud"] is True


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
        user = User(username="cloud_tester", email="cloud@test.io")
        user.set_password("Str0ngPass!")
        db.session.add(user)
        db.session.commit()
    yield "cloud_tester"  # a handle, not a live ORM object


FLOWS = {
    "cloud-orientation": ["overview", "list-users", "list-buckets",
                          "network", "list-vms", "audit"],
    "cloud-public-bucket": ["list-buckets", "get-bucket customer-backups",
                            "risk public-bucket",
                            "make-private customer-backups",
                            "encrypt-bucket customer-backups",
                            "get-bucket customer-backups"],
    "cloud-iam-overprivileged": ["list-users", "get-user dev-sita",
                                 "risk over-permissive-iam",
                                 "detach-role dev-sita administrator",
                                 "simulate dev-sita iam:delete-user",
                                 "audit"],
    "cloud-open-ssh": ["list-sgs", "get-sg web-sg", "risk open-ssh",
                       "revoke-ingress web-sg 22", "audit"],
    "cloud-exposed-database": ["list-dbs", "get-db customers-db",
                               "risk public-database",
                               "make-db-private customers-db",
                               "revoke-ingress db-sg 5432", "audit"],
    "cloud-hardening": ["password-policy", "risk weak-password-policy",
                        "set-password-policy min-length 14",
                        "set-password-policy require-mfa on",
                        "get-user old-admin", "risk unused-admin",
                        "disable-user old-admin",
                        "deactivate-key old-admin", "audit"],
}


class TestSeedShape:
    def test_track_shape(self, app):
        with app.app_context():
            from app.achievement.models import Achievement
            from app.certificates.models import Certificate
            from app.labs.models import Lab, LabCategory, LabObjective
            category = LabCategory.query.filter_by(
                slug="cloud-security").first()
            assert category is not None
            labs = (Lab.query.filter_by(category_id=category.id)
                    .order_by(Lab.display_order).all())
            assert [lab.slug for lab in labs] == list(FLOWS)
            assert LabObjective.query.join(Lab).filter(
                Lab.category_id == category.id).count() == 37
            assert labs[0].prerequisite_lab_id is None
            for previous, lab in zip(labs, labs[1:]):
                assert lab.prerequisite_lab_id == previous.id
            assert all(lab.simulator_key == "cloud" for lab in labs)
            assert Achievement.query.filter_by(
                condition_type="cloud_labs_completed").count() == 3
            certificate = Certificate.query.filter_by(
                slug="cloud-security-fundamentals").first()
            assert certificate is not None
            assert certificate.required_labs.split(",") == list(FLOWS)


class TestFullTrack:
    def test_six_labs_xp_achievements_certificate(self, app, student):
        with app.app_context(), app.test_request_context():
            from app.achievement.models import UserAchievement
            from app.auth.models import User
            from app.certificates.models import Certificate, UserCertificate
            from app.labs import lab_services
            from app.labs.models import Lab

            user = User.query.filter_by(username="cloud_tester").first()
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

            user = User.query.filter_by(username="cloud_tester").first()
            assert (user.xp or 0) - xp_before > 3000

            titles = {ua.achievement.title for ua in
                      UserAchievement.query.filter_by(user_id=user.id)}
            assert {"Cloud Explorer", "Cloud Defender",
                    "Cloud Security Architect"} <= titles

            issued = (UserCertificate.query.filter_by(user_id=user.id)
                      .join(Certificate)
                      .filter(Certificate.slug ==
                              "cloud-security-fundamentals")
                      .first())
            assert issued is not None


class TestHTTPSurface:
    def _login(self, app):
        client = app.test_client()
        client.post("/auth/login",
                    data={"identifier": "cloud_tester",
                          "password": "Str0ngPass!"},
                    follow_redirects=True)
        return client

    def test_workspace_renders_cloud_console(self, app, student):
        client = self._login(app)
        page = client.get("/labs/cloud-orientation").data.decode()
        assert 'id="cldx"' in page
        assert "cloud_console.js" in page
        assert "cloud_console.css" in page
        assert "cloudStateUrl" in page

    def test_state_endpoint_reflects_session_mutations(self, app, student):
        client = self._login(app)
        data = client.get(
            "/labs/cloud-orientation/cloud/state").get_json()
        assert data["tree"]["account"]["name"].startswith("YushaCloud")
        bucket = next(b for b in data["tree"]["buckets"]
                      if b["slug"] == "customer-backups")
        assert bucket["public"] is True
        client.post("/labs/cloud-orientation/action",
                    json={"type": "command",
                          "payload":
                          {"command": "make-private customer-backups"}})
        data = client.get(
            "/labs/cloud-orientation/cloud/state").get_json()
        bucket = next(b for b in data["tree"]["buckets"]
                      if b["slug"] == "customer-backups")
        assert bucket["public"] is False

    def test_state_endpoint_404_for_non_cloud_lab(self, app, student):
        client = self._login(app)
        assert client.get(
            "/labs/linux-basics/cloud/state").status_code == 404


class TestAdminScenarioBuilder:
    def _admin_client(self, app):
        from app.auth.models import User
        from app.extensions import db
        with app.app_context():
            admin = User.query.filter_by(username="cloud_admin").first()
            if admin is None:
                admin = User(username="cloud_admin",
                             email="cloud_admin@test.io", is_admin=True)
                admin.set_password("Str0ngPass!")
                db.session.add(admin)
                db.session.commit()
        client = app.test_client()
        client.post("/auth/login",
                    data={"identifier": "cloud_admin",
                          "password": "Str0ngPass!"},
                    follow_redirects=True)
        return client

    def test_list_shows_builtin(self, app):
        client = self._admin_client(app)
        page = client.get("/admin/cloud").data.decode()
        assert "yushacloud-prod" in page
        assert "Clone" in page

    def test_clone_create_shadow_and_delete(self, app):
        client = self._admin_client(app)
        page = client.get(
            "/admin/cloud/new?from=yushacloud-prod").data.decode()
        assert "yushacloud-prod-copy" in page

        definition = dict(accounts.YUSHACLOUD_PROD)
        definition["key"] = "training-cloud-1"
        definition["name"] = "Training Cloud 1"
        response = client.post(
            "/admin/cloud/new",
            data={"definition_json": json.dumps(definition)},
            follow_redirects=True)
        assert response.status_code == 200
        assert "created and validated" in response.data.decode()

        with app.app_context():
            resolved = accounts.get_account("training-cloud-1")
            assert resolved is not None
            assert resolved["name"] == "Training Cloud 1"
            from app.labs.cloud.models import CloudCustomScenario
            row = CloudCustomScenario.query.filter_by(
                key="training-cloud-1").first()
            row_id = row.id

        response = client.post(f"/admin/cloud/{row_id}/delete",
                               follow_redirects=True)
        assert "deleted" in response.data.decode()

    def test_invalid_json_rejected_with_400(self, app):
        client = self._admin_client(app)
        response = client.post("/admin/cloud/new",
                               data={"definition_json": "{broken"})
        assert response.status_code == 400
        response = client.post(
            "/admin/cloud/new",
            data={"definition_json": json.dumps(
                {"key": "BAD KEY", "name": ""})})
        assert response.status_code == 400
