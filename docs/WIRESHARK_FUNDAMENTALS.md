# Wireshark Fundamentals Mission (YC-034.9)

## Purpose

Teaches packet-analysis fundamentals — reading protocol layers, recognizing
the TCP three-way handshake, analyzing DNS and HTTP traffic, following a
conversation, applying display filters, and investigating a capture for
unusual traffic — through a fully simulated capture environment. The
student investigates evidence rather than memorizing protocol
definitions; the real Wireshark application is never installed, executed,
or required.

This is the first packet-analysis mission, so unlike YC-034.6–034.8 (which
all extended the existing `VirtualNetwork`/`VirtualHost` model), it adds a
genuinely new, independent engine: packet *traffic* is a different concept
from network *state*, and nothing resembling it existed yet. It follows the
same reuse discipline as everything else in this series: existing
`MissionRunner`, `MissionValidator`, terminal command registry, XP/
achievement services, and mission UI — unchanged.

## Simulated packet architecture

New module: `app/core/terminal/packets.py` (kept alongside `network.py` in
the existing `app/core/terminal/` package rather than the ticket's
suggested `app/core/network/packets/` — everything terminal-simulation
related already lives in one package; splitting it would fragment reuse
without benefit).

- **`Packet`** — a structured dataclass (number, timestamp, length,
  protocol, src/dst MAC, src/dst IP, src/dst port, TCP flags, TTL, payload
  summary, application protocol, conversation id). Every field is data;
  nothing is a hardcoded terminal string at construction time.
- **`PacketCapture`** — a fixed list of packets plus read-only inspection
  (`get`, `conversation`, `filter`) and text rendering (`list_text`,
  `detail_text`, `conversation_text`). Never mutated after construction.
- **`PacketLab`** — holds every capture available to a mission session and
  which one is currently "open" (mirrors opening a `.pcap` file), plus the
  selected packet and last filter typed. Small, JSON-serializable state
  (`to_dict`/`apply_state`) that survives session resume the same way
  `VirtualNetwork`'s mutation snapshot does (YC-034.6).

Both `Packet` and `PacketCapture` are pure data/formatting — the same
"structured data in, formatted text out" separation used by `VirtualNetwork`
for `ip addr`/`nmap` output.

### Why captures are Python functions, not mission-config dicts

Every other mission config (`"filesystem"`, `"network"`, `"permissions"`)
is a plain declarative dict. Packet captures deliberately break that
pattern: a 30–45 packet capture with a dozen fields per packet is
qualitatively more data than a handful of host/service entries, and a
dict literal that size in `mission_loader.py` would be far less readable
than the same data built with a small, deterministic loop. The mission's
config stays declarative at the boundary that matters —
`"packet_captures": ["handshake", "dns", "http", "icmp", "mixed",
"investigation"]` is just a list of names — while the packet *content*
lives in maintainable builder functions in `packets.py`, looked up through
`CAPTURE_REGISTRY`. `build_packet_lab(names)` calls each builder fresh, so
concurrent sessions never share mutable packet data (the same
shared-reference bug fixed for `VirtualFS` in YC-034.3 is avoided here by
construction).

## Simulated captures

| Capture | Packets | Teaches |
|---|---:|---|
| `handshake` | 3 | SYN / SYN-ACK / ACK |
| `dns` | 2 | A single query + response |
| `http` | 8 | Full handshake + GET + 200 OK + teardown |
| `icmp` | 2 | Echo request/reply |
| `mixed` | 32 | DNS + HTTP + ICMP + background UDP together — filtering becomes necessary |
| `investigation` | 45 | Realistic background traffic (DNS/HTTP/ICMP) plus one anomalous TCP connection to `10.10.10.77:4444` |

All IPs/domains are fictional (`*.training`, the `10.10.10.0/24` lab range
already used by every prior networking mission). `handshake`/`dns`/`http`/
`icmp` are kept small and focused — a handshake capture with 50+ packets
would defeat its own teaching purpose. `mixed` and `investigation` are
generated larger via small deterministic loops (fixed port/hostname
increments, never `random`) specifically because filtering only makes
pedagogical sense once there's real volume to filter through — the
ticket's "50–200 packets" guidance is applied where it matters rather than
uniformly padding every capture.

The investigation capture's anomaly is analysis-only, matching the
ticket's explicit instruction: an unusual destination and port, a generic
"Unrecognized binary payload" summary — no exploit content, no attack
mechanics, nothing to execute.

## Supported filters

A small, safe subset, matching the ticket's list exactly: bare protocol
names (`tcp`, `udp`, `dns`, `http`, `icmp`) and `field == value`
comparisons for `tcp.port`, `udp.port`, `ip.addr`, `ip.src`, `ip.dst`.
`PacketCapture.filter()` is pure Python string parsing over the in-memory
packet list — no filter ever touches anything outside that list.

## Terminal commands

Extends the existing command registry (`app/core/terminal/commands.py`) —
no second terminal. All read from `sh.packet_lab` only:

- `capture [name]` — list available captures / open one by name
- `packets` — list all packets in the active capture
- `show N` / `packet N` (alias) — full layer-by-layer detail for packet N
- `follow ID` (accepts a conversation id or a packet number) — the full
  packet sequence for one exchange
- `filter EXPR` — apply a display filter to the active capture

## Conversation tracking

A conversation id is computed as an order-independent pair of
`ip:port` (or bare IP for ICMP), so both directions of one exchange map to
the same id regardless of who's "source" in a given packet:
`tcp:10.10.10.10:80<->10.10.10.20:49152`. Assigned once per exchange, not
recomputed per packet.

## Mission objectives (12, 450 XP)

Open the handshake capture → read source/destination IPs → filter TCP →
recognize the three-way handshake → read ports → filter DNS in mixed
traffic → analyze an HTTP GET → follow a conversation → IP filter → port
filter → analyze mixed traffic (recognizing background UDP) → final
investigation (find the anomaly and write a structured conclusion).

## Validation changes

None. Every check reuses the existing `command`/`output_contains`/
`file_contains` types (`app/core/missions/mission_validator.py`, including
the list-of-alternatives support added in YC-034.8) — every objective's
evidence appears in `show`/`filter`/`follow` output that's deterministic
and only produced by actually running the right inspection, so text
matching is state matching here, same principle used throughout this
series wherever it holds. The final investigation reuses the
"write-a-conclusion-to-a-file" pattern from Network Reconnaissance
(YC-034.8) rather than inventing a new mechanism — a `wireshark/` workspace
directory is seeded, validated with `file_contains`.

## CyberMentor integration

`MissionRunner.ai_context()` (already extended in YC-034.8 with
`last_output`) gains one more section when a packet lab is attached:
`packet_lab` — active capture name, total packet count, selected packet
number, and last filter typed (`MissionRunner.packet_lab_status()`, also
reused by `to_dict()` for the mission UI panel). Nothing mission-specific
is hardcoded into the shared context function — any future packet-analysis
mission gets this for free by attaching a `packet_lab`.

## Security isolation

`packets.py` has zero imports beyond `dataclasses`/`typing`/
`collections.abc` — no `socket`, `subprocess`, `os`, `requests`, or any
capture/networking library of any kind. Every packet is Python data
constructed once at capture-build time; `filter`/`show`/`follow` only ever
read that in-memory list. Verified with an AST-walking import check (not a
substring search — this module's own docstrings mention "socket" while
explaining they avoid one, which is exactly the false-positive a naive
check would hit) plus a source-body scan of the terminal command handlers
for shell-execution patterns.

## Achievement

"Packet Detective" was evaluated and not added as a database row, for the
same reason as "Network Detective" (YC-034.6) and "Recon Scout" (YC-034.8):
the existing achievement metric calculator doesn't yet track "missions
completed," so a new row would never unlock. The existing generic
mission-completion achievement check still runs unchanged.

## UI

Reuses the existing mission UI entirely. One small addition: a "PACKET LAB"
status block in the existing objectives sidebar, styled with the same CSS
classes as the YC-034.6 "NETWORK STATUS" panel (no new stylesheet), updated
live after every command via the existing `packet_lab_status` field on the
mission API responses. The ticket's optional clickable packet table was
**not** built: the terminal's own `packets`/`show`/`filter` commands
already provide the full experience textually, and a clickable grid would
need new frontend interaction wiring (selection state, click handlers, a
richer table component) that the ticket itself gates on "only if it
integrates cleanly" — the terminal remaining the primary, fully-capable
interface was judged the safer call.
