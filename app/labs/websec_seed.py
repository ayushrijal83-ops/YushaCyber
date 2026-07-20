"""Web Security Lab seed (YC-029.0).

10 labs covering each module from the ticket. Each lab loads its
scenario into the web-security simulator via the lab's content field.
"""

from __future__ import annotations

from app.achievement.models import Achievement
from app.extensions import db
from app.labs.models import Lab, LabCategory, LabObjective, SimulatorEngine


def _obj(title, instruction, vtype, vdata, hints, xp, optional=False):
    return {"title": title, "instruction": instruction,
            "validator_type": vtype, "validator_data": vdata,
            "hints": hints, "xp": xp, "optional": optional}


LABS = [
    # 1. HTTP Basics
    ("websec-http", "HTTP Requests & Responses", "Easy", 10, 120,
     "http-basics", [
        _obj("Inspect the HTTP request",
             "View the full HTTP request using the http command.",
             "event_emitted", {"event": "http_inspected"},
             ["Type `http` to see the raw request.",
              "Look at the method, URL, and headers.",
              "The request shows GET /dashboard HTTP/1.1."], 25),
        _obj("Examine the response headers",
             "Check the response headers for information leakage.",
             "event_emitted", {"event": "headers_inspected"},
             ["Use `headers` or `headers res` to see response headers.",
              "Look for headers that reveal server technology.",
              "X-Powered-By and Server headers leak version info."], 25),
        _obj("Check the response status",
             "Verify the HTTP status code of the response.",
             "event_emitted", {"event": "status_inspected"},
             ["Use the `status` command.",
              "HTTP 200 means OK — the request succeeded.",
              "Status codes 4xx are client errors, 5xx are server errors."], 20),
    ]),

    # 2. Cookie Security
    ("websec-cookies", "Cookie Security Flags", "Easy", 10, 140,
     "cookie-flags", [
        _obj("Inspect the cookies",
             "Examine the session cookies and their security flags.",
             "event_emitted", {"event": "cookies_inspected"},
             ["Use the `cookies` command.",
              "Look at both request cookies and Set-Cookie response headers.",
              "Check which security flags are present or missing."], 30),
        _obj("Identify missing flags",
             "Submit your finding about the insecure cookie configuration.",
             "event_emitted", {"event": "answer_submitted", "key": "correct", "equals": True},
             ["The session cookie is missing important security flags.",
              "Think about Secure, HttpOnly, and SameSite.",
              "Try `answer missing Secure HttpOnly SameSite flags`."], 40),
    ]),

    # 3. Session Management
    ("websec-sessions", "Session Fixation", "Medium", 15, 160,
     "session-fixation", [
        _obj("Inspect the login request",
             "View the POST request to understand what's happening.",
             "event_emitted", {"event": "http_inspected"},
             ["Use `http` to see the full request.",
              "Notice the session ID in the Cookie header.",
              "The session ID is ATTACKER_KNOWN_ID."], 30),
        _obj("Check the response Set-Cookie",
             "Examine whether the session ID changes after login.",
             "event_emitted", {"event": "cookies_inspected"},
             ["Use `cookies` to see the Set-Cookie header.",
              "Compare the session ID before and after login.",
              "Does the server issue a NEW session ID?"], 30),
        _obj("Identify the vulnerability",
             "Explain why this session management is dangerous.",
             "event_emitted", {"event": "answer_submitted", "key": "correct", "equals": True},
             ["The session ID doesn't change after authentication.",
              "This is called session fixation.",
              "Try `answer session fixation — server should regenerate session ID`."], 40),
    ]),

    # 4. Authentication
    ("websec-auth", "Authentication Bypass", "Easy", 10, 140,
     "auth-bypass", [
        _obj("Inspect the request parameters",
             "Look at how credentials are transmitted.",
             "event_emitted", {"event": "params_inspected"},
             ["Use `params` to see the query parameters.",
              "Notice where the username and password appear.",
              "Are credentials in the URL or the body?"], 30),
        _obj("Identify the vulnerability",
             "Explain what's wrong with this login implementation.",
             "event_emitted", {"event": "answer_submitted", "key": "correct", "equals": True},
             ["Credentials are visible in the URL.",
              "GET requests with passwords get logged everywhere.",
              "Try `answer password in URL query string — should use POST`."], 40),
    ]),

    # 5. Authorization (IDOR)
    ("websec-idor", "IDOR — Insecure Direct Object Reference", "Medium", 15, 180,
     "idor", [
        _obj("Inspect the API request",
             "View the request to the user data endpoint.",
             "event_emitted", {"event": "http_inspected"},
             ["Use `http` to see the full request.",
              "Notice the user ID in the URL path.",
              "Check the Authorization header — whose token is it?"], 30),
        _obj("Examine the response body",
             "Check what data the API returns.",
             "event_emitted", {"event": "body_inspected"},
             ["Use `body` or `body res` to see the response.",
              "Look at what personal data is exposed.",
              "The response includes sensitive fields like SSN."], 30),
        _obj("Identify the IDOR vulnerability",
             "Explain how an attacker could exploit this.",
             "event_emitted", {"event": "answer_submitted", "key": "correct", "equals": True},
             ["User 1041's token can access user 1042's data.",
              "The server doesn't check if the token owner matches the requested ID.",
              "Try `answer IDOR — no authorization check on resource ownership`."], 50),
    ]),

    # 6. SQL Injection
    ("websec-sqli", "SQL Injection — Login Bypass", "Medium", 20, 200,
     "sqli-login", [
        _obj("Inspect the login form",
             "Examine the POST request and its parameters.",
             "event_emitted", {"event": "params_inspected"},
             ["Use `http` then `params` to see the form data.",
              "The body contains username and password fields.",
              "Notice the form uses application/x-www-form-urlencoded."], 30),
        _obj("Test for SQL injection",
             "Use the sqli command to test the login form.",
             "event_emitted", {"event": "sqli_tested", "key": "success", "equals": True},
             ["Try common SQL injection payloads.",
              "Classic login bypass: ' OR 1=1--",
              "Run `sqli test ' OR 1=1--`."], 50),
        _obj("Submit your assessment",
             "Identify the vulnerability and the correct mitigation.",
             "event_emitted", {"event": "answer_submitted", "key": "correct", "equals": True},
             ["You've proven the injection works.",
              "What's the root cause? How should it be fixed?",
              "Try `answer SQL injection in username field — use parameterized queries`."], 50),
    ]),

    # 7. XSS
    ("websec-xss", "Cross-Site Scripting — Reflected", "Medium", 20, 200,
     "xss-reflected", [
        _obj("Inspect the search page",
             "View the request and response to understand the search functionality.",
             "event_emitted", {"event": "params_inspected"},
             ["Use `params` to see the search query parameter.",
              "Then use `body res` to see how the search term appears in the response.",
              "Is the search term reflected without encoding?"], 30),
        _obj("Test for XSS",
             "Use the xss command to test the search parameter.",
             "event_emitted", {"event": "xss_tested", "key": "success", "equals": True},
             ["Try injecting a script tag into the search parameter.",
              "Classic XSS: <script>alert(1)</script>",
              "Run `xss test <script>alert(1)</script>`."], 50),
        _obj("Submit your assessment",
             "Identify the type of XSS and the mitigation.",
             "event_emitted", {"event": "answer_submitted", "key": "correct", "equals": True},
             ["The search query is reflected in the HTML without escaping.",
              "This is reflected XSS (vs stored or DOM-based).",
              "Try `answer reflected XSS — sanitize and HTML-encode user input`."], 50),
    ]),

    # 8. CSRF
    ("websec-csrf", "Cross-Site Request Forgery", "Medium", 15, 180,
     "csrf-transfer", [
        _obj("Inspect the transfer request",
             "View the POST request that transfers money.",
             "event_emitted", {"event": "http_inspected"},
             ["Use `http` to see the full request.",
              "Check the body — it sends money to 'attacker'.",
              "Is there anything preventing a forged request?"], 30),
        _obj("Run the CSRF check",
             "Use the csrf command to analyze protections.",
             "event_emitted", {"event": "csrf_checked", "key": "vulnerable", "equals": True},
             ["The simulator can check for CSRF protections automatically.",
              "Run `csrf check`.",
              "Look for missing CSRF token, SameSite flag, and Origin check."], 50),
        _obj("Submit your assessment",
             "Explain why this endpoint is vulnerable to CSRF.",
             "event_emitted", {"event": "answer_submitted", "key": "correct", "equals": True},
             ["There's no CSRF token in the form.",
              "The session cookie lacks SameSite.",
              "Try `answer CSRF — add anti-CSRF token and SameSite cookie flag`."], 40),
    ]),

    # 9. File Upload
    ("websec-upload", "File Upload Validation", "Medium", 15, 180,
     "file-upload", [
        _obj("Inspect the upload request",
             "View the multipart POST request.",
             "event_emitted", {"event": "http_inspected"},
             ["Use `http` and `body req` to see the upload.",
              "Notice the filename and Content-Type.",
              "Is the file extension checked?"], 30),
        _obj("Examine the response",
             "Check where the file was saved.",
             "event_emitted", {"event": "body_inspected"},
             ["Use `body res` to see the server's response.",
              "Look at the file path — does it preserve the original extension?",
              "A .php file in /uploads/ means code execution."], 30),
        _obj("Submit your assessment",
             "Identify the file upload vulnerability.",
             "event_emitted", {"event": "answer_submitted", "key": "correct", "equals": True},
             ["The server only checks Content-Type, not the file extension.",
              "A PHP shell uploaded as image/jpeg still executes.",
              "Try `answer unrestricted file upload — validate extension and magic bytes`."], 50),
    ]),

    # 10. Security Headers
    ("websec-headers", "Security Headers Audit", "Easy", 10, 140,
     "security-headers", [
        _obj("Inspect the response headers",
             "Check what security headers are present or missing.",
             "event_emitted", {"event": "headers_inspected"},
             ["Use `headers res` to see only response headers.",
              "Look for security headers like CSP, HSTS, X-Frame-Options.",
              "Also note any headers that leak information."], 30),
        _obj("Identify information leakage",
             "The response reveals server technology. What headers expose it?",
             "state_flag", {"path": "flags.headers_inspected", "equals": True},
             ["Look for Server and X-Powered-By headers.",
              "These tell attackers exactly what software and version to target.",
              "Apache/2.4.41 and PHP/7.4 are disclosed."], 30),
        _obj("Submit your audit findings",
             "List the missing security headers.",
             "event_emitted", {"event": "answer_submitted", "key": "correct", "equals": True},
             ["Several important security headers are missing.",
              "CSP, X-Frame-Options, HSTS, X-Content-Type-Options.",
              "Try `answer missing CSP X-Frame-Options HSTS X-Content-Type-Options`."], 40),
    ]),
]

ACHIEVEMENTS = [
    ("Bug Hunter",
     "Complete your first web security lab.",
     "lock", "labs", "websec_labs_completed", 1, 100),
    ("OWASP Explorer",
     "Complete 5 web security labs.",
     "lock", "labs", "websec_labs_completed", 5, 250),
    ("AppSec Specialist",
     "Complete all 10 web security labs.",
     "lock", "labs", "websec_labs_completed", 10, 500),
]


def seed_websec_labs() -> dict[str, int]:
    """Seed the 10 web security labs + achievements. Idempotent."""
    if SimulatorEngine.query.filter_by(key="web-security").first() is None:
        db.session.add(SimulatorEngine(
            key="web-security",
            name="Web Security Simulator",
            description="Scenario-based HTTP vulnerability analysis.",
        ))
        db.session.flush()

    category = LabCategory.query.filter_by(slug="web-security").first()
    if category is None:
        category = LabCategory(
            slug="web-security", name="Web Security", icon="lock",
            description="Learn to identify and exploit common web vulnerabilities in a safe, sandboxed environment.",
            display_order=35, is_active=True,
        )
        db.session.add(category)
        db.session.flush()

    created = {"labs": 0, "objectives": 0, "achievements": 0}
    base_order = db.session.query(
        db.func.coalesce(db.func.max(Lab.display_order), 0)
    ).filter_by(category_id=category.id).scalar()
    prev_lab_id = None

    for offset, (slug, title, diff, minutes, xp, scenario_key, objectives) in enumerate(LABS, start=1):
        existing = Lab.query.filter_by(slug=slug).first()
        if existing is not None:
            prev_lab_id = existing.id
            continue

        lab = Lab(
            category_id=category.id, title=title, slug=slug,
            description=f"{title} — web security analysis lab.",
            difficulty=diff, estimated_minutes=minutes, xp_reward=xp,
            display_order=base_order + offset, is_active=True,
            simulator_key="web-security", is_interactive=True,
            prerequisite_lab_id=prev_lab_id,
        )
        db.session.add(lab)
        db.session.flush()
        created["labs"] += 1

        for o_order, o in enumerate(objectives, start=1):
            objective = LabObjective(
                lab_id=lab.id, title=o["title"], description=o["instruction"],
                instruction=o["instruction"], display_order=o_order,
                validator_type=o["validator_type"], xp_reward=o["xp"],
                is_optional=o["optional"],
                hint1=o["hints"][0], hint2=o["hints"][1], hint3=o["hints"][2],
            )
            objective.set_validator_data(o["validator_data"])
            db.session.add(objective)
            created["objectives"] += 1

        prev_lab_id = lab.id

    max_order = db.session.query(
        db.func.coalesce(db.func.max(Achievement.display_order), 0)
    ).scalar()
    for offset, (title, desc, icon, cat, ctype, cvalue, bonus) in \
            enumerate(ACHIEVEMENTS, start=1):
        if Achievement.query.filter_by(title=title).first() is not None:
            continue
        db.session.add(Achievement(
            title=title, description=desc, icon=icon, category=cat,
            condition_type=ctype, condition_value=cvalue, bonus_xp=bonus,
            is_active=True, display_order=max_order + offset,
        ))
        created["achievements"] += 1

    db.session.commit()
    return created
