# Hands-on Practice: Network Investigation

## 1. What You Will Learn

This lesson is an investigation, not a tour. By the end of it you should be able to:

- open a capture, orient yourself in it, and describe what you're looking at before touching a filter
- identify the endpoints, protocols and ports of a conversation from evidence alone
- locate a TCP handshake and explain what each packet proves — not merely point at three lines
- investigate a DNS lookup and state what evidence identifies it as DNS
- analyse an HTTP exchange in a capture and connect it to Web Fundamentals
- narrow a noisy capture step by step, with a stated reason for every narrowing
- write an evidence-based investigation report with an honest confidence level
- keep **observation**, **interpretation** and **conclusion** separate, permanently

## 2. Authorization Comes First

Everything in this lesson runs against fixed, simulated captures built into this platform. No real packet is captured, transmitted, or inspected — and that is the correct environment for learning this, not a compromise.

State the boundary plainly, because packet analysis is the point in this roadmap where it stops being abstract:

**Capturing network traffic means obtaining a copy of communications that may not be yours.** On a network you own, or one you have explicit written authorization to analyse, that's ordinary engineering. Anywhere else it is interception, and no amount of curiosity or good intent changes what it is.

Legitimate contexts where this skill is used every day:

- your own systems, networks and test environments
- an employer's network, in a role authorized to analyse it
- an engagement with documented, agreed scope
- an incident response with proper authority
- purpose-built training environments — this one included

**This module does not teach**, and will not help with: intercepting third parties' traffic, harvesting credentials from captures, session hijacking, capturing on networks you don't have authority over, defeating encryption on traffic that isn't yours, or evading network monitoring. Those aren't gaps in the material. They're the line, and it does not move.

One more practical point worth internalising early: captures frequently contain sensitive data even when you were entirely authorized to take them. Treat a capture file as sensitive by default — store it deliberately, share it deliberately, and delete it when the investigation that justified it is finished.

## 3. The Lab Environment

Open the environment and see what's available:

```
$ capture
Available captures: dns, handshake, http, icmp, investigation, mixed
Active capture: none
```

Six fixed captures. Each is deterministic — identical every time you open it, so a conclusion you draw today is still checkable tomorrow.

| Capture | Packets | What it contains |
|---|---|---|
| `handshake` | 3 | A TCP three-way handshake, isolated |
| `dns` | 2 | One DNS query and its response |
| `http` | 8 | A complete HTTP request/response inside a full TCP connection lifecycle |
| `icmp` | 2 | One ping request and reply |
| `mixed` | 32 | Several protocols interleaved — the noisy one |
| `investigation` | 45 | Mixed traffic containing one exchange that doesn't fit the rest |

**The hosts.** Deliberately, you are not given a table of host names and roles. The captures carry IP addresses and behaviour, and nothing else — no asset inventory, no labels. That is realistic: in a genuine investigation you very often start with addresses and have to determine roles from what the hosts actually *do*. Working out which address is the client, which is a DNS server, and which is a web server — from evidence, in Exercise 1 — is part of the exercise, not a prerequisite for it.

**The commands**, from Introduction §13:

| Command | Purpose |
|---|---|
| `capture` | List captures / show the active one |
| `capture NAME` | Open a capture |
| `packets` | List every packet in the open capture |
| `show N` | Expand packet N's protocol layers |
| `follow N` | Show every packet in packet N's conversation |
| `filter EXPR` | Show only packets matching a display filter |

## 4. The Investigation Workflow

Every exercise below follows the same seven steps. Learn the shape, because it's the part that transfers to real Wireshark and to captures nobody has prepared for you.

```
CAPTURE      obtain or open the evidence
  ↓
ORIENT       what is here? how much? what protocols? who's involved?
  ↓
FILTER       narrow deliberately — one dimension at a time, with a reason
  ↓
IDENTIFY     endpoints, protocols, ports, direction, roles
  ↓
FOLLOW       reconstruct the conversation the packet belongs to
  ↓
ANALYZE      what does the evidence support? what does it rule out?
  ↓
CONCLUDE     state findings, evidence, and confidence — separately
```

The step people skip is **ORIENT**. Jumping straight to a filter means you're searching for what you already expect, which is precisely how you miss the thing you didn't expect. Look at the whole capture first, even when it's big. Especially when it's big.

## 5. Exercise 1 — Find the Conversation

**Objective:** given a capture and no other information, identify who is talking to whom, over what protocol, using which ports — and say what communication appears to be happening.

**Do this:**

```
$ capture icmp
2 packets loaded from 'icmp'.
Type 'packets' to list them.

$ packets
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
1    0.001     10.10.10.20     10.10.10.10     ICMP      Echo (ping) request
2    0.002     10.10.10.10     10.10.10.20     ICMP      Echo (ping) reply
```

**Now inspect the detail:**

```
$ show 1
Packet #1
Time: 0.001000
Length: 98 bytes

Ethernet II
    Source: 02:42:0a:0a:0a:14
    Destination: 02:42:0a:0a:0a:0a

IPv4
    Source: 10.10.10.20
    Destination: 10.10.10.10
    TTL: 64

ICMP
    Type: Echo (ping) request
```

**Reasoning — work through it before reading on.**

Who initiated? `10.10.10.20` sent the request; `10.10.10.10` sent the reply. Source and destination reverse between the two packets, which is the signature of a request/reply pair.

What protocol? ICMP. And notice what's *absent* from the detail view: **there is no TCP or UDP layer, and therefore no ports at all.** That's not an omission — ICMP sits directly on top of IP and doesn't use ports. If you went looking for a port number here you would find nothing, and the reason is structural.

What communication is happening? An echo request and its reply — a reachability check. `10.10.10.20` asked "are you there?" and `10.10.10.10` answered.

**What you can state:**

- `10.10.10.20` initiated a reachability check to `10.10.10.10`.
- `10.10.10.10` responded, so it was reachable and responsive at that moment.
- Round-trip took approximately one millisecond, consistent with a local network.
- No transport-layer ports are involved, because ICMP doesn't use them.

**What you cannot state:** anything about what services either host runs, what applications were involved, or why the check happened. A ping proves reachability. Nothing more.

**Common mistake:** looking for a port number and assuming the capture is incomplete when there isn't one. The absence of a transport layer is itself a fact about the protocol — read it as evidence rather than as a gap.

**Now try it yourself.** Run the same procedure on `capture handshake`. Identify the two endpoints, both ports, the protocol, and which host initiated. Write down what evidence supports each answer before moving to Exercise 2.

## 6. Exercise 2 — The TCP Handshake, With Reasoning

**Objective:** locate a three-way handshake and explain what each packet proves. Finding three lines is not the exercise. **Explaining them is.**

**Do this:**

```
$ capture handshake
3 packets loaded from 'handshake'.
Type 'packets' to list them.

$ packets
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
1    0.001     10.10.10.20     10.10.10.10     TCP       SYN
2    0.002     10.10.10.10     10.10.10.20     TCP       SYN, ACK
3    0.003     10.10.10.20     10.10.10.10     TCP       ACK
```

Inspect all three with `show 1`, `show 2` and `show 3`. The full output is in Core Concepts §3 — don't take it from there, run it, and read the flags and ports yourself.

**Required reasoning.** For each packet, answer three questions. Write the answers down; this is the exercise.

**Packet 1 — SYN**

- *What does it mean?* `10.10.10.20` is requesting a connection to port 80 on `10.10.10.10`.
- *What evidence demonstrates it?* `Flags: SYN` with no ACK. A lone SYN is the only packet in a normal connection carrying SYN without ACK, which is what marks it as the connection's first packet rather than one from the middle.
- *What can you NOT conclude?* That a connection was established. This is a request. Requests can go unanswered — the port could be closed, filtered, or the host gone.

**Packet 2 — SYN, ACK**

- *What does it mean?* The server acknowledges the client's request and opens its own direction.
- *What evidence demonstrates it?* Three things: `Flags: SYN, ACK`; the IP addresses reversed from packet 1; the ports reversed (source 80, destination 49152). Same two endpoints, opposite direction.
- *What does this prove that packet 1 could not?* **A service was actually listening on port 80 and accepted the attempt.** A closed port would have refused; a filtered port would have produced silence. This packet is the strongest single piece of evidence in the handshake, and it is exactly what the Nmap module's "open" port state means, observed from the traffic side.

**Packet 3 — ACK**

- *What does it mean?* The client acknowledges the server's SYN. Both directions are established; the connection is open.
- *What evidence demonstrates it?* `Flags: ACK` alone — no SYN, because the client has nothing left to synchronise. And the length: **66 bytes against 74** for the two previous packets, consistent with a pure acknowledgement carrying no options and no application data.
- *What can you conclude overall?* The connection was successfully established between `10.10.10.20:49152` and `10.10.10.10:80`, in roughly three milliseconds.

**The standard to hold yourself to.** Compare these two statements:

> "I saw SYN, SYN-ACK, ACK, so it's a handshake."

> "Packet 1 is a lone SYN from `10.10.10.20:49152` to `10.10.10.10:80`, so that host initiated. Packet 2 is a SYN-ACK from `10.10.10.10:80` back to the same client port, so a service was listening and accepted. Packet 3 is a lone ACK completing the exchange. The connection was established."

The first is pattern recognition. The second is analysis, and every clause in it names its evidence. In an incident review, only the second one survives being questioned.

**Extension.** Open `capture http` and find the handshake there. Then find the *termination* — which packets end the connection, and what do the flags tell you about which side closed first?

## 7. Exercise 3 — DNS Investigation

**Objective:** identify a queried hostname, the DNS server that answered, the response, and the returned record — then answer the question that matters: *what evidence proves this was a DNS lookup?*

**Do this:**

```
$ capture dns
2 packets loaded from 'dns'.
Type 'packets' to list them.

$ packets
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
1    0.001     10.10.10.20     10.10.10.53     DNS       Standard query A example.training
2    0.002     10.10.10.53     10.10.10.20     DNS       Standard query response A example.training 10.10.10.10
```

Inspect both packets with `show 1` and `show 2` (full output in Core Concepts §9).

**Extract the facts:**

| Question | Answer | Evidence |
|---|---|---|
| What hostname was queried? | `example.training` | DNS application data in packet 1 |
| Who made the query? | `10.10.10.20` | Source IP of packet 1 |
| Which server answered? | `10.10.10.53` | Source IP of packet 2 |
| What record type? | `A` | "Standard query **A**" |
| Was it successful? | Yes | A matching response exists, carrying an answer |
| What was returned? | `10.10.10.10` | The address in the response |

**Now the real question: what evidence proves this was a DNS lookup?**

The weak answer is "the Protocol column says DNS." Core Concepts §20 explained why that's a decoded conclusion rather than a transmitted fact. Here is the evidence that actually supports it, and notice it's four independent things:

1. **Transport and port.** UDP with destination port 53 on the query, and source port 53 on the response. Port 53 is DNS by convention — a clue, not proof, but a strong starting point.
2. **Message structure.** The application data has the shape of a DNS query: a record type (`A`) and a queried name (`example.training`).
3. **The query/response pairing.** The response references the same name and arrives back at the client's same ephemeral port `53412`. It answers *that* query specifically.
4. **The behaviour of the exchange.** Request, single reply, done — no handshake, no shutdown. That's the UDP shape, and it's what DNS looks like.

Four independent signals agreeing is what makes this a confident identification. Any one alone — especially the port — would be considerably weaker. That is the evidence-weighing discipline from Core Concepts §20, applied.

**The correlation worth doing.** The response returned `10.10.10.10`. Hold onto that address: Exercise 4 shows the same client connecting to it. A DNS answer matching a subsequent connection destination is one of the most reliable analytical moves in packet analysis — it tells you which *name* a host was actually trying to reach, when the connection itself only shows an IP.

**Now try it yourself.** Open `capture mixed` and run `filter dns`. Six query/response pairs. Answer: which host asked? Which server answered? How many distinct names, and were all six answered? Does the client use the same ephemeral port each time — and what does your answer imply?

## 8. Exercise 4 — HTTP Investigation

**Objective:** locate an HTTP exchange and identify the request method, host, path, status code and response — connecting what you see to Web Fundamentals.

**Do this:**

```
$ capture http
8 packets loaded from 'http'.
Type 'packets' to list them.

$ filter http
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
4    0.004     10.10.10.20     10.10.10.10     HTTP      GET /index.html HTTP/1.1
6    0.006     10.10.10.10     10.10.10.20     HTTP      HTTP/1.1 200 OK  Content-Type: text/html
```

Two packets carry the application exchange. Inspect them with `show 4` and `show 6` (full output in Core Concepts §11).

**Extract the facts:**

| Element | Value | Evidence |
|---|---|---|
| Method | `GET` | Request line, packet 4 |
| Path | `/index.html` | Request line, packet 4 |
| Protocol version | `HTTP/1.1` | Request line, packet 4 |
| Client | `10.10.10.20:49153` | Source IP and port, packet 4 |
| Server | `10.10.10.10:80` | Destination IP and port, packet 4 |
| Status code | `200 OK` | Status line, packet 6 |
| Content type | `text/html` | Status line, packet 6 |

**The Host header.** Web Fundamentals taught you that `Host` is what tells a server *which site* was requested when one server hosts many. This platform's simulator summarises each HTTP packet as a single line — the request line or the status line — and does not model individual headers, so `Host` is not visible in this capture. That is a real limitation of the simulator, stated rather than papered over. In real Wireshark, following the stream shows every header, and `Host` is usually the first thing you'd read after the request line. Here, the closest equivalent evidence is the DNS correlation from Exercise 3: the client resolved `example.training` to `10.10.10.10`, and this connection goes to `10.10.10.10`.

**Now put HTTP back in context.** Filtering to `http` gave you the application exchange, but it hid the transport that carried it. Follow the conversation:

```
$ follow 4
Conversation: tcp:10.10.10.10:80<->10.10.10.20:49153

Packets:
  #1  TCP    SYN
  #2  TCP    SYN, ACK
  #3  TCP    ACK
  #4  HTTP   GET /index.html HTTP/1.1
  #5  TCP    ACK
  #6  HTTP   HTTP/1.1 200 OK  Content-Type: text/html
  #7  TCP    FIN, ACK
  #8  TCP    ACK
```

**This is the point of the exercise.** The filtered view showed you two packets. The conversation shows you eight, and the six extra ones are not noise — they're the reason the two were possible:

```
packets 1-3   the TCP connection had to be established first
packet  4     the request
packet  5     the server acknowledged RECEIVING the request
packet  6     the server's actual answer
packets 7-8   the connection was closed
```

Note packet 5 specifically. TCP acknowledging receipt is not the application answering. Those are separate events, and the gap between them is where "the server never got my request" and "the server got it and took four seconds to think" become distinguishable — two different problems with two different fixes.

**Connect it to Web Fundamentals.** Everything you learned there — request line, method, path, status code, `Content-Type` — is here, exactly as taught, wrapped in the transport that delivers it. What packet analysis adds is the layer below: you can now see not just *what* the application said, but whether the connection carrying it opened cleanly, how long each step took, and how it ended.

**Now try it yourself.** Open `capture investigation` and run `filter http`. Several exchanges. Answer: how many distinct paths were requested? Did every request receive a response? Are they all to the same server?

## 9. Exercise 5 — Filtering a Noisy Capture

**Objective:** take a capture too large to read line by line and narrow it deliberately, with a stated reason for each step.

**Do this — and start by orienting, not filtering:**

```
$ capture mixed
32 packets loaded from 'mixed'.
Type 'packets' to list them.

$ packets
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
1    0.001     10.10.10.20     10.10.10.53     DNS       Standard query A example.training
2    0.002     10.10.10.53     10.10.10.20     DNS       Standard query response A example.training 10.10.10.10
3    0.003     10.10.10.20     10.10.10.10     TCP       SYN
4    0.004     10.10.10.10     10.10.10.20     TCP       SYN, ACK
5    0.005     10.10.10.20     10.10.10.10     TCP       ACK
6    0.006     10.10.10.20     10.10.10.10     HTTP      GET /index.html HTTP/1.1
7    0.007     10.10.10.10     10.10.10.20     HTTP      HTTP/1.1 200 OK
8    0.008     10.10.10.20     10.10.10.1      ICMP      Echo (ping) request
9    0.009     10.10.10.1      10.10.10.20     ICMP      Echo (ping) reply
```

(The listing continues to packet 32 — run it and read the whole thing.)

**Orientation, before any filter.** From the full list you can already say: five protocols are present (DNS, TCP, HTTP, ICMP and UDP); `10.10.10.20` appears in nearly every packet, which suggests it's the observation point or the host of interest; three other addresses appear alongside it; and all 32 packets fall within the first 32 milliseconds of the capture. None of that required a filter, and all of it shapes what you filter for.

**The question:** *this client made a web request. Show me the complete exchange and everything that led up to it.*

**Step 1 — narrow to the protocol that answers the question.**

*Reason:* the question is about a web request, and HTTP is the application protocol.

```
$ filter http
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
6    0.006     10.10.10.20     10.10.10.10     HTTP      GET /index.html HTTP/1.1
7    0.007     10.10.10.10     10.10.10.20     HTTP      HTTP/1.1 200 OK
```

From 32 packets to 2. One request, one response, between `10.10.10.20` and `10.10.10.10`.

**Step 2 — narrow by host, to see everything involving that server.**

*Reason:* the HTTP filter showed only the application layer. The transport that carried it is not labelled HTTP and was excluded — Core Concepts §17 explains exactly why.

```
$ filter ip.addr == 10.10.10.10
```

Now the handshake packets appear alongside the HTTP ones. `ip.addr` matches either direction, so you get both halves of the conversation rather than one.

**Step 3 — narrow by port, to confirm the service endpoint.**

*Reason:* an address alone doesn't distinguish which service on that host you're looking at. A port does.

```
$ filter tcp.port == 80
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
3    0.003     10.10.10.20     10.10.10.10     TCP       SYN
4    0.004     10.10.10.10     10.10.10.20     TCP       SYN, ACK
5    0.005     10.10.10.20     10.10.10.10     TCP       ACK
6    0.006     10.10.10.20     10.10.10.10     HTTP      GET /index.html HTTP/1.1
7    0.007     10.10.10.10     10.10.10.20     HTTP      HTTP/1.1 200 OK
```

Five packets: the full handshake plus the application exchange. Note this filter found packets 6 and 7 that `filter tcp` would have missed — filtering on a **field** rather than a protocol **label**, exactly the cross-check habit from Core Concepts §17.

**Step 4 — follow the conversation.**

*Reason:* to read the exchange in order as a single unit, and confirm nothing was left out by the narrowing.

```
$ follow 6
```

**Step 5 — find what led up to it.**

*Reason:* the client connected to `10.10.10.10`. How did it know to? Look for a name lookup that returned that address.

```
$ filter dns
```

Packet 1 queried `example.training`; packet 2 answered `10.10.10.10` — the address the client then connected to. **The DNS lookup and the HTTP connection fit together**, and you have now reconstructed the full sequence from a 32-packet capture:

```
resolve example.training  →  10.10.10.10        packets 1-2
open a TCP connection to 10.10.10.10:80          packets 3-5
GET /index.html                                  packet 6
HTTP/1.1 200 OK                                  packet 7
```

**What made that work.** Not the filters — the reasons. Every step narrowed along a specific dimension (protocol → host → port → conversation → correlation) because a stated question required it. If you memorise the filters and skip the reasons, you can reproduce this exact investigation and nothing else.

**Now try it yourself.** Same capture, different question: *what did this client ping, and how many times?* Choose your filters, state your reason for each, and answer with evidence.

## 10. Exercise 6 — The Investigation Report

**Objective:** investigate a capture end to end and produce a written report separating observation, interpretation and conclusion, with an honest confidence level.

This is the exercise that matters most. Everything before it was skill-building for this.

**Step 1 — CAPTURE and ORIENT.**

```
$ capture investigation
45 packets loaded from 'investigation'.
Type 'packets' to list them.

$ packets
```

Read the whole listing. Forty-five packets is genuinely readable, and reading it first is the habit worth building — filters find what you look for, and orientation finds what you didn't.

**Step 2 — establish what normal looks like here.**

Before anything can stand out, you need a baseline. Filter by protocol and characterise each:

```
$ filter dns
```

Seven query/response pairs, all from `10.10.10.20` to `10.10.10.53`, all answered, all resolving to `10.10.10.10`.

```
$ filter icmp
```

Three ping request/reply pairs between `10.10.10.20` and `10.10.10.1`.

```
$ filter http
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
6    0.006     10.10.10.20     10.10.10.10     HTTP      GET /index.html HTTP/1.1
7    0.007     10.10.10.10     10.10.10.20     HTTP      HTTP/1.1 200 OK
28   0.028     10.10.10.20     10.10.10.10     HTTP      GET /page0.html HTTP/1.1
29   0.029     10.10.10.10     10.10.10.20     HTTP      HTTP/1.1 200 OK
32   0.032     10.10.10.20     10.10.10.10     HTTP      GET /page1.html HTTP/1.1
33   0.033     10.10.10.10     10.10.10.20     HTTP      HTTP/1.1 200 OK
36   0.036     10.10.10.20     10.10.10.10     HTTP      GET /page2.html HTTP/1.1
37   0.037     10.10.10.10     10.10.10.20     HTTP      HTTP/1.1 200 OK
40   0.040     10.10.10.20     10.10.10.10     HTTP      GET /page3.html HTTP/1.1
41   0.041     10.10.10.10     10.10.10.20     HTTP      HTTP/1.1 200 OK
```

Five requests to `10.10.10.10`, every one answered `200 OK`.

**Roles, derived from behaviour rather than from labels:**

- `10.10.10.20` — initiates everything, always uses ephemeral source ports. **A client.**
- `10.10.10.53` — only ever answers DNS queries on port 53. **A DNS server.**
- `10.10.10.10` — serves HTTP on port 80, and is the address DNS returns. **A web server.**
- `10.10.10.1` — answers pings; `.1` is conventionally a gateway address, but *conventionally* is doing real work in that sentence. The capture proves it responds to ICMP. It does not prove it routes anything.

**Step 3 — a detour worth taking, because it teaches restraint.**

Look carefully at packets 26–29 in the full listing:

```
26   0.026     10.10.10.20     10.10.10.10     TCP       SYN
27   0.027     10.10.10.10     10.10.10.20     TCP       SYN, ACK
28   0.028     10.10.10.20     10.10.10.10     HTTP      GET /page0.html HTTP/1.1
29   0.029     10.10.10.10     10.10.10.20     HTTP      HTTP/1.1 200 OK
```

SYN, SYN-ACK, then straight to the request — **no completing ACK, and no FIN afterwards.** The same pattern repeats at 30–33, 34–37 and 38–41. Compare that to the clean, complete lifecycle in packets 3–7 and in the `http` capture.

What should you do with that? Exactly this:

- **Observation:** four connections in this capture show SYN and SYN-ACK followed immediately by application data, with no completing ACK and no termination packets.
- **Interpretation:** the most likely explanations are that those packets did not cross the observation point, or that the capture recorded a subset. A missing packet in a capture is far more often a limit of the capture than a fact about the network — Introduction §4.
- **Conclusion:** insufficient evidence to conclude anything about the network from this. It is a property of the capture worth noting, not a finding.

That is the discipline in miniature. The tempting move is to declare something wrong. The correct move is to note it, explain what would distinguish the possibilities, and not spend the investigation on it.

**Step 4 — find what doesn't fit.**

Scan the listing again with the baseline in mind. Packets 42–45 involve an address that appears nowhere else:

```
$ filter ip.addr == 10.10.10.77
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
42   0.042     10.10.10.20     10.10.10.77     TCP       SYN
43   0.043     10.10.10.77     10.10.10.20     TCP       SYN, ACK
44   0.044     10.10.10.20     10.10.10.77     TCP       ACK
45   0.045     10.10.10.20     10.10.10.77     TCP       Unrecognized binary payload
```

**Step 5 — INSPECT.**

```
$ show 42
Packet #42
Time: 0.042000
Length: 74 bytes

Ethernet II
    Source: 02:42:0a:0a:0a:14
    Destination: 02:42:0a:0a:0a:4d

IPv4
    Source: 10.10.10.20
    Destination: 10.10.10.77
    TTL: 64

TCP
    Source Port: 49999
    Destination Port: 4444
    Flags: SYN

Conversation: tcp:10.10.10.20:49999<->10.10.10.77:4444
```

```
$ show 45
Packet #45
Time: 0.045000
Length: 90 bytes

Ethernet II
    Source: 02:42:0a:0a:0a:14
    Destination: 02:42:0a:0a:0a:4d

IPv4
    Source: 10.10.10.20
    Destination: 10.10.10.77
    TTL: 64

TCP
    Source Port: 49999
    Destination Port: 4444
    Flags: PSH, ACK

Conversation: tcp:10.10.10.20:49999<->10.10.10.77:4444
```

**Step 6 — FOLLOW.**

```
$ follow 42
Conversation: tcp:10.10.10.20:49999<->10.10.10.77:4444

Packets:
  #42  TCP    SYN
  #43  TCP    SYN, ACK
  #44  TCP    ACK
  #45  TCP    Unrecognized binary payload
```

**Step 7 — ANALYZE, keeping the three levels apart.**

**OBSERVATIONS** — facts readable directly from the capture, each pointing at a packet:

- The client `10.10.10.20` opened a TCP connection to `10.10.10.77` on port `4444` (packets 42–44: SYN, SYN-ACK, ACK — a complete handshake).
- The handshake completed, so a service was listening on port 4444 and accepted (packet 43).
- One packet of application data was sent client → server (packet 45, `PSH, ACK`, 90 bytes).
- The payload was not identified by the decoder — reported as an unrecognised binary payload (packet 45).
- `10.10.10.77` appears in no other packet in this capture.
- No DNS query in this capture resolved to `10.10.10.77` — the seven lookups all returned `10.10.10.10`.
- The exchange occurs at the end of the capture and shows no termination packets.

**INTERPRETATIONS** — what the observations might mean, with alternatives kept alive:

- Port 4444 is not a well-known service port and appears nowhere else in this capture's traffic. It is unusual *for this baseline* — which is a statement about this capture, not about port 4444 in general.
- The client connected by IP with no preceding name lookup. That could mean the address was configured or hardcoded, or that the lookup happened before the capture began, or that it was cached. Three possibilities, none currently distinguishable.
- The decoder not recognising the payload means it didn't match a known protocol's structure. That covers a custom protocol, an encrypted one, a compressed one, or simply one this decoder doesn't model.
- One destination appearing once, at the end, with a payload the decoder can't parse, is a departure from a baseline of DNS-then-HTTP-to-one-web-server.

**CONCLUSION** — what the evidence actually supports:

> The client `10.10.10.20` established a TCP connection to `10.10.10.77:4444` and sent one packet of data the decoder could not identify. This exchange does not match any other traffic pattern in the capture: a destination seen nowhere else, a non-standard port, no preceding DNS resolution, and an unrecognised payload. **It warrants further investigation.**
>
> The evidence does **not** establish that this is malicious. Four packets on a non-standard port are consistent with malicious activity and equally consistent with a custom application, an administrative tool, a monitoring agent, a test, or a legitimate internal service the analyst simply doesn't recognise.

**CONFIDENCE:**

- *High* — that the connection occurred and completed as described. The packets are unambiguous.
- *High* — that this traffic differs from everything else in this capture.
- *Low* — as to purpose or intent. Nothing in these four packets establishes it.

**NEXT INVESTIGATION** — what would actually resolve it:

1. What is `10.10.10.77`? Is it a known, inventoried asset?
2. What process on `10.10.10.20` opened the connection? Host-level evidence, not network evidence — the capture cannot answer this.
3. Is port 4444 in use by any sanctioned application in this environment?
4. Does this pattern repeat? A single occurrence and a fixed-interval beacon are very different findings.
5. Are there earlier captures showing prior communication with this address?
6. What was in the payload? Requires evidence beyond this capture.

**The point of this exercise.** Notice what the conclusion did *not* say. It didn't say "compromised." It didn't say "attack." It said: here is what the packets show, here is why it's anomalous relative to this baseline, here is what I can't determine, and here is what would determine it.

That restraint is not timidity — it is the difference between an analyst whose findings can be acted on and one whose findings have to be re-verified by someone else. Port 4444 has a reputation, and an analyst who leads with that reputation instead of with the evidence will eventually be confidently, expensively wrong. State the evidence. Rank the possibilities. Name what would settle it.

## 11. The Report Template

Use this structure for any capture investigation. Filling every field is the point — the fields you can't fill honestly are exactly the ones telling you what you don't yet know.

```
CAPTURE
  Which capture, how many packets, what time span.

OBSERVED CLIENT(S)
  Addresses that initiate connections and use ephemeral ports.

OBSERVED SERVER(S)
  Addresses that accept connections on well-known/service ports.

PROTOCOLS
  Which protocols are present, and in what proportion.

PORTS
  Which service ports appear, and whether each is conventional here.

DNS ACTIVITY
  Names queried, servers that answered, addresses returned,
  whether lookups succeeded.

HTTP ACTIVITY
  Methods, paths, status codes, which server.

TCP BEHAVIOUR
  Do connections establish cleanly? Terminate cleanly? Any resets
  or retransmissions? Anything structurally incomplete?

INTERESTING OBSERVATIONS
  What departs from the baseline you established — stated as
  observation only, no interpretation yet.

EVIDENCE
  Specific packet numbers and fields supporting each observation.
  If you cannot cite a packet, it is not an observation.

CONCLUSION
  What the evidence supports. Explicitly include what it does NOT
  support.

CONFIDENCE
  Per claim, not overall. High / Medium / Low, with a reason.

NEXT INVESTIGATION
  What you would examine next, and what question each step answers.
```

**Now write one.** Complete this template for `capture mixed` on your own. It contains no anomaly — which makes it the more useful exercise, because writing an honest report that concludes "this all looks like ordinary traffic" is a genuine skill and one most beginners never practise. Most captures you will ever open are exactly this: entirely normal. Being able to say so, with evidence, is as valuable as spotting the outlier.

## 12. Observation, Interpretation, Conclusion

The single most important habit in this module, stated on its own because it's the thing that outlasts every tool.

```
OBSERVATION      what the capture shows — checkable, citable to a packet
     ↓
INTERPRETATION   what it might mean — plural, alternatives kept open
     ↓
CONCLUSION       what the evidence supports — with a confidence level
```

Worked, using the example from the ticket that shaped this module:

- **OBSERVATION:** Several TCP retransmissions appear between two hosts.
- **INTERPRETATION:** Packets may be getting lost or delayed. Possible causes include congestion, a marginal physical link, an overloaded endpoint, or ordinary acknowledgement timing.
- **CONCLUSION:** There may be a network reliability problem affecting this path. Confidence: medium — the pattern is consistent with loss, but I have not ruled out timing, and I have not checked whether it affects other paths.

And a second, using the `investigation` capture:

- **OBSERVATION:** One TCP connection to an address seen nowhere else, on port 4444, with an unidentified payload.
- **INTERPRETATION:** Could be a custom internal application, an administrative or monitoring tool, a test, or unauthorized activity.
- **CONCLUSION:** Anomalous relative to this capture's baseline and worth investigating. Confidence in "it happened": high. Confidence in "it's malicious": low — no evidence here establishes purpose.

**Why this separation matters so much.** Skipping straight from observation to conclusion is the single most common failure in security analysis, and it fails in both directions. Call everything malicious and you generate false positives until people stop reading your reports. Call everything benign and you miss the real thing. The separation is what lets you be *useful*: precise about what you saw, honest about what you don't know, and clear about what would settle it.

The most useful sentence in an analyst's vocabulary is: **"Here is what I observed, here is what I think it might mean, and here is what I'd need to know for certain."**

## 13. Common Mistakes

**Filtering before orienting.** Filters find what you look for. Orientation finds what you weren't looking for. Read the capture first. §4.

**Treating "not in my capture" as "didn't happen."** A capture is one observation point over one time window. §2 of Introduction, and §10 Step 3 here.

**Concluding from a single packet.** Follow the conversation. The exchange carries the meaning; one packet rarely does. §8.

**Assuming an unusual port proves intent.** A non-standard port is a departure from a baseline. It's a reason to look, not a finding. §10.

**Reading a missing packet as a network fault.** Incomplete connections in a capture are usually a limit of the capture. §10 Step 3.

**Skipping the baseline.** Nothing can stand out until you know what ordinary looks like *here*. §10 Step 2.

**Reporting interpretation as observation.** If you can't cite a packet number, it isn't an observation. §11.

**Stating one confidence for a whole report.** Different claims deserve different confidence. Rank them individually. §10 Step 7.

## 14. Cross-Track Connections

This module sits at a junction, and it's worth seeing how much of the roadmap it draws on:

**Computer Networking** — IP addressing, TCP, UDP, ports, DNS. Wireshark is where those stop being definitions and become things you can point at in evidence.

**Web Fundamentals** — HTTP methods, paths, status codes, headers. Exercise 4 shows the same request/response model you learned there, riding inside the transport that delivers it.

**Operating Systems** — processes, sockets, services. A port is a program's endpoint; when Exercise 6 asks "what process opened this connection," it's asking a question packet analysis can't answer and host-level investigation can. Knowing which tool answers which question is part of the skill.

**Cryptography Basics** — the evidence, attack surface and investigation model. This module is that reasoning applied to network traffic: asset, observation, evidence, confidence.

**Nmap** — the sharpest connection, and worth stating directly:

> **Nmap** tells you: *what services might exist here?*
> **Wireshark** shows you: *what is actually happening on the network?*

Nmap sends probes and infers. Wireshark observes what already happened. They answer different questions and are strongest together: Nmap says a service is listening on port 80; Wireshark shows you whether anyone is actually using it, who, how often, and whether those connections succeed. And the SYN-ACK you identified in Exercise 2 is *exactly* what Nmap means by an "open" port — the same evidence, viewed from the traffic side rather than the scanner's.

## 15. Practice on This Platform

Two real, authorized environments reinforce this module. Both are fully simulated.

**Wireshark Fundamentals** (terminal mission) — twelve objectives working through the same captures used in this lesson: opening a capture, identifying source and destination IPs, filtering TCP, recognising the three-way handshake, identifying ports, filtering DNS, analysing an HTTP request, following a conversation, IP and port filters, reading mixed traffic, and a final investigation that asks you to record the anomalous host, port and your reason. It is the direct rehearsal of Exercises 1–6, in the same environment, scored.

**Wireshark: Capture & Inspect** (interactive lab) — a different simulator with a different shape: you *generate* traffic yourself (ping, nslookup, nmap) on a small simulated network and then inspect what your own actions produced in the capture viewer. That reverses this lesson's direction usefully — instead of analysing a capture someone handed you, you see how your own activity appears in one. Two further labs in the same category continue it: **Wireshark: Protocol Analysis** and **Wireshark: Advanced Analysis**.

Note the difference honestly: the lab's capture viewer is a separate simulator from the terminal mission's, with its own command syntax. The concepts are the same; the exact commands are not interchangeable between them.

## 16. Knowledge Check

1. Walk through the investigation workflow from §4. Why is ORIENT before FILTER, and what goes wrong if you reverse them?
2. In Exercise 1, the ICMP packets had no port numbers. Why not, and what does that tell you about which layer ICMP occupies?
3. What evidence in a capture proves a TCP connection was *established*, as opposed to merely *attempted*?
4. Beyond "the Protocol column says DNS," name three independent pieces of evidence that identify a DNS query.
5. In Exercise 4, filtering to `http` showed 2 packets but the conversation had 8. What were the other 6, and why does it matter that they're there?
6. Why does packet 5 in the HTTP capture (a bare ACK from the server) matter, when the actual response is packet 6?
7. In Exercise 6, why is "port 4444 is unusual" a statement about the capture rather than about the network?
8. Four connections in the `investigation` capture have no completing ACK. Give the most likely explanation and say why it beats "the network is broken."
9. State one observation, one interpretation, and one conclusion about the `10.10.10.77` traffic, keeping them properly separate.
10. Why should confidence be stated per claim rather than once for a whole report?
11. Why is writing an honest "nothing anomalous here" report a genuine skill worth practising?
12. Nmap reports port 80 open on a host. Wireshark shows no traffic to port 80 on that host in your capture. Are these in conflict? Explain.

## 17. Key Takeaways

- Investigation follows a shape: capture → orient → filter → identify → follow → analyze → conclude. Orienting first is what makes the rest work.
- Establish a baseline before hunting anomalies. Nothing can stand out until you know what ordinary looks like *in this capture*.
- Derive roles from behaviour, not labels. A host that only answers DNS on port 53 is a DNS server because of what it does.
- Evidence means a citable packet. If you can't point at a packet number, you're stating an interpretation.
- Follow the conversation. Filtering to one protocol hides the transport that made it possible.
- A missing packet is usually a limit of the capture, not a fault in the network.
- Keep observation, interpretation and conclusion separate — always, and especially when the answer looks obvious.
- State confidence per claim. "This happened: high. This is malicious: low." Both can be true in one report.
- Most traffic is normal. Being able to say "this is ordinary," with evidence, is as valuable as finding the outlier.
- Anomalous means "differs from the baseline and deserves a look." It does not mean malicious, and the gap between those two words is where analytical credibility lives.

## 18. What's Next

You can now capture, filter, inspect, follow and interpret network traffic, and — more importantly — report on it in a way that distinguishes what you saw from what you think it means.

That combination feeds directly into what follows on this roadmap. **Burp Suite** applies the same intercept-and-inspect model to HTTP specifically, with the ability to modify traffic rather than only observe it. **OWASP Top 10** and **Web Pentesting** build on the request/response analysis you practised in Exercise 4. **Reconnaissance** and **Enumeration** extend the evidence-gathering discipline you've now built across two tools. And any incident-response work you meet later runs on precisely the observation/interpretation/conclusion separation this lesson drilled — because in an incident, the cost of jumping from "unusual traffic" to "we've been breached" without evidence is measured in hours of other people's time.

The tool changes. The reasoning doesn't.
