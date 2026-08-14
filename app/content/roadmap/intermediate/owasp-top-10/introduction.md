# Introduction to Web Application Security and OWASP Thinking

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what OWASP is, what the **OWASP Top 10** actually is, and — just as importantly — what it is not
- state which edition of the Top 10 this module teaches, and why naming the edition matters
- map an application's **attack surface**: the places where it accepts input and makes decisions
- identify a **trust boundary**, and explain why the browser is never on the trusted side of one
- name the ordinary sources of untrusted input, without treating every input as an attack
- distinguish **validation**, **sanitisation** and **encoding**, and say what each one is actually for
- describe a vulnerability as a **failed security control**, rather than as a scary-sounding name
- run the evidence loop: observe → identify input → change one thing → send → compare → hypothesise → validate → document
- keep **observation**, **interpretation** and **conclusion** separate in your own reasoning

## 2. Why This Matters

You have arrived here with three tools and one habit.

**Nmap** taught you to turn a network into a list of things that exist. **Wireshark** taught you to read traffic you did not create and reason about it as evidence. **Burp Suite** taught you to take a single HTTP request, change one part of it deliberately, send it, and read the answer honestly.

The habit is the important part: *never state a conclusion your evidence does not support.*

This module adds the missing piece. Burp taught you **how to ask** a web application a question. It stopped short of teaching you **which questions are worth asking**, and **what the answers mean when something is genuinely wrong**. That is what the OWASP Top 10 gives you: a vocabulary of the ways web applications actually fail, backed by a way of reasoning about each one.

Here is the distinction that matters most, and it is the reason this module exists at all:

> A vulnerability is not a payload you typed.
> A vulnerability is a **security assumption the application made that turned out to be false**.

`' OR '1'='1` is not a vulnerability. It is a string. If an application handles it as data — which a correctly built application does — nothing has gone wrong. The vulnerability, when there is one, is that the application *built a database query by gluing that string into it*, so the string stopped being data and started being instructions. The payload is only how you demonstrated the failure. The failure was already there.

Everything in this module follows from that. You are learning to reason about broken assumptions, not to memorise ten names.

## 3. The Authorization Boundary

You met this in the Burp Suite module and it has not changed:

**Testing a web application for vulnerabilities is authorized only against systems you own or have explicit written permission to test.**

| Allowed | Not allowed |
|---|---|
| This platform's simulated `cybershop.training` environment | Any site you happen to be browsing |
| A deliberately vulnerable app you installed yourself (OWASP Juice Shop, DVWA) | A company's site because it "looked insecure" |
| PortSwigger's Web Security Academy labs | A friend's account, "just to show them" |
| A client system inside a signed engagement scope | Anything outside that scope, even at the same company |
| A bug bounty target, inside its published scope rules | A target whose programme excludes that asset |

Two things people get wrong even when they mean well. **"I only sent one request"** is not a defence — the testing is the regulated act, not the damage. **"It's my own account"** authorizes nothing about the *server*; your account is yours, the system is not.

Everything runnable in this module happens inside YushaCyber's simulated training site, which exists entirely as Python data structures and has no HTTP client in it at all. It cannot reach anything real:

```
$ open https://evil.example.com/
External hosts are not available in the training environment.
```

That refusal is the environment's scope control, enforced before a request object is even built. It is the technical expression of the boundary above.

## 4. What OWASP Actually Is

**OWASP** — the Open Worldwide Application Security Project — is a non-profit foundation that produces free, openly licensed resources about software security: documentation, standards, testing guides, and tools. It is community-run. Nobody has to pay to read or use any of it.

OWASP publishes a great deal more than the Top 10. Two things worth knowing exist:

- the **OWASP Application Security Verification Standard (ASVS)** — a detailed, levelled list of security requirements you can actually verify an application against
- the **OWASP Web Security Testing Guide (WSTG)** — a methodology describing *how* to test, in far more depth than a top-ten list can

The **OWASP Top 10** is the best-known of these, and the most misunderstood. It is an **awareness document**: a periodically-revised list of the ten most significant categories of web application security risk, built from analysing vulnerability data across many organisations, plus a community survey for risks the data cannot yet see.

Read that definition slowly, because four things follow from it that people routinely get wrong.

**It is a list of *categories*, not of bugs.** "Injection" is not a bug. It is a family containing SQL injection, OS command injection, and several others that share one mechanism.

**It is a list of *risks*, not a list of *tests*.** "This application has no A09 issues" is not something you can conclude by running a scanner. Some categories have no signature to scan for at all.

**It is *ranked by observed risk*, not by importance to you.** A category being tenth does not make it harmless in your application.

**It is *not exhaustive*, and was never meant to be.** This is the single most important thing in this section, so it gets its own heading.

## 5. Why the Top 10 Is Not a Complete List

There are thousands of distinct weakness types catalogued in the industry (MITRE's CWE list runs to well over nine hundred entries). Ten categories cannot contain them.

Concretely, all of the following are real, serious, and **not** their own Top 10 entry:

- business logic flaws — a discount code that can be applied twice, a refund flow that can be run before the return arrives
- race conditions — two simultaneous requests that both pass a "do you have enough balance?" check
- denial of service
- most client-side-only issues
- most mobile-specific and most purely infrastructure-level issues

Some of these hide *inside* a category once you look (a business logic flaw is very often an access control or insecure design problem). Others simply are not there.

So what is the Top 10 for? Three honest uses:

1. **A shared vocabulary.** When you write "A01: Broken Access Control" in a report, an engineer on the other side of the world knows what class of problem you found.
2. **A prompt list.** When you are looking at an unfamiliar application, running down the ten categories gives you ten different angles of attack on the question "how could this be wrong?"
3. **An awareness baseline** for teams who have never thought about application security systematically.

What it is **not** for: a certificate of completeness. "We checked the OWASP Top 10 and found nothing" means you checked ten categories of thing. It says nothing about the eleventh.

## 6. Which Edition This Module Teaches

The Top 10 has been revised repeatedly since it first appeared: 2003, 2004, 2007, 2010, 2013, 2017, 2021 — and it continues to be revised. **Category names, category boundaries, and the ranking all change between editions.** "Broken Authentication" in 2017 became "Identification and Authentication Failures" in 2021, and moved from second place to seventh. "Sensitive Data Exposure" became "Cryptographic Failures", refocusing the category on the *cause* rather than the *symptom*.

**This module teaches the OWASP Top 10 – 2021 edition**, whose ten categories are A01:2021 through A10:2021. Every category name, identifier and ordering used in these three lessons is the 2021 edition's, and nothing from an earlier or later edition is mixed in.

Two practical consequences, and they matter more than they look:

**Always state the edition when you cite a category.** "A03: Injection" is ambiguous on its own — in the 2017 edition, A03 was a different category entirely. Writing `A03:2021 – Injection` in a finding removes all doubt.

**Check which edition is current before you write a professional report.** The list on `owasp.org` is authoritative and it is revised on its own schedule, not yours. A report that cites a superseded edition without saying so looks careless, and can genuinely mislead a reader who maps your categories onto a newer list.

The *reasoning* this module teaches does not expire when the list is revised. The categories are labels for underlying failures — broken authorization, unsafe interpretation of input, weak design, poor configuration — and those failures are older than any edition of the list and will outlive this one too.

## 7. The Chain This Module Runs On

Every investigation in these three lessons follows the same chain. It is worth learning as a shape, because it is what stops you from jumping from "that looks odd" straight to "that's a vulnerability."

```
APPLICATION
    ↓  what is this thing, and what does it do?
ATTACK SURFACE
    ↓  where does it accept input or make decisions?
INPUT / REQUEST
    ↓  what exactly did the client send?
TRUST BOUNDARY
    ↓  which side of the boundary was that input on?
APPLICATION BEHAVIOR
    ↓  what did the server actually do with it?
VULNERABILITY
    ↓  which security assumption turned out to be false?
IMPACT
    ↓  what does that let someone do, concretely?
EVIDENCE
    ↓  what proves the two steps above, to someone who wasn't there?
MITIGATION
    ↓  what change removes the false assumption?
VALIDATION
       how would you confirm the change actually worked?
```

Most beginners run the first five links and then leap to the eighth. The middle links — *which assumption broke*, and *what that actually lets someone do* — are the difference between a finding and a screenshot.

## 8. Attack Surface

An application's **attack surface** is every point where it accepts input from outside, or makes a decision based on something the client controls.

You already have the tool that shows it. Here is the training site's own route list, from this platform's simulator:

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

A real application will not hand you this list. You build it yourself, from browsing, from the proxy's HTTP history, and from whatever documentation exists. But the *shape* of what you are looking for is the same, and it is worth naming the categories explicitly:

| Surface | What to look at | Why it matters |
|---|---|---|
| **URLs and paths** | `/products`, `/upload/<id>` | A path segment can be an identifier — and identifiers are things a client can change |
| **Query parameters** | `?id=42`, `?q=laptop` | Visible, easy to change, often used unmodified by the server |
| **Forms** | login, feedback, transfer | Determine what a request body contains — but the body is not limited to what the form offers |
| **JSON bodies** | `POST /api/profile` | Same as forms, different encoding; field names are guessable and extra fields are sometimes accepted |
| **Cookies** | `session_id` | Client-held, client-editable state, sent automatically |
| **Headers** | `Authorization`, `Origin`, `Content-Type`, `User-Agent` | Every one of them is client-controlled input |
| **Authentication** | `/login`, `/logout`, `/api/login` | Where identity is established, and where it is destroyed |
| **Authorization** | `/admin`, `/profile`, `/account` | Where identity is turned into permission — a separate decision |
| **File uploads** | `/upload`, `/secure-upload` | Content *and* filename *and* type are all attacker-influenced |
| **APIs** | `/api/me`, `/api/profile` | Often less carefully guarded than the HTML routes doing the same job |
| **Administrative functionality** | `/admin`, `/settings` | Higher impact when the decision is wrong |
| **Business logic** | `/transfer`, `/upload-security` | Where the application does something that *means* something |

Notice how much of that list is stuff a browser never shows a user. That is precisely why the proxy from the last module is the tool that reveals attack surface: it shows you the requests, not the page.

**Three questions to ask of every surface you find**, and they are the same three every time:

1. What input does this accept?
2. What decision does the server make because of that input?
3. What would happen if the input were not what the interface intended to send?

## 9. Trust Boundaries

A **trust boundary** is a line in a system where data crosses from somewhere you do not control into somewhere you do.

```
   BROWSER                    ┃                  SERVER
   (user-controlled)          ┃                  (you control)
                              ┃
   HTML page                  ┃   application code
   JavaScript                 ┃   session store
   form fields                ┃   database
   hidden fields              ┃   filesystem
   cookies                    ┃   external services
   disabled buttons           ┃
                              ┃
        ─────  HTTP request ──╂──►
        ◄─── HTTP response ───┨
                              ┃
                       TRUST BOUNDARY
```

Everything on the left of that line is under the user's control. Not "mostly", not "unless they're a normal user" — entirely. The browser is a program running on someone else's computer, and they can change it, replace it, or skip it altogether and send the HTTP request by hand. You have done exactly that in the last module.

From which one rule follows, and it is the single most load-bearing sentence in this entire module:

> **A restriction that exists only in the browser is not a security control.**

A greyed-out button, a hidden form field, a JavaScript `if (user.isAdmin)`, a dropdown that only lists your own account numbers, a maximum length on an `<input>` — every one of those is a *user interface* decision. Each may be excellent design. None is a security boundary, because none of them is on the server's side of that line.

The server must independently:

- **authenticate** — establish *who is sending this request*, from the request itself
- **authorize** — decide *whether that identity may do this specific thing to this specific resource*
- **validate** — decide whether the input is acceptable at all
- **handle safely** — use the input in a way that cannot change the meaning of a query, a command, a document, or a file path

Those four are separate decisions. A great deal of this module is about what happens when an application does one and forgets another.

## 10. Input

Every one of these is untrusted input:

- query string parameters (`?id=42`)
- form fields
- JSON body fields
- path segments (`/upload/7` — the `7` is input)
- HTTP headers, including ones you did not expect the client to set
- cookies
- uploaded files: contents, filename, declared type, size
- data from an external API your server calls
- data read back out of your own database that a user put there earlier

That last one surprises people. Data does not become trustworthy by having been stored. A comment someone submitted last week is still user input when you render it next week — which is exactly the difference between reflected and stored cross-site scripting.

Now the correction that keeps this from becoming paranoia:

> **Input is not dangerous. Assumptions about input are dangerous.**

An application that receives `' OR '1'='1` in a search box and searches for a product literally named `' OR '1'='1` has done nothing wrong. It found nothing, and it should not have. Input becomes dangerous only where the application does something with it that lets it stop being data:

- concatenating it into a database query → the input can change the query
- concatenating it into an HTML page → the input can become markup
- concatenating it into an OS command → the input can become another command
- using it as a filename → the input can escape into another directory
- using it as a URL the *server* then fetches → the input can pick the destination
- using it as an identifier without checking ownership → the input can select someone else's data

The category names you are about to learn are, in almost every case, a name for one of those six sentences.

## 11. Validation, Sanitisation, Encoding

Three words that beginners use interchangeably and that mean three genuinely different things. Getting these straight now will save you from writing a bad mitigation later.

| | The question it asks | What it does with bad input | Where it belongs |
|---|---|---|---|
| **Validation** | *Is this input allowed at all?* | Rejects it | At the boundary, as early as possible |
| **Sanitisation** | *Can this be transformed into something safe?* | Modifies it | Rarely; only where you must accept rich content |
| **Encoding** | *How is this represented safely **here**?* | Represents it inertly | At the point of output, per destination |

**Validation** is a yes/no decision against an expectation. "Is this a positive integer?" "Is this one of these four values?" Prefer an **allowlist** (define what is acceptable and reject everything else) over a **denylist** (list what is forbidden and allow the rest) — denylists fail silently every time someone thinks of an input you did not list.

**Encoding** is contextual, and the context is *where the data is going*. The same string needs different treatment in HTML text, in an HTML attribute, in a URL, in JavaScript, in JSON. Encoding does not remove anything; it represents the data so that the destination reads it as data. You can see exactly this in the training simulator: the secure search endpoint returns your input HTML-escaped, so `<` arrives as `&lt;` and is displayed rather than interpreted.

**Sanitisation** is the awkward one. It means accepting input and transforming it into a version believed to be safe — stripping tags from submitted HTML, for example. It is genuinely necessary in a few places (a rich-text editor has to accept *some* markup) and it is where people get into trouble everywhere else, because "believed to be safe" is doing enormous work in that sentence.

Which brings us to the correction:

> **Sanitisation is not a substitute for parameterised queries or contextual output encoding.**

"We strip apostrophes from the input, so we're safe from SQL injection" is one of the most reliable ways to *still* have SQL injection. Parameterised queries do not filter your input; they make the input structurally incapable of changing the query, whatever it contains. That is a different and far stronger guarantee. Lesson 2 shows both, side by side, against the same payload.

## 12. A Vulnerability Is a Failed Control

Here is the framing that makes the ten categories cohere instead of feeling like a list to memorise.

An application makes promises to itself. *Only logged-in users reach this page. Only admins reach that one. This input will be treated as text. This file is really an image. This dependency does what its documentation says.* Each promise is kept by a **security control** — some mechanism that makes it true.

**A vulnerability exists when a control that was supposed to keep one of those promises does not.**

| Control that fails | Broken promise | 2021 category |
|---|---|---|
| Authorization | "only the owner sees this record" | A01: Broken Access Control |
| Protection of data | "this is unreadable to anyone but us" | A02: Cryptographic Failures |
| Safe handling of input | "this input stays data" | A03: Injection |
| The design itself | "this workflow cannot be abused" | A04: Insecure Design |
| Configuration | "nothing is exposed that shouldn't be" | A05: Security Misconfiguration |
| Dependency management | "our components are known-good" | A06: Vulnerable and Outdated Components |
| Authentication | "this really is who they claim to be" | A07: Identification and Authentication Failures |
| Integrity verification | "this code/data has not been tampered with" | A08: Software and Data Integrity Failures |
| Logging and monitoring | "we would notice" | A09: Security Logging and Monitoring Failures |
| Control over outbound requests | "the server chooses what it fetches" | A10: Server-Side Request Forgery |

Read that table as ten different ways of finishing the sentence *"the application assumed X, and X was not enforced."* That is the whole list.

## 13. Evidence-Based Testing

The loop, which is the Burp loop with two extra steps on the end:

```
OBSERVE the normal behaviour            ← you cannot spot abnormal without this
    ↓
IDENTIFY an input the client controls
    ↓
FORM a hypothesis about what the server does with it
    ↓
CHANGE exactly one thing
    ↓
SEND
    ↓
OBSERVE the response, completely — status, headers, body, and side effects
    ↓
COMPARE against the baseline
    ↓
VALIDATE — reproduce it; rule out coincidence; check the state actually changed
    ↓
DOCUMENT — evidence, impact, mitigation
```

Three rules govern this loop and none of them is optional.

**Establish a baseline first.** "The response was 403" is meaningless without knowing what the response was before you changed anything. Most of the time your first request should be entirely normal, precisely so you have something to compare against.

**Change one variable at a time.** If you alter the session cookie *and* the resource identifier and the response changes, you have learned nothing about which change mattered. This is not pedantry; it is the only way the comparison means anything.

**A status code is evidence, not a verdict.** `403` tells you the server refused. It does not tell you the server *checked properly* — a server that returns 403 to everyone including the legitimate owner is also "403". Meanwhile a `200` that returns an empty body is not access granted. Read the whole response.

## 14. Observation, Interpretation, Conclusion

Keep these three separate, in your notes and in your head. Collapsing them is the most common way competent testers produce wrong findings.

**OBSERVATION** — what you can point at. No inference.
> Requesting `/admin` with no cookie returned `401`. Requesting `/admin` with the `student` session cookie returned `403`. Requesting `/admin` with the `admin` session cookie returned `200` and an admin page body.

**INTERPRETATION** — what that suggests, stated as a suggestion.
> The server appears to distinguish "not authenticated" from "authenticated but not permitted", and to grant access based on which account the session belongs to. The authorization decision appears to be made server-side.

**CONCLUSION** — what you are willing to assert, with its limits attached.
> On this route, authorization is enforced server-side and is not bypassable by the request modifications tested. This does not establish that every route enforces it, and does not establish that the check cannot be bypassed by means not tested.

Notice that the conclusion in that example is *"this looks correct"* — which is a real finding too, and a far more common outcome than beginners expect. Most requests you send during a real assessment will confirm the application behaving properly. The discipline is what makes the exception recognisable when it comes.

## 15. The Ten Categories at a Glance

A map, not a syllabus. Lesson 2 takes each of these apart properly, with real evidence from this platform's simulator where it exists.

| # | Category | The control that failed | Evidence that might reveal it | One common misconception |
|---|---|---|---|---|
| **A01** | Broken Access Control | Authorization | Same request, different account or identifier, different data returned | "Authenticated" means "allowed" |
| **A02** | Cryptographic Failures | Protection of sensitive data | Data in transit or at rest that is readable, or protected by a weak/misused mechanism | "We use HTTPS, so data is protected" |
| **A03** | Injection | Safe handling of input in an interpreter | Input that changes application behaviour in a way only a change of *structure* explains | "SQL-looking input proves SQL injection" |
| **A04** | Insecure Design | The design itself | A workflow that can be abused even when every line of code works as written | "It's a bug in the code somewhere" |
| **A05** | Security Misconfiguration | Configuration | Verbose errors, default accounts, debug output, absent or wrong security headers | "That's just a settings issue, not a vulnerability" |
| **A06** | Vulnerable and Outdated Components | Dependency management | Version disclosure, dependency inventory, published advisories | "Old version = vulnerable" |
| **A07** | Identification and Authentication Failures | Authentication | Login, session issue/expiry/invalidation behaviour | "This is the same thing as A01" |
| **A08** | Software and Data Integrity Failures | Integrity verification | Code, data or updates accepted without verification | "It's the same as A06" |
| **A09** | Security Logging and Monitoring Failures | Detection and response | Absence — an attack that leaves no usable trace | "Nothing was logged, so nothing happened" |
| **A10** | Server-Side Request Forgery | Control over outbound requests | The server fetching a URL the client chose | "That's just the browser making a request" |

Two structural things to notice before you meet them properly.

**They overlap, on purpose.** A file upload that accepts a `.php` file is arguably A08 (integrity of accepted content), A05 (a web-writable upload directory), and A04 (the design never asked what happens if the file is executable). Real findings frequently touch two or three categories. Pick the one that best describes *the control that failed*, and say why you chose it.

**Some are visible from outside, some are not.** You can demonstrate A01 and A03 from a request. You generally cannot demonstrate A09 from outside at all — its symptom is the absence of something on the defender's side. That is not a flaw in the list; it is a reminder that testing from outside is one perspective, not the only one.

## 16. Common Misconceptions

**WRONG:** "The OWASP Top 10 contains every vulnerability that matters."
**CORRECT:** It is a risk-awareness framework covering ten categories. Business logic flaws, race conditions, denial of service and many others are real, serious, and outside it. Passing a Top 10 review is not a clean bill of health.

**WRONG:** "If I'm authenticated, I'm allowed."
**CORRECT:** Authentication establishes *who you are*. Authorization decides *what that identity may do*. They are separate decisions, and an application can get the first right and the second wrong — which is exactly what A01 is.

**WRONG:** "This parameter takes user input, so it's vulnerable."
**CORRECT:** Every parameter takes user input; that is what a parameter is. A vulnerability requires *unsafe handling* of that input, and you have to demonstrate the unsafe handling, not the existence of the parameter.

**WRONG:** "The application returned 403, so authorization is secure."
**CORRECT:** `403` is one piece of evidence from one request. It shows this request was refused. It does not show that the check is applied consistently, applied on the right resource, or applied at all on a different route or method.

**WRONG:** "HTTPS solves web security."
**CORRECT:** TLS protects data *in transit* — confidentiality, integrity, and authentication of the server. It does nothing whatsoever about broken authorization, injection, insecure design, or application logic. An application can be fully HTTPS and still hand every user everyone else's records.

**WRONG:** "The button isn't shown to this user, so this user can't do it."
**CORRECT:** The interface is on the user's side of the trust boundary. Not rendering a button removes a convenience, not a capability. The server must enforce the restriction regardless of what the page displays.

## 17. Exercises

Reasoning questions. Everything you need is printed above — no commands to run yet.

**Exercise A — Attack surface.**
From the route list in §8, pick the five routes you would investigate first, and write one sentence per route saying *which question you would ask it*. There is no single right answer, but "because it sounds interesting" is not a reason — name the input or the decision.

<details>
<summary>Discussion</summary>

Reasonable picks, with the question each one raises:

- `/admin` — is the authorization decision made server-side, or only in the interface?
- `/upload/<id>` — the identifier is in the path; does the server check who owns it?
- `/search` — takes free text that plausibly reaches a data store; how is it handled?
- `/transfer` — it *does* something with consequences; what proves the user intended it?
- `/api/profile` — an API doing the same job as an HTML page; is it guarded as carefully?

The pattern to notice: the interesting routes are the ones that either accept an identifier, or take an action, or make an access decision. Routes that only display fixed content are rarely where the interesting failures live.
</details>

**Exercise B — Trust boundary.**
An application hides its "Delete all records" button unless the logged-in user is an administrator. The developer says this prevents non-administrators from deleting records. Name the assumption, and say precisely why it is unsafe.

<details>
<summary>Discussion</summary>

The assumption is that the only way to send the delete request is by clicking the button. That is false, because the button and the page it lives on are on the **user's** side of the trust boundary. Anyone can construct the same HTTP request by hand — you already know how — and the server will receive a request identical to the one the button would have produced.

Hiding the button is a reasonable *interface* decision. The security control has to be a server-side authorization check on the delete endpoint itself. If that check exists, hiding the button changes nothing about security. If it does not exist, hiding the button changes nothing about security either.
</details>

**Exercise C — Input is not the problem.**
Two applications both receive `<script>alert(1)</script>` in a comment field. Application A stores it and later displays it on a page, HTML-encoded, so visitors see the literal text. Application B stores it and later writes it straight into the page's HTML. Which one has a vulnerability, and what exactly is the vulnerability?

<details>
<summary>Discussion</summary>

Application B. And it is worth being precise about *what* the vulnerability is: it is not "the field accepted a script tag" — accepting text is what a comment field does. The vulnerability is that at the point of **output**, data was written into an HTML document without being encoded for that context, so it stopped being data and became markup.

That also explains why the fix belongs at output, not input. Application A accepted the identical text and is fine, because it encodes when it renders. Note too that the danger arrived *later*, when the stored comment was displayed — which is the difference between reflected and stored XSS, and the reason stored data is still untrusted input.
</details>

**Exercise D — Observation, interpretation, conclusion.**
You change `?id=42` to `?id=43` and the response body changes. Write one observation, one interpretation, and one conclusion — and make the conclusion honest.

<details>
<summary>Discussion</summary>

**Observation:** with `id=42` the response body described product 42; with `id=43` it described product 43. Status was 200 both times.

**Interpretation:** the `id` parameter selects which product record is returned. The server appears to accept a client-supplied identifier and use it to look up a record.

**Conclusion:** none yet — and that is the correct answer. A product catalogue is *supposed* to let anyone request any product. Nothing here is a finding. It would become interesting only if the resource being selected were one that belongs to a specific user, and the server returned it to someone who does not own it. That is a different test, and it needs a second account to run honestly.

If your conclusion was "this is IDOR", re-read the chain in §7: you skipped the impact link. Selecting a public record by id is not an impact.
</details>

## 18. Knowledge Check

1. Why is the OWASP Top 10 not an exhaustive list of vulnerabilities, and what should you say instead of "we passed the Top 10"?
2. What is the difference between authentication and authorization? Give an example of an application that gets the first right and the second wrong.
3. Why must security-sensitive checks be enforced server-side? Answer using the trust boundary, not "because the client is untrusted."
4. What actually makes an input dangerous? Give the two-part answer (the input, and the thing the application does with it).
5. Distinguish validation, sanitisation and encoding in one sentence each.
6. Why is `403` insufficient on its own to conclude that authorization is correctly enforced?
7. Why does citing an OWASP category without its edition risk being ambiguous?
8. Why should you establish a baseline request before changing anything?

<details>
<summary>Answers</summary>

1. It is an awareness document covering ten *categories* of risk, derived from observed data plus a community survey — not a catalogue of every weakness type (there are hundreds). Business logic flaws, race conditions and denial of service sit outside it. Say instead: "we assessed against the ten OWASP Top 10 2021 categories, and here is what that scope did and did not cover."
2. Authentication = "who are you?"; authorization = "what may you do?". An application that correctly verifies your password and then lets you read any record by changing an id in the URL has authenticated you correctly and authorized you incorrectly.
3. Because everything on the client side of the trust boundary — the page, its JavaScript, its hidden fields, its disabled buttons, the browser itself — is under the user's control and can be modified or bypassed entirely. The server receives an HTTP request; it cannot know, and must not assume, that any client-side restriction was applied to it.
4. Input is dangerous only in combination with what the application does with it: when the application uses it in a way that lets it stop being data and start being structure — query syntax, markup, a command, a file path, a URL the server fetches, or an identifier used without an ownership check.
5. **Validation** asks whether the input is allowed and rejects it if not. **Sanitisation** transforms input into a form believed to be safe. **Encoding** represents data so that a specific destination context reads it as data rather than as instructions.
6. Because it is a single data point from a single request. It shows one request was refused; it does not show that the check is applied on every route and method, applied against the right resource, or that it cannot be bypassed by an input you have not yet tried. It is evidence, not a verdict.
7. Because the identifiers are reused across editions with different meanings — `A03` names a different category in the 2017 and 2021 lists, and several categories have been renamed or merged between editions. Writing `A03:2021 – Injection` removes the ambiguity.
8. Because "the response changed" is only meaningful relative to something. Without a normal, unmodified request to compare against, you cannot distinguish a change you caused from behaviour that was always there.
</details>

## 19. Where This Goes Next

**Core Concepts** takes each of the ten 2021 categories apart: what control fails, what evidence reveals it, what the impact is, what the fix is, and — for every category this platform can actually demonstrate — real output from the training simulator rather than a description of what output might look like.

**Hands-on Practice** turns that into a single continuous investigation: access control, injection, authentication and configuration, run as experiments against the authorized training environment, ending in a complete written finding with evidence, impact, severity reasoning, mitigation and confidence.

Beyond this module, **Active Directory Basics** and the privilege-escalation modules move the same reasoning off the web and onto systems, and the Red Team track's **Web Pentesting** builds full assessment methodology on top of exactly what you learn here.
