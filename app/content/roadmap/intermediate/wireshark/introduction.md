# Introduction to Wireshark and Packet Analysis

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what Wireshark is and what a packet capture actually represents
- explain the difference between a live capture and a saved capture, and what an interface has to do with either
- use the words **frame**, **packet**, and **segment** correctly instead of calling everything a "packet"
- describe encapsulation — how one captured unit contains several protocol layers stacked inside each other
- read a packet list: number, time, source, destination, protocol, length, info
- expand a single packet's protocol layers and say what evidence each layer contributes
- identify the endpoints of a communication and explain why direction matters
- distinguish a MAC address from an IP address from a port, precisely

## 2. Why This Matters

The Nmap module taught you to ask a network a question and read the answer: *what hosts are here, and what might they be running?* Every answer Nmap gives is an inference drawn from a handful of probes you deliberately sent.

Wireshark answers a different question, and it is the more fundamental one:

> **Nmap:** what services *might* exist here?
> **Wireshark:** what is *actually happening* on this network, right now, packet by packet?

That difference matters more than it first appears. Nmap tells you a door exists. Wireshark lets you watch who walked through it, when, in which direction, carrying what, and whether the conversation completed or fell apart. It is the single most direct source of network evidence available to you — which is exactly why it sits at the centre of network troubleshooting, protocol debugging, incident response, and security monitoring alike.

It is also where a specific professional discipline gets built: the habit of separating **what you observed** from **what you think it means**. A capture will hand you thousands of facts. Almost all of them are ordinary. Learning to say "here is what the packets show, and here is how confident I am about what that implies" is the skill this module is really teaching. The tool is the easy part.

## 3. What Wireshark Actually Is

**Wireshark** is a network protocol analyser. It records network traffic and decodes it — taking the raw sequence of bytes that crossed a network interface and presenting it as structured, labelled protocol fields you can read, filter, sort, and follow.

Two halves, and it's worth separating them:

- **Capture** — obtaining a copy of traffic as it passes a network interface.
- **Analysis** — decoding those bytes into protocol layers and fields, then letting you search, filter and reconstruct conversations.

Wireshark does both, but the analysis half is where nearly all of your time goes and where nearly all of the skill lives. A capture is easy to obtain and tells you nothing on its own; a 40,000-packet file is not evidence until someone can narrow it to the twelve packets that answer a question.

**What Wireshark is used for, legitimately and daily:**

| Use | The question being asked |
|---|---|
| Network troubleshooting | Why is this connection slow, failing, or resetting? |
| Protocol debugging | Is my application actually sending what I think it sends? |
| Incident response | What did this host communicate with, and when? |
| Network visibility | What protocols and destinations are normal here? |
| Malware / network investigation | Does this host's traffic match its expected behaviour? |
| Performance analysis | Where is the delay — client, network, or server? |
| Security monitoring | Does observed traffic match policy and expectation? |

**The authorization boundary, stated once and meant permanently.** Capturing network traffic means obtaining a copy of other people's communications. On a network you own or are explicitly authorized to analyse, that is ordinary engineering work. On any other network it is interception, and it is not something this platform teaches, excuses, or works around. Every capture in this module is a fixed, simulated dataset built into the platform — no real packet is ever captured, transmitted, or inspected. That constraint is not a limitation of the lesson; it is the correct default for learning this skill.

## 4. What a Packet Capture Actually Represents

This is the idea most beginners skip past, and it quietly causes most bad conclusions later.

A capture is a **recording of traffic that passed one observation point during one window of time.** Three consequences follow directly, and you should hold all three permanently:

**It is past tense.** A capture is a recording, not a live view of the network. Everything in it already happened. You are reading history, and history does not update itself when you find something confusing.

**It is partial by construction.** A capture contains what reached the interface doing the capturing — nothing else. Traffic between two other hosts that never crossed your observation point is not in the file, and its absence is not evidence that it didn't happen. "I don't see it in the capture" and "it didn't happen" are two very different statements, and confusing them is one of the most common analytical errors in this whole discipline.

**It is bounded in time.** A capture starts and stops. A connection that began before you started capturing will appear without its handshake — not because the handshake never occurred, but because you weren't watching yet. When you see something that looks structurally wrong, "my capture started in the middle" is usually a better first hypothesis than "something malicious happened."

A capture file typically stores, for every unit of traffic it recorded: a timestamp, the length, and the raw bytes exactly as they crossed the wire. Everything else you see in Wireshark — protocol names, field names, "GET /index.html", the words "SYN, ACK" — is Wireshark *decoding* those bytes for you. That distinction matters and Core Concepts returns to it: the bytes are the evidence, and the labels are an interpretation of the evidence, usually right and occasionally not.

## 5. Live Capture vs. Saved Capture, and Interfaces

**Live capture** means Wireshark is attached to a network **interface** — a specific network connection on the machine, such as a wired Ethernet adapter or a wireless adapter — and is displaying traffic as it arrives. Choosing the interface is choosing your observation point, and it decides what you can possibly see. Capture on the wrong interface and you will see a perfectly valid capture of entirely the wrong traffic.

**Saved capture** means opening a file recorded earlier (conventionally `.pcap` or `.pcapng`). This is how captures are shared with a colleague, attached to an incident ticket, or handed to a student — the file is fixed and everyone analysing it sees exactly the same packets.

The analysis skills are identical either way. The practical difference is that a live capture keeps growing under you while you work, which makes it a poor place to reason carefully; most real analysis is done against a saved file for exactly that reason.

**On this platform**, every capture is a saved, fixed dataset. You open one by name and the same packets are there every time — which is what you want while learning, because a conclusion you draw on Tuesday is still checkable on Friday.

## 6. The Mental Model

Everything from here to the end of Hands-on Practice is one step of this chain:

```
NETWORK ACTIVITY        something actually communicated
  ↓
CAPTURE                 an observation point recorded it
  ↓
PACKETS                 individual units of that recording
  ↓
PACKET LIST             one summary line per packet — the overview
  ↓
SELECT A PACKET         narrow to one unit of evidence
  ↓
EXPAND PROTOCOL LAYERS  read what each layer actually contains
  ↓
INTERPRET EVIDENCE      say what this supports — and how confidently
```

Notice what is *not* in that chain: "recognise the protocol name and stop." Reading "DNS" in a column is the beginning of an investigation, not the end of one.

## 7. Frame, Packet, Segment — Say It Precisely

In casual speech everyone says "packet" for everything, including experienced engineers. That's fine in conversation and actively harmful when you're reasoning about evidence, because the three words name three different things stacked inside each other.

```
Ethernet frame              ← what the network interface actually sends/receives
  └── IP packet             ← addressing across networks
        └── TCP segment  /  UDP datagram    ← delivery to a specific program
              └── Application data          ← DNS query, HTTP request, …
```

This is **encapsulation**: each layer wraps the layer above it in its own header, and the interface transmits the whole thing as one unit.

- **Frame** — the complete link-layer unit, the thing the interface handles. It carries MAC addresses.
- **Packet** — the network-layer unit inside the frame. It carries IP addresses.
- **Segment** (TCP) or **datagram** (UDP) — the transport-layer unit inside the packet. It carries port numbers.
- **Application data** — what the program actually wanted to send, inside the segment or datagram.

So which word is correct for a line in Wireshark's packet list? Strictly, what was captured is a **frame** — and Wireshark's own detail view says exactly that, labelling the outermost layer "Ethernet II". But that frame *contains* an IP packet, which contains a TCP segment, which contains an HTTP request. All four descriptions are true simultaneously; they just refer to different layers of the same captured unit.

**The rule to carry forward:** use the word that matches the layer you're discussing. If you're talking about MAC addresses, say frame. If you're talking about IP addresses and routing, say packet. If you're talking about ports, sequence numbers, or TCP flags, say segment. And do not assume the words are interchangeable just because everyone treats them that way — the moment you're explaining evidence to someone else, the precision is what makes you understandable.

## 8. The Protocol Stack, Seen in One Packet

The layers you met separately across Computer Networking, Web Fundamentals and Operating Systems all appear together, in a single captured unit:

```
Ethernet          MAC addresses — who handed this to whom on the local network
  ↓
IPv4 / IPv6       IP addresses — which host, across networks
  ↓
TCP / UDP         ports — which program on that host
  ↓
DNS / HTTP / TLS  the actual application conversation
```

This is Wireshark's real superpower and the reason it's worth learning properly: **you can inspect several layers of the same communication at once.** A single packet can tell you the local interface it came from, the host it was addressed to, the program it was destined for, and what that program was saying — all from one selection.

That also means a single packet can answer questions at very different levels. "Is this reaching the right machine?" is an IP-layer question. "Is it reaching the right service?" is a transport-layer question. "Is the request correct?" is an application-layer question. Knowing which layer holds your answer is most of knowing where to look.

## 9. The Packet List

The packet list is the overview — one summary line per captured unit. Here is a real capture opened on this platform:

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

Column by column, and what each is actually good for:

**Number (`#`)** — the packet's position in the capture. It is an index into *this file*, not anything meaningful about the network. It's how you refer to a specific packet when talking to someone else, and nothing more.

**Time** — when this packet was recorded, by default as seconds elapsed since the capture began. Time is more useful evidence than beginners expect: the *gaps* between packets often tell you more than the packets do. A response 0.001 seconds after a request is a local, healthy service. The same response three seconds later is a fact worth explaining.

**Source / Destination** — who sent it and who it was addressed to, normally as IP addresses. Read these as a pair, always: one packet's source and destination give you one direction of a conversation, and you have not understood the conversation until you've seen both directions.

**Protocol** — Wireshark's best identification of the most specific protocol it recognised in this packet. Note the wording carefully: *best identification*. This is a decoded conclusion, not a field that was transmitted. Core Concepts §20 shows you a real case where this label is not the whole story.

**Info** — a short human-readable summary of what this packet appears to be doing. In the capture above, the Info column alone shows a complete TCP three-way handshake — which is exactly the kind of pattern the overview is for.

**Length** — the size of the captured unit in bytes. Not shown in the list on this platform, but visible when you inspect a single packet (§10), and genuinely useful: size distinguishes an empty acknowledgement from one carrying real data, even when you cannot read the data itself.

Already, from three lines, you can state facts: two hosts are involved; `10.10.10.20` spoke first; `10.10.10.10` replied; the exchange took about two milliseconds. You cannot yet say *why* — that needs the detail view.

## 10. The Packet Details

Selecting a packet expands it into its protocol layers. This is where evidence actually lives. Real output for packet 1 of the capture above:

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

Read it top to bottom and watch the encapsulation from §7 appear literally:

- **Ethernet II** — the frame layer. MAC addresses: the local interfaces that physically handed this frame along.
- **IPv4** — the packet layer. IP addresses, plus **TTL** (Time To Live), a counter decremented by each router the packet crosses.
- **TCP** — the segment layer. Port numbers and **flags** — here, a single `SYN`, which Core Concepts explains in full.
- **Conversation** — not a protocol layer, but this platform's identifier for the exchange this packet belongs to, so you can pull up every related packet at once (§18 of Core Concepts).

Each layer answers a different question, and being able to name which layer answered is part of the skill:

| Layer | What it tells you |
|---|---|
| Ethernet | Which local interfaces handled this frame (MAC addresses) |
| IPv4 | Which hosts, across networks (IP addresses); how many hops remain (TTL) |
| TCP / UDP | Which program endpoint (ports); for TCP, connection state via flags |
| Application | What the program actually said (a DNS query, an HTTP request line) |

**A note on the third pane.** Real Wireshark shows a third view alongside the list and the details: the **packet bytes** pane, displaying the raw captured bytes in hex and ASCII, with the selected field highlighted in place. It matters because it is the ground truth — the decoded field names above it are Wireshark's interpretation of exactly those bytes. This platform's simulator models the packet list and the packet details but has **no byte-level pane**, because its packets are structured objects rather than real captured bytes. That is a real limitation of the simulator, stated plainly rather than papered over: you should know the pane exists and what it's for, and you will meet it the first time you open real Wireshark.

## 11. Endpoints: Who Is Talking to Whom

An **endpoint** is one side of a communication, and identifying both endpoints correctly is step one of every investigation you will ever run.

Four values define them, and packet 1 above gives all four:

| | Value | Meaning |
|---|---|---|
| Source address | `10.10.10.20` | which host sent it |
| Destination address | `10.10.10.10` | which host it was addressed to |
| Source port | `49152` | which program endpoint on the sender |
| Destination port | `80` | which program endpoint on the receiver |

**Direction matters, and it is not a formality.** Source and destination swap on every reply — compare packet 1 and packet 2 in §9 and you'll see `10.10.10.20 → 10.10.10.10` become `10.10.10.10 → 10.10.10.20`. If you read only one direction, you have half a conversation and you will draw conclusions from it that the other half would have corrected.

Direction also tells you **who initiated**, which is frequently the most important fact in an investigation. Look at the port numbers:

```
client, ephemeral port 49152   →   server, port 80
```

Port `49152` is in the dynamic/private range you met in Nmap — a short-lived port the operating system assigned to a client program for the duration of this one connection. Port `80` is a well-known port a server claimed in advance and holds persistently. So this pattern is genuine evidence about roles: **the side using a high, arbitrary-looking port is normally the client, and the side using a low, well-known port is normally the server.**

Normally — because this is a convention, not a law, exactly as the Nmap module said about port numbers generally. Nothing prevents a service from listening on a high port. The pattern is strong evidence about who initiated, not proof about what software is running:

> **WRONG:** "Destination port 80, so this is HTTP."
> **CORRECT:** "Destination port 80 tells me the client addressed a program that claimed port 80 — conventionally a web server. What the program actually spoke is a separate question, answered by looking at the application data."

## 12. MAC Address vs. IP Address vs. Port

Three identifiers, visible together in every TCP or UDP packet you inspect, and constantly confused for one another. Precision here is what makes the rest of the module coherent.

**MAC address** — a link-layer identifier belonging to a network interface, used to deliver a frame across one local network segment. In packet 1: `02:42:0a:0a:0a:14`. Its scope is local. As a frame is forwarded by a router from one network to the next, the MAC addresses are rewritten for each hop — so the MAC addresses you observe identify the interfaces *nearest to your observation point*, not necessarily the original sender's or the final recipient's.

**IP address** — a network-layer identifier for a host, used to route a packet across networks toward its destination. In packet 1: `10.10.10.20`. Its scope is end-to-end for that packet's journey, and it normally survives the whole trip unchanged — which is precisely why it, and not the MAC address, is what you reason about when asking "which machine was this?"

**Port** — a transport-layer number identifying one endpoint of a connection on a host, so the operating system can deliver data to the right program rather than to some other program on the same machine. In packet 1: `49152` and `80`. Its scope is a single host: port 80 on one machine has nothing to do with port 80 on another.

Together:

| | Layer | Identifies | Scope |
|---|---|---|---|
| MAC | Link (Ethernet) | A network interface | One local network segment; rewritten per hop |
| IP | Network | A host | End-to-end across networks |
| Port | Transport | A program endpoint on a host | That one host only |

The compact way to hold it: **MAC gets a frame across the room. IP gets a packet across the world. Port gets the data to the right program once it arrives.**

## 13. How This Platform Models Wireshark

Worth being explicit about, so you know what transfers to the real tool and what doesn't.

Real Wireshark is a graphical application: you pick an interface, watch a live packet list fill, click a packet to expand its layers in a tree, type display filters into a bar at the top, and right-click a packet to follow its stream.

This platform provides a **simulated packet-analysis environment inside the terminal**. The captures are fixed, hand-authored datasets — deterministic, identical every time, and never derived from real traffic. You work with a small command set instead of a GUI:

| Command | What it does | Wireshark equivalent |
|---|---|---|
| `capture` | List available captures / show the active one | The file-open dialog |
| `capture NAME` | Open a capture | Opening a `.pcap` file |
| `packets` | List all packets in the open capture | The packet list pane |
| `show N` | Expand packet N's protocol layers | Clicking a packet → the details pane |
| `follow N` | Show every packet in packet N's conversation | Right-click → Follow → TCP Stream |
| `filter EXPR` | Show only packets matching a display filter | The display filter bar |

**What transfers directly:** the concepts. Encapsulation, endpoints, TCP flags, the handshake, DNS query/response structure, HTTP request/response structure, display-filter reasoning, following a conversation, and above all the analytical discipline of separating observation from conclusion. Those are the actual skills, and they are tool-independent.

**What doesn't transfer:** the exact commands (real Wireshark is a GUI), the byte-level pane (§10), and the breadth of protocol support — real Wireshark decodes thousands of protocols; this simulator models a handful chosen to teach the fundamentals. Where a lesson describes real Wireshark behaviour that the simulator does not implement, it says so explicitly rather than pretending the two are the same tool.

## 14. Common Mistakes

**Calling everything a "packet."** Frame, packet, and segment name different layers of the same captured unit. Use the word that matches what you're discussing. §7.

**Treating absence in a capture as absence on the network.** A capture records one observation point over one time window. "Not in my capture" is not "did not happen." §4.

**Reading only one direction.** Every conversation has two. One direction gives you half the evidence and a confident wrong answer. §11.

**Trusting the Protocol column as a fact.** It's Wireshark's decoded identification, not a transmitted field. Useful, and not infallible. §9.

**Assuming a port number proves an application.** Same correction as the Nmap module, one layer lower. Ports indicate conventional roles; application data provides better evidence. §11.

**Reasoning about hosts using MAC addresses.** MACs identify interfaces one hop away and get rewritten as traffic is routed. For "which machine," use the IP address. §12.

## 15. Practice

Reasoning exercises. No commands yet — work through these before Core Concepts.

1. **Name the layers.** Look at the `show 1` output in §10. Write down which line tells you (a) which local interface handed the frame along, (b) which host it was addressed to, (c) which program endpoint it was destined for. Name the layer that supplied each answer.
2. **Use the right word.** A colleague says "the packet's MAC address is wrong." Which word should they have used, and why does the distinction matter here specifically?
3. **Identify the roles.** In §9's capture, ports `49152` and `80` appear. Which host is behaving as the client, which as the server, and what specific evidence supports each answer? What would make you doubt it?
4. **Reason about absence.** You're told "the capture proves this host never contacted the file server." What would you need to know about how the capture was taken before accepting that claim?
5. **Correct the conclusion.** Someone points at packet 2 (`10.10.10.10 → 10.10.10.20`) and says "the server started this conversation." What in the capture contradicts them?
6. **Explain the gap.** Packets 1, 2 and 3 are one millisecond apart. Suppose packet 2 had instead arrived at time `4.001`. State one observation, one interpretation, and one thing you'd want to check before concluding anything.

## 16. Knowledge Check

1. What does a packet capture actually represent, and what are the three limits that follow from that?
2. What is the difference between a live capture and a saved capture? Why is most careful analysis done on a saved file?
3. Explain frame, packet, and segment in terms of encapsulation. Why isn't "packet" always the right word?
4. Which layer carries MAC addresses, which carries IP addresses, and which carries ports?
5. In the packet list, what is the Protocol column actually telling you — a transmitted fact, or something else?
6. Why does the direction of a packet matter when identifying endpoints?
7. What does an ephemeral source port paired with a well-known destination port suggest about which host initiated the connection? Why is that evidence rather than proof?
8. Why can't you use a MAC address to reason about which distant machine sent something?

## 17. Key Takeaways

- Wireshark captures traffic and decodes it into readable protocol layers. The capturing is easy; the analysis is the skill.
- A capture is past tense, partial, and time-bounded. Absence from a capture is not absence from the network.
- Frame, packet and segment are three layers of one captured unit, not three words for the same thing. Encapsulation is why.
- One packet can be inspected at several layers at once — link, network, transport, application — and each layer answers a different kind of question.
- The packet list is the overview; the packet details are the evidence. Time gaps in the list are evidence too.
- An endpoint is an address plus a port. Direction distinguishes client from server, and reading only one direction gives you half a conversation.
- MAC is local and per-hop, IP is end-to-end, port identifies a program on one host.
- Protocol labels and port conventions are strong clues, not proof. That distinction is the whole discipline.

## 18. What's Next

**Core Concepts** turns this vocabulary into analysis. You'll watch a TCP connection open packet by packet and learn exactly what evidence proves each step of the three-way handshake; read TCP flags and know which ones you can actually recognise in a capture; work through DNS and HTTP exchanges as real captured evidence; learn what does and does not stay visible when traffic is encrypted with TLS; and — the skill that makes every other one usable — learn to narrow a noisy capture with display filters, including the difference between a display filter and a capture filter, which are not the same thing and are constantly confused.
