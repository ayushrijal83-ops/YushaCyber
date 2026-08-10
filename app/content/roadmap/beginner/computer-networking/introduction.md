# Introduction to Computer Networking

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what a network actually is, in terms of hosts and communication
- describe the general path data takes from your computer to a server and back
- explain the difference in *purpose* between a MAC address and an IP address (without the mechanics yet — that's next lesson)
- explain what a protocol is and why networking needs them
- run `ping` and correctly interpret both a successful and a failed result

## 2. Why This Matters

Every tool in this platform's Intermediate track — Nmap, Wireshark, Burp Suite — is a way of *looking at* or *interacting with* the network conversations this lesson introduces. Before you can scan a port, you need to know what a port even represents. Before you can read a packet capture, you need a mental model of what's traveling across the wire and why. This lesson builds that mental model from zero — not protocol trivia, but the actual shape of "how do two computers talk to each other."

## 3. What Is a Network?

A **network** is just two or more devices (called **hosts**) connected in a way that lets them exchange data. That's the whole definition — everything else is detail on top of it.

Most of the communication you'll study in this platform follows a **client/server** pattern:

- A **client** is the host that initiates a request (your laptop opening a website).
- A **server** is the host that's waiting to receive requests and respond to them (the machine hosting that website).

Every host that wants to participate in a network needs a **network interface** — the physical or virtual component that actually sends and receives data (a Wi-Fi adapter, an Ethernet port, or in this platform's simulated terminal, a virtual interface named `eth0`). No interface, no network access — this becomes important in the Hands-on Practice lesson, where a *disabled* interface is the first thing you'll learn to diagnose.

## 4. The Path of a Request

Here's the mental model to hold onto for the rest of this module. When your computer talks to a server, the data doesn't teleport there — it passes through a chain of real, physical steps:

```
Your computer
    ↓  (leaves through your network interface)
Switch or router (your local network)
    ↓  (forwarded toward its destination)
The wider network / Internet
    ↓  (arrives at the destination network)
Server
    ↓  (server processes the request, sends a reply)
Response travels back through the same kind of chain
    ↓
Your computer
```

Two things to notice here, because they matter for everything that follows:

**It's a round trip, not a one-way trip.** A request without a response isn't useful — every protocol you'll learn in this platform is fundamentally about "who says what, in what order" between two hosts.

**Something has to make forwarding decisions at each step.** A switch decides which local device to hand data to; a router decides which network to forward it toward next. You'll build a real model of that decision-making in Hands-on Practice, when you learn about routing tables and the default gateway.

## 5. Two Addresses, Two Jobs

You'll go deep on this in the next lesson, but it's worth previewing now because it trips up almost every beginner: a single host on a network is identified by **two different addresses, doing two different jobs**.

| Address | Scope | Rough job |
|---|---|---|
| **MAC address** | The local network only | "Which physical device on this network segment?" |
| **IP address** | Can span the whole Internet | "Which host, anywhere in the world?" |

For now, the only thing to remember is: **MAC ≠ IP**. They are not two names for the same thing, and they're not interchangeable — they solve different problems at different points in the journey a request takes. Core Concepts will explain exactly how each one works and why both are necessary.

## 6. Protocols: Agreed-Upon Rules

A **protocol** is simply an agreed-upon set of rules for how communication happens — what messages look like, what order they're sent in, and how each side is supposed to respond. Without a shared protocol, two hosts could technically send each other data and have absolutely no idea what to do with it, like two people trying to have a conversation using completely different languages and no interpreter.

You already rely on protocols constantly without thinking about it: when a web browser loads a page, it isn't improvising — it's following HTTP, a protocol that defines exactly how a browser should ask for a page and how a server should respond. Later lessons in this platform introduce specific protocols (DNS, TCP, HTTP) in depth. For now, just internalize the concept: **a protocol is a contract, not a suggestion** — both sides have to follow it correctly, or communication breaks down.

## 7. Observing a Network for the First Time: `ping`

**What it does:** `ping` sends a small probe to a target host and reports whether that host responded, and how quickly.

**Why it matters:** `ping` is usually the very first thing anyone runs when something isn't working — it answers the most basic question in networking: "can I even reach this host at all?" It doesn't tell you *why* something is broken, but it tells you where to start looking.

**Basic syntax:**

```bash
ping <target>
```

**Example:**

```bash
ping 10.10.10.1
```

**Expected output (success):**

```
PING 10.10.10.1 (10.10.10.1) 56(84) bytes of data.
64 bytes from 10.10.10.1: icmp_seq=1 ttl=64 time=1 ms

--- 10.10.10.1 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss
```

**What the output means:** `64 bytes from 10.10.10.1` confirms the target actually replied — the host is reachable. `time=1 ms` is the round-trip latency: how long the probe took to get there and back. `0% packet loss` means every probe you sent got a reply.

**Expected output (failure):**

```
connect: Network is unreachable
```

**What this means:** Your own machine has no usable path onto the network at all — this is a different, *earlier* failure than "the target didn't answer." You'll learn to tell these failure modes apart precisely in the Hands-on Practice lesson's troubleshooting walkthrough.

**Common mistake:** Treating a successful `ping` as proof that "the network is fine." `ping` only confirms basic reachability at a low level — a host can respond to `ping` while the actual service you care about (a website, an SSH server) is completely broken. `ping` narrows down *where* to look next; it doesn't replace checking the actual service.

**Safe exercise:** In the YushaCyber terminal, run `ping` against a target and read the output carefully — identify whether it succeeded, and if so, what the reported latency was.

## 8. Common Mistakes

**Confusing "connected to Wi-Fi" with "connected to the Internet."** A device can have a fully working connection to its local network (and even get an IP address) while the path beyond that local network is broken. This distinction — local network reachability vs. remote reachability — is exactly what the troubleshooting scenario in Hands-on Practice is built around.

**Assuming MAC and IP addresses are interchangeable.** They are not — this is covered fully next lesson, but it's worth flagging now since it's one of the most common beginner misconceptions in networking.

**Treating a protocol as optional or "close enough."** Small deviations from a protocol's rules cause real failures, not approximate ones — a request formatted 99% correctly usually just fails, the same way a sentence with one wrong word can become unparseable rather than "almost understood."

## 9. Practice

In the YushaCyber terminal:

1. Run `ping` against a target host and read every line of the output.
2. Identify which line tells you whether the host responded.
3. Identify which line tells you the round-trip latency.

## 10. Knowledge Check

1. What is the difference between a client and a server?
2. In the "path of a request" model, name at least three steps data passes through between your computer and a server.
3. At a conceptual level (without the mechanics yet), what's different about what a MAC address identifies versus what an IP address identifies?
4. What is a protocol, in your own words?
5. If `ping` succeeds, what exactly has been proven — and what has *not* been proven?

## 11. Key Takeaways

- A network is hosts exchanging data; most communication in this platform follows a client/server pattern.
- A request's journey passes through real forwarding steps (switch, router) on the way to a server, and the response retraces a similar path back.
- MAC addresses and IP addresses solve different problems — local-network identity vs. global reachability. They are never the same thing.
- A protocol is a shared rulebook both sides must follow exactly for communication to succeed.
- `ping` tests basic reachability and latency — a useful first diagnostic step, not proof that everything is working.

## 12. What's Next

**Core Concepts** goes deep on the addressing you previewed here: how MAC addresses work at the local-network level, how IPv4 addresses are structured, what a subnet is and how to calculate one, and how ports let a single IP address host many different services at once.
