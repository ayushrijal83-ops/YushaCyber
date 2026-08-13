# Core Concepts — Proxy, Repeater, Parameters, Cookies and Authorization

## 1. What You Will Learn

By the end of this lesson you should be able to:

- run the full Proxy workflow: generate → find in history → inspect → identify inputs → send to Repeater → modify → compare
- explain what Repeater is for, and why it is not "a hacking button"
- apply the **one-variable-at-a-time** rule and say precisely why it is the difference between evidence and noise
- name the six places client-controlled input hides in an HTTP request
- explain what cookies are for, how a session cookie carries identity, and what `Set-Cookie` vs `Cookie` mean
- state the difference between **authentication** and **authorization** and recognise each in a real response
- read `401`, `403`, `404`, `302` and `200` the way a tester should — as evidence, not verdicts
- compare two responses across status, length, headers and body, and say what the difference does and doesn't prove
- write an observation, an interpretation and a conclusion as three separate statements

Every terminal block in this lesson is real output from this platform's proxy simulator, captured in one continuous session so the history numbers line up. Nothing here is invented.

## 2. Where This Fits

Introduction gave you the shape: browser → proxy → server → response → proxy → browser, and a proxy that can pause the traffic in the middle. This lesson is the working method built on top of that shape.

The method is small enough to memorise:

```
GENERATE       do the thing in the application
  ↓
FIND           locate that request in HTTP history
  ↓
INSPECT        read exactly what was sent — every part
  ↓
IDENTIFY       which values here are client-controlled inputs?
  ↓
REPEATER       load the request into a place you can re-send it
  ↓
MODIFY         change exactly one thing
  ↓
SEND           re-send
  ↓
COMPARE        status, length, headers, body — what actually differs?
  ↓
HYPOTHESIS     what would explain that difference?
  ↓
VALIDATE       one more test that would distinguish it from the alternative
  ↓
DOCUMENT       observation / interpretation / confidence, kept apart
```

Everything below is one of those steps, in detail.

## 3. The Proxy, Precisely

The Proxy is the component that sits in the traffic path. Two things it does, and it is worth separating them because people conflate them constantly:

**It records, always.** Every request and response that passes through goes into HTTP history whether or not you were watching. That is passive, and it is where most of your evidence comes from.

**It intercepts, when you ask.** Interception is opt-in and it pauses traffic.

```
$ proxy
Browser --> Proxy --> Server
Intercept: OFF
Scope: cybershop.training
Requests outside scope are never proxied — they're rejected before a request object even exists.
```

Intercept is off by default here, exactly as it is in a sensible real Burp workflow.

### Intercepting the request vs. intercepting the response

Real Burp can hold traffic in both directions, and the two are used for different purposes:

| | What you can change | What it tests |
|---|---|---|
| **Request interception** | Method, path, parameters, headers, cookies, body | What the **server** does with input it didn't expect |
| **Response interception** | Status, headers, body — before the browser sees them | What the **browser/client-side code** does with data it didn't expect |

**Request interception is the more important of the two for security testing**, and the reason is the single most important idea in this module:

> The browser is not the security boundary. The server is.

Whatever the interface allows, disallows, hides or validates is a convenience for honest users. A tester (or an attacker) does not have to use the interface at all — a request can be constructed by hand, with any values at all. So the only validation that provides any security is validation the **server** performs. Request interception is how you test whether that server-side validation actually exists, or whether the application was merely relying on its own form to behave.

Response interception is genuinely useful too — it is how you test client-side behaviour, feature flags returned by an API, or what a page does with malformed data. It is just a different question.

### Forward, drop, and the baseline habit

Once a request is held: **forward** it (release it), **modify then forward**, or **drop** it (it never arrives).

Build one habit now: **the first time you intercept a request, forward it unchanged and confirm the response is what you got without the proxy.** If it isn't, your instrument is affecting your experiment and everything downstream is suspect. It takes ten seconds and it removes a whole category of confusing results.

## 4. HTTP History as a Working Tool

History answers "what did the client actually do?" — and it answers it after the fact, without requiring you to have been watching.

```
$ requests
Request history:
  #1  GET /products  -> 200 OK
  #2  GET /products  -> 200 OK
  #3  GET /account  -> 302 Found
  #4  POST /auth/login  -> 302 Found
  #5  GET /account  -> 200 OK
  #6  GET /admin  -> 403 Forbidden
  #7  POST /logout  -> 302 Found
  #8  GET /admin  -> 401 Unauthorized
  #9  GET /api/me  -> 401 Unauthorized
  #10  GET /api/me  -> 200 OK
  #11  GET /api/me  -> 401 Unauthorized
```

That is the entire session this lesson uses, in eleven lines. Everything below unpacks parts of it.

**How to actually use history**, as a workflow rather than a log to scroll:

1. **Do one thing** in the application — one click, one form submission.
2. **Look at what appeared.** Often it's several requests, not one. That in itself is information.
3. **Find the one that carries the action** — usually the `POST`, or the request whose parameters look like your input.
4. **Open it fully.** Method, path, query, headers, cookies, body — all of it.
5. **Ask: which of these values did the client choose?** Those are your test surface.

In real Burp, history is a filterable table with columns for host, method, URL, status, length and MIME type — and sorting by **length** is a well-worn trick for spotting the one response among two hundred that differs.

**A caution that generalises past this platform:** the history line is a summary. Entries #1 and #2 above both read `GET /products`, and they were different requests — one asked for `id=42`, the other for `id=43`. The line omits the query string. Never cite a history line as your evidence; open the exchange.

## 5. Repeater: Controlled Repetition

**Repeater** takes one request, holds it in an editor, and lets you send it as many times as you like, changing whatever you want between sends.

That is all it is. And the "that is all it is" is the point:

> **WRONG:** "Repeater exploits the server."
>
> **CORRECT:** Repeater gives you controlled replay and modification of a request you already have. Every consequence comes from the request you chose to send — Repeater has no opinions and does nothing on its own.

Why it matters is subtler than it looks. Without Repeater you can only test through the browser, which means the browser gets to decide what your request contains. The form validates the field. The interface only offers the buttons it wants to offer. The JavaScript encodes your input before sending. All of that stands between you and the question you're trying to ask.

Repeater removes the intermediary. **You** decide what the request contains, byte by byte, and you can send it fifty times with fifty small differences and watch what the server says to each.

Here is loading a request into Repeater — the request from history entry #1:

```
$ repeater 1
Sent to Repeater (from history #1):
GET /products?id=42 HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
```

Nothing has been sent. It's loaded, editable, and waiting — a copy, not the original, so editing it can't corrupt the history entry it came from.

Change exactly one thing:

```
$ edit query id 43
Query parameter 'id' set to '43'.
```

Send it:

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

**Proxy vs. Repeater — the distinction to keep straight:**

| | Proxy | Repeater |
|---|---|---|
| Where the request comes from | The browser generated it | You loaded it from history |
| When you can edit it | Only while it's held in flight | Any time, repeatedly |
| How many times it's sent | Once | As many as you like |
| Best for | Catching what the app really sends | Experimenting on one request |

A one-line version: **Proxy is for capture; Repeater is for experiment.**

## 6. Change One Variable at a Time

This is the methodology section, and it is more important than any tool feature in this module.

Suppose you change the `id` parameter, add a header, alter the cookie, and switch the method — all at once — and the response changes. What did you learn?

**Nothing.** You have one difference in the output and four differences in the input. You cannot attribute the effect to any cause. Worse, two of your changes might be cancelling each other out, hiding a real behaviour completely.

The rule:

> **Change exactly one thing. Send. Compare against the unchanged baseline.**

Which means you need three things before you start:

1. **A baseline** — the original request and its exact response, recorded.
2. **One change**, chosen because you can say *what question it answers*.
3. **A comparison** across status, length, headers and body.

The worked example above is precisely this. Baseline: `id=42`. One change: `id=43`. Now compare:

```
$ compare 1 2
Comparing #1 vs #2 responses:
  HTTP/1.1 200 OK
  Content-Type: text/html
  Content-Length: 34
  Server: CyberShop-Sim/1.0
  Cache-Control: max-age=60
! #1: ETag: "product-42-v1"
! #2: ETag: "product-43-v1"
  Last-Modified: Wed, 01 Jan 2025 00:00:00 GMT
  Content-Security-Policy: default-src 'self'; script-src 'self'
  
! #1: Product #42: Sample training item.
! #2: Product #43: Sample training item.
```

Lines with `!` differ; the rest are identical. Two things changed: the `ETag` header and the body. Everything else — status, content type, length, cache directives — is the same.

Now state what you actually know, in three separate registers:

> **OBSERVATION.** Changing the `id` query parameter from `42` to `43` returned a response with a different body and a different `ETag`. Status code, `Content-Type` and `Content-Length` were unchanged.
>
> **INTERPRETATION.** The `id` parameter selects which product resource the endpoint describes, and the value also appears inside the cache identifier the server generates.
>
> **CONCLUSION.** This endpoint uses a client-controlled identifier to select the resource it returns.

Notice what is **not** in there:

> **NOT:** "The endpoint is vulnerable."

It isn't — not on this evidence and possibly not at all. A product catalogue is *supposed* to let you request different products by id; that is the entire design of the web. A client-controlled identifier only becomes a security finding when it selects data the requesting user is **not authorized to see**, and nothing above tested authorization at all. §11 does.

> **WRONG:** "I changed a parameter and the response changed, so it's vulnerable."
>
> **CORRECT:** Changing an input is a *test*. The response is *data*. Whether the result is a security issue depends on what the returned data is, who was asking, and whether the server should have allowed it.

That gap — between "something changed" and "something is wrong" — is where a tester's credibility is either built or destroyed.

**Two more disciplines that come with the same rule:**

**Reproduce before you report.** Send the baseline again after the modified request. If the baseline no longer produces the baseline response, something else changed (state, session, timing) and your comparison is contaminated.

**Record as you go, not afterwards.** Original request, modified request, both responses, what differed. Ten minutes later you will not remember whether it was `id=43` or `id=44`, and re-running from memory is how false findings get written.

## 7. Where Parameters Hide

A **parameter** is any named value the client sends. It is not a special or dangerous thing; it is just input. But testers who only look at the URL miss most of them.

Six locations, all real, all client-controlled:

**1. Query string** — after `?` in the URL.

```
GET /products?id=42 HTTP/1.1
```

**2. Path segment** — part of the URL itself. `GET /users/42/orders` has `42` as a path parameter, exactly as much an input as `?id=42` is. This platform's simulator has one such route, `/upload/<id>`.

**3. Form body** — `POST` with `Content-Type: application/x-www-form-urlencoded`:

```
POST /auth/login HTTP/1.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 37

username=student&password=training123
```

Two parameters: `username` and `password`.

**4. JSON body** — the API equivalent:

```
POST /api/profile HTTP/1.1
Content-Type: application/json
Content-Length: 31

{"display_name": "Alex Rivera"}
```

One parameter, `display_name`. JSON bodies nest, and nested fields are parameters too — `{"user": {"role": "admin"}}` contains a `role` input several levels down. Testers who only skim the top level miss them.

**5. Header value** — every header is client-supplied. `User-Agent`, `Referer`, `Accept-Language`, `Origin`, `X-Forwarded-For`, and any custom `X-` header an application invents. If the server *uses* a header value in a decision, that header is an input to that decision.

**6. Cookie value** — cookies are headers, but worth naming separately because they usually carry identity. §9.

**The practical drill.** Take a request from history, list every named value in it — query, path, body, headers, cookies — and for each one ask two questions: *what would this value change?* and *what does the server do if it isn't what the form would have sent?* That list is your test surface for that endpoint. It is normally longer than people expect.

**And do not overreach in the other direction.** A parameter is not a vulnerability, and a long list of parameters is not a long list of findings. It is a list of things you now know exist.

## 8. Headers, and What They're Actually For

Learn the ordinary purpose of a header before you learn what testers do with it. A tester who doesn't know what `Host` normally does cannot recognise when something is odd about it.

| Header | Normal purpose |
|---|---|
| `Host` | Which site the request is for — required in HTTP/1.1, since one server hosts many sites |
| `User-Agent` | The client describing itself (browser, version, platform) |
| `Accept` | What content types the client can handle in the response |
| `Content-Type` | How the **request body** is encoded (also used on responses, for the response body) |
| `Content-Length` | How many bytes the body is |
| `Cookie` | Values the client is sending back to the server — usually including a session identifier |
| `Authorization` | Credentials or a token proving identity — an alternative to cookie-based sessions |
| `Referer` | The page the request came from (note the historical misspelling — it's in the standard) |
| `Origin` | The scheme/host/port that initiated a cross-origin request |

On the response side you already met `Server`, `Set-Cookie`, `Location`, `Cache-Control`, `ETag` and `Content-Security-Policy`.

**Why headers matter to a tester** — three ordinary reasons, none of them mystical:

- **They carry identity.** `Cookie` and `Authorization` are how the server knows who you are. Nearly all authorization testing runs through them.
- **They're client-controlled.** Every one of them. If the server makes a decision based on a header, the client can influence that decision.
- **They disclose.** `Server: CyberShop-Sim/1.0` names product and version. A real one might name a framework with known CVEs.

> **WRONG:** "Headers are where the vulnerabilities are — add weird ones and see what breaks."
>
> **CORRECT:** Headers are ordinary protocol machinery with defined purposes. They become security-relevant when the server *uses* one to make a decision. Testing a header without a hypothesis about which decision it feeds is guessing, and guessing produces noise.

### The Authorization header

`Authorization` deserves its own treatment because students routinely confuse it with cookie sessions.

```
Authorization: Bearer <token>
```

A **bearer token** is a credential where possession is sufficient — whoever bears it is treated as the identity it represents. That is why tokens are short-lived, scoped, and never pasted into a report, a screenshot, a ticket or a chat message.

Here is the real difference between the two mechanisms, in this platform's environment. First a request to a token-protected API endpoint with no credentials at all:

```
$ open https://cybershop.training/api/me
━━━━━━━━ REQUEST ━━━━━━━━
GET /api/me HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 401 Unauthorized
Content-Type: application/json
Content-Length: 57
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'

{"status": "error", "message": "Authentication required"}
```

Now the same request carrying the fixed training token (`training-token-001` — a fictional, non-secret value hardcoded into the simulator for exactly this demonstration):

```
$ open -H "Authorization: Bearer training-token-001" https://cybershop.training/api/me
━━━━━━━━ REQUEST ━━━━━━━━
GET /api/me HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Authorization: Bearer training-token-001

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 23
Server: CyberShop-Sim/1.0
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; script-src 'self'

{"username": "student"}
```

And with an invalid token:

```
$ open -H "Authorization: Bearer wrong-token" https://cybershop.training/api/me
━━━━━━━━ REQUEST ━━━━━━━━
GET /api/me HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
Authorization: Bearer wrong-token

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 401 Unauthorized
Content-Type: application/json
Content-Length: 57
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'

{"status": "error", "message": "Authentication required"}
```

Three requests, one variable changed each time, and a clean result: **this endpoint authenticates by bearer token and by nothing else.** A valid session cookie does not open it — you can verify that yourself in Hands-on Practice.

> **OBSERVATION.** `GET /api/me` returns `401` with no `Authorization` header, `200` with `Authorization: Bearer training-token-001`, and `401` with a different token value.
>
> **INTERPRETATION.** This endpoint authenticates via the `Authorization` header and validates the token's value.
>
> **CONCLUSION.** Token authentication is a separate mechanism from the cookie session used by the HTML pages of the same site.

That last point is the one to carry: **one application can use several authentication mechanisms at once**, and they may not enforce the same rules. Finding an API endpoint whose checks are weaker than the web pages' is an entirely realistic finding.

## 9. Cookies and Sessions

You met cookies in Web Fundamentals. Here is the same mechanism, viewed as evidence.

The cycle, in four steps:

```
1. Client sends credentials         POST /auth/login  (username + password in the body)
2. Server responds with a cookie    Set-Cookie: session_id=...
3. Client stores it                 the browser's cookie jar
4. Client sends it back, always     Cookie: session_id=...   on every later request
```

Two header names, two directions, and they are not interchangeable:

- **`Set-Cookie`** is a **response** header. The server telling the client to store something.
- **`Cookie`** is a **request** header. The client sending stored values back.

Watch the whole cycle in real output. Start with a protected page, not logged in:

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

No `Cookie` header on the request — there's nothing stored yet. The server answers `302 Found` with `Location: /login`: *go and log in.* Note the body is empty; the entire meaning is in the status line and one header.

Now log in:

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

There it is: `Set-Cookie: session_id=student-session`. The client stores it:

```
$ cookies
session_id=student-session
```

And now the identical request to `/account` behaves differently:

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

Same method, same path, different outcome. The comparison:

```
$ compare 3 5
Comparing #3 vs #5 responses:
! #3: HTTP/1.1 302 Found
! #5: HTTP/1.1 200 OK
! #3: Location: /login
! #5: Content-Type: text/html
! #3: Content-Length: 0
! #5: Content-Length: 29
  Server: CyberShop-Sim/1.0
! #3: Content-Security-Policy: default-src 'self'; script-src 'self'
! #5: Cache-Control: no-store
! #3: 
! #5: Content-Security-Policy: default-src 'self'; script-src 'self'
  
! #3: 
! #5: Account settings for student.
```

> **OBSERVATION.** `GET /account` returned `302 Found` with `Location: /login` when no `Cookie` header was present, and `200 OK` with account content when `Cookie: session_id=student-session` was present. Nothing else about the request changed.
>
> **INTERPRETATION.** The server uses the session cookie to decide whether the requester is authenticated, and `/account` requires authentication.
>
> **CONCLUSION.** The session cookie carries the identity that this route's access decision depends on.

That is a complete, correct, evidence-backed piece of work about a session, and notice what it did **not** require: no stolen cookie, no forged value, no other user's session. Comparing *your own authorized session against your own unauthenticated state* is a legitimate, informative test, and it's most of what session testing is.

**What this module does not teach, deliberately:** stealing session identifiers, forging them, or using anyone's session but your own. Session theft has its own module later (`owasp-top-10`), where the defensive side — `Secure`, `HttpOnly`, `SameSite`, session regeneration on login, proper invalidation on logout — is taught alongside it, which is the only responsible order.

> **WRONG:** "Cookie = authentication."
>
> **CORRECT:** A cookie is a general mechanism for carrying state between requests — preferences, language, cart contents, anything. A *session* cookie is one use of that mechanism, where the value identifies a server-side session that may represent an authenticated user. Plenty of cookies have nothing to do with identity at all.

## 10. Authentication vs. Authorization

Two words, routinely used as synonyms, describing two different decisions the server makes in sequence.

| | Question | Failure means | Typical status |
|---|---|---|---|
| **Authentication** | *Who are you?* | The server doesn't know who's asking | `401 Unauthorized` |
| **Authorization** | *What are you allowed to do?* | The server knows, and says no | `403 Forbidden` |

Authentication happens first and answers identity. Authorization happens second and answers permission. You can pass the first and fail the second — that's the normal case for any user hitting an admin page.

Here it is in real responses, on one URL, with one variable changing between them.

**Logged in as `student`, requesting `/admin`:**

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

The server's own message says it exactly: *authenticated, but not authorized.* Identity established; permission refused.

**Now log out and request the same URL:**

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

Note the logout response: `Set-Cookie: session_id=; Max-Age=0` — the server telling the client to *delete* the cookie by setting it empty with a zero lifetime. A proper logout does two things: invalidates the session on the server, and clears the client's copy. Only the first actually provides security; the second is hygiene.

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

`401` this time, not `403`. Same URL, same method. The only difference is whether the request carried a session.

```
$ compare 6 8
Comparing #6 vs #8 responses:
! #6: HTTP/1.1 403 Forbidden
! #8: HTTP/1.1 401 Unauthorized
! #6: Content-Type: application/json
! #8: Content-Type: text/plain
! #6: Content-Length: 103
! #8: Content-Length: 34
  Server: CyberShop-Sim/1.0
  Content-Security-Policy: default-src 'self'; script-src 'self'
  
! #6: {"error": "Forbidden", "message": "You are authenticated, but not authorized to access this resource."}
! #8: You must log in to view this page.
```

> **OBSERVATION.** `GET /admin` returned `403 Forbidden` when carrying the `student` session cookie, and `401 Unauthorized` when carrying no cookie. Status, content type, length and body all differ.
>
> **INTERPRETATION.** The endpoint distinguishes "not authenticated" from "authenticated but not permitted", and enforces both server-side.
>
> **CONCLUSION.** `/admin` requires both authentication and a specific authorization level, and the server — not the interface — is making both decisions.

That third statement is a genuinely useful finding to be able to write, and note that it is a statement about *correct* behaviour. **Testing that confirms a control works is real work, not a failed test.**

## 11. Authorization Testing — the Reasoning, Not the Acronym

You will eventually meet a three-letter name for one class of authorization flaw. Skip it for now; learning the reasoning first is what makes the name useful later instead of a label you pattern-match onto things.

The question authorization testing asks is always the same:

> **Does the server enforce, for this specific request, that the requester is allowed to have this specific thing?**

The procedure, on a system you are authorized to test:

1. **Authenticate as user A** in the authorized environment.
2. **Capture the request** that fetches a resource belonging to A.
3. **Find the identifier** that selects the resource — a query parameter, a path segment, a body field.
4. **Change only that identifier**, to one belonging to another *test* account you also control or that the engagement explicitly permits.
5. **Send it.**
6. **Compare the responses.**
7. **Determine whether the server enforced authorization** — or merely relied on the interface not offering the option.

Step 4 is where the boundary lives, and it is not a formality. Changing an identifier to a value belonging to a **real** person, on a system you don't own, is unauthorized access to their data. The technique is identical; the authorization is what separates a test from an offence. In a professional engagement you are given multiple test accounts precisely so this can be done without touching anyone real.

**How to read the outcome:**

| Response to A's request for B's resource | What it means |
|---|---|
| `403` / `401` | The server checked ownership and refused. Working as intended. |
| `404` | Refused, and the server declined to confirm the resource exists — a deliberate design choice some applications make. |
| `200` with **B's data** | The server did **not** check. This is the finding. |
| `200` with **A's own data** | The identifier isn't what selects the resource; look again at what does. |

Note the last row. A `200` alone proves nothing — you must read the body and determine *whose data came back*. Reporting a finding on the strength of a status code, without checking what the response actually contained, is one of the most common ways a beginner's report gets rejected.

**Then there is the trap the interface sets:**

> **WRONG:** "The button isn't shown to this user, so this user can't do it."
>
> **CORRECT:** The server must enforce authorization regardless of what the interface displays. A hidden button hides an option from an honest user. It does not remove the endpoint, and anyone with a proxy can send the request the button would have sent.

That is the single most valuable sentence in this module, and the reason the whole discipline exists. Half of all real authorization findings are exactly this: a control implemented in the interface and never implemented on the server.

**What this platform's environment can and cannot demonstrate.** It has three fixed training accounts — `student`, `analyst` and `admin` — and a route (`/admin`) whose access depends on which of them you are. That is enough to demonstrate the authentication/authorization distinction from real responses, and Hands-on Practice §9 walks it. What it does **not** have is a per-user resource endpoint (something like `/orders/1041` belonging to one user and `/orders/1042` to another), so the "fetch another user's object by changing its id" scenario cannot be executed here. That gap is stated rather than papered over with an invented example — you'll meet the real thing in `owasp-top-10`, and in any deliberately vulnerable application you install for practice.

## 12. Comparing Responses Properly

"Compare the responses" is easy to say and easy to do badly. Here is what to compare, in the order you should look:

| Compare | Why it matters |
|---|---|
| **Status code** | The coarsest signal — a `200` vs `403` is a completely different decision |
| **Response length** | The fastest way to spot a difference in a large body. Two `200`s of different lengths are two different answers |
| **Headers** | `Set-Cookie`, `Location`, `Content-Type`, `Cache-Control`, `ETag` — decisions live here |
| **Body** | What actually came back. `200` with an error message inside is not success |
| **Redirect target** | `Location` tells you where the app wanted to send you, which reveals what it thought happened |
| **Error messages** | Different errors for different causes leak how the server reasons — sometimes usefully, sometimes as a finding in itself |
| **Timing** | A response that takes markedly longer can indicate different work being done. Weak evidence alone; suggestive in combination |

Two rules that prevent most bad comparisons:

**Compare like with like.** Two responses are only comparable if everything except your one variable was the same — same session, same headers, same order. If you logged in between them, you changed two things.

**A difference is not a diagnosis.** It tells you the server behaved differently. *Why* is a hypothesis, and the next request you send should be the one that would distinguish your hypothesis from the obvious alternative.

**And the case that catches everyone:** the response can be *identical* and something can still have happened. A `POST` that returns the same `200` regardless of whether it worked tells you nothing about whether it worked. To find out, you `GET` the resource back and read it. Hands-on Practice §10 investigates a real instance of exactly this in this environment.

## 13. Status Codes, Read as Evidence

You met status codes in Web Fundamentals. Here they are again, as a tester reads them.

| Code | Generally means | What a tester should think |
|---|---|---|
| `200 OK` | Request succeeded | Success at the HTTP level. Says nothing about whether the *action* worked — read the body |
| `201 Created` | A resource was created | Something now exists that didn't. Check `Location` |
| `204 No Content` | Success, no body | Common for deletes and updates. Verify the effect separately |
| `301` / `302` | Redirect | Where to? `Location` often reveals the app's view of what happened |
| `400 Bad Request` | Malformed request | Your input was rejected before processing. Often a parser limit, not a security control |
| `401 Unauthorized` | Missing or invalid authentication | The server doesn't know who you are |
| `403 Forbidden` | Understood, refused | The server knows who you are and says no |
| `404 Not Found` | No such resource | Or: a deliberate choice not to confirm one exists |
| `405 Method Not Allowed` | Wrong method for this path | The path exists; the method doesn't apply to it |
| `500 Internal Server Error` | Server-side failure | Something broke. Often the most informative response you'll get — and a strong signal to stop and think rather than push harder |

**401 vs 403 vs 404 — the distinction worth internalising:**

> **WRONG:** "401 means you don't have permission."
>
> **CORRECT:** `401` generally indicates *missing or invalid authentication* — the server doesn't know who you are. `403` generally indicates the server *understood the request and refuses it* — identity established, permission denied. `404` says the resource wasn't found, which some applications deliberately return instead of `403` so that an unauthorized requester can't even confirm a resource exists.

Why it matters practically: those three codes tell you three different things about how far your request got.

- `401` → you haven't got past identity. Nothing about permissions has been evaluated yet.
- `403` → identity is fine; the authorization layer stopped you. **There is something there.**
- `404` → either nothing is there, or something is and the server won't say. Distinguishing those two is a real testing skill, usually done by comparing against a path you *know* doesn't exist.

Here is that baseline in this environment — a path that genuinely doesn't exist:

```
$ open https://cybershop.training/nothing-here
━━━━━━━━ REQUEST ━━━━━━━━
GET /nothing-here HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 404 Not Found
Content-Type: text/plain
Content-Length: 37
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'

The requested resource was not found.
```

That's your known-nonexistent baseline: `404`, `text/plain`, 37 bytes. If a path you *suspect* exists returns something subtly different from that — a different length, a different content type, a different message — the difference is a signal worth following.

**One caution that applies to this entire table.** These are the standard's general meanings, and applications deviate constantly: returning `200` with an error in the body, `403` where `401` is meant, `404` for everything unauthorized. Read what the application actually does and describe *that*. The specification tells you what a code is supposed to mean; only testing tells you what this application means by it.

> **Never write:** "the endpoint returned 403, therefore [specific vulnerability]." A status code is one piece of evidence. Findings need several.

## 14. Repeater Experiment — Practise the Method

Do this in the **Burp Suite Fundamentals** mission terminal. Every command is one you have already seen in this lesson.

**Setup.** Make one baseline request and load it into Repeater:

```
open https://cybershop.training/products?id=42
requests
repeater 1
```

**Run the experiment.** Change one thing, send, compare:

```
edit query id 43
repeater send
compare 1 2
```

**Now record it.** Fill this in properly, in writing — the recording is the exercise, not the commands:

```
ORIGINAL REQUEST:
    GET /products?id=42 HTTP/1.1

MODIFIED REQUEST:
    GET /products?id=43 HTTP/1.1

VARIABLE CHANGED:
    the `id` query parameter, 42 → 43. Nothing else.

ORIGINAL RESPONSE:
    200 OK, Content-Length 34, ETag "product-42-v1",
    body "Product #42: Sample training item."

MODIFIED RESPONSE:
    200 OK, Content-Length 34, ETag "product-43-v1",
    body "Product #43: Sample training item."

OBSERVED DIFFERENCE:
    ETag and body changed. Status, Content-Type and Content-Length identical.

INTERPRETATION:
    The `id` parameter selects which product the endpoint describes, and its
    value is used to build the cache identifier.

SECURITY SIGNIFICANCE:
    None demonstrated. A catalogue endpoint returning different products for
    different ids is its intended function. Nothing here tested authorization.

CONFIDENCE:
    High that the parameter selects the resource — directly observed, twice,
    with a controlled comparison.

WHAT WOULD VALIDATE THIS FURTHER:
    Whether any id maps to data a requester shouldn't see; whether unknown or
    non-numeric ids are handled differently; whether the endpoint behaves the
    same unauthenticated.
```

**Then extend it, one variable at a time.** For each, predict the result *before* you send, then check:

1. `edit query id 99999` — does a very large id behave differently?
2. `edit query id abc` — does a non-numeric id behave differently?
3. `edit header User-Agent CyberBrowser/2.0` then send — does the server's answer depend on the client's self-description?
4. Log in, load a `/account` request into Repeater, and send it. Then log out and send the *same* Repeater request again. What changes, and why?

Number 4 is the most instructive. The Repeater copy is fixed — but the *session it refers to* lives on the server, and the server's answer to a fixed request can change when the state behind it changes. That's a real and frequently-missed subtlety: **the request being identical does not make the conditions identical.**

## 15. Observation, Interpretation, Conclusion

Every result in this lesson was written in three separate registers, and it is the habit worth taking away more than any command:

**OBSERVATION** — what the evidence literally shows. Anyone re-running your steps would see the same thing. No inference.

> Changing `id` from 42 to 43 returned a different body and a different `ETag`; status and length were unchanged.

**INTERPRETATION** — what you think explains the observation. This is where judgement enters, and it may be wrong.

> The `id` parameter selects which resource the endpoint returns.

**CONCLUSION** — what you are prepared to state as a claim about the application, with a stated confidence.

> This endpoint uses a client-controlled identifier to select the resource returned. Confidence: high.

Keeping these apart does three things. It makes your findings checkable, because someone else can verify your observation independently of whether they accept your interpretation. It makes you honest with yourself, because writing "interpretation" forces you to notice you're inferring. And it makes you credible, because the tester who says "I observed X; I think it means Y; I'm not certain" is the one people believe when they later say "I'm certain."

## 16. Common Misconceptions

**"Changing a parameter means the application is vulnerable."** Changing an input is a test. The response is data. Whether it's a finding depends on what came back, who asked, and whether the server should have allowed it.

**"Repeater exploits the server automatically."** Repeater replays and edits a request you chose. Every consequence follows from what you sent.

**"401 means you don't have permission."** `401` means the server doesn't know who you are. `403` means it does and refuses. The gap between them is diagnostic.

**"If the button isn't visible, the user can't do it."** The server must enforce authorization regardless of the interface. A hidden button hides an option; it doesn't remove the endpoint.

**"Cookie = authentication."** A cookie carries state. A session cookie is one use of that mechanism, which may represent an authenticated session.

**"Same status code, so nothing changed."** Two `200`s can carry entirely different bodies — and a `200` can be returned by an operation that silently did nothing.

**"Burp sees inside HTTPS automatically."** Reading TLS traffic requires deliberate setup on a machine you control: the client must trust the proxy's CA certificate.

**"More changes per test finds bugs faster."** Multiple simultaneous changes produce uninterpretable results and can mask real behaviour. One variable, always.

## 17. Knowledge Check

1. What problem does an intercepting proxy solve that reading the page cannot?
2. Why is HTTP history useful even when you weren't watching at the time?
3. What's the difference between Proxy and Repeater? Give one task each is right for.
4. Why change one variable at a time? Describe a concrete way a two-variable change could mislead you.
5. Name the six locations client-controlled input can occupy in an HTTP request.
6. What is the difference between authentication and authorization? Give the typical status code for each failure.
7. Why must the server enforce authorization even when the interface never offers the option?
8. What can a cookie carry, and what specifically does a *session* cookie carry?
9. Explain the difference between `Set-Cookie` and `Cookie`, including direction.
10. Why compare status, headers and body rather than just the status code?
11. Why isn't a changed parameter automatically a vulnerability? Answer with reference to §6's worked example.
12. What does `401` generally indicate? What does `403` generally indicate? Why might an application return `404` where `403` would be more literal?
13. In §8, three requests to `/api/me` produced `401`, `200`, `401`. What single variable changed, and what does the pattern establish?
14. Two responses are byte-identical. Name a circumstance in which something nevertheless happened on the server.
15. Why must every technique in this lesson be run only against authorized targets, given that none of it "breaks" anything?

## 18. Key Takeaways

- The workflow is fixed: generate → find → inspect → identify inputs → Repeater → modify → send → compare → hypothesise → validate → document.
- Proxy captures; Repeater experiments. Interception pauses traffic; history records it whether you were watching or not.
- Change one variable at a time, against a recorded baseline, or your result means nothing.
- A parameter is just an input. Six places to look: query, path, form body, JSON body, headers, cookies.
- Headers have ordinary purposes. They matter to a tester when the server uses one to make a decision.
- `Authorization: Bearer <token>` is a separate mechanism from cookie sessions, and one application can use both — with different strictness.
- `Set-Cookie` is a response header; `Cookie` is a request header. A session cookie carries the identity the server's access decisions depend on.
- Authentication asks who you are; authorization asks what you may do. `401` and `403` are the server telling you which one you failed.
- The browser is not the security boundary. The server is. A hidden control is not an enforced control.
- Compare status, length, headers, body, redirect and error text — and remember that identical responses don't prove nothing happened.
- Keep observation, interpretation and conclusion separate, and state confidence per claim.

## 19. What's Next

**Hands-on Practice** puts all of this in your hands: six exercises in the authorized training environment, from capturing a single request through to writing a documented, evidence-based finding about a real bug that lives in this platform's simulator — one that returns `200 OK` and quietly does nothing.

After this module, `owasp-top-10` takes the authorization reasoning of §11 to its named categories, `web-pentesting` builds full assessment methodology on it, and every API-security topic you meet later runs on the request/response reading you're practising now.
