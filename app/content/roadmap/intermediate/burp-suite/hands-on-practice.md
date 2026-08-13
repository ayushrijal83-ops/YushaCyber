# Hands-on Practice — Controlled Web Request Investigation

## 1. What You Will Learn

By the end of this lesson you should be able to:

- capture a request in an authorized environment and identify every part of it
- send a request to Repeater, change one value, re-send, and compare properly
- investigate a parameter and report what the evidence supports — and only that
- investigate a session by comparing your own authenticated and unauthenticated requests
- investigate authorization using the training accounts the environment provides
- find a real bug that returns `200 OK` and does nothing
- write a complete, evidence-based finding that another person could verify

## 2. Authorization Comes First

Everything below runs against `cybershop.training` — a fictional site that exists only as Python data structures inside YushaCyber. No real network request is made at any point; the simulator contains no HTTP client, and it rejects every host but its own:

```
$ open https://evil.example.com/
External hosts are not available in the training environment.
```

The rule these exercises exist to build the habit for is unchanged from Introduction §3: **intercept and modify traffic only against systems you own or are explicitly authorized to test.** Nothing in this lesson works as a technique against a system you haven't been given permission to touch — not because it would fail technically, but because doing it would be unauthorized access, and this platform does not teach interception of third-party traffic, credential theft, session hijacking, or attacks on live services.

When you want to practise beyond this module, install a deliberately vulnerable application on your own machine — OWASP Juice Shop, DVWA — or use PortSwigger's Web Security Academy, which provides targets explicitly for this purpose.

## 3. The Environment

Open the **Burp Suite Fundamentals** terminal mission. It attaches a simulated CyberShop site and a Burp-style proxy to your shell. (These commands only work inside a mission — the free-practice terminal has no web environment attached, and every command below would answer "no simulated web environment configured for this session".)

Start by asking the environment what it is:

```
$ web
Simulated site: cybershop.training
Not logged in
Routes: / /products /search /secure-search /login /auth/login /training-login /secure-login /profile /account /settings /dashboard /admin /logout /api/login /api/profile /api/me /csrf-demo /secure-transfer /transfer /transfer-history /upload /secure-upload /uploads /upload/<id> /upload-security
Type 'open URL' or 'request METHOD PATH' to make a request.
Proxy: 'intercept on|off', 'forward', 'drop', 'edit ...', 'repeater [N]', 'repeater send', 'compare N M'.
Session: 'expire' invalidates your session server-side without clearing your browser's cookie (see how that differs from logout).
SQL Injection Fundamentals: 'schema [table]' inspects the training database (read-only). 'query' shows the simulated query representation for your last request/response.
CSRF Fundamentals: POST /transfer is the vulnerable, unprotected endpoint; POST /secure-transfer requires a csrf_token. 'samesite strict|lax|none' explains SameSite cookie behavior.
File Upload Security: POST /upload checks only the file extension; POST /secure-upload also checks size, MIME, content signature, filename normalization, and executable content.
```

That route list covers several modules; this lesson uses `/products`, `/account`, `/auth/login`, `/logout`, `/admin` and `/api/profile`. The rest belong to `owasp-top-10` and later work — leave them for now.

And the proxy:

```
$ proxy
Browser --> Proxy --> Server
Intercept: OFF
Scope: cybershop.training
Requests outside scope are never proxied — they're rejected before a request object even exists.
```

**The training accounts.** The environment provides three fixed, fictional accounts: `student` / `training123`, `analyst` / `analyst123`, and `admin` / `admin123`. They are built into the simulator and published here deliberately — Exercise 5 needs two accounts with different permission levels, and having them *given* to you is what makes that exercise an authorized comparison rather than a credential attack. You are not discovering these credentials; you are being handed test accounts, which is exactly how a real engagement provides them.

**The workflow**, from Core Concepts §2:

```
OPEN AUTHORIZED ENVIRONMENT
  ↓
GENERATE REQUEST
  ↓
CAPTURE / FIND IN HISTORY
  ↓
INSPECT
  ↓
SEND TO REPEATER
  ↓
MODIFY ONE VALUE
  ↓
SEND
  ↓
COMPARE
  ↓
FORM HYPOTHESIS
  ↓
VALIDATE
  ↓
DOCUMENT
```

**The six exercises below run as one continuous session**, so the history numbers shown are the real ones you'll see if you follow along in order. If you restart the mission, your numbering restarts too — check with `requests` rather than assuming.

## 4. Exercise 1 — Capture a Request

**Goal:** make one request and be able to describe every part of it and its response without guessing.

**Step 1.** Generate the request.

```
$ open https://cybershop.training/products?id=42
━━━━━━━━ REQUEST ━━━━━━━━
GET /products?id=42 HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 34
Server: CyberShop-Sim/1.0
Cache-Control: max-age=60
ETag: "product-42-v1"
Last-Modified: Wed, 01 Jan 2025 00:00:00 GMT
Content-Security-Policy: default-src 'self'; script-src 'self'

Product #42: Sample training item.
```

**Step 2.** Separate the headers out, to practise reading them on their own:

```
$ headers
Request headers:
  Host: cybershop.training
  User-Agent: YushaCyber-Trainer/1.0
  Accept: */*

Response headers:
  Content-Type: text/html
  Content-Length: 34
  Server: CyberShop-Sim/1.0
  Cache-Control: max-age=60
  ETag: "product-42-v1"
  Last-Modified: Wed, 01 Jan 2025 00:00:00 GMT
  Content-Security-Policy: default-src 'self'; script-src 'self'
```

**Step 3.** Confirm it's in history:

```
$ requests
Request history:
  #1  GET /products  -> 200 OK
```

**Now answer, in writing:**

1. Method, path, and query string — with the parameter named separately from its value.
2. Which headers did the *client* send, and which did the *server* send?
3. Which client-sent values could the client have chosen differently?
4. Status code, content type, and body length.
5. Which response header contains a value derived from your input?
6. The history line reads `GET /products`. What is it not telling you, and why does that matter?

<details>
<summary>Discussion</summary>

1. `GET`, path `/products`, query string `?id=42` — one parameter named `id`, value `42`.
2. Client sent `Host`, `User-Agent`, `Accept`. Server sent `Content-Type`, `Content-Length`, `Server`, `Cache-Control`, `ETag`, `Last-Modified`, `Content-Security-Policy`.
3. **All three**, plus the path and the parameter. `User-Agent` in particular is just a string the client picked — it is a claim, not a fact.
4. `200 OK`, `text/html`, 34 bytes.
5. `ETag: "product-42-v1"` — the `42` came from your query string.
6. It omits the query string. Three different product requests all appear as `GET /products`. The summary line is an index for finding things; the full exchange is the evidence you cite.
</details>

## 5. Exercise 2 — Intercept, Inspect, Forward

**Goal:** hold a request in flight, confirm the proxy isn't altering your experiment, and release it.

**Step 1.** Turn interception on:

```
$ intercept on
Intercept is now ON. Your next request will be held before it reaches the server.
```

**Step 2.** Make the same request as before. Note what you *don't* get:

```
$ open https://cybershop.training/products?id=42
Request intercepted:
GET /products?id=42 HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

Use 'forward', 'drop', or 'edit <field> ...' before it reaches the server.
```

No response — because nothing has reached the server. The request is fully formed and held.

**Step 3.** Forward it **unchanged**. This is the baseline habit from Core Concepts §3:

```
$ forward
Request forwarded.
━━━━━━━━ REQUEST ━━━━━━━━
GET /products?id=42 HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 34
Server: CyberShop-Sim/1.0
Cache-Control: max-age=60
ETag: "product-42-v1"
Last-Modified: Wed, 01 Jan 2025 00:00:00 GMT
Content-Security-Policy: default-src 'self'; script-src 'self'

Product #42: Sample training item.
```

**Step 4.** Turn interception off — you don't want every subsequent request stopping:

```
$ intercept off
Intercept is now OFF. Requests will pass straight through.
```

**Answer:**

1. What was different about the output in Step 2 compared with Exercise 1?
2. Compare the Step 3 response with Exercise 1's response. Are they the same? Should they be?
3. Why is forwarding unchanged, once, a worthwhile thing to do deliberately?
4. If you had run `drop` instead of `forward`, what would have reached the server?
5. Give a concrete reason a tester would leave intercept **off** most of the time.

<details>
<summary>Discussion</summary>

1. No response at all — just the held request and a prompt for what to do with it.
2. Identical, and they must be: nothing was modified. If they *weren't* identical, either the proxy is interfering or the server's state changed between the two requests, and either way every result after that point is suspect.
3. It establishes that your instrument isn't affecting your experiment. Ten seconds; removes a whole category of confusing results later.
4. Nothing. `drop` discards the request entirely.
5. Because *everything* stops — every image, stylesheet, and background API call a real page fires. Real workflow: browse with intercept off, read history, and turn intercept on only for the one request you mean to catch.
</details>

## 6. Exercise 3 — Parameter Investigation with Repeater

**Goal:** change exactly one value, compare the responses, and state what the evidence supports without overreaching.

**Step 1.** Load history entry #1 into Repeater:

```
$ repeater 1
Sent to Repeater (from history #1):
GET /products?id=42 HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
```

Nothing has been sent — it's a copy, loaded and editable.

**Step 2.** Change one thing. One:

```
$ edit query id 43
Query parameter 'id' set to '43'.
```

**Step 3.** Send:

```
$ repeater send
Repeater: request sent.
━━━━━━━━ REQUEST ━━━━━━━━
GET /products?id=43 HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 34
Server: CyberShop-Sim/1.0
Cache-Control: max-age=60
ETag: "product-43-v1"
Last-Modified: Wed, 01 Jan 2025 00:00:00 GMT
Content-Security-Policy: default-src 'self'; script-src 'self'

Product #43: Sample training item.
```

**Step 4.** Compare against the baseline. The Repeater send became history entry #3 (entry #2 was the forwarded request from Exercise 2):

```
$ compare 1 3
Comparing #1 vs #3 responses:
  HTTP/1.1 200 OK
  Content-Type: text/html
  Content-Length: 34
  Server: CyberShop-Sim/1.0
  Cache-Control: max-age=60
! #1: ETag: "product-42-v1"
! #3: ETag: "product-43-v1"
  Last-Modified: Wed, 01 Jan 2025 00:00:00 GMT
  Content-Security-Policy: default-src 'self'; script-src 'self'
  
! #1: Product #42: Sample training item.
! #3: Product #43: Sample training item.
```

**Answer:**

1. List every line that differs, and every line that doesn't.
2. Write the **observation** — literally what the evidence shows, no inference.
3. Write the **interpretation** — what you think explains it.
4. Is this a vulnerability? Justify your answer from the evidence, not from instinct.
5. What further test would tell you something the two requests above cannot?

<details>
<summary>Discussion</summary>

1. Differ: `ETag` and body. Identical: status line, `Content-Type`, `Content-Length`, `Server`, `Cache-Control`, `Last-Modified`, `Content-Security-Policy`.

2. **Observation.** Changing the `id` query parameter from `42` to `43`, with nothing else altered, returned a response with a different body and a different `ETag`. Status, content type and length were unchanged.

3. **Interpretation.** The `id` parameter selects which product resource the endpoint describes, and its value is incorporated into the cache identifier.

4. **No — and this is the important answer in this whole lesson.** A product catalogue letting you request different products by id is its *intended function*. Nothing here tested who was asking or whether they were allowed to ask. "The parameter changed the response" is a fact about how the endpoint works, not a finding. It would only become one if the id selected data the requester wasn't authorized to see — and that is a different test, run in Exercise 5.

5. Several worth trying, one variable at a time: an id that shouldn't exist (`edit query id 99999`); a non-numeric id (`edit query id abc`); the same request with no session versus with one. Each answers a different question — and each should have a prediction written down *before* you send it.
</details>

**Extend it.** Try `edit query id 99999` and `edit query id abc`, sending each. You'll find both return `200 OK` with the same shape of body. That is a genuine observation: **this endpoint does not validate that the requested id corresponds to anything.** In this simulator that's simply how the training route is built (it formats the id into a fixed sentence). In a real application, an endpoint that returns a success page for every conceivable identifier is worth a second look, because it tells you the server isn't checking existence — and an endpoint that doesn't check existence often isn't checking ownership either. Note the reasoning: *worth a second look*, not *therefore vulnerable*.

## 7. Exercise 4 — Session Investigation

**Goal:** determine, from evidence, whether a route requires authentication — by comparing your own unauthenticated request against your own authenticated one.

**Step 1.** Request a protected page before logging in:

```
$ open https://cybershop.training/account
━━━━━━━━ REQUEST ━━━━━━━━
GET /account HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 302 Found
Location: /login
Content-Length: 0
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'
```

**Step 2.** Log in with the training account:

```
$ open -X POST -d "username=student&password=training123" https://cybershop.training/auth/login
━━━━━━━━ REQUEST ━━━━━━━━
POST /auth/login HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 37

username=student&password=training123

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 302 Found
Location: /profile
Content-Length: 0
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'
Set-Cookie: session_id=student-session
```

**Step 3.** Confirm what the client now holds:

```
$ cookies
session_id=student-session
```

**Step 4.** Repeat the *identical* request from Step 1:

```
$ open https://cybershop.training/account
━━━━━━━━ REQUEST ━━━━━━━━
GET /account HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 29
Server: CyberShop-Sim/1.0
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'

Account settings for student.
```

**Step 5.** Compare (entries #4 and #6):

```
$ compare 4 6
Comparing #4 vs #6 responses:
! #4: HTTP/1.1 302 Found
! #6: HTTP/1.1 200 OK
! #4: Location: /login
! #6: Content-Type: text/html
! #4: Content-Length: 0
! #6: Content-Length: 29
  Server: CyberShop-Sim/1.0
! #4: Content-Security-Policy: default-src 'self'; script-src 'self'
! #6: Cache-Control: no-store
! #4: 
! #6: Content-Security-Policy: default-src 'self'; script-src 'self'
  
! #4: 
! #6: Account settings for student.
```

**Answer:**

1. What is the *only* difference between the two requests?
2. Which response header in Step 2 caused that difference, and which request header carries it afterwards?
3. Record the four observable differences: status, redirect target, length, body.
4. Does this prove `/account` requires authentication? What would strengthen it?
5. The Step 1 response has an empty body. Where is its entire meaning carried?
6. Why is this a legitimate test that involves no session theft whatsoever?

<details>
<summary>Discussion</summary>

1. The presence of `Cookie: session_id=student-session`. Method, path and every other header are identical.
2. `Set-Cookie` in the login *response* (server → client); `Cookie` in every later *request* (client → server). Two names, two directions, one mechanism.
3. `302` → `200`; `Location: /login` present → absent; length `0` → `29`; empty body → `Account settings for student.`
4. It is strong evidence. It would be strengthened by logging out and confirming the `302` returns — which Exercise 5 does incidentally — and by checking whether an invalid session value is treated as unauthenticated rather than accepted.
5. Entirely in the status line and the `Location` header. A response with no body is not a response with no information.
6. Because every request used *your own* session, and the comparison was between your authenticated and unauthenticated states. No other user's session was involved, obtained, or guessed. That's the standard shape of legitimate session testing.
</details>

## 8. Exercise 5 — Authorization Investigation

**Goal:** demonstrate, from real responses, that authentication and authorization are two different decisions — using two accounts the environment gave you.

You are logged in as `student` from Exercise 4.

**Step 1.** Request the admin route as `student`:

```
$ open https://cybershop.training/admin
━━━━━━━━ REQUEST ━━━━━━━━
GET /admin HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 403 Forbidden
Content-Type: application/json
Content-Length: 103
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'

{"error": "Forbidden", "message": "You are authenticated, but not authorized to access this resource."}
```

**Step 2.** Log out, and watch what the response does to your cookie:

```
$ open -X POST https://cybershop.training/logout
━━━━━━━━ REQUEST ━━━━━━━━
POST /logout HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 302 Found
Location: /login
Content-Length: 0
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'
Set-Cookie: session_id=; Max-Age=0
```

**Step 3.** Request the same URL with no session:

```
$ open https://cybershop.training/admin
━━━━━━━━ REQUEST ━━━━━━━━
GET /admin HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 401 Unauthorized
Content-Type: text/plain
Content-Length: 34
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'

You must log in to view this page.
```

**Step 4.** Log in as the second training account:

```
$ open -X POST -d "username=admin&password=admin123" https://cybershop.training/auth/login
━━━━━━━━ REQUEST ━━━━━━━━
POST /auth/login HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 32

username=admin&password=admin123

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 302 Found
Location: /profile
Content-Length: 0
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'
Set-Cookie: session_id=admin-session
```

**Step 5.** The same URL, a third time:

```
$ open https://cybershop.training/admin
━━━━━━━━ REQUEST ━━━━━━━━
GET /admin HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=admin-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 40
Server: CyberShop-Sim/1.0
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'

Admin dashboard: training-site controls.
```

**Step 6.** Compare the first and last (entries #7 and #11):

```
$ compare 7 11
Comparing #7 vs #11 responses:
! #7: HTTP/1.1 403 Forbidden
! #11: HTTP/1.1 200 OK
! #7: Content-Type: application/json
! #11: Content-Type: text/html
! #7: Content-Length: 103
! #11: Content-Length: 40
  Server: CyberShop-Sim/1.0
! #7: Content-Security-Policy: default-src 'self'; script-src 'self'
! #11: Cache-Control: no-store
! #7: 
! #11: Content-Security-Policy: default-src 'self'; script-src 'self'
! #7: {"error": "Forbidden", "message": "You are authenticated, but not authorized to access this resource."}
! #11: 
! #7: 
! #11: Admin dashboard: training-site controls.
```

**Answer:**

1. Three requests to one URL produced `403`, `401`, `200`. What single dimension varied?
2. Which of those three is an *authentication* failure and which is an *authorization* failure? How do you know?
3. The `403` body states the distinction in words. Why is it unwise to depend on that in general?
4. Does `403` here indicate the server is working correctly or incorrectly? Explain.
5. `/admin` was never linked from any page you visited. What does that tell you about interface-based restrictions?
6. Write observation / interpretation / conclusion for this exercise, with a confidence statement.

<details>
<summary>Discussion</summary>

1. The identity attached to the request — carried entirely by the `Cookie` header: `student-session`, then none, then `admin-session`.

2. The `401` (Step 3) is authentication: no session, so the server doesn't know who's asking. The `403` (Step 1) is authorization: the session was valid and the identity established, and the server refused anyway.

3. Because most applications don't say so. This training server is unusually explicit; a real one typically returns a bare `403`, or an HTML error page, or `404`. You have to infer the distinction from the *pattern across requests* — which is what Steps 1–5 did — rather than from a helpful message.

4. Correctly. Both decisions were enforced server-side, and the two failure modes are distinguished. **Confirming a control works is a real result** — most testing time is spent establishing that things are fine, and being able to say so with evidence is as professional as finding a bug.

5. That the endpoint exists and responds regardless of whether anything links to it. A control that only exists in the interface controls nothing: any client can send the request directly. The `403` is what actually protects `/admin` — not the absence of a link.

6. For example:

> **OBSERVATION.** `GET /admin` returned `403 Forbidden` with `Cookie: session_id=student-session`, `401 Unauthorized` with no cookie, and `200 OK` with `Cookie: session_id=admin-session`. Method and path were identical in all three.
>
> **INTERPRETATION.** The route requires authentication first and a specific authorization level second, and the two failures are reported with different status codes.
>
> **CONCLUSION.** Access control for `/admin` is enforced server-side and distinguishes unauthenticated from unauthorized requests. Confidence: high — directly observed across three controlled requests differing in exactly one dimension.
</details>

**On authorization testing beyond this environment.** The classic next test is: log in as user A, capture a request for A's own resource (`/orders/1041`), change only the identifier to one belonging to test user B (`/orders/1042`), and see whether the server returns B's data. This simulator has no per-user resource endpoint, so that test cannot be run here — stated plainly rather than dressed up with an invented example. You will run it for real in `owasp-top-10`, and in any deliberately vulnerable application you install. The reasoning is exactly the reasoning you practised above; only the resource differs.

## 9. Exercise 6 — The `200 OK` That Did Nothing

**Goal:** find a real bug in this environment, using nothing but the method — and prove it with evidence rather than a status code.

A user reports: *"I updated my display name and it said it saved, but it's still showing the old one."* Investigate.

**Step 1.** Log out of the admin account and back in as `student`:

```
$ open -X POST https://cybershop.training/logout
```
```
$ open -X POST -d "username=student&password=training123" https://cybershop.training/auth/login
```

**Step 2.** Establish the baseline — what does the profile API currently hold?

```
$ open https://cybershop.training/api/profile
━━━━━━━━ REQUEST ━━━━━━━━
GET /api/profile HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 50
Server: CyberShop-Sim/1.0
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'

{"username": "student", "display_name": "student"}
```

Record that: `display_name` is currently `"student"`, and the response is 50 bytes. **That is your baseline**, and it is the thing every later claim in this exercise will be measured against. If your own session shows a different value here, an earlier request in your session already changed it — establish your own baseline rather than assuming the one printed in a lesson.

**Step 3.** Send the update the user described. Note the field name carefully:

```
$ open -X POST -H "Content-Type: application/json" -d '{"Display_Name": "Alex Rivera"}' https://cybershop.training/api/profile
━━━━━━━━ REQUEST ━━━━━━━━
POST /api/profile HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/json
Content-Length: 31
Cookie: session_id=student-session

{"Display_Name": "Alex Rivera"}

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 48
Server: CyberShop-Sim/1.0
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'

{"status": "updated", "display_name": "student"}
```

**Stop and read that response properly.** Status `200 OK`. Body says `"status": "updated"`. And `"display_name": "student"` — the *old* value. The server reported success and returned unchanged data in the same breath.

**Step 4.** Verify independently. Never trust a write operation's own report:

```
$ open https://cybershop.training/api/profile
━━━━━━━━ REQUEST ━━━━━━━━
GET /api/profile HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 50
Server: CyberShop-Sim/1.0
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'

{"username": "student", "display_name": "student"}
```

Confirmed. Nothing was stored.

**Step 5.** Form a hypothesis and test it with one variable changed. The only difference you can control is the field name — `Display_Name` versus `display_name`:

```
$ open -X POST -H "Content-Type: application/json" -d '{"display_name": "Alex Rivera"}' https://cybershop.training/api/profile
━━━━━━━━ REQUEST ━━━━━━━━
POST /api/profile HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/json
Content-Length: 31
Cookie: session_id=student-session

{"display_name": "Alex Rivera"}

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 52
Server: CyberShop-Sim/1.0
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'

{"status": "updated", "display_name": "Alex Rivera"}
```

**Step 6.** Verify again:

```
$ open https://cybershop.training/api/profile
━━━━━━━━ REQUEST ━━━━━━━━
GET /api/profile HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 54
Server: CyberShop-Sim/1.0
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'

{"username": "student", "display_name": "Alex Rivera"}
```

**Step 7.** Review the whole session and compare the two POSTs directly:

```
$ requests
Request history:
  #1  GET /products  -> 200 OK
  #2  GET /products  -> 200 OK
  #3  GET /products  -> 200 OK
  #4  GET /account  -> 302 Found
  #5  POST /auth/login  -> 302 Found
  #6  GET /account  -> 200 OK
  #7  GET /admin  -> 403 Forbidden
  #8  POST /logout  -> 302 Found
  #9  GET /admin  -> 401 Unauthorized
  #10  POST /auth/login  -> 302 Found
  #11  GET /admin  -> 200 OK
  #12  POST /logout  -> 302 Found
  #13  POST /auth/login  -> 302 Found
  #14  GET /api/profile  -> 200 OK
  #15  POST /api/profile  -> 200 OK
  #16  GET /api/profile  -> 200 OK
  #17  POST /api/profile  -> 200 OK
  #18  GET /api/profile  -> 200 OK
```

Look at #15 and #17. Both `POST /api/profile`, both `200 OK`. From the history line alone they are indistinguishable — yet one worked and one did nothing.

```
$ compare 15 17
Comparing #15 vs #17 responses:
  HTTP/1.1 200 OK
  Content-Type: application/json
! #15: Content-Length: 48
! #17: Content-Length: 52
  Server: CyberShop-Sim/1.0
  Cache-Control: no-store
  Content-Security-Policy: default-src 'self'; script-src 'self'
  
! #15: {"status": "updated", "display_name": "student"}
! #17: {"status": "updated", "display_name": "Alex Rivera"}
```

Two differences: `Content-Length` (48 vs 52) and the body. **That length difference is the whole finding, visible at a glance** — this is exactly why testers sort history by length.

**Answer:**

1. Why is `200 OK` insufficient evidence that the update succeeded?
2. What was the one variable that differed between the two POSTs?
3. Why did Step 4 need to exist at all, given Step 3 already returned a response?
4. Why did the history summary lines fail to distinguish the working from the broken request?
5. Is this a *security* vulnerability? Argue it either way, then state where you land.
6. What would you check next if this were a real application?

<details>
<summary>Discussion</summary>

1. Because the status code reports the HTTP exchange, not the business outcome. The server received the request, understood it, and answered — all true, and none of it says the value was stored. This is the single most common source of false confidence in web testing.

2. The JSON field name's capitalisation: `Display_Name` versus `display_name`. Everything else — method, path, headers, cookie, value, even body length — was identical.

3. Because Step 3's response is the *writer's own report* of what it did, and it was wrong. Independent verification means reading the state back through a different operation. Never accept a write's self-assessment.

4. Because the summary shows method, path and status only. All three were identical. The difference lived in the request body and the response body — which is why you open the exchange rather than reading the index.

5. **Against:** it's a data-integrity/usability bug — an update silently fails, no data is exposed, no control is bypassed. **For:** an API that accepts unrecognised fields without complaint conceals whatever else a client might send; silent-ignore behaviour hides errors from monitoring; and the same tolerant-parsing habit is what lets mass-assignment bugs through, where an unexpected field like `role` *is* honoured. **Where to land:** report it as a functional defect with a security note about silent acceptance of unknown fields. Precise, honest, and useful to the team receiving it — which is a better outcome than either inflating it or dismissing it.

6. Whether *other* fields are silently ignored; whether any unexpected field is silently *accepted* (send `{"role": "admin"}` and read the state back); whether the same endpoint's `GET` and `POST` enforce the same authorization; whether the failure is logged server-side at all.
</details>

## 10. The Evidence Report

This is the deliverable. A finding nobody can verify isn't a finding — it's an assertion.

```
TARGET
    Authorized training application — cybershop.training, YushaCyber
    Burp Suite Fundamentals mission (fully simulated; no real host).

ENDPOINT
    POST /api/profile   (JSON body, cookie-session authenticated)

REQUEST
    POST /api/profile HTTP/1.1
    Host: cybershop.training
    Content-Type: application/json
    Content-Length: 31
    Cookie: session_id=student-session

ORIGINAL INPUT
    {"Display_Name": "Alex Rivera"}

MODIFIED INPUT
    {"display_name": "Alex Rivera"}      (field name capitalisation only)

ORIGINAL RESPONSE
    200 OK, Content-Length 48
    {"status": "updated", "display_name": "student"}

MODIFIED RESPONSE
    200 OK, Content-Length 52
    {"status": "updated", "display_name": "Alex Rivera"}

VERIFICATION
    GET /api/profile after each POST.
    After the original:  {"username": "student", "display_name": "student"}
    After the modified:  {"username": "student", "display_name": "Alex Rivera"}

OBSERVED DIFFERENCE
    Identical status (200) and identical "status": "updated" text in both
    cases; the stored value changed only for the lowercase field name.
    Response length differed: 48 vs 52 bytes.

INTERPRETATION
    The endpoint accepts a JSON body and applies only the exact key
    `display_name`. An unrecognised key is ignored without error, while the
    response still reports success.

SECURITY SIGNIFICANCE
    Primarily a data-integrity and observability defect: a failed update is
    indistinguishable from a successful one to any client, and to any
    monitoring that keys on status codes. Secondary concern: silent
    acceptance of unrecognised fields is the same tolerance that permits
    mass-assignment issues where an unexpected field IS honoured. No data
    exposure or access-control bypass was observed or tested for.

CONFIDENCE
    High that the behaviour is as described — reproduced twice, with
    independent read-back verification after each write, one variable
    changed between the two attempts.
    Low regarding wider security impact — no test was performed for
    mass assignment or for authorization on this endpoint.

WHAT WOULD VALIDATE THIS FURTHER
    - Send an unexpected privileged-looking field and read the state back.
    - Enumerate which field names the endpoint honours.
    - Check whether rejected/ignored fields are logged server-side.
    - Test whether GET and POST enforce the same authorization.
```

**What makes this report work**, and what to copy from it:

- **Anyone can reproduce it.** Exact endpoint, exact bodies, exact responses.
- **Verification is separate from the write.** The `GET` read-back is what turns an assertion into evidence.
- **Confidence is stated per claim**, not once for the whole document — high on the behaviour, low on the impact. Both are true simultaneously, and saying so is what makes the high-confidence claim believable.
- **It says what it did *not* test.** That is not weakness; it's the difference between a report and a sales pitch.
- **It doesn't inflate.** No CVSS score invented, no scary label attached. A functional defect described precisely is more useful to the team fixing it than a vulnerability that isn't there.

## 11. Observation, Interpretation, Conclusion

The habit, once more, because it is what the whole module is really teaching:

| Register | What it is | Test for it |
|---|---|---|
| **Observation** | What the evidence literally shows | Could someone re-run your steps and see the same thing? |
| **Interpretation** | What you think explains it | Is there a competing explanation you haven't ruled out? |
| **Conclusion** | The claim you'll stand behind | Would you say it in a meeting with the engineer who wrote the code? |

Applied to Exercise 6:

> **OBSERVATION.** A `POST` with `{"Display_Name": ...}` returned `200 OK` and `"status": "updated"`; a subsequent `GET` showed the value unchanged. A `POST` differing only in the field name's capitalisation returned `200 OK` and the `GET` showed the value changed.
>
> **INTERPRETATION.** The endpoint matches the field name exactly and ignores unrecognised keys without signalling an error.
>
> **CONCLUSION.** Updates via this endpoint can fail silently while reporting success. Confidence: high on the behaviour; low on any wider security impact, which was not tested.

## 12. Common Mistakes

**Treating `200 OK` as "it worked."** Exercise 6 exists entirely to break this habit. Verify by reading the state back.

**Changing several things at once.** You get one difference in the output and no way to attribute it.

**Citing the history summary line.** It shows method, path and status. Entries #15 and #17 were indistinguishable there and completely different in reality.

**Skipping the baseline.** Without the original request and its exact response recorded, "it changed" is unsupportable.

**Not re-running the baseline afterwards.** If the original request no longer produces the original response, something else moved and your comparison is contaminated.

**Reporting a parameter change as a vulnerability.** Exercise 3's `id` parameter behaves exactly as a catalogue should. Different response ≠ finding.

**Inferring authorization from the interface.** `/admin` isn't linked anywhere and still answers. The `403` is the control; the missing link is not.

**Testing outside scope.** In this environment the proxy refuses. In the real world, nothing refuses for you — you are the control.

## 13. Practice on This Platform

**Burp Suite Fundamentals** (terminal mission) — the environment these six exercises run in, with fourteen scored objectives covering the same ground and more: proxy architecture, enabling interception, intercepting a `GET`, forwarding, dropping, modifying a query parameter, modifying a header, modifying a `POST` body, reviewing history, sending to Repeater, modifying and re-sending in Repeater, comparing two responses, hitting the scope boundary, and a final investigation of the same silent-update bug you met in Exercise 6 — where you're asked to find it yourself and write your conclusion to a file.

**HTTP Requests & Responses** (interactive lab) — a different simulator with a different shape: a single fixed HTTP exchange you inspect with `http`, `headers` and `status` commands, auditing what the request and response contain. You met it in Web Fundamentals; it's worth a second visit now, because the questions you can ask of an exchange have grown considerably since then.

Note the difference honestly: the lab is a separate simulator with its own commands, and it has no proxy, no Repeater and no history. The concepts transfer; the commands don't.

The remaining web-security labs (`websec-idor`, `websec-auth`, `websec-sessions`, `websec-headers` and the rest) are real and sit in the same category, but they unlock in sequence behind one another and their subject matter belongs to `owasp-top-10`. You'll meet them there rather than here.

## 14. Knowledge Check

1. Walk through the workflow from §3. Why does INSPECT come before MODIFY, and what breaks if you reverse them?
2. In Exercise 2 you forwarded a request unchanged. What would you conclude if the response had differed from Exercise 1's?
3. In Exercise 3, `id=42` and `id=43` returned different bodies. Write the observation and then explain why it is not a finding.
4. `edit query id abc` returns `200 OK`. What does that tell you about the endpoint, and what does it *not* tell you?
5. In Exercise 4, exactly one thing differed between the two `/account` requests. What was it, and which earlier response created it?
6. Why is comparing your own authenticated and unauthenticated requests a complete session test that requires nobody else's session?
7. In Exercise 5, one URL returned `403`, `401` and `200`. Explain each in terms of authentication versus authorization.
8. `/admin` is not linked from any page. Why doesn't that protect it?
9. In Exercise 6, both POSTs returned `200 OK`. What single piece of evidence proved one of them did nothing?
10. Why does the evidence report include a "what would validate this further" section?
11. Why is confidence stated per claim rather than once per report?
12. Why must every technique in this lesson only ever be used against authorized targets, given that none of it damages anything?

## 15. Key Takeaways

- Inspect before you modify. Without a recorded baseline, a change produces no evidence.
- One variable at a time, always — and re-run the baseline afterwards to prove nothing else moved.
- The history line is an index; the full exchange is the evidence. Two identical-looking entries can be completely different requests.
- `200 OK` describes the HTTP exchange, not the outcome. Verify a write by reading the state back through a separate request.
- Response length is the fastest difference detector you have. 48 versus 52 bytes was an entire finding.
- Compare status, length, headers, body and redirect target — not just the status code.
- A parameter that changes the response is doing its job. It becomes a finding only when it crosses an authorization boundary.
- `401` means the server doesn't know you; `403` means it does and refuses. Both being enforced server-side is a control working correctly, and reporting that is real work.
- The server is the security boundary. A hidden button, an unlinked route and a client-side check protect nothing.
- Keep observation, interpretation and conclusion separate. State confidence per claim, and say plainly what you did not test.
- Authorization first, permanently. The technique is identical whether authorized or not; the permission is the entire difference.

## 16. What's Next

You can now capture a request, read it completely, replay it deliberately, change one thing at a time, compare the results honestly, and write up what you found in a form somebody else can verify. That is the working method of web application testing, and the tool is the least important part of it.

**OWASP Top 10** takes the authorization reasoning from Exercise 5 into its named categories — broken access control, injection, authentication failures — with the labs to match. **Web Pentesting** builds full assessment methodology on the same loop. **API security**, when you meet it, is the `/api/profile` investigation from Exercise 6 repeated against systems where the silent acceptance of an unexpected field is not merely a defect.

The instrument changes. The reasoning — observe, hypothesise, test one thing, compare, document honestly — does not.
