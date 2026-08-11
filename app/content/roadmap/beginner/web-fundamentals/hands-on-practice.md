# Hands-on Practice: Cookies, Sessions, Auth, and APIs

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain why HTTP needs cookies at all, and trace the Set-Cookie → Cookie flow yourself
- explain the difference between authentication and authorization, using real evidence, not just definitions
- explain what HTTPS actually protects, and what it doesn't
- read and make a JSON API request, including token-based authentication
- explain why security decisions must be enforced server-side, not client-side
- use this platform's terminal to make requests and inspect headers, cookies, and responses yourself

## 2. Why This Matters

Core Concepts gave you the vocabulary — methods, status codes, headers, bodies. This lesson is where that vocabulary explains *behavior* you already take for granted: why a website remembers you're logged in, why some pages let you in and others don't even though you're logged in either way, and why "hiding" something in a browser is never the same as actually protecting it. Session hijacking, broken authentication, and broken access control — three entries in the OWASP Top 10 you'll study later — are all failures of exactly the concepts this lesson makes concrete.

## 3. The Problem: HTTP Doesn't Remember You

Here's something worth sitting with: **HTTP, by itself, is stateless.** Every request is handled as if it's the very first one the server has ever seen from you — nothing about a previous request is automatically remembered. That's a real design property of the protocol, not a bug, and it creates a genuine problem: how does a website keep you "logged in" across multiple page loads, if every single request arrives with no memory of the last one?

The answer is **cookies** — and the flow is worth tracing exactly.

## 4. Cookies: Set-Cookie and Cookie

When you log in successfully, the server's response includes a `Set-Cookie` header — an instruction to your browser: "store this, and send it back to me on every future request." Here's a real login exchange from this platform's training site:

```
POST /login HTTP/1.1
Host: cybershop.training
Content-Type: application/x-www-form-urlencoded

username=student&password=training123

HTTP/1.1 302 Found
Location: /profile
Set-Cookie: session_id=student-session
```

That `Set-Cookie: session_id=student-session` line is the entire mechanism. Your browser stores `session_id=student-session` and, from now on, automatically attaches it to every request it sends to this same site — you never type it again, and you (mostly) never even see it happen. Watch it appear on the very next request:

```
GET /profile HTTP/1.1
Host: cybershop.training
Cookie: session_id=student-session

HTTP/1.1 200 OK
Content-Type: text/html

Profile: student
```

That `Cookie: session_id=student-session` line is your browser honoring the server's earlier instruction. Compare this with the exact same request sent *without* the cookie:

```
GET /profile HTTP/1.1
Host: cybershop.training

HTTP/1.1 401 Unauthorized

You must log in to view this page.
```

Same path, same method — the only difference is one header, and it's the difference between "here's your profile" and "you must log in." This is the entire session mechanism, made visible: **the cookie is what turns a stateless protocol into something that feels stateful.**

**Security attributes, briefly — what each one actually changes:**

| Attribute | What it changes |
|---|---|
| `Secure` | The browser will only ever send this cookie over HTTPS, never plain HTTP — stops it leaking over an unencrypted connection |
| `HttpOnly` | Client-side JavaScript cannot read this cookie at all — only the browser's own request-sending logic can — closing off an entire class of theft via injected script |
| `SameSite` | Controls whether this cookie gets attached to requests originating from a *different* site — the direct defense against the CSRF attacks you'll study later |

None of these change *what* the cookie contains — they change *when and how* the browser is willing to send it, which is exactly why each one closes off a specific, different way a cookie could otherwise be misused.

## 5. Sessions: The Model Behind the Cookie

Put the whole flow together, and you have the standard session model used across the vast majority of the web:

```
Login (username + password)
    ↓
Server verifies credentials, creates a session record
    ↓
Server sends the session identifier to the browser (Set-Cookie)
    ↓
Browser stores it, sends it automatically on every future request (Cookie)
    ↓
Server looks up the session identifier on each request, knows who you are
```

Notice what the cookie actually *is*, structurally: just an identifier — a lookup key the server uses to find your session record. The real "you are logged in as student" fact lives on the server, not inside the cookie itself. This is exactly why, later in this platform, you'll learn that a stolen session identifier is just as good to an attacker as stolen credentials — the server can't tell the difference between "the real student" and "someone holding student's session identifier," because the identifier *is* what the server checks.

## 6. Authentication vs. Authorization

These two words get used almost interchangeably in casual conversation, and conflating them is one of the most common — and most consequential — mistakes in web security.

**Authentication answers: "Who are you?"** Logging in with a username and password is authentication — it establishes your identity.

**Authorization answers: "What are you allowed to do?"** Being logged in doesn't mean you're allowed to do *everything* — a logged-in ordinary user and a logged-in administrator are both authenticated, but not equally authorized.

Recall the exact pair of responses from Core Concepts, and read them again through this lens. Requesting `/admin` while logged out:

```
GET /admin HTTP/1.1

HTTP/1.1 401 Unauthorized
```

The server doesn't know who's asking — an **authentication** failure. Now the same request, logged in as an ordinary training account:

```
GET /admin HTTP/1.1
Cookie: session_id=student-session

HTTP/1.1 403 Forbidden

{"error": "Forbidden", "message": "You are authenticated, but not authorized to access this resource."}
```

The response says it almost word for word: authenticated, but not authorized. **Logged in as a student does not equal allowed to access the admin panel** — that's the entire distinction, demonstrated rather than defined. Every access-control vulnerability you study later in this platform is, at its core, a case where this second check either didn't happen or was implemented incorrectly.

## 7. Why Authorization Must Be Enforced Server-Side

This connects directly back to the client-side/server-side distinction from the Introduction lesson, and it's worth stating as plainly as possible: **hiding an "Admin Panel" button in the page a regular user sees does not stop that user from reaching `/admin`.** The button's visibility is a client-side, cosmetic decision — nothing about hiding an HTML element prevents a request to that URL from being sent, with or without a visible button to click. The only thing that actually protects `/admin` is the server checking, on every single request, "is this specific user actually authorized for this?" — exactly the check that produced the `403` above.

This is the practical reason security decisions live on the server: the client — the browser, and everything rendered inside it — is fully within the user's control. A user can view page source, disable JavaScript, edit form fields, or send requests a UI never intended to allow. None of that is hacking in any exotic sense; it's just using an HTTP client (which is all a browser is) directly instead of through the interface it was designed for. Server-side checks are the only checks a client can't simply route around.

## 8. APIs and JSON, Including Two Ways to Prove Who You Are

An **API endpoint** is just a URL, exactly like the ones you've been using — the only real difference is that its response is meant for a program to parse, not a human to read as a page. You've already made API-shaped requests without necessarily labeling them that way. Here's one, deliberately chosen to show something new: this platform's `/api/me` endpoint doesn't use the cookie session from Section 4 at all — it uses a completely different authentication mechanism, a **bearer token**, sent in the `Authorization` header:

```
GET /api/me HTTP/1.1
Host: cybershop.training
Authorization: Bearer training-token-001

HTTP/1.1 200 OK
Content-Type: application/json

{"username": "student"}
```

Send the exact same request with a valid *session cookie* instead of the token, and it fails:

```
GET /api/me HTTP/1.1
Host: cybershop.training
Cookie: session_id=student-session

HTTP/1.1 401 Unauthorized
Content-Type: application/json

{"status": "error", "message": "Authentication required"}
```

This is a genuinely important, easy-to-miss lesson: **"authenticated" is not one universal state — it depends entirely on which mechanism a specific endpoint checks.** Cookie-based sessions and token-based (`Authorization: Bearer ...`) authentication are two different, common schemes, and a real application can use either — or, as here, use different schemes for different parts of itself. When you later work with unfamiliar APIs, checking *which* authentication mechanism an endpoint actually expects is a real, necessary first step, not an assumption you can carry over from the last endpoint you tested.

## 9. HTTPS and TLS, Conceptually

Every request in this lesson used `https://`. Recall from the Introduction that this determines the *scheme* — whether the underlying TCP connection is wrapped in TLS encryption before any HTTP happens at all:

```
TCP connection established
    ↓
TLS negotiation — browser and server agree on encryption, and the
    server proves its identity with a certificate
    ↓
Encrypted channel now exists
    ↓
Your actual HTTP request/response travels *inside* that encrypted
    channel — invisible to anyone else on the network
```

TLS gives you three specific guarantees, worth naming individually rather than lumping together as "security": **confidentiality** (no one else on the network can read the contents of your request or response), **integrity** (no one can silently alter the data in transit without it being detectable), and **server authentication** (the certificate proves you're actually talking to the server you intended to, not an impostor).

What TLS does *not* do is worth stating just as plainly: it protects data **in transit** — between your browser and the server. It says nothing about whether the server itself is trustworthy, whether the application has a SQL injection flaw, or whether its authorization checks are correct. A perfectly encrypted connection to a vulnerable application is still a vulnerable application — this is a real, common misconception worth avoiding early, before you build a mental model where "HTTPS" quietly becomes a synonym for "safe."

## 10. Practicing With This Platform's Terminal

Everything in this lesson has been demonstrated with real request/response pairs — now make some yourself. Four commands round out your toolkit, all usable right now in the **Web Fundamentals** mission:

**`open URL`** — sends a request and shows the full request/response exchange (you've seen this throughout this lesson).

**`headers`** — shows the headers from your most recent request and response, separately.

**`cookies`** — lists every cookie your session currently holds.

**`response`** — shows just the response from your most recent request, on its own.

**Common mistake:** running `headers` or `response` before making any request at all. Both commands report on your *most recent* exchange — there has to be one first, which is exactly what `open` (or `request METHOD PATH`) is for.

## 11. Debugging Exercise: A Malformed Request

Here's a realistic scenario. You send this:

```
POST /api/login HTTP/1.1
Content-Type: application/json

{bad json
```

In many real-world APIs, this produces `400 Bad Request` — the server can't parse the body as valid JSON at all, so it rejects the request before even looking at what's inside it. This platform's simulator handles the same malformed body a little more leniently: unparseable JSON is treated as an empty body, so the request reaches the login logic with no username or password at all, and comes back `401 Unauthorized` — "missing credentials" rather than "malformed syntax." Different servers really do handle this differently, which is precisely the point: **when you see an unexpected status code, checking `Content-Type` and body syntax first is the right instinct regardless of which specific error a particular server chooses to return.**

## 12. Capstone: The Web Fundamentals Mission

Everything in this module comes together in the platform's **Web Fundamentals** terminal mission, against the same simulated CyberShop training site used throughout this lesson:

1. Open a product page and identify the scheme, host, path, and query parameter in its URL
2. Make a `GET` request and confirm the method used
3. Search the site and identify a query parameter's name and value
4. Confirm a valid page returns `200 OK`
5. Request a page that doesn't exist and confirm `404`
6. Inspect the `Host` header your own request sent
7. Inspect the `Content-Type` header the server responded with
8. Submit the login form and confirm its request `Content-Type`
9. Log in and identify the session cookie you received
10. Use that session cookie to reach your profile
11. Request the login page and identify where it redirects
12. Investigate a user-reported access problem using request/response evidence, and record your conclusion

Once you're comfortable with that, **HTTP Deep Dive** goes further on the same simulated site: JSON request/response bodies, the `Authorization` header, `Referer`, cache headers, URL-encoding, and reconstructing a multi-request investigation from history.

## 13. Knowledge Check

1. Why does HTTP need cookies at all? What problem, specifically, do they solve?
2. Trace the exact sequence: what does the server send after a successful login, and what does the browser send back on the next request?
3. A user is logged in but gets `403 Forbidden` on a page. What does that tell you — and what would `401` have told you instead?
4. Why is hiding a button in the page's HTML not a real access-control mechanism?
5. What three guarantees does TLS provide, and what does it explicitly *not* guarantee about the application behind it?

## 14. Key Takeaways

- HTTP is stateless; cookies (`Set-Cookie` from the server, `Cookie` from the browser on every later request) are what let an application recognize you across multiple requests.
- `Secure`, `HttpOnly`, and `SameSite` each restrict *when and how* a cookie is sent — they don't change what it contains.
- Authentication answers "who are you?"; authorization answers "what are you allowed to do?" — a `401` is an authentication failure, a `403` is an authorization failure, and they are never interchangeable.
- Security decisions must be enforced server-side — the client, including everything rendered in a browser, is under the user's control and can't be trusted to enforce anything on its own.
- Not every API uses the same authentication mechanism — a cookie session and a bearer token can coexist on the same server, protecting different endpoints.
- HTTPS/TLS protects data in transit (confidentiality, integrity, server authentication) — it says nothing about whether the application itself is secure.

## 15. What's Next

This is the last lesson in Web Fundamentals — you now have the HTTP vocabulary and the request/response mental model that every later web-security module in this platform assumes you already have. The roadmap's next module, **Git & GitHub**, is a shift toward developer tooling — and the Intermediate track's **Burp Suite** and **OWASP Top 10** modules pick up exactly where this one leaves off, using the same requests, responses, cookies, and status codes you just practiced reading and making yourself.
