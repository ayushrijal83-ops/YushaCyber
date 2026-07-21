"""Cloud Security lab seed (YC-032.0). Idempotent — safe to re-run."""

from __future__ import annotations

from app.achievement.models import Achievement
from app.certificates.models import Certificate
from app.extensions import db
from app.labs.models import Lab, LabCategory, LabObjective, SimulatorEngine


def _obj(title, instruction, vtype, vdata, hints, xp, optional=False):
    return {"title": title, "instruction": instruction,
            "validator_type": vtype, "validator_data": vdata,
            "hints": hints, "xp": xp, "optional": optional}


LABS = [
    ("cloud-orientation", "Cloud Basics: Tour the Account", "Easy", 20, 260, [
        _obj("Open the account dashboard",
             "Get the big picture of what this cloud account runs.",
             "event_emitted", {"event": "overview_viewed"},
             ["Every investigation starts with an inventory.",
              "Run `overview`.",
              "Note the resource counts — you will visit each service."],
             35),
        _obj("Review the IAM identities",
             "List the account's users, their roles and their status.",
             "event_emitted", {"event": "iam_users_viewed"},
             ["Identity is the cloud's real perimeter.",
              "Run `list-users`.",
              "The ⚠ markers in STATUS matter in later labs."], 35),
        _obj("Review the storage buckets",
             "List the buckets and read their access policies.",
             "event_emitted", {"event": "buckets_viewed"},
             ["Buckets are where breaches make headlines.",
              "Run `list-buckets`.",
              "PUBLIC is fine only for content meant to be public."], 35),
        _obj("Map the virtual network",
             "See the VPC, its subnets and the internet gateway.",
             "event_emitted", {"event": "network_viewed"},
             ["Public subnets face the internet; private ones do not.",
              "Run `network`.",
              "Note which tier the databases live in."], 35),
        _obj("Review the virtual machines",
             "List the VMs and see which ones hold public IPs.",
             "event_emitted", {"event": "vms_viewed"},
             ["A public IP means the internet can knock.",
              "Run `list-vms`.",
              "Only the web tier should be internet-facing."], 35),
        _obj("Run your first security audit",
             "Scan the account for misconfigurations.",
             "event_emitted", {"event": "audit_run"},
             ["The scanner checks six classic misconfiguration classes.",
              "Run `audit`.",
              "Each ✖ becomes its own lab in this track."], 45),
    ]),

    ("cloud-public-bucket", "The Public Backup Bucket", "Easy", 20, 280, [
        _obj("Survey the buckets",
             "List the buckets and find the one that should not be public.",
             "event_emitted", {"event": "buckets_viewed"},
             ["Compare each bucket's ACCESS column against its purpose.",
              "Run `list-buckets`.",
              "Backups have no business being PUBLIC."], 35),
        _obj("Confirm the exposure",
             "Inspect the leaking bucket and read what it exposes.",
             "event_emitted", {"event": "bucket_inspected",
                               "key": "exposed", "equals": True},
             ["The bucket description explains how this happened.",
              "Run `get-bucket customer-backups`.",
              "`list-objects customer-backups` shows what is exposed."],
             45),
        _obj("Understand the risk",
             "Read the risk brief for public storage exposure.",
             "event_emitted", {"event": "risk_reviewed",
                               "key": "topic", "equals": "public-bucket"},
             ["Explaining a risk is half of fixing it.",
              "Run `risk public-bucket`.",
              "Note how fast scanners find newly public buckets."], 45),
        _obj("Make the bucket private",
             "Flip the access policy so anonymous access is denied.",
             "event_emitted", {"event": "bucket_access_set",
                               "key": "public", "equals": False},
             ["One command undoes the vendor-transfer mistake.",
              "Run `make-private customer-backups`.",
              "Anonymous requests now get 403 Forbidden."], 60),
        _obj("Enable at-rest encryption",
             "Encrypt the backups so stolen disks stay unreadable.",
             "event_emitted", {"event": "bucket_encryption_enabled"},
             ["Defense in depth: privacy AND encryption.",
              "Run `encrypt-bucket customer-backups`.",
              "web-assets shows encryption and public can coexist."], 55),
        _obj("Verify the bucket is secured",
             "Re-inspect the bucket and confirm both fixes took effect.",
             "event_emitted", {"event": "bucket_secured",
                               "key": "bucket",
                               "equals": "customer-backups"},
             ["Always verify a remediation by looking again.",
              "Run `get-bucket customer-backups`.",
              "Private + encrypted = secured."], 55),
    ]),

    ("cloud-iam-overprivileged", "The Over-Permissive Developer",
     "Medium", 25, 300, [
        _obj("Audit the IAM identities",
             "List the users and spot who holds more than their job needs.",
             "event_emitted", {"event": "iam_users_viewed"},
             ["Compare each user's ROLES against who they are.",
              "Run `list-users`.",
              "⚠ excessive marks the finding."], 40),
        _obj("Investigate the over-privileged user",
             "Open the developer who somehow holds Administrator.",
             "event_emitted", {"event": "iam_user_inspected",
                               "key": "excessive", "equals": True},
             ["A frontend developer with full account control?",
              "The description explains the \"temporary\" grant.",
              "Run `get-user dev-sita`."], 50),
        _obj("Understand the risk",
             "Read the risk brief for over-permissive IAM.",
             "event_emitted", {"event": "risk_reviewed", "key": "topic",
                               "equals": "over-permissive-iam"},
             ["One phished password = full account takeover.",
              "Run `risk over-permissive-iam`.",
              "\"Temporary\" grants are rarely revoked."], 50),
        _obj("Detach the Administrator role",
             "Remove the excessive role; keep the one that fits the job.",
             "event_emitted", {"event": "iam_role_detached",
                               "key": "role", "equals": "administrator"},
             ["Least privilege: access matches role, nothing more.",
              "The developer role stays — normal work continues.",
              "Run `detach-role dev-sita administrator`."], 70),
        _obj("Test the developer's permissions",
             "Run a permission simulation for dev-sita on an admin action.",
             "event_emitted", {"event": "permission_simulated",
                               "key": "username", "equals": "dev-sita"},
             ["Simulations show WHY access is allowed or denied.",
              "Pick an admin-only action, like deleting IAM users.",
              "Run `simulate dev-sita iam:delete-user`."], 50),
        _obj("Verify with a fresh audit",
             "Confirm the excessive-permission finding is gone.",
             "event_emitted", {"event": "audit_run",
                               "key": "excessive_iam", "equals": 0},
             ["Always verify a remediation.",
              "Run `audit`.",
              "Over-permissive IAM must show ✔ clean."], 60),
    ]),

    ("cloud-open-ssh", "SSH Open to the World", "Medium", 25, 320, [
        _obj("Survey the security groups",
             "List the firewall groups and find the risky one.",
             "event_emitted", {"event": "sgs_viewed"},
             ["Security groups are your virtual firewalls.",
              "Run `list-sgs`.",
              "One group carries a ⚠."], 45),
        _obj("Confirm the world-open SSH rule",
             "Inspect the web tier's group and find the offending rule.",
             "event_emitted", {"event": "sg_inspected",
                               "key": "open_ssh", "equals": True},
             ["0.0.0.0/0 means the entire internet.",
              "Run `get-sg web-sg`.",
              "The rule description tells the familiar story."], 55),
        _obj("Understand the risk",
             "Read the risk brief for internet-exposed SSH.",
             "event_emitted", {"event": "risk_reviewed", "key": "topic",
                               "equals": "open-ssh"},
             ["Port 22 gets scanned within minutes of opening.",
              "Run `risk open-ssh`.",
              "Note the recommended alternatives."], 55),
        _obj("Revoke the world-open rule",
             "Remove SSH-from-anywhere from the web security group.",
             "event_emitted", {"event": "sg_rule_revoked",
                               "key": "port", "equals": 22},
             ["Revoking beats editing: remove the exact bad rule.",
              "Run `revoke-ingress web-sg 22`.",
              "app-sg shows how SSH should look — VPC-only."], 90),
        _obj("Verify with a fresh audit",
             "Confirm the open-SSH finding is gone.",
             "event_emitted", {"event": "audit_run",
                               "key": "open_ssh", "equals": 0},
             ["Trust, but verify.",
              "Run `audit`.",
              "SSH open to the internet must show ✔ clean."], 65),
    ]),

    ("cloud-exposed-database", "The Exposed Customer Database",
     "Hard", 30, 340, [
        _obj("Survey the databases",
             "List the databases and read the EXPOSURE column.",
             "event_emitted", {"event": "dbs_viewed"},
             ["Databases are the crown jewels.",
              "Run `list-dbs`.",
              "INTERNET-REACHABLE on a customer DB is a five-alarm fire."],
             45),
        _obj("Confirm the exposure paths",
             "Inspect the customer database — it is exposed TWO ways.",
             "event_emitted", {"event": "db_inspected",
                               "key": "exposed", "equals": True},
             ["Check both the endpoint and the firewall.",
              "Run `get-db customers-db`.",
              "The findings list names both paths."], 55),
        _obj("Understand the risk",
             "Read the risk brief for publicly exposed databases.",
             "event_emitted", {"event": "risk_reviewed", "key": "topic",
                               "equals": "public-database"},
             ["Exposed databases get ransomed by bots.",
              "Run `risk public-database`.",
              "Either path alone keeps the DB reachable."], 55),
        _obj("Disable the public endpoint",
             "Turn off the database's internet-facing endpoint.",
             "event_emitted", {"event": "db_access_set",
                               "key": "public", "equals": False},
             ["Half the fix: the vendor-demo endpoint goes first.",
              "Run `make-db-private customers-db`.",
              "The output reminds you what is still open."], 75),
        _obj("Close the firewall path",
             "Revoke the world-open PostgreSQL rule too.",
             "event_emitted", {"event": "sg_rule_revoked",
                               "key": "port", "equals": 5432},
             ["Both doors must close.",
              "The database's group is db-sg.",
              "Run `revoke-ingress db-sg 5432`."], 75),
        _obj("Verify with a fresh audit",
             "Confirm no database is internet-reachable anymore.",
             "event_emitted", {"event": "audit_run",
                               "key": "public_dbs", "equals": 0},
             ["A remediation is done when the scanner agrees.",
              "Run `audit`.",
              "Databases exposed publicly must show ✔ clean."], 70),
    ]),

    ("cloud-hardening", "Account Hardening Capstone", "Hard", 35, 360, [
        _obj("Review the password policy",
             "Check the account's sign-in rules against the baseline.",
             "event_emitted", {"event": "policy_viewed",
                               "key": "strong", "equals": False},
             ["Six characters and no MFA is an open door.",
              "Run `password-policy`.",
              "The baseline: 12+ characters AND MFA."], 45),
        _obj("Understand the password-policy risk",
             "Read the risk brief for weak password policies.",
             "event_emitted", {"event": "risk_reviewed", "key": "topic",
                               "equals": "weak-password-policy"},
             ["Password spraying beats weak policies quietly.",
              "Run `risk weak-password-policy`.",
              "MFA stops most credential attacks cold."], 50),
        _obj("Enforce a strong policy",
             "Raise the minimum length AND require MFA.",
             "event_emitted", {"event": "policy_updated",
                               "key": "strong", "equals": True},
             ["Two settings to fix — the posture flips when both pass.",
              "Run `set-password-policy min-length 14`.",
              "Then `set-password-policy require-mfa on`."], 65),
        _obj("Investigate the dormant administrator",
             "Find the admin account nobody has used in months.",
             "event_emitted", {"event": "iam_user_inspected",
                               "key": "stale_admin", "equals": True},
             ["`list-users` flags the stale admin.",
              "The description mentions a departed employee.",
              "Run `get-user old-admin`."], 55),
        _obj("Understand the unused-admin risk",
             "Read the risk brief for dormant administrator accounts.",
             "event_emitted", {"event": "risk_reviewed", "key": "topic",
                               "equals": "unused-admin"},
             ["A skeleton key nobody is watching.",
              "Run `risk unused-admin`.",
              "Off-boarding gaps top real audit findings."], 50),
        _obj("Disable the dormant account",
             "Block sign-in for the departed employee's account.",
             "event_emitted", {"event": "iam_user_disabled",
                               "key": "username", "equals": "old-admin"},
             ["Disable first — history and audit trails survive.",
              "Run `disable-user old-admin`.",
              "Read the warning about access keys."], 70),
        _obj("Deactivate its access key",
             "Kill the API key so automation with old credentials fails.",
             "event_emitted", {"event": "iam_key_deactivated",
                               "key": "username", "equals": "old-admin"},
             ["Disabled accounts can still have live keys.",
              "Run `deactivate-key old-admin`.",
              "Now both the console AND the API are closed."], 60),
        _obj("Final verification audit",
             "Prove the hardening findings are fully resolved.",
             "event_emitted", {"event": "audit_run",
                               "key": "hardening_findings", "equals": 0},
             ["The capstone ends the way every incident should.",
              "Run `audit`.",
              "Weak policy AND unused admins must both show ✔."], 70),
    ]),
]

ACHIEVEMENTS = [
    {"title": "Cloud Explorer", "condition_type": "cloud_labs_completed",
     "condition_value": 1, "bonus_xp": 50, "icon": "layers",
     "description": "Complete your first Cloud Security lab."},
    {"title": "Cloud Defender", "condition_type": "cloud_labs_completed",
     "condition_value": 3, "bonus_xp": 100, "icon": "shield",
     "description": "Complete three Cloud Security labs."},
    {"title": "Cloud Security Architect",
     "condition_type": "cloud_labs_completed",
     "condition_value": 6, "bonus_xp": 150, "icon": "award",
     "description": "Complete the entire Cloud Security track."},
]

CERTIFICATE = {
    "title": "Cloud Security Fundamentals",
    "slug": "cloud-security-fundamentals",
    "category": "labs",
    "certificate_type": "track",
    "icon": "layers",
    "description": "Awarded for completing the full Cloud Security lab "
                   "track on the simulated YushaCloud platform: account "
                   "reconnaissance, storage exposure remediation, IAM "
                   "least privilege, firewall hardening, database "
                   "isolation and account-wide security hardening.",
    "required_labs": ",".join(slug for slug, *_ in LABS),
}


def seed_cloud_labs() -> dict[str, int]:
    """Seed the Cloud Security category, simulator engine row, labs +
    objectives, achievements and the track certificate. Idempotent by
    slug/title — existing rows are updated in place, never duplicated."""
    result = {"category": 0, "engine": 0, "labs": 0, "objectives": 0,
              "achievements": 0, "certificates": 0}

    # ---- Category -----------------------------------------------------
    category = LabCategory.query.filter_by(slug="cloud-security").first()
    if category is None:
        category = LabCategory(slug="cloud-security")
        db.session.add(category)
        result["category"] = 1
    category.name = "Cloud Security"
    category.description = ("Secure the simulated YushaCloud account — "
                            "IAM, storage, networking, databases and the "
                            "misconfigurations attackers hunt for.")
    category.icon = "layers"
    category.display_order = 80
    category.is_active = True

    # ---- Simulator engine row ----------------------------------------
    engine_row = SimulatorEngine.query.filter_by(key="cloud").first()
    if engine_row is None:
        engine_row = SimulatorEngine(key="cloud")
        db.session.add(engine_row)
        result["engine"] = 1
    engine_row.name = "Cloud Security Simulator"
    engine_row.description = ("Simulated cloud provider: IAM, buckets, "
                              "VPCs, security groups, VMs, databases and "
                              "a security posture auditor.")
    engine_row.capabilities = "terminal"
    engine_row.is_active = True
    db.session.flush()

    # ---- Labs + objectives (chained prerequisites) --------------------
    previous_lab = None
    for order, (slug, title, difficulty, minutes, xp, objectives) in \
            enumerate(LABS, start=1):
        lab = Lab.query.filter_by(slug=slug).first()
        if lab is None:
            lab = Lab(slug=slug)
            db.session.add(lab)
            result["labs"] += 1
        lab.category_id = category.id
        lab.title = title
        lab.description = objectives[0]["instruction"]
        lab.difficulty = difficulty
        lab.estimated_minutes = minutes
        lab.xp_reward = xp
        lab.display_order = order
        lab.is_active = True
        lab.simulator_key = "cloud"
        lab.is_interactive = True
        lab.prerequisite_lab_id = previous_lab.id if previous_lab else None
        db.session.flush()
        previous_lab = lab

        for obj_order, spec in enumerate(objectives, start=1):
            objective = LabObjective.query.filter_by(
                lab_id=lab.id, title=spec["title"]).first()
            if objective is None:
                objective = LabObjective(lab_id=lab.id, title=spec["title"])
                db.session.add(objective)
                result["objectives"] += 1
            objective.instruction = spec["instruction"]
            objective.description = spec["instruction"]
            objective.display_order = obj_order
            objective.validator_type = spec["validator_type"]
            objective.set_validator_data(spec["validator_data"])
            objective.hint1 = spec["hints"][0]
            objective.hint2 = spec["hints"][1]
            objective.hint3 = spec["hints"][2]
            objective.xp_reward = spec["xp"]
            objective.is_optional = spec["optional"]

    # ---- Achievements -------------------------------------------------
    for order, spec in enumerate(ACHIEVEMENTS, start=95):
        achievement = Achievement.query.filter_by(title=spec["title"]).first()
        if achievement is None:
            achievement = Achievement(title=spec["title"],
                                      condition_type=spec["condition_type"])
            db.session.add(achievement)
            result["achievements"] += 1
        achievement.description = spec["description"]
        achievement.icon = spec["icon"]
        achievement.category = "labs"
        achievement.condition_type = spec["condition_type"]
        achievement.condition_value = spec["condition_value"]
        achievement.bonus_xp = spec["bonus_xp"]
        achievement.is_active = True
        achievement.display_order = order

    # ---- Certificate --------------------------------------------------
    certificate = Certificate.query.filter_by(slug=CERTIFICATE["slug"]).first()
    if certificate is None:
        certificate = Certificate(slug=CERTIFICATE["slug"],
                                  title=CERTIFICATE["title"])
        db.session.add(certificate)
        result["certificates"] = 1
    certificate.title = CERTIFICATE["title"]
    certificate.description = CERTIFICATE["description"]
    certificate.category = CERTIFICATE["category"]
    certificate.certificate_type = CERTIFICATE["certificate_type"]
    certificate.icon = CERTIFICATE["icon"]
    certificate.required_labs = CERTIFICATE["required_labs"]
    certificate.is_active = True

    db.session.commit()
    return result
