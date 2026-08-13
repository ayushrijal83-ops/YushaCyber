# Core Concepts: TCP, DNS, HTTP and Filtering

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what a TCP connection is and identify the three-way handshake from evidence, not from memory
- read the TCP flags you can actually recognise in a capture — SYN, ACK, FIN, RST, PSH — and say what each one indicates
- trace a full TCP connection lifecycle from establishment through data exchange to termination
- explain why retransmissions and resets need context before they mean anything
- analyse a DNS query and its response, and say precisely what evidence identifies it as DNS
- analyse an HTTP request and response inside a capture, connecting it to what you learned in Web Fundamentals
- explain what remains visible about HTTPS traffic and what does not
- write display filters, narrow a capture step by step, and explain the reasoning behind each narrowing
- state the difference between a **capture filter** and a **display filter** without hesitating
- follow a TCP conversation to reconstruct an exchange
- treat protocol identification as a decoded label rather than a transmitted fact

Every capture quoted in this lesson is a real, fixed dataset built into this platform, opened with the commands from Introduction §13. Where an example describes real-Wireshark behaviour the simulator does not implement, it is labelled explicitly.

## 2. TCP: What a Connection Actually Is

You met TCP in Computer Networking as the connection-oriented transport protocol: ordered, acknowledged, reliable delivery. Wireshark is where that stops being a definition and becomes something you can watch happen.

A **TCP connection** is not a physical thing. It is an agreement between two endpoints — state held on each side — that says: *we are exchanging a stream, here is where we each are in it, and we will acknowledge what we receive.* Nothing on the network holds that state. It exists only at the two ends.

Which is exactly why the connection is visible in a capture: because both sides must **tell each other** about the state, the negotiation crosses the network and gets recorded. Establishment, acknowledgement and shutdown are all messages you can point at.

That gives you the first genuinely powerful analytical move in this module: **the shape of a connection is evidence.** A connection that opened cleanly, exchanged data and closed politely looks different from one that opened and went quiet, which looks different again from one that was refused outright. You don't need to read a single byte of application data to tell those apart.

## 3. The Three-Way Handshake

Every TCP connection begins with a three-packet exchange. Here is a real capture of exactly that and nothing else:

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

The sequence, and — more importantly — the evidence for each step.

### Packet 1 — SYN: the client asks

```
$ show 1
Packet #1
Time: 0.001000
Length: 74 bytes

Ethernet II
    Source: 02:42:0a:0a:0a:14
    Destination: 02:42:0a:0a:0a:0a

IPv4
    Source: 10.10.10.20
    Destination: 10.10.10.10
    TTL: 64

TCP
    Source Port: 49152
    Destination Port: 80
    Flags: SYN

Conversation: tcp:10.10.10.10:80<->10.10.10.20:49152
```

**What this means:** `10.10.10.20` wants to open a connection to port 80 on `10.10.10.10`.

**What in Wireshark demonstrates it:** the TCP layer shows `Flags: SYN` — SYN alone, with no ACK. A lone SYN is a request to synchronise, and it is the only packet in a normal connection that carries SYN without ACK. That is what makes it identifiable as the *first* packet of a connection rather than a packet somewhere in the middle.

Two facts you can already state with confidence, and one you cannot: you know which host initiated (the SYN sender), and you know which endpoint it addressed (port 80). You do **not** yet know whether the connection succeeded — a SYN is a request, and requests can go unanswered.

### Packet 2 — SYN, ACK: the server agrees

```
$ show 2
Packet #2
Time: 0.002000
Length: 74 bytes

Ethernet II
    Source: 02:42:0a:0a:0a:0a
    Destination: 02:42:0a:0a:0a:14

IPv4
    Source: 10.10.10.10
    Destination: 10.10.10.20
    TTL: 64

TCP
    Source Port: 80
    Destination Port: 49152
    Flags: SYN, ACK

Conversation: tcp:10.10.10.10:80<->10.10.10.20:49152
```

**What this means:** the server acknowledges the client's request *and* makes its own synchronisation request in the same packet.

**What in Wireshark demonstrates it:** three things together, and it's worth naming all three because each rules something out.

1. `Flags: SYN, ACK` — both flags set. The ACK acknowledges the client's SYN; the SYN opens the server's own direction of the connection. TCP is bidirectional, so both directions must be established.
2. The addresses are **reversed** from packet 1 — source and destination have swapped. This is the reply.
3. The ports are reversed too: source `80`, destination `49152`. The same two endpoints, in the other direction.

This single packet is the strongest evidence in the whole handshake, because it proves something a SYN alone never can: **a service was actually listening on port 80 and accepted the connection attempt.** A closed port would have produced a refusal instead; a filtered port would have produced nothing at all. Compare this directly to the Nmap module's port states — a SYN-ACK is precisely what makes a port "open."

### Packet 3 — ACK: the client confirms

```
$ show 3
Packet #3
Time: 0.003000
Length: 66 bytes

Ethernet II
    Source: 02:42:0a:0a:0a:14
    Destination: 02:42:0a:0a:0a:0a

IPv4
    Source: 10.10.10.20
    Destination: 10.10.10.10
    TTL: 64

TCP
    Source Port: 49152
    Destination Port: 80
    Flags: ACK

Conversation: tcp:10.10.10.10:80<->10.10.10.20:49152
```

**What this means:** the client acknowledges the server's SYN. Both directions are now established; the connection is open and data can flow.

**What in Wireshark demonstrates it:** `Flags: ACK` — ACK alone, no SYN. The client has nothing left to synchronise, so it only acknowledges. Notice the length: **66 bytes, against 74 for the two previous packets.** That is not decoration. This packet carries no options that the SYN packets needed, and no application data at all — it is a pure acknowledgement, and its size is consistent with that. Length is real evidence and it is free to read.

### The chain, and how to state it

```
Client wants a connection            →  packet 1: SYN
Server acknowledges and responds     →  packet 2: SYN, ACK
Client acknowledges                  →  packet 3: ACK
Connection established
```

The professional way to state this is not "I saw three packets so it's a handshake." It is:

> Packet 1 is a lone SYN from `10.10.10.20:49152` to `10.10.10.10:80`, so that host initiated. Packet 2 is a SYN-ACK from `10.10.10.10:80` back to the same client port, so a service was listening and accepted. Packet 3 is a lone ACK completing the exchange. The connection was successfully established, in three milliseconds.

Every clause names the evidence. That is the standard for the rest of this module.

## 4. TCP Flags

Flags are single bits in the TCP header that describe what a segment is doing. Wireshark decodes them into the short names you've been reading. You only need to recognise five in practice.

| Flag | Name | What it indicates |
|---|---|---|
| **SYN** | Synchronise | A connection establishment attempt |
| **ACK** | Acknowledge | Acknowledging data or a control flag received |
| **FIN** | Finish | An orderly shutdown of this sender's direction |
| **RST** | Reset | An abrupt termination or refusal |
| **PSH** | Push | An indication to deliver buffered data to the application promptly |

Flags combine — that's why you see `SYN, ACK`, `FIN, ACK` and `PSH, ACK` rather than single names. Combination is normal: ACK rides along with almost everything once a connection is open, because there is nearly always something to acknowledge.

Reading each one honestly:

**SYN** — a request to open. A lone SYN is a connection attempt, nothing more. It does not mean a connection happened.

**SYN, ACK** — the response that proves something was listening and accepted. Strong, specific evidence.

**ACK** — acknowledgement of receipt. Extremely common and, on its own, almost never interesting. Its value is contextual: what makes an ACK meaningful is what it is acknowledging and when.

**FIN** — this sender has finished sending. Because TCP is bidirectional, an orderly close normally takes a FIN and an ACK in *each* direction. Seeing one FIN does not mean the connection is fully closed; it means one direction is done.

**PSH** — an indication that buffered data should be delivered to the receiving application without further delay. In practice you will usually see PSH on packets that carry application data, which makes it a handy visual marker when skimming a capture.

> **WRONG:** "A PSH flag proves an application event happened."
> **CORRECT:** "PSH indicates data should be delivered promptly. It commonly appears on packets carrying application data, but it is a delivery hint from the sending TCP stack — the application data itself, not the flag, is what tells you what happened."

**RST** — abrupt termination. Section 8 covers it properly, because it is the flag most often misread.

**A note on this platform's captures.** The datasets built into this simulator contain SYN, `SYN, ACK`, ACK, `FIN, ACK` and `PSH, ACK`. There is **no RST anywhere in them, and no retransmission**. Sections 7 and 8 therefore teach those two concepts without quoting captured output, because none exists to quote — and inventing an example capture to fill the gap would be exactly the fabrication this module tells you to distrust. You will meet both in real traffic almost immediately; what you need now is the reasoning, which transfers intact.

## 5. The Connection Lifecycle, End to End

The handshake capture showed establishment in isolation. Here is a complete connection — open, exchange, close:

```
$ capture http
8 packets loaded from 'http'.
Type 'packets' to list them.

$ packets
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
1    0.001     10.10.10.20     10.10.10.10     TCP       SYN
2    0.002     10.10.10.10     10.10.10.20     TCP       SYN, ACK
3    0.003     10.10.10.20     10.10.10.10     TCP       ACK
4    0.004     10.10.10.20     10.10.10.10     HTTP      GET /index.html HTTP/1.1
5    0.005     10.10.10.10     10.10.10.20     TCP       ACK
6    0.006     10.10.10.10     10.10.10.20     HTTP      HTTP/1.1 200 OK  Content-Type: text/html
7    0.007     10.10.10.20     10.10.10.10     TCP       FIN, ACK
8    0.008     10.10.10.10     10.10.10.20     TCP       ACK
```

Three phases, visible without reading a single detail pane:

```
ESTABLISHMENT     packets 1-3    SYN → SYN,ACK → ACK
DATA EXCHANGE     packets 4-6    request → acknowledgement → response
TERMINATION       packets 7-8    FIN,ACK → ACK
```

Walk the middle phase, because it shows something people miss. Packet 4 is the client's request. Packet 5 is the server acknowledging *receipt of the request* — this is TCP saying "I got your bytes," and it happens before and independently of the application deciding what to answer. Packet 6 is the actual response. **Acknowledgement and answer are two different things**, and separating them is how you tell "the server never received my request" from "the server received it and took four seconds to answer" — two very different problems with two very different fixes.

### Real traffic is messier than this

The capture above is deliberately clean, and you should not expect real captures to look like it. Real traffic routinely shows:

- **Connections already in progress** when the capture started — no handshake visible, because you weren't watching yet.
- **Interleaved conversations** — dozens of connections' packets mixed together in one list, with no visual grouping at all.
- **Data split across many segments** — a large response is not one packet; it's a long run of them.
- **Connections that never close cleanly** — a client that vanished, a timeout, a reset.
- **Retransmissions and out-of-order delivery** (§7).

> **WRONG:** "This connection has no SYN, so something is wrong."
> **CORRECT:** "This connection has no SYN in my capture. Either it began before I started capturing, or its handshake didn't cross my observation point, or it genuinely never happened. Those are three different explanations and I need more than one packet to choose between them."

The `follow` command (§18) exists precisely because interleaving makes the raw list unreadable.

## 6. UDP, and Why DNS Looks Different

TCP's whole visible structure — handshake, acknowledgements, orderly shutdown — comes from being connection-oriented. **UDP has none of it.** There is no handshake, no acknowledgement, no connection state, and therefore nothing to see except the datagrams themselves.

In a capture this is immediately obvious: a UDP exchange is typically just a request and a reply, with no surrounding ceremony. Which is exactly what DNS looks like, as the next section shows. When you're skimming an unfamiliar capture, "two packets, done" versus "a handshake, then data, then a shutdown" is a fast, reliable way to tell the two transports apart before you read anything else.

## 7. Retransmissions

**Concept, taught without quoted output** — this platform's captures contain no retransmissions (§4).

TCP guarantees delivery. It cannot do that by wishing, so when a sender doesn't receive an acknowledgement within its expected time, it **sends the data again**. Wireshark detects this by noticing it has already seen this data on this connection, and flags the packet as a retransmission.

A retransmission is a completely normal mechanism doing exactly its job. It tells you something didn't get acknowledged in time. What it does *not* tell you is why. Legitimate causes include:

- **Packet loss** — the original genuinely didn't arrive.
- **Congestion** — a link or device is saturated and dropping traffic.
- **Wireless or physical-layer problems** — interference, weak signal, a bad cable.
- **Timing and delayed acknowledgements** — the acknowledgement was on its way but the sender's timer expired first.
- **An overloaded endpoint** — the receiver is too busy to keep up.

> **WRONG:** "Retransmissions mean an attack."
> **CORRECT:** "Retransmissions usually reflect ordinary network behaviour — loss, congestion, or timing. Whether they're suspicious depends on context that a retransmission count alone does not contain."

The right response to seeing retransmissions is to characterise them, not to alarm on them: are they on one connection or all of them? One direction or both? Clustered at one moment or spread throughout? Between one pair of hosts or across the whole capture? Those answers point at a cause. "There were retransmissions" points at nothing.

## 8. TCP Reset (RST)

**Concept, taught without quoted output** — this platform's captures contain no RST packets (§4).

A RST is an abrupt end. Where FIN says "I've finished sending, let's wind this down," RST says "stop — this connection is over now." No negotiation, no acknowledgement expected.

RSTs are extremely common in ordinary networks and have many entirely legitimate causes:

- **Nothing is listening** on the destination port — the host refuses the connection. (This is precisely the Nmap module's "closed" port state, seen from the traffic side.)
- **The application closed abruptly** — a process exited, crashed, or closed a socket without a graceful shutdown.
- **A timeout was reached** — one side gave up on an idle or stalled connection.
- **A firewall or middlebox** deliberately terminated the connection by policy.
- **A protocol-level condition** — a segment arrived that doesn't fit any known connection, so the receiver resets it.

> **WRONG:** "A RST means an attacker reset the connection."
> **CORRECT:** "A RST means some party terminated the connection abruptly. Applications, operating systems, firewalls and normal protocol conditions all produce resets routinely. Which one it was requires context — who sent it, when in the connection's life, and whether the pattern repeats."

The useful question about a RST is never "is this bad?" It is **"who sent it, and at what point?"** A RST from the server immediately after a client's SYN means the port was refused. A RST from the client midway through a data transfer means something ended on the client side. A RST from neither endpoint's address at all would be genuinely unusual and worth real attention. Same flag, three completely different stories.

## 9. DNS Analysis

DNS is the name-to-address lookup you met in Computer Networking. In a capture it is usually the *first* thing a host does before contacting anything by name, which makes DNS traffic disproportionately valuable: it often tells you a host's intent before the connection that follows it.

A real DNS exchange:

```
$ capture dns
2 packets loaded from 'dns'.
Type 'packets' to list them.

$ packets
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
1    0.001     10.10.10.20     10.10.10.53     DNS       Standard query A example.training
2    0.002     10.10.10.53     10.10.10.20     DNS       Standard query response A example.training 10.10.10.10
```

Two packets. Query, response. Now the detail — the query first:

```
$ show 1
Packet #1
Time: 0.001000
Length: 70 bytes

Ethernet II
    Source: 02:42:0a:0a:0a:14
    Destination: 02:42:0a:0a:0a:35

IPv4
    Source: 10.10.10.20
    Destination: 10.10.10.53
    TTL: 64

UDP
    Source Port: 53412
    Destination Port: 53

Application: DNS
    Standard query A example.training

Conversation: udp:10.10.10.20:53412<->10.10.10.53:53
```

And the response:

```
$ show 2
Packet #2
Time: 0.002000
Length: 86 bytes

Ethernet II
    Source: 02:42:0a:0a:0a:35
    Destination: 02:42:0a:0a:0a:14

IPv4
    Source: 10.10.10.53
    Destination: 10.10.10.20
    TTL: 64

UDP
    Source Port: 53
    Destination Port: 53412

Application: DNS
    Standard query response A example.training 10.10.10.10

Conversation: udp:10.10.10.20:53412<->10.10.10.53:53
```

Everything an investigation needs is in those two packets:

| Question | Answer | Evidence |
|---|---|---|
| Who asked? | `10.10.10.20` | Source IP of the query |
| Which server answered? | `10.10.10.53` | Source IP of the response |
| What name was queried? | `example.training` | The DNS application data |
| What record type? | `A` | "Standard query **A**" |
| Was it answered? | Yes | A response packet exists, matching the query |
| What was returned? | `10.10.10.10` | The address in the response |

Note the transport: **UDP**, not TCP. Destination port 53 on the query, source port 53 on the response, with the client's ephemeral port `53412` on the other end of both. No handshake, no shutdown — exactly the UDP shape from §6.

### Record types, briefly

DNS answers different kinds of questions, and the record type tells you which was asked:

| Type | Question it answers |
|---|---|
| **A** | What IPv4 address does this name have? |
| **AAAA** | What IPv6 address does this name have? |
| **CNAME** | What other name is this name an alias for? |
| **MX** | Which mail servers handle mail for this domain? |

That's enough to read most DNS traffic you'll encounter. This is deliberately not a DNS administration course — you need to recognise what was asked and what came back, not to operate a resolver. This platform's captures model **A** record queries only, so A is the only type you'll see quoted here.

## 10. DNS Investigation

DNS is where a lot of network investigation actually starts, so build the habit of asking a fixed set of questions of every DNS exchange:

1. **What domain was queried?**
2. **Who made the query?** (Which host — and, if you can determine it, which process or user?)
3. **Which DNS server answered?** Is it the one this host is supposed to be using?
4. **What answer was returned?**
5. **Was the response successful?** A response can legitimately say "this name does not exist."
6. **Is there a pattern?** How often, how many distinct names, in what rhythm?

That last one needs care, because it is where beginners go wrong most confidently.

> **WRONG:** "Long or unusual-looking domain names are malicious."
> **CORRECT:** "Domain name characteristics are one weak signal among many. Content delivery networks, cloud services, analytics platforms and ordinary software all generate long, machine-shaped names constantly. Suspiciousness comes from context — whether the host is *supposed* to be contacting that name, whether the pattern fits its role, whether the volume and timing make sense — not from the shape of the string."

The genuinely useful DNS signals are relational, not cosmetic: a host querying names entirely unrelated to its function; queries at a fixed interval when nobody is using the machine; a host bypassing the organisation's DNS server to ask someone else; a sudden change in the *variety* of names a host looks up. All of those are still starting points for investigation, not conclusions — but they're built on behaviour rather than on how a string looks.

**A useful correlation, and one you can perform right now.** The DNS response above returned `10.10.10.10` for `example.training`. In the HTTP capture from §5, the client connects to `10.10.10.10` on port 80. Those are two separate pieces of evidence, from two different protocols, that fit together: the host resolved a name, then connected to the address it got back. That kind of cross-protocol correlation — DNS answer matching a subsequent connection destination — is one of the most reliable analytical moves you have, and it's how you determine which *name* a host was actually trying to reach when all the connection itself shows you is an IP address.

## 11. HTTP Analysis

You built the real model of HTTP in Web Fundamentals: a request with a method, path and headers; a response with a status code, headers and a body. Wireshark is where you see that model as it crosses the network, inside TCP, inside IP, inside a frame.

Return to the HTTP capture from §5 and look at the request:

```
$ capture http
8 packets loaded from 'http'.
Type 'packets' to list them.

$ show 4
Packet #4
Time: 0.004000
Length: 210 bytes

Ethernet II
    Source: 02:42:0a:0a:0a:14
    Destination: 02:42:0a:0a:0a:0a

IPv4
    Source: 10.10.10.20
    Destination: 10.10.10.10
    TTL: 64

TCP
    Source Port: 49153
    Destination Port: 80
    Flags: PSH, ACK

Application: HTTP
    GET /index.html HTTP/1.1

Conversation: tcp:10.10.10.10:80<->10.10.10.20:49153
```

And the response:

```
$ show 6
Packet #6
Time: 0.006000
Length: 512 bytes

Ethernet II
    Source: 02:42:0a:0a:0a:0a
    Destination: 02:42:0a:0a:0a:14

IPv4
    Source: 10.10.10.10
    Destination: 10.10.10.20
    TTL: 64

TCP
    Source Port: 80
    Destination Port: 49153
    Flags: PSH, ACK

Application: HTTP
    HTTP/1.1 200 OK  Content-Type: text/html

Conversation: tcp:10.10.10.10:80<->10.10.10.20:49153
```

The full encapsulation stack, in one packet, exactly as Introduction §8 described:

```
Ethernet frame        02:42:0a:0a:0a:14 → 02:42:0a:0a:0a:0a
  IP packet           10.10.10.20 → 10.10.10.10
    TCP segment       port 49153 → port 80, flags PSH, ACK
      HTTP request    GET /index.html HTTP/1.1
```

Observations worth making explicitly:

- **The request rides inside an established connection.** Packets 1–3 opened it. HTTP could not have been sent first; the transport had to exist.
- **PSH, ACK on both.** Application data is being pushed, and the previous direction is being acknowledged at the same time. Compare packet 3's bare ACK at 66 bytes.
- **Length carries meaning.** The request is 210 bytes, the response 512. That difference is consistent with a small request and a larger body coming back — and length is readable even when the content is not, which becomes important in §13.
- **The status line answers Web Fundamentals' question.** `HTTP/1.1 200 OK` with `Content-Type: text/html` — the response was successful and returned HTML.

### What to look for in HTTP traffic

Mapping Web Fundamentals onto packet analysis:

| Element | What it tells you | Where in the capture |
|---|---|---|
| **Method** (`GET`, `POST`) | What the client was trying to do | Request line |
| **Path** (`/index.html`) | Which resource | Request line |
| **Host** header | Which site was requested — decisive when one server hosts many | Request headers |
| **User-Agent** header | What the client claims to be — a claim, freely set by the client | Request headers |
| **Content-Type** | What format the body is in | Request or response headers |
| **Status code** | How the server answered | Status line |

**Illustrative example — not captured output.** Real Wireshark, following an HTTP stream, shows the complete text of both messages including every header. This platform's simulator summarises each HTTP packet as a single line (the request line or the status line) rather than modelling full headers, so the block below is written to show you the *shape* of what real Wireshark displays. It is illustrative, and it is not from any capture on this platform:

```
GET /index.html HTTP/1.1
Host: example.training
User-Agent: Mozilla/5.0
Accept: text/html

HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 438
```

Read `User-Agent` with the same scepticism you'd apply to a port number: it is a string the client chose to send. It is evidence of what the client *claims*, which is genuinely useful and is not the same as what the client *is*.

## 12. The Request/Response Chain

Putting HTTP back into its full context, using the real capture from §5:

```
client                                          server
10.10.10.20                                     10.10.10.10

  │── SYN ─────────────────────────────────────────→│   packet 1
  │←──────────────────────────────────── SYN, ACK ──│   packet 2
  │── ACK ─────────────────────────────────────────→│   packet 3
  │                                                  │
  │── GET /index.html HTTP/1.1 ────────────────────→│   packet 4
  │←──────────────────────────────────────── ACK ──│   packet 5
  │←────────────────────────── HTTP/1.1 200 OK ────│   packet 6
  │                                                  │
  │── FIN, ACK ────────────────────────────────────→│   packet 7
  │←──────────────────────────────────────── ACK ──│   packet 8
```

This diagram is drawn from the eight real packets listed in §5 — every arrow corresponds to a numbered packet you can inspect yourself. It's worth internalising the layering it shows: **a web request is not one thing on the network.** It is a transport connection that had to be established first, an application exchange inside it, and a shutdown afterwards. When a web request fails, knowing which of those three phases it failed in is most of the diagnosis.

## 13. TLS and HTTPS: What Stays Visible

Here is a misconception that needs correcting directly, because it stops people from analysing traffic they could analyse perfectly well.

> **WRONG:** "It's HTTPS, so Wireshark shows nothing."
> **CORRECT:** "Encryption protects the application payload. A substantial amount of metadata remains fully visible, and metadata is real evidence."

What you can still observe in an encrypted connection:

- **Both endpoints** — source and destination IP addresses. Encryption cannot hide who is talking; the network needs the addresses to deliver the packets at all.
- **Ports** — including that this is conventionally HTTPS traffic on 443.
- **The TCP connection itself** — handshake, lifecycle, resets, retransmissions. All of it, unchanged.
- **Timing** — when the connection opened, how long it lasted, the rhythm of exchanges. Regular, machine-like intervals look different from human browsing, and that difference survives encryption completely.
- **Packet sizes and volume** — how much was sent in each direction. A connection that sent 40 bytes and received 2 MB tells a different story from one that sent 2 MB and received 40, without a byte of plaintext.
- **TLS handshake metadata** — the initial negotiation happens before encryption is fully in effect, and parts of it are observable, including protocol version and cipher information.

What you generally **cannot** read: the application payload — the actual HTTP request, headers, body, and response content. Making that readable requires the appropriate decryption material and a deliberate, authorized setup; it is not something Wireshark does by itself, and it is not something this module teaches you to do to traffic that isn't yours.

**No TLS traffic exists in this platform's captures**, so this section quotes no output — the datasets model plain TCP, UDP, DNS, HTTP and ICMP only. The reasoning is what transfers: when you meet an encrypted connection in a real capture, the correct response is not "I can't see anything." It's "the payload is unreadable — what do the endpoints, timing, sizes and connection behaviour tell me?" That question has answered a great many real investigations.

## 14. Display Filters

A real capture is far too large to read. Filtering is the skill that makes everything else in this module usable, and it deserves the same care as the analysis it enables.

A **display filter** narrows what you are shown from packets already in the capture. Start with the capture that has actual noise in it:

```
$ capture mixed
32 packets loaded from 'mixed'.
Type 'packets' to list them.
```

Thirty-two packets is small by real standards and already awkward to read line by line. Filter it.

**By protocol** — the broadest useful narrowing:

```
$ filter dns
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
1    0.001     10.10.10.20     10.10.10.53     DNS       Standard query A example.training
2    0.002     10.10.10.53     10.10.10.20     DNS       Standard query response A example.training 10.10.10.10
23   0.023     10.10.10.20     10.10.10.53     DNS       Standard query A host0.training
24   0.024     10.10.10.53     10.10.10.20     DNS       Standard query response A host0.training 10.10.10.10
25   0.025     10.10.10.20     10.10.10.53     DNS       Standard query A host1.training
26   0.026     10.10.10.53     10.10.10.20     DNS       Standard query response A host1.training 10.10.10.10
27   0.027     10.10.10.20     10.10.10.53     DNS       Standard query A host2.training
28   0.028     10.10.10.53     10.10.10.20     DNS       Standard query response A host2.training 10.10.10.10
29   0.029     10.10.10.20     10.10.10.53     DNS       Standard query A host3.training
30   0.030     10.10.10.53     10.10.10.20     DNS       Standard query response A host3.training 10.10.10.10
31   0.031     10.10.10.20     10.10.10.53     DNS       Standard query A host4.training
32   0.032     10.10.10.53     10.10.10.20     DNS       Standard query response A host4.training 10.10.10.10
```

Twelve DNS packets — six query/response pairs, all between the same client and the same DNS server. That's a fact you could not see in the unfiltered list without counting carefully.

**By address**:

```
$ filter ip.addr == 10.10.10.53
```

`ip.addr` matches the address in **either** direction, source or destination — which is what you almost always want, because you want the whole conversation, not one half of it. For one direction specifically, `ip.src` and `ip.dst` exist:

```
$ filter ip.src == 10.10.10.20
```

**By port**:

```
$ filter tcp.port == 80
```

Like `ip.addr`, `tcp.port` matches either source or destination port. `udp.port` does the same for UDP.

The display filters this platform supports:

| Filter | Matches |
|---|---|
| `tcp` | Packets identified as TCP |
| `udp` | Packets identified as UDP |
| `icmp` | Packets identified as ICMP |
| `dns` | Packets identified as DNS |
| `http` | Packets identified as HTTP |
| `ip.addr == ADDRESS` | Either source or destination IP |
| `ip.src == ADDRESS` | Source IP only |
| `ip.dst == ADDRESS` | Destination IP only |
| `tcp.port == PORT` | Either TCP source or destination port |
| `udp.port == PORT` | Either UDP source or destination port |

This is a deliberately small subset of real Wireshark's display-filter language, which supports thousands of protocol fields plus boolean operators (`and`, `or`, `not`), comparisons (`>`, `<`, `!=`), and field-content matching. Real Wireshark also lets you write, for example, `dns.qry.name == "example.training"` to match a specific queried name — a field-level filter this simulator does not implement, mentioned so you know the capability exists rather than left as a surprise. The **reasoning** you practise here — start broad, narrow deliberately, one dimension at a time — is identical at any scale of filter language.

**When a filter matches nothing**, you get told so plainly:

```
$ filter ip.addr == 10.10.10.99
No packets matched filter 'ip.addr == 10.10.10.99'.
```

That is itself a result, and a useful one. It means no packet in *this capture* involved that address. Remember Introduction §4 before you turn it into a claim about the network.

## 15. Capture Filters vs. Display Filters

These are two different things at two different stages, and confusing them is one of the most common beginner errors in this whole tool.

| | **Capture filter** | **Display filter** |
|---|---|---|
| **When it applies** | While capturing | After capturing |
| **What it controls** | Which traffic is *recorded* | Which recorded traffic is *shown* |
| **Reversible?** | **No** — unrecorded traffic is gone permanently | **Yes** — change or clear it any time |
| **Syntax** | BPF (also used by `tcpdump`) | Wireshark's own display-filter language |
| **Example form** | `tcp port 80` | `tcp.port == 80` |

Look at those two example expressions carefully, because they are the trap:

```
tcp port 80          ← capture filter (BPF): spaces, no dots, no ==
tcp.port == 80       ← display filter: dotted field name, explicit ==
```

They express nearly the same idea in two completely different languages. Typing one where the other belongs is a routine mistake, and the error message you get is often unhelpful about which mistake you made.

> **WRONG:** "A display filter changes what was captured."
> **CORRECT:** "A display filter changes what is currently shown from an existing capture. Every packet is still in the file; clearing the filter brings them all back. A capture filter is what changes what was recorded — and what it excludes was never written down at all."

**Which should you use?** Default to a display filter. Capturing everything and filtering the view is almost always right, because you can always narrow later and you can never un-discard what you never recorded. The main legitimate reason to use a capture filter is volume — on a busy link, capturing everything can produce files too large to handle, or fill a disk. That is a real constraint and a real reason. But understand what you're trading: **a capture filter is a decision made before you know what you're looking for.** If your capture filter was wrong, you find out later, and the traffic that would have answered your question is gone.

**On this platform**, only display filters exist — the captures are fixed datasets, so there is nothing to filter at capture time. The distinction still matters the moment you open real Wireshark, which is why it's taught here rather than deferred.

## 16. Filter Reasoning: Broad to Narrow

Filters are not something to memorise. They're a way of asking successively sharper questions, and each narrowing should have a reason you could state out loud.

```
Start broad             what protocols are even here?
  ↓
Find the protocol       narrow to the one that answers your question
  ↓
Narrow by host          which endpoints are involved?
  ↓
Narrow by port          which service endpoint specifically?
  ↓
Narrow by field         which exact exchange?
  ↓
Follow the conversation read the whole exchange in order
```

A worked example, on the noisy capture. **The question:** what name lookups did this client perform, and did they succeed?

**Step 1 — start broad.** Open the capture and look at everything. 32 packets, several protocols. Too much to reason about, but you now know DNS is present.

**Step 2 — narrow to the protocol that answers the question.**

```
$ filter dns
```

Twelve packets, six query/response pairs. Every query comes from `10.10.10.20`; every response comes from `10.10.10.53`.

**Step 3 — narrow by host, to confirm the server relationship.**

```
$ filter ip.addr == 10.10.10.53
```

Same twelve packets. That's informative: **every packet involving `10.10.10.53` in this capture is DNS.** Combined with the fact that it answers on port 53, that's solid behavioural evidence for its role — not because something labelled it a DNS server, but because DNS is all it does here.

**Step 4 — inspect the individual exchange.** `show 1` and `show 2` (§9) give you the queried name, the record type, the answer, and the client's ephemeral port.

**Step 5 — correlate.** The response returned `10.10.10.10`. Filter for that address and you'll find the client's subsequent HTTP connection to it. The lookup and the connection fit together.

**Answer, stated with its evidence:** the client `10.10.10.20` performed six A-record lookups against `10.10.10.53`, all of which were answered. One of them resolved `example.training` to `10.10.10.10`, and the client then connected to that address on port 80. Every clause is checkable.

Notice that no step was "run the filter I memorised." Each one narrowed along a specific dimension — protocol, then host, then individual packet — for a stated reason. That's the transferable part.

## 17. When a Filter Result Surprises You

Here is a real behaviour of this platform's simulator that turns out to be an excellent lesson about protocol identification. Open the HTTP capture and filter for TCP:

```
$ capture http
8 packets loaded from 'http'.
Type 'packets' to list them.

$ filter tcp
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
1    0.001     10.10.10.20     10.10.10.10     TCP       SYN
2    0.002     10.10.10.10     10.10.10.20     TCP       SYN, ACK
3    0.003     10.10.10.20     10.10.10.10     TCP       ACK
5    0.005     10.10.10.10     10.10.10.20     TCP       ACK
7    0.007     10.10.10.20     10.10.10.10     TCP       FIN, ACK
8    0.008     10.10.10.10     10.10.10.20     TCP       ACK
```

Six packets — but the capture has eight, and you know from §5 that **all eight are TCP.** Packets 4 and 6 are missing. Now filter by port instead:

```
$ filter tcp.port == 80
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
1    0.001     10.10.10.20     10.10.10.10     TCP       SYN
2    0.002     10.10.10.10     10.10.10.20     TCP       SYN, ACK
3    0.003     10.10.10.20     10.10.10.10     TCP       ACK
4    0.004     10.10.10.20     10.10.10.10     HTTP      GET /index.html HTTP/1.1
5    0.005     10.10.10.10     10.10.10.20     TCP       ACK
6    0.006     10.10.10.10     10.10.10.20     HTTP      HTTP/1.1 200 OK  Content-Type: text/html
7    0.007     10.10.10.20     10.10.10.10     TCP       FIN, ACK
8    0.008     10.10.10.10     10.10.10.20     TCP       ACK
```

All eight. The same packets that `filter tcp` excluded are matched by a filter on a TCP **field**.

**Why:** this simulator gives each packet a single protocol *label* — the most specific protocol it represents — and `filter tcp` matches that label. Packets 4 and 6 are labelled `HTTP`, so a label-based filter for `tcp` skips them, even though they are unquestionably TCP segments carrying HTTP. Filtering on `tcp.port` looks at an actual transport-layer field instead, so it finds them.

**This is a simulator simplification, and you should know it.** Real Wireshark's `tcp` display filter matches every packet containing a TCP layer, HTTP packets included, so real Wireshark would return all eight for `tcp`. The simplification is stated here rather than hidden, because the lesson it accidentally teaches is one of the most valuable in the module — and it generalises to real captures, where the same reasoning applies to genuinely mislabelled or undecoded traffic.

The same thing happens with UDP. In the DNS capture, all traffic is UDP on port 53, but:

```
$ capture dns
2 packets loaded from 'dns'.
Type 'packets' to list them.

$ filter udp
No packets matched filter 'udp'.

$ filter udp.port == 53
#    TIME      SOURCE          DESTINATION     PROTOCOL  INFO
1    0.001     10.10.10.20     10.10.10.53     DNS       Standard query A example.training
2    0.002     10.10.10.53     10.10.10.20     DNS       Standard query response A example.training 10.10.10.10
```

Both packets are UDP datagrams. `filter udp` returns nothing because both are labelled `DNS`.

**The transferable lesson, and it's a big one:**

> **WRONG:** "The filter returned nothing, so that traffic isn't in the capture."
> **CORRECT:** "The filter returned nothing. Either the traffic isn't there, or it's there and my filter didn't match how it's identified. Check with a second, independent filter before concluding."

Cross-checking with a different kind of filter — a field instead of a label, a port instead of a protocol name — is a habit worth building permanently. It costs one command and it catches an entire category of wrong conclusion.

## 18. Follow the Conversation

In a busy capture, one conversation's packets are scattered among everyone else's. **Following** reassembles them: given any packet, show every packet belonging to the same exchange, in order.

Real Wireshark calls this **Follow TCP Stream** (right-click a packet → Follow → TCP Stream), and it additionally reconstructs the application data as continuous readable text. This platform's `follow` command reassembles the packet sequence:

```
$ capture http
8 packets loaded from 'http'.
Type 'packets' to list them.

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

Give it *any* packet in the exchange and you get the whole exchange. Notice the conversation identifier: `tcp:10.10.10.10:80<->10.10.10.20:49153` — the two endpoints and the transport, written so both directions map to the same conversation regardless of which side you started from. That's the definition of a conversation: **the same two endpoints, same transport, both directions.**

What following is genuinely useful for:

- **Conversation context** — a single packet rarely means much. The exchange around it usually does.
- **Request/response sequences** — seeing what was asked and what came back, in order.
- **Troubleshooting** — the shape of a failed exchange is diagnostic: did it never establish? Establish and stall? Establish and get reset?
- **Plaintext protocol analysis** — for unencrypted protocols, following reconstructs the readable application conversation.

That last point needs its boundary stated plainly. Following an unencrypted stream shows whatever that stream carried. On a network you're authorized to analyse — your own systems, your own test environments, an engagement with explicit scope — that's ordinary debugging and incident response. It is also exactly why unencrypted protocols are discouraged for anything sensitive, and it is why this module's captures contain no credentials and why extracting other people's authentication data is not something this platform teaches. The analytical skill is reading a conversation you're entitled to read.

## 19. Reading the Layers for Evidence

Pulling §§2–18 together: what does each layer of an expanded packet actually give you?

**Ethernet** — MAC addresses of the interfaces that handled this frame *at your observation point*. Useful for local-segment questions: which physical interface, whether traffic passed through the device you expected. Not useful for identifying a distant host, because MACs are rewritten at each hop (Introduction §12).

**IPv4** — the host addresses, end to end. This is your primary answer to "which machines." Also TTL, which decreases per router hop; a TTL far from the common starting values suggests the packet crossed more hops than a local exchange would, which is occasionally a useful hint.

**TCP** — ports (which program endpoint) and flags (what this segment is doing to the connection). Together with direction, this is where connection state lives: established, tearing down, refused.

**UDP** — ports only. No state, because there is none.

**Application (DNS, HTTP, …)** — what the program actually said. The most directly meaningful layer when it's readable, and the one encryption removes (§13).

The practical habit: **know which layer answers your question before you start looking.** "Is traffic reaching the right machine?" is an IP question. "Is it reaching the right service?" is a transport question. "Is the request correct?" is an application question. Expanding a packet and reading top to bottom without a question in mind is how people spend an hour learning nothing.

## 20. Protocol Identification Is a Conclusion, Not a Fact

Section 17 gave you a concrete case; here is the principle behind it.

The Protocol column is Wireshark **decoding** the bytes and reporting its best identification. That identification is usually right, and it is arrived at by heuristics: known port numbers, recognisable message structure, and the context of the surrounding conversation. It is not a field that was transmitted. Nothing in a packet says "I am HTTP."

Which means protocol labels can be wrong, in both directions:

- A service on a non-standard port may be **under-identified** — shown as plain TCP because no port convention triggered a decoder.
- Traffic on a conventional port may be **mis-identified** — shown as HTTP because it's on port 80, when it's something else entirely. This is precisely the Nmap module's "port 80 is not proof of HTTP," met one layer down.

> **WRONG:** "Wireshark says it's HTTP, so it's HTTP."
> **CORRECT:** "Wireshark identified this as HTTP. That's a good working hypothesis. The message structure, the conversation's behaviour, and the actual field contents are what confirm it."

When identification matters, correlate several independent things:

| Evidence | What it contributes |
|---|---|
| **Port** | Conventional expectation — weakest signal alone |
| **Message structure** | Does it actually look like that protocol's messages? |
| **Protocol fields** | Do the decoded fields make sense, or is the decoder guessing? |
| **Conversation behaviour** | Does the exchange pattern fit? Request/response, streaming, periodic? |

Any one of these can mislead. Together they're strong. That is the same evidence-weighing discipline the Nmap module built, applied to a different tool — and it's the reason both modules exist before any module that acts on what you find.

## 21. Common Mistakes

**Concluding a connection succeeded from a SYN.** A SYN is a request. The SYN-ACK is what proves something was listening. §3.

**Reading a lone FIN as "connection closed."** FIN closes one direction. An orderly close needs both. §4.

**Treating a RST or a retransmission as inherently suspicious.** Both are ordinary mechanisms with many benign causes. Context decides. §§7–8.

**Assuming HTTPS means nothing is visible.** Endpoints, ports, timing, sizes and connection behaviour all survive encryption. §13.

**Confusing capture filters with display filters.** One decides what gets recorded, permanently. The other decides what's on screen, reversibly. `tcp port 80` vs `tcp.port == 80`. §15.

**Trusting an empty filter result.** "No matches" can mean the traffic isn't there — or that your filter didn't match how it's identified. Cross-check. §17.

**Judging a domain by how it looks.** Long and machine-shaped is normal on the modern internet. Suspicion comes from behaviour and context. §10.

**Analysing a single packet in isolation.** Follow the conversation. One packet almost never carries the answer. §18.

## 22. Knowledge Check

1. What does the SYN packet represent, and what can you *not* conclude from seeing one?
2. What does a SYN-ACK demonstrate that a SYN alone does not?
3. In the handshake capture, packet 3 is 66 bytes while packets 1 and 2 are 74. What does that difference indicate?
4. Why does an orderly TCP close normally involve more than one FIN?
5. Why isn't a TCP retransmission automatically malicious? Name three legitimate causes.
6. A RST arrives immediately after a client's SYN. What is the most likely explanation, and how does it relate to Nmap's port states?
7. What evidence in a capture identifies a packet as a DNS query — specifically, not just "the Protocol column says DNS"?
8. Why is "this domain name looks unusual" a weak basis for calling traffic suspicious?
9. Why is a display filter different from a capture filter, and which one is irreversible?
10. What can Wireshark still reveal about HTTPS traffic, and what does it generally not reveal?
11. What is the purpose of Follow TCP Stream, and why is it more useful than reading packets individually?
12. `filter tcp` returned six packets from a capture you know contains eight TCP packets. What are the two possible explanations, and how would you tell them apart?
13. Why should the Protocol column be treated as a conclusion rather than a fact?

## 23. Key Takeaways

- A TCP connection is state held at both ends. It's visible in a capture only because the two ends must tell each other about it.
- SYN → SYN-ACK → ACK. The SYN-ACK is the packet that proves a service was listening and accepted.
- Five flags carry you a long way: SYN, ACK, FIN, RST, PSH. Combinations are normal; ACK rides along with almost everything.
- The lifecycle is establishment → data exchange → termination, and real captures rarely show all three cleanly. Missing pieces usually mean the capture, not the network.
- Retransmissions and resets are ordinary mechanisms. Ask *who, when, and how often* — never just "is this bad?"
- DNS is query and response over UDP; it tells you what a host was trying to reach before it reached it, and it correlates with the connection that follows.
- HTTP rides inside an established TCP connection. The transport had to exist first, and knowing which phase failed is most of a diagnosis.
- Encryption hides payload, not endpoints, ports, timing, sizes, or connection behaviour. Metadata is evidence.
- Display filters narrow the view of an existing capture and are reversible. Capture filters decide what gets recorded and are not. `tcp.port == 80` is not `tcp port 80`.
- Narrow deliberately: protocol, then host, then port, then field, then follow the conversation. Every step should have a stated reason.
- A filter returning nothing is a result to verify, not a conclusion to trust.
- Protocol labels are decoded conclusions. Correlate port, structure, fields and behaviour before treating one as settled.

## 24. What's Next

**Hands-on Practice** turns all of this into an actual investigation. You'll work through six exercises against the real captures on this platform — identifying a conversation from scratch, proving a handshake with evidence rather than recognition, investigating a DNS lookup, analysing an HTTP exchange, narrowing a noisy capture step by step, and finally producing a written investigation report on a capture containing something that doesn't fit. That last exercise is the one that matters most: it's where you practise separating **observation** from **interpretation** from **conclusion**, and stating your confidence honestly instead of guessing.
