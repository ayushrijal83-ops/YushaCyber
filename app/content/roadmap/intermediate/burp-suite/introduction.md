# Introduction to Burp Suite and the HTTP Testing Workflow

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what an **intercepting proxy** is, and what problem it solves that a browser alone cannot
- describe the path a request takes: browser → proxy → server → response → proxy → browser
- read an HTTP request out loud: method, path, version, headers, blank line, body
- read an HTTP response out loud: status line, headers, blank line, body
- explain what **intercept**, **forward** and **drop** each do, and when each is the right choice
- explain why **HTTP history** is stronger evidence than what the page looked like
- state the authorization boundary for proxy testing precisely enough to apply it
- describe what Burp Suite actually is — and what it is not

## 2. Why This Matters

Web Fundamentals taught you what an HTTP request *is*. Wireshark taught you to observe traffic you did not create and reason about it as evidence. This module closes the loop: it teaches you to **see the exact request your browser sent, and to send a deliberately different one**.

That second half is the whole point, and it is worth being precise about how big a change it is:

> **Wireshark:** what is actually happening on this network?
> **Burp:** what happens if I send *this* request instead?

Wireshark is read-only by nature. You watch, you decode, you conclude. An intercepting proxy adds an ability that changes what questions you can ask: you can hold a request in mid-flight, alter it, release it, and observe the consequence. That turns HTTP from something you *watch* into something you can *experiment on*.

Everything a web application does for a user happens through requests and responses. Login, adding to a cart, viewing an order, updating a profile, loading a dashboard — every one of them is an HTTP request the browser constructed on your behalf, and a response the server sent back. If you can see those requests, you can see what the application actually does. If you can modify them safely and in an authorized environment, you can find out what the server does when the input is not what the interface intended to send.

That is the skill this module builds. Not "how to click around Burp." How to **form a question about an application, express that question as a request, send it, and read the answer honestly.**

## 3. The Authorization Boundary — Read This First

An intercepting proxy sits between a client and a server and can read and alter everything that passes through it. That capability is exactly why the boundary has to be stated before any technique.

**Interception is authorized only against systems you own or have explicit written permission to test.** That's not a courtesy convention; in most jurisdictions unauthorized interception and unauthorized modification of traffic to a system you don't control are criminal offences, entirely independent of whether any harm resulted.

What that means in practice:

| Allowed | Not allowed |
|---|---|
| Your own application on your own machine | Any site you happen to be browsing |
| A deliberately vulnerable training app you installed | A company's site because it "looked insecure" |
| This platform's simulated CyberShop environment | A friend's account "just to show them" |
| A client system inside a signed engagement scope | Anything outside that scope, even the same company |
| A bug-bounty target, inside its published scope rules | A target whose programme excludes that asset |

Two boundaries people get wrong even when they mean well:

**"I only looked, I didn't change anything"** is not a defence. Interception is the act being regulated, not damage.

**"It's my own account"** does not authorize the *system*. Your account is yours; the server is not. Testing what the server does with your account's requests is still testing someone else's system.

**On this platform**, every request you will make in this module goes to a simulated site (`cybershop.training`) that exists entirely as Python data structures inside YushaCyber. No real network request is ever made — the simulator has no HTTP client in it at all, and it rejects any host but its own. When you finish this module and want to practise further, use a deliberately vulnerable application you have installed yourself (OWASP Juice Shop, DVWA, PortSwigger's own Web Security Academy labs) — never a live site you don't own.

This is the last time this lesson repeats the boundary. It applies permanently.

## 4. What Burp Suite Actually Is

**Burp Suite** is a toolkit for testing web application security, made by PortSwigger. Its core is an **intercepting HTTP proxy**: you configure your browser to send its traffic through Burp instead of straight to the network, and Burp records, displays, and — if you tell it to — pauses that traffic so you can examine or change it before it continues.

Around that core sit several tools. The ones that matter for this module:

| Tool | What it does |
|---|---|
| **Proxy** | Sits between browser and server; records traffic, optionally pauses it for editing |
| **HTTP history** | The log of every request/response that passed through the proxy |
| **Repeater** | Send one request manually, edit it, send again, compare responses |
| **Intruder** | Automate sending many variations of one request |
| **Decoder / Comparer** | Encode/decode values; diff two responses |
| **Scanner** | Automated vulnerability scanning (Professional edition only) |

Burp ships in editions — a free Community edition and paid Professional/Enterprise editions. The differences matter practically: Community has Proxy, Repeater, Intruder (rate-limited) and Decoder, but no Scanner. Everything this module teaches is manual work that Community can do.

**And here is the correction to make now, before it sets wrong:**

> **WRONG:** "Burp is a vulnerability scanner. You point it at a site and it finds the bugs."
>
> **CORRECT:** Burp is primarily a toolkit for *observing and manually testing* HTTP traffic. Some editions add automated scanning, but the scanner is one feature among many — and the findings that matter most in professional testing are usually the ones a scanner cannot reach: authorization flaws, business-logic errors, and anything that requires understanding what the application is *for*.

A scanner can tell you a parameter reflects input. Only a person who understands the application can tell you that user A being able to read user B's invoice is a serious problem. Burp is the instrument that lets a person ask that question precisely.

## 5. What a Proxy Is

A **proxy** is an intermediary that sits between a client and a server and relays traffic between them.

Without a proxy:

```
BROWSER  ─────────────────────────────────►  SERVER
         ◄─────────────────────────────────
```

With an intercepting proxy configured:

```
BROWSER  ────►  PROXY  ────►  SERVER
                  │
         ◄────────┴──────◄────
```

The browser thinks it is talking to the server. The server sees a request arriving. In between, the proxy has the complete request in a readable form and can:

- **record** it (always, into HTTP history),
- **display** it (so you can read what was actually sent, not what you assume was sent),
- **pause** it before forwarding (interception),
- **modify** it before forwarding,
- **drop** it so it never arrives at all.

The same applies in the other direction for responses.

Notice what a proxy is *not*: it is not an attack, not an exploit, and not inherently adversarial. Proxies are ordinary infrastructure — corporate networks, CDNs, load balancers and caches are all proxies. What makes Burp a *testing* proxy is that it hands the controls to you instead of applying a fixed policy.

**One honest note about HTTPS.** Nearly all real traffic is encrypted with TLS. A proxy that only relayed bytes would see ciphertext and nothing more.

> **WRONG:** "Burp just sees inside HTTPS automatically."
>
> **CORRECT:** HTTPS traffic is encrypted between client and server. To read it, Burp terminates the TLS connection itself and creates a second one onward to the server — which means your browser must be configured to trust Burp's own CA certificate, a step you perform deliberately on your own machine. Without that setup, the browser refuses the connection and shows a certificate warning, exactly as it should. Decryption isn't a magic property of the tool; it is a trust decision you make explicitly, on a machine you control.

That detail matters beyond trivia: it is *why* proxying someone else's traffic is not something you can quietly do. It requires a change on the client machine.

## 6. The Mental Model

Everything in this module is one step of this chain. Learn its shape now; Core Concepts and Hands-on Practice walk it repeatedly.

```
BROWSER              a user action produces a request
  ↓
HTTP REQUEST         method, path, headers, body — the real thing sent
  ↓
BURP PROXY           records it; optionally pauses it
  ↓
INSPECT              read exactly what the client sent
  ↓
MODIFY (if authorized) change one thing, deliberately
  ↓
FORWARD              release it to the server
  ↓
SERVER               the application processes the request
  ↓
RESPONSE             status, headers, body — the real answer
  ↓
OBSERVE              read the response; note what differs
  ↓
HYPOTHESIS           "the server appears to behave like X"
  ↓
TEST SAFELY          one more controlled request that would distinguish X from not-X
  ↓
COMPARE EVIDENCE     what actually changed between the two exchanges?
  ↓
DOCUMENT             observation, interpretation, confidence — kept separate
```

The step beginners skip is **INSPECT**. It is tempting to change something immediately and see what happens. But if you don't know precisely what the original request contained, you cannot say what your change actually changed — and an experiment with an unknown starting point produces no evidence at all.

## 7. Anatomy of an HTTP Request

You met this in Web Fundamentals. Here it is again, this time as something you will read dozens of times.

```
METHOD  PATH[?QUERY]  HTTP-VERSION      ← request line
Header-Name: value                      ← headers, one per line
Header-Name: value
                                        ← blank line (mandatory separator)
body                                    ← body, only for requests that have one
```

Four parts, and the blank line matters: it is what tells the server the headers have ended and any body begins.

Here is a real request, captured by this platform's proxy simulator inside the **Burp Suite Fundamentals** mission. This is actual output, not an illustration:

```
$ open https://cybershop.training/products?id=42
━━━━━━━━ REQUEST ━━━━━━━━
GET /products?id=42 HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*
```

Read it aloud, part by part:

- **`GET`** — the method. What kind of operation is being asked for. `GET` asks to retrieve something.
- **`/products`** — the path. Which resource on the server.
- **`?id=42`** — the query string. One parameter, named `id`, with the value `42`. This is *client-supplied input*, and it is the single most important thing on the line for a tester.
- **`HTTP/1.1`** — the protocol version.
- **`Host: cybershop.training`** — which site this request is for. Required in HTTP/1.1, because one server can host many sites.
- **`User-Agent: ...`** — the client identifying itself. Purely a claim; the client chooses what to put here.
- **`Accept: */*`** — what content types the client will accept back.
- No blank-line-plus-body, because this `GET` has no body.

And here is a request that *does* have a body — the login POST from the same environment:

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
```

Two new headers appear, and both exist *because* there is a body: `Content-Type` says how the body is encoded, and `Content-Length` says how many bytes it is. Then the blank line, then the body itself — which here carries the two form fields the login page collected.

`student` / `training123` are fixed, fictional training credentials built into the simulator. They are not a real account anywhere.

**Where client input lives.** Notice that the two requests above put input in two different places: a query parameter in the URL, and form fields in the body. Core Concepts catalogues all six places input can hide. For now, just register the idea: *input is not always in the URL.*

## 8. Anatomy of an HTTP Response

The response has the same shape with a different first line:

```
HTTP-VERSION  STATUS-CODE  REASON        ← status line
Header-Name: value                       ← headers
                                         ← blank line
body                                     ← body
```

The real response to that first request:

```
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

- **`200 OK`** — the status. The request succeeded.
- **`Content-Type: text/html`** — how to interpret the body.
- **`Content-Length: 34`** — the body's size in bytes. Worth noticing every time: response *length* is often the fastest way to spot that two responses differ.
- **`Server: CyberShop-Sim/1.0`** — the server identifying itself. Like `User-Agent`, this is a claim, and a real server disclosing its exact product and version is a small information leak.
- **`ETag: "product-42-v1"`** — a cache identifier for this specific version of this specific resource. Note that it contains the id we asked for. That will matter shortly.
- **`Content-Security-Policy`** — a security header, telling the browser what it may load and execute.
- Blank line, then the body: the actual content.

**Both halves are evidence.** Beginners read the body and ignore the headers. In security testing the headers frequently carry the finding — a cookie being set, a redirect target, a cache directive, a missing protection, a leaked version.

## 9. Interception: Holding a Request in Flight

Interception means the proxy **stops** a request before forwarding it, and waits for you.

```
BROWSER ──►  PROXY  ✋ HELD                SERVER
                    │
                    ├─ read it
                    ├─ change it (if authorized)
                    │
                    ├─ forward ──────────► SERVER
                    └─ drop ─────────────► (never arrives)
```

Three things you can do with a held request:

- **Forward** — send it on. Unmodified, this is exactly what would have happened anyway.
- **Modify, then forward** — send a deliberately different request than the browser composed.
- **Drop** — discard it. It never reaches the server; the browser sees a failed request.

Here is interception, real, from the same environment. Intercept is off by default, so first it is turned on:

```
$ intercept on
Intercept is now ON. Your next request will be held before it reaches the server.
```

Now the same request as before is made — and instead of a response, the request is held:

```
$ open https://cybershop.training/products?id=42
Request intercepted:
GET /products?id=42 HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

Use 'forward', 'drop', or 'edit <field> ...' before it reaches the server.
```

Nothing has reached the server yet. The request exists, fully formed, waiting. Releasing it:

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

The response is identical to the un-intercepted one, because nothing was changed. **That is the correct baseline behaviour and it is worth doing deliberately at least once:** intercept, forward untouched, confirm the result matches. Now you know the proxy itself isn't altering your experiment.

Dropping instead:

```
$ drop
Request dropped. It never reached the simulated server.
```

**Interception is not an attack.** It is a pause button on your own traffic. What you do next may be ordinary inspection, or a deliberate test — the pause itself is neutral.

**A practical note real Burp users learn quickly:** leaving intercept on while browsing is exhausting, because *every* request stops — including the dozens of images, stylesheets and API calls a modern page fires. Most real work is done with intercept **off**, reading HTTP history afterwards, and intercept turned on only for the specific request you intend to catch.

## 10. HTTP History: What the Browser Actually Did

Everything that passes through the proxy is logged. That log is the single most useful thing in Burp for a beginner, and the reason is worth stating plainly:

> **The page is what the application chose to show you. The HTTP history is what actually crossed the wire.**

A page can look completely normal while the browser is quietly firing requests to endpoints no link mentions. It can show "Saved!" when the server returned an error. It can hide a button that the underlying endpoint still happily serves. None of that is visible in the interface. All of it is visible in the history.

Here is a real history from a session in the training environment:

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
```

Read that list as a story, because that is exactly what it is:

- Three product requests, all `200`.
- `/account` returned **302 Found** — a redirect. Something was refused, politely.
- A login POST, also `302`.
- `/account` again, this time **200**. Whatever the login did, it changed the outcome of an identical request.
- `/admin` returned **403 Forbidden**.
- A logout, then `/admin` again — now **401 Unauthorized**, a *different* code for the same URL.
- Another login, and `/admin` now returns **200**.

You can reconstruct that entire session — who was logged in, when, and what they were allowed to do — from eleven summary lines. That is the value of history.

**Read the summary honestly, though.** Notice entries #1, #2 and #3 all read `GET /products`, yet they were not identical requests: the history line shows method, path and status, and omits the query string. The summary line is an index, not the evidence. When something matters, open the full request and response.

That is a general discipline, not a quirk of this platform: **the summary tells you where to look; the full exchange is what you cite.**

## 11. This Platform's Proxy Environment

The exercises in this module run inside the **Burp Suite Fundamentals** terminal mission on this platform. It is a *simulated* Burp-style proxy — a command-driven version of the same workflow, against a fixed fictional site called CyberShop (`cybershop.training`). No real Burp Suite is installed, and no real network request is ever made.

That trade is deliberate, and it is worth knowing exactly what it costs and buys. What it costs: no GUI, no clicking, no certificate setup, no Intruder or Scanner. What it buys: the environment is identical every time, so a conclusion you draw today is still checkable tomorrow, and nothing you type can ever reach a real system.

The commands you will use:

| Command | Purpose |
|---|---|
| `web` | Show the simulated site, your login status, and its routes |
| `proxy` | Show proxy status: intercept on/off, and the scope |
| `open URL` | Make a request (add `-X METHOD`, `-H "Header: value"`, `-d DATA`) |
| `intercept on` / `off` | Turn interception on or off |
| `forward` | Release the held request to the server |
| `drop` | Discard the held request |
| `edit query\|header\|body\|method\|path ...` | Modify the held (or Repeater-loaded) request |
| `requests` | List the HTTP history |
| `inspect` | Show the full last request and response |
| `headers` | Show request and response headers |
| `cookies` | Show the cookies your simulated browser holds |
| `response` | Show the last response on its own |
| `repeater [N]` / `repeater send` | Load a history entry into Repeater / send it |
| `compare N M` | Diff two responses from history |

Here is what the proxy reports about itself:

```
$ proxy
Browser --> Proxy --> Server
Intercept: OFF
Scope: cybershop.training
Requests outside scope are never proxied — they're rejected before a request object even exists.
```

**Scope** is that last line, and it is the authorization boundary of §3 expressed as a technical control. Real Burp has a scope setting too, and configuring it correctly is part of professional discipline — it stops you accidentally proxying traffic to systems outside your engagement. Here, the scope is enforced absolutely:

```
$ open https://evil.example.com/
External hosts are not available in the training environment.
```

No request object is even constructed. There is nothing in this module that can reach outside the simulation.

## 12. Practice — Reading Evidence

These five exercises use output already shown in this lesson. Write your answers down before reading the discussion; the discussion is much less useful if you've only skimmed the question.

### Exercise 1 — Identify the request

Look again at §7's first request block.

1. What is the method?
2. What is the path?
3. What is the query string, and how many parameters does it contain?
4. Which line tells the server which *site* is being requested, and why is that necessary?
5. Does this request have a body? How can you tell without being told?

<details>
<summary>Discussion</summary>

Method `GET`; path `/products`; query string `?id=42`, one parameter named `id` with value `42`; `Host: cybershop.training` identifies the site, necessary because one server may host many sites on one IP address.

No body — and you can tell structurally, in two independent ways: there is no blank line followed by content, and there is no `Content-Length` header. Compare with the POST in the same section, which has both. Answering "because GET requests never have bodies" is the weaker answer: it's a convention, not a rule, and reading the structure is what generalises.
</details>

### Exercise 2 — Method, path, headers, body

Look at §7's POST request block.

1. What is the method and path?
2. How many headers are there, and what does each one do?
3. What is in the body, and what format is it in?
4. Which two headers exist *because* the body exists?
5. Name every piece of client-controlled input in this request.

<details>
<summary>Discussion</summary>

`POST /auth/login`. Five headers: `Host` (which site), `User-Agent` (client's self-description), `Accept` (acceptable response types), `Content-Type` (body encoding — `application/x-www-form-urlencoded`, i.e. `key=value&key=value`), `Content-Length` (37 bytes).

Body: `username=student&password=training123` — two form fields.

`Content-Type` and `Content-Length` exist because of the body.

Client-controlled input is the interesting question, and the answer is broader than most people expect: the path, the two body fields, *and every header*. `User-Agent` is not a fact about the client — it is a string the client chose. Anything the client sends, the client can change. Which is precisely why a server must never trust it.
</details>

### Exercise 3 — Read the response

Look at §8's response.

1. What is the status code and what does it mean?
2. How large is the body?
3. Which header would reveal the server software, and why might that matter?
4. What does the `ETag` value contain that connects it to the request?
5. Which header is a security control rather than a description of the content?

<details>
<summary>Discussion</summary>

`200 OK` — the request succeeded. Body is 34 bytes (`Content-Length: 34`). `Server: CyberShop-Sim/1.0` discloses product and version — on a real server that helps an attacker match known vulnerabilities to your exact build, which is why production systems often suppress it.

`ETag: "product-42-v1"` contains **42** — the same value that was supplied as `id` in the request's query string. The server built the cache identifier from client input. That's an observation, not a finding, but it's the kind of detail worth registering.

`Content-Security-Policy` is the security control; it restricts what the browser is permitted to load and execute.
</details>

### Exercise 4 — What changed between two requests?

In §10's history, entries #7, #9 and #11 are all `GET /admin`. They returned `403 Forbidden`, `401 Unauthorized`, and `200 OK` respectively.

1. The URL is identical in all three. So what changed?
2. What happened between #7 and #9 that would explain the change?
3. What happened between #9 and #11?
4. What does this tell you about where the difference lives — in the request, or in the server?

<details>
<summary>Discussion</summary>

The URL didn't change; the **identity attached to the request** did. Between #7 and #9 there is a `POST /logout` (#8) — after logging out, the request carries no valid session, so the server no longer knows who is asking. Between #9 and #11 there is a `POST /auth/login` (#10) — a different login, evidently as a user permitted to see `/admin`.

Where does the difference live? Both. The *request* differed (a session cookie present or absent, representing a different user), and the *server* made a different decision as a result. Neither alone explains it — and separating "what did I send?" from "what did the server decide?" is the core analytical habit of this whole module.

Core Concepts takes the 401-vs-403 distinction apart properly, with the real responses.
</details>

### Exercise 5 — Why is a request evidence?

A colleague says: "I clicked Save and the page said 'Profile updated', so the update worked."

1. What exactly has that observed?
2. What has it *not* observed?
3. What would you look at in HTTP history to check the claim?
4. Design the smallest follow-up request that would settle it.

<details>
<summary>Discussion</summary>

It observed that **the interface displayed a success message**. It did not observe that the server accepted the change, stored it, or that the stored value is what was typed. A message rendered in a browser is a statement made by the application, not proof of what happened behind it.

In history: find the save request; read its full body (what was actually sent); read the response status *and body* (what the server actually said).

The settling test is a fresh `GET` of the same resource, read back and compared to what you submitted. This is not a hypothetical — Hands-on Practice §10 investigates a real case in this platform's environment where the server answers `200 OK` with `"status": "updated"` and the value does not change. "Status code 200" and "the thing I wanted happened" are two different claims, and a very large number of real bugs live in the gap between them.
</details>

## 13. Common Misconceptions

**"Burp is a vulnerability scanner."** Burp is a toolkit for observing and manually testing HTTP traffic, with automated scanning available depending on edition. The manual tools are where the judgement lives.

**"Using a proxy means you're attacking something."** A proxy relays traffic. Corporate networks, CDNs and caches are all proxies. Interception is a capability; whether its use is legitimate depends entirely on authorization.

**"Intercept should always be on."** Intercept on means *every* request stops, including all the automatic ones a page fires. Most real work runs with intercept off and reads history afterwards.

**"Burp sees inside HTTPS automatically."** It requires deliberate setup — your browser must trust Burp's CA certificate, a change you make on a machine you control. That's why proxying someone else's traffic isn't quietly possible.

**"The history line is the evidence."** The history line is a summary: method, path, status. Three entries reading `GET /products` in §10 were three different requests. The full exchange is the evidence.

**"If the browser sent it, it must be correct."** The browser sends what the application's code told it to send. That code can be wrong, and testing what happens when the request is *not* what the interface intended is exactly the point.

## 14. Knowledge Check

1. What problem does an intercepting proxy solve that reading a web page cannot?
2. Draw the path of a request through a proxy and back, labelling every point where the tester can act.
3. Name the four structural parts of an HTTP request. What is the blank line for?
4. Given a request with no `Content-Length` header and no blank line, what can you conclude?
5. Why is `User-Agent` untrustworthy as a statement about the client?
6. What are the three things you can do with an intercepted request, and when would you choose each?
7. Why is HTTP history more reliable evidence than what the page displayed?
8. Why did three entries in §10's history all read `GET /products` despite being different requests, and what does that teach you about summaries?
9. Explain in your own words why proxy scope exists, in both this simulator and real Burp.
10. Two responses to identical URLs differ only in status code. Name three things that could account for the difference.
11. Why is "I only intercepted, I didn't change anything" not an authorization defence?
12. Someone says Burp will "find the vulnerabilities" in an app. What's wrong with that expectation, and what would you say instead?

## 15. Key Takeaways

- An intercepting proxy sits between browser and server, and lets you **see, pause, modify, forward or drop** the traffic your own client produces.
- Authorization comes first, permanently. Interception is only legitimate against systems you own or are explicitly permitted to test.
- Every HTTP request has four parts: request line, headers, blank line, body. Every response has status line, headers, blank line, body. Read all four, every time.
- Client-controlled input is not just the URL — it includes the body and *every header*. Anything the client sends, the client can change.
- Both halves of a response are evidence. The headers frequently carry the finding.
- HTTP history is what actually crossed the wire; the page is what the application chose to show. When they disagree, the history is right.
- The history summary line is an index, not the evidence. Open the full exchange before you cite it.
- Intercept, then forward unmodified at least once, to confirm your baseline before running any experiment.
- Burp is an instrument for asking precise questions about an application. It is not a machine that produces findings without you.

## 16. What's Next

**Core Concepts** takes each piece apart properly: the Proxy and HTTP history workflow, Repeater and the one-variable-at-a-time discipline, the six places parameters hide, cookies and sessions, the difference between authentication and authorization with the real 401/403/200 responses, and how to compare two responses so the comparison actually means something.

**Hands-on Practice** then puts you in the environment for six exercises, ending with a real investigation and a written, evidence-based finding.

The tool is a means. What you're actually building is the habit of turning a question about an application into a request, sending it deliberately, and reading the answer without deciding in advance what it says.
