"""Active Directory lab seed (YC-031.0). Idempotent — safe to re-run."""

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
    ("ad-orientation", "AD Basics: Explore YUSHA.LOCAL", "Easy", 20, 260, [
        _obj("Survey the user accounts",
             "List every user account in the domain and read the status column.",
             "event_emitted", {"event": "users_viewed"},
             ["The explorer tree shows objects — the console shows detail.",
              "Run `get-users` to list every account.",
              "Notice the STATUS and LAST LOGON columns — they matter later."],
             35),
        _obj("Survey the security groups",
             "List the domain's security groups and spot the privileged one.",
             "event_emitted", {"event": "groups_viewed"},
             ["Groups grant access; one group grants EVERYTHING.",
              "Run `get-groups`.",
              "The ⚠ marker flags privileged groups."], 35),
        _obj("Review the organizational units",
             "List the OUs to see how the company structures its directory.",
             "event_emitted", {"event": "ous_viewed"},
             ["OUs are folders for delegation and policy, not permissions.",
              "Run `get-ous`.",
              "Note the 'Disabled Accounts' quarantine OU."], 35),
        _obj("Inspect the Domain Controller",
             "Find the computer that runs Active Directory itself.",
             "event_emitted", {"event": "computer_inspected", "key": "is_dc",
                               "equals": True},
             ["One computer holds the keys to the kingdom.",
              "Run `get-computers`, then inspect the DC.",
              "Run `get-computer dc-01`."], 40),
        _obj("Review the shared folders",
             "List the file shares and their servers.",
             "event_emitted", {"event": "shares_viewed"},
             ["Shares are where identity meets data.",
              "Run `get-shares`.",
              "You will audit these permissions in a later lab."], 35),
        _obj("Watch a Kerberos authentication",
             "Visualize how a healthy account gets its tickets.",
             "event_emitted", {"event": "kerberos_viewed", "key": "ok",
                               "equals": True},
             ["Kerberos is how Windows proves who you are.",
              "Pick an active user, e.g. skhadka.",
              "Run `kerberos skhadka`."], 45),
    ]),

    ("ad-inactive-account", "Find the Inactive Account", "Easy", 20, 280, [
        _obj("Review last-logon activity",
             "List the users and find who has not logged on for months.",
             "event_emitted", {"event": "users_viewed"},
             ["Stale accounts are a favourite attacker foothold.",
              "Run `get-users` and read the LAST LOGON column.",
              "The ⚠ marker flags 90+ days of inactivity."], 40),
        _obj("Investigate the stale account",
             "Open the inactive user's properties to confirm the finding.",
             "event_emitted", {"event": "user_inspected", "key": "inactive",
                               "equals": True},
             ["One account has been unused for around 7 months.",
              "The description often explains why.",
              "Run `get-user kshrestha`."], 50),
        _obj("Disable the account",
             "Deactivate the inactive account so it can no longer log on.",
             "event_emitted", {"event": "account_disabled",
                               "key": "sam", "equals": "kshrestha"},
             ["Disabling beats deleting: access stops, history survives.",
              "Run `disable kshrestha`.",
              "Verify with `get-user kshrestha` — status shows DISABLED."], 60),
        _obj("Quarantine it in the Disabled Accounts OU",
             "Move the account into the quarantine OU per company policy.",
             "event_emitted", {"event": "user_moved", "key": "ou",
                               "equals": "disabled-accounts"},
             ["A dedicated OU keeps deactivated accounts visible and policied.",
              "OU names with spaces need quotes.",
              "Run `move kshrestha \"Disabled Accounts\"`."], 60),
        _obj("Prove the account can no longer authenticate",
             "Show that Kerberos now refuses the disabled account.",
             "event_emitted", {"event": "kerberos_viewed", "key": "reason",
                               "equals": "disabled"},
             ["The KDC checks account status before issuing any ticket.",
              "Run `kerberos kshrestha`.",
              "KDC_ERR_CLIENT_REVOKED is exactly what you want to see."], 70),
    ]),

    ("ad-compromised-password", "The Compromised Password", "Medium", 25, 300, [
        _obj("Review the password and lockout policy",
             "Know the rules before you reset anything.",
             "event_emitted", {"event": "policy_viewed"},
             ["Every reset must satisfy the domain policy.",
              "Run `policy`.",
              "Note the minimum length and complexity rules."], 45),
        _obj("Investigate the locked account",
             "Find the account locked out by the failed-login storm.",
             "event_emitted", {"event": "user_inspected", "key": "locked",
                               "equals": True},
             ["The user list shows who is LOCKED.",
              "Read the account description — it references the incident.",
              "Run `get-user mrai`."], 50),
        _obj("Reset the password (policy-compliant)",
             "Give the account a new password that passes the domain policy.",
             "event_emitted", {"event": "password_reset", "key": "policy_ok",
                               "equals": True},
             ["Try a weak one first and read WHY it is rejected.",
              "12+ chars, 3 of 4 character classes, not the username.",
              "Run `reset-password mrai Str0ng-Aut umn-2026!` style — no spaces."],
             65),
        _obj("Unlock the account",
             "Clear the lockout so the legitimate owner can sign in again.",
             "event_emitted", {"event": "account_unlocked", "key": "was_locked",
                               "equals": True},
             ["Reset first, THEN unlock — never the other way round.",
              "Run `unlock mrai`.",
              "The failed-attempt counter resets to zero."], 65),
        _obj("Verify authentication works again",
             "Confirm Kerberos now issues the user a TGT.",
             "event_emitted", {"event": "kerberos_viewed", "key": "ok",
                               "equals": True},
             ["A clean flow ends with a service ticket.",
              "Run `kerberos mrai`.",
              "All six steps should succeed."], 75),
    ]),

    ("ad-overprivileged", "The Over-Privileged Intern", "Medium", 25, 320, [
        _obj("Audit the Domain Admins membership",
             "List who currently holds full administrative control.",
             "event_emitted", {"event": "group_members_viewed",
                               "key": "group", "equals": "domain-admins"},
             ["Start every privilege audit at the top.",
              "Group names with spaces need quotes.",
              "Run `members \"Domain Admins\"`."], 55),
        _obj("Investigate the suspicious member",
             "Open the account that does not belong in that group.",
             "event_emitted", {"event": "user_inspected", "key": "privileged",
                               "equals": True},
             ["Compare each member's role against their privilege.",
              "An intern with domain-wide admin rights is a finding.",
              "Run `get-user intern01`."], 60),
        _obj("Remove the excessive privilege",
             "Take the intern out of Domain Admins.",
             "event_emitted", {"event": "member_removed", "key": "sam",
                               "equals": "intern01"},
             ["Least privilege: access matches role, nothing more.",
              "The intern keeps Domain Users — normal work continues.",
              "Run `remove-member \"Domain Admins\" intern01`."], 90),
        _obj("Verify the membership is clean",
             "Re-audit Domain Admins and confirm only true admins remain.",
             "event_emitted", {"event": "group_members_viewed",
                               "key": "member_count", "equals": 1},
             ["Always verify a remediation.",
              "Run `members \"Domain Admins\"` again.",
              "Only 'administrator' should remain."], 60),
    ]),

    ("ad-least-privilege", "Least Privilege Audit", "Hard", 30, 360, [
        _obj("Audit the shared folders",
             "List the shares — one of them leaks confidential data.",
             "event_emitted", {"event": "shares_viewed"},
             ["Permissions drift over time; audits catch the drift.",
              "Run `get-shares`, then inspect each with `get-share <name>`.",
              "Pay attention to HR-Confidential."], 50),
        _obj("Prove the exposure",
             "Show that a regular, non-HR user can read HR-Confidential.",
             "event_emitted", {"event": "access_checked",
                               "key": "via_domain_users", "equals": True},
             ["Pick someone outside HR — the accountant, for example.",
              "Run `access dtamang hr-confidential`.",
              "GRANTED via 'Domain Users' = everyone can read it."], 65),
        _obj("Revoke the over-broad permission",
             "Remove Domain Users from the HR-Confidential ACL.",
             "event_emitted", {"event": "access_revoked", "key": "share",
                               "equals": "hr-confidential"},
             ["Revoke the group grant, not individual users.",
              "Quotes for names with spaces.",
              "Run `revoke-access hr-confidential \"Domain Users\"`."], 90),
        _obj("Verify least privilege holds",
             "Re-test the same user — access must now be denied.",
             "event_emitted", {"event": "access_checked", "key": "allowed",
                               "equals": False},
             ["The HR group keeps its access; everyone else loses it.",
              "Run `access dtamang hr-confidential` again.",
              "DENIED is the success state here."], 80),
        _obj("Review the applied Group Policy",
             "Check the GPOs that keep the environment hardened.",
             "event_emitted", {"event": "gpo_viewed"},
             ["Policy is prevention; audits are detection.",
              "Run `gpos`.",
              "Note what Desktop Restrictions denies to interns."], 75),
    ]),
]

ACHIEVEMENTS = [
    {"title": "Domain Explorer", "condition_type": "ad_labs_completed",
     "condition_value": 1, "bonus_xp": 50, "icon": "cpu",
     "description": "Complete your first Active Directory lab."},
    {"title": "Identity Defender", "condition_type": "ad_labs_completed",
     "condition_value": 3, "bonus_xp": 100, "icon": "shield",
     "description": "Complete three Active Directory labs."},
    {"title": "Least Privilege Champion", "condition_type": "ad_labs_completed",
     "condition_value": 5, "bonus_xp": 150, "icon": "award",
     "description": "Complete the entire Active Directory security track."},
]

CERTIFICATE = {
    "title": "Active Directory Security Fundamentals",
    "slug": "ad-security-fundamentals",
    "category": "labs",
    "certificate_type": "track",
    "icon": "shield",
    "description": "Awarded for completing the full Active Directory "
                   "security lab track: directory exploration, account "
                   "lifecycle management, password policy enforcement, "
                   "privileged-group auditing and least-privilege "
                   "remediation on the simulated YUSHA.LOCAL domain.",
    "required_labs": ",".join(slug for slug, *_ in LABS),
}


def seed_ad_labs() -> dict[str, int]:
    """Seed the AD category, simulator engine row, labs + objectives,
    achievements and the track certificate. Idempotent by slug/title —
    existing rows are updated in place, never duplicated."""
    result = {"category": 0, "engine": 0, "labs": 0, "objectives": 0,
              "achievements": 0, "certificates": 0}

    # ---- Category -----------------------------------------------------
    category = LabCategory.query.filter_by(slug="active-directory").first()
    if category is None:
        category = LabCategory(slug="active-directory")
        db.session.add(category)
        result["category"] = 1
    category.name = "Active Directory"
    category.description = ("Enterprise identity security on the simulated "
                            "YUSHA.LOCAL domain — users, groups, policies, "
                            "Kerberos and least privilege.")
    category.icon = "cpu"
    category.display_order = 70
    category.is_active = True

    # ---- Simulator engine row ----------------------------------------
    engine_row = SimulatorEngine.query.filter_by(key="ad").first()
    if engine_row is None:
        engine_row = SimulatorEngine(key="ad")
        db.session.add(engine_row)
        result["engine"] = 1
    engine_row.name = "Active Directory Simulator"
    engine_row.description = ("Simulated enterprise domain: directory "
                              "objects, account operations, group policy, "
                              "share permissions and conceptual Kerberos.")
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
        lab.simulator_key = "ad"
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
    for order, spec in enumerate(ACHIEVEMENTS, start=90):
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
