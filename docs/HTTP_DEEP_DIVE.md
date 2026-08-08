# HTTP Deep Dive Mission (YC-035.1)

## Purpose

The second mission in the Web Security learning path, chained after
YC-035.0 (Web Fundamentals). Moves the student from "I know what HTTP is"
to "I can read and reconstruct an HTTP exchange": JSON APIs, the
Authorization header, Referer, cache headers, URL-encoding, and
reconstructing a multi-request chain from history. Still purely
educational — no injection, no session hijacking, no real network request
ever made. SQL injection, XSS, CSRF, SSRF, and auth attacks are explicitly
out of scope for this mission (they belong to later missions in the path).

## Architecture — extends, doesn't duplicate

No new module. Everything lives in the same `app/core/terminal/web.py`
built for YC-035.0, extended in place — `WebApp` gained new routes and two
new auth mechanisms, `build_request()` gained an `extra_headers` param, a
`parse_body()` helper was added, and a second fixed investigation
transcript was added alongside the first via a small scenario registry.
`MissionValidator`, `MissionRunner`, and the terminal command layer
(`commands.py`) were extended the same way — new checks/commands added to
their existing single implementations, never new parallel systems.

## New routes

| Route | Method | Behavior |
|---|---|---|
| `/auth/login` | POST | Alias of `/login`'s POST handler — lets the ticket's exact chain example (`GET /login → /auth/login → POST /auth/login`) work without changing YC-035.0's existing `/login` behavior |
| `/api/login` | POST | JSON login: `{"username":..,"password":..}` in, `{"status":"success","message":"Authentication successful"}` (200) or an error body (401) out — no cookie set, matching the ticket's worked example |
| `/api/profile` | GET/POST | JSON counterpart to `/profile`, session-cookie protected (same mechanism as the HTML page) |
| `/api/me` | GET | `Authorization: Bearer training-token-001` protected — returns `{"username": "student"}`. Deliberately **not** cookie-accepting, so cookie-session auth and bearer-token auth read as two distinct concepts, not the same thing in different clothes |
| `/products?id=N` | GET | Now also carries `Cache-Control: max-age=60`, `ETag: "product-N-v1"`, `Last-Modified` — fixed, deterministic values, not a cache engine |

Training credentials and the training token are unchanged/fixed, never
real secrets: `student`/`training123` (+`analyst`, `admin`), token
`training-token-001`.

## Request model changes

`build_request()` gained `extra_headers: dict[str, str] | None` — applied
*after* the existing defaults, so a caller can override `Content-Type`
(to send JSON instead of form data) or add `Authorization`/`Referer`. The
`open` terminal command exposes this as a repeatable curl-like `-H "Key:
Value"` flag:

```
open -X POST -H "Content-Type: application/json" -d '{"bio": "training"}' https://cybershop.training/api/profile
open -H "Authorization: Bearer training-token-001" https://cybershop.training/api/me
open -H "Referer: https://cybershop.training/" https://cybershop.training/products
```

## Body parsing

`parse_body(body, content_type)` is the new counterpart to the existing
`_parse_form()` — routes to `json.loads` when the Content-Type contains
"json", otherwise to form parsing. Used by `WebApp._check_credentials()`
(shared by both the form and JSON login endpoints — one function, two
wire formats) and by the new `body_field` validator check. Pure parsing,
same isolation guarantee as the rest of the module.

## Two authentication mechanisms, kept conceptually separate

- `WebApp._session_user(req)` — cookie-based, used by `/profile` and
  `/api/profile`.
- `WebApp._bearer_user(req)` — `Authorization: Bearer <token>`-based,
  used only by `/api/me`.

Deliberately not merged into one "check either" helper for `/api/me`, so
the objective that exercises it can only be satisfied by actually using
the Authorization header — not by having a leftover session cookie.

## Request history

`WebSession.history` (already existed from YC-035.0) is exposed via a new
`requests` terminal command — a numbered list, the same rendering pattern
as `evidence`/`packets`. Kept as a separate command from the shell's own
`history` (which lists typed commands, not HTTP traffic) to avoid
overloading an existing, differently-scoped command name.

## Redirect-chain reconstruction

Objective `hd-13` requires the student to actually perform, in one
session, `GET /login` → `GET /auth/login` → `POST /auth/login`, in that
order — not just visit the destinations individually. Validated by a new
`history_sequence` check (below) that scans the session's own history for
that exact ordered subsequence.

## Validation changes

Three new `check` values added to the **existing** `web_state` type
(YC-035.0) — no new validator type, per the ticket's explicit "extend
MissionValidator only where required":

- **`body_field`** — parses the request or response body (via
  `parse_body()`) and checks one field's value. Structured, so it can't be
  satisfied by unrelated text elsewhere containing the expected value.
- **`history_sequence`** — checks that an ordered list of `"METHOD path"`
  tokens appears, in order (not necessarily contiguous), in the session's
  request history. Reuses the existing match-as-list mechanism
  (`_match_candidates`, YC-034.8) as the ordered sequence itself, rather
  than "any of these" alternatives.
- **`request_count`** — checks the session has made at least N requests.
  Defined for completeness (the ticket lists it) but not needed by any of
  this mission's 14 objectives, since `history_sequence` is the stronger
  check wherever request count would otherwise apply.

`header_exists`/`header_value`/`cookie_exists`/`cookie_value`/
`redirect_location`/`status_code`/`request_method`/`request_path`/
`response_content_type` from the ticket's suggested list were **not**
added as new checks — YC-035.0's existing `header`, `cookie`,
`redirect_location`, `status_code`, `method`, and `path` checks already
cover exactly the same ground (a `header` check already parametrizes
existence-vs-value and request-vs-response via its `in` field). Adding
near-duplicate check names would fragment the validator for no
behavioral gain.

One caught bug during implementation: `_validate_web_state`'s
`history_sequence` branch initially referenced the wrong local variable
(`candidates`, computed once for single-value checks, instead of a
fresh list built from `v["match"]`) — a `NameError` caught immediately
by the first smoke test, fixed by computing the ordered sequence
directly inside that branch.

## Mission objectives (14, 500 XP)

Request line → status line → request header → response header → form
encoding → JSON request → URL-decoding → redirect → session cookie →
Authorization header → Referer header → cache headers → chain
reconstruction (60 XP) → final investigation (60 XP).

### Final investigation — a new, independent scenario

YC-035.0's final objective used a fixed transcript ("Alex" never
submitted the login form). This mission needs a *different* scenario per
the ticket ("a user successfully logs in but their profile loads
incorrectly"), so `web.py` now has a small scenario registry:

```python
_INVESTIGATION_BUILDERS = {
    "login-flow": build_investigation_log,        # YC-035.0
    "content-type-bug": build_content_type_bug_log,  # YC-035.1
}
build_web_lab(scenario: str = "login-flow") -> WebLab
```

`MissionRunner._attach_web_lab` reads the mission's `web_lab` config —
`True` (legacy boolean, still works, defaults to `"login-flow"`) or a
scenario-name string — fully backward compatible with YC-035.0's existing
`"web_lab": True`.

The new transcript: login succeeds (form submitted, redirect followed,
cookie set), then the profile request succeeds too (status 200, correct
body) — but the response's `Content-Type` is `application/json` instead
of `text/html`. A benign misconfiguration bug, not an attack, and not an
authentication failure — the "loads incorrectly" report is explained by
one wrong header, which the student must notice by actually reading the
transcript, not be told outright. The 7 evidence questions in the ticket
(what starts the flow, which request submits credentials, which response
redirects, where the session is created, which request sends the cookie,
which response returns the profile, what Content-Type comes back) are
all directly answerable by inspecting the 4-entry transcript in order.

## Progressive hints

Every prior mission's objectives had one `"hint"` string. This ticket
explicitly asks for escalating hints that never hand over the answer on
the first ask, so `MissionRunner.use_hint()` now supports a second
shape: an objective can define `"hints": [level0, level1, level2, ...]`
instead of `"hint"`. Each further hint request for the *same* objective
advances one level deeper (tracked per-objective in
`MissionProgress.hint_index`, persisted through `save_state`/
`from_state`), capped at the last entry. Objectives without a `"hints"`
list keep working exactly as before via `"hint"` — all nine prior
missions are unaffected. All 14 objectives in this mission use 2–3 level
progressive hints: a conceptual nudge, then a narrower pointer, then the
concrete command.

## CyberMentor integration

`ai_context()`'s existing `web` section (added in YC-035.0) is extended
with headers, cookies, and a short recent-history summary — not the full
request/response objects the browser's HTTP Inspector needs, to avoid
padding every mentor turn with repeated raw bodies:

```python
ctx["web"] = {
    "logged_in_as": ..., "last_path": ..., "last_status": ...,
    "last_request_headers": {...}, "last_response_headers": {...},
    "cookies": {...}, "recent_history": ["GET /login -> 302", ...],
}
```

The ticket also asked for a "mistakes" field. There is no existing
mechanism anywhere in the codebase that tracks failed validation
attempts (only successful ones feed `completed_ids`); adding one would be
a new, currently-unused tracking structure with no consumer beyond this
one field. Evaluated and not added, for the same reason every prior
mission's optional-but-unsupported tracking idea (e.g. "missions
completed" for achievements) was skipped — `hints_used` and `attempts`
(already present at the top level of `ai_context()`) are the closest
existing signals of struggle.

## Security isolation

Same guarantees as YC-035.0, re-verified for every new route: `web.py`
still imports nothing network-capable (`json` and `collections.abc` are
the only new imports, both pure stdlib with zero I/O). `open`/`request`
still reject any host other than `cybershop.training` before constructing
a request at all. Unknown routes (including well-formed-looking ones like
`/api/does-not-exist`) fall through to the existing 404 handler — nothing
new was added that could dispatch outside the registered route table.

## UI — HTTP Inspector (hard requirement)

Unlike YC-035.0 (where a tabbed inspector was evaluated and skipped in
favor of the terminal's own text commands), this ticket explicitly
requires browser-reachable interactivity, so a real component was built:
a collapsible **HTTP Inspector** panel below the terminal
(`app/templates/labs/terminal.html`, styled in `terminal.css`, driven by
`terminal.js`), shown only for missions with a web lab attached.

- **Tabs**: Request / Response / Headers / Body / Cookies / History —
  exactly the ticket's list, standard accessible tab pattern (`role="tab"`/
  `"tabpanel"`, `aria-selected`, `aria-controls`).
- **Data source**: `MissionRunner.web_lab_status()` was enriched (still
  the same field, no new API surface) to carry the full last
  request/response (via `dataclasses.asdict`) and a bounded history (last
  20, matching `WebSession.to_dict()`'s existing cap) — the same JSON
  already returned by `/execute`, `/start`, and `to_dict()`. The page
  seeds the inspector from server-rendered state via a small
  `<script type="application/json">` blob, then keeps it live via the
  exact same `d.web_lab_status` field the NETWORK STATUS/PACKET LAB/WEB
  SESSION panels already consume — no new endpoint.
- **History tab**: clicking any past entry re-renders the Request/
  Response/Headers/Body tabs with *that* exchange's data, client-side,
  since the full objects are already present in the payload.
- **Request Builder** (optional per the ticket, built anyway since it
  integrates cleanly): Method/Path/Query/Headers/Body fields + Send/Clear,
  which constructs an `open ...` command string and submits it through
  the terminal's existing `exec()` — the same command path the student
  would type by hand, so "only registered simulated routes" is enforced
  exactly once, server-side, with no separate code path to keep in sync.
  Values are wrapped in POSIX single quotes (`'...'`, with `'\''` for any
  embedded literal quote) rather than double-quote-escaping a JSON body,
  avoiding any escaping ambiguity between the builder's JSON textarea and
  the shell's own tokenizer.
- **HTTP vs HTTPS**: a small always-visible visual block above the tabs
  (`You ──────→ Server` / `You ──🔒 TLS──→ Server`, plus one line each on
  plaintext-vs-encrypted/tamper-evident/identity-verified) — conceptual
  only, explicitly not a real TLS implementation, matching the ticket's
  own example diagram.

## Responsive design & accessibility

The inspector panel sits full-width below the existing two-column
`.tm-layout` (sidebar + terminal), so it naturally stacks on narrow
viewports without a bespoke breakpoint; its own tab bar wraps instead of
overflowing, and every text panel uses `white-space: pre-wrap` +
`word-break: break-word` inside a scrollable container so long header
values or JSON bodies never force horizontal page scroll. Tabs and the
collapse toggle are real `<button>` elements with visible focus rings
(`:focus-visible`) and correct ARIA wiring; the project's existing global
`prefers-reduced-motion` rule (`* { animation: none; transition: none }`)
already covers this new component with no extra work.

## Achievement

"HTTP Investigator" was evaluated and not added as a database row — same
reasoning as every prior mission's optional achievement in this series
(HTTP Detective, Packet Detective, Recon Scout, Network Detective): the
achievement metric calculator doesn't yet track "missions completed", so
a new row would never unlock. The existing generic mission-completion
achievement check still runs unchanged.

## Manual browser test

1. Log in, open `/terminal/mission/http-deep-dive` (unlocks after
   completing Web Fundamentals).
2. Confirm the mission header, objectives sidebar, and WEB SESSION panel
   render, and the HTTP Inspector panel is visible below the terminal
   with its HTTP-vs-HTTPS visual and six tabs.
3. `open https://cybershop.training/products` — confirm the Request tab
   shows the request line and the Response tab shows the status line.
4. `headers` — confirm Request/Response headers both appear (Headers tab
   mirrors this).
5. `open -X POST -d "username=student&password=training123" https://cybershop.training/auth/login`
   — confirm the Body tab shows the form-encoded request body.
6. `open -X POST -H "Content-Type: application/json" -d '{"bio": "x"}' https://cybershop.training/api/profile`
   — confirm the Body tab shows the JSON body and Headers shows
   `Content-Type: application/json`.
7. `open https://cybershop.training/search?q=web%20security` — confirm
   the decoded query.
8. `open https://cybershop.training/login` — confirm a 302 with
   `Location: /auth/login` in the Response tab.
9. `cookies` — confirm `session_id` appears (Cookies tab mirrors this).
10. `open -H "Authorization: Bearer training-token-001" https://cybershop.training/api/me`
    — confirm `{"username": "student"}` in the Response/Body tabs.
11. `open -H "Referer: https://cybershop.training/" https://cybershop.training/products`
    — confirm the Referer header in the Request tab.
12. `open https://cybershop.training/products?id=42` — confirm
    `Cache-Control`/`ETag`/`Last-Modified` in the Response tab.
13. `requests` — open the History tab, click an earlier entry, confirm
    the other tabs update to that entry's data.
14. Complete the chain-reconstruction and final-investigation objectives;
    confirm the completion overlay shows 500 XP.
15. Open AI Mentor, ask "what is Content-Type?" while mid-mission —
    confirm the answer references the current response's actual value.
16. `open https://evil.example.com/` — confirm the exact rejection
    message and that nothing appears in the Inspector as a new exchange.

## Windows commands

```powershell
$env:PYTHONPATH = "."
python -m pytest tests/test_http_deep_dive.py -q
python -m pytest tests/ -q
venv\Scripts\ruff.exe check app\core\terminal\web.py app\core\terminal\commands.py app\core\missions\mission_validator.py app\core\missions\mission_runner.py app\core\missions\mission_loader.py tests\test_http_deep_dive.py
```
