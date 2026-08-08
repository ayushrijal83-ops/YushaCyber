# Web Fundamentals Mission (YC-035.0)

## Purpose

The first mission in the Web Security learning path. Teaches how modern web
applications communicate — URL structure, HTTP methods and status codes,
headers, query parameters, request bodies, cookies, and sessions — against
a fully simulated training site, **CyberShop** (`cybershop.training`).
Purely educational: no SQL injection, XSS, CSRF, or authentication
attacks — those belong to later missions in this path. No real network
request is ever made to any host, simulated or otherwise.

## Simulated web architecture

New module: `app/core/terminal/web.py`, kept alongside `network.py` and
`packets.py` in the existing `app/core/terminal/` package rather than the
ticket's suggested `app/core/web_simulator/` — the same reasoning applies
as every prior mission in this series: one package already holds every
terminal-simulation concern, and splitting it fragments reuse without
benefit.

- **`HttpRequest`** / **`HttpResponse`** — structured dataclasses (method,
  scheme, host, port, path, query dict, headers dict, cookies dict, body,
  status code / reason / content type). Structured data throughout, never
  a giant string.
- **`ParsedUrl`** / **`parse_url()`** — splits a URL into scheme/host/port/
  path/query/fragment using the Python standard library's `urllib.parse`
  (`urlsplit`, `parse_qs`). This is pure string parsing with zero I/O —
  distinct from `urllib.request`, which *would* be network-capable and is
  never imported anywhere in this codebase's web layer.
- **`WebApp`** — the simulated CyberShop server: plain Python control flow
  over deterministic canned responses, with one small piece of mutable
  state (`sessions: dict[session_id, username]`), the same pattern as
  `VirtualNetwork`'s interface state (YC-034.6).
- **`WebSession`** — the *student's own* client-side state: cookie jar +
  request/response history.
- **`WebLab`** — bundles a `WebApp`, a `WebSession`, and a fixed
  investigation transcript for the final objective; the session container
  attached to `Shell`, mirroring `PacketLab` (YC-034.9).

## HTTP request model

`HttpRequest(method, scheme, host, port, path, query, headers, cookies,
body, timestamp)`. `build_request()` populates realistic default headers
(`Host`, `User-Agent`, `Accept`, and `Content-Type`/`Content-Length` when a
body is present) so a request built from one line of student input still
inspects like a real one.

## HTTP response model

`HttpResponse(status_code, reason, headers, cookies, body, content_type,
server)`. Every response carries a `Content-Length` computed from its own
body and a `Server: CyberShop-Sim/1.0` header, making clear at a glance
that this is simulated.

## Routes

| Route | Method | Behavior |
|---|---|---|
| `/` | GET | 200, welcome text |
| `/products` | GET | 200; `?id=N` returns a specific "product" |
| `/search` | GET | 200; echoes the `q` query parameter |
| `/login` | GET | 302 → `Location: /auth/login` |
| `/auth/login` | GET | 200, login page placeholder |
| `/login` | POST | Validates `username`/`password` form body; success → 302 to `/profile` + `Set-Cookie: session_id=<user>-session`; failure → 401 |
| `/profile` | GET | 200 if `session_id` cookie maps to a valid session, else 401 |
| `/logout` | GET | Clears the session, 302 → `/` |
| anything else | any | 404 |

Training accounts only: `student`/`training123`, `analyst`/`analyst123`,
`admin`/`admin123` — never real credentials.

## URL parsing

`parse_url()` is exercised directly by the `open` command and by every
objective that inspects `scheme`/`host`/`path`/query parameters — students
see the actual parsed structure, not a hand-written explanation of one.

## Headers

Every request/response carries realistic headers (`Host`, `User-Agent`,
`Accept`, `Content-Type`, `Content-Length`, `Cookie` on requests;
`Content-Type`, `Content-Length`, `Server`, `Cache-Control`, `Set-Cookie`,
`Location` on responses). The `headers` command deliberately prints
**Request headers** and **Response headers** as two clearly separate
sections — the ticket's explicit "students should learn to distinguish
request headers from response headers."

## Cookies

`WebApp._login()` returns `Set-Cookie: session_id=<username>-session` on
success. `WebSession.record()` automatically folds any `Set-Cookie` from a
response into the student's cookie jar, and every subsequent `open`/
`request` call sends the current jar as the `Cookie` header — real browser
behavior, entirely in memory.

## Sessions

`WebApp.sessions` is a plain dict (`session_id -> username`), checked by
`/profile`. No password hashing, no real auth security — this mission
teaches the *concept* (server-side session state keyed by a cookie), not
production authentication engineering, matching the ticket's explicit
scope.

## Redirects

`GET /login` → `302 Found` with `Location: /auth/login`, exactly the
ticket's worked example. The redirect objective validates the `Location`
header value directly rather than whether the student happened to visit
`/auth/login` by some other means — visiting the destination directly
does **not** satisfy the objective, only actually triggering and observing
the redirect does (verified in testing).

## Mission objectives (12, 450 XP)

URL structure → GET method → query parameter → 200 OK → 404 → request
headers → response headers → submit the login form → inspect Set-Cookie →
use the session against `/profile` → analyze the login redirect → final
investigation (a fixed transcript showing a user who visited the login
page but never submitted the form, so no session was ever created —
students must conclude this from the evidence, not be told).

One real design bug was caught and fixed while testing: the session-use
objective originally passed immediately after login (a valid cookie was
already sitting in the jar), without the student ever actually requesting
`/profile`. Fixed so `session_authenticated` requires the *last* request
to be a successful (200), cookie-bearing hit — i.e. the student must
actually exercise the session against a protected resource, not just
possess a cookie.

## Validation changes

**One new type, `web_state`**, added for this mission specifically because
the ticket explicitly instructs "do not validate by brittle string
matching when structured data is available" — a meaningful escalation from
prior missions, where deterministic text output was judged sufficient.
HTTP responses have many small overlapping numbers and strings (multiple
`200`s, multiple `Content-Type`s) where a plain substring check is
genuinely weaker than reading the actual structured `HttpRequest`/
`HttpResponse` objects. Checks: `status_code`, `method`, `path`,
`query_param`, `header` (request or response), `cookie`, `redirect_location`,
`session_authenticated`. Same shape as `network_state` (YC-034.6) for
consistency across the codebase — a new `check` value only added when
genuinely needed, following the same discipline that led every *other*
mission in this series to conclude a new type wasn't warranted.

The final investigation objective reuses the established
"write-a-conclusion-to-a-workspace-file" pattern (`file_contains`) from
YC-034.8/034.9 rather than inventing new persistence.

## CyberMentor integration

`MissionRunner.ai_context()` gains a `web` section when a web lab is
attached: who's logged in, the last response's status code, the last
request's path, and how many cookies are stored
(`MissionRunner.web_lab_status()`, also reused by `to_dict()` for the UI
panel). Nothing web-specific is hardcoded into the shared context
function — generic, like the `network`/`packet_lab` sections before it.

## Security isolation

`web.py` imports nothing capable of a real network request: no `socket`,
`subprocess`, `requests`, `urllib.request`, or `http.client` — only
`urllib.parse` (string parsing, verified by inspecting the *specific*
dotted import path rather than collapsing `urllib.parse` and
`urllib.request` into the same "urllib" bucket, which would either
false-flag legitimate parsing or miss a real network-capable import).
`open`/`request` reject any host other than `cybershop.training` **before**
dispatching to `WebApp` at all, returning the exact ticket-specified
message: *"External hosts are not available in the training environment."*
No request object is even constructed for a rejected host.

## Achievement

"HTTP Detective" was evaluated and not added as a database row, for the
same reason as every prior mission's optional achievement in this series:
the existing achievement metric calculator doesn't yet track "missions
completed," so a new row would never unlock. The existing generic
mission-completion achievement check still runs unchanged.

## UI

Reuses the existing mission UI entirely. One small addition: a "WEB
SESSION" status block in the objectives sidebar, styled with the same CSS
classes as the "NETWORK STATUS" (YC-034.6) and "PACKET LAB" (YC-034.9)
panels — no new stylesheet — updated live via the existing
`web_lab_status` field on mission API responses. The ticket's optional
tabbed request/response inspector was not built: the terminal's own
`open`/`inspect`/`headers`/`cookies`/`response` commands already provide
the full experience textually, and a tabbed UI component would need new
frontend state management the ticket itself gates on "only if it
integrates cleanly" — consistent with the same call made for Wireshark's
optional packet table.
