import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0351-smoke-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_hd.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

from app import create_app
from app.extensions import db

app = create_app()
app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

with app.app_context():
    db.create_all()
    from app.auth.models import User
    u = User(username="hd_smoke", email="hdsmoke@t.io")
    u.set_password("Str0ngPass!")
    db.session.add(u)
    db.session.commit()
    uid = u.id

with app.test_client() as c:
    c.post("/auth/login", data={"identifier": "hd_smoke", "password": "Str0ngPass!"},
           follow_redirects=True)

    r = c.get("/terminal/mission/http-deep-dive")
    print("status:", r.status_code)
    body = r.data.decode("utf-8")
    checks = [
        ("HTTP Inspector button", 'data-inspector-toggle' in body),
        ("tabs present", 'data-tab="request"' in body and 'data-tab="history"' in body),
        ("request panel", 'data-inspector-request' in body),
        ("response panel", 'data-inspector-response' in body),
        ("cookies panel", 'data-inspector-cookies' in body),
        ("history panel", 'data-inspector-history' in body),
        ("builder form", 'data-inspector-form' in body),
        ("initial json script tag", 'id="tm-web-lab-initial"' in body),
        ("HTTPS/TLS hint text", 'TLS encryption' in body),
        ("mission title", 'HTTP Deep Dive' in body),
    ]
    for name, ok in checks:
        print(("OK  " if ok else "FAIL"), name)

    # Drive a couple of commands via the execute API and confirm
    # web_lab_status now carries full request/response data.
    r2 = c.post("/api/terminal/mission/execute", json={
        "slug": "http-deep-dive",
        "command": "open https://cybershop.training/products?id=42",
    })
    d = r2.get_json()
    print("execute status:", r2.status_code)
    print("has last_request:", d["web_lab_status"]["last_request"] is not None)
    print("has last_response:", d["web_lab_status"]["last_response"] is not None)
    print("response ETag:", d["web_lab_status"]["last_response"]["headers"].get("ETag"))
    print("history entries:", len(d["web_lab_status"]["history"]))
