# Hands-on Practice: An OWASP-Style Web Application Investigation

## 1. Authorization Comes First

Everything below runs against YushaCyber's simulated training site, `cybershop.training`, which exists entirely as Python data structures inside this platform and has no HTTP client in it at all. It cannot reach anything real. You are explicitly authorized to test it, and explicitly authorized to use all three training accounts, because you are being handed them.

**Nothing in this lesson may be repeated against a system you do not own or have written permission to test.** Not a public site, not your employer's site, not a friend's account. The techniques are ordinary HTTP requests; what makes testing legitimate is authorization, and nothing else.

When you want to go further after this module, install a deliberately vulnerable application on your own machine — OWASP Juice Shop, DVWA — or use PortSwigger's Web Security Academy, which provides targets published for exactly this purpose.

**What this lesson does not teach**, and will not: stealing or forging sessions, credential stuffing or brute-forcing real accounts, attacking cloud metadata services, destructive injection against any system, or evading detection. Where this platform cannot demonstrate something honestly, the lesson says so instead of inventing an example — there is one such exercise below, and it is labelled.

## 2. The Environment

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

Three fixed, fictional training accounts:

| Account | Password | Role |
|---|---|---|
| `student` | `training123` | ordinary user |
| `analyst` | `analyst123` | ordinary user |
| `admin` | `admin123` | administrator |

**Everything below is one continuous session, run in order.** That matters: the request history at the end is the real history of these exact commands, and the numbers in it line up with the exercises. If you run the exercises out of order your history will differ from the one printed here, and that is fine — but the numbers will not match.

## 3. The Workflow

```
AUTHORIZED TARGET
    ↓
ORIENT — what is this application, what does it do, what does it expose?
    ↓
CAPTURE a normal request                    ← the baseline; skip this and nothing later means anything
    ↓
IDENTIFY the input the client controls
    ↓
FORM a hypothesis about what the server does with it
    ↓
CHANGE exactly one variable
    ↓
SEND
    ↓
COMPARE against the baseline — status, headers, body, length, state
    ↓
VALIDATE — reproduce it, rule out coincidence, read the state back
    ↓
IDENTIFY the security impact
    ↓
RECOMMEND a mitigation
    ↓
DOCUMENT the evidence
```

ORIENT is the step people skip, and skipping it is why so many first assessments consist of firing payloads at whatever field is visible. You cannot recognise abnormal behaviour in an application whose normal behaviour you never observed.

---

## 4. Exercise 1 — Broken Access Control (A01:2021)

**Objective:** determine whether the authorization decision on `/admin` is made server-side, and whether it distinguishes identity from permission.

**Hypothesis to test:** *if authorization is enforced server-side, the same URL will produce different outcomes purely as a function of which session the request carries.*

### Step 1 — the unauthenticated baseline

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

No `Cookie` header went out; `401` came back. Record it — this is the baseline, and the reason you can interpret everything that follows.

### Step 2 — authenticate as an ordinary user

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

```
$ cookies
session_id=student-session
```

The `Set-Cookie` is the server establishing a session; `cookies` confirms your client stored it. Authentication has succeeded — which is a fact about *identity*, and about nothing else yet.

### Step 3 — change exactly one variable

The URL is identical to step 1. The only difference is that a session cookie now goes with it.

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

The status changed from `401` to `403`, and the body states the distinction outright. Confirm the session genuinely works on a route this account *is* entitled to, so you know the `403` is about permission rather than a broken session:

```
$ open https://cybershop.training/profile
━━━━━━━━ REQUEST ━━━━━━━━
GET /profile HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 16
Server: CyberShop-Sim/1.0
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'

Profile: student
```

That control step matters. Without it, "`/admin` returned 403" is compatible with "my session is invalid", and you would be interpreting the wrong thing.

### Step 4 — the privileged comparison

```
$ open -X POST -d "username=admin&password=admin123" https://cybershop.training/auth/login
━━━━━━━━ REQUEST ━━━━━━━━
POST /auth/login HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 32
Cookie: session_id=student-session

username=admin&password=admin123

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 302 Found
Location: /profile
Content-Length: 0
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'
Set-Cookie: session_id=admin-session
```

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

Log back out before the next exercise:

```
$ open -X POST https://cybershop.training/logout
━━━━━━━━ REQUEST ━━━━━━━━
POST /logout HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=admin-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 302 Found
Location: /login
Content-Length: 0
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'
Set-Cookie: session_id=; Max-Age=0
```

### Required reasoning

**OBSERVATION:** `GET /admin` returned `401` with no session cookie, `403` with the `student` session cookie, and `200` with an admin page body under the `admin` session cookie. `GET /profile` returned `200` under the `student` session, confirming that session was valid.

**INTERPRETATION:** the server distinguishes "unauthenticated" from "authenticated but not permitted", and grants access as a function of which account the session belongs to. Because the URL and every other part of the request were held constant, the decision cannot be coming from anything the client chose except the session identity.

**CONCLUSION:** on this route, authorization appears to be enforced server-side and was not bypassed by the modifications tested. **This is not a finding — it is the control working.** Confidence: high for this route and these requests; nothing here establishes anything about other routes, other HTTP methods, or bypasses not attempted.

### What you cannot conclude

- That **every** route enforces authorization. You tested one.
- That the check cannot be bypassed at all. You tested three request shapes.
- That `403` in general means a control is working. Here it does, because you controlled for session validity. Elsewhere, a `403` returned to everyone including legitimate owners would look identical and mean something quite different.

### The test this environment cannot run

The horizontal case — log in as user A, request A's own record, change **only** the record identifier to one belonging to user B, and see whether B's data comes back — is the most common shape of broken access control in the wild. **This simulator has no per-user resource endpoint**, so that test cannot be performed here, and no invented example is offered in its place. The reasoning is in Core Concepts §6 in full; the runnable version lives in the real **IDOR — Insecure Direct Object Reference** lab (see §12 for how the lab chain unlocks) and in any deliberately vulnerable application you install yourself.

### Common mistake

Concluding "secure" from step 3 alone. A single `403` tells you one request was refused. It was the *comparison* across three identities on one unchanged URL that made the interpretation possible.

---

## 5. Exercise 2 — Injection (A03:2021)

**Objective:** determine whether the `/search` endpoint builds its database query by concatenating user input, and demonstrate the difference against the parameterised endpoint.

**Hypothesis to test:** *if the query is built by concatenation, an input containing quoting syntax will change the query's structure rather than only its value — and that change will be visible in the application's behaviour.*

### Step 1 — orient

```
$ schema
Training database schema (read-only, fictional — cybershop.training):

users:
  id (INTEGER)
  username (TEXT)
  role (TEXT)

products:
  id (INTEGER)
  name (TEXT)
  price (INTEGER)
  category (TEXT)

orders:
  id (INTEGER)
  user_id (INTEGER)
  product_id (INTEGER)
  quantity (INTEGER)

reviews:
  id (INTEGER)
  product_id (INTEGER)
  username (TEXT)
  rating (INTEGER)

comments:
  id (INTEGER)
  author (TEXT)
  content (TEXT)
  created_at (TEXT)
```

Structure only — no rows, ever. Knowing the table a search probably queries tells you what a structural change would be *for*.

### Step 2 — the baseline

```
$ open https://cybershop.training/search?q=Monitor
━━━━━━━━ REQUEST ━━━━━━━━
GET /search?q=Monitor HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 85
Server: CyberShop-Sim/1.0
Cache-Control: no-store
X-Sim-Query-Kind: normal
X-Sim-Query: SELECT * FROM products WHERE name = 'Monitor'
X-Sim-XSS-Kind: none
X-Sim-XSS-Context: html_text
Content-Security-Policy: default-src 'self'; script-src 'self'

Search results for 'Monitor': 1 match(es) in the training catalog.
  - Monitor ($199)
```

```
$ query
Simulated query representation — not a live SQL console.

User Input:         Monitor
Application Query:  SELECT * FROM products WHERE name = 'Monitor'
Database:           cybershop.training (simulated, read-only)
Response:           200 OK
```

One search term, one matching product. Ordinary behaviour, and now recorded.

### Step 3 — change one character

```
$ open "https://cybershop.training/search?q='"
━━━━━━━━ REQUEST ━━━━━━━━
GET /search?q=' HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 500 Internal Server Error
Content-Type: text/plain
Content-Length: 51
Server: CyberShop-Sim/1.0
X-Sim-Query-Kind: error
X-Sim-Query: SELECT * FROM products WHERE name = '''
X-Sim-XSS-Kind: none
X-Sim-XSS-Context: html_text
Content-Security-Policy: default-src 'self'; script-src 'self'

Database error: Unexpected quote in training query.
```

```
$ query
Simulated query representation — not a live SQL console.

User Input:         '
Application Query:  SELECT * FROM products WHERE name = '''
Database:           cybershop.training (simulated, read-only)
Response:           500 Internal Server Error

Unsafe string concatenation let the input change the query's structure.
```

A signal, not yet a finding. The `500` and the three-apostrophe query say the input reached something that cares about quoting. Do not stop here — a `500` alone is compatible with an ordinary bug.

### Step 4 — change the query's meaning

```
$ open "https://cybershop.training/search?q=' OR '1'='1"
━━━━━━━━ REQUEST ━━━━━━━━
GET /search?q=' OR '1'='1 HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 275
Server: CyberShop-Sim/1.0
Cache-Control: no-store
X-Sim-Query-Kind: boolean_true
X-Sim-Query: SELECT * FROM products WHERE name = '' OR '1'='1'
X-Sim-XSS-Kind: none
X-Sim-XSS-Context: html_text
Content-Security-Policy: default-src 'self'; script-src 'self'

Search results for '' OR '1'='1': 4 match(es) in the training catalog.
  - Laptop ($999)
  - Keyboard ($49)
  - Monitor ($199)
  - Mouse ($25)

Simulated: the injected condition made the query's logic always true, so every row matched — not a real, intentional search result.
```

```
$ query
Simulated query representation — not a live SQL console.

User Input:         ' OR '1'='1
Application Query:  SELECT * FROM products WHERE name = '' OR '1'='1'
Database:           cybershop.training (simulated, read-only)
Response:           200 OK

Unsafe string concatenation let the input change the query's structure.
```

**This is the evidence.** A term matching no product returned every product. `Content-Length` went from `85` to `275`. The only explanation consistent with the baseline is that the query no longer asks "name equals this text."

### Step 5 — prove the defence

```
$ open "https://cybershop.training/secure-search?q=' OR '1'='1"
━━━━━━━━ REQUEST ━━━━━━━━
GET /secure-search?q=' OR '1'='1 HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 90
Server: CyberShop-Sim/1.0
Cache-Control: no-store
X-Sim-Query-Kind: parameterized
X-Sim-Query: SELECT * FROM products WHERE name = ?
X-Sim-XSS-Kind: none
X-Sim-XSS-Context: html_text
Content-Security-Policy: default-src 'self'; script-src 'self'

Search results for '&#x27; OR &#x27;1&#x27;=&#x27;1': 0 match(es) in the training catalog.
```

```
$ query
Simulated query representation — not a live SQL console.

User Input:         ' OR '1'='1
Application Query:  SELECT * FROM products WHERE name = ?
Database:           cybershop.training (simulated, read-only)
Response:           200 OK

Parameterized query: the input stayed data — the query structure never changed.
```

Same input. Zero matches, because no product has that name. The query is `WHERE name = ?` — the identical string it would be for any input at all.

### Required reasoning

**OBSERVATION:** on `/search`, a term matching no product returned all four catalogue rows, and a single apostrophe produced `500` with a database error message in the body. On `/secure-search`, the identical term returned zero matches with a `200`, and the reported query contained a placeholder rather than the input.

**INTERPRETATION:** `/search` appears to construct its query by concatenating the `q` parameter into the query string, so the parameter can alter the query's structure. `/secure-search` appears to pass `q` as a bound parameter, so the structure is fixed before the value is applied.

**CONCLUSION:** `/search` is affected by SQL injection. The evidence is a behavioural change — a non-matching term returning every row — that only a structural change to the query explains, corroborated by the reported query representation and by the contrasting behaviour of a parameterised endpoint given identical input. Confidence: high.

### What you cannot conclude

- That data outside the `products` table was reached. You did not demonstrate that, and you should not claim it.
- That the same flaw exists on other endpoints. `/secure-search` demonstrably does not have it.
- Anything at all from step 3 on its own.

### Common mistake

Reporting the payload as the finding. `' OR '1'='1` is how you demonstrated the problem; it is not the problem. The finding is that user input can alter query structure at `/search`, and the fix is parameterisation — which is why step 5 belongs in your evidence just as much as step 4.

---

## 6. Exercise 3 — Identification and Authentication Failures (A07:2021)

**Objective:** trace the full authentication lifecycle and determine where session validity is actually decided.

**Hypothesis to test:** *if the server is the authority on session validity, then a request carrying a cookie the server no longer recognises will be rejected even though the client changed nothing.*

### Step 1 — a failed login

```
$ open -X POST -d "username=student&password=wrong-password" https://cybershop.training/auth/login
━━━━━━━━ REQUEST ━━━━━━━━
POST /auth/login HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 40

username=student&password=wrong-password

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 401 Unauthorized
Content-Type: application/json
Content-Length: 41
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'

{"error": "Invalid training credentials"}
```

Two observations worth writing down. **No `Set-Cookie`** — a failed login establishes nothing. And the message does not distinguish "no such user" from "wrong password", which denies an enumeration signal that many applications leak.

### Step 2 — a successful login

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

### Step 3 — establish that the session works

```
$ open https://cybershop.training/profile
━━━━━━━━ REQUEST ━━━━━━━━
GET /profile HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 16
Server: CyberShop-Sim/1.0
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'

Profile: student
```

Baseline recorded: this cookie, this route, `200 OK`, body `Profile: student`.

### Step 4 — change one variable, on the server's side only

```
$ expire
Session expired (simulator-controlled, not real time). Your browser still holds the old session cookie, but the server no longer recognizes it — the next protected request will be treated as unauthenticated.
```

```
$ open https://cybershop.training/profile
━━━━━━━━ REQUEST ━━━━━━━━
GET /profile HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 401 Unauthorized
Content-Type: text/plain
Content-Length: 34
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'

You must log in to view this page.
```

Compare the two requests line by line. They are **identical**, `Cookie: session_id=student-session` included. The client sent exactly what it sent when the request succeeded. The response is `401`.

### Required reasoning

**OBSERVATION:** `GET /profile` with `Cookie: session_id=student-session` returned `200 OK` with body `Profile: student`. After the server-side expiry, the byte-identical request returned `401 Unauthorized`.

**INTERPRETATION:** session validity is determined by server-side state, not by the presence of a cookie. Holding the cookie is a *claim* of identity, which the server re-evaluates on every request.

**CONCLUSION:** authentication state on this application is maintained server-side, and possession of a session cookie does not by itself grant access. This is the correct behaviour — again, a control working rather than a finding. Confidence: high, for this route.

### What you cannot conclude

- That the session identifier is generated securely. You never examined how it is produced — and in this simulator it is a fixed, readable training value, which a real application must never do.
- That the cookie carries appropriate `Secure` / `HttpOnly` / `SameSite` attributes. Look at the `Set-Cookie` line in step 2: it carries none. In a real assessment that is a genuine, reportable observation about cookie configuration; here it is a property of a deliberately simplified simulator, and reporting it as a finding against a training environment would be padding.
- Anything about rate limiting. One failed login is not a test of that.

### Common mistake

Treating logout and expiry as the same event. Logout does two things — tells the browser to drop the cookie *and* invalidates the session server-side. Only the second is a security control. An application that clears the cookie without invalidating the session server-side is broken in a way that looks perfectly fine from the browser.

---

## 7. Exercise 4 — Security Misconfiguration (A05:2021)

**Objective:** examine what the application discloses about itself, and which browser-enforced protections it does and does not request.

Log back in first (your session was expired in the previous exercise):

```
$ open -X POST -d "username=student&password=training123" https://cybershop.training/auth/login
━━━━━━━━ REQUEST ━━━━━━━━
POST /auth/login HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 37
Cookie: session_id=student-session

username=student&password=training123

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 302 Found
Location: /profile
Content-Length: 0
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'
Set-Cookie: session_id=student-session
```

Notice the request still carried the stale cookie — the client had no way to know the server had discarded that session. That is the same lesson as Exercise 3, arriving from the other direction.

### Step 1 — read a response's headers properly

```
$ open https://cybershop.training/products?id=42
━━━━━━━━ REQUEST ━━━━━━━━
GET /products?id=42 HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

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

Work through it as two lists.

**What is present:**

| Header | Reading |
|---|---|
| `Content-Security-Policy: default-src 'self'; script-src 'self'` | A real, restrictive policy, sent on every response. A control doing its job — record it |
| `Server: CyberShop-Sim/1.0` | Software name and version, volunteered to anyone. Information disclosure |
| `Cache-Control: max-age=60` | This page may be cached. Correct for a public catalogue page — and worth checking is *not* the value on pages carrying user data |

**What is absent:** `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options` (or a CSP `frame-ancestors` directive), `Referrer-Policy`.

### Step 2 — compare error handling

You already have one verbose error from Exercise 2:

```
Database error: Unexpected quote in training query.
```

Now the application's handling of an ordinary missing route:

```
$ open https://cybershop.training/nothing-here
━━━━━━━━ REQUEST ━━━━━━━━
GET /nothing-here HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 404 Not Found
Content-Type: text/plain
Content-Length: 37
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'

The requested resource was not found.
```

Two error paths, two very different disclosure levels. The `404` is exactly right: accurate, useful, revealing nothing internal. The database error is not — it hands an unauthenticated stranger information about the application's internals.

### Required reasoning

**OBSERVATION:** responses carry `Server: CyberShop-Sim/1.0` and a `Content-Security-Policy`, and do not carry `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options` or `Referrer-Policy`. The `/search` error path returns an internal database message; the `404` path returns a generic message.

**INTERPRETATION:** security headers appear to have been configured deliberately but partially. Error handling appears inconsistent: the generic path is well-behaved, and at least one specific path leaks internal detail.

**CONCLUSION:** the version disclosure and the verbose database error are real observations, and the missing headers are real absences. Whether each rises to a *finding*, and at what severity, depends on what the application does — a missing `X-Frame-Options` matters far more on a page with a one-click state-changing action than on a static catalogue page. State the observation; justify the severity separately.

### What you cannot conclude

- That the disclosed version is vulnerable. See Exercise 5's discussion and Core Concepts §20 — a version string is where an investigation starts.
- That missing headers are exploitable. Absence of a defence is not the presence of an attack; you would need to show what it lets someone do.

### Common mistake

Reporting every absent header as a high-severity finding because a scanner listed it. That is the fastest way to make a report that a competent engineer stops reading. Tie each one to what it would have protected on *this* application, or leave it as an informational note.

---

## 8. Exercise 5 — Server-Side Request Forgery (A10:2021), reasoning only

**This exercise runs no commands against a vulnerable endpoint, because this platform has no SSRF scenario and none is invented here.** Every route on the simulated site serves data it already holds; none fetches a URL on the server's behalf. Rather than fabricate a lab, this exercise is a reasoning exercise — which is genuinely how you assess SSRF risk in a design review anyway.

One thing you *can* run, and it is instructive precisely because it is the **contrast**:

```
$ open https://evil.example.com/
External hosts are not available in the training environment.
```

That is a client-side scope control: your own tool refused to build the request. No server was involved. It is the opposite of SSRF, and holding the two side by side is the fastest way to fix the distinction.

```
NORMAL:   client  ──►  your server                       you fetch nothing on their behalf

SSRF:     client  ──►  your server  ──►  somewhere else   the client chose the destination
```

**The scenario.** An application adds a feature: users may set a profile picture by supplying a URL, which the server fetches and stores. The submitted request looks like this — **illustrative example, not captured output; no such endpoint exists on this platform**:

```
POST /profile/avatar HTTP/1.1
Host: example-app.invalid
Content-Type: application/x-www-form-urlencoded

image_url=https://cdn.example.com/pictures/me.png
```

**Answer these before reading on:**

1. Which component makes the outbound request — the browser or the server?
2. What does that component have access to that the user's browser does not?
3. Why is "block URLs containing `localhost` or `127.0.0.1`" an inadequate defence?
4. If the server fetches the URL but never shows the user the fetched content, is there still a risk?
5. What would you actually recommend?

<details>
<summary>Discussion</summary>

**1.** The server. The user submits a *string*; the application's own code turns that string into an outbound HTTP request from the server. That single fact is the whole category.

**2.** The server's network position (internal networks, management interfaces and services never exposed externally), its credentials and trust relationships, and its position inside the perimeter — every firewall rule written to keep outsiders out is a rule the server is already on the trusted side of. "It's only reachable internally" is a network assumption, and SSRF is precisely the thing that breaks it.

**3.** Because it is a blocklist, and blocklists fail against inputs you did not enumerate. Alternative representations of the same address, other private ranges, a hostname you control whose DNS record points into private space, and a redirect from an allowed host to an internal one all defeat it. Worse, validating the submitted string and then following redirects means the thing you validated is not the thing you fetched.

**4.** Yes. Even with no content returned, differences in response time and in error behaviour let an attacker infer which hosts and ports respond — enough to map an internal network. If the request itself causes a state change at the destination, the impact does not depend on reading the response at all.

**5.** Allowlist the destinations — protocols, hosts, ports — rather than blocklisting. Resolve the hostname and validate the resulting address *before connecting*, and again after any redirect, rather than validating the submitted string. Segment the network so the fetching service can reach only what it needs. Do not return the raw fetched response to the client. And require authentication on internal services, so reaching them is not the same as using them.

Notice that the strongest answer to "should we build this?" is sometimes "have the user upload the image instead" — which removes the server-side fetch entirely. Design changes are legitimate mitigations.
</details>

---

## 9. Exercise 6 — The Finding Report

A vulnerability name is not a finding. A finding is a claim someone else can verify, whose impact someone else can weigh, with a fix someone else can implement.

### Step 1 — your session history

```
$ requests
Request history:
  #1  GET /admin  -> 401 Unauthorized
  #2  POST /auth/login  -> 302 Found
  #3  GET /admin  -> 403 Forbidden
  #4  GET /profile  -> 200 OK
  #5  POST /auth/login  -> 302 Found
  #6  GET /admin  -> 200 OK
  #7  POST /logout  -> 302 Found
  #8  GET /search  -> 200 OK
  #9  GET /search  -> 500 Internal Server Error
  #10  GET /search  -> 200 OK
  #11  GET /secure-search  -> 200 OK
  #12  POST /auth/login  -> 401 Unauthorized
  #13  POST /auth/login  -> 302 Found
  #14  GET /profile  -> 200 OK
  #15  GET /profile  -> 401 Unauthorized
  #16  POST /auth/login  -> 302 Found
  #17  GET /products  -> 200 OK
  #18  GET /nothing-here  -> 404 Not Found
```

That is the whole investigation in eighteen lines, and it is the skeleton your evidence hangs on. Note what the summary does **not** show: the query string. Entries `#8`, `#9` and `#10` all read `GET /search`, and they are three completely different tests. A history listing is an index, not evidence — the individual request and response are the evidence.

### Step 2 — the template

Use every field. The ones people skip — severity *reasoning*, validation strategy, confidence — are the ones that make a report trustworthy.

```
FINDING:
    A single sentence naming the failure, not the payload.

OWASP CATEGORY:
    AXX:2021 – Name. Plus one line saying which control failed, and why
    this category rather than a neighbouring one.

AFFECTED ENDPOINT:
    Method, path, and the parameter or header involved.

INPUT:
    The exact input, and where in the request it sits.

ORIGINAL REQUEST:
    The baseline, in full.

MODIFIED REQUEST:
    The test request, in full. Exactly one thing differs from the baseline.

OBSERVED RESPONSE:
    Status, relevant headers, and the body — or the part of it that matters.

EVIDENCE:
    Why these two responses together demonstrate the claim. This is the
    reasoning, not a restatement of the output.

SECURITY IMPACT:
    What this lets someone do, concretely, on this application.

SEVERITY REASONING:
    Why that rating: impact, how reachable it is, what is required to
    exploit it, and what data or function is at stake.

RECOMMENDED FIX:
    The specific change that removes the false assumption.

VALIDATION STRATEGY:
    How someone confirms the fix worked — including the case that must
    now fail.

CONFIDENCE:
    High / Medium / Low, and what would raise it.

NOT TESTED:
    What you did not check, so nobody reads more into this than it says.
```

### Step 3 — a worked example

Written from Exercise 2, using only evidence actually produced above.

```
FINDING:
    The /search endpoint constructs its database query by concatenating
    the client-supplied `q` parameter, allowing that parameter to alter
    the query's structure.

OWASP CATEGORY:
    A03:2021 – Injection. The control that failed is safe handling of
    untrusted input at an interpreter boundary: the input does not stay
    data. Not A04, because the endpoint has a correct implementation
    available on the same application (/secure-search) — this is how the
    query was built, not what the feature was designed to do.

AFFECTED ENDPOINT:
    GET /search  —  query string parameter `q`

INPUT:
    ' OR '1'='1        (query string, parameter `q`)

ORIGINAL REQUEST:
    GET /search?q=Monitor HTTP/1.1
    Host: cybershop.training

MODIFIED REQUEST:
    GET /search?q=' OR '1'='1 HTTP/1.1
    Host: cybershop.training

OBSERVED RESPONSE:
    Baseline: 200 OK, Content-Length 85, one matching product.
    Modified: 200 OK, Content-Length 275, all four catalogue products,
    with the reported query reading:
        SELECT * FROM products WHERE name = '' OR '1'='1'
    A single apostrophe additionally produced 500 Internal Server Error
    with the body "Database error: Unexpected quote in training query."

EVIDENCE:
    No product is named "' OR '1'='1", so a correctly parameterised
    query must return zero rows — which is exactly what /secure-search
    returns for the identical input, reporting its query as
    "SELECT * FROM products WHERE name = ?". /search instead returned
    every row. A change in result semantics of that kind cannot be
    produced by a change of value alone; it requires a change of query
    structure. The 500 on a lone apostrophe corroborates that the input
    reaches the query as syntax rather than as data.

SECURITY IMPACT:
    An attacker controls part of a database query. On this training
    application that demonstrably returns catalogue rows the query was
    not meant to select. On a comparable production application the same
    flaw class permits reading data outside the intended result set,
    modifying or deleting data if the database account permits it, and —
    where the same pattern is used on a login query — bypassing
    authentication entirely.

SEVERITY REASONING:
    High. Unauthenticated (no session was required for the requests
    above), reachable over a single GET request with no preconditions,
    and affecting the boundary between the application and its data
    store. Rated on the flaw class and its reachability, not on the
    sensitivity of this particular training catalogue, which is
    fictional.

RECOMMENDED FIX:
    Build the query with a parameterised statement so the query text is
    fixed and `q` is bound as a value — the pattern /secure-search
    already uses. Additionally: run the application's database account
    with least privilege, and return a generic error page instead of the
    database's own message.

VALIDATION STRATEGY:
    Re-send both requests. The baseline must still return one matching
    product. The modified request must return zero matches, and the lone
    apostrophe must return a normal response rather than 500. Add a
    regression test asserting that a search term containing quoting
    syntax returns zero results rather than the full catalogue.

CONFIDENCE:
    High. Reproduced across three inputs, corroborated by the query
    representation, and controlled against a parameterised endpoint on
    the same application given identical input.

NOT TESTED:
    Whether data outside the products table is reachable; whether write
    operations are possible; whether other endpoints share the pattern.
    /secure-search and /secure-login were tested with the same inputs
    and were not affected.
```

### Step 4 — your turn

Write the same report for **Exercise 3**. It is deliberately harder, because your conclusion there was *"the control is working"* — and a finding that says so is still a finding worth writing, with evidence, scope and limits. Note the fields that change shape: severity becomes "informational", impact becomes "none observed", and the NOT TESTED section carries most of the weight.

---

## 10. Observation, Interpretation, Conclusion — Applied Twice

**Case 1 — a `500`.**

**OBSERVATION:** `GET /search?q='` returned `500 Internal Server Error` with body `Database error: Unexpected quote in training query.`
**INTERPRETATION:** the input reached a component that parses quoting, and that component objected. This is consistent with concatenation into a query — and also with several other explanations.
**CONCLUSION:** *none yet.* This warrants further testing. It does not establish injection.

Exercise 2's step 4 is what turned that into a conclusion, and it is worth noticing that the additional evidence was a *`200`*, not an error. The successful, quiet response was the strong evidence; the dramatic error was the weak one.

**Case 2 — a `403`.**

**OBSERVATION:** `GET /admin` returned `403` under the `student` session, and `200` under the `admin` session. `GET /profile` returned `200` under the `student` session.
**INTERPRETATION:** the refusal is about permission rather than about a broken session, since the same session succeeded elsewhere. The decision varies with account identity while the URL is held constant.
**CONCLUSION:** authorization on this route appears to be enforced server-side. Scope: this route, these three request shapes, this session mechanism. Not a general statement about the application.

## 11. Common Mistakes

1. **Testing without a baseline.** "The response was 275 bytes" means nothing until you know it was 85 before.
2. **Changing two things at once.** If you change the cookie and the parameter, the result tells you about neither.
3. **Reading only the status code.** A `200` with an empty body is not success; a `302` can be an access control decision.
4. **Reporting the payload instead of the failure.** The payload is your method; the finding is the false assumption.
5. **Trusting a `200 OK` that something happened.** For anything that changes state, read the state back — that is why Core Concepts §24 lists `/uploads` after the upload.
6. **Concluding from a single request.** One `403` does not establish a control; one `500` does not establish injection.
7. **Padding a report with scanner output.** Every finding needs impact reasoning specific to the application.
8. **Skipping ORIENT.** You cannot see abnormal in an application whose normal you never looked at.
9. **Claiming more than you tested.** "Not tested" is a professional statement, not an admission of weakness.

## 12. Practising on This Platform

Everything below is real and was verified before being named here.

**Terminal missions** — all reachable directly, none gated behind another:

| Mission | What it drills | OWASP category |
|---|---|---|
| **Authentication & Sessions** | login, `Set-Cookie` vs `Cookie`, protected routes, `401`/`403`/`302`, logout, invalidation, expiry | A01, A07 |
| **SQL Injection Fundamentals** | the schema, the query visualiser, error/boolean/union behaviour, parameterisation | A03 |
| **Cross-Site Scripting Fundamentals** | reflected, stored and DOM contexts; output encoding as the fix | A03 |
| **Cross-Site Request Forgery Fundamentals** | the vulnerable and protected transfer endpoints, tokens, `Origin`, `SameSite` | A04 |
| **File Upload Security Fundamentals** | the ten-step pipeline, extension vs MIME vs signature, storage and serving | A08 |

The first two are linked directly from this module — **SQL Injection Fundamentals** from this lesson, **Authentication & Sessions** from Core Concepts. The other three are reached from `/interactive-labs`.

**Interactive labs.** The `web-security` lab category contains ten labs covering almost exactly this module's categories: HTTP Requests & Responses, Cookie Security Flags, Session Fixation, Authentication Bypass, IDOR — Insecure Direct Object Reference, SQL Injection — Login Bypass, Cross-Site Scripting — Reflected, Cross-Site Request Forgery, File Upload Validation, and Security Headers Audit.

They unlock **in that order**, each requiring the previous one — which is worth knowing, because the ones most relevant here (IDOR, SQL Injection, XSS, CSRF, File Upload, Security Headers) sit fifth through tenth in the chain. The entry point is **HTTP Requests & Responses**, linked from this lesson; if you completed it during the Burp Suite module you already have it, and Cookie Security Flags is next. Work down the chain in order and every category in this module has a lab waiting at the end of it.

That first lab is worth revisiting even if you have done it, for one specific reason: its second objective asks you to examine response headers for information leakage — which is Exercise 4's material, read through a different application's headers. Same skill, different evidence.

**A note on the other side.** A09 is the one category you cannot investigate from the attacker's seat. The **SOC: Brute Force Investigation** lab (`soc-brute-force`, in the SOC category, with no prerequisite) puts you on the defending side of exactly the failed-login events Core Concepts §25 says should be recorded and alerted on.

## 13. What This Module Built, and Where It Goes

Five modules now sit on top of each other, and it is worth seeing them as one chain rather than five topics:

- **Web Fundamentals** — what an HTTP request and response actually are
- **Nmap** — what exists on a network, and what services answer
- **Wireshark** — what is actually happening, read as evidence
- **Burp Suite** — what happens when I send *this* request instead
- **OWASP Top 10** — which questions are worth asking, and what the answers mean

The reasoning habit is the transferable part. Baseline first. One variable at a time. Read the whole response. Separate observation from interpretation from conclusion. Say what you did not test. That habit is what the next modules assume you have.

**Active Directory Basics** and the two privilege-escalation modules move the same reasoning off the web and onto systems and identity, where "authenticated but not authorized" becomes a question about accounts, groups and rights rather than cookies and routes. The Red Team track's **Web Pentesting** builds full assessment methodology on exactly the loop you just ran, against targets with more than one thing wrong at a time.

And the professional habit that outlasts all of it: **a vulnerability name is a label, evidence is a claim, and impact is what makes anyone act.** A report with all three is useful. A report with only the first is noise.
