# Burp Suite Fundamentals Mission (YC-035.2)

## Purpose

The third mission in the Web Security learning path, chained after
YC-035.0 (Web Fundamentals) and YC-035.1 (HTTP Deep Dive). Teaches how an
intercepting proxy works — intercept, forward, drop, modify requests,
review history, use Repeater, compare responses, and understand proxy
scope — entirely inside the existing simulated training environment.
Still purely educational: no injection, no session hijacking, no CSRF,
no SSRF, no real Burp Suite integration, and no real network request ever
made. SQL injection, XSS, CSRF, SSRF, and authentication attacks remain
out of scope for this mission (they belong to later missions in the
path).

## Architecture — extends, doesn't duplicate

No new mission engine, XP engine, AI mentor, HTTP simulator, or terminal.
Everything lives in the same modules built for YC-035.0/YC-035.1:

- `app/core/terminal/web.py` — `WebApp` gained per-user profile storage;
  a new `ProxyState` dataclass holds intercept/forward/drop/Repeater/
  compare state on `WebLab`; a new fixed investigation transcript
  (`build_profile_mismatch_log`) was added to the existing scenario
  registry.
- `app/core/terminal/commands.py` — seven new `@cmd(...)` functions
  (`proxy`, `intercept`, `forward`, `drop`, `edit`, `repeater`,
  `compare`) alongside the 44 that already existed; `open` gained one new
  branch (queue instead of send, when intercept is on) and one new
  counter increment (on scope rejection).
- `app/core/missions/mission_validator.py` — eight new `check` values
  added to the existing `web_state` type; five of the ticket's suggested
  checks were **not** added because an existing check already covers the
  same ground exactly (see "Validation" below).
- `app/core/missions/mission_runner.py` — `web_lab_status()` and
  `ai_context()` extended with proxy fields; no new methods.
- `app/core/missions/mission_loader.py` — one new `MISSIONS` entry;
  `http-deep-dive`'s `next_mission` now points here instead of `None`.
- `app/templates/labs/terminal.html` / `terminal.css` / `terminal.js` —
  a new Proxy Control section reusing the existing HTTP Inspector
  (Request/Response/Headers/Body/Cookies/History tabs, `web_lab_status`
  data source, `exec()` submission path) rather than a parallel UI.

## Simulated profile storage

`WebApp._api_profile` previously returned a no-op `{"status": "updated"}`
with nothing persisted. It now keeps `self.profiles: dict[str, dict]`
(mirrors `self.sessions`) and actually updates `display_name` — but only
when the JSON key is exactly `display_name` (case-sensitive); an
unrecognized key is silently ignored, still returning 200 OK. This gives
the request-modification objectives (and the final investigation) a real,
observable effect instead of an acknowledgment that never changes
anything. Purely additive to the existing response shape — no
YC-035.0/YC-035.1 objective inspects this field, so nothing there is
affected.

## `ProxyState` (new)

```python
@dataclass
class ProxyState:
    intercept_enabled: bool = False
    pending: HttpRequest | None = None
    intercepted_count: int = 0
    forwarded_count: int = 0
    dropped_count: int = 0
    blocked_count: int = 0
    repeater_request: HttpRequest | None = None
    repeater_loaded_count: int = 0
    repeater_sent_count: int = 0
    compared_count: int = 0
```

Attached to `WebLab` as `self.proxy`, with `to_dict()`/`from_dict()`
mirroring `WebSession`'s — round-tripped through `WebLab.to_dict()`/
`apply_state()` exactly like the cookie jar and history already were, so
a page refresh or resumed session keeps intercept state, any pending
request, and the Repeater's loaded request. Every prior mission's
`WebLab` gets a `proxy` attribute too, but its counters simply stay at
their defaults forever — no behavior change, no extra cost.

## New terminal commands

| Command | Behavior |
|---|---|
| `proxy` | Status: `Browser --> Proxy --> Server`, intercept ON/OFF, scope |
| `intercept [on\|off]` | Toggles interception; bare form shows status |
| `forward` | Sends the pending intercepted request, records it in history |
| `drop` | Discards the pending request — never reaches the server |
| `edit method\|path\|query\|header\|body ...` | Mutates the pending request if one exists, else the Repeater request |
| `repeater [N]` | Copies history entry `#N` (default: most recent) into Repeater |
| `repeater send` | Sends the Repeater's request, records a new history entry |
| `compare N M` | Simple line-based diff between two history entries' responses |

`open`/`request` gained one new branch: when `intercept_enabled` is
`True`, the built `HttpRequest` is queued as `proxy.pending` instead of
being handled immediately. **When intercept is off (the default, and the
only state YC-035.0/YC-035.1 ever use), `open`/`request` behave
byte-for-byte as before** — verified by the full existing test suite
(1293 tests, unchanged) and by a dedicated regression test in this
mission's own suite.

`edit`'s field-priority rule (pending, else Repeater, else an error) is
deliberate: a student can only ever be mutating one request's fields at a
time, and it matches which request is "live" from the student's point of
view. The UI surfaces this via a note that appears on the Repeater edit
box whenever a request is currently intercepted.

One bug caught and fixed during implementation: `repeater`'s initial
implementation used `dataclasses.replace(req)` to make an "independent"
copy for Repeater/resend — but `dataclasses.replace()` only shallow-copies,
so the `query`/`headers`/`cookies` **dicts** stayed shared with the
original history entry. Editing a Repeater-loaded request's query
parameter was silently corrupting the History entry it came from. Caught
by `TestRepeater::test_repeater_editing_does_not_mutate_history`; fixed
with a small `_copy_request()` helper that copies the three mutable dict
fields explicitly.

## Validation

Eight new `check` values on the existing `type: "web_state"` (no new
validator type, per this project's established discipline):
`proxy_enabled`, `request_intercepted`, `request_forwarded`,
`request_dropped`, `repeater_used`, `repeater_sent`, `response_compared`,
`scope_blocked` — each a simple counter/flag comparison on `lab.proxy`,
mirroring `request_count`'s existing shape.

**Explicitly reused, not duplicated** — five of the ticket's suggested
checks (`request_modified`/`query_modified`, `header_modified`,
`body_modified`, `history_contains`, `final_investigation`) map exactly
onto checks YC-035.0/YC-035.1 already built (`query_param`, `header`,
`body_field`, `request_count`, `file_contains` respectively). Adding
near-duplicate check names would fragment the validator for no
behavioral gain — the same reasoning `docs/HTTP_DEEP_DIVE.md` used for
its own suggested-but-skipped checks.

## Mission objectives (14, 550 XP)

Proxy architecture → enable intercept → intercept a GET → forward →
drop → modify query parameter → modify header → modify POST body →
inspect history → send to Repeater → modify + send via Repeater →
compare responses → proxy scope → final investigation (75 XP).

### Final investigation — Proxy Investigation

A new, independent scenario (`profile-mismatch`), registered in
`_INVESTIGATION_BUILDERS` alongside `login-flow` and `content-type-bug`:
a user logs in, then tries to update their display name, but a client
bug sends the field under the wrong key (`Display_Name` instead of
`display_name`). The server accepts it (200 OK) — the bug is invisible at
the status-code level — but silently ignores the field, so a follow-up
`GET /api/profile` still shows the old name. "Profile information is not
displaying correctly," the fictional bug report.

Live grading requires the student to reproduce and fix this themselves:
intercept a similarly-shaped POST, inspect it, `edit body` to correct the
key, `forward`, confirm the fix, `repeater send` the corrected request
again, `compare` the broken and fixed responses, then record a conclusion
via `echo "..." > web/proxy-investigation.txt` — validated with the
existing `file_contains` check, the identical pattern `hd-14` used.

## CyberMentor integration

`ai_context()`'s existing `web` section (YC-035.0, extended by YC-035.1)
gains a small `proxy` sub-key — intentionally compact, not the full
pending/Repeater request objects the browser's Proxy Control panel needs:

```python
ctx["web"]["proxy"] = {
    "intercept_enabled": ..., "pending_request": "GET /products" or None,
    "repeater_loaded": True/False,
    "intercepted_count": ..., "forwarded_count": ..., "dropped_count": ...,
}
```

As with YC-035.1's own note on this: `ai_context()`/`mission_services.ai_context()`
is a documented extension point, but the live `/api/ai/chat` path doesn't
currently thread mission state into the prompt — this hook is built for
consistency with the established precedent, not as new chat wiring.

## Security isolation

Same guarantees as YC-035.0/YC-035.1, re-verified for every new command:
`web.py` and `commands.py` still import nothing network-capable (checked
by an AST-based test scanning for `socket`/`subprocess`/`requests`/
`http.client`/`urllib.request`/etc.). `open`/`request`'s single
`host != HOST` rejection is still the *only* place a request can be
refused — the interception queue sits entirely downstream of it, so an
out-of-scope host is rejected before a request object even exists,
regardless of intercept state. Repeater can only ever replay a request
that was already built through `open`/`request` (and therefore already
scope-checked); `edit path`/`edit query` can change a request's path or
query string but never its `.host`, so there is no path from "intercept
one in-scope request" to "the proxy becomes an open proxy." All of this
is covered by dedicated tests (`TestSecurityIsolation`).

## UI — Proxy Control panel

A new section (`app/templates/labs/terminal.html`, styled in
`terminal.css`, driven by `terminal.js`), shown only for this mission
(gated on `mission.mission.id == 'burp-fundamentals'`), placed directly
above the existing HTTP Inspector so Request/Response/Headers/Body/
Cookies/History stay a single shared component rather than being
duplicated:

- **Header row**: `Intercept: ON/OFF` badge, `Scope: cybershop.training`,
  a toggle button.
- **Intercepted-request box**: shown only when a request is pending;
  Forward/Drop buttons plus a collapsible edit form (method, path, query
  key/value, header name/value, body) — one small "Set" button per field,
  each issuing exactly one `edit ...` command, matching the command's own
  one-field-at-a-time shape.
- **Repeater box**: shows the currently loaded request, the same edit
  form, and a Send button. A note appears whenever a request is currently
  intercepted, since `edit` would apply to that one instead (matches the
  server-side priority rule, not hidden from the student).
- **Compare box**: two history-index inputs and a Compare button; the
  result renders directly from the `compare` command's own output — no
  separate diff-rendering logic to keep in sync.
- **History tab** (shared with the Inspector): each entry gained a small
  "→ Repeater" button issuing `repeater N`.

Every one of these buttons does exactly one thing: build a command string
and submit it through the same `exec()`/`/execute` path the terminal
input already uses — the same design the Request Builder (YC-035.1)
established, so "only registered simulated routes, one enforcement point"
holds for buttons exactly as it does for typed commands.

`exec()` gained an optional `onDone(d)` callback so the Compare button
could read one field of its own command's response without firing a
second `/execute` call for the same command (an early draft of the
Compare handler did fire two requests for one click — caught before
shipping, fixed by threading a callback through the existing function
instead of duplicating the fetch).

## Accessibility & responsive design

Reuses every existing pattern verbatim: real `<button>` elements,
`:focus-visible` rings, the page's global `prefers-reduced-motion` rule,
`aria-live` already on the terminal output. The Proxy Control grid uses
`repeat(auto-fit, minmax(260px, 1fr))` so its three boxes reflow to a
single column under 600px with no bespoke breakpoint logic, matching how
the Inspector already stacks.

## Achievement

"Proxy Operator" was evaluated and **not** added as a database row — the
same reasoning as every prior mission's optional achievement in this
series (HTTP Detective, Packet Detective, Recon Scout, Network Detective,
HTTP Investigator): the achievement metric calculator
(`app/achievement/services.py`'s `_user_progress_metrics()`) doesn't yet
track a `missions_completed`-style metric, so a new row would never
unlock. The existing generic mission-completion achievement check still
runs unchanged.

## Manual browser test

1. Log in, open `/terminal/mission/burp-fundamentals` (unlocks after
   completing HTTP Deep Dive).
2. Confirm the mission header, objectives sidebar, WEB SESSION panel,
   and the new **Proxy Control** section all render, with the HTTP
   Inspector still present below it.
3. `proxy` — confirm the architecture/scope status text.
4. Click "Turn Intercept On" — badge flips to ON.
5. `open https://cybershop.training/products` — confirm the Intercepted
   Request box appears with the pending request.
6. Click **Forward** — confirm the response appears and the box clears.
7. Repeat intercept, this time click **Drop** — confirm "Request
   dropped." and no response appears anywhere.
8. Intercept `products?id=42`, use the query edit row (`id` → `43`),
   click Set, then Forward — confirm the response shows product 43.
9. Intercept a request, edit a header, Forward — confirm the header in
   the Request tab.
10. Log in via the terminal, intercept a POST to `/api/profile`, edit the
    body's `display_name`, Forward — confirm the updated value in the
    Response tab.
11. Open the History tab, click "→ Repeater" on an entry — confirm the
    Repeater box populates.
12. Edit the Repeater request's query parameter, click Send — confirm a
    new History entry appears with the new value.
13. Fill in two History indices in the Compare box, click Compare —
    confirm the differences render.
14. `open https://evil.example.com/` — confirm the exact rejection
    message and that nothing new appears in the Inspector.
15. Complete the final investigation objective; confirm the completion
    overlay shows 550 XP.
16. Open AI Mentor, ask "what does intercept do?" mid-mission.
17. Refresh the page — confirm intercept state, any pending request, and
    Repeater's loaded request all survive.

## Windows commands

```powershell
$env:PYTHONPATH = "."
python -m pytest tests/test_burp_fundamentals.py -q
python -m pytest tests/ -q
venv\Scripts\ruff.exe check app\core\terminal\web.py app\core\terminal\commands.py app\core\missions\mission_validator.py app\core\missions\mission_runner.py app\core\missions\mission_loader.py tests\test_burp_fundamentals.py tests\test_http_deep_dive.py
```
