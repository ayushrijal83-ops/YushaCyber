# Authentication & Sessions Mission (YC-035.3)

## Purpose

The fourth mission in the Web Security learning path, chained after
YC-035.0 (Web Fundamentals), YC-035.1 (HTTP Deep Dive), and YC-035.2
(Burp Suite Fundamentals). Teaches how web authentication actually
works — login, logout, sessions, cookies, protected routes, and
authorization — entirely inside the existing simulated training
environment (`cybershop.training`), using the same simulated browser,
HTTP inspector, and intercepting proxy the last two missions already
built. Still purely educational: no session hijacking, no credential
attacks, no real authentication provider, and no real network request
ever made. Session exploitation (fixation, hijacking, forging a session
identifier) is explicitly out of scope — it belongs to a later mission.

## Architecture — extends, doesn't duplicate

No new mission engine, HTTP simulator, proxy, XP engine, AI mentor, or
cookie/session engine. Everything lives in the same modules built for
YC-035.0–YC-035.2:

- `app/core/terminal/web.py` — `WebApp` gains three new browser-style
  protected routes (`/account`, `/dashboard`, `/admin`) and a `POST
  /logout` alongside the existing `GET /logout`; `HttpResponse` gains a
  `deleted_cookies` list so a response can tell the browser to *remove*
  a cookie, distinct from `cookies` (which only ever holds values being
  *set*); `WebApp.expire_session()` is a new, deliberately
  simulator-controlled way to invalidate a session server-side without
  touching the browser's cookie jar; a new fixed investigation
  transcript (`build_auth_lifecycle_log`) is added to the existing
  scenario registry.
- `app/core/terminal/commands.py` — one new `@cmd("expire")` function
  alongside the ones already registered; `web`'s status text lists the
  three new routes and documents `expire`.
- `app/core/missions/mission_validator.py` — three new `check` values
  added to the existing `web_state` type (`cookie_sent`,
  `logout_completed`, `session_expired`); every other objective in this
  mission reuses checks YC-035.0–YC-035.2 already built (`status_code`,
  `method`, `body_field`, `cookie`, `redirect_location`,
  `session_authenticated`) — see "Validation" below.
- `app/core/missions/mission_runner.py` — `web_lab_status()` gains
  `authenticated`/`session_present`/`expired_count`; `ai_context()`'s
  existing `web` section gains a security-filtered authentication
  summary with a masked session id; no new methods.
- `app/core/missions/mission_loader.py` — one new `MISSIONS` entry;
  `burp-fundamentals`'s `next_mission` now points here instead of
  `None`.
- `app/templates/labs/terminal.html` / `terminal.css` / `terminal.js` —
  a new **Session State** panel and a static authentication-flow
  reference diagram, reusing the existing Proxy Control panel and HTTP
  Inspector (Request/Response/Headers/Body/Cookies/History tabs,
  `web_lab_status` data source, `exec()` submission path) rather than a
  parallel UI.

## Cookie deletion (`deleted_cookies`)

`HttpResponse.cookies` (YC-035.0) only ever holds values a response is
*setting*; there was no way for a response to say "delete this cookie"
until logout needed exactly that. `HttpResponse.deleted_cookies: list[str]`
is a new, separate field for cookie *names* being removed. `render_response`
renders each as the real wire form, `Set-Cookie: name=; Max-Age=0`, and
`WebSession.record()` drops the name from the browser's own jar — the
same distinction a real browser draws between "store this Set-Cookie"
and "delete this Set-Cookie," modeled as two fields instead of one
`cookies` dict overloaded with `None`-as-delete sentinels.

## Login, logout, and the new protected routes

`_login` (unchanged from YC-035.0/YC-035.1) still sets `session_id` on
success and redirects to `/profile`; its 401 failure body is now
JSON — `{"error": "Invalid training credentials"}` — matching the
exact shape the spec calls for, while the underlying 401 status code
YC-035.0 already locked in in `test_web_fundamentals.py` is unchanged.

`POST /logout` (new) invalidates the server-side session exactly like
the pre-existing `GET /logout`, but additionally queues `session_id` in
`deleted_cookies` and redirects to `/login` instead of `/`. **`GET
/logout`'s original behavior (redirect to `/`, no explicit cookie
deletion header) is left untouched** so YC-035.0/YC-035.1/YC-035.2 keep
passing byte-for-byte — verified by
`test_get_logout_still_redirects_home`.

Three new routes demonstrate that "protected route" has more than one
correct shape in the wild:

| Route | Unauthenticated | Authenticated |
|---|---|---|
| `/profile` (existing) | `401 Unauthorized` | `200 OK` |
| `/account` (new) | `302 Found` → `/login` | `200 OK` |
| `/dashboard` (new) | `302 Found` → `/login` | `200 OK` |
| `/admin` (new) | `401 Unauthorized` | `403 Forbidden` (unless the fictional `admin` account), else `200 OK` |

`/admin` is the mission's authentication-vs-authorization exhibit:
authenticating as `student` succeeds, but `student` is still not
`admin` — the request is denied with `403`, not `401`, because the
server *does* know who's asking; it just says no. Only the training
account `admin`/`admin123` (already defined in `_USERS` since
YC-035.0, never previously reachable through any mission) may pass.

## Session expiration (`expire_session`)

A student can trigger simulated expiration on demand with the new
`expire` terminal command, which calls `WebApp.expire_session(sid)`.
Server-side this does exactly what logout does — the session is
removed from `self.sessions` — but it **never touches the browser's
cookie jar**. The point is the contrast with logout: after `expire`,
`cookies` still shows `session_id=...` in the student's own jar, yet
the next protected request is rejected, because validity is a
server-side fact the browser cannot see or control. This is
deterministic and simulator-controlled by design (an explicit command),
never tied to wall-clock time, so it can never be flaky in tests or
unpredictable for a student mid-mission.

`WebLab.expired_count` (a plain counter, mirroring `ProxyState`'s
counters rather than a new dataclass for one field) distinguishes "this
session died because of `expire`" from "because of logout," backing the
`session_expired` validator check and the Session State panel's
"Expires" field.

## Validation

Three new `check` values on the existing `type: "web_state"` (no new
validator type, per this project's established discipline):

- **`cookie_sent`** — inspects the *last request actually sent*
  (`req.cookies`), i.e. "did the browser attach this cookie to a
  request?" Distinct from the pre-existing `cookie` check, which
  inspects the client-side jar (`lab.session.cookies`), i.e. "has the
  browser ever received this cookie?" The two can differ — a cookie can
  sit in the jar between receiving it and using it.
- **`logout_completed`** — requires the last exchange to actually be a
  `POST /logout` whose response both returned a redirect status and
  listed the cookie name in `deleted_cookies`, not just "some 302
  happened."
- **`session_expired`** — compares `lab.expired_count` against the
  expected count, matching the shape of every proxy counter check from
  YC-035.2.

**Explicitly reused, not duplicated** — most of the ticket's suggested
check names map exactly onto checks earlier missions already built:
`authenticated`/`login_success` → `session_authenticated`/`status_code`
(302 on login), `unauthenticated`/`protected_route` → `status_code`
(401) or `redirect_location` (302 → `/login`), `login_failure` →
`status_code` (401), `set_cookie_exists` → `cookie`,
`request_contains_cookie`/`request_missing_cookie` → `cookie_sent`,
`session_valid`/`session_invalid` → `session_authenticated`,
`authorization_denied`/`api_authenticated` → `status_code` (403) /
`body_field`, `history_sequence` → the existing `history_sequence`
check, `final_investigation` → the existing `file_contains` check.
Adding near-duplicate check names for the same underlying comparison
would fragment the validator for no behavioral gain — the same
reasoning `docs/BURP_SUITE_FUNDAMENTALS.md` used for its own
suggested-but-skipped checks.

## Mission objectives (15, 600 XP)

Authentication vs. authorization (30) → the login request's method
(30) → the fictional training credentials (30) → successful login's
302 (35) → `Set-Cookie` (35) → `Cookie` on the next request (35) → an
authenticated `/profile` hit (40) → a failed login's 401 (35) →
authenticated-but-not-authorized `/admin` 403 (45) → API session
authentication via `/api/profile` (40) → logout's cookie deletion (40)
→ post-logout session invalidation (40) → a redirect-style protected
route (40) → simulator-controlled session expiration (45) → the final
investigation (80).

### Final investigation — "The Missing Session"

A new, independent scenario (`auth-lifecycle`), registered in
`_INVESTIGATION_BUILDERS` alongside `login-flow`, `content-type-bug`,
and `profile-mismatch`: a student reports "I logged in fine, but after
logging out I can't get back into my profile," framed as if it were a
bug. It isn't — the four-request transcript (login → authenticated
`/profile` → `POST /logout` with a cookie deletion → a final `/profile`
that's correctly rejected) shows the system working exactly as
designed. The "investigation" is recognizing that logout is *supposed*
to do that, not finding a defect. Graded identically to every prior
mission's final objective: `evidence` / `inspect N` to read the log,
then a conclusion recorded via
`echo "..." > web/auth-investigation.txt`, validated with the existing
`file_contains` check.

## CyberMentor integration

`ai_context()`'s existing `web` section (built up across YC-035.0–.2)
gains a security-filtered authentication summary:

```python
ctx["web"] = {
    ...,
    "authentication_state": "authenticated" | "unauthenticated",
    "session_id_present": bool,
    "session_active": bool,
    "session_expired": bool,          # cookie present, but no longer valid
    "session_id_masked": "stud****" | None,
    "last_authentication_status": <last HTTP status code>,
}
```

The session id is never exposed in full, even though it is always
fictional training data (`student-session`, etc.) — `_mask_session_id()`
keeps only the first four characters and replaces the rest with `****`,
so CyberMentor's prompt never carries a copy-pasteable "secret" out of
habit, matching the spirit of masking a real session token. As with
every mission before it: `ai_context()` is a documented extension
point, but the live `/api/ai/chat` path doesn't currently thread
mission state into the prompt — this hook is built for consistency with
the established precedent, not as new chat wiring.

## Security isolation

Same guarantees as every prior web mission, re-verified for the new
surface: `web.py` still imports nothing network-capable (checked by an
AST-based test scanning for `socket`/`subprocess`/`requests`/
`http.client`/`urllib.request`/etc.). The new routes (`/account`,
`/dashboard`, `/admin`, `POST /logout`) sit behind the exact same
`host != HOST` rejection `open`/`request` already enforce — tested
directly against all four with `evil.example.com`. `expire_session()`
only ever mutates the `WebApp` instance it's called on; two independent
`WebLab`s (two students, or two test cases) never share state. No real
credential, real session-hijacking mechanic, or real authentication
provider is introduced anywhere in this mission.

## UI — Session State panel & flow diagram

A new section (`app/templates/labs/terminal.html`, styled in
`terminal.css`, driven by `terminal.js`), shown only for this mission
(gated on `mission.mission.id == 'authentication-sessions'`), placed
above the existing Proxy Control panel and HTTP Inspector so
Request/Response/Headers/Body/Cookies/History stay a single shared
component rather than being duplicated:

- **Status bar**: an `Authenticated`/`Unauthenticated` badge (never
  color alone — always labeled with text), plus **Logout** and
  **Expire Session** buttons.
- **State grid**: User, Session (the raw training session id — this
  panel is the student's own browser view, not the AI mentor's
  security-filtered one, so showing it in full is correct here),
  Expires (`Active` / `Expired / invalid` / `—`), and Cookie count.
- **Login/session flow diagram**: a compact, always-visible ordered
  list (`POST /login` → server validates → `302 Found` → `Set-Cookie`
  → browser stores the cookie → `GET /profile` → `Cookie` → `200 OK`)
  as a static reference — the live panels immediately below it (Session
  State, HTTP Inspector, History) already let a student click into any
  real step of their own traffic, so this stays a compact legend rather
  than a second, duplicate interactive rebuild of the History tab.

The Proxy Control panel and HTTP Inspector from YC-035.2/YC-035.1 are
reused verbatim (extended to also render on this mission's id) so the
student can intercept the login `POST`, forward it, inspect the 302 and
its `Set-Cookie`, and watch the following request carry `Cookie` — the
mission's central practical exercise — without any new proxy code.

Every button here does exactly one thing: build a command string
(`open -X POST https://cybershop.training/logout`, `expire`) and submit
it through the same `exec()`/`/execute` path the terminal input and
every other mission's buttons already use.

## Accessibility & responsive design

Reuses every existing pattern verbatim: real `<button>` elements,
`:focus-visible` rings, the page's global `prefers-reduced-motion`
rule, `aria-live` already on the terminal output. Authentication state
is always communicated as text (`Authenticated`, `Unauthenticated`,
`Expired / invalid`, `Access denied`), never by badge color alone. The
Session State grid uses `repeat(auto-fit, minmax(160px, 1fr))` so it
reflows to fewer columns under narrow viewports with no bespoke
breakpoint logic, matching how the Proxy Control grid already stacks.

## Achievement

"Session Detective" was evaluated and **not** added as a database row —
the same reasoning as every prior mission's optional achievement in
this series (HTTP Detective, Packet Detective, Recon Scout, Network
Detective, HTTP Investigator, Proxy Operator): the achievement metric
calculator doesn't yet track a mission-completion metric keyed by
mission id, so a new row would never unlock. The existing generic
mission-completion/XP-based achievements still run unchanged.

## Testing

`tests/test_authentication_sessions.py` — WebApp routing for every new
route (unauthenticated/authenticated/authorization-denied cases),
cookie-deletion rendering and jar handling, the `expire` command
(including "no lab configured" and "no active session" edge cases),
the three new validator checks (including graceful failure with no
`web_lab`), the `auth-lifecycle` investigation scenario's determinism
and isolation from live session state, mission registration/loading
(15 objectives, XP sums to 600, progressive hints, chaining after
`burp-fundamentals`), a full scripted solve plus a "no premature
completion" guard, `web_lab_status`/`ai_context` reflecting
authentication and expiration state, save/restore preserving
`expired_count`, session isolation between runners, security isolation
(no network-capable imports, external hosts rejected on every new
route, no real credentials in the module, `expire` never leaking across
instances), a full HTTP-level chain (locked → available after
completing Burp Fundamentals → completed, with real XP/level/dashboard
stats), and page/API reachability (Session State panel present only on
this mission, `/execute` returning authentication state).

`tests/test_burp_fundamentals.py` — one updated assertion:
`burp-fundamentals["next_mission"]` is now `"authentication-sessions"`
instead of `None`, since this mission is no longer terminal in the
chain.

## Manual browser test

1. Log in, open `/terminal/mission/authentication-sessions` (unlocks
   after completing Burp Suite Fundamentals).
2. Confirm the mission header, objectives sidebar, WEB SESSION panel,
   the new **Session State** panel (with its login/session flow
   diagram), the Proxy Control panel, and the HTTP Inspector all
   render.
3. `web` — confirm the routes list includes `/account`, `/dashboard`,
   `/admin`, and the `expire` note.
4. Turn Proxy intercept ON.
5. Submit the login: `open -X POST -d "username=student&password=training123"
   https://cybershop.training/login` — confirm it's intercepted.
6. Click **Forward** — confirm the `302` response and its `Set-Cookie:
   session_id=...` header appear in the Response tab.
7. `open https://cybershop.training/profile` — confirm the Request tab
   shows `Cookie: session_id=...` and the response is `200 OK`.
8. `open https://cybershop.training/api/me` — confirm this stays
   `401` (bearer-only, unaffected by this mission) — then
   `open https://cybershop.training/api/profile` for the
   cookie-authenticated JSON response.
9. `open https://cybershop.training/admin` — confirm `403 Forbidden`
   (authenticated but not authorized).
10. Click **Logout** — confirm the `302` response's `Set-Cookie:
    session_id=; Max-Age=0` and the Session State badge flips to
    Unauthenticated.
11. `open https://cybershop.training/profile` again — confirm `401`.
12. Log back in, then click **Expire Session** — confirm the badge
    flips to Unauthenticated even though `cookies` still lists
    `session_id`.
13. `open https://cybershop.training/profile` — confirm `401` (or, for
    `/dashboard`, a `302` to `/login`).
14. Open the History tab — confirm the full login → profile → logout →
    profile sequence is all present and inspectable.
15. Send an authenticated request to Repeater, remove its `Cookie`
    header, send again — compare the authenticated vs. unauthenticated
    responses.
16. `open https://evil.example.com/` — confirm the exact rejection
    message and that nothing new appears in the Inspector.
17. Complete the final investigation objective; confirm the completion
    overlay shows 600 XP.
18. Open AI Mentor, ask "why did /profile work before but not after
    logout?" — confirm the answer reflects the actual session state
    (invalidated, not just "an error").
19. Refresh the page — confirm authentication state, the cookie jar,
    and mission progress all survive.

## Windows commands

```powershell
$env:PYTHONPATH = "."
python -m pytest tests/test_authentication_sessions.py -q
python -m pytest tests/ -q
venv\Scripts\ruff.exe check app\core\terminal\web.py app\core\terminal\commands.py app\core\missions\mission_validator.py app\core\missions\mission_runner.py app\core\missions\mission_loader.py tests\test_authentication_sessions.py tests\test_burp_fundamentals.py
```
