# Introduction to Web Fundamentals

## 1. What You Will Learn

By the end of this lesson you should be able to:

- break a URL down into its parts and explain what each one does
- explain, at a high level, what happens between typing a URL and seeing a page
- connect this module to what you already know from Computer Networking (DNS, TCP)
- explain the difference between client-side and server-side, in outline
- make your first request and read a status code

## 2. Why This Matters

Every tool in the Intermediate track — Burp Suite, the OWASP Top 10, web pentesting — is a way of *inspecting* or *manipulating* the exact request/response exchange this module introduces. XSS, SQL injection, and CSRF, which you'll meet later, are all attacks that abuse specific pieces of the flow you're about to learn: a URL parameter, a request body, a cookie. You cannot understand a web attack without first understanding normal web behavior — that's the entire purpose of this module.

## 3. From Networking to the Web

Computer Networking taught you how two hosts find each other and exchange data at all: DNS resolves a name to an IP address, and TCP's handshake establishes a reliable connection between two machines. The web is what gets built *on top of* that foundation — one specific, extremely common way of using a TCP connection: to request and receive documents.

```
You type: https://example.local/products

DNS         → example.local resolves to an IP address
    ↓
TCP         → your browser opens a reliable connection to that IP
    ↓
TLS         → (if the URL is https) that connection is encrypted — Hands-on
               Practice covers what this actually protects
    ↓
HTTP        → your browser sends a request *through* that connection,
               asking for one specific thing: /products
    ↓
Response    → the server sends back data, and your browser renders it
```

Everything below the "HTTP" line in this diagram is Networking's territory — you've already studied it. Everything from "HTTP" down is this module's. Notice that DNS and TCP happen *before* a single byte of your actual request is sent — a broken web page and a broken network connection are different problems, and being able to tell them apart is a real diagnostic skill you'll use for the rest of this platform.

## 4. Anatomy of a URL

A URL (Uniform Resource Locator) is not one opaque string — it's several distinct pieces, each with its own job. Take this one apart:

```
https://example.local:443/products?id=42#reviews
└─┬─┘   └─────┬─────┘└┬┘└────┬────┘└──┬──┘└──┬──┘
scheme       host    port   path    query  fragment
```

| Part | Value here | What it does |
|---|---|---|
| **scheme** | `https` | Which protocol to use for this request — `https` means HTTP over an encrypted TLS connection; plain `http` means unencrypted |
| **host** | `example.local` | The name DNS resolves to an IP address — *this* is what the "DNS → IP address" step above actually looks up |
| **port** | `443` | Which service on that IP to connect to (Computer Networking, Core Concepts) — `443` is HTTPS's default, `80` is HTTP's, which is why you rarely see either typed explicitly |
| **path** | `/products` | Which specific resource on that server you're asking for |
| **query** | `id=42` | Extra parameters, as `key=value` pairs after a `?`, additional to `&` more pairs |
| **fragment** | `reviews` | A location *within* the page (like a heading to jump to) |

**The one distinction that matters most for everything that follows: the fragment never leaves your browser.** Scheme, host, port, path, and query are all sent to the server as part of the actual request — the server sees and can act on every one of them. The fragment is handled entirely client-side, by your browser, after the page has already loaded; the server never even knows it was there. This isn't a minor trivia point — it's the reason a fragment can never carry information the *server* needs, only information about where the *browser* should scroll to once the page is already in front of you.

## 5. Client and Server, Browser and Web Server

Two pairs of terms get used almost interchangeably, and it's worth being precise:

**Client and server** describe *roles* in a conversation — whoever initiates a request is the client, whoever receives and answers it is the server. This is the same client/server pattern from Computer Networking's introduction, applied specifically to HTTP.

**Browser and web server** are the *specific programs* that usually fill those roles on the web. Your browser (Chrome, Firefox) is the client — it builds requests and renders whatever comes back. A web server (the program, not the physical machine) is what's listening on the other end, built to understand HTTP requests and produce HTTP responses.

At its simplest, that's the whole picture: browser asks, server answers.

```
Browser  ──────  request  ─────▶  Web server
Browser  ◀─────  response ─────  Web server
```

Real applications usually add more pieces behind that web server — an application layer that decides *what* to respond with, and often a database it queries to get the data. You don't need the full picture yet; just know that "the server" in this lesson's diagrams is often really "the server, plus whatever it talks to before it can answer you." Hands-on Practice returns to this once you have the HTTP vocabulary to make it concrete.

## 6. Client-Side vs. Server-Side — the First Look

You'll meet this distinction constantly for the rest of your security career, so it's worth naming now, even briefly:

**Server-side** means code that runs on the server, before the response is ever sent to you. You never see this code — only its output.

**Client-side** means code that runs in *your* browser, after the response arrives — visible, and (this matters enormously later) fully under the *user's* control, not the server's.

The one-sentence version to hold onto: **anything that happens client-side, the person using the browser can see and change.** Core Concepts and Hands-on Practice build directly on this idea; for now, just notice that "where" a piece of logic runs is not a minor implementation detail — it's a genuine security boundary.

## 7. Making Your First Request

**What it does:** in this platform's terminal, the `open` command sends an HTTP request to a URL and shows you exactly what went out and what came back — request and response, side by side.

**Basic syntax:**

```bash
open URL
```

**Example:**

```bash
open https://cybershop.training/
```

**Expected output:**

```
━━━━━━━━ REQUEST ━━━━━━━━
GET / HTTP/1.1
Host: cybershop.training
User-Agent: YushaCyber-Trainer/1.0
Accept: */*

━━━━━━━━ RESPONSE ━━━━━━━━
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 34
Server: CyberShop-Sim/1.0
Content-Security-Policy: default-src 'self'; script-src 'self'

Welcome to CyberShop — a simulated training storefront.
```

**What the output means:** the top block is the request your `open` command actually built and sent — notice it already includes a `Host` header, even though you only typed a URL; your client fills that in automatically. The bottom block is the server's reply: `HTTP/1.1 200 OK` is the status line — `200` means the request succeeded — followed by response headers, then a blank line, then the body: the actual content the server sent back.

**Common mistake:** trying to read a request/response exchange top-to-bottom as if it were one thing. It's always two separate messages — what *you* sent, and what the server sent back — and every field belongs to one side or the other, never both. `Host` only ever appears in a request; `Server` only ever appears in a response.

**Safe exercise:** in the YushaCyber terminal, run `open` against the CyberShop training site shown above and identify the status code in the response.

## 8. Common Mistakes

**Assuming a URL is just "the address bar text," with no internal structure.** Every part of a URL — especially the query string — is information the server receives and often acts on directly. This is exactly why query parameters are one of the first things a security tester inspects.

**Confusing "the browser" with "the internet."** The browser is one program, running on your machine, that happens to be very good at sending HTTP requests and rendering HTML. It has no special powers beyond what any HTTP client can do — this matters later when you learn that tools like Burp Suite and `curl` can do everything a browser can, just without the rendering.

**Treating "client-side" as synonymous with "less important" or "less real."** Client-side code still runs, still executes, and still shapes what the user sees — it's just running somewhere the *user*, not the server, ultimately controls.

## 9. Practice

In the YushaCyber terminal:

1. Run `open https://cybershop.training/` and identify the status code.
2. Given the URL `https://cybershop.training/products?id=7`, identify the path and the query parameter without running anything — just by reading it.
3. State, in one sentence, why the fragment `#reviews` in `https://example.local/products?id=42#reviews` would never appear in a server's access log.

## 10. Knowledge Check

1. Which parts of a URL are sent to the server, and which part is handled entirely by the browser?
2. What is the difference between a *client* and a *browser*? Between a *server* and a *web server*?
3. In the DNS → TCP → TLS → HTTP diagram, which steps did you already learn in Computer Networking?
4. What does it mean for code to run "client-side," and why does that matter for who controls it?
5. If `open` shows you a request and a response, which one did your own machine create?

## 11. Key Takeaways

- A URL has six distinct parts — scheme, host, port, path, query, and fragment — each with its own job; only the fragment stays local to the browser.
- The web is built on top of Networking's DNS and TCP: DNS finds the server, TCP (optionally wrapped in TLS) connects to it, and only then does an HTTP request actually get sent.
- Client and server are roles; browser and web server are the specific programs that usually fill them.
- Client-side code runs in, and is controlled by, the browser it's running in — a distinction that becomes a genuine security boundary later in this platform.
- Every request/response exchange is two separate messages, not one — learn to read them as a pair, not a single block.

## 12. What's Next

**Core Concepts** goes deep on the HTTP request/response format you just glimpsed: methods, status codes, headers, and request/response bodies — the actual vocabulary every web security tool in this platform assumes you already have.
