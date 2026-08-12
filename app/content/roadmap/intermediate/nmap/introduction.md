# Introduction to Nmap

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what Nmap actually does and why network scanning exists as a discipline
- use the words **host**, **port**, and **service** correctly and distinguish them from each other
- explain why a port number alone is not proof of what's running behind it
- explain, at a conceptual level, why TCP and UDP scans behave differently
- correctly interpret the three port states — **open**, **closed**, **filtered**
- explain the difference between host discovery and port scanning

## 2. Why This Matters

You've spent this roadmap building a model of how a network actually works: hosts, IP addresses, ports, TCP, UDP, the request path from an interface to a server and back. Nmap is the tool that turns that model into a question you can ask a real network: *what's actually here, and what's it running?*

That question is the first step of almost every security engagement that follows this module. Before you can test a web application, you need to know it's there and what's in front of it. Before you can assess a host's exposure, you need to know which doors are open. Reconnaissance and enumeration — the Red Team modules waiting later on this roadmap — are built entirely on the skill this module teaches: turning scan output into evidence, and evidence into a decision about what to look at next.

This is not a module about attacking anything. Nmap discovers and enumerates. What you do with what it finds is a separate, later question — and one this module deliberately does not answer, because jumping to "exploit it" before you understand what you're looking at is how beginners get themselves — and their targets — into trouble.

## 3. What Nmap Actually Is

**Nmap** ("Network Mapper") is a network scanning tool that discovers hosts on a network and investigates what those hosts are running: which ports respond, what services appear to be listening, and, with more probing, what software and version those services are likely running.

The most useful way to think about Nmap is as an **investigation tool**, not a magic answer machine. Every Nmap command sends a small number of carefully constructed network probes and reports back how the target responded — or didn't. Nmap does not "know" what's running on a target; it *infers* it from observable network behavior, the same way you'd infer a store is open from its lights being on and its door unlocked, without being able to see inside. Most of this module is really about learning to read that inference correctly: what the evidence supports, what it merely suggests, and what it says nothing about at all.

That framing matters because it sets up the model this whole module follows:

```
TARGET
  ↓
HOST DISCOVERY        is anything answering at this address at all?
  ↓
PORT DISCOVERY         which specific doors respond?
  ↓
SERVICE DETECTION      what does the door claim to be?
  ↓
VERSION DETECTION      what does the door claim to be running?
  ↓
OS / NETWORK CLUES      what does the surrounding behavior suggest?
  ↓
EVIDENCE INTERPRETATION   what do I actually know now, and how confident am I?
  ↓
NEXT INVESTIGATION      what does this evidence tell me to look at next?
```

Every section from here to the end of Hands-on Practice is one step of that chain.

## 4. Hosts, Ports, and Services

Three words you'll use constantly, and mixing them up is the single most common way beginners talk themselves into wrong conclusions.

**Host** — a device reachable on a network, identified by an IP address. In this module, a host is something Nmap can address and ask questions of: a server, a workstation, a router — anything with a network stack. You already met hosts and IP addressing in Computer Networking.

**Port** — a numbered endpoint (0–65535) on a host that a running program has claimed, so network traffic addressed to that number reaches that program instead of some other one on the same machine. You met ports and sockets in Computer Networking too; Nmap is largely a tool for finding out, from the outside, which of a host's 65,536 possible ports currently have something behind them.

**Service** — the actual program or protocol answering on a port: an SSH server, a web server, a database, a DNS resolver. This is the thing you actually care about — a port is just the address it happens to be listening at.

The relationship: a host has ports; a subset of those ports have services behind them; Nmap's job, in stages, is to find the host, find which ports respond, and then investigate what service is actually behind each one.

## 5. A Port Number Is Not Proof

Here is the single most important correction in this lesson, and it's worth getting right before you run a single command.

**"Port 80 is open" does not mean "HTTP is definitely running."**

Port numbers below 1024 are **well-known ports** — a long-standing convention (port 22 for SSH, port 80 for HTTP, port 443 for HTTPS) that most software follows by default. Ports 1024–49151 are **registered ports**, used by convention for specific applications but far less rigidly enforced. Ports 49152–65535 are **dynamic/private ports**, typically used for short-lived outbound connections rather than services waiting for traffic.

But "convention" is exactly that — a convention, not a law enforced by the network. Nothing stops an administrator from running a web server on port 8443, SSH on port 2222, or a completely custom service on port 80. When you see a port is open, you know precisely one fact: **something answered at that address**. You do not yet know what.

The reasoning to build is:

> *"Port 22 is open"* does **not** automatically mean *"SSH is definitely running."*
> It means the port is reachable. **Service detection** (Core Concepts §7) provides stronger evidence about what's actually listening — and even that evidence is an identification, not a certainty.

Keep that distinction in your head through the rest of this module. Every section from here on is really about *how much confidence a particular piece of evidence deserves* — a port being open is weak evidence of a specific service; a version string returned by the service itself is much stronger evidence, but still not absolute proof.

## 6. TCP vs. UDP, Briefly

You built the real model of TCP and UDP in Computer Networking — the three-way handshake, connection-oriented vs. connectionless delivery. This module doesn't re-teach that; it uses it.

**TCP** is connection-oriented: a client and server perform a handshake before data flows. That handshake gives a scanner a clean, reliable signal — if a host responds to the connection attempt, something is there; if it actively refuses, nothing is there; if nothing comes back at all, something in between (a firewall, most likely) is happening. This is why TCP scanning is fast and its results are usually unambiguous.

**UDP** has no handshake. A UDP scan sends a probe and waits — and many services simply don't respond to a probe that isn't a well-formed request in their specific protocol. Silence is genuinely ambiguous: it can mean the port is open and the service just didn't answer this particular probe, or it can mean a firewall silently dropped the packet, or it can mean nothing is listening at all. That ambiguity is exactly why UDP scanning tends to be slower (Nmap often has to wait out a timeout, and sometimes retry, before concluding anything) and why its results demand more careful reading than a TCP scan's do. You'll see this concretely in Core Concepts §8.

## 7. Port States: Open, Closed, Filtered

Nmap reports one of three states for each port it tests, and all three get misread by beginners constantly. Get these exactly right now.

**Open** — a service is actively listening on this port and accepted (or would accept) a connection. This is the strongest of the three states: something is there, and it's willing to talk.

**Closed** — the host responded, but nothing is listening on that specific port. This is a critical distinction to hold onto:

> **WRONG:** "Closed means the machine is offline."
> **CORRECT:** "Closed means the host responded but no service is listening on that port."

A closed port is actually *evidence the host is up*. A machine that doesn't exist, or is unreachable, doesn't get to say "closed" — it simply doesn't answer at all (which Nmap reports differently, as the host being down — Section 8).

**Filtered** — Nmap cannot determine whether the port is open, because something (almost always a firewall or packet filter) is blocking the probe without giving a clear answer either way.

> **WRONG:** "Filtered means the port is closed."
> **CORRECT:** "Filtered means Nmap cannot determine whether the port is open because packet filtering prevents a clear conclusion."

Filtered is not a third kind of "sort of closed" — it's Nmap being honest that the evidence is inconclusive. You'll see a real filtered port in Hands-on Practice, and the correct response to seeing one is *not* "that port is closed, move on" — it's "I don't actually know what's here."

## 8. Host Discovery vs. Port Scanning

These are two different questions, and Nmap answers them differently depending on what you ask it.

**Host discovery** asks: *is anything at this address at all?* It's typically fast and doesn't investigate any specific port — it's a sweep across a range of addresses to find out which ones are worth investigating further.

**Port scanning** asks: *of this one host, which specific ports respond, and how?* It's a deeper, more targeted investigation of a single address you've already decided is worth looking at.

The relationship between them matters: **a host can be alive while the specific port you're testing is closed.** Discovering that a host exists tells you nothing about what's running on it — those are two separate steps in the chain from Section 3, and conflating them is a common beginner mistake. A host being "up" is not the same claim as "this port is open," and a host being unreachable to a discovery probe doesn't necessarily mean every port on it is closed either — some hosts are configured to not respond to discovery probes at all while still running real services, which is exactly why Nmap gives you a way to skip discovery and scan ports directly (`-Pn` — Core Concepts §9).

Here is real host-discovery output, captured by running this platform's own Nmap simulator (`app/core/terminal/network.py`) against the same authorized lab network the Hands-on Practice mission uses — not invented output:

```
$ nmap -sn 10.10.10.0/24

Starting Nmap

Nmap scan report for 10.10.10.1
Host is up.

Nmap scan report for 10.10.10.10
Host is up.

Nmap scan report for 10.10.10.20
Host is up.

Nmap scan report for 10.10.10.30
Host is up.

Nmap scan report for 10.10.10.53
Host is up.

Nmap done: 6 IP addresses (5 hosts up) scanned.
```

Notice what this command did *not* do: it never asked about a single port. It swept an entire address range (`10.10.10.0/24`, the same CIDR notation you learned in Computer Networking) and reported only which addresses answered. Five hosts answered out of six scanned — the sixth was configured to not respond to discovery probes, which you'll investigate directly in Hands-on Practice using `-Pn`.

## 9. Common Mistakes

**Assuming an open port proves a specific service.** It's evidence, not proof. Section 5.

**Assuming closed means offline.** A closed port is a host actively telling you nothing is there — which requires the host to be reachable in the first place. Section 7.

**Assuming filtered means closed.** Filtered means "I can't tell," not "it's shut." Treat it as an open question, not a dead end. Section 7.

**Treating host discovery and port scanning as the same step.** They answer different questions, and a host can pass one and be irrelevant to the other. Section 8.

**Forgetting that TCP and UDP are separate investigations.** A host can show completely different results depending on which protocol you scan — this isn't a bug, it's two genuinely different kinds of evidence. Section 6.

## 10. Practice

Reasoning exercises — no scanning yet. Work through these before Core Concepts.

1. **State the distinction.** In your own words, what is the difference between a host, a port, and a service? Give a real-world analogy for each.
2. **Correct the claim.** A classmate says "I scanned the server and port 3306 was open, so MySQL is definitely running." What's wrong with that conclusion, and what would make it stronger evidence?
3. **Diagnose the state.** You scan a host and get "closed" for port 21. Does that tell you the host is reachable? Does it tell you FTP is not installed anywhere on that host? Explain both answers.
4. **Read the discovery output.** Look again at the `-sn` output in Section 8. If you were told to investigate this network further, which single fact from that output would you use to decide where to start, and why?
5. **Separate the questions.** A host answers a discovery probe but every port you scan on it comes back closed. Is that a contradiction? Explain using Section 8's distinction.

## 11. Knowledge Check

1. What is Nmap, and what kind of question does it answer?
2. Why is "port 80 is open" not the same claim as "HTTP is running"?
3. What's the difference between the well-known, registered, and dynamic/private port ranges?
4. Why can a TCP scan usually give a clearer answer than a UDP scan for the same port?
5. What does "closed" actually mean? What does it rule out, and what does it not rule out?
6. What does "filtered" mean, and why is it not the same as "closed"?
7. What is the difference between host discovery and port scanning, and why does the difference matter?

## 12. Key Takeaways

- Nmap is an investigation tool: it infers what's on a network from observable behavior, not a tool that "knows" the answer outright.
- Host, port, and service are three distinct things — a host has ports, and a subset of those ports have services behind them.
- A port number is a convention, not a guarantee. An open port is evidence of a service, not proof of one.
- TCP scanning gives cleaner signals because of the handshake; UDP's lack of one makes silence genuinely ambiguous.
- Open means something is listening. Closed means the host responded but nothing is there. Filtered means Nmap can't tell — treat it as unresolved, not as closed.
- Host discovery (is anything here?) and port scanning (what's listening on this one host?) are separate questions with separate answers.

## 13. What's Next

**Core Concepts** puts commands behind every idea in this lesson. You'll run a basic scan and learn exactly what it asks Nmap to determine, narrow it to specific ports and ranges, and see the real tradeoff between coverage and time. You'll meet service and version detection — the evidence that actually strengthens the "what's running here" question this lesson raised — and OS detection, framed honestly as an inference rather than a certainty. Every example uses real output captured from this platform's own lab network, the same one you'll investigate yourself in Hands-on Practice.
