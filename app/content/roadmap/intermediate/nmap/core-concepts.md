# Nmap Core Concepts

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain exactly what a default `nmap TARGET` scan asks Nmap to determine
- scan specific ports and port ranges, and reason about the coverage/time tradeoff of each
- explain why service and version detection (`-sV`) is stronger evidence than an open port alone, and why it's still not certainty
- explain OS detection (`-O`) as an inference from network behavior, not a guaranteed identification
- explain what Nmap Scripting Engine (NSE) scripts conceptually add, without treating them as automatic vulnerability discovery
- correct the specific false assumptions beginners make about scan results
- explain the conceptual difference between TCP connect scanning, SYN scanning, and UDP scanning

## 2. Why This Matters

Introduction gave you the vocabulary and the honest framing: Nmap infers, it doesn't know. This lesson is where that framing earns its keep. Every command here produces a different *kind* of evidence, with a different amount of confidence attached to it — a bare port scan tells you less than a version scan, which tells you less than a version scan you've cross-checked against other clues. Learning to run these commands is the easy part. Learning to know how much to trust what they tell you is the actual skill, and it's the one that separates someone reciting Nmap flags from someone doing real reconnaissance.

Every example in this lesson is real output, captured by running this platform's own Nmap simulator (`app/core/terminal/network.py`) against the authorized lab network used by the real **Nmap Fundamentals** terminal mission — the same network you'll work in directly during Hands-on Practice. Nothing here is invented.

## 3. The Basic Scan: What `nmap TARGET` Actually Asks

The simplest possible Nmap command is the target and nothing else:

```
nmap TARGET
```

Here's precisely what this asks Nmap to determine, in order: first, whether the host responds to discovery at all (Introduction §8); if it does, Nmap tests a default set of commonly-used TCP ports and reports the state of each one it finds open. It is **not** a scan of every possible port (Section 6 covers what that actually takes), and it does **not** identify service versions on its own (Section 7) — a bare scan tells you *which doors respond*, nothing more.

Real output, scanning the lab's web server:

```
$ nmap 10.10.10.10

Starting Nmap

Nmap scan report for 10.10.10.10

PORT     STATE    SERVICE
22/tcp open ssh
80/tcp open http
443/tcp open https

Nmap done.
```

Read this the way Introduction's enumeration mindset asks you to: three ports responded, each labeled with the state (`open`) and Nmap's best guess at the conventional service name for that port number (`ssh`, `http`, `https`). That last column is a *label*, drawn from the port-number convention Introduction §5 already warned you about — it is not yet confirmed by anything the service itself said. You have three reachable services worth investigating further. You do not yet have confirmation of what they actually are.

## 4. Targeted Scanning: Specific Ports

Once you know (or suspect) which ports matter, scanning only those is faster and more focused:

```
nmap -p PORT TARGET
```

```
$ nmap -p 22 10.10.10.30

Starting Nmap

Nmap scan report for 10.10.10.30

PORT     STATE    SERVICE
22/tcp open ssh

Nmap done.
```

Why bother narrowing at all, if a default scan already covers common ports? Two real reasons. First, speed: testing one port is faster than testing a thousand, which matters on a slow link or a large set of targets. Second — and more important for reconnaissance — a targeted scan lets you re-check a *specific* port after you already have a reason to care about it, without re-running everything else. You'll do exactly that in Hands-on Practice.

You can also scan a comma-separated list in one command (`-p 22,80,443`) — useful when you already know which few ports matter and want one clean result instead of three separate commands.

## 5. Port Ranges

```
nmap -p 1-1000 TARGET
```

A range trades speed for coverage: you're testing every port in the range, not just the ones you already suspect. Real output, scanning ports 20–30 on the lab's file server — a small range chosen because it demonstrates something Section 4's single-port scan can't:

```
$ nmap -p 20-30 10.10.10.30

Starting Nmap

Nmap scan report for 10.10.10.30

PORT     STATE    SERVICE
20/tcp closed unknown
21/tcp open ftp
22/tcp open ssh
23/tcp closed unknown
24/tcp closed unknown
25/tcp filtered unknown
26/tcp closed unknown
27/tcp closed unknown
28/tcp closed unknown
29/tcp closed unknown
30/tcp closed unknown

Nmap done.

```

This is a genuinely more informative result than scanning port 22 alone: it reveals an open FTP port (21) you wouldn't have found by guessing, *and* a **filtered** port (25) — Introduction §7's "Nmap can't tell" state, shown here for real rather than described abstractly. A single-port scan of 22 would have missed both.

The tradeoff is exactly what it looks like: a wider range takes proportionally longer to scan, and — for a real target outside a lab — sends proportionally more traffic, which matters for the responsible-scanning discussion in Section 12. **A range is not the same as "all ports."** `-p 1-1000` covers the well-known range and a good portion of the registered range (Introduction §5) — it says nothing about ports 1001–65535, including the entire dynamic/private range.

## 6. Scanning All TCP Ports

```
nmap -p- TARGET
```

`-p-` means exactly what it looks like: every TCP port from 1 to 65535, not just the default set or a chosen range. This is the highest-coverage TCP scan Nmap can run, and the tradeoff is real: testing 65,535 ports takes meaningfully longer than testing the ~1,000 most common ones, and on a real (non-simulated) network it generates far more traffic — a fact with real consequences, covered in Section 12 and again in Hands-on Practice's ethics section.

The practical pattern this motivates: **a broad scan is often followed by targeted enumeration, not the other way around.** Run `-p-` (or accept the default scan) to find out what's out there in the first place, then go back with `-p` on the specific ports that turned out to matter and dig deeper with the tools in the next two sections. Casting the wide net first and narrowing second is usually more efficient than guessing narrowly and hoping you picked right.

## 7. Service and Version Detection

Every scan so far has answered "is this port open?" None of them have confirmed *what's actually listening*. That's what `-sV` is for:

```
nmap -sV TARGET
```

Service/version detection works by sending each open port a set of **probes** — small, protocol-aware exchanges — and comparing how the port responds against Nmap's database of known service signatures. A real web server tends to respond to an HTTP-shaped probe the way real web servers do; that response is the **evidence** version detection is built on.

Real output:

```
$ nmap -sV 10.10.10.10

Starting Nmap

Nmap scan report for 10.10.10.10

PORT     STATE    SERVICE    VERSION
22/tcp open ssh OpenSSH 9.x
80/tcp open http nginx
443/tcp open https nginx

Nmap done.
```

Compare this to Section 3's bare scan of the same host: the `STATE` and `SERVICE` columns are identical, but there's now a `VERSION` column with real, specific findings — `OpenSSH 9.x`, `nginx` twice. This is meaningfully stronger evidence than the port number alone: the service itself responded in a way that identified it, rather than Nmap merely guessing from the port convention.

**It is still not absolute truth.** Version detection is an identification process, built on how the service *chose* to respond to a probe — a deliberately misconfigured or hardened service can respond misleadingly, a proxy can sit in front of the real service and answer on its behalf, and Nmap's signature database can be wrong or out of date for something unusual. Treat a version-detection result as strong evidence you'd cite in a finding, not as a fact you'd stake something important on without a second source.

## 8. TCP vs. UDP Scanning, in Practice

Introduction §6 explained *why* TCP and UDP scans behave differently. Here's what that looks like as real commands and real output.

```
nmap -sT TARGET
```

`-sT` is an explicit **TCP connect scan** — Nmap completes a real TCP handshake with each port it tests, the cleanest possible signal a port is genuinely open (Section 13 covers how this differs from a SYN scan under the hood):

```
$ nmap -sT 10.10.10.10

Starting Nmap

Nmap scan report for 10.10.10.10

PORT     STATE    SERVICE
22/tcp open ssh
80/tcp open http
443/tcp open https

Nmap done.
```

```
nmap -sU TARGET
```

`-sU` switches to UDP, tested against the lab's DNS server:

```
$ nmap -sU 10.10.10.53

Starting Nmap

Nmap scan report for 10.10.10.53

PORT     STATE    SERVICE
53/udp open dns

Nmap done.
```

This lab's simulator gives a clean, definitive answer here — but Introduction §6 already told you the honest real-world version: a real UDP scan often can't be this clean. Because UDP has no handshake, a target that never replies to a UDP probe is genuinely ambiguous — it can mean "open, and this service just doesn't answer this kind of probe," or it can mean "a firewall silently ate the packet," and Nmap frequently has to report an "open|filtered" combined state rather than a confident single answer. That's the concrete shape of the ambiguity Introduction described, and it's exactly why real UDP scanning takes longer (waiting out timeouts, sometimes retrying) and demands more careful reading than TCP results do.

## 9. Host Discovery and `-Pn`

Introduction §8 mentioned that some hosts don't respond to discovery probes at all, even while running real services. Here's what that looks like:

```
$ nmap 10.10.10.40

Starting Nmap
Note: Host seems down. If it is really up, but blocking pings, try -Pn
Nmap done: 0 hosts up.
```

Nmap is telling you exactly what it knows and doesn't: the discovery probe got no response, so *by default* it assumes there's nothing worth scanning and stops — but it also tells you the specific reason this might be wrong, and the specific flag to fix it. `-Pn` means **skip host discovery, and scan the ports anyway**:

```
$ nmap -Pn -O 10.10.10.40

Starting Nmap

Nmap scan report for 10.10.10.40

PORT     STATE    SERVICE
22/tcp open ssh
8080/tcp open http-proxy

OS guess: Linux 5.X (embedded)

Nmap done.
```

The host was never actually down — it was configured to not respond to discovery probes (a real, common hardening choice), and skipping discovery revealed two real open ports Nmap would otherwise have never told you about. This is the concrete cost of conflating host discovery with port scanning that Introduction §8 warned about: trusting the first result without `-Pn` would have written this host off entirely.

## 10. OS Detection as Inference

That last example also used `-O`, Nmap's OS detection:

```
nmap -O TARGET
```

`-O` makes Nmap look at low-level network behavior — how the target's TCP/IP stack handles specific probe patterns — and compares that fingerprint against a database of known operating system behaviors. Different operating systems implement networking with small, consistent differences (default settings, how certain edge cases are handled), and those differences are what OS detection is actually reading.

**This is an inference, not a certainty, and treating it as magic is a mistake.** The result above — `Linux 5.X (embedded)` — is Nmap's best match against its fingerprint database, not a guarantee. Virtual machines, unusual network configurations, unusual embedded stacks, unpatched or heavily modified systems, and unlucky partial evidence can all produce a wrong or vague guess. Use an OS detection result as one more piece of evidence feeding into your overall picture (Section 12's enumeration mindset), never as the single fact a conclusion rests on.

## 11. NSE Scripting, Conceptually

Nmap ships with the **Nmap Scripting Engine (NSE)** — a library of scripts that can run additional, more specific checks against a target beyond the plain scan types above:

```
nmap -sC TARGET
```

`-sC` runs a default set of NSE scripts. Conceptually, scripts extend the same evidence-gathering idea this whole lesson has been building: instead of just "is the port open" or "what version responded," a script can perform a more specific probe — asking a web server for its default page title, or asking an FTP server whether it allows anonymous login — and report back what it finds as additional evidence.

**Two things to hold onto here.** First, NSE scripts extend *discovery and enumeration* — they gather more specific evidence about what's running and how it's configured. **Nmap does not become a universal vulnerability scanner just because scripting is involved**, and some individual NSE scripts genuinely do check for specific known issues, but running scripts is not the same activity as vulnerability assessment as a discipline, and this module does not teach exploitation or vulnerability scripting — that's deliberately out of scope here, consistent with this being a reconnaissance and enumeration module, not an exploitation one. Second, this platform's terminal simulator accepts `-sC` without error but does not model script-specific output — so no simulated NSE result is quoted here, honestly, rather than invented.

## 12. Correcting the False Assumptions

Four claims worth stating plainly, because each one is a real beginner mistake this lesson has already built the material to correct:

> **WRONG:** "Closed means the machine is offline."
> **CORRECT:** "Closed means the host responded but no service is listening on that port." (Introduction §7)

> **WRONG:** "Filtered means the port is closed."
> **CORRECT:** "Filtered means Nmap cannot determine whether the port is open because packet filtering prevents a clear conclusion." (Introduction §7, demonstrated for real in Section 5)

> **WRONG:** "Port 80 always means HTTP."
> **CORRECT:** "Port 80 is conventionally associated with HTTP, but service detection provides stronger evidence." (Introduction §5, demonstrated for real in Section 7)

> **WRONG:** "Nmap finds vulnerabilities automatically."
> **CORRECT:** "Nmap primarily provides discovery and enumeration capabilities; some NSE scripts can perform additional checks, but Nmap is not a universal vulnerability scanner." (Section 11)

## 13. Scan Types: What's Actually Happening on the Wire

You've already used `-sT` (Section 8). There's a second common TCP scan type worth understanding conceptually, because it's the default Nmap uses when it has the privileges to do so:

```
nmap -sS TARGET
```

**`-sT` (connect scan)** completes the full TCP three-way handshake with every port it tests — the same handshake any normal application performs to open a connection (Computer Networking). It's reliable and simple, and it's the only option available without elevated privileges.

**`-sS` (SYN scan)**, conceptually, sends only the first part of that handshake (a SYN packet) and reads how the target responds, without completing the connection. A response that continues the handshake indicates open; a response that actively refuses indicates closed; no response at all is the same "filtered" ambiguity you've already met. This is sometimes called a "half-open" scan because the connection is never actually finished.

This module teaches SYN scanning as a **different way of gathering the same kind of evidence**, not as a way to hide from anything. **Scan behavior — SYN or otherwise — is still detectable.** Firewalls, intrusion detection systems, and modern logging routinely see and record scan traffic regardless of which scan type produced it; treating any scan type as a way to evade a defender is both technically wrong and outside what this module teaches. Section 15 of Hands-on Practice covers exactly what a scan is likely to trigger and why that's a real-world fact worth knowing before you ever scan anything you don't own.

## 14. Timing and Responsible Scanning

Every scan you run has a real cost: time, and network traffic. A broader scan (more ports, more targets) takes longer and generates more traffic than a narrow one — Sections 5 and 6 already showed you that tradeoff directly.

This module teaches **responsible** scanning, not fastest-possible scanning. In a lab environment, speed barely matters. Against any real, authorized target, an aggressively fast scan can degrade the performance of the systems you're testing, trip rate limits or automated defenses, and generate a disproportionate amount of noise for the value of the evidence it produces. The right question before increasing a scan's aggressiveness is not "how fast can this go" — it's "does this scope and pace actually match what I'm authorized to do and what I actually need to find out."

## 15. Output Formats, Briefly

Nmap can produce output meant for a person to read directly — everything you've seen in this lesson — and it can also produce structured output (XML, grepable formats) meant to be consumed by another program: a report generator, a script that compares two scans, a larger toolchain. This module doesn't teach automation — that's a separate skill for a separate context — but it's worth knowing the capability exists: the same investigation you're learning to do by eye in this module scales, later, into something a script can do repeatedly and compare over time.

## 16. Common Mistakes

**Treating a bare scan's SERVICE column as confirmed.** It's the port-number convention, not evidence from the service itself. Section 3.

**Assuming `-p 1-1000` covers "basically everything."** It misses the entire dynamic/private range and most of the registered range. Section 5.

**Trusting a "host is down" result without considering `-Pn`.** Some hosts are configured to ignore discovery probes while still running real services. Section 9.

**Treating an OS guess as certain.** It's Nmap's best match against a fingerprint database, not a confirmed identity. Section 10.

**Believing `-sC` or NSE scripts turn Nmap into a vulnerability scanner.** They extend enumeration; they are not a substitute for real vulnerability assessment. Section 11.

**Thinking a SYN scan hides your activity.** It produces different traffic, not invisible traffic. Section 13.

**Scanning as fast and broad as possible "just to be thorough."** Coverage and responsibility are both real constraints, not just coverage alone. Section 14.

## 17. Practice

Reasoning exercises — work through them before Hands-on Practice.

1. **Explain the escalation.** Put these in order of how strong the evidence is for "a specific service is really running here," and justify the order: (a) a bare `nmap TARGET` scan, (b) an `-sV` scan, (c) an `-sV` scan plus a matching NSE script result.
2. **Diagnose the filtered port.** Section 5's `-p 20-30` scan showed port 25 as filtered. What do you actually know about port 25 right now, and what would you need to do to know more?
3. **Justify the flag.** A host reports "seems down," but you have a legitimate reason to believe it's actually running services. What do you try next, and why might that host be configured that way in the first place?
4. **Compare confidence.** Section 10 produced `Linux 5.X (embedded)` from OS detection. Name two realistic reasons this specific guess could be wrong.
5. **Correct a claim out loud.** A classmate says, "I ran `-sC` and it didn't find any vulnerabilities, so this host is secure." What's wrong with that conclusion?

## 18. Knowledge Check

1. What does a default `nmap TARGET` scan actually test, and what does it not tell you?
2. Why might you scan all ports (`-p-`) after an initial common-port scan, rather than the other way around?
3. Why is service detection (`-sV`) useful after discovering an open port, and why is it still not proof?
4. Why can UDP scan results be harder to interpret than TCP results?
5. What does `-Pn` do, and when would you actually need it?
6. Why is OS detection described as an inference rather than a fact?
7. What does Nmap's scripting engine (NSE) conceptually add, and what does it *not* turn Nmap into?
8. What is the practical difference between a TCP connect scan and a SYN scan, and why doesn't either one make a scan undetectable?

## 19. Key Takeaways

- A default scan tests a set of common TCP ports and reports their state — it does not scan every port, and it does not confirm service versions on its own.
- Narrower scans (`-p`) trade coverage for speed; broader scans (`-p-`) trade speed for coverage. Neither is "correct" — the right choice depends on what you already know and what you're trying to find out.
- Service/version detection (`-sV`) is real, stronger evidence than an open port alone — because the service itself responded — but it's still an identification, not a guarantee.
- A host that doesn't respond to discovery may still be running real services; `-Pn` skips discovery and scans anyway.
- OS detection (`-O`) infers from network behavior and can be wrong; treat it as one input, not a conclusion.
- NSE (`-sC` and beyond) extends enumeration with more specific probes. It does not turn Nmap into a vulnerability scanner.
- SYN scans (`-sS`) and connect scans (`-sT`) gather the same kind of evidence through different mechanisms — neither one hides scan activity from a defender.
- Scanning has a real cost in time and traffic; responsible scanning matches scope and pace to actual authorization and actual need.

## 20. What's Next

**Hands-on Practice** puts every command in this lesson to work in one connected investigation, on this platform's real authorized lab network. You'll discover hosts, enumerate their ports, identify services and versions, and — the actual point of the whole module — turn what you found into a documented, evidence-based conclusion about what to investigate next, exactly the way a real reconnaissance engagement starts.
