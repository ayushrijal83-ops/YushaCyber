# Core Concepts: Addressing — MAC, IP, Subnets, and Ports

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what a MAC address identifies and why it only matters on the local network
- explain the structure of an IPv4 address and the difference between private and public addresses
- read CIDR notation (like `/24`) and calculate a subnet's network address, broadcast address, and usable host range
- explain what a port is and how it relates to an IP address
- explain why each of these matters for security work later in this platform

## 2. Why This Matters

Every security tool you'll touch after this module works directly with these four ideas. Nmap enumerates IP addresses and ports. Wireshark shows you MAC and IP addresses on every single packet. A pentest scope is almost always defined as a CIDR range. A SOC analyst reading logs is constantly asking "what IP, what port, what does that combination mean?" This lesson is the vocabulary and math that all of that depends on.

## 3. MAC Addresses: Local Identity

A **MAC address** (Media Access Control address) is a unique identifier burned into a network interface — every network card, real or virtual, has one. It looks like six pairs of hex digits: `00:1A:2B:3C:4D:5E`.

**The key property: a MAC address only matters on the local network segment.** When a switch receives data, it looks at the destination MAC address to decide which physical port to forward it out of — that's the switch's entire job. A MAC address is never used to route data across the wider Internet; once data leaves your local network through a router, MAC addresses get rewritten at each hop and stop being relevant to the journey.

**How a host learns another host's MAC address** on the same network is a protocol called ARP (Address Resolution Protocol) — a host broadcasts "who has IP address X?" and the owner of that IP replies with its MAC address. You don't need to operate ARP directly at this stage; the important takeaway is *why* it exists: IP addresses are what applications and humans use, but the actual local hardware delivery still runs on MAC addresses, so something has to bridge the two.

**Broadcast, briefly.** A switch normally forwards data to one specific port (the one matching the destination MAC), but some traffic — like the ARP request above — is deliberately sent to *every* device on the local network at once. This is called a broadcast, and it's how a host can ask "who has this address?" without already knowing who to ask directly.

## 4. IP Addresses: Global Identity

An **IPv4 address** is written as four numbers from 0–255 separated by dots, like `192.168.1.10`. Unlike a MAC address, an IP address can identify a host anywhere reachable on a network — including the entire public Internet — which is exactly why routers need it to make forwarding decisions.

**Private vs. public addresses.** Certain address ranges are reserved for private, internal networks and are never routable on the public Internet:

| Range | Common use |
|---|---|
| `10.0.0.0 – 10.255.255.255` | Large private networks (this platform's simulated labs use `10.10.10.x`) |
| `172.16.0.0 – 172.31.255.255` | Private networks |
| `192.168.0.0 – 192.168.255.255` | Private networks (most home routers) |

If you see one of these addresses, you already know something concrete: that host is on a private network, not directly reachable from the public Internet without something translating for it (you'll meet that concept — NAT — in the next lesson).

**Loopback and localhost.** `127.0.0.1` is a special address that always means "this machine, talking to itself" — traffic sent to `127.0.0.1` never touches a real network interface at all. You'll see this constantly once you start running local tools and services.

## 5. Subnetting: Dividing a Network into Ranges

A **subnet** is a defined, contiguous range of IP addresses treated as one local network. Subnetting is how you describe *exactly* which addresses belong to that range — and it's simple arithmetic once you see the pattern, not something to memorize from a table.

**CIDR notation.** You'll see subnets written like `192.168.1.0/24`. The number after the slash — the **prefix length** — tells you how many of the address's 32 bits are fixed as the "network portion." The remaining bits are the "host portion," free to vary for each individual device on that subnet.

`/24` means the first 24 bits (the first three of the four numbers) are fixed, and only the last 8 bits can vary:

```
192.168.1.0/24
└──────┬──────┘ └┬┘
  network part   host part (8 bits free = 256 possible values)
```

With 8 free bits, there are 2⁸ = 256 possible addresses in this subnet (`192.168.1.0` through `192.168.1.255`). But two of those are always reserved and never assigned to a host:

- **Network address** (`192.168.1.0`) — identifies the subnet itself, not a host.
- **Broadcast address** (`192.168.1.255`) — the last address, used to reach every host on the subnet at once.

That leaves **254 usable host addresses** (`192.168.1.1` through `192.168.1.254`) — the formula is **2^(host bits) − 2**.

**Shrinking the subnet.** A larger prefix number means *fewer* free host bits, which means a *smaller* subnet:

| CIDR | Host bits | Usable hosts | Example range |
|---|---|---|---|
| `/24` | 8 | 254 | `192.168.1.1`–`192.168.1.254` |
| `/25` | 7 | 126 | `192.168.1.1`–`192.168.1.126` |
| `/26` | 6 | 62 | `192.168.1.1`–`192.168.1.62` |
| `/27` | 5 | 30 | `192.168.1.1`–`192.168.1.30` |

Notice the pattern: every time the prefix grows by 1, the usable host count roughly halves, because you've taken one more bit away from the host portion. This is the entire logic of subnetting — there's no separate table to memorize, just "how many bits are left for hosts, and what does 2^(that number) − 2 give me."

**Worked example.** Take `192.168.1.64/26`. The prefix is `/26`, so there are 6 host bits (2⁶ = 64 total addresses in the block). Since `/26` blocks fall on multiples of 64, this block runs from `192.168.1.64` (network address) to `192.168.1.127` (broadcast address), giving usable hosts `192.168.1.65` through `192.168.1.126` — 62 addresses (2⁶ − 2).

**The subnet mask** is the same information as the CIDR prefix, written differently — `/24` is the same thing as a mask of `255.255.255.0`. You'll encounter both notations; they always mean the same fixed/free bit split.

## 6. Ports and Sockets

An **IP address gets you to the right machine. A port gets you to the right service on that machine.** A single server can run a website, an SSH server, and a mail server simultaneously, all reachable at the same IP address — the port is what tells incoming data which of those services it's meant for.

Port numbers range from 0–65535. A handful of low-numbered ports are so standardized they're called **well-known ports**:

| Port | Service |
|---|---|
| 22 | SSH (remote terminal access) |
| 53 | DNS |
| 80 | HTTP (unencrypted web traffic) |
| 443 | HTTPS (encrypted web traffic) |

The combination of an IP address, a port, and a protocol (TCP or UDP — covered fully next lesson) is called a **socket** — the complete, unambiguous address of one specific conversation. `10.10.10.20:80` isn't just an IP with an extra number tacked on; it's a socket, specifying exactly "the web service on this particular machine."

A port that's actively accepting connections is called a **listening port**. When you connect *to* a server, you're connecting to one of its listening ports (a fixed, well-known number like 80); your own machine, meanwhile, uses a temporary, randomly chosen **source port** for that one conversation, closed again once it's done.

## 7. Why This Matters for Security

**IP addresses** are how you identify assets — every scope document in a real penetration test starts with a list of IP ranges (usually CIDR blocks) that are in or out of bounds. **Ports** are the first thing enumerated in any reconnaissance: an open port means a running service, and a running service is something that can potentially be attacked or misconfigured. **Subnetting** is also a security control in its own right — segmenting a network into smaller subnets limits how far an attacker can move if they compromise one host on it. None of this requires deep expertise yet — it requires exactly the vocabulary this lesson just gave you.

## 8. Common Mistakes

**Confusing the network address or broadcast address with a usable host.** `192.168.1.0` and `192.168.1.255` in a `/24` are never valid addresses to assign to a device.

**Assuming a smaller prefix number means a smaller subnet.** It's the opposite — `/24` is *larger* than `/26`. Fewer fixed network bits means more free host bits means more addresses.

**Treating a private IP address as unreachable from anywhere.** Private addresses aren't routable on the public Internet, but they're absolutely reachable *within* their own network — this distinction matters constantly once you start working with internal lab networks.

**Confusing a port number with a protocol.** Port 80 is *conventionally* HTTP, but nothing stops a service from listening on any port — port numbers are a strong hint, not a guarantee, which is exactly why tools like Nmap try to fingerprint the actual service instead of trusting the port number alone.

## 9. Practice

**Exercise 1 — Guided.** Given `10.10.10.0/24`, state the network address, the broadcast address, and the number of usable host addresses.

**Exercise 2 — Independent.** Given `192.168.5.128/27`, calculate the number of host bits, the number of usable hosts, and the broadcast address.

**Exercise 3 — Reasoning.** You see traffic to `172.16.4.9`. Without knowing anything else, what can you already conclude about where that host is (public Internet vs. private network)?

**Challenge.** A server is described as listening at `10.10.10.10:80/tcp`. Explain, in one sentence each, what each of the three parts of that address (IP, port, protocol) tells you.

## 10. Knowledge Check

1. Why does a MAC address stop being relevant once data leaves your local network?
2. What's the difference between the network address and the broadcast address of a subnet?
3. Why does a `/26` subnet have fewer usable hosts than a `/24` subnet?
4. What is a socket, and what three pieces of information does it combine?
5. Why is a private IP address like `192.168.1.10` not directly reachable from the public Internet?

## 11. Key Takeaways

- A MAC address identifies a physical interface on the *local* network; an IP address identifies a host that can be reached across the wider network, including the Internet.
- CIDR notation (`/24`, `/26`, etc.) defines how many address bits are fixed as "network" vs. free as "host" — usable hosts = 2^(host bits) − 2.
- The network address and broadcast address of a subnet are reserved, never assignable to a host.
- A port identifies a specific service on a host; IP + port + protocol together form a socket.
- Ports and IP ranges are exactly what security reconnaissance and pentest scoping are built on.

## 12. What's Next

**Hands-on Practice** shows you what actually happens when two hosts communicate: how a TCP connection is established, how DNS turns a name into an IP address, how a host finds its way to a destination through a default gateway — and gives you the real diagnostic commands to observe all of it in this platform's terminal.
