# Cross-Site Scripting (XSS) Fundamentals Mission (YC-035.5)

## Purpose

The sixth mission in the Web Security learning path, chained after
YC-035.0 (Web Fundamentals), YC-035.1 (HTTP Deep Dive), YC-035.2 (Burp
Suite Fundamentals), YC-035.3 (Authentication & Sessions), and YC-035.4
(SQL Injection Fundamentals). Teaches how unsafe HTML rendering lets
untrusted input become part of the page itself — reflected, stored, and
DOM-based XSS, source/sink analysis, HTML context, output encoding, and
Content Security Policy — entirely inside the existing simulated
training environment (`cybershop.training`), using the same simulated
browser, HTTP inspector, and intercepting proxy the last four missions
already built. Still purely educational: the simulator recognizes only
a fixed set of exact training markers and maps each to a predetermined,
deterministic "simulated browser event." It never executes anything a
student types as real JavaScript, never touches a real browser, cookie,
or `localStorage`, and never lets a student escape the training
environment. Real exploitation tooling, cookie/credential theft,
payload generators, and CSP-bypass tooling are explicitly out of scope
— they don't belong in this or any future mission in this series.

## Architecture — extends, doesn't duplicate

No new mission engine, HTTP simulator, proxy, XP engine, AI mentor, or
browser sandbox. Everything lives in the same modules built for
YC-035.0–YC-035.4:

- `app/core/terminal/web.py` — `WebApp` gains four new routes (`GET`/
  `POST /feedback`, `POST /secure-feedback`, `GET /comments`, `GET
  /dom-demo`); `/search` and `/secure-search` (YC-035.4) are extended
  with a second, independent classification (`X-Sim-XSS-Kind`/
  `X-Sim-XSS-Context` headers, alongside `/search`'s existing
  `X-Sim-Query-Kind`) so both missions' concerns coexist on the same
  endpoints without collision; a public `has_xss_marker()` classifier
  and a fixed `TRAINING_XSS_MARKERS` tuple (same discipline as
  YC-035.4's SQLi payload constants — pure string equality, never a
  parser); a `Comment` dataclass and `WebApp.comments` list (the
  feedback store); a centralized `Content-Security-Policy` header,
  applied once in `WebApp.handle()` to every response via a new
  `_route()` split (so every current and future route gets it
  automatically); a new `XssLabState` dataclass (mirrors
  `SqliLabState`) attached to `WebLab` as `.xss`; a new fixed
  investigation transcript (`build_xss_investigation_log`) registered
  in the existing `_INVESTIGATION_BUILDERS` registry; `DB_SCHEMA` gains
  a `comments` table (structure only, YC-035.4's `schema` command and
  Database Inspector panel pick it up automatically, unchanged).
- `app/core/terminal/commands.py` — a new `_track_xss_response()`
  helper (mirrors `_track_sqli_response()`), called from `_open`,
  `_forward`, and `_repeater`'s `send` branch exactly like its SQLi
  counterpart — updates `WebLab.xss` from a response's structured
  header instead of re-parsing rendered text.
- `app/core/terminal/shell.py` — **one bug fix**, not new behavior:
  `Shell.execute()`'s output-redirection detection (`_REDIR_RE`, a raw
  regex, not a quote-aware tokenizer) previously mistook a `>` sitting
  at the very end of a *quoted* argument for real `>` redirection —
  invisible until this mission's `<TRAINING_XSS>`-shaped markers became
  the first legitimate case of a `>` character appearing right before
  end-of-line inside quotes (`open "...q=<TRAINING_XSS>"`). A new
  `_ends_inside_quotes()` helper checks quote parity before the match
  point; a `>`/`>>` found inside an open quote is no longer treated as
  redirection. See "Security isolation" below for the regression check
  this required.
- `app/core/missions/mission_validator.py` — ten new `check` values
  added to the existing `web_state` type (`reflected_input`,
  `html_context`, `simulated_xss_event`, `stored_input`,
  `reflected_vs_stored`, `dom_source`, `dom_sink`, `secure_encoding`,
  `html_escaped_observed`, `xss_evidence_collected`); several objectives
  reuse checks YC-035.0–YC-035.4 already built (`command`,
  `query_param`, `request_intercepted`, `header`, `file_contains`) — see
  "Validation" below.
- `app/core/missions/mission_runner.py` — `web_lab_status()` gains an
  `xss` sub-dict (mirrors `sqli`) and a `comments` list (the stored
  feedback, for the Comments panel); `ai_context()`'s existing `web`
  section gains a small `xss` summary; no new methods.
- `app/core/missions/mission_loader.py` — one new `MISSIONS` entry;
  `sql-injection-fundamentals`'s `next_mission` now points here instead
  of `None`.
- `app/templates/labs/terminal.html` / `terminal.css` / `terminal.js` —
  a new **Training Application** section (Search, Feedback, DOM Demo,
  Comments, Reflection Visualizer, Source/Sink Visualizer,
  Vulnerable-vs-Secure comparison, CSP panel, evidence badges), reusing
  the existing Proxy Control panel (now also gated on this mission's id)
  and HTTP Inspector rather than a parallel UI or a second HTTP client.

## Reflected XSS

`GET /search` (already vulnerable, string-concatenated, since YC-035.4)
now also runs `has_xss_marker(q)` independently of its SQLi
classification. If `q` is exactly one of the fixed
`TRAINING_XSS_MARKERS` (`<TRAINING_XSS>`, `<TRAINING_ALERT>`,
`<TRAINING_MARKER>`, `<script>TRAINING_XSS</script>`), the response
carries `X-Sim-XSS-Kind: reflected`, `X-Sim-XSS-Context: html_text`, and
a "SIMULATED BROWSER EVENT" panel is appended to the body — always with
the explicit disclaimer "Simulation only — no JavaScript executed in
YushaCyber." An unrecognized, even realistic-looking, XSS-shaped string
(`<img src=x onerror=alert(1)>`, `javascript:alert(1)`) is never treated
specially — `has_xss_marker()` is pure, case-insensitive string
equality against the fixed set, never an HTML/JS parser.

## Stored XSS

`POST /feedback` (vulnerable) and `POST /secure-feedback` (secure) both
append a `Comment` to `WebApp.comments`, tagged with which endpoint
stored it (`sink: "vulnerable" | "secure"`). Critically, **the
submission's own response never shows the simulated-event panel** —
only a structured header (`X-Sim-XSS-Kind: stored`) — preserving the
pedagogical distinction from reflected XSS: the attacker doesn't see
their payload "execute" at submission time; a later visitor does, when
the comment is actually *rendered*. That render happens on `GET
/comments`: each vulnerable comment with a marker triggers the
simulated-event panel *there*, and only there; each secure comment is
always shown HTML-escaped, never triggering anything.

## DOM-based XSS

`GET /dom-demo?input=...` is a purely textual, conceptual demonstration
— there is no client-side JavaScript anywhere in this simulator, so
"source" and "sink" are described in the response body, not executed.
If `input` matches a training marker, the response carries
`X-Sim-XSS-Kind: dom`, `X-Sim-XSS-Context: dom`, and the same simulated-
event panel, describing the source (`the 'input' URL parameter`) and
sink (`simulated innerHTML DOM sink`) explicitly.

## Source/sink

The Source/Sink Visualizer panel (UI) and the DOM demo's response body
both name the same two concepts consistently: **source** — where
untrusted data enters (a URL parameter) — and **sink** — where it would
be inserted into the page (a simulated `innerHTML`-style assignment).
`dom_source`/`dom_sink` validator checks read this from structured
request/response state, not the visualizer's UI state, so an objective
can never be satisfied by merely clicking a panel button without
actually making the corresponding request.

## HTML context

Every live endpoint in this simulator renders reflected/stored input
into plain HTML text content (`X-Sim-XSS-Context: html_text`), the DOM
demo's context is `dom`. The mission still teaches that attribute,
`<script>`, and URL contexts exist and need different defenses (see
"Mission objectives" — Objective 6) primarily through description and
CyberMentor rather than four additional live weaponizable endpoints,
per the ticket's explicit "focus on identifying context, not a
weaponized payload collection."

## Output encoding

`/secure-search`'s output is passed through `html.escape(q, quote=True)`
before being embedded in the response body — `'<'` becomes `'&lt;'`,
`'>'` becomes `'&gt;'`, etc. — so a training marker like
`<TRAINING_XSS>` is displayed as inert text (`&lt;TRAINING_XSS&gt;`),
visibly never interpreted as markup. `/secure-feedback`-sourced comments
are escaped identically when rendered by `/comments`. The escaping is
real (Python's standard library `html.escape`), not a fake string
substitution — the same function a real templating engine's
auto-escaping would call.

## Content Security Policy

`WebApp.handle()` centrally attaches a fixed, informational
`Content-Security-Policy: default-src 'self'; script-src 'self'` header
to **every** response (via `resp.headers.setdefault(...)` after
`_route()` dispatches), so a student can inspect it from any request.
Nothing in this simulator enforces it against anything — no real script
ever runs here regardless — and the mission's CSP panel and hints
explicitly state that CSP is an *additional* defense, never a
replacement for correct, context-aware output encoding (the ticket's
explicit instruction: "Do NOT claim CSP alone fixes XSS").

## Vulnerable simulation

`/search`, `/feedback` (vulnerable sink), and `/dom-demo` all reflect
raw, unescaped input somewhere in their response body when a training
marker is present, and only a training marker ever triggers the
simulated-event panel — an unrecognized string is always just literal,
inert text (a normal search term, a normal comment, or `(none)`), never
specially interpreted.

## Secure simulation

`/secure-search`, `/secure-feedback`, and every `/comments` entry with
`sink: "secure"` always HTML-escape their output, so the exact same
training marker that triggers a simulated event on the vulnerable side
produces zero events on the secure side — proving the defense instead
of merely asserting it, the same discipline YC-035.4 established for
parameterized queries.

## Training application

Fixed, fictional routes on `cybershop.training`: `GET /search`, `GET
/secure-search` (both extended, not new), `GET`/`POST /feedback`, `POST
/secure-feedback`, `GET /comments`, `GET /dom-demo` (all new). `GET
/profile` (existing, from earlier missions) is unaffected.

## Proxy integration

Reused verbatim from YC-035.2. `app/templates/labs/terminal.html`'s
Proxy Control section gate now includes `'xss-fundamentals'` alongside
the three prior missions. A student can intercept `GET
/search?q=laptop`, forward it, load it into Repeater, edit the `q`
parameter to a training marker, and send — `_track_xss_response()` is
called from `_forward` and `_repeater`'s `send` branch exactly like the
direct `open` path, so evidence is recorded identically regardless of
which path a student uses.

## Repeater

No changes — `repeater`/`repeater send`/`edit query q ...`/`edit body
...` already support everything this mission needs (editing `q` for
search, or the form-encoded `comment` field for feedback); only
`_track_xss_response()`'s extra call inside the `send` branch is new.

## HTTP history

No changes — the existing `requests`/`history` tab already lists every
`GET /search`, `GET /secure-search`, `POST /feedback`, `POST
/secure-feedback`, `GET /comments`, and `GET /dom-demo` exchange in
order, exactly like every prior web mission.

## Evidence collection

The Comments panel, evidence badges (Reflected/Stored/DOM/Secure
endpoint), and the CSP panel are all pure views over
`web_lab_status()`'s `xss`/`comments` fields — the same "server computes
structured state once, the browser only renders it" discipline as every
prior mission's panels. The final objective additionally requires
`evidence`/`inspect N` against the fixed investigation transcript.

## Mission objectives (17, 750 XP)

XSS basics via `web` (35) → identifying untrusted input (35) →
triggering reflected XSS (40) → intercepting the search request (40) →
confirming the reflection in the response body (35) → identifying the
HTML context (40) → observing the simulated execution panel (45) →
submitting stored XSS via feedback (40) → viewing the delayed, stored
reflection (45) → articulating reflected vs. stored (35) → opening the
DOM demo (40) → triggering the DOM sink (45) → testing `/secure-search`
with the same marker (45) → identifying the `&lt;`/`&gt;` output
encoding (40) → inspecting the CSP header (40) → an evidence-collection
checkpoint (55) → the final investigation (95).

### Final investigation — "The Reflected Comment Box"

A new, independent scenario (`xss-investigation`), registered in
`_INVESTIGATION_BUILDERS` alongside `login-flow`, `content-type-bug`,
`profile-mismatch`, `auth-lifecycle`, and `sqli-investigation`: a bug
report says "our search bar and comments section might be exposing us
to script injection." The five-request transcript — a normal search (no
event) → the same search with the training marker (reflected,
immediate) → a feedback submission carrying the marker (stored, not yet
visible) → `/comments` (the delayed, stored reflection — the actual
moment the simulated event fires) → the same marker against
`/secure-search` (HTML-escaped, no event) — shows reflected vs. stored
vs. defended, side by side. Graded identically to every prior mission's
final objective: `evidence` / `inspect N` to read the log, then a
conclusion recorded via `echo "..." > web/xss-investigation.txt`,
validated with the existing `file_contains` check (requiring the phrase
"output encoding").

## Validation

Ten new `check` values on the existing `type: "web_state"` (no new
validator type, per this project's established discipline):

- **`reflected_input`** — the last response carries
  `X-Sim-XSS-Kind: reflected`.
- **`html_context`** — the last response's `X-Sim-XSS-Context` header
  matches the expected value (`html_text`).
- **`simulated_xss_event`** — the last response's `X-Sim-XSS-Kind` is
  one of `reflected`/`stored`/`dom`.
- **`stored_input`** — `match: "submitted"` requires a `POST /feedback`
  whose response carries `X-Sim-XSS-Kind: stored`; `match: "displayed"`
  requires the *same* kind on a `GET /comments` response — the request
  path is what distinguishes "you sent it" from "it rendered."
- **`reflected_vs_stored`** — both `WebLab.xss.reflected_seen` and
  `.stored_seen` are set.
- **`dom_source`** — the last request hit `/dom-demo` (any method/query).
- **`dom_sink`** — the last response carries `X-Sim-XSS-Kind: dom`.
- **`secure_encoding`** — the last request hit the expected secure
  endpoint (`endpoint` field, default `/secure-search`) and the response
  carries `X-Sim-XSS-Kind: encoded`.
- **`html_escaped_observed`** — the last response body literally
  contains both `&lt;` and `&gt;`.
- **`xss_evidence_collected`** — a capstone conjunction of reflected
  seen, stored seen, DOM seen, and at least one secure endpoint tested.
  **Deliberately a distinct name from YC-035.4's `evidence_collected`**
  (not a reuse) — the two read different `WebLab` sub-states
  (`.xss` vs. `.sqli`) and would silently never pass for a student who
  only ever touched this mission's endpoints if they shared a name;
  `TestXssValidatorChecks::test_xss_evidence_collected_does_not_reuse_sqli_evidence_collected`
  guards this directly.

**Explicitly reused, not duplicated**: the conceptual "XSS basics"/
"untrusted input" objectives are validated the same way prior missions'
opening objectives were — via the existing `command` type (`web`) and
`query_param` check; "Inspect HTTP Request" reuses YC-035.2's
`request_intercepted`; "Content Security Policy" reuses the existing
generic `header` check (`header: "Content-Security-Policy"`) rather than
inventing a `csp_header` check for one fixed, global value; the final
investigation reuses `file_contains`, matching every prior mission.

## Hints

Every objective has three progressive hints (a nudge, a narrower nudge,
then the exact command), following the same pattern established since
YC-035.1 — `MissionRunner.use_hint()` advances one step per re-ask,
capped at the last entry, unchanged.

## CyberMentor integration

`ai_context()`'s existing `web` section (built up across
YC-035.0–.4) gains a small `xss` summary:

```python
ctx["web"]["xss"] = {
    "last_xss_kind": "reflected" | "stored" | "dom" | "encoded" | "none" | None,
    "last_xss_context": "html_text" | "dom" | None,
    "reflected_seen": bool,
    "stored_seen": bool,
    "dom_seen": bool,
    "secure_search_tested": bool,
    "secure_feedback_tested": bool,
    "stored_comment_count": int,
}
```

Small and structured, so CyberMentor can explain *why* something is
reflected vs. stored vs. DOM-based from actual mission state (e.g. "why
is this reflected XSS instead of stored?" — because `last_xss_kind` came
from `/search`, not a later `/comments` view) without repeating full
response bodies (which may contain the simulated-event panel text) on
every turn, and without ever solving the objective for the student. As
with every mission before it: `ai_context()` is a documented extension
point, but the live `/api/ai/chat` path doesn't currently thread mission
state into the prompt — this hook is built for consistency with the
established precedent, not as new chat wiring.

## Security isolation

Same guarantees as every prior web mission, re-verified for the new
surface:

- `web.py` and `commands.py` still import nothing network- or
  database-capable (AST-based tests, extended with `sqlite3`/
  `psycopg2`/etc. to match YC-035.4's precedent).
- Every new route (`/feedback`, `/secure-feedback`, `/comments`,
  `/dom-demo`) sits behind the exact same `host != HOST` rejection
  `open`/`request` already enforce — tested directly with
  `evil.example.com`.
- `has_xss_marker()` is pure string equality against a fixed,
  documented list — an arbitrary, realistic-looking payload
  (`<script>alert(document.cookie)</script>`, `<img src=x
  onerror=fetch('http://evil.example.com')>`) is never treated
  specially, only ever as normal, literal, inert text.
  `test_unrecognized_arbitrary_payloads_never_trigger_event` and
  `test_search_unrecognized_xss_shaped_string_is_normal` exercise this
  directly, and a source-text test confirms `eval(`/`exec(`/`compile(`/
  `subprocess.` appear nowhere in `web.py`.
- **The browser-side Comments panel never uses `innerHTML` with stored
  content** — `renderXss()` in `terminal.js` builds each comment's DOM
  node with `textContent`/`createTextNode` exclusively, so a stored
  training marker (even the `<script>...</script>`-shaped one) can never
  become live markup in the real YushaCyber page, regardless of what the
  simulated backend "renders" in its own text response.
  `test_comments_never_rendered_via_innerhtml_in_browser_js` and
  `test_no_eval_or_dangerous_dom_apis_in_terminal_js_xss_section` assert
  this against the actual shipped JS source.
- No real cookie, `localStorage`, or browser API is ever touched — this
  simulator has no concept of either; "cookie" here is always the
  training session-cookie jar from YC-035.0/.3, unrelated to XSS.
- `WebLab.xss`/`WebApp.comments` state is per-instance, like every other
  `WebLab` field — two students, or two test cases, never share state.
- The `Shell._ends_inside_quotes()` fix (see "Architecture" above) is a
  strict tightening, not a behavior change for any existing command: it
  only suppresses a redirection match that was already inside quotes,
  never adds a new one — re-verified by running
  `test_bash_fundamentals.py`'s existing echo/redirection-heavy tests
  unchanged after the fix.

## UI — Training Application section

A new section (`app/templates/labs/terminal.html`, styled in
`terminal.css`, driven by `terminal.js`), shown only for this mission
(gated on `mission.mission.id == 'xss-fundamentals'`), placed above the
existing Proxy Control panel and HTTP Inspector so
Request/Response/Headers/Body/Cookies/History stay a single shared
component rather than being duplicated:

- **Search box**: a text input, quick-pick buttons (a plain keyword vs.
  the fixed training marker), and **Search (Vulnerable)** / **Search
  (Secure)** buttons.
- **Feedback box**: name/comment fields, a **Fill training marker**
  quick-fill button, **Submit (Vulnerable)** / **Submit (Secure)**
  buttons, and a **View Comments** shortcut.
- **DOM Demo box**: an input field, a marker quick-fill button, and an
  **Open DOM Demo** button.
- **Comments**: a live list (from `web_lab_status.comments`), each entry
  labeled "(vulnerable)" or "(secure — HTML-escaped)" — text only, never
  color alone, and never inserted via `innerHTML`.
- **Reflection Visualizer**: seven clickable steps (User Input → HTTP
  Request → Server → HTML Response → Browser Parser → HTML Context →
  Simulated XSS Event), each showing a short explanation on click.
- **Source/Sink Visualizer**: four clickable steps (Source → Processing
  → Sink → Result), same interaction pattern.
- **Vulnerable vs. Secure — Side by Side**: one input, a **Send to
  Both** button, and two result panes with a small facts strip
  (`HTML rendering` / `Input affects markup` / `Potential XSS` vs.
  `Context-aware encoding` / `Input stays text` / `Safer`).
- **Content Security Policy panel**: the fixed CSP value, with an
  explicit note that it's an additional defense, not a replacement for
  output encoding.
- **Evidence badges**: a pure view over `WebLab.xss`'s flags (Reflected,
  Stored, DOM, Secure endpoint) — always labeled text, never color
  alone.

Every button here does exactly one thing: build an `open ...` command
string a student could type themselves and submit it through the same
`exec()`/`/execute` path the terminal input and every other mission's
buttons already use — no new HTTP client, no client-side script
execution, no live HTML/JS console.

## Accessibility & responsive design

Reuses every existing pattern verbatim: real `<button>` elements,
`:focus-visible` rings, the page's global `prefers-reduced-motion` rule,
`aria-live` already on the terminal output. Every evidence badge,
comment tag, and comparison fact is communicated as text, never by
color alone (e.g. "Reflected: seen" / "not seen", "(vulnerable)" /
"(secure — HTML-escaped)"). The new grids use
`repeat(auto-fit, minmax(...))` so they reflow to a single column under
narrow viewports with no bespoke breakpoint logic, matching how the
Proxy Control and SQLi grids already stack.

## Achievement

"Context Hunter" was evaluated and **not** added as a database row —
the same reasoning as every prior mission's optional achievement in
this series (HTTP Detective, Packet Detective, Recon Scout, Network
Detective, HTTP Investigator, Proxy Operator, Session Detective, Query
Detective): the achievement metric calculator doesn't yet track a
mission-completion metric keyed by mission id, so a new row would never
unlock. The existing generic mission-completion/XP-based achievements
still run unchanged.

## Testing

`tests/test_xss_fundamentals.py` — `WebApp` routing for every new/
extended route (normal, reflected, unrecognized-payload, and every
secure-endpoint counterpart for search, feedback, comments, and the DOM
demo), `has_xss_marker()`'s classification, `_track_xss_response()`'s
wiring through `open`/`forward`/`repeater send`, save/restore of
`WebLab.xss` and stored comments, the ten new validator checks
(including graceful failure with no `web_lab`, and a dedicated
regression guard against colliding with YC-035.4's `evidence_collected`
name), the `xss-investigation` scenario's determinism and isolation from
live session state, mission registration/loading (17 objectives, XP sums
to 750, progressive hints, chaining after `sql-injection-fundamentals`),
a full scripted solve plus a "no premature completion" guard,
`web_lab_status`/`ai_context` reflecting XSS and comment state, security
isolation (no network/DB-capable imports in either Python module, no
`eval`/`exec`/`subprocess` anywhere in `web.py`, external hosts rejected
on every new route, arbitrary XSS-shaped strings never treated
specially, the browser-side Comments panel never using `innerHTML` with
stored content, state never leaking across instances), a full
HTTP-level chain (locked → available after completing SQL Injection
Fundamentals → completed, with real XP/level/dashboard stats), and
page/API reachability (the Training Application section present only on
this mission, `/execute` returning XSS state, the hint endpoint
advancing progressively).

`tests/test_sql_injection_fundamentals.py` — one updated assertion:
`sql-injection-fundamentals["next_mission"]` is now `"xss-fundamentals"`
instead of `None`, since this mission is no longer terminal in the
chain (same pattern YC-035.4 applied to `test_authentication_sessions.py`).

## Manual browser test

1. Log in, open `/terminal/mission/xss-fundamentals` (unlocks after
   completing SQL Injection Fundamentals).
2. Confirm the mission header, objectives sidebar, the new **Training
   Application** section (Search/Feedback/DOM Demo boxes, Comments,
   Reflection Visualizer, Source/Sink Visualizer, Vulnerable-vs-Secure
   comparison, CSP panel, evidence badges), the Proxy Control panel, and
   the HTTP Inspector all render.
3. In the Search box, search for `laptop`, click **Search
   (Vulnerable)** — confirm a normal result and the objectives sidebar
   advances.
4. Turn Proxy intercept ON, use the "Training marker" quick-pick, click
   **Search (Vulnerable)** — confirm it's intercepted, then **Forward**.
5. Confirm the response shows the SIMULATED BROWSER EVENT panel and the
   disclaimer "no JavaScript executed in YushaCyber" — and confirm no
   dialog, alert, or console error appears anywhere in the real page.
6. Click through the Reflection Visualizer's seven steps — confirm each
   shows a distinct explanation.
7. In the Feedback box, click **Fill training marker**, then **Submit
   (Vulnerable)** — confirm the submission response has no event panel.
8. Click **View Comments** — confirm the stored marker now renders with
   the simulated event panel, and appears in the Comments list tagged
   "(vulnerable)".
9. In the DOM Demo box, click **Fill training marker**, then **Open DOM
   Demo** — confirm the simulated DOM sink event fires; click through
   the Source/Sink Visualizer's four steps.
10. Use the **Vulnerable vs. Secure — Side by Side** panel with the
    training marker — confirm the vulnerable pane shows the event panel
    and the secure pane shows `&lt;TRAINING_XSS&gt;` with no event.
11. Submit the training marker via **Submit (Secure)** — confirm it's
    escaped in Comments, tagged "(secure — HTML-escaped)".
12. Open the CSP panel — confirm the Content-Security-Policy value is
    shown, with the "additional defense, not a replacement" note.
13. Open the History tab — confirm every request above is present and
    inspectable.
14. Complete the final investigation objective (`evidence`, `inspect
    1`–`5`, then the `echo ... > web/xss-investigation.txt` command);
    confirm the completion overlay shows 750 XP.
15. Open AI Mentor, ask "why is this reflected XSS instead of stored?"
    — confirm the answer reflects the actual mission state (which
    endpoint the last event came from), not a generic definition.
16. Refresh the page — confirm mission progress, XP, comments, and the
    evidence badges all survive.
17. Attempt `open https://evil.example.com/feedback` — confirm the
    exact rejection message and that nothing new appears in the
    Inspector.
18. Attempt to submit an arbitrary, non-training XSS payload (e.g.
    `<img src=x onerror=alert(1)>`) — confirm it is reflected/stored as
    inert text with no simulated event, and confirm nothing executes in
    the real browser (no alert box, no console error).

## Windows commands

```powershell
$env:PYTHONPATH = "."
python -m pytest tests/test_xss_fundamentals.py -q
python -m pytest tests/ -q
venv\Scripts\ruff.exe check app\core\terminal\web.py app\core\terminal\commands.py app\core\terminal\shell.py app\core\missions\mission_validator.py app\core\missions\mission_runner.py app\core\missions\mission_loader.py tests\test_xss_fundamentals.py tests\test_sql_injection_fundamentals.py
```
