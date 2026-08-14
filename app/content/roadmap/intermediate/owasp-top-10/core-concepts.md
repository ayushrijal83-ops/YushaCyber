# The Ten Categories, Read as Security Failures

## 1. What You Will Learn

This lesson walks the **OWASP Top 10 – 2021** edition, category by category. For each one you should be able to say:

- **what control failed** — the promise the application could not keep
- **what evidence would reveal it** — what you could actually point at
- **what the impact is** — what it lets someone do, concretely
- **how it is fixed** — the change that removes the false assumption
- **what people get wrong about it** — because most of these have one specific misconception attached

Everything runnable in this lesson happens in YushaCyber's authorized simulated training site (`cybershop.training`). Every request and response block below was captured by actually running the platform's simulator, in the order shown, as one continuous session. Where this platform cannot demonstrate a category, the lesson says so plainly rather than inventing an example — there are three such places, and all three are labelled.

## 2. Reading the Ten as One Idea

Before the categories, the sentence that holds them together:

> An application makes promises to itself, and each promise is kept by a control. A vulnerability is a control that did not keep its promise.

That is why the categories overlap, why they are named after *failures* rather than *attacks*, and why "which category is this?" is sometimes a genuinely debatable question with a defensible answer either way. You are classifying a failure, not looking up a payload.

The 2021 list, in order:

| | Category | Control that failed |
|---|---|---|
| A01:2021 | Broken Access Control | Authorization |
| A02:2021 | Cryptographic Failures | Protection of sensitive data |
| A03:2021 | Injection | Safe handling of input in an interpreter |
| A04:2021 | Insecure Design | The design itself |
| A05:2021 | Security Misconfiguration | Configuration |
| A06:2021 | Vulnerable and Outdated Components | Dependency management |
| A07:2021 | Identification and Authentication Failures | Authentication |
| A08:2021 | Software and Data Integrity Failures | Integrity verification |
| A09:2021 | Security Logging and Monitoring Failures | Detection and response |
| A10:2021 | Server-Side Request Forgery (SSRF) | Control over outbound requests |

## 3. The Training Environment

Three fixed, fictional training accounts exist on the simulated site, and you are being *handed* all three deliberately. That is what makes the comparison in §5 an authorized test rather than a credential attack: you are not discovering someone's password, you are being given two accounts of different privilege so you can compare what the server does for each.

| Account | Password | Role |
|---|---|---|
| `student` | `training123` | ordinary user |
| `analyst` | `analyst123` | ordinary user |
| `admin` | `admin123` | administrator |

There is also a fixed API bearer token, `training-token-001`, used by the JSON API routes. None of these values exists anywhere outside this simulator.

---

# A01:2021 – Broken Access Control

## 4. Authentication Is Not Authorization

This is the first category in the 2021 list because it is, by a wide margin, the most commonly found. It is also the one beginners most often mis-diagnose, and the confusion always traces back to the same two words.

**Authentication** answers *"who are you?"* It happens once, at login, and produces something the server can recognise on later requests — usually a session identifier in a cookie, or a token in a header.

**Authorization** answers *"is this identity allowed to do this specific thing to this specific resource?"* It has to happen on **every** request that touches a protected resource, because every request is a fresh decision.

An application can get the first entirely right and the second entirely wrong. That combination is A01.

The training site distinguishes the two, and shows you the distinction in the status codes. Start with no session at all:

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

`401` and the body both say the same thing: the server does not know who you are. This is an **authentication** failure, in the ordinary sense that authentication has not happened.

Now log in as an ordinary user:

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

Authentication has now succeeded — the `Set-Cookie` proves the server established a session. Request the same URL again, changing nothing but the fact that a session now exists:

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

The server is spelling the distinction out for you. It knows exactly who you are — and it is refusing anyway, because *who you are* is not *what may access this*. `401` said "I don't know you." `403` says "I know you, and no."

Finally, the same URL as the administrator:

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

**One URL. One variable changed — which session cookie was attached. Three different outcomes.** That is a well-behaved authorization control: the decision is made on the server, from the identity the server established, on every request.

**OBSERVATION:** `GET /admin` returned `401` with no cookie, `403` with the `student` session cookie, and `200` with the `admin` session cookie.
**INTERPRETATION:** the server distinguishes unauthenticated from unauthorized, and grants access based on the account the session belongs to. The decision appears to be made server-side, since the only thing that changed between requests was the cookie.
**CONCLUSION:** on this route, authorization is enforced server-side and was not bypassed by the changes tested. This says nothing about other routes, other methods, or bypasses not attempted.

## 5. Not Every Refusal Looks the Same

A protected route does not have to answer with an error status. Compare `/account` while logged in as `student`, and then after logging out:

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

No `401` anywhere — a `302` to the login page. This is the browser-friendly pattern, and it is just as much an access control decision as a `403` is. If you were grepping your test results for "401 or 403" you would have missed it entirely.

**The lesson: the access control decision is what matters, not the status code that expresses it.** Different routes on the same application legitimately express refusal differently, and an application that returns `200` with an empty body has also refused you.

## 6. Vertical and Horizontal

Two shapes of broken access control, worth naming because they need different tests.

**Vertical** — a lower-privileged user reaches functionality intended for a higher-privileged one. Ordinary user reaches `/admin`. Test: request privileged functionality as an unprivileged account, as above.

**Horizontal** — a user reaches *another user's* resource at the same privilege level. This is the family that includes **IDOR** (Insecure Direct Object Reference): the client supplies an identifier, and the server looks the record up without checking who owns it.

```
User A requests  /orders/1041   →  200, A's order          (correct)
User A requests  /orders/1042   →  200, B's order          (broken access control)
User A requests  /orders/1042   →  403 or 404              (correct)
```

The reasoning, in seven steps:

1. Authenticate as training user A.
2. Perform the normal action and capture the request.
3. Find the identifier — path segment, query parameter, body field, or header.
4. Establish that A can reach A's own resource. **This is your baseline.**
5. Change **only** the identifier to one belonging to training user B.
6. Send, and read the whole response — status, body, and length.
7. Interpret against this table:

| Outcome | What it means |
|---|---|
| `403` / `404`, no data | Authorization appears to be enforced |
| `200` with **B's** data | Strong evidence of broken access control |
| `200` with **A's own** data | The server ignored your changed identifier — a very different finding, and not access control at all |
| `200` with an empty body | Ambiguous. Compare `Content-Length` against the baseline before concluding anything |
| `500` | The server errored. That is a bug, not proof of an authorization failure |

**This platform cannot run that test, and the honest thing is to say so.** The simulated training site has no per-user resource endpoint — no `/orders/<id>` where record 1041 belongs to one account and 1042 to another. Every identifier-bearing route it has (`/products?id=42`, `/upload/<id>`) either serves public data or is guarded only by session, not by ownership. Rather than invent an endpoint and quote made-up responses, the reasoning is taught above in full and the runnable version is left to two real places: the platform's **IDOR — Insecure Direct Object Reference** lab (`websec-idor`, real and in the web-security lab category — see Hands-on Practice §12 for how the lab chain unlocks), and any deliberately vulnerable application you install yourself.

## 7. Access Control Evidence

Evidence that can bear on an access control question:

- **HTTP status** — necessary, never sufficient
- **Response body** — whose data is in it? Is it real data or an error page with a 200 status?
- **`Content-Length`** — an identical length across two accounts is itself informative
- **Redirect behaviour** — where does `Location` point, and does following it help?
- **Server-side state** — did the action actually happen? For anything that changes state, *read it back*
- **Differences between accounts** — the whole basis of a horizontal test

And the discipline that goes with it:

> **Never conclude a vulnerability from a single status code.** `403` is not proof of a working control; `200` is not proof of a broken one. Read the whole response, and where the request was supposed to *do* something, verify by reading the state back.

**Impact when A01 is real:** unauthorized viewing, modification or deletion of other users' data; access to administrative functionality; performing actions as another user. This category tends to be high-severity precisely because it is direct — there is no chain of exploitation, the data simply comes back.

**Mitigation:**

- **Deny by default.** Every route requires an explicit grant, rather than being open unless someone remembered to protect it.
- **Enforce on the server, per request, per resource** — never in the interface alone.
- Check **ownership**, not just authentication: "does this record belong to this identity?"
- Prefer identifiers a client cannot guess or enumerate where the data is sensitive — but treat that as defence in depth, **not** as the access control itself.
- Test authorization as part of the normal test suite, not only in security review.

**Misconception:** *"The button isn't shown to this user, so this user can't do it."*
**Correct:** the interface lives on the user's side of the trust boundary. The server must enforce the restriction regardless of what the page renders.

---

# A02:2021 – Cryptographic Failures

## 8. Protecting Data, and the Ways That Goes Wrong

The 2021 edition renamed this category from "Sensitive Data Exposure" for a good reason: exposure is the *symptom*, and the category is about the *cause* — sensitive data that is not protected, or is protected by something that does not work.

Four places it goes wrong:

**In transit.** Data sent unencrypted, or over TLS that is misconfigured or not enforced. You have the tooling for this already: the Wireshark module showed you exactly what an observer on the network can and cannot read, and what metadata survives even when the payload does not.

**At rest.** Passwords stored in a recoverable form; sensitive fields stored in plaintext; backups protected less carefully than the live system.

**Password storage specifically.** From Cryptography Basics: passwords should be **hashed**, with a **per-user salt**, using a **slow, purpose-built password hashing function** designed to resist brute force. Encryption is the wrong tool — encryption is reversible by design, and you never need to recover a password, only to check one. Fast general-purpose hashes are the wrong tool for the same reason they are the right tool elsewhere: speed is the attacker's friend here.

**Key management.** A perfect algorithm with a key committed to the repository protects nothing. The Git & GitHub module's rule applies directly: a secret that has been pushed is compromised, and the fix is to rotate it at its source.

Wrong choices worth recognising:

| Choice | Why it fails |
|---|---|
| Base64 "encryption" | Base64 is an **encoding**. It is reversible by anyone, requires no key, and provides no confidentiality at all |
| A fast hash for passwords | Designed to be fast; that is exactly what makes offline guessing cheap |
| Unsalted password hashes | Identical passwords produce identical hashes, and precomputed tables apply |
| Hard-coded or committed keys | The key is now as public as the code |
| Rolling your own cipher | Cryptography fails silently — it looks like it works right up until it does not |

## 9. What This Platform Can and Cannot Show

**This module has no runnable cryptographic evidence, and inventing some would be exactly the fabrication the whole platform tells you to distrust.** The simulator has no TLS layer to misconfigure, no password store to inspect, and no key management to get wrong. What it does have is one real, observable *data-handling* decision, which is genuinely adjacent and worth reading properly.

Compare the response headers for a public product page and for a page containing account data. First the public page:

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

Now the same command after requesting `/profile` with a session:

```
$ headers
Request headers:
  Host: cybershop.training
  User-Agent: YushaCyber-Trainer/1.0
  Accept: */*

Response headers:
  Content-Type: text/html
  Content-Length: 16
  Server: CyberShop-Sim/1.0
  Cache-Control: no-store
  Content-Security-Policy: default-src 'self'; script-src 'self'
```

`Cache-Control: max-age=60` on the public catalogue page; `Cache-Control: no-store` on the page containing a user's own data. That is a deliberate decision about *where sensitive data is allowed to come to rest* — a caching proxy, a browser cache on a shared computer, a CDN. It is not cryptography, but it belongs to the same question this category asks: **who else can end up holding this data?**

**Impact when A02 is real:** disclosure of credentials, personal data, payment data or session material; account takeover; regulatory consequences; loss of trust in every other control that depended on the protected data.

**Mitigation:** classify what is actually sensitive; encrypt in transit and enforce it (HSTS, no plaintext fallbacks); encrypt at rest where the threat model calls for it; use a purpose-built salted password hashing function for passwords; manage keys outside the codebase with rotation; and do not store what you do not need.

**Misconception:** *"We use HTTPS, so our data is protected."*
**Correct:** TLS protects data **in transit**, between two endpoints. It does nothing about how the data is stored, who is authorized to read it once it arrives, whether it is logged, or whether it is cached. An application can be fully HTTPS and still store every password in plaintext.

---

# A03:2021 – Injection

## 10. The Model

One mechanism produces this whole family, and it is worth stating as a formula:

```
untrusted data   +   an interpreter that reads structure from a string
                          ↓
        the data can become part of the structure
```

An **interpreter** is anything that reads a string and decides what it *means*: a SQL engine, a shell, an HTML parser, a template engine, an LDAP directory, an XML parser, an expression evaluator. The vulnerability appears when the application builds the string for that interpreter by **concatenating** untrusted data into it, because concatenation cannot distinguish "this part is my instruction" from "this part is their data."

That is why the same reasoning covers SQL injection, OS command injection, template injection, LDAP injection and cross-site scripting, which the 2021 edition folds into this category — in XSS the interpreter is the browser's HTML parser, and the injected structure is markup.

## 11. SQL Injection, Watched Rather Than Guessed

The training simulator exposes something rare and extremely useful: a **query visualiser** that shows you the query the application would have built from your input. There is no SQL engine here — nothing you type is ever executed — but the string it shows you is constructed by the same concatenation the vulnerable endpoint models, so you can watch the structure change.

Start with the schema, so you know what the application is querying:

```
$ schema products
products:
  id (INTEGER)
  name (TEXT)
  price (INTEGER)
  category (TEXT)
```

Now an entirely ordinary search — **your baseline**:

```
$ open https://cybershop.training/search?q=Laptop
━━━━━━━━ REQUEST ━━━━━━━━
GET /search?q=Laptop HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 83
Server: CyberShop-Sim/1.0
Cache-Control: no-store
X-Sim-Query-Kind: normal
X-Sim-Query: SELECT * FROM products WHERE name = 'Laptop'
X-Sim-XSS-Kind: none
X-Sim-XSS-Context: html_text
Content-Security-Policy: default-src 'self'; script-src 'self'

Search results for 'Laptop': 1 match(es) in the training catalog.
  - Laptop ($999)
```

```
$ query
Simulated query representation — not a live SQL console.

User Input:         Laptop
Application Query:  SELECT * FROM products WHERE name = 'Laptop'
Database:           cybershop.training (simulated, read-only)
Response:           200 OK
```

Nothing is wrong yet. The input sat inside the quotes, as data. That is what a search is supposed to do.

**Change one character.** Send a single apostrophe:

```
$ open "https://cybershop.training/search?q='"
━━━━━━━━ REQUEST ━━━━━━━━
GET /search?q=' HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

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

Look at the query string: `name = '''`. Three apostrophes. The one you typed did not stay inside the quotes — it **became** a quote in the query. The application's string-building had no way to keep it as data.

That `500` is the classic first signal, and it is worth being precise about what it does and does not mean. It shows the input reached something that cares about quoting. It does **not** on its own prove injection — a `500` could be any error. Which is why the next request matters more.

**Change the logic rather than breaking it:**

```
$ open "https://cybershop.training/search?q=' OR '1'='1"
━━━━━━━━ REQUEST ━━━━━━━━
GET /search?q=' OR '1'='1 HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

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

**This is the evidence.** Not the payload — the *behaviour*. A search for a product named `' OR '1'='1` should match nothing; there is no such product. Instead it returned the entire catalogue, four rows, because the condition the query evaluates is no longer "name equals this text." The input added a new clause, and the query's **meaning** changed.

**OBSERVATION:** a search term matching no product returned every product in the catalogue. The visualised query shows the term's quotes closing the intended string literal and adding an `OR` clause.
**INTERPRETATION:** the endpoint appears to build its query by concatenating the parameter into the query string, so the parameter can alter the query's structure rather than only its value.
**CONCLUSION:** this endpoint is affected by SQL injection. The evidence is a change in result semantics that only a structural change to the query explains, corroborated by the query representation — not the mere presence of SQL-looking characters in the input.

## 12. The Defence, Proven Rather Than Asserted

The site exposes a second endpoint that does the same job with **parameterised queries**. Send the identical payload:

```
$ open "https://cybershop.training/secure-search?q=' OR '1'='1"
━━━━━━━━ REQUEST ━━━━━━━━
GET /secure-search?q=' OR '1'='1 HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

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

Look at the query: `WHERE name = ?`. It is the **same string every time**, whatever you send. The input never appears in it.

That is the whole idea of a **parameterised query** (also called a prepared statement). The application sends the query structure and the data to the database *separately*. The database compiles the structure first, then binds the data into the placeholder. There is no point at which the data could be read as structure, because by the time it arrives the structure is already fixed.

Notice what this is **not**. It is not filtering. Nothing removed the apostrophes — the response shows the search term echoed back, HTML-encoded (`&#x27;` is an apostrophe) and searched for as literal text. Zero matches, because no product is named that. The input was accepted, kept as data, and used safely.

> **Parameterisation does not clean your input. It makes your input structurally incapable of being anything but data.** That is why it is a stronger guarantee than any amount of filtering.

## 13. Injection in the Login, and the Same Fix

The pattern is not specific to search. Here is a login endpoint built the unsafe way, given a username containing a SQL comment sequence:

```
$ open -X POST -d "username=admin'--&password=anything" https://cybershop.training/training-login
━━━━━━━━ REQUEST ━━━━━━━━
POST /training-login HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 35
Cookie: session_id=student-session

username=admin'--&password=anything

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 200
Server: CyberShop-Sim/1.0
Cache-Control: no-store
X-Sim-Query-Kind: auth_bypass
X-Sim-Query: SELECT * FROM users WHERE username = 'admin'--' AND password = '***'
Content-Security-Policy: default-src 'self'; script-src 'self'

{"status": "success", "authenticated_as": "admin", "simulated": true, "note": "Simulated authentication bypass: a comment sequence in the username removed the password check from the query entirely."}
```

```
$ query
Simulated query representation — not a live SQL console.

User Input:         username=admin'--&password=anything
Application Query:  SELECT * FROM users WHERE username = 'admin'--' AND password = '***'
Database:           cybershop.training (simulated, read-only)
Response:           200 OK

Unsafe string concatenation let the input change the query's structure.
```

Read the query. Everything after `--` is a comment in SQL, so the `AND password = ...` clause is no longer part of the query at all. The application still *believes* it is checking a password. The database was never asked.

This is worth dwelling on, because it shows why injection is often more serious than "an attacker can read data": here the injected structure **deleted a security control**. The password check did not fail — it ceased to exist.

The same input against the parameterised login:

```
$ open -X POST -d "username=admin'--&password=anything" https://cybershop.training/secure-login
━━━━━━━━ REQUEST ━━━━━━━━
POST /secure-login HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 35
Cookie: session_id=student-session

username=admin'--&password=anything

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 401 Unauthorized
Content-Type: application/json
Content-Length: 62
Server: CyberShop-Sim/1.0
X-Sim-Query-Kind: parameterized
X-Sim-Query: SELECT * FROM users WHERE username = ? AND password = ?
Content-Security-Policy: default-src 'self'; script-src 'self'

{"status": "error", "message": "Invalid training credentials"}
```

```
$ query
Simulated query representation — not a live SQL console.

User Input:         username=admin'--&password=anything
Application Query:  SELECT * FROM users WHERE username = ? AND password = ?
Database:           cybershop.training (simulated, read-only)
Response:           401 Unauthorized

Parameterized query: the input stayed data — the query structure never changed.
```

`401`. The username `admin'--` was looked up as a literal username, no such user exists, and the login failed exactly as a wrong username should. The payload did nothing because there was nothing for it to do.

## 14. Cross-Site Scripting: the Same Idea, a Different Interpreter

XSS lives in this category in the 2021 edition because it is the same mechanism with the browser's HTML parser as the interpreter. Untrusted data is written into an HTML document, and the browser reads part of it as markup instead of as text.

This platform models the effect with fixed training markers and a **simulated** browser event — no JavaScript is ever executed anywhere in YushaCyber. Reflected first:

```
$ open https://cybershop.training/search?q=<TRAINING_XSS>
━━━━━━━━ REQUEST ━━━━━━━━
GET /search?q=<TRAINING_XSS> HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 379
Server: CyberShop-Sim/1.0
Cache-Control: no-store
X-Sim-Query-Kind: normal
X-Sim-Query: SELECT * FROM products WHERE name = '<TRAINING_XSS>'
X-Sim-XSS-Kind: reflected
X-Sim-XSS-Context: html_text
Content-Security-Policy: default-src 'self'; script-src 'self'

Search results for '<TRAINING_XSS>': 0 match(es) in the training catalog.

┌─────────────────────────────────┐
│ SIMULATED BROWSER EVENT          │
├─────────────────────────────────┤
│ XSS marker detected              │
└─────────────────────────────────┘
Source: search?q=
Sink: reflected HTML
Result: simulated execution
Simulation only — no JavaScript executed in YushaCyber.
```

The marker came back into the page body **unchanged**: `<TRAINING_XSS>` still has its angle brackets. In a real browser, angle brackets in an HTML text node are how markup begins.

Now the encoded endpoint:

```
$ open https://cybershop.training/secure-search?q=<TRAINING_XSS>
━━━━━━━━ REQUEST ━━━━━━━━
GET /secure-search?q=<TRAINING_XSS> HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 79
Server: CyberShop-Sim/1.0
Cache-Control: no-store
X-Sim-Query-Kind: parameterized
X-Sim-Query: SELECT * FROM products WHERE name = ?
X-Sim-XSS-Kind: encoded
X-Sim-XSS-Context: html_text
Content-Security-Policy: default-src 'self'; script-src 'self'

Search results for '&lt;TRAINING_XSS&gt;': 0 match(es) in the training catalog.
```

`&lt;TRAINING_XSS&gt;`. Same input, same page, and now the angle brackets are represented as entities. A browser displays that as the literal text `<TRAINING_XSS>` and parses no markup from it. **Nothing was removed** — it was *encoded for the context it was going into*.

Three XSS shapes to recognise: **reflected** (the input comes straight back in the response to the same request), **stored** (the input is saved and delivered to whoever views it later — the danger is delayed and hits other people), and **DOM-based** (the unsafe write happens in client-side JavaScript, so it may never appear in the server's response at all).

**Other injection contexts, named honestly and not runnable here.** OS command injection (untrusted data concatenated into a shell command), server-side template injection (untrusted data placed into a template that is then evaluated), LDAP injection, and NoSQL injection (where a JSON document is built from untrusted values and an operator object arrives where a scalar was expected) all follow the identical model. The simulator implements none of them, so this lesson does not quote output for any of them.

**Impact when A03 is real:** reading, modifying or destroying data the query was never meant to touch; bypassing authentication entirely (§13); command execution on the server, for command injection; for XSS, actions taken in another user's browser under their session.

**Mitigation, in priority order:**

1. **Use the interpreter's safe API.** Parameterised queries and prepared statements for SQL; parameter arrays rather than shell strings for OS commands; a template engine's own escaping for templates.
2. **Encode at output, per context.** HTML text, HTML attribute, URL, JavaScript and JSON each need different encoding. The output context decides, not the input.
3. **Validate as allowlists** where the shape is known — that a value must be one of four options, or a positive integer.
4. **Apply least privilege to the database account.** If the application never deletes rows, its database user should not be able to.
5. Treat filtering and blocklists as **defence in depth only**. Never as the control.

**Misconception:** *"Any SQL-looking input proves SQL injection."*
**Correct:** the evidence is a demonstrated change in application or database *behaviour* that only a structural change explains — the catalogue returning every row for a term matching nothing, the password clause disappearing. An apostrophe in a field proves nothing at all on its own, and a `500` might be any error.

---

# A04:2021 – Insecure Design

## 15. When the Code Is Correct and the System Is Still Wrong

Every category so far describes something that was *built* wrong. This one describes something that was *designed* wrong — a system that behaves exactly as specified, where the specification itself never asked the right question.

The distinction that makes this concrete:

| | Implementation flaw | Design flaw |
|---|---|---|
| Nature | The code does not do what it was meant to | The code does exactly what it was meant to |
| Found by | Code review, testing, static analysis | Threat modelling, abuse-case analysis, asking "what could someone make this do?" |
| Fixed by | Patching the code | Changing the design — often across several components |
| Example | The password comparison has a bug | There is no rate limit, so unlimited guesses are allowed by design |

You cannot patch your way out of a design flaw. If a workflow has no step at which authorization could be checked, no amount of careful coding inserts one.

Recognisable shapes:

- **No authorization model at all** — protection was added route by route as someone remembered, rather than designed once and applied by default
- **Client-side roles** — the design treats a value the client sends (`role=admin` in a request, a claim in an unverified token) as the authority on privilege
- **No rate-limiting strategy** — password guessing, one-time-code guessing, and resource exhaustion are all *permitted by design*
- **Unsafe business workflow** — a refund that can be issued before the return is received; a discount that can be applied repeatedly; a multi-step process where a later step can be reached without completing an earlier one
- **No abuse-case analysis** — the design covered what users should do, and never asked what someone determined could do

## 16. A Design Question You Can Run

The training site has two endpoints that move simulated training funds. They are not "buggy" and "fixed" versions of the same code — they are two different *design decisions*, and the difference is what the design requires as proof.

The site describes the first one itself:

```
$ open https://cybershop.training/csrf-demo
━━━━━━━━ REQUEST ━━━━━━━━
GET /csrf-demo HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 768
Server: CyberShop-Sim/1.0
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'

CSRF Demo — Vulnerable Transfer

POST /transfer moves simulated training funds between accounts. It is protected only by the session cookie: any request carrying a valid session_id cookie is accepted, with no check that the request was actually intended by the logged-in user.

Example vulnerable request:
POST /transfer
recipient=training-user
amount=100

A page on any other origin can auto-submit this same request; the student's browser still attaches their cybershop.training session cookie automatically, because that's how browsers handle cookies for requests to a given site, regardless of which page triggered them.

Compare with the protected version at /secure-transfer, which additionally requires a csrf_token parameter and validates the request's Origin.
```

That paragraph is a design statement. Now the ordinary case, as an authenticated user performing a normal transfer:

```
$ open -X POST -d "amount=100&recipient=training-user" https://cybershop.training/transfer
━━━━━━━━ REQUEST ━━━━━━━━
POST /transfer HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 34
Cookie: session_id=student-session

amount=100&recipient=training-user

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 104
Server: CyberShop-Sim/1.0
Cache-Control: no-store
X-Sim-CSRF-Kind: vulnerable_success
Content-Security-Policy: default-src 'self'; script-src 'self'

{"status": "success", "sender": "student", "recipient": "training-user", "amount": 100, "balance": 4900}
```

Balance `4900`. The transfer happened. Now the same request with one header added, declaring that it came from a different site:

```
$ open -X POST -H "Origin: https://attacker.training" -d "amount=100&recipient=training-user" https://cybershop.training/transfer
━━━━━━━━ REQUEST ━━━━━━━━
POST /transfer HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 34
Origin: https://attacker.training
Cookie: session_id=student-session

amount=100&recipient=training-user

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 104
Server: CyberShop-Sim/1.0
Cache-Control: no-store
X-Sim-CSRF-Kind: attack_simulated
Content-Security-Policy: default-src 'self'; script-src 'self'

{"status": "success", "sender": "student", "recipient": "training-user", "amount": 100, "balance": 4800}
```

Balance `4800`. Accepted again. The endpoint's only requirement is a valid session cookie — and the browser attaches that cookie automatically to any request aimed at this site, no matter which page caused the request. **The design has no way to tell an action the user chose from an action a page on another site caused their browser to make.** That is Cross-Site Request Forgery, and it is a design failure rather than a coding error: nothing in that code is written incorrectly.

The second endpoint asks for more. It hands the logged-in user a token bound to their session:

```
$ open https://cybershop.training/secure-transfer
━━━━━━━━ REQUEST ━━━━━━━━
GET /secure-transfer HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 258
Server: CyberShop-Sim/1.0
Cache-Control: no-store
X-Sim-CSRF-Token: TRAINING_TOKEN_STUDENT_SESSION
X-Sim-CSRF-Kind: token_shown
Content-Security-Policy: default-src 'self'; script-src 'self'

Secure Transfer — logged in as student

csrf_token=TRAINING_TOKEN_STUDENT_SESSION

Submit this token together with 'recipient' and 'amount' in a POST to /secure-transfer. Requests missing the token, or carrying the wrong one, are rejected with 403 Forbidden.
```

The same forged-origin request, this time carrying the token:

```
$ open -X POST -H "Origin: https://attacker.training" -d "amount=100&recipient=training-user&csrf_token=TRAINING_TOKEN_STUDENT_SESSION" https://cybershop.training/secure-transfer
━━━━━━━━ REQUEST ━━━━━━━━
POST /secure-transfer HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 76
Origin: https://attacker.training
Cookie: session_id=student-session

amount=100&recipient=training-user&csrf_token=TRAINING_TOKEN_STUDENT_SESSION

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 403 Forbidden
Content-Type: application/json
Content-Length: 76
Server: CyberShop-Sim/1.0
X-Sim-CSRF-Kind: origin_rejected
Content-Security-Policy: default-src 'self'; script-src 'self'

{"status": "error", "message": "CSRF validation failed: unexpected Origin."}
```

And a same-origin request that simply forgets the token:

```
$ open -X POST -d "amount=100&recipient=training-user" https://cybershop.training/secure-transfer
━━━━━━━━ REQUEST ━━━━━━━━
POST /secure-transfer HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 34
Cookie: session_id=student-session

amount=100&recipient=training-user

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 403 Forbidden
Content-Type: application/json
Content-Length: 77
Server: CyberShop-Sim/1.0
X-Sim-CSRF-Kind: missing_token
Content-Security-Policy: default-src 'self'; script-src 'self'

{"status": "error", "message": "CSRF validation failed: missing csrf_token."}
```

With both the right origin and the right token, it works:

```
$ open -X POST -d "amount=100&recipient=training-user&csrf_token=TRAINING_TOKEN_STUDENT_SESSION" https://cybershop.training/secure-transfer
━━━━━━━━ REQUEST ━━━━━━━━
POST /secure-transfer HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 76
Cookie: session_id=student-session

amount=100&recipient=training-user&csrf_token=TRAINING_TOKEN_STUDENT_SESSION

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 104
Server: CyberShop-Sim/1.0
Cache-Control: no-store
X-Sim-CSRF-Kind: token_valid
Content-Security-Policy: default-src 'self'; script-src 'self'

{"status": "success", "sender": "student", "recipient": "training-user", "amount": 100, "balance": 4700}
```

**The design difference in one sentence:** the first endpoint asks *"do you have a session?"*; the second asks *"do you have a session, **and** can you demonstrate that this request came from our own page?"* Only the second question distinguishes an intended action from a forged one, and no amount of careful coding adds that question to the first design.

The modern browser-side defence is the `SameSite` cookie attribute, which changes when the browser attaches a cookie to a cross-site request at all. It is a genuinely strong mitigation and it is not a replacement for the token — you do not control which browser your users run, and the token is the part the server can actually enforce.

**Impact when A04 is real:** whatever the abused workflow can do — unauthorised state changes, financial loss, privilege escalation, account takeover. Impact follows the business function, not the code.

**Mitigation:** threat model during design, not after; write **abuse cases** alongside use cases ("what does someone who wants to cheat do here?"); build the authorization model once and apply it by default; design limits (rate limits, transaction limits, approval steps) in as requirements; require proof of intent for state-changing actions.

**Misconception:** *"Insecure design is just a bug we haven't found yet."*
**Correct:** in a design flaw, every line of code may be correct. The missing control was never specified, so there is nothing to fix at the line level.

---

# A05:2021 – Security Misconfiguration

## 17. Correct Software, Wrong Settings

The software works. It was deployed, or left, in a state that gives away more than it should — or that never enabled a protection that was available for free.

What to look for:

| Misconfiguration | Why it matters |
|---|---|
| Debug mode enabled in production | Stack traces, framework versions, file paths, sometimes configuration and secrets |
| Default credentials | Unchanged admin accounts on the app, the database, the appliance |
| Unnecessary features enabled | Sample apps, unused endpoints, directory listing, extra HTTP methods — all attack surface with no benefit |
| Verbose error messages | Internal detail leaked to whoever caused the error |
| Missing or wrong security headers | Protections the browser would have enforced, simply not requested |
| Overly permissive permissions | Files, buckets, database accounts with far more access than the function needs |
| Exposed administrative interfaces | Management consoles reachable from networks that never needed them |

## 18. Real Evidence, Read Two Ways

Here is a set of response headers from the training site, captured for real:

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

Read that twice — once for what is there, once for what is not.

**Present:** `Content-Security-Policy: default-src 'self'; script-src 'self'`. A real, restrictive policy, applied to every response on this site. That is a control doing its job, and it belongs in your notes as much as anything missing does.

**Present and worth noting:** `Server: CyberShop-Sim/1.0`. The response volunteers the software name and version. That is **information disclosure** — it does not compromise anything by itself, and it is the first thing an attacker writes down. (This particular version string is the simulator's own fictional one; on a real server it would name a real product and a real version, which is why §20 picks it up again.)

**Absent:** several headers a hardened site would usually send —

| Header | What it would do |
|---|---|
| `Strict-Transport-Security` | Instruct the browser to use HTTPS for this site, always |
| `X-Content-Type-Options: nosniff` | Stop the browser guessing a content type different from the declared one |
| `X-Frame-Options` / CSP `frame-ancestors` | Prevent the page being embedded in another site's frame |
| `Referrer-Policy` | Limit what URL information leaks to other sites |

Absence is evidence too — and this is where the discipline matters. "These headers are missing" is an **observation**. Whether it is a *finding*, and at what severity, depends on what the application does and what the missing header would have protected. A missing `X-Frame-Options` on a page with no state-changing actions is close to irrelevant; on a page with a one-click transfer button it is not.

## 19. Verbose Errors, and the Contrast

You already saw a real verbose error in §11:

```
Database error: Unexpected quote in training query.
```

That message tells the person who caused it that their input reached a database layer and that the layer objected to a quote. It is an internal detail, offered to an unauthenticated stranger.

Compare with how the same site handles a route that simply does not exist:

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

`The requested resource was not found.` — accurate, useful, and completely uninformative about the application's internals. That is what a production error should look like. The detail belongs in the server's own logs, where the operators can read it and strangers cannot.

**Impact when A05 is real:** ranges from a small intelligence gain (version disclosure) to complete compromise (a default administrator password on an exposed console). Configuration issues are also frequently the *easiest* to find, which is why they show up constantly in real assessments.

**Mitigation:** a repeatable, reviewed hardening process rather than per-server improvisation; identical configuration across environments so production is not a special case; debug and verbose errors off in production; change every default credential; remove unused features and sample content; set security headers deliberately; and verify configuration automatically so drift is caught.

**Misconception:** *"That's just a settings issue, not a real vulnerability."*
**Correct:** an exposed admin console with a default password does not require any clever exploitation to be catastrophic. Configuration is one of the controls; when it fails, the promise is broken exactly as thoroughly as when code fails.

---

# A06:2021 – Vulnerable and Outdated Components

## 20. Your Dependencies Are Your Attack Surface

Modern applications are mostly other people's code — frameworks, libraries, runtimes, containers, operating system packages. Every one is part of your attack surface, and a vulnerability in any of them is a vulnerability in your application, whatever your own code does.

The chain:

```
APPLICATION
    ↓  depends on
COMPONENT (library, framework, runtime, base image)
    ↓  has
KNOWN VULNERABILITY (published, with an identifier)
    ↓  reachable from your application's inputs?
POTENTIAL IMPACT
```

That third arrow is where careful reasoning belongs, and it is where most people skip a step.

The signal you can often see from outside is version disclosure — like the training site's own header:

```
Server: CyberShop-Sim/1.0
```

Take that as the **beginning of an investigation**, not the end of one. It tells you what to look up. It does not tell you whether anything is wrong.

Now the correction that this category exists to teach:

> **An old version is not automatically vulnerable.**

Several things all have to be true before a published vulnerability in a component means your application is affected:

1. **The version really is affected.** Version strings are frequently wrong — many distributions backport security fixes without changing the version number, so a "vulnerable-looking" version may already be patched.
2. **The vulnerable code path is actually reachable** in how you use the component. A vulnerability in a feature you never enable may not apply.
3. **The preconditions hold** — many advisories require a specific configuration, a specific platform, or an authenticated position to matter at all.
4. **Nothing else already blocks it.** Another control may make it unexploitable in your deployment.

Conversely, and just as importantly: **a current version is not automatically safe.** Vulnerabilities are discovered in current versions constantly; that is what "zero-day" means.

So the honest way to write this up is: *"the server discloses version X; version X falls within the affected range of advisory Y; exploitability in this deployment was not tested."* That is a truthful finding. *"The server runs a vulnerable version"* is a claim you have not established.

**What good component management actually is:**

- **Inventory** — know what you depend on, including transitive dependencies you never chose directly. A software bill of materials (SBOM) is this, written down.
- **Monitoring** — subscribe to advisories for what you actually use; scan dependencies as part of the build.
- **Patching** — a real process with a real cadence, not an annual panic.
- **Trusted sources** — official registries, verified publishers, pinned versions, checked integrity. (Where this fails, you are in A08 territory — see below.)
- **Removal** — the safest dependency is one you deleted.

**Impact when A06 is real:** whatever the component's vulnerability permits — often remote code execution, since serialization, parsing and templating libraries are common culprits, and often without any flaw in your own code at all.

**Misconception:** *"The version is old, therefore it's vulnerable."*
**Correct:** old means "worth investigating." Confirm the version is genuinely affected, that the vulnerable path is reachable in your usage, and that the advisory's preconditions hold — otherwise you are reporting a version number, not a vulnerability.

---

# A07:2021 – Identification and Authentication Failures

## 21. Proving Identity, and Keeping It Proven

A01 was about *permission*. This category is about *identity*: establishing it correctly, and maintaining it safely afterwards. Renamed from 2017's "Broken Authentication", partly to make clear that it covers identification and session management as well as the login form.

Two halves, and the second is where most of the interesting failures live.

**Establishing identity** — the login itself. Weak or unenforced password requirements; permitting credentials known to be breached; no protection against automated guessing; no multi-factor option for accounts that need it; account recovery flows weaker than the login they bypass (a recovery path is a second front door, and it is often the badly-built one).

**Maintaining identity** — sessions. A session identifier that is predictable; one that is not regenerated at login (which permits session fixation); one that never expires; one that survives logout; cookies without `Secure`, `HttpOnly` and `SameSite`; a token whose signature is never verified.

Here is a failed login on the training site:

```
$ open -X POST -d "username=student&password=wrong-password" https://cybershop.training/auth/login
━━━━━━━━ REQUEST ━━━━━━━━
POST /auth/login HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 40
Cookie: session_id=student-session

username=student&password=wrong-password

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 401 Unauthorized
Content-Type: application/json
Content-Length: 41
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'

{"error": "Invalid training credentials"}
```

Two things to notice, and both are design decisions rather than accidents.

**No `Set-Cookie`.** A failed login establishes nothing. Compare with the successful login in §4, which issued a session.

**The message says nothing useful about *why*.** `Invalid training credentials` does not reveal whether the username exists. A message like "no such user" versus "wrong password" would let anyone enumerate valid accounts one request at a time — a real and common finding. (There is a genuine tension here with usability, and different applications resolve it differently; the point is that it is a decision with a security consequence, and should be made deliberately.)

## 22. Sessions End in More Than One Way

Two different endings, and the difference is worth understanding properly because they fail differently.

**Logout**, from §5, does two things: it sends `Set-Cookie: session_id=; Max-Age=0` (telling the browser to discard the cookie) **and** invalidates the session server-side. Only the second one is a security control. The first is a convenience — a client can always keep a cookie it was told to delete.

**Expiry** is different: the browser keeps its cookie, and the server stops honouring it. The simulator lets you trigger it deterministically:

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

Look at the request line by line. The `Cookie: session_id=student-session` header is **still there** — the browser sent exactly what it sent when the request succeeded. The response is `401` anyway.

That is the clearest demonstration in this module of a principle you have now met from several directions: **the server decides.** A session is not "valid because the client has a cookie"; it is valid because the server still recognises it. Possession of a token is a *claim*, and the server checks the claim on every request.

**A note on what this module does not teach.** Session hijacking, session theft, credential stuffing and brute-force attacks against real accounts are all outside this module and outside this platform. Every session you inspect here is your own, on training accounts you were handed. The defensive side — regeneration at login, invalidation at logout, expiry, cookie flags — is what belongs in a fundamentals module, and it is what is taught above.

**Impact when A07 is real:** account takeover, and everything the compromised account can do. Where the account is administrative, that is the whole application.

**Mitigation:** multi-factor authentication where the account's value justifies it; check passwords against known-breached lists rather than imposing arbitrary composition rules; rate-limit and monitor authentication attempts; generate session identifiers with a cryptographically secure random source; **regenerate the session identifier on login**; invalidate server-side on logout; set sensible absolute and idle timeouts; set `Secure`, `HttpOnly` and `SameSite` on session cookies; make account recovery at least as strong as the login.

**Misconception:** *"This is the same as A01."*
**Correct:** they are adjacent and they interact, but they are different controls. A07 is *"is this really who they claim to be, and is that claim still valid?"* A01 is *"given that we know who this is, may they do this?"* An application can pass one and fail the other, and the fixes live in different code.

---

# A08:2021 – Software and Data Integrity Failures

## 23. Trusting Code and Data You Did Not Verify

This category asks one question: **did we check that this is what it claims to be, before we relied on it?**

Where it shows up:

- **Dependencies from untrusted sources** — a package pulled from a mirror nobody vetted, or a name one character away from the one you meant
- **Update mechanisms without verification** — software that fetches and applies an update without checking a signature. Whoever can answer the update request now runs code on every installation
- **Insecure deserialization** — an application that reconstructs objects from data supplied by a client. Depending on the format and library, deserializing attacker-controlled data can construct arbitrary objects and, in the worst cases, execute code. The safe pattern is to use data-only formats and never deserialize untrusted input into arbitrary types
- **CI/CD pipeline integrity** — the pipeline has credentials for everything it deploys to. Anyone who can alter what it builds, or slip a step into it, can ship code without touching the source repository
- **Content accepted without verification** — including files a user uploads

Note the relationship with A06, since these are easy to blur: **A06 is "our component has a known vulnerability."** **A08 is "we cannot be sure this component is even the component we asked for."** Different questions, different controls.

## 24. Uploads, Where Integrity Becomes Concrete

The training site models this end to end. It documents the pipeline it *should* have:

```
$ open https://cybershop.training/upload-security
━━━━━━━━ REQUEST ━━━━━━━━
GET /upload-security HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 434
Server: CyberShop-Sim/1.0
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'

FILE UPLOAD SECURITY PIPELINE
1. Authentication
2. Authorization
3. Size validation
4. Extension allowlist
5. MIME validation
6. Content/signature validation
7. Filename normalization
8. Randomized storage name
9. Safe (non-web-accessible) storage
10. Controlled serving

No single layer is sufficient by itself — defense in depth means applying multiple independent controls, since any one of them could be misconfigured or bypassed.
```

The vulnerable endpoint implements only step 4. Send it a filename with two extensions:

```
$ open -X POST -d "filename=shell.php.jpg" https://cybershop.training/upload
━━━━━━━━ REQUEST ━━━━━━━━
POST /upload HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 22
Cookie: session_id=student-session

filename=shell.php.jpg

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 100
Server: CyberShop-Sim/1.0
Cache-Control: no-store
X-Sim-Upload-Extension: .jpg
X-Sim-Upload-Mime: 
X-Sim-Upload-Signature: 
X-Sim-Upload-Kind: accepted_vulnerable
X-Sim-Upload-Stored-Name: shell.php.jpg
X-Sim-Upload-Web-Accessible: true
Content-Security-Policy: default-src 'self'; script-src 'self'

{"status": "success", "id": "shell.php.jpg", "stored_name": "shell.php.jpg", "web_accessible": true}
```

Three things in that response, each worth a separate note:

- `X-Sim-Upload-Extension: .jpg` — the check passed, because the *last* extension is on the allowlist
- `X-Sim-Upload-Stored-Name: shell.php.jpg` — the original filename was kept, including the `.php` in the middle
- `X-Sim-Upload-Web-Accessible: true` — and it was stored somewhere the web server serves

None of those alone is fatal. Together they are the classic chain: some server configurations route a file by an extension that is not the last one, so a file the application believes is an image may be handed to a script interpreter. The application never checked whether the file's **content** matched what its name claimed.

Confirm it is stored:

```
$ open https://cybershop.training/uploads
━━━━━━━━ REQUEST ━━━━━━━━
GET /uploads HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Cookie: session_id=student-session

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 75
Server: CyberShop-Sim/1.0
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'

Uploaded files:
  #shell.php.jpg shell.php.jpg (vulnerable, web-accessible)
```

That read-back is the step people skip. `200 OK` was the server's claim; the listing is the *state*, and the state is the evidence.

The same upload against the endpoint that implements more of the pipeline:

```
$ open -X POST -d "filename=shell.php.jpg" https://cybershop.training/secure-upload
━━━━━━━━ REQUEST ━━━━━━━━
POST /secure-upload HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 22
Cookie: session_id=student-session

filename=shell.php.jpg

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 415 Unsupported Media Type
Content-Type: application/json
Content-Length: 85
Server: CyberShop-Sim/1.0
X-Sim-Upload-Extension: .jpg
X-Sim-Upload-Mime: 
X-Sim-Upload-Signature: 
X-Sim-Upload-Kind: mime_rejected
Content-Security-Policy: default-src 'self'; script-src 'self'

{"status": "error", "message": "Declared Content-Type does not match the extension."}
```

`415`, rejected at the MIME check — a layer the vulnerable endpoint does not have. **Same filename, same allowlist, different outcome, because the second design does not stop at the first check.** That is defence in depth stated as a behaviour rather than as a slogan.

**Impact when A08 is real:** at the low end, unexpected content served to users; at the high end, code execution on the server or on every machine that installed a tampered update. Integrity failures tend to be severe because they undermine the assumption every other control rests on.

**Mitigation:** verify signatures on dependencies and updates; pin versions and check integrity hashes; use trusted registries; do not deserialize untrusted data into arbitrary types; protect the build pipeline as production infrastructure; and for uploads, apply the layers in the list above rather than any single one of them.

**Misconception:** *"Checking the file extension is enough."*
**Correct:** the extension is a claim made by the client, in a name the client chose. So is the declared `Content-Type`. Neither is evidence about the file's content. Verify the content, normalise the name, store outside the web root under a name you generated, and serve it deliberately.

---

# A09:2021 – Security Logging and Monitoring Failures

## 25. The Category You Cannot Test From Outside

Every other category describes something present that should not be. This one describes something **absent** — and it is the reason this category is genuinely different in kind.

If an application is attacked and nothing was recorded, nobody notices; if nobody notices, nobody responds; and when someone eventually does notice, there is nothing left to reconstruct what happened. The vulnerability is not what the attacker did. It is that the organisation had no way to find out.

Events worth recording, at minimum:

- authentication attempts, both successful and failed, with source and account
- authorization failures — someone repeatedly hitting resources they may not have is a strong signal
- administrative actions and privilege changes
- unexpected application errors, especially clusters of them
- input validation failures, especially many from one source
- high-value business transactions

And what makes a log actually useful, rather than merely large:

| Requirement | Why |
|---|---|
| Enough context | Who, what, when, from where, and the outcome. A line saying "error" helps nobody |
| Consistent timestamps | Correlating across systems is impossible without a common, synchronised time base |
| Centralised and tamper-resistant | Logs on the compromised host are logs the intruder can edit |
| Retained long enough | Intrusions are routinely discovered months after they began |
| **No secrets** | Never log passwords, session identifiers, tokens or full payment details. A log is a copy of your data with different access controls, and it is easy to over-share |
| Monitored | An alert nobody reads is not detection. This is the step organisations skip |

## 26. What This Platform Can Honestly Show

**Nothing.** The simulator models no server-side log at all, and there is no runnable evidence for this category anywhere in this module.

There is one distinction worth drawing from that, though, and it is a genuinely useful one. The `requests` command you have been using lists **your own client's** history — what you sent and what came back. It is not the server's log. Even a perfect record on the client side tells the defender nothing, because it lives on the attacker's machine. The whole point of A09 is what exists on the *other* side.

That is also why this category is nearly invisible to an external tester. You cannot generally establish whether an application logs and alerts adequately without access to its logging pipeline, its retention policy and its alerting rules. In an assessment, this is a question you *ask*, and a control you *review* — not one you probe.

If you want to see what the defending side of this looks like on this platform, the **SOC: Brute Force Investigation** lab (`soc-brute-force`, in the SOC lab category) is real, active, and has no prerequisite — it puts you on the other side of exactly the failed-login events this section says should be recorded.

**Impact when A09 is real:** intrusions continue undetected for far longer; incident response has no evidence to work from; the true scope of a breach cannot be established, which frequently means assuming the worst.

**Mitigation:** log the events above with enough context; centralise; protect and retain logs; **alert** on meaningful patterns rather than only storing; and rehearse the response, because a plan nobody has run is a document, not a capability.

**Misconception:** *"Nothing was logged, so nothing happened."*
**Correct:** absence of evidence in a system that records almost nothing is not evidence of absence. It is exactly the condition A09 describes.

---

# A10:2021 – Server-Side Request Forgery (SSRF)

## 27. When the Server Fetches What the Client Chose

The whole category turns on one distinction, so start there:

```
NORMAL:   client  ──►  your server           the client requests something from you

SSRF:     client  ──►  your server  ──►  somewhere else
                         (fetches a URL the client influenced)
```

In the normal case, the client's request goes wherever the client can already reach. In the SSRF case, the client causes **your server** to make a request — and your server sits inside your network, with your server's network position, your server's credentials, and past your perimeter controls.

That is the entire impact in one sentence: **the attacker borrows your server's position on the network.**

Applications end up here for perfectly reasonable-sounding reasons. Fetching a user-supplied image URL for a profile picture. Rendering a link preview. Importing data from a URL. Calling a webhook a user configured. Converting a page at a supplied address to PDF. In every case the application accepts a URL from a user and fetches it, which is exactly the thing SSRF requires.

**Potential impact, stated as categories rather than as instructions:**

- reaching internal services that were never exposed externally, because they were on a network nobody outside could reach
- reaching cloud instance metadata services, which in some configurations hand out credentials to whatever asks from the instance itself
- mapping internal networks by inference from response timing and error differences
- using the server as a relay to reach further systems

**This module gives no operational detail for attacking internal networks or metadata services, deliberately.** The reasoning above is what a defender and an assessor need; the technique against real infrastructure is out of scope for a fundamentals module and would be out of scope on this platform regardless.

**This platform has no SSRF scenario, and none is invented here.** The simulated site has no endpoint that fetches a URL on the server's behalf — every route serves data it already holds. There is nothing to run, so nothing is quoted.

One thing does exist and is worth using precisely because it is the *contrast*:

```
$ open https://evil.example.com/
External hosts are not available in the training environment.
```

That is a **client-side scope control**: your tool refused to make a request. Nothing server-side was involved, no server fetched anything, and no request object was even built. It is the opposite of SSRF, and holding the two side by side is the fastest way to fix the distinction in your head — SSRF is not about where *you* can send a request, it is about where you can make *the server* send one.

An illustrative example of what the vulnerable shape looks like — **illustrative only, not captured output, and no such endpoint exists on this platform**:

```
POST /import HTTP/1.1
Host: example-app.invalid
Content-Type: application/x-www-form-urlencoded

source_url=https://example.com/data.csv
```

The security question is not "is that URL malicious?" It is: **who decides what the server fetches, and what can the server reach?** If the answer to the first is "the client", the second becomes urgent.

**Mitigation:**

- **Allowlist** destinations — protocols, hosts, ports. Do not attempt to blocklist internal addresses; that reliably fails to redirects, alternative encodings and DNS records pointing at internal space.
- **Resolve and validate before connecting**, and again after any redirect, rather than validating the string the user submitted.
- **Segment the network** so the fetching service cannot reach anything it does not need.
- **Do not return the raw fetched response** to the client; that turns a blind SSRF into a full read primitive.
- **Require authentication on internal services.** "It's only reachable internally" is a network assumption, and SSRF is precisely the thing that breaks it.

**Misconception:** *"That's just the browser making a request."*
**Correct:** in SSRF, the *server* makes the request. That difference is the whole vulnerability, because the server's network position, credentials and trust relationships are entirely different from the browser's.

---

## 28. Categories Overlap — and That Is Fine

A single real finding often touches several of these. The file upload from §24 is a fair example:

| Reading | Category |
|---|---|
| Content was accepted without verifying it matches its claimed type | A08 — Integrity Failures |
| Uploads are stored in a web-accessible directory under a client-supplied name | A05 — Misconfiguration |
| The design never asked what happens if an uploaded file is executable | A04 — Insecure Design |

All three are defensible. The way to resolve it in a report is not to pick one and hope, and not to list all three vaguely — it is to **name the control that failed**, classify accordingly, and say in one line why you chose that category. A reader can then disagree with your classification while still understanding your finding perfectly, which is exactly the property a good report needs.

## 29. Common Misconceptions, Collected

**WRONG:** "Injection means SQL injection."
**CORRECT:** injection is any case where untrusted data reaches an interpreter that reads structure from a string. SQL, OS commands, templates, LDAP, and — in the 2021 edition — XSS are all members of the family, with the same cause and the same class of fix.

**WRONG:** "Filtering dangerous characters prevents injection."
**CORRECT:** filtering is a blocklist, and blocklists fail against the input you did not think of. Use the interpreter's parameterised API so the data cannot become structure regardless of its content, and encode at output per context.

**WRONG:** "A 500 error proves SQL injection."
**CORRECT:** a `500` proves the server errored. It is a useful signal to investigate, not evidence. The evidence is a demonstrated change in behaviour that only a structural change to the query explains.

**WRONG:** "If it's behind a login, it's protected."
**CORRECT:** that is authentication. Authorization is a separate decision that has to be made on every request, against the specific resource. A01 exists because applications routinely do the first and skip the second.

**WRONG:** "A09 doesn't matter — it doesn't let anyone in."
**CORRECT:** correct, and irrelevant. It determines whether anyone finds out, how long an intrusion lasts, and whether its scope can ever be established afterwards. It changes the *duration and cost* of every other failure on this list.

**WRONG:** "We're on the latest version, so A06 doesn't apply."
**CORRECT:** current versions have undiscovered vulnerabilities, and you still need inventory, monitoring and a patching process — otherwise you are only current until the next advisory, which you will not hear about.

## 30. Knowledge Check

1. Why is `403` not sufficient evidence that authorization is correctly enforced?
2. Explain, in terms of query structure, why parameterised queries prevent SQL injection while filtering apostrophes does not.
3. What is the difference between an implementation flaw and a design flaw? Which one can be fixed by patching a line of code?
4. Give two reasons an application running an old version of a library might nevertheless not be exploitable.
5. Distinguish A06 (Vulnerable and Outdated Components) from A08 (Software and Data Integrity Failures) in one sentence each.
6. In §22, the request carried a valid-looking session cookie and still received `401`. What does that demonstrate about where session validity is decided?
7. Why is A09 nearly impossible to assess from outside the application?
8. What single fact distinguishes SSRF from an ordinary client-side request, and why does it matter so much?
9. Why does the 2021 edition place cross-site scripting inside A03 (Injection)?
10. A finding could plausibly be classified as A04, A05 or A08. What should the report do?

<details>
<summary>Answers</summary>

1. It is one response to one request. It shows this request was refused; it does not show the check is applied on other routes and methods, applied against the correct resource, or that it cannot be bypassed by an approach not tested. Read the whole response and test more than one path before concluding.
2. Filtering tries to remove characters that could change the query's structure — a blocklist, which fails against encodings and inputs you did not anticipate. Parameterisation sends the query structure and the data to the database separately: the structure is compiled first and the data is bound into a placeholder afterwards, so there is no point at which the data could be read as structure, whatever it contains.
3. An implementation flaw means the code does not do what it was meant to; a design flaw means the code does exactly what it was meant to, and what it was meant to do is unsafe. Only the implementation flaw can be fixed by patching a line — a design flaw requires changing what the system is specified to do.
4. Any two of: the version may already carry a backported fix despite its version string; the vulnerable code path may be unreachable in how the application uses the component; the advisory's preconditions (configuration, platform, authenticated position) may not hold; another control may already block exploitation.
5. **A06:** a component we depend on has a *known vulnerability*. **A08:** we cannot be sure the component, data or update *is what it claims to be*, because its integrity was never verified.
6. That session validity is decided **server-side**. The client sent exactly the same cookie it had sent successfully moments earlier; the server had invalidated the session, so the request was unauthenticated. Possession of a token is a claim, and the server checks the claim on every request.
7. Because its symptom is an absence on the defender's side. Whether adequate events are recorded, retained, protected, monitored and alerted on cannot generally be established by sending requests; it is reviewed by examining the logging pipeline and the response process.
8. In SSRF the **server** makes the outbound request rather than the client. It matters because the server has a different network position, different credentials and different trust relationships — it can reach internal services no external client can, which is exactly what the attacker is borrowing.
9. Because it is the same mechanism: untrusted data reaches an interpreter — here the browser's HTML parser — and is read as structure (markup) rather than as data. The cause and the class of fix (contextual output encoding, the framework's safe API) match the rest of the family.
10. Name the control that failed, classify by that control, and state in one line why that category was chosen. That way a reader who would classify it differently still understands the finding exactly.
</details>

## 31. Where This Goes Next

**Hands-on Practice** runs this as one continuous investigation against the authorized training environment: access control, injection, authentication and configuration, each as a hypothesis you test and evidence you record — ending in a complete written finding with impact, severity reasoning, mitigation, validation strategy and stated confidence.
