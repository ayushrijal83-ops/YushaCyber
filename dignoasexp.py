"""XP display diagnostic — run from the project root:  python diagnose_xp.py

Checks every link in the chain (files -> DB -> render) and prints a verdict.
Safe to run: creates one throwaway user (diag_xp_user), awards it XP via the
service, and renders the dashboard in-process. Delete this file afterwards.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
print(f"[i] Project root: {ROOT}")

# ---------------------------------------------------------------- 1. FILES
print("\n=== 1. File checks (are the updated files actually here?) ===")
checks = {
    "app/dashboard/services.py": ["def get_xp_info", "def award_xp", '"xp_info": get_xp_info'],
    "app/dashboard/routes.py": ["get_dashboard_context(current_user)", "test_xp"],
    "app/templates/dashboard/welcome_banner.html": ["xp_info.xp", "xp_info.next_threshold", "xp_info.percent"],
    "app/templates/dashboard/dashboard.html": ['include "dashboard/welcome_banner.html"'],
}
files_ok = True
for rel, markers in checks.items():
    path = ROOT / rel
    if not path.exists():
        print(f"  FAIL  {rel}  — FILE MISSING")
        files_ok = False
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    missing = [m for m in markers if m not in text]
    if missing:
        print(f"  FAIL  {rel}  — missing: {missing}")
        files_ok = False
    else:
        print(f"  ok    {rel}")

if not files_ok:
    print("\n>>> VERDICT: your local files are OUTDATED or hand-edited.")
    print(">>> Replace the files marked FAIL with the versions from the latest zip,")
    print(">>> restart the server, and the banner will update. Stopping here.")
    sys.exit(1)

# ------------------------------------------------------------- 2. APP + DB
print("\n=== 2. App import + database ===")
sys.path.insert(0, str(ROOT))
from app import create_app                      # noqa: E402
from app.auth.models import User                # noqa: E402
from app.dashboard import services              # noqa: E402
from app.extensions import db                   # noqa: E402

app = create_app()
print(f"  app template folder: {app.template_folder}")
print(f"  database URI:        {app.config['SQLALCHEMY_DATABASE_URI']}")

with app.app_context():
    try:
        users = User.query.order_by(User.id).all()
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL  cannot query users: {exc}")
        print("\n>>> VERDICT: database not migrated. Run: flask --app app db upgrade")
        sys.exit(1)
    print(f"  users in DB ({len(users)}):")
    for u in users:
        print(f"    id={u.id}  {u.username:<20} xp={u.xp:<6} level={u.level}")

# ------------------------------------------------- 3. SERVICE ROUND-TRIP
print("\n=== 3. award_xp() round-trip on a throwaway user ===")
with app.app_context():
    diag = User.query.filter_by(username="diag_xp_user").first()
    if diag is None:
        diag = User(username="diag_xp_user", email="diag_xp@local.test")
        diag.set_password("DiagPass123")
        db.session.add(diag)
        db.session.commit()
    before = (diag.xp, diag.level)
    services.award_xp(diag, 100)
    db.session.refresh(diag)
    print(f"  before: xp={before[0]} level={before[1]}  ->  after: xp={diag.xp} level={diag.level}")
    if diag.xp == before[0]:
        print("\n>>> VERDICT: award_xp did NOT persist — commit is failing on this DB.")
        print(">>> Check file permissions on instance/yushacyber.db and the server log.")
        sys.exit(1)

# ------------------------------------------------------ 4. RENDER CHECK
print("\n=== 4. Rendered banner for diag_xp_user ===")
client = app.test_client()
page = client.get("/auth/login")
token = re.search(rb'name="csrf_token" type="hidden" value="([^"]+)"', page.data).group(1).decode()
client.post("/auth/login", data={"csrf_token": token, "identifier": "diag_xp_user",
                                 "password": "DiagPass123", "submit": "Login"})
html = client.get("/dashboard/").data.decode()
match = re.search(r"<strong>(\d+)</strong>&nbsp;/ (\d+) XP", html)
if not match:
    print("  FAIL  banner XP fraction not found in rendered HTML.")
    print(">>> VERDICT: the server is rendering a DIFFERENT welcome_banner.html")
    print(">>> than the one checked in step 1 — you likely have a second copy of")
    print(">>> the project and are running the server from the other folder.")
    sys.exit(1)

print(f"  banner renders: {match.group(1)} / {match.group(2)} XP")
with app.app_context():
    diag = User.query.filter_by(username="diag_xp_user").one()
    if int(match.group(1)) == diag.xp:
        print("\n>>> VERDICT: EVERYTHING WORKS in this project folder.")
        print(">>> If your browser still shows 0/100: (a) you are running the Flask")
        print(">>> server from a DIFFERENT folder/copy of the project, or (b) the")
        print(">>> server was not restarted after updating files, or (c) the browser")
        print(">>> session is logged into a different account than the one earning XP.")
    else:
        print("\n>>> VERDICT: render/DB mismatch — send me this full output.")