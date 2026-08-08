# Burp Suite Fundamentals Mission (YC-035.2)

## Purpose

The third mission in the Web Security learning path, chained after YC-035.1
(HTTP Deep Dive). Moves the student from "I can read an HTTP exchange" to
"I understand how an intercepting proxy sits in the middle of one": proxy
architecture, intercept, forward, drop, request modification (query
parameters, headers, POST bodies), HTTP history, a simulated Repeater, and
response comparison — against the same simulated training site (CyberShop).
Still purely educational: no SQL injection, XSS, CSRF, SSRF, or auth attacks
(those belong to later missions), no real Burp Suite integration, and no
real network request is ever made to any host, simulated or otherwise.

## Architecture — extends, doesn't duplicate

One new module, `app/core/terminal/proxy.py`, added alongside `web.py`,
`network.py`, and `packets.py` in the existing `app/core/terminal/` package
— the same package every prior terminal-simulation mission in this series
has extended. `ProxyLab` **reuses** `web.py`'s `HttpRequest`/`HttpResponse`
dataclasses and `WebApp`/`build_request`/`parse_url` helpers unchanged —
there is no second HTTP model and no second simulated server. `MissionRunner`,
`MissionValidator`, and the terminal command layer (`commands.py`) were
extended the same way prior missions were: new attach/status methods, one
new validator type, and new `@cmd(...)` handlers added to their existing
single implementations — never a new mission engine, XP engine, AI mentor,
HTTP simulator, or terminal.

## Simulated proxy state — `ProxyLab`

`app/core/terminal/proxy.py` defines one dataclass, `ProxyLab`, holding:

- `app: WebApp` — the same simulated CyberShop server `web.py` already has.
- `intercept_enabled`, `pending_request`, `last_intercepted` — the
  Intercept panel's state: whether new requests pause, the currently
  paused request (if any), and the most recently intercepted request
  (kept even after it's forwarded/dropped, so an objective can still ask
  "was this ever intercepted?").
- `history` — every **forwarded** request/response pair, in order (the HTTP
  History panel). Dropped requests are deliberately excluded — the Burp
  concept of "this never reached the server."
- `last_dropped`, `dropped_count` — Drop panel state.
- `repeater_request`, `repeater_log`, `compared`, `last_comparison` — the
  Repeater workspace: the current editable draft, every response the
  student has actually sent, and the outcome of the last comparison.
- `blocked_hosts` — every out-of-scope host a `browse` attempt tried to
  reach; never turned into a request object.

Like `web.py`, this module makes zero real network requests: no `socket`,
`subprocess`, `requests`, `urllib.request`, or `http.client` anywhere.
Every request `ProxyLab` ever handles ends up at `WebApp.handle()`, the
same in-process dispatcher `web.py` already uses.

### Forward / Drop / Edit

`forward_pending()` and `drop_pending()` mutate `pending_request` and
either dispatch it (recording into `history`) or discard it
(incrementing `dropped_count`). `edit_pending(method, path, query,
headers, body)` mutates the paused request in place — query parameters
are merged (not replaced wholesale), headers are merged, and a body
replacement also recomputes `Content-Length`, mirroring `web.py`'s
`build_request()` semantics.

### Repeater

`send_to_repeater(index)` copies a 1-based `history` entry into
`repeater_request` as an independent draft (`dataclasses.replace` with
fresh dicts for the mutable fields), so editing it — or re-sending it —
never mutates the original history entry. `send_repeater()` dispatches
the current draft, appends the exchange to `repeater_log`, and resets
`repeater_request` to a fresh copy of what was just sent, so further
edits start from the last-sent state rather than silently rewriting an
already-logged entry.

### Comparison

`compare(a, b)` is a deliberately simple line-based comparison of two
`repeater_log` responses (by 1-based index): status codes are compared,
then each response body is split into lines and compared position by
position. Not a real diff engine, per the ticket's explicit instruction.

### Scope

`ProxyLab.in_scope(host)` checks a hostname against `web.py`'s existing
`HOST` constant (`cybershop.training`) — the single source of truth for
the training site's hostname, reused rather than duplicated. `browse` (the
terminal command that simulates a browser navigation) checks scope
**before** constructing an `HttpRequest` at all, exactly like `web.py`'s
`open`/`request` commands — a rejected host never reaches
`build_request()`, `intercept()`, or `dispatch()`.

## Terminal commands

Added to `app/core/terminal/commands.py`, reading/writing `sh.proxy_lab`
only (guarded with the same "no simulated proxy configured" message
pattern every other lab-specific command uses when its lab isn't
attached):

| Command | Behavior |
|---|---|
| `proxy` | Prints the Browser → Proxy → Server diagram, current Intercept state, scope, and history count |
| `intercept on\|off` | Toggles interception |
| `browse [-X METHOD] [-H "K: V"] [-d DATA] URL` | Simulated browser navigation — the curl-like flags mirror `open`'s exactly; pauses in the proxy if Intercept is ON, dispatches immediately otherwise |
| `forward` | Forwards the paused request |
| `drop` | Discards the paused request |
| `modify [-X M] [-P PATH] [-Q "k=v"] [-H "K: V"] [-d DATA]` | Edits the paused request before forwarding; `-Q`/`-H` are each repeatable |
| `proxy-history` | Lists every forwarded request, numbered |
| `send-to-repeater N` | Copies HTTP History entry N into the Repeater |
| `repeater-edit [-X M] [-P PATH] [-Q "k=v"] [-H "K: V"] [-d DATA]` | Edits the Repeater draft, same grammar as `modify` |
| `repeater-send` | Sends the Repeater draft, logs the exchange |
| `compare A B` | Line-based comparison of two Repeater responses by index |

`browse`'s flag parsing reuses `commands.py`'s existing `_parse_open_args`
(built for `open` in YC-035.0/YC-035.1) unchanged. `modify`/`repeater-edit`
share one new parser, `_parse_edit_args`, extending that same grammar with
`-P` (path) and `-Q` (a single query-parameter assignment, repeatable).

## Validation — one new type, `proxy_state`

Added to `app/core/missions/mission_validator.py` as `_validate_proxy_state`,
the same shape as `_validate_web_state` (YC-035.0) and `_validate_network_state`
(YC-034.6) — a new type only because the underlying state (intercept
toggle, a paused request, forwarded history, a Repeater workspace, a
comparison flag, a scope-violation log) is genuinely new, not a variant of
existing web-request/response state:

- `intercept_enabled` — the Intercept toggle's current value
- `intercepted` — `"METHOD path"` of the most recently intercepted request
- `forwarded` — `"METHOD path"` of the most recently forwarded request
- `dropped_count` — at-least-N dropped requests
- `query_param` — a query parameter's value on the most recently forwarded request
- `header` — a header's value, in the request or response of the most recently forwarded exchange
- `body_field` — a JSON/form field's value in the request or response body (reuses `web.py`'s `parse_body()`)
- `history_contains` — whether `"METHOD path"` appears anywhere in HTTP History
- `repeater_loaded` — whether a Repeater draft exists
- `repeater_query_param` — a query parameter's value on the current Repeater draft
- `repeater_used` — at-least-N Repeater sends logged
- `response_compared` — whether `compare` has been run at least once
- `scope_blocked` — at-least-N out-of-scope hosts blocked

Every check reads `ProxyLab`'s structured fields directly, never rendered
text — the same "don't validate by brittle string matching when
structured data is available" discipline as `web_state`. The final
objective (`bf-14`) reuses the established `file_contains` pattern from
every prior mission's final investigation rather than inventing new
persistence.

## Mission state — attach/status/persist

`MissionRunner` gained `_attach_proxy_lab()`, `proxy_lab_status()`, and
wiring into `execute()`, `to_dict()`, `ai_context()`, and `from_state()` —
the same four integration points `_attach_web_lab`/`web_lab_status`
already have, keyed off the mission config's `"proxy_lab": True` flag
(mirroring `"web_lab"`). `Shell` gained a `proxy_lab: ProxyLab | None`
attribute plus `_pending_proxy_lab_state`, following the exact pattern
`network`/`packet_lab`/`web_lab` already use: the simulated site is always
rebuilt fresh and deterministically on attach; a saved session snapshot
(intercept toggle, forwarded history, Repeater workspace, cookie jar,
server-side login state) is replayed on top so a resumed session picks up
exactly where it left off.

## Mission objectives (14, 550 XP)

Proxy architecture → enable Intercept → intercept a GET → forward it → drop
a different request → modify a query parameter → modify a header → modify
a POST body → inspect HTTP History → send to Repeater → modify the
Repeater draft → compare two responses → understand proxy scope → final
investigation (80 XP).

### Final investigation — PROXY INVESTIGATION

A fictional scenario: "A user reports that their profile information is
not displaying correctly." The student intercepts the `POST /api/profile`
request that updates `display_name`, modifies the parameter, forwards it,
inspects the response, sends the same request through Repeater, compares
two different values, and records their conclusion. Deliberately not a
real vulnerability — an HTTP manipulation exercise, not an exploitation
one, matching the ticket's explicit instruction. Validated the same way as
every prior mission's final objective: `file_contains` on a workspace file
(`web/proxy-investigation.txt`) the student writes themselves, not a
structural check on every intermediate step, matching the ticket's own
"do NOT introduce a real vulnerability, this is an HTTP manipulation
exercise only" framing.

### Progressive hints

All 14 objectives use the `"hints"` list form established in YC-035.1
(`MissionRunner.use_hint()`), 2–3 levels each: a conceptual nudge, a
narrower pointer, then the concrete command.

## CyberMentor integration

`ai_context()` gains a `proxy` section, trimmed the same way the existing
`web` section is (headers/full bodies are useful for the browser's Proxy
Dashboard, not for repeating on every mentor turn):

```python
ctx["proxy"] = {
    "intercept_enabled": ..., "pending_request": "GET /products" | None,
    "last_forwarded": "GET /products" | None, "dropped_count": ...,
    "repeater_loaded": ..., "repeater_sends": ..., "compared": ...,
    "recent_history": ["GET /products -> 200", ...],
}
```

As with YC-035.1's `web` section, this extends `MissionRunner.ai_context()`
(unit-tested directly) rather than the live `/api/ai/chat` context-engine
pipeline (`app/core/ai/context_engine`), which still only receives the
mission slug/title and current-objective title as plain strings — a
pre-existing gap noted in HTTP Deep Dive's own documentation, not
introduced or silently worked around here. Actually wiring
`mission_services.ai_context()` into the live chat pipeline would be a
larger, separate change affecting every mission with rich context, not
just this one.

## Security isolation

Same guarantees as `web.py`, re-verified for the new module: `proxy.py`
imports nothing network-capable — only `dataclasses` and `typing`, plus
`web.py`'s own already-verified exports. `browse` rejects any host other
than `cybershop.training` **before** constructing a request object, exactly
like `open`/`request`. The Repeater can never escape scope: every
`HttpRequest` it ever holds was originally built by `build_request()`
against an already scope-checked `ParsedUrl` (either directly, or copied
from a `history` entry that was itself already scope-checked at intercept
time) — there is no code path that lets a Repeater draft's `host` field be
set to anything but `cybershop.training`. `localhost`, `127.0.0.1`, and
private IP ranges are all rejected the same way as any other non-scope
hostname — there's no special-casing that treats them differently from
`google.com`.

## UI — Proxy Dashboard (hard requirement)

A new, genuinely interactive panel — `app/templates/labs/terminal.html`,
styled in `terminal.css`, driven by `terminal.js` — shown only for
missions with a proxy lab attached (`mission.proxy_lab_status`), reusing
the existing dark-theme tokens and the HTTP Inspector's tab/panel CSS
classes rather than inventing a new visual language:

- **Header**: mission title, `Proxy: ON` badge, `Scope: cybershop.training`
  badge.
- **Simulated Browser panel**: six buttons for the ticket's deterministic
  scenarios (`GET /products`, `GET /products?id=42`, `GET /search?q=linux`,
  `POST /login`, `GET /profile`, `POST /api/profile`) plus a free-text URL
  field for testing scope — every button just builds a `browse ...`
  command and submits it through the same `exec()` pipeline the terminal
  itself uses, so "only the simulated proxy" is enforced exactly once,
  server-side.
- **Intercept panel**: an ON/OFF toggle (`aria-pressed`, not color-only),
  the paused request (or "No request intercepted."), Forward/Drop buttons,
  and a collapsible edit form (method/path/query/headers/body) that
  builds a `modify ...` command from only the fields the student actually
  filled in.
- **Request/Response tabs**: Request/Response/Headers/Body/Cookies, the
  same accessible tab pattern (`role="tab"`/`"tabpanel"`, `aria-selected`)
  as the HTTP Inspector, showing the most recently forwarded exchange or
  whichever History/Repeater entry the student clicked.
- **HTTP History**: every forwarded request, each with a "→ Repeater"
  button (`send-to-repeater N`) alongside the click-to-inspect row.
- **Repeater**: the current draft, a collapsible edit form (same grammar
  as Intercept's), a Send button, the last response, a log of every sent
  response, and a simple A/B index comparison with its result shown
  inline.

All of it is data-driven from `MissionRunner.proxy_lab_status()` — the
same JSON already returned by `/start`, `/execute`, and `to_dict()`, no
new API endpoint, the same pattern the HTTP Inspector established in
YC-035.1.

## Accessibility

Real `<button>` elements throughout (Intercept toggle uses `aria-pressed`,
tabs use `role="tab"`/`aria-selected`), visible `:focus-visible` rings via
the shared `.tm-inspector__field`-style input rules, and interception/
forwarding/dropping/completion state is always paired with text (ON/OFF
labels, "Request dropped.", ✓ checkmarks) — never color alone. The
project's existing global `prefers-reduced-motion` rule already covers
this new component with no extra work.

## Responsive design

`.tm-proxy__grid` is a two-column CSS grid on desktop, collapsing to one
column at the same 1024px breakpoint `.tm-layout`/`.tm-inspector` already
use — the Request/Response and Repeater panels span both columns
(`.tm-proxy__panel--wide`) so they never feel cramped. Every text panel
uses `white-space: pre-wrap` + `word-break: break-word` inside a
scrollable container, so long headers or JSON bodies never force
horizontal page scroll.

## Achievement

"Proxy Operator" was evaluated and not added as a database row — same
reasoning as every prior mission's optional achievement in this series
(HTTP Investigator, HTTP Detective, Packet Detective, Recon Scout, Network
Detective): the achievement metric calculator doesn't yet track "missions
completed" via `MissionRecord`, only the legacy `labs_completed` metric
(which nothing in the interactive-mission system populates), so a new row
would never unlock. The existing generic mission-completion check still
runs unchanged.

## Manual browser test

1. Log in, open `/terminal/mission/burp-fundamentals` (unlocks after
   completing HTTP Deep Dive).
2. Confirm the mission header, objectives sidebar, and Proxy Dashboard
   render below the terminal with its header (`Proxy: ON`,
   `Scope: cybershop.training`), Simulated Browser, Intercept, Request/
   Response tabs, HTTP History, and Repeater panels all visible.
3. Click the Intercept toggle — confirm it reads "ON" and `aria-pressed`
   flips to `true`.
4. Click the `GET /products` scenario button — confirm the Intercept
   panel shows the paused request.
5. Click **Forward** — confirm the Request/Response tabs update and HTTP
   History shows one entry.
6. Click `GET /profile` — confirm it pauses again — then click **Drop** —
   confirm "Request dropped." appears and HTTP History is unchanged.
7. Click `GET /products?id=42`, open "Edit intercepted request", change
   the query field to `id=43`, Save Edit, then Forward — confirm the
   Response tab shows `Product #43`.
8. Repeat with a header change (`User-Agent: CyberBrowser/2.0`) and a POST
   body change (`POST /api/profile`, body field `display_name`) — confirm
   each shows up correctly after Forward.
9. In HTTP History, click "→ Repeater" on any entry — confirm the
   Repeater panel shows that request.
10. Edit the Repeater draft's query parameter, click **Send** — confirm a
    response appears and "SENT RESPONSES" gains an entry.
11. Edit again with a different value, Send again, then use the
    Compare A/B fields (1 and 2) and click **Compare** — confirm a
    line-based difference is shown.
12. In the Simulated Browser panel's custom URL field, try
    `https://google.com/` — confirm "Outside training scope... blocked"
    appears and no new HTTP History entry is created.
13. Complete every mission objective; confirm the completion overlay shows
    550 XP.
14. Open AI Mentor, ask "what does Drop do?" — confirm a reasonable answer;
    the mentor's context now includes live proxy state (intercept
    on/off, pending request, dropped count).
15. Refresh the page — confirm mission progress, XP, and Proxy Dashboard
    state (intercept toggle, HTTP History, Repeater) all persist.

## Windows commands

```powershell
$env:PYTHONPATH = "."
python -m pytest tests/test_burp_fundamentals.py -q
python -m pytest tests/ -q
venv\Scripts\ruff.exe check app\core\terminal\proxy.py app\core\terminal\commands.py app\core\terminal\shell.py app\core\missions\mission_validator.py app\core\missions\mission_runner.py app\core\missions\mission_loader.py tests\test_burp_fundamentals.py
```
