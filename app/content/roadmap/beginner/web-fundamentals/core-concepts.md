# Core Concepts: HTTP — Requests, Responses, and Everything Between

## 1. What You Will Learn

By the end of this lesson you should be able to:

- read a raw HTTP request and identify its method, path, headers, and body
- read a raw HTTP response and identify its status code, headers, and body
- explain what each common HTTP method conventionally means
- explain the difference between the `4xx`, `5xx`, and other status-code families, including 401 vs. 403 vs. 404
- explain why `Content-Type` matters for both requests and responses
- explain why each of these matters for the security work later in this platform

## 2. Why This Matters

HTTP is the single most important protocol in this entire platform's later curriculum. Burp Suite is, at its core, a tool for viewing and editing exactly the requests and responses this lesson teaches you to read. Every vulnerability in the OWASP Top 10 — injection, broken authentication, broken access control — expresses itself as *something wrong in an HTTP request or response*: a parameter that shouldn't be trusted, a status code that reveals too much, a header that's missing. If you can't read raw HTTP fluently, none of that later material will make sense. This lesson is that fluency.

## 3. The Request Line and the Response Line

Every HTTP message — request or response — starts with one line that tells you what kind of message it is.

**A request's first line:**

```
GET /products?id=42 HTTP/1.1
```

Three parts: the **method** (`GET` — what the client wants to do), the **target** (`/products?id=42` — the path and query string from the URL), and the **protocol version** (`HTTP/1.1`).

**A response's first line — the status line:**

```
HTTP/1.1 200 OK
```

Also three parts: the **protocol version**, the **status code** (`200` — a three-digit number), and the **reason phrase** (`OK` — a short, human-readable label for that code).

Everything else in an HTTP message — headers, then an optional body — follows the same shape whether it's a request or a response: some number of `Header-Name: value` lines, then a single blank line, then the body (if there is one). Here's a full real exchange, captured from this platform's simulated training site:

```
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

Product #42: Sample training item.
```

Hold onto this exact example — the rest of this lesson explains every line in it.

## 4. HTTP Methods

The method is the verb of a request — what the client is asking the server to *do*. Real applications don't always follow this exactly, but you should learn the conventional meaning of each one first, because that's what every framework, every API, and every security tool assumes by default:

| Method | Conventional meaning |
|---|---|
| `GET` | Retrieve a resource. Should not change anything on the server. |
| `POST` | Submit data — create something new, or trigger an action (like logging in). |
| `PUT` | Replace a resource entirely with the data provided. |
| `PATCH` | Partially update a resource — change only some fields. |
| `DELETE` | Remove a resource. |
| `HEAD` | Same as `GET`, but the server sends only headers, no body — used to check things like size or existence without downloading content. |
| `OPTIONS` | Ask the server which methods a given resource actually supports. |

**Why this distinction matters for security:** `GET` requests are conventionally *safe* — they shouldn't change server state, which is why browsers pre-fetch links and search engines crawl them freely. A `GET` request that secretly deletes something (a bug, not a feature) is a real, well-known class of vulnerability precisely because it breaks that assumption. `POST`, `PUT`, `PATCH`, and `DELETE` are the *state-changing* methods — every one of them is a request you should expect an application to check "is this user actually allowed to do this?" before acting on. You'll rely on this exact distinction when you study access-control vulnerabilities later.

## 5. Status Codes: Reading the First Digit

A status code's first digit tells you its *family* — you can often reason about a response correctly from that digit alone, even before reading anything else:

| Family | Meaning | 
|---|---|
| `1xx` | Informational — the request was received, processing continues (rare to see directly) |
| `2xx` | Success — the request was understood and handled as expected |
| `3xx` | Redirection — you need to go somewhere else to complete this |
| `4xx` | Client error — *you* (the request) did something the server won't accept |
| `5xx` | Server error — the server failed while trying to handle an otherwise valid request |

That last distinction is one of the most useful habits you can build: **a `4xx` means look at your request; a `5xx` means the problem is on the server's side, not yours.**

**The codes worth knowing by name, not just by family:**

| Code | Meaning | Notes |
|---|---|---|
| `200 OK` | Success | The default success response |
| `201 Created` | Success, and a new resource now exists | Common after a `POST` that creates something |
| `204 No Content` | Success, but there's no body to return | Common after a `DELETE` |
| `301 Moved Permanently` | This resource now lives at a new URL, permanently | Browsers and search engines update their records |
| `302 Found` | Go here instead, but only for now | The most common redirect — you'll see it below in Section 7 |
| `304 Not Modified` | You already have the current version cached — use it | Saves the server from re-sending unchanged content |
| `400 Bad Request` | The server couldn't understand the request as sent | Malformed syntax, missing required data |
| `401 Unauthorized` | You need to authenticate, and haven't | Despite the name, this is about *identity*, not permission |
| `403 Forbidden` | The server understood exactly who you are, and says no | This is about *permission*, not identity |
| `404 Not Found` | Nothing exists at this path | The single most common status code beginners recognize |
| `405 Method Not Allowed` | This path exists, but not for the method you used | E.g., `DELETE`-ing a path that only supports `GET` |
| `429 Too Many Requests` | You're being rate-limited | A direct, deliberate anti-automation/anti-abuse control |
| `500 Internal Server Error` | The server hit an unexpected failure handling your request | A `5xx` you did nothing wrong to cause |
| `502 Bad Gateway` | A server acting as a proxy got an invalid response from the server behind it | Common in multi-server architectures |
| `503 Service Unavailable` | The server is temporarily unable to handle requests | Overload, maintenance, etc. |

**401 vs. 403 vs. 404 — the distinction that matters most for security work.** These three get confused constantly, so compare them directly using this platform's real training site. Requesting `/admin` while logged out:

```
GET /admin HTTP/1.1
Host: cybershop.training

HTTP/1.1 401 Unauthorized
Content-Type: text/plain

You must log in to view this page.
```

The server has no idea who you are yet — `401` means "authenticate first." Now the *same* request, logged in as an ordinary student account:

```
GET /admin HTTP/1.1
Host: cybershop.training
Cookie: session_id=student-session

HTTP/1.1 403 Forbidden
Content-Type: application/json

{"error": "Forbidden", "message": "You are authenticated, but not authorized to access this resource."}
```

Same path, same server — but now the server knows *exactly* who's asking, and the answer is still no. That's the whole distinction: **401 means "I don't know who you are"; 403 means "I know exactly who you are, and the answer is no."** `404`, by contrast, says nothing about identity or permission at all — it claims the resource doesn't exist. (Some applications deliberately return `404` instead of `403` for a resource a user isn't allowed to know exists — worth remembering, but that's a defensive *choice*, not what `404` inherently means.)

## 6. Headers: What They Communicate

A header is one line of metadata about the message it belongs to — not part of the actual content, but information *about* that content or about the two parties talking. You saw several already in Section 3's example. A handful matter enough to name individually:

**Request headers:**

| Header | Communicates |
|---|---|
| `Host` | Which website, on this server, the request is for — required on every request since one server can host many sites |
| `User-Agent` | What client is making the request (browser, script, tool) |
| `Accept` | What response content types the client can handle |
| `Content-Type` | The format of the request *body*, when there is one (Section 7) |
| `Authorization` | Credentials proving who's making the request — covered fully in Hands-on Practice |
| `Cookie` | Data the browser is sending back that the server previously asked it to store (also Hands-on Practice) |
| `Referer` | The URL of the page that linked to this request, if any |
| `Origin` | Which site's page initiated this request — a security-relevant cousin of `Referer` |

**Response headers:**

| Header | Communicates |
|---|---|
| `Content-Type` | The format of the response body (Section 8) |
| `Content-Length` | How many bytes the body contains |
| `Set-Cookie` | Data the server wants the browser to store and send back later (Hands-on Practice) |
| `Cache-Control` | How long, and under what conditions, this response can be reused without asking again |
| `Content-Security-Policy` | A security control telling the browser what content sources it's allowed to trust |
| `Strict-Transport-Security` | Tells the browser to only ever use HTTPS for this site, never plain HTTP |
| `X-Content-Type-Options` | Tells the browser not to guess a different content type than what was declared |

You don't need to memorize this table — you need to recognize, when you see one of these in a real exchange, *what question it's answering*. Every header is metadata answering a specific question ("what format is this body in?", "who sent this?", "how long can this be cached?") — that habit of asking "what question does this header answer" will make an unfamiliar header in a real Burp Suite capture far less intimidating later.

## 7. Request Bodies: Forms and JSON

`GET` requests conventionally have no body — everything they need to say is in the URL. `POST`, `PUT`, and `PATCH` usually *do* carry one: the actual data being submitted. When there's a body, `Content-Type` tells the server how to parse it — get this wrong and the server can't understand data that's otherwise perfectly correct.

**Form submission (`application/x-www-form-urlencoded`)** — the classic HTML-form format, `key=value` pairs joined by `&`:

```
POST /login HTTP/1.1
Host: cybershop.training
Content-Type: application/x-www-form-urlencoded
Content-Length: 37

username=student&password=training123
```

**JSON (`application/json`)** — a structured, nested format, common for APIs:

```
POST /api/login HTTP/1.1
Host: cybershop.training
Content-Type: application/json
Content-Length: 50

{"username": "student", "password": "training123"}
```

Both requests carry logically the same information — a username and a password — in two different wire formats. `Content-Type` is what tells the server which one it's looking at; an application built to expect JSON that receives form-encoded data (or the reverse) generally can't parse it correctly, regardless of whether the data itself is valid.

## 8. Response Bodies: Not Always HTML

A response body can be any format `Content-Type` declares — HTML is common, but far from the only option. An API endpoint on the same server can return structured data instead of a page:

```
GET /api/me HTTP/1.1
Host: cybershop.training
Authorization: Bearer training-token-001

HTTP/1.1 200 OK
Content-Type: application/json

{"username": "student"}
```

Nothing about this exchange looks like a webpage — no HTML tags, nothing to render visually — and that's the point: this response isn't meant for a human to read directly, it's meant for a program (often JavaScript running in a browser) to parse and use. You'll see this pattern constantly in this platform's later API-security content: the same server, the same protocol, the same status codes and headers you just learned — just a different body format on the other end.

## 9. Common Mistakes

**Assuming the method name guarantees the behavior.** `GET` is *conventionally* safe and non-destructive, but nothing in HTTP itself enforces that — a poorly built application can absolutely make a `GET` request delete data. Convention isn't a guarantee, which is exactly why security testers check state-changing behavior on every method, not just the ones that are "supposed to" cause it.

**Treating 401 and 403 as interchangeable "access denied" codes.** They answer two completely different questions — "do I know who you are?" vs. "do I permit what you're asking?" — and confusing them will actively mislead you when you're debugging or testing access control later.

**Forgetting that `Content-Type` describes the body, not the endpoint.** The same URL path can often accept either form data or JSON, depending entirely on what `Content-Type` the request declares — the header, not the path, is what determines how the body gets parsed.

**Assuming a response body is always HTML.** APIs, images, and other formats are all equally valid response bodies — always check `Content-Type` before assuming what you're looking at.

## 10. Practice

**Exercise 1 — Guided.** Given this response's first line — `HTTP/1.1 404 Not Found` — state the status code, its family, and what that family generally means.

**Exercise 2 — Independent.** You send `POST /api/profile` with a JSON body, but you forgot to set `Content-Type: application/json`. Using what Section 7 taught you, explain why the server might fail to parse your data correctly even though the JSON itself is perfectly valid.

**Exercise 3 — Reasoning.** A request to `/settings` returns `403 Forbidden`. A different request, to `/settings-old`, returns `404 Not Found`. Using Section 5's distinction, what does each response tell you — and which one, if either, confirms that `/settings-old` doesn't exist at all versus simply not being disclosed?

**Challenge.** Using this platform's terminal, run `open https://cybershop.training/does-not-exist`, then `headers`. Identify the status code, and name at least two response headers present even on a `404`.

## 11. Knowledge Check

1. What are the three parts of a request's first line? Of a response's status line?
2. Name three HTTP methods and their conventional meanings.
3. What is the practical difference between a `401` and a `403` response?
4. Why does `Content-Type` matter for a request body?
5. Give an example of a response body that is *not* HTML, and explain what typically consumes it.

## 12. Key Takeaways

- Every HTTP message starts with one line (request line or status line) followed by headers, a blank line, and an optional body — request and response share this exact shape.
- HTTP methods have conventional meanings (`GET` = retrieve, `POST`/`PUT`/`PATCH`/`DELETE` = state-changing) that security tooling assumes, even though nothing in the protocol enforces them.
- A status code's first digit tells you its family; `401` means unauthenticated, `403` means authenticated-but-forbidden, and `404` claims the resource doesn't exist at all — three genuinely different answers.
- `Content-Type` determines how a body (request or response) is parsed — form-encoded and JSON are the two you'll see constantly.
- A response body isn't necessarily HTML — APIs commonly return JSON, meant for a program to consume rather than a human to read directly.

## 13. What's Next

**Hands-on Practice** puts this vocabulary to work: cookies and sessions (how a stateless protocol tracks a logged-in user), the difference between authentication and authorization made concrete, a real look at API request/response pairs, HTTPS explained conceptually, and hands-on time making and inspecting real requests in this platform's terminal.
