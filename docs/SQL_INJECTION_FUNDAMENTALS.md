# SQL Injection Fundamentals Mission (YC-035.4)

## Purpose

The fifth mission in the Web Security learning path, chained after
YC-035.0 (Web Fundamentals), YC-035.1 (HTTP Deep Dive), YC-035.2 (Burp
Suite Fundamentals), and YC-035.3 (Authentication & Sessions). Teaches
how unsafe, string-concatenated database queries let user input change
a query's own logic — error-based clues, boolean-based behavior
differences, the UNION concept, and an authentication-bypass concept —
entirely inside the existing simulated training environment
(`cybershop.training`), using the same simulated browser, HTTP
inspector, and intercepting proxy the last three missions already
built. Still purely educational: the simulator recognizes only a fixed
set of exact training payloads and maps each to a predetermined,
deterministic outcome. It never parses or executes anything a student
types as real SQL, never touches a real database or the application's
own production database, never allows arbitrary SQL execution, and
never lets a student escape the training environment. Real exploitation
tooling, data dumping, credential attacks, and scanning real systems
are explicitly out of scope — they don't belong in this or any future
mission in this series.

## Architecture — extends, doesn't duplicate

No new mission engine, HTTP simulator, proxy, XP engine, AI mentor, or
database engine. Everything lives in the same modules built for
YC-035.0–YC-035.3:

- `app/core/terminal/web.py` — `WebApp` gains four new routes (`GET
  /search` is rewritten from its old "always 0 matches" stub into the
  intentionally vulnerable training search; `GET /secure-search`, `POST
  /training-login`, `POST /secure-login` are new); a fixed `PRODUCTS`
  catalog and read-only `DB_SCHEMA` constant; five fixed training
  payload constants (`TRAINING_TRUE_PAYLOAD`, `TRAINING_FALSE_PAYLOAD`,
  `TRAINING_ERROR_PAYLOAD`, `TRAINING_COMMENT_PAYLOAD`,
  `TRAINING_UNION_PAYLOAD`, `TRAINING_AUTH_BYPASS_USERNAME`) and two
  pure string-equality classifier functions
  (`_classify_query_pattern`/`_classify_login_pattern`) — never a SQL
  parser; a new `SqliLabState` dataclass (mirrors `ProxyState`) attached
  to `WebLab` as `.sqli`; `_json_ok`/`_json_error` gain an optional
  `extra_headers` parameter (backward compatible); a new fixed
  investigation transcript (`build_sqli_investigation_log`) registered
  in the existing `_INVESTIGATION_BUILDERS` registry.
- `app/core/terminal/commands.py` — two new commands, `@cmd("schema")`
  (read-only database inspector) and `@cmd("query")` (the query
  visualizer, reading the response's `X-Sim-Query`/`X-Sim-Query-Kind`
  headers); a new `_track_sqli_response()` helper called from `_open`,
  `_forward`, and `_repeater`'s `send` branch — the same "counters back
  a validator check" pattern `ProxyState`'s counters already established
  — updates `WebLab.sqli` from a response's structured header instead of
  re-parsing rendered text; `web`'s status text lists the two new
  routes and the new commands.
- `app/core/missions/mission_validator.py` — ten new `check` values
  added to the existing `web_state` type (`normal_request`,
  `error_observed`, `boolean_true_observed`, `boolean_false_observed`,
  `response_difference`, `query_structure_inspected`,
  `training_auth_scenario`, `secure_endpoint_tested`,
  `parameterized_query_identified`, `evidence_collected`); several
  objectives reuse checks YC-035.0–YC-035.3 already built (`command`,
  `query_param`, `request_intercepted`, `file_contains`) — see
  "Validation" below.
- `app/core/missions/mission_runner.py` — `web_lab_status()` gains a
  `sqli` sub-dict (mirrors the existing `proxy` sub-dict) and a static
  `db_schema` field; `ai_context()`'s existing `web` section gains a
  small `injection` summary; no new methods.
- `app/core/missions/mission_loader.py` — one new `MISSIONS` entry;
  `authentication-sessions`'s `next_mission` now points here instead of
  `None`.
- `app/templates/labs/terminal.html` / `terminal.css` / `terminal.js` —
  a new **Training Application** section (Search, Login, Database
  Inspector, Query Visualizer, Vulnerable-vs-Secure comparison, evidence
  badges), reusing the existing Proxy Control panel (now also gated on
  this mission's id) and HTTP Inspector (Request/Response/Headers/Body/
  Cookies/History tabs, `web_lab_status` data source, `exec()`
  submission path) rather than a parallel UI or a second HTTP client.

## Training database

`PRODUCTS` (`app/core/terminal/web.py`) is a fixed, fictional four-item
catalog (Laptop, Keyboard, Monitor, Mouse) used by `/search` and
`/secure-search`. `DB_SCHEMA` is a fixed, fictional, read-only mapping
of table name to `(column, type)` pairs for four tables — `users`,
`products`, `orders`, `reviews` — structure only, never row data, so the
Database Inspector panel and `schema` command can never resemble a real
data dump. Neither constant is a database engine; both are plain Python
dicts/lists, matched and iterated, never queried.

## Vulnerable simulation

`_search()` and `_training_login()` are conceptually equivalent to
`SELECT * FROM products WHERE name = '<input>'` and `SELECT * FROM
users WHERE username = '<input>' AND password = '<input>'` — but that
string is never built and executed as SQL. `_classify_query_pattern()`
and `_classify_login_pattern()` compare the input, case-insensitively,
against a fixed handful of exact training payloads (`TRAINING_TRUE_PAYLOAD
= "' OR '1'='1"`, `TRAINING_FALSE_PAYLOAD = "' AND '1'='2"`,
`TRAINING_ERROR_PAYLOAD = "'"`, `TRAINING_COMMENT_PAYLOAD = "' --"`,
`TRAINING_UNION_PAYLOAD = "' UNION SELECT NULL, NULL --"`,
`TRAINING_AUTH_BYPASS_USERNAME = "admin'--"`); anything that isn't an
exact match — including realistic-looking but unrecognized strings like
`DROP TABLE users;` or `' OR 1=1 --` — falls through to `"normal"`, a
plain, literal, safe substring search or a literal (and therefore
failing) username comparison. `test_no_arbitrary_sql_execution_only_fixed_patterns`
in the test suite exercises this directly. Every response carries two
structured headers — `X-Sim-Query-Kind` (`normal` / `error` /
`boolean_true` / `boolean_false` / `comment` / `union` / `auth_bypass` /
`parameterized`) and `X-Sim-Query` (the "Application Query" text the
Query Visualizer renders) — so every downstream check (validator, JS
panel, CyberMentor context) reads structured state instead of matching
rendered page text.

| Training input (`q` or `username`) | `X-Sim-Query-Kind` | Simulated outcome |
|---|---|---|
| `laptop` (or any other literal text) | `normal` | Literal substring search |
| `' OR '1'='1` | `boolean_true` | Every product returned — the WHERE clause "always true" |
| `' AND '1'='2` | `boolean_false` | Zero results — the WHERE clause "always false" |
| `'` (a lone quote) | `error` | `500`, `Database error: Unexpected quote in training query.` |
| `' --` | `comment` | Zero results, structural-change note (conceptual only) |
| `' UNION SELECT NULL, NULL --` | `union` | Zero results, structural-change note (conceptual only, never leaks data) |
| `admin'--` (username, `/training-login` only) | `auth_bypass` | `200`, `authenticated_as: "admin"` — a comment sequence conceptually removes the password check |

## Secure simulation

`_secure_search()` and `_secure_login()` always treat the input as
literal data — no classification step exists on these endpoints at all.
The exact same training payloads that flip `/search`'s behavior produce
zero matches (or a normal `401`) here, because they simply don't match
any literal product name or username. `X-Sim-Query` on these endpoints
is always the fixed string `SELECT * FROM products WHERE name = ?` /
`SELECT * FROM users WHERE username = ? AND password = ?`, regardless of
input — the concrete, observable proof that a parameterized query's
*structure* never changes, which is the whole point students are asked
to notice (Objective 13/14).

## Query visualizer

The new `query` terminal command (and the browser's Query Visualizer
panel, which renders the same data) shows **User Input → Application
Query → Database → Response** for the student's last request/response,
reading straight off the `X-Sim-Query`/`X-Sim-Query-Kind` headers —
never a live SQL console, and clearly labeled "Simulated query
representation" per the spec. Each use increments
`WebLab.sqli.query_inspections`, backing the `query_structure_inspected`
validator check.

## Boolean comparison

Sending `TRAINING_TRUE_PAYLOAD` then `TRAINING_FALSE_PAYLOAD` to
`/search` sets `WebLab.sqli.boolean_true_seen`/`boolean_false_seen`
(via `_track_sqli_response()`, reading the response header — never
re-parsing text), independently of whether the student also uses the
Proxy's `compare N M`. The `response_difference` validator check passes
once both flags are set, teaching the core signal of boolean-based SQL
injection: identical requests except for one condition, visibly
different application behavior.

## Authentication scenario

`POST /training-login` is a deliberately separate, fictional endpoint
from `/login`/`/auth/login` (YC-035.0/.3) so the two missions' login
flows never collide. Submitting the fixed
`TRAINING_AUTH_BYPASS_USERNAME` (`admin'--`) with any password
authenticates as `admin` — the conceptual demonstration that a comment
sequence in unsafe, concatenated SQL can remove everything after it,
including a password check. `POST /secure-login` is the parameterized
counterpart: the exact same bypass payload is rejected with `401`,
exactly like any other wrong username, proving the defense rather than
just asserting it. Neither endpoint is a generic authentication-bypass
tool — only this one fixed, fictional pattern is ever recognized.

## Parameterized queries

Objective 14 requires a student to have tested the *same* training
input against both `/search` (structural change) and `/secure-search`
(no change) before it passes — `parameterized_query_identified` checks
`(boolean_true_seen or boolean_false_seen) and secure_search_tested`.
The side-by-side comparison panel (below) makes this concrete and
interactive rather than only textual.

## Secure endpoint

`secure_endpoint_tested` (a new check, parameterized by an `endpoint`
field so it can validate either `/secure-search` or `/secure-login`)
reads `WebLab.sqli.secure_search_tested`/`secure_login_tested` — set the
moment a request to that endpoint completes with
`X-Sim-Query-Kind: parameterized`.

## Proxy integration

Reused verbatim from YC-035.2 — no second proxy, no second Repeater.
`app/templates/labs/terminal.html`'s Proxy Control section gate now
includes `'sql-injection-fundamentals'` alongside
`'burp-fundamentals'`/`'authentication-sessions'`. A student can turn
intercept on, capture `GET /search?q=laptop`, forward it, load it into
Repeater, edit the `q` query parameter to a training payload, and send —
`_track_sqli_response()` is called from `_forward` and `_repeater`'s
`send` branch exactly like the direct `open` path, so evidence is
recorded identically regardless of which path a student uses.

## Repeater

No changes — `repeater`/`repeater send`/`edit query q ...` already
support everything this mission needs; only `_track_sqli_response()`'s
extra call inside the `send` branch is new.

## HTTP history

No changes — the existing `requests`/`history` tab already lists every
`GET /search`, `GET /secure-search`, and `POST /training-login`/
`/secure-login` exchange in order, exactly like every prior web mission.

## Database inspector

A new, explicitly read-only panel and `schema [table]` command, both
backed by the same fixed `DB_SCHEMA` constant (`web_lab_status()`'s new
`db_schema` field feeds the template; the `schema` command reads the
same constant directly) — structure only, never row data, never an
input field, never arbitrary SQL.

## Mission objectives (16, 700 XP)

Database basics via `schema` (30) → query flow via `web` (30) → a
normal search (35) → intercepting the search request (35) → identifying
`q` as the user-controlled parameter (35) → the malformed-input error
clue (45) → the TRUE training condition (45) → the FALSE training
condition (45) → comparing the two (45) → inspecting the query
representation (45) → opening the training login (30) → completing the
authentication-bypass exercise (55) → testing `/secure-search` with the
same input (45) → identifying why parameterized queries prevent
injection (45) → an evidence-collection checkpoint (55) → the final
investigation (80).

### Final investigation — "The Inconsistent Search"

A new, independent scenario (`sqli-investigation`), registered in
`_INVESTIGATION_BUILDERS` alongside `login-flow`, `content-type-bug`,
`profile-mismatch`, and `auth-lifecycle`: a bug report says the training
site's search "sometimes returns every product, and sometimes returns
none, for no obvious reason." The four-request transcript (a normal
search → the TRUE condition against `/search` → the FALSE condition
against `/search` → the same TRUE condition against `/secure-search`)
shows the actual cause — unsafe string concatenation lets the input
change the query's own logic — and its fix, side by side. Graded
identically to every prior mission's final objective: `evidence` /
`inspect N` to read the log, then a conclusion recorded via `echo "..."
> web/sqli-investigation.txt`, validated with the existing
`file_contains` check (requiring the phrase "parameterized queries").

## Validation

Ten new `check` values on the existing `type: "web_state"` (no new
validator type, per this project's established discipline):

- **`normal_request`** — the last request hit `/search` with
  `X-Sim-Query-Kind: normal` and the expected literal query parameter.
- **`error_observed`** — the last response was `500` with
  `X-Sim-Query-Kind: error`.
- **`boolean_true_observed`** / **`boolean_false_observed`** — the last
  response carries the matching `X-Sim-Query-Kind`.
- **`response_difference`** — both `boolean_true_seen` and
  `boolean_false_seen` are set on `WebLab.sqli`.
- **`query_structure_inspected`** — `WebLab.sqli.query_inspections`
  meets the expected count (the `query` command was used).
- **`training_auth_scenario`** — `match: "opened"` requires a `POST
  /training-login`; `match: "bypassed"` requires
  `WebLab.sqli.auth_bypass_triggered`.
- **`secure_endpoint_tested`** — reads
  `secure_search_tested`/`secure_login_tested`, selected by an
  `endpoint` field.
- **`parameterized_query_identified`** — requires both a structural
  change having been observed *and* the secure endpoint having been
  tested.
- **`evidence_collected`** — a capstone conjunction of TRUE seen, FALSE
  seen, the secure endpoint tested, and at least one query inspection.

**Explicitly reused, not duplicated** — several of the ticket's
suggested check names map exactly onto checks earlier missions already
built: `parameter_identified` → the existing `query_param` check,
`final_investigation` → the existing `file_contains` check, and the
conceptual "database basics"/"query flow" objectives are validated the
same way `authentication-sessions`' `as-1` was — via the existing
`command` type against a single, teaching-relevant command (`schema`,
`web`). Adding near-duplicate check names for the same underlying
comparison would fragment the validator for no behavioral gain — the
same reasoning `docs/AUTHENTICATION_AND_SESSIONS.md` used for its own
suggested-but-skipped checks.

## Hints

Every objective has three progressive hints (a nudge, a narrower nudge,
then the exact command), following the same pattern established since
YC-035.1 — `MissionRunner.use_hint()` advances one step per re-ask,
capped at the last entry, unchanged.

## CyberMentor integration

`ai_context()`'s existing `web` section (built up across
YC-035.0–.3) gains a small `injection` summary:

```python
ctx["web"]["injection"] = {
    "last_query_kind": "boolean_true" | "error" | "normal" | ... | None,
    "query_inspections": int,
    "boolean_true_observed": bool,
    "boolean_false_observed": bool,
    "secure_search_tested": bool,
    "secure_login_tested": bool,
    "auth_bypass_triggered": bool,
}
```

Small and structured, so CyberMentor can explain *why* a response
changed (which training condition was sent, whether the secure endpoint
has been compared yet) without repeating full request/response bodies
on every turn, and without ever solving the objective for the student.
As with every mission before it: `ai_context()` is a documented
extension point, but the live `/api/ai/chat` path doesn't currently
thread mission state into the prompt — this hook is built for
consistency with the established precedent, not as new chat wiring.

## Security isolation

Same guarantees as every prior web mission, re-verified for the new
surface: `web.py` and `commands.py` still import nothing network- or
database-capable (checked by AST-based tests scanning for
`socket`/`subprocess`/`requests`/`http.client`/`urllib.request`/
`sqlite3`/`psycopg2`/`pymysql`/etc.). The new routes (`/search` is
rewritten but keeps the same host check; `/secure-search`,
`/training-login`, `/secure-login` are new) sit behind the exact same
`host != HOST` rejection `open`/`request` already enforce — tested
directly with `evil.example.com`. Every classifier is pure string
equality against a fixed, documented list of training payloads — an
arbitrary, realistic-looking "SQL-shaped" string (`DROP TABLE users;`,
`' OR 1=1 --`, `SELECT * FROM users`) is never treated specially, only
ever as a normal, literal, safe search/login attempt. `WebLab.sqli`
state is per-instance, like every other `WebLab` field — two students,
or two test cases, never share state. No real credential, real
database, or real SQL execution is introduced anywhere in this mission.

## UI — Training Application section

A new section (`app/templates/labs/terminal.html`, styled in
`terminal.css`, driven by `terminal.js`), shown only for this mission
(gated on `mission.mission.id == 'sql-injection-fundamentals'`), placed
above the existing Proxy Control panel and HTTP Inspector so
Request/Response/Headers/Body/Cookies/History stay a single shared
component rather than being duplicated:

- **Search box**: a text input, quick-pick buttons for the fixed
  training payloads (normal / TRUE / FALSE / malformed), and
  **Search (Vulnerable)** / **Search (Secure)** buttons.
- **Login box**: username/password fields, a **Fill bypass training
  payload** quick-fill button, and **Login (Vulnerable)** / **Login
  (Secure)** buttons.
- **Database Inspector box**: the fixed, read-only schema.
- **Query Visualizer**: User Input → Application Query → Database →
  Response, live from the student's last request/response, explicitly
  labeled "simulated query representation."
- **Vulnerable vs. Secure — Side by Side**: one input, a **Send to
  Both** button, and two result panes with a small facts strip
  (`String concatenation` / `Input affects syntax` / `Unsafe` vs.
  `Parameterized query` / `Input stays data` / `Safer`) — never color
  alone.
- **Evidence badges**: a pure view over `WebLab.sqli`'s counters/flags
  (TRUE seen, FALSE seen, auth bypass triggered, secure endpoint
  tested, query inspections) — always labeled text, never color alone.

Every button here does exactly one thing: build an `open ...` command
string a student could type themselves and submit it through the same
`exec()`/`/execute` path the terminal input and every other mission's
buttons already use — no new HTTP client, no client-side query logic.

## Accessibility & responsive design

Reuses every existing pattern verbatim: real `<button>` elements,
`:focus-visible` rings, the page's global `prefers-reduced-motion` rule,
`aria-live` already on the terminal output. Every evidence badge and
comparison fact is communicated as text, never by color alone. The new
grids use `repeat(auto-fit, minmax(...))` so they reflow to a single
column under narrow viewports with no bespoke breakpoint logic,
matching how the Proxy Control grid already stacks.

## Achievement

"Query Detective" was evaluated and **not** added as a database row —
the same reasoning as every prior mission's optional achievement in
this series (HTTP Detective, Packet Detective, Recon Scout, Network
Detective, HTTP Investigator, Proxy Operator, Session Detective): the
achievement metric calculator doesn't yet track a mission-completion
metric keyed by mission id, so a new row would never unlock. The
existing generic mission-completion/XP-based achievements still run
unchanged.

## Testing

`tests/test_sql_injection_fundamentals.py` — `WebApp` routing for every
new/rewritten route (normal, TRUE, FALSE, error, comment, union,
auth-bypass, and every secure-endpoint counterpart), the `schema` and
`query` commands (including "no lab configured"/"no request yet" edge
cases), `_track_sqli_response()`'s wiring through `open`/`forward`/
`repeater send`, save/restore of `WebLab.sqli`, the ten new validator
checks (including graceful failure with no `web_lab`), the
`sqli-investigation` scenario's determinism and isolation from live
session state, mission registration/loading (16 objectives, XP sums to
700, progressive hints, chaining after `authentication-sessions`), a
full scripted solve plus a "no premature completion" guard,
`web_lab_status`/`ai_context` reflecting injection state, security
isolation (no network/DB-capable imports in either module, external
hosts rejected on every route, arbitrary "SQL-shaped" strings never
treated specially, `schema` never returning row data, state never
leaking across instances), a full HTTP-level chain (locked → available
after completing Authentication & Sessions → completed, with real
XP/level/dashboard stats), and page/API reachability (the Training
Application section present only on this mission, `/execute` returning
injection state, the hint endpoint advancing progressively).

## Manual browser test

1. Log in, open `/terminal/mission/sql-injection-fundamentals` (unlocks
   after completing Authentication & Sessions).
2. Confirm the mission header, objectives sidebar, the new **Training
   Application** section (Search/Login/Database Inspector boxes, Query
   Visualizer, Vulnerable-vs-Secure comparison, evidence badges), the
   Proxy Control panel, and the HTTP Inspector all render.
3. `schema` — confirm all four tables (`users`, `products`, `orders`,
   `reviews`) print with column names and types.
4. Search for `laptop` in the Training Application's Search box, click
   **Search (Vulnerable)** — confirm a normal result and the objectives
   sidebar advances.
5. Turn Proxy intercept ON, search for `keyboard` again, confirm it's
   intercepted, then **Forward**.
6. Use a quick-pick to fill the TRUE condition, click **Search
   (Vulnerable)** — confirm every product in the catalog is returned.
7. Use a quick-pick to fill the FALSE condition, click **Search
   (Vulnerable)** — confirm zero results.
8. Use a quick-pick to fill the malformed (error) payload, click
   **Search (Vulnerable)** — confirm a `500` and the database error
   message.
9. Open the Query Visualizer — confirm it shows Input / Application
   Query / Database / Response for the last search, and that the
   Application Query text visibly contains the injected quotes/keyword.
10. Open the secure endpoint: fill the TRUE condition, click **Search
    (Secure)** — confirm zero results and that the Query Visualizer's
    Application Query is the fixed `SELECT * FROM products WHERE name =
    ?`, unchanged from any other input.
11. Use the **Vulnerable vs. Secure — Side by Side** panel: type the
    TRUE condition, click **Send to Both** — confirm the vulnerable pane
    shows every product and the secure pane shows zero.
12. In the Training Application's Login box, click **Fill bypass
    training payload**, then **Login (Vulnerable)** — confirm
    `authenticated_as: "admin"`.
13. Click **Login (Secure)** with the same fields still filled — confirm
    `401 Unauthorized`.
14. Confirm the evidence badges panel shows TRUE/FALSE/auth-bypass/
    secure-endpoint all flipped to their "seen"/"triggered"/"tested"
    state.
15. Open the History tab — confirm every request above is present and
    inspectable.
16. Complete the final investigation objective (`evidence`, `inspect
    1`–`4`, then the `echo ... > web/sqli-investigation.txt` command);
    confirm the completion overlay shows 700 XP.
17. Open AI Mentor, ask "why did the search return every product?" —
    confirm the answer reflects the actual injection state (the TRUE
    condition, not just "an error").
18. Refresh the page — confirm mission progress, XP, and the evidence
    badges all survive.
19. Attempt `open https://evil.example.com/` — confirm the exact
    rejection message and that nothing new appears in the Inspector.

## Windows commands

```powershell
$env:PYTHONPATH = "."
python -m pytest tests/test_sql_injection_fundamentals.py -q
python -m pytest tests/ -q
venv\Scripts\ruff.exe check app\core\terminal\web.py app\core\terminal\commands.py app\core\missions\mission_validator.py app\core\missions\mission_runner.py app\core\missions\mission_loader.py tests\test_sql_injection_fundamentals.py tests\test_authentication_sessions.py
```
