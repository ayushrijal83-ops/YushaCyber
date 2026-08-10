# Cross-Site Request Forgery (CSRF) Fundamentals Mission (YC-035.6)

## Purpose

The seventh mission in the Web Security learning path, chained after
YC-035.0 (Web Fundamentals), YC-035.1 (HTTP Deep Dive), YC-035.2 (Burp
Suite Fundamentals), YC-035.3 (Authentication & Sessions), YC-035.4 (SQL
Injection Fundamentals), and YC-035.5 (XSS Fundamentals). Teaches how a
browser's automatic, per-site cookie attachment lets a state-changing
request reach a vulnerable endpoint without the user's intent — the
CSRF attack flow, why GET should never change state, the synchronizer
token pattern, SameSite cookies, and Origin/Referer validation — entirely
inside the existing simulated training environment
(`cybershop.training`), using the same simulated browser, HTTP
inspector, and intercepting proxy the last five missions already built.
Still purely educational: the "Simulate Request" action never makes a
real cross-origin request, never contacts a second host, and never
touches a real cookie or session — it only ever builds the same `open
...` terminal command (with an `Origin`/`Referer` header set to a fixed,
fictional `attacker.training` value) a student could type themselves,
dispatched through the exact same in-memory simulator as every other
request on this page. Real attacker infrastructure, cookie theft,
phishing, and external-target testing are explicitly out of scope — they
don't belong in this or any future mission in this series.

## Architecture — extends, doesn't duplicate

No new mission engine, HTTP simulator, proxy, XP engine, AI mentor, or
browser sandbox. Everything lives in the same modules built for
YC-035.0–YC-035.5:

- `app/core/terminal/web.py` — `WebApp` gains seven new routes (`GET
  /settings`, `GET /csrf-demo`, `GET`/`POST /secure-transfer`, `POST
  /transfer`, `GET /transfer-history`; `GET /account` was already
  present from YC-035.3 and is reused unchanged); fixed training
  constants (`TRANSFER_RECIPIENT`, `STARTING_BALANCE`, `TRUSTED_ORIGIN`,
  `ATTACKER_ORIGIN`) and a deterministic, session-bound
  `_csrf_token_for_session()` helper (same discipline as YC-035.1's
  `API_TOKEN` — fixed and reproducible, never actually random); a
  `Transfer` dataclass and `WebApp.balances`/`WebApp.transfers` (mirrors
  YC-035.5's `Comment`/`WebApp.comments`); a new `CsrfLabState` dataclass
  (mirrors `XssLabState`) attached to `WebLab` as `.csrf`; a new fixed
  investigation transcript (`build_csrf_investigation_log`) registered
  in the existing `_INVESTIGATION_BUILDERS` registry.
- `app/core/terminal/commands.py` — a new `_track_csrf_response()`
  helper (mirrors `_track_xss_response()`), called from `_open`,
  `_forward`, and `_repeater`'s `send` branch exactly like its XSS/SQLi
  counterparts; a new `samesite strict|lax|none` command — a purely
  conceptual, educational SameSite explainer (there is no real
  cookie-attribute engine anywhere in this simulator).
- `app/core/missions/mission_validator.py` — ten new `check` values
  added to the existing `web_state` type (`state_change_identified`,
  `get_vs_post_identified`, `csrf_simulated`, `csrf_token_identified`,
  `missing_token_rejected`, `invalid_token_rejected`,
  `valid_token_accepted`, `origin_rejected`, `samesite_inspected`,
  `csrf_evidence_collected`); several objectives reuse checks
  YC-035.0–YC-035.5 already built (`command`, `cookie_sent`, `path`,
  `request_intercepted`, `file_contains`) — see "Validation" below.
- `app/core/missions/mission_runner.py` — `web_lab_status()` gains a
  `csrf` sub-dict (mirrors `xss`) and `transfers`/`balances` fields (the
  simulated account state, for the Transfer History / balance panels);
  `ai_context()`'s existing `web` section gains a small `csrf` summary;
  no new methods.
- `app/core/missions/mission_loader.py` — one new `MISSIONS` entry;
  `xss-fundamentals`'s `next_mission` now points here instead of `None`.
- `app/templates/labs/terminal.html` / `terminal.css` / `terminal.js` —
  a new **Training Application** section (Transfer Funds, CSRF Token
  panel, Simulated Attacker Page, Attack Flow Visualizer, SameSite Lab,
  Origin/Referer Inspector, GET-vs-POST comparison, CSRF-vs-XSS panel,
  Transfer History, evidence badges), reusing the existing Proxy Control
  panel (now also gated on this mission's id) and HTTP Inspector rather
  than a parallel UI or a second HTTP client.

## Authenticated browsers and automatic credential inclusion

Every request the simulated browser sends already carries whatever
cookies are in `WebLab.session.cookies` (`_open`'s existing
`cookies=sh.web_lab.session.cookies` argument, unchanged since
YC-035.0) — regardless of which command, button, or "page" triggered
the request. This is the entire mechanism the mission demonstrates: the
"Simulated Attacker Page" button builds a request targeting
`cybershop.training` with an `Origin`/`Referer` header set to
`attacker.training`, but the session cookie is still attached
automatically by the same code path every other request already uses —
exactly how a real browser attaches cookies to any request to a given
site, independent of which page initiated it.

## State-changing requests

`POST /transfer` moves a fixed amount between two fictional, in-memory
balances (`WebApp.balances`, `username -> int`) — never a real
financial system, never persisted anywhere real. The training user
("student") starts at `STARTING_BALANCE` (5,000); the fixed recipient
(`TRANSFER_RECIPIENT`, `"training-user"`) starts at 0, matching the
mission's documented starting state. There is deliberately no `GET
/transfer` route at all — requesting it returns `404 Not Found`,
concretely demonstrating that this training site never performs a
state-changing action through GET (see "GET vs. POST" below).

## Vulnerable CSRF scenario

`POST /transfer` checks only the session cookie (`WebApp._session_user`,
unchanged since YC-035.0/.3) — no CSRF token, no Origin/Referer check of
any kind. `GET /csrf-demo` is a purely informational page describing
this: visiting it never itself performs a transfer, it only explains why
the endpoint is vulnerable. Sending the same request shape with an
`Origin: https://attacker.training` header still succeeds (`X-Sim-CSRF-
Kind: attack_simulated`) — proving the endpoint never even inspects
that header, exactly like a real vulnerable CSRF target.

## Simulated attacker page

There is no second host anywhere in this simulator — `attacker.training`
is only ever a header *value* a terminal command can set via `open -H
"Origin: ..."` (the same mechanism YC-035.1 already built for
`Authorization`/`Referer`), never an actual origin this codebase
contacts. The "Simulated Attacker Page" UI box shows the shape of a
malicious auto-submitting form (`POST /transfer`, fixed recipient and
amount) and its **Simulate Request** button builds exactly that
`open -X POST -H "Origin: https://attacker.training" -H "Referer:
https://attacker.training/" -d "recipient=training-user&amount=100"
https://cybershop.training/transfer` command — a student could type the
identical command themselves — and submits it through the same
`exec()`/`/execute` path as every other button on the page. No new HTTP
client, no arbitrary URL fetching, no real cross-origin request, ever.

## Session/cookie simulator

Reused verbatim from YC-035.0/.3 — the Session State panel, the training
`session_id` cookie, and `WebLab.session.cookies` are unchanged. This
mission adds no new cookie/session mechanism; it only demonstrates what
the *existing* one already does (attach automatically, regardless of
request origin).

## CSRF token system

`_csrf_token_for_session(sid)` returns a fixed, deterministic string
derived only from the session id (`"TRAINING_TOKEN_" +
sid.upper().replace("-", "_")`, e.g. `"TRAINING_TOKEN_STUDENT_SESSION"`
for the training account) — never a cryptographic secret, never actual
randomness, so both the Token panel and the mission validator can
compute/verify it independently with no hidden state, the same
discipline as YC-035.1's fixed `API_TOKEN`. `GET /secure-transfer` shows
the logged-in student their own token (`X-Sim-CSRF-Token` header, plus
the value in the body); `POST /secure-transfer` requires the exact same
value as a `csrf_token` body field, rejecting a missing (`X-Sim-CSRF-
Kind: missing_token`) or incorrect (`invalid_token`) one with `403
Forbidden`, and accepting a correct one (`token_valid`) with `200 OK` —
each of the three outcomes provable, not merely asserted.

## SameSite

There is no real cookie-attribute model anywhere in this simulator (as
with YC-035.5's CSP header, this is intentionally informational, not a
new engine). The `samesite strict|lax|none` terminal command prints a
fixed, deterministic explanation for one of the three policy names and
records that the student inspected it (`WebLab.csrf.samesite_inspected`,
a plain counter, not a real cookie flag) — explicitly labeled "simulated,
educational only" and noting that actual browser behavior also depends
on the request type and the browser's own policy, per the ticket's
explicit instruction not to overstate certainty here.

## Origin validation

`POST /secure-transfer` checks the request's `Origin` header **only when
present** — a real browser doesn't always send one, so this never
blocks a request that simply omits it, only one that explicitly carries
an unexpected value (`https://attacker.training` vs. the fixed
`TRUSTED_ORIGIN`, `https://cybershop.training`). The check runs before
the token check, so a forged-origin request is rejected
(`X-Sim-CSRF-Kind: origin_rejected`, `403`) regardless of whether a
valid token was also attached — demonstrating Origin validation as a
genuine, independent layer, while the mission's hints and UI note
explicitly that it is not claimed to be sufficient by itself.

## Referer validation

Referer is carried on every request the same way Origin is (a plain
request header a terminal command can set via `-H`), and the Origin/
Referer Inspector panel displays both from the last request. The
mission and its hints explicitly teach that Referer may be absent or
stripped by real browsers' privacy/security policies, so it is framed
only as a secondary signal — this simulator does not implement a
separate live Referer-rejection path, to avoid teaching it as an
equally strong standalone defense.

## GET vs. POST

The GET-vs-POST panel shows the unsafe design
(`GET /transfer?recipient=training-user&amount=100`) next to this
training site's actual design (`POST /transfer`), and an interactive
**Try GET /transfer** button issues the real request and shows the
resulting `404 Not Found` — concrete, not merely asserted: there is no
GET route for this action at all, so a link, image tag, or prefetch
could never trigger it.

## Vulnerable vs. secure endpoints

`POST /transfer` (vulnerable — cookie only) and `POST /secure-transfer`
(secure — cookie **and** Origin validation **and** token verification)
share one handler, `WebApp._transfer(req, defense=...)`, so the only
behavioral difference between them is exactly the checks documented
above — never two independently-drifting code paths.

## Proxy integration

Reused verbatim from YC-035.2. `app/templates/labs/terminal.html`'s
Proxy Control section gate now includes `'csrf-fundamentals'` alongside
the four prior missions. A student can intercept `POST /transfer`,
forward it, load it into Repeater, and inspect the `Cookie`/`recipient`/
`amount`/`csrf_token` fields exactly like any other captured request.

## Repeater integration

No changes — `repeater`/`repeater send`/`edit body ...`/`edit header
...` already support everything this mission needs: removing
`csrf_token` (edit the body to drop the field), replacing it (edit body
with a new value), changing `amount`, or changing `Origin` (`edit header
Origin ...`), then resending. Only `_track_csrf_response()`'s extra call
inside the `send` branch is new — no second Repeater implementation, no
external requests.

## HTTP history

No changes — the existing `requests`/`history` tab already lists every
`POST /transfer`, `POST /secure-transfer`, and `GET /transfer-history`
exchange in order, exactly like every prior web mission.

## Request inspector / response inspector

No changes — the existing HTTP Inspector's Request/Response/Headers/
Body/Cookies/History tabs already surface `Cookie`, `Origin`, `Referer`,
and body parameters (including `csrf_token`) for any request, and
`200`/`403`/`401` status codes with their JSON `message` field for any
response — the same shared component every prior mission uses, never a
parallel one. No internal stack traces are ever exposed; every rejection
reason is one of the fixed, deterministic messages `WebApp._transfer`
returns.

## Evidence collection

The Transfer History panel, evidence badges (Attack simulated / Token
viewed / Missing token / Invalid token / Valid token / Origin rejection /
SameSite inspections), and balance display are all pure views over
`web_lab_status()`'s `csrf`/`transfers`/`balances` fields — the same
"server computes structured state once, the browser only renders it"
discipline as every prior mission's panels. The final objective
additionally requires `evidence`/`inspect N` against the fixed
investigation transcript.

## Mission objectives (17, 750 XP)

Identifying CSRF via `web` (35) → confirming the authenticated browser's
automatic cookie attachment (35) → identifying `POST /transfer` as a
state-changing request (40) → intercepting it via Proxy (40) →
inspecting the attached session cookie (35) → reading the vulnerable-
endpoint explanation at `/csrf-demo` (35) → running the simulated
attacker request (55) → articulating why the server trusted it (35) →
confirming no `GET /transfer` route exists (40) → identifying the CSRF
token at `/secure-transfer` (40) → a missing-token rejection (45) → an
invalid-token rejection (45) → a valid-token acceptance (45) →
inspecting all three SameSite policies (45) → an Origin rejection (45) →
an evidence-collection checkpoint (55) → the final investigation (80).

### Final investigation — "The Unexpected Transfer"

A new, independent scenario (`csrf-investigation`), registered in
`_INVESTIGATION_BUILDERS` alongside `login-flow`, `content-type-bug`,
`profile-mismatch`, `auth-lifecycle`, `sqli-investigation`, and
`xss-investigation`: a bug report says "a training user's balance
changed after they visited an unrelated page — they never clicked
transfer." The five-request transcript — a login → a legitimate transfer
→ a forged-looking transfer (attacker `Origin`/`Referer`, but the
browser's own session cookie) succeeding against the vulnerable
endpoint → the same shape rejected by the secure endpoint → the same
shape succeeding once the correct token is included — shows the
vulnerability and its fix side by side. Graded identically to every
prior mission's final objective: `evidence`/`inspect N` to read the log,
then a conclusion recorded via `echo "..." > web/csrf-investigation.txt`,
validated with the existing `file_contains` check (requiring the phrase
"anti-csrf token").

## Validation

Ten new `check` values on the existing `type: "web_state"` (no new
validator type, per this project's established discipline):

- **`state_change_identified`** — the last request hit `POST /transfer`.
- **`get_vs_post_identified`** — the last request hit `GET /transfer`
  and the response was `404`.
- **`csrf_simulated`** — `WebLab.csrf.attack_simulated` is set (a
  vulnerable `/transfer` response carrying `X-Sim-CSRF-Kind:
  attack_simulated` — i.e. the request's `Origin` was the fixed
  attacker value).
- **`csrf_token_identified`** — `WebLab.csrf.token_viewed` is set (a
  `GET /secure-transfer` response was received while authenticated).
- **`missing_token_rejected`** — the last response is `403` with
  `X-Sim-CSRF-Kind: missing_token`.
- **`invalid_token_rejected`** — the last response is `403` with
  `X-Sim-CSRF-Kind: invalid_token`.
- **`valid_token_accepted`** — the last response is `200` with
  `X-Sim-CSRF-Kind: token_valid`.
- **`origin_rejected`** — the last response is `403` with
  `X-Sim-CSRF-Kind: origin_rejected`.
- **`samesite_inspected`** — `WebLab.csrf.samesite_inspected` has
  reached the expected count (`3`, one per policy).
- **`csrf_evidence_collected`** — a capstone conjunction of all six
  `CsrfLabState` flags (attack simulated, token viewed, missing/invalid/
  valid token, Origin rejected). **Deliberately a distinct name from
  YC-035.4's `evidence_collected` and YC-035.5's `xss_evidence_collected`**
  (not a reuse) — each reads its own mission's `WebLab` sub-state and
  would silently never pass for a student who only touched this
  mission's endpoints if the names collided;
  `TestCsrfValidatorChecks::test_csrf_evidence_collected_does_not_reuse_other_missions_evidence_checks`
  guards this directly.

**Explicitly reused, not duplicated**: the opening "identify CSRF"
objective reuses the existing `command` type (`web`); "authenticated
browser" and "inspect credentials" reuse YC-035.3's `cookie_sent`
check; "capture request" reuses YC-035.2's `request_intercepted`; "the
vulnerable endpoint" reuses the existing generic `path` check; the final
investigation reuses `file_contains`, matching every prior mission.

## Hints

Every objective has three progressive hints (a nudge, a narrower nudge,
then the exact command), following the same pattern established since
YC-035.1 — `MissionRunner.use_hint()` advances one step per re-ask,
capped at the last entry, unchanged.

## CyberMentor integration

`ai_context()`'s existing `web` section (built up across
YC-035.0–.5) gains a small `csrf` summary:

```python
ctx["web"]["csrf"] = {
    "last_csrf_kind": "attack_simulated" | "token_shown" | "missing_token"
                     | "invalid_token" | "token_valid" | "origin_rejected"
                     | "unauthenticated" | "invalid_amount" | "vulnerable_success" | None,
    "attack_simulated": bool,
    "token_viewed": bool,
    "missing_token_rejected": bool,
    "invalid_token_rejected": bool,
    "valid_token_accepted": bool,
    "origin_rejected": bool,
    "samesite_inspected": int,
    "transfer_count": int,
}
```

Small and structured, so CyberMentor can explain *why* the vulnerable
transfer worked without a CSRF token — e.g. answering "the request was
authenticated through your session cookie, but the vulnerable endpoint
never verified the request's intent with an anti-CSRF mechanism" from
actual mission state (`last_csrf_kind`, `attack_simulated`) — without
repeating full request/response bodies on every turn, and without ever
solving the objective for the student. As with every mission before it:
`ai_context()` is a documented extension point, but the live
`/api/ai/chat` path doesn't currently thread mission state into the
prompt — this hook is built for consistency with the established
precedent, not as new chat wiring.

## Security isolation

Same guarantees as every prior web mission, re-verified for the new
surface:

- `web.py` and `commands.py` still import nothing network- or
  database-capable (AST-based tests, matching YC-035.4/.5's precedent).
- Every new route (`/csrf-demo`, `/secure-transfer`, `/transfer-history`)
  sits behind the exact same `host != HOST` rejection `open`/`request`
  already enforce — tested directly with `evil.example.com`.
- `attacker.training` never resolves to, or contacts, a second host —
  it is structurally only ever a header *value* on a request whose
  `host` field is still the one simulated `cybershop.training` app;
  `test_attacker_origin_never_reaches_a_second_host` asserts this
  directly against `HttpRequest.host`.
- No real cookie, session, or credential is ever exposed — the session
  cookie remains the same fictional `session_id` jar from YC-035.0/.3,
  and the training CSRF token is a fixed, non-secret, deterministic
  string, never real randomness or a real secret.
- No arbitrary URL fetching, no external form submission, no phishing
  or credential-harvesting functionality exists anywhere in this
  module — the "attacker page" is UI text plus one terminal command,
  not a hosted page of any kind.
- `WebLab.csrf`/`WebApp.balances`/`WebApp.transfers` state is
  per-instance, like every other `WebLab` field — two students, or two
  test cases, never share state.
- No real JavaScript execution, `eval`, `exec`, or dangerous DOM APIs
  (`document.write`, `Function(...)`, `fetch`, `XMLHttpRequest`) appear
  anywhere in `web.py` or the CSRF section of `terminal.js` — asserted
  directly against the shipped source.

## UI — Training Application section

A new section (`app/templates/labs/terminal.html`, styled in
`terminal.css`, driven by `terminal.js`), shown only for this mission
(gated on `mission.mission.id == 'csrf-fundamentals'`), placed above the
existing Proxy Control panel and HTTP Inspector so
Request/Response/Headers/Body/Cookies/History stay a single shared
component rather than being duplicated:

- **Transfer Funds box**: recipient/amount fields and a **Transfer
  (Vulnerable)** button, plus a **View History** shortcut.
- **CSRF Token box**: a **View My Token** button, a live token display,
  a `csrf_token` input, a **Secure Transfer** button, and dedicated
  **Send Missing Token** / **Send Invalid Token** buttons.
- **Simulated Attacker Page box**: a visual mock of the malicious
  request shape and a **Simulate Request** button — visually marked
  (red-tinted border) to distinguish it from the legitimate application.
- **Attack Flow Visualizer**: seven clickable steps (Attacker-Controlled
  Page → Victim Visits Page → Browser → Session Cookie Auto-Attached →
  cybershop.training → State-Changing Request → Transfer Occurs), each
  showing a short explanation on click, labeled "Simulated CSRF flow."
- **SameSite Cookie Lab**: three buttons (Strict/Lax/None), each
  running the `samesite` command and displaying its explanation.
- **Origin/Referer Inspector**: an Origin selector (none / trusted /
  attacker) with a **Send to Secure Transfer** button, plus a live view
  of the last request's `Origin`/`Referer` headers.
- **GET vs. POST panel**: the unsafe vs. actual request shape, with an
  interactive **Try GET /transfer** button showing the real `404`.
- **CSRF vs. XSS panel**: a static side-by-side comparison.
- **Transfer History**: a live list (from `web_lab_status.transfers`),
  each entry tagged "(vulnerable — cookie only)" or "(secure — token
  verified)".
- **Evidence badges**: a pure view over `WebLab.csrf`'s flags — always
  labeled text, never color alone.

Every button here does exactly one thing: build an `open ...` (or
`samesite ...`) command string a student could type themselves and
submit it through the same `exec()`/`/execute` path the terminal input
and every other mission's buttons already use — no new HTTP client, no
real cross-origin request, no live attacker infrastructure.

## Accessibility & responsive design

Reuses every existing pattern verbatim: real `<button>` elements,
`:focus-visible` rings, the page's global `prefers-reduced-motion` rule,
`aria-live` already on the terminal output. Every evidence badge and
history entry is communicated as text, never by color alone (e.g.
"Attack simulated: seen" / "not seen", "(vulnerable — cookie only)" /
"(secure — token verified)"). Security states are always explicit labels
("Authenticated"/"Unauthenticated", token viewed/missing/invalid, Origin
accepted/rejected) reusing the Session State panel's existing pattern.
The new grids use `repeat(auto-fit, minmax(...))` so they reflow to a
single column under narrow viewports with no bespoke breakpoint logic,
matching how the Proxy Control and XSS grids already stack.

## Achievement

"Request Guardian" was evaluated and **not** added as a database row —
the same reasoning as every prior mission's optional achievement in this
series (HTTP Detective, Proxy Operator, Session Detective, Query
Detective, Context Hunter): the achievement metric calculator doesn't
yet track a mission-completion metric keyed by mission id, so a new row
would never unlock. The existing generic mission-completion/XP-based
achievements still run unchanged.

## Testing

`tests/test_csrf_fundamentals.py` — `WebApp` routing for every new
route (auth-gated pages, the vulnerable/secure transfer split, forged-
Origin acceptance on the vulnerable endpoint, Origin/token rejection
paths on the secure endpoint, the missing GET route, transfer history),
the deterministic session-bound token helper, `_track_csrf_response()`'s
wiring through `open`/`forward`/`repeater send`, save/restore of
`WebLab.csrf` and transfer/balance state, the ten new validator checks
(including graceful failure with no `web_lab`, and a dedicated
regression guard against colliding with YC-035.4/.5's evidence-check
names), the `csrf-investigation` scenario's determinism and isolation
from live session state, mission registration/loading (17 objectives,
XP sums to 750, progressive hints, chaining after `xss-fundamentals`), a
full scripted solve plus a "no premature completion" guard,
`web_lab_status`/`ai_context` reflecting CSRF and transfer state,
security isolation (no network/DB-capable imports, no real second host
ever contacted, no `eval`/dangerous DOM APIs in either the Python module
or the CSRF section of `terminal.js`, state never leaking across
instances), a full HTTP-level chain (locked → available after completing
XSS Fundamentals → completed, with real XP/level/dashboard stats), and
page/API reachability (the Training Application section present only on
this mission, `/execute` returning CSRF state, the hint endpoint
advancing progressively).

`tests/test_xss_fundamentals.py` — one updated assertion:
`xss-fundamentals["next_mission"]` is now `"csrf-fundamentals"` instead
of `None`, since this mission is no longer terminal in the chain (same
pattern YC-035.5 applied to `test_sql_injection_fundamentals.py`).

## Manual browser test

1. Log in, open `/terminal/mission/csrf-fundamentals` (unlocks after
   completing XSS Fundamentals).
2. Confirm the mission header, objectives sidebar, the new **Training
   Application** section (Transfer Funds, CSRF Token, Simulated Attacker
   Page boxes, Attack Flow Visualizer, SameSite Lab, Origin/Referer
   Inspector, GET-vs-POST panel, CSRF-vs-XSS panel, Transfer History,
   evidence badges), the Proxy Control panel, and the HTTP Inspector all
   render.
3. In the Transfer Funds box, click **Transfer (Vulnerable)** — confirm
   a `200 OK` response and the objectives sidebar advances.
4. Turn Proxy intercept ON, click **Transfer (Vulnerable)** again —
   confirm it's intercepted (inspect the `Cookie`/`recipient`/`amount`
   fields), then **Forward**.
5. Click **Simulate Request** on the Simulated Attacker Page box —
   confirm the response still succeeds (`200 OK`) even though it carries
   an `attacker.training` Origin, and confirm no real network request
   left the browser (check the address bar/tab count is unchanged).
6. Click through the Attack Flow Visualizer's seven steps — confirm each
   shows a distinct explanation, and the "Simulated CSRF flow" label is
   visible.
7. Click **Try GET /transfer** — confirm a `404 Not Found` result.
8. Click **View My Token** — confirm the training `csrf_token` value
   appears.
9. Click **Send Missing Token** — confirm `403 Forbidden`.
10. Click **Send Invalid Token** — confirm `403 Forbidden`.
11. With the real token still in the token field, click **Secure
    Transfer** — confirm `200 OK`.
12. In the Origin/Referer Inspector, select the attacker origin and
    click **Send to Secure Transfer** — confirm `403 Forbidden` even
    though the token field still holds a valid token.
13. Click each SameSite Lab button (Strict/Lax/None) — confirm each
    shows a distinct explanation, and only "None" reports the cookie
    would still attach cross-site.
14. Open the History tab — confirm every request above is present and
    inspectable.
15. Complete the final investigation objective (`evidence`, `inspect
    1`–`5`, then the `echo ... > web/csrf-investigation.txt` command);
    confirm the completion overlay shows 750 XP.
16. Open AI Mentor, ask "why did the vulnerable transfer work without a
    CSRF token?" — confirm the answer reflects the actual mission state
    (the vulnerable endpoint's lack of token/Origin checks), not a
    generic definition.
17. Refresh the page — confirm mission progress, XP, transfer history,
    and the evidence badges all survive.
18. Attempt `open https://evil.example.com/csrf-demo` — confirm the
    exact rejection message and that nothing new appears in the
    Inspector; confirm at no point does any button on this page open a
    new tab, navigate away, or contact any host other than
    `cybershop.training`.

## Windows commands

```powershell
$env:PYTHONPATH = "."
python -m pytest tests/test_csrf_fundamentals.py -q
python -m pytest tests/ -q
venv\Scripts\ruff.exe check app\core\terminal\web.py app\core\terminal\commands.py app\core\missions\mission_validator.py app\core\missions\mission_runner.py app\core\missions\mission_loader.py tests\test_csrf_fundamentals.py tests\test_xss_fundamentals.py
```
