# Hands-on Practice: How Hosts Actually Communicate

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain the difference between TCP and UDP, and when each is the right tool
- explain what happens during a TCP three-way handshake and why it exists
- trace exactly what happens during DNS resolution, from typed name to connected IP
- explain what a default gateway is and why a host without one can't leave its local network
- use `ip addr`, `ip route`, and `ss` to inspect a machine's real network configuration
- reason through a broken network step by step, instead of guessing at fixes

## 2. Why This Matters

Everything in Core Concepts was vocabulary — MAC, IP, subnets, ports. This lesson is where that vocabulary becomes a working process: how a connection actually gets established, how a name becomes an address, and how you diagnose a network that isn't working, the same way you'll diagnose a target, a lab, or a real production issue for the rest of your career in this field.

## 3. TCP vs. UDP: Two Ways to Send Data

Once your data is addressed (IP) and aimed at the right service (port), it still has to actually get delivered — and there are two fundamentally different ways that can happen.

**TCP (Transmission Control Protocol)** is **connection-oriented**: before any real data is sent, both sides perform a handshake (Section 4) to agree the connection exists. Every piece of data is numbered (sequenced) so it can be reassembled in the right order, and the receiver acknowledges what it got — if something is lost, TCP notices and retransmits it. This makes TCP **reliable**: the sender can trust that data either arrives correctly, or the connection reports a failure. That reliability isn't free — it costs extra round trips and overhead.

**UDP (User Datagram Protocol)** is **connectionless**: there's no handshake, no acknowledgement, and no automatic retransmission. A UDP sender just sends data and moves on, trusting nothing about whether it arrived. This makes UDP lower-overhead than TCP — but "lower overhead" is not the same as "faster" as a blanket rule; it depends entirely on what the application actually needs.

**When each is used, and why:** DNS uses UDP because a single lost query is cheap to just retry — setting up a full TCP connection for one tiny question-and-answer would be wasted overhead. Web browsing (HTTP) uses TCP because a webpage silently missing 10% of its data isn't acceptable — reliability matters more than avoiding handshake overhead. The right choice always comes down to: **does this application need guaranteed, ordered delivery, or can it tolerate loss in exchange for less overhead?**

## 4. The TCP Three-Way Handshake

Before two hosts exchange any real data over TCP, they perform a three-message handshake to establish the connection:

```
Client                          Server
  │                                │
  │ ────────── SYN ─────────────▶  │   "I'd like to connect"
  │                                │
  │ ◀──────── SYN-ACK ──────────── │   "Acknowledged — I'd like to connect too"
  │                                │
  │ ────────── ACK ─────────────▶  │   "Acknowledged — connection established"
  │                                │
```

**SYN** ("synchronize") — the client sends the first message, proposing a connection and a starting sequence number for the data it plans to send.

**SYN-ACK** — the server acknowledges the client's SYN *and* sends its own SYN in the same message, proposing its own starting sequence number for data flowing back to the client.

**ACK** — the client acknowledges the server's SYN. At this point, both sides have confirmed they can send *and* receive, and the connection is officially established — only now does real application data (like an HTTP request) start flowing.

**Why it exists:** the handshake isn't ceremony — it's how both sides confirm, before committing any real data, that the other side is actually listening and reachable, and it's how they agree on the starting sequence numbers that make reliable, ordered delivery possible for the rest of the connection. This is also exactly what a port scanner is probing when it checks whether a port is "open": a port that completes a SYN/SYN-ACK exchange has a service actively listening on it.

## 5. DNS: Turning Names into Addresses

Humans use names (`example.local`); computers route traffic using IP addresses. **DNS (Domain Name System)** is the lookup service that bridges the two:

```
You type: example.local
    ↓
Your machine asks its configured DNS resolver: "what's the IP for example.local?"
    ↓
DNS query sent to the resolver (over UDP, port 53 — see Section 3: a lost query is cheap to retry)
    ↓
Resolver replies with the matching IP address
    ↓
Your machine now has the IP, and connects to *that* — DNS's job is done
```

Let's watch this actually happen in this platform's terminal:

```bash
nslookup example.local
```

```
Server:		10.10.10.53

Name:	example.local
Address: 10.10.10.10
```

**What this output means:** `Server: 10.10.10.53` is the DNS resolver that answered your query — not the site itself. `Name: example.local` / `Address: 10.10.10.10` is the actual answer: this hostname maps to that IP. Every connection you make by name — a website, a lab target — starts with an exchange that looks exactly like this one, even though your browser normally hides it from you.

**When DNS fails**, the resolver reports it explicitly rather than staying silent:

```
Server:		10.10.10.53

** server can't find fake.local: NXDOMAIN
```

`NXDOMAIN` means "no such domain" — the resolver understood the question and answered honestly that no record exists. This is a distinct, specific failure, not a generic connectivity problem — a distinction you'll rely on directly in Section 8.

## 6. Routing and the Default Gateway

Your earlier `ping` and `nslookup` examples both worked because your machine knew *where to send data it couldn't deliver locally*. That's the job of the **default gateway** — the router your machine hands off to whenever the destination isn't on its own local subnet.

```
Host (10.10.10.20)
    ↓  destination isn't on my local subnet — hand off to my gateway
Default Gateway (10.10.10.1)
    ↓  gateway forwards it onward, toward the destination network
Router(s) beyond the local network
    ↓
Destination host
```

Inspect this directly:

```bash
ip route
```

```
default via 10.10.10.1 dev eth0
10.10.10.0/24 dev eth0
```

**What this means:** `10.10.10.0/24 dev eth0` says "anything in this subnet, deliver directly out the `eth0` interface — no gateway needed, it's local." `default via 10.10.10.1 dev eth0` is the fallback rule: "anything that doesn't match a more specific route, send to `10.10.10.1`, and let it figure out the next step." Every host needs a default gateway to reach anything outside its own subnet — without one, your machine simply has no idea where to send traffic bound for the wider network, even if its own IP configuration is otherwise perfect.

**A brief note on NAT.** Recall from Core Concepts that private addresses like `10.10.10.20` aren't routable on the public Internet. **NAT (Network Address Translation)**, typically performed by a router at the edge of a private network, rewrites private source addresses to a shared public one as traffic leaves the network (and rewrites replies back) — it's why an entire private network of `192.168.x.x` devices can share one public IP address to reach the Internet. NAT is a practical necessity, not a security boundary on its own — a common misconception worth avoiding early.

## 7. Inspecting Your Own Machine

Two more commands round out the diagnostic toolkit — both real, both usable right now in this platform's terminal.

**`ip addr`** — shows every network interface on your machine and its assigned IP address.

```bash
ip addr
```

```
eth0:
    inet 10.10.10.20/24
    state UP
lo:
    inet 127.0.0.1/8
    state UP
```

**What this means:** `eth0` is your real network interface, with IP `10.10.10.20/24` (recognize that CIDR notation from Core Concepts) and `state UP` — meaning it's active and able to send/receive. `lo` is the loopback interface from Core Concepts (`127.0.0.1`) — always present, always separate from your real network connectivity. **Common mistake:** if `eth0` ever reports `state DOWN`, nothing else about your IP configuration matters yet — a down interface can't send anything at all, which is exactly the first thing to check when a machine can't reach the network (Section 8).

**`ss`** — lists the ports your own machine is actively listening on.

```bash
ss
```

```
State   Local Address:Port
LISTEN  10.10.10.20:22  (tcp/ssh)
LISTEN  10.10.10.20:80  (tcp/http)
```

**What this means:** your own machine is running two services — SSH on port 22, and a web server on port 80 — and both are in the `LISTEN` state, meaning they're ready to accept incoming connections. This is the same read you'll later do against a *remote* target with Nmap; `ss` is just this exact question asked about the machine you're sitting on.

## 8. Troubleshooting: Reasoning from Symptoms

Here's a realistic scenario: **"My machine has an IP address, but I can't reach anything."** Don't guess — check each layer in order, closest to your machine first:

1. **Is the interface even up?** `ip addr` (or `ip link`) — if it reports `state DOWN`, nothing past this point matters until it's fixed.
2. **Is the IP address correct for this network?** `ip addr` again — compare the address and its `/24` (or whatever prefix) against the network you're actually supposed to be on. An address on the wrong subnet behaves like a wrong address, even though it looks superficially valid.
3. **Is the default gateway correct?** `ip route` — a gateway address outside your actual subnet's range can't ever be reached, so nothing beyond your local network will work even if everything else is fine.
4. **Can you reach the gateway itself?** `ping <gateway>` — this isolates "my local network is fine" from "the wider network is the problem."
5. **Can you reach a host beyond the gateway?** `ping <remote-host>` — confirms routing is actually working end-to-end, not just to the first hop.
6. **Does name resolution work?** `nslookup <hostname>` — and here's the critical distinction: if `ping <ip>` succeeds but `nslookup <hostname>` fails, that is specifically a **DNS problem**, not a connectivity problem. Conflating the two is one of the most common beginner mistakes in troubleshooting — they have different causes and different fixes.

This exact reasoning chain — interface, IP, gateway, connectivity, DNS — is precisely what the platform's **Network Troubleshooting** terminal mission (linked below) walks you through hands-on, using real broken configurations you diagnose and repair yourself.

## 9. Common Mistakes

**Assuming "I have an IP address" means "my network is configured correctly."** An interface can be up with a perfectly valid-looking IP address that's still on the wrong subnet entirely.

**Treating DNS failure and connectivity failure as the same problem.** They have different symptoms (Section 8, step 6) and require checking completely different things.

**Believing UDP is unconditionally "faster than" TCP.** UDP has less overhead per packet, but an application that needs reliable delivery will end up building its own retry logic on top of UDP anyway — "faster" depends entirely on what the application actually needs, not a fixed rule.

**Forgetting that NAT isn't a firewall.** NAT solves an addressing problem (too few public addresses), not a security problem — don't confuse "this device isn't directly addressable from outside" with "this device is protected."

## 10. Practice

**Exercise 1 — Guided.** Run `ip addr` in the YushaCyber terminal and identify your interface's IP address and its CIDR prefix.

**Exercise 2 — Independent.** Run `ip route` and identify your default gateway. Then `ping` it and confirm you get a reply.

**Exercise 3 — Reasoning.** You run `ping 10.10.10.10` and it succeeds, but `nslookup example.local` returns `NXDOMAIN`. Using Section 8's reasoning chain, what category of problem is this — and what step first isolated it?

**Challenge.** Run `ss` and identify every listening service on your machine, including its port number and protocol.

## 11. Capstone: The Networking Fundamentals Mission

Everything in this module comes together in the platform's **Networking Fundamentals** terminal mission, on a simulated LAN using the exact commands and addresses from this lesson:

1. Inspect your network interfaces (`ip addr`)
2. Identify your own IPv4 address
3. Inspect the routing table (`ip route`)
4. Identify the default gateway
5. Test connectivity to the gateway (`ping`)
6. Test connectivity to a web server across the network
7. Inspect your machine's listening services (`ss`)
8. Identify the open web server port
9. Perform a DNS lookup (`nslookup`)
10. Inspect the local hosts file (`cat /etc/hosts`)
11. Identify the DNS server's address
12. Confirm connectivity to a file server to complete the mission

Once you're comfortable with that mission, **Network Troubleshooting** puts Section 8's diagnostic reasoning to the test on a network that starts broken — a down interface, a misconfigured IP, a wrong gateway, and a DNS failure that only appears *after* connectivity is restored — and asks you to find and fix each layer in order, exactly as you practiced above.

## 12. Knowledge Check

1. What's the fundamental difference between how TCP and UDP handle reliability?
2. Put the three messages of the TCP handshake in order, and say which side sends each one.
3. If `nslookup` succeeds but returns the wrong-looking IP, what part of the DNS process would you suspect?
4. What does a host's default gateway actually do, conceptually?
5. A machine can `ping` its gateway but not a host beyond it. Using Section 8's reasoning, what would you check next?

## 13. Key Takeaways

- TCP is connection-oriented and reliable (handshake, sequencing, retransmission); UDP is connectionless and lower-overhead, with no delivery guarantee — the right choice depends on what the application needs, not a blanket rule.
- The TCP handshake (SYN → SYN-ACK → ACK) is how both sides confirm reachability and agree on sequencing before real data flows.
- DNS resolves a name to an IP through a query/response exchange with a resolver — `NXDOMAIN` means the resolver worked correctly and reported "no such name," a different failure than unreachability.
- A default gateway is required to reach anything outside your local subnet; `ip route` shows you exactly what your machine will do with traffic bound for elsewhere.
- Real troubleshooting checks interface → IP → gateway → connectivity → DNS, in that order, rather than guessing.

## 14. What's Next

This is the last lesson in Computer Networking — you now have the addressing vocabulary and communication mental model that every later network-facing tool in this platform assumes you already have. The roadmap's next module, **Python Programming**, shifts focus to writing code — and the module after that, **Web Fundamentals**, is where HTTP (the protocol you saw mentioned throughout this lesson) gets the deep treatment it deserves, built directly on everything you just learned about how hosts find and connect to each other.
