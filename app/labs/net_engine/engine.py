"""Virtual Network Services & Connectivity Engine — core (YC-026.3).

Design intent
=============
This is the *only* place in the codebase that models "how a packet gets
from A to B in the simulated network". Any simulator (interactive
network, Nmap, Wireshark, firewall, AD, SOC) that needs reachability,
packet flow, or service probes calls into this module instead of
implementing its own BFS or its own ping.

Everything below is a pure function of a topology snapshot. There are no
sockets. There is no subprocess. There is no filesystem. Nothing here
learns anything, mutates anything, or persists anything — session state
still lives where it always has (per-simulator state envelope). This
module answers questions; simulators decide what to *do* with the
answers (award XP, mutate ARP, fill an event).

The engine works off a duck-typed ``HostLike`` protocol so both
:class:`app.labs.topology.engine.Device` (topology-JSON world) and
:class:`app.labs.interactive_network_simulator.Host` (simulator-owned
world) can feed it — no coupling to either concrete class.

Determinism
-----------
Ping latency, hop latency and packet IDs are derived from a stable hash
of ``(source, destination, port, sequence)`` so lab objectives can match
exact output. That means unit tests are reproducible and simulators can
diff two snapshots without flakiness. There's still enough variation
between different flows that outputs look real.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional, Protocol


# ===========================================================================
# Constants
# ===========================================================================
DEFAULT_TTL: int = 64
"""Starting TTL for outbound packets. Real Linux uses 64, Windows 128;
we standardise on 64 for readable traceroute output."""


# ===========================================================================
# Service catalogue — the ticket's mandated port/service list plus a
# handful of adjacent ones that are cheap to include and will save the
# next lab from a code change.
# ===========================================================================
SERVICE_CATALOGUE: dict[int, dict[str, str]] = {
    21:   {"name": "ftp",         "protocol": "tcp", "description": "File Transfer Protocol"},
    22:   {"name": "ssh",         "protocol": "tcp", "description": "Secure Shell"},
    23:   {"name": "telnet",      "protocol": "tcp", "description": "Telnet (unencrypted)"},
    25:   {"name": "smtp",        "protocol": "tcp", "description": "Simple Mail Transfer Protocol"},
    53:   {"name": "dns",         "protocol": "udp", "description": "Domain Name System"},
    80:   {"name": "http",        "protocol": "tcp", "description": "Hypertext Transfer Protocol"},
    110:  {"name": "pop3",        "protocol": "tcp", "description": "Post Office Protocol v3"},
    143:  {"name": "imap",        "protocol": "tcp", "description": "Internet Message Access Protocol"},
    443:  {"name": "https",       "protocol": "tcp", "description": "HTTP over TLS"},
    445:  {"name": "smb",         "protocol": "tcp", "description": "SMB / CIFS file sharing"},
    3306: {"name": "mysql",       "protocol": "tcp", "description": "MySQL"},
    3389: {"name": "rdp",         "protocol": "tcp", "description": "Remote Desktop Protocol"},
    5432: {"name": "postgresql",  "protocol": "tcp", "description": "PostgreSQL"},
    8080: {"name": "http-alt",    "protocol": "tcp", "description": "HTTP (alternate)"},
}


def service_name_for(port: int) -> str:
    """Human name for a well-known port, or "unknown" if we've never
    heard of it. Deliberately doesn't guess — a real Nmap will fingerprint;
    the simulator's answer stays honest until that lab lands."""
    entry = SERVICE_CATALOGUE.get(port)
    return entry["name"] if entry else "unknown"


# ===========================================================================
# Packet — the atom of the engine. Immutable + hashable.
# ===========================================================================
class PacketStatus(str, Enum):
    """Outcome of routing a single packet. Kept as strings so JSON dumps
    of a captured pcap-like feed stay human-readable in the future
    Wireshark simulator."""

    DELIVERED           = "delivered"
    UNREACHABLE_HOST    = "unreachable-host"
    UNREACHABLE_NETWORK = "unreachable-network"
    TIMEOUT             = "timeout"
    TTL_EXCEEDED        = "ttl-exceeded"
    OFFLINE             = "offline"
    PORT_CLOSED         = "port-closed"
    FILTERED            = "filtered"           # future-ready: firewall drop


@dataclass(frozen=True)
class Packet:
    """One simulated packet moving through the network.

    Every field a future Wireshark lane would want to render is captured
    here. ``payload`` is intentionally left empty for now — real
    payloads land with the pcap lab.
    """

    packet_id:   str
    source:      str
    destination: str
    protocol:    str            # icmp | tcp | udp
    ttl:         int
    port:        Optional[int]  # None for ICMP (ping/traceroute)
    status:      PacketStatus
    path:        tuple[str, ...]      # devices actually traversed
    latency_ms:  float                # round-trip for delivered, one-way for TTL_EXCEEDED
    sequence:    int = 0
    payload:     bytes = b""

    def to_dict(self) -> dict[str, Any]:
        """Serializable snapshot — used by ``/labs/net/packets`` etc."""
        return {
            "id": self.packet_id, "source": self.source,
            "destination": self.destination, "protocol": self.protocol,
            "ttl": self.ttl, "port": self.port,
            "status": self.status.value, "path": list(self.path),
            "latency_ms": round(self.latency_ms, 3), "sequence": self.sequence,
        }


# ===========================================================================
# Ping & Traceroute result shapes.
# ===========================================================================
@dataclass(frozen=True)
class PingReply:
    """One ICMP echo reply / non-reply."""

    sequence: int
    status: PacketStatus
    latency_ms: float
    ttl: int
    packet: Packet


@dataclass(frozen=True)
class TracerouteHop:
    """One row of a traceroute report."""

    hop: int
    hostname: str
    ip: str
    latency_ms: float
    reached: bool                # True when the ICMP TIME_EXCEEDED came back


@dataclass(frozen=True)
class TracerouteResult:
    """The full trace, plus a `reached_destination` flag so simulators
    don't have to inspect hops themselves."""

    destination: str
    hops: tuple[TracerouteHop, ...]
    reached_destination: bool


# ===========================================================================
# Nmap-style port state (future-ready for the Nmap simulator).
# ===========================================================================
class PortState(str, Enum):
    OPEN     = "open"
    CLOSED   = "closed"
    FILTERED = "filtered"       # future firewall lab surface


# ===========================================================================
# Host protocol — duck-typed. Both Device and Host satisfy it today.
# ===========================================================================
class HostLike(Protocol):  # pragma: no cover — structural typing only
    hostname: str
    ip: str
    mac: str
    device_type: str
    os: str
    gateway: str
    open_ports: Iterable[int]


# ===========================================================================
# Subnet math — enough for the labs we ship, not a full ipaddress lib.
# ===========================================================================
def subnet_of(ip: str, prefix: int = 24) -> str:
    """Return the /24 network address for an IPv4 dotted-quad.

    Kept single-purpose: routing decisions in a lab only need to know
    "same LAN or not". A full CIDR helper can land when a lab actually
    needs /28 or /16 arithmetic.
    """
    if not ip or ip.count(".") != 3:
        return ""
    parts = ip.split(".")
    if prefix >= 24:
        return ".".join(parts[:3]) + ".0/24"
    if prefix >= 16:
        return ".".join(parts[:2]) + ".0.0/16"
    if prefix >= 8:
        return parts[0] + ".0.0.0/8"
    return "0.0.0.0/0"


def same_subnet(a: str, b: str, prefix: int = 24) -> bool:
    """True iff two IPs share a /24 (default) or smaller subnet."""
    if not a or not b:
        return False
    return subnet_of(a, prefix) == subnet_of(b, prefix)


# ===========================================================================
# The engine.
# ===========================================================================
class NetworkEngine:
    """Reachability + packet flow over a snapshot of hosts and links.

    Constructed via :func:`make_engine` (topology JSON world) or
    :func:`make_engine_from_devices` (simulator-owned world). Nothing
    inside is mutable — call the factory again to reflect a state
    change (host went offline, port opened).
    """

    def __init__(self, hosts: dict[str, HostLike],
                 adjacency: dict[str, set[str]],
                 offline: set[str] | None = None) -> None:
        self._hosts = dict(hosts)
        self._adjacency = {h: set(v) for h, v in adjacency.items()}
        self._offline = set(offline or ())

    # -------------------- host / status helpers ----------------------
    def hosts(self) -> tuple[HostLike, ...]:
        return tuple(self._hosts.values())

    def host(self, key: str) -> Optional[HostLike]:
        """Resolve a host by hostname, IP, or label (case-insensitive)."""
        if not key:
            return None
        h = self._hosts.get(key)
        if h is not None:
            return h
        for candidate in self._hosts.values():
            if candidate.ip == key:
                return candidate
            label = getattr(candidate, "label", "")
            if label and label.lower() == key.lower():
                return candidate
        return None

    def is_online(self, hostname: str) -> bool:
        """A host is online unless the caller marked it offline; a host
        not in the topology at all is treated as offline (safest default)."""
        if hostname not in self._hosts:
            return False
        return hostname not in self._offline

    def mark_offline(self, hostname: str) -> None:
        """Session-level offline flag. Simulators managing a session
        state envelope should call this on a fresh clone of the engine
        rather than sharing engine instances across sessions."""
        if hostname in self._hosts:
            self._offline.add(hostname)

    # -------------------- reachability -------------------------------
    def neighbours(self, hostname: str) -> tuple[str, ...]:
        return tuple(sorted(self._adjacency.get(hostname, set())))

    def path(self, start: str, end: str) -> Optional[list[str]]:
        """Shortest BFS path via *online* devices only.

        An offline device blocks routing THROUGH it — that's the whole
        point of the offline concept in a simulated network.
        """
        if start not in self._hosts or end not in self._hosts:
            return None
        if start == end:
            return [start]
        if not self.is_online(start) or not self.is_online(end):
            return None
        seen, queue = {start}, [[start]]
        while queue:
            path = queue.pop(0)
            for n in self._adjacency.get(path[-1], ()):
                if n in seen:
                    continue
                if not self.is_online(n) and n != end:
                    continue
                if n == end:
                    return path + [n]
                seen.add(n)
                queue.append(path + [n])
        return None

    def reachable(self, a: str, b: str) -> bool:
        return self.path(a, b) is not None

    # -------------------- packet / ping / traceroute -----------------
    def send_packet(self, source: str, destination: str, *,
                    protocol: str = "icmp", port: Optional[int] = None,
                    ttl: int = DEFAULT_TTL, sequence: int = 0,
                    payload: bytes = b"") -> Packet:
        """Route one packet through the current topology and return the
        immutable :class:`Packet` describing the outcome.

        Ordering of checks is important and mirrors what a real router
        stack would return: offline first, host unreachable next,
        network unreachable if there's simply no route, TTL exceeded if
        the hop count exceeds the TTL, port_closed for tcp/udp with a
        closed port on a reachable host, then DELIVERED.
        """
        src = self.host(source)
        dst = self.host(destination)
        pid = _packet_id(source, destination, protocol, port, sequence)

        # 1. Bad addressing.
        if src is None or dst is None:
            return Packet(pid, source, destination, protocol, ttl, port,
                          PacketStatus.UNREACHABLE_HOST, (), 0.0, sequence, payload)

        # 2. Offline endpoint (source can't send, destination can't ack).
        if not self.is_online(src.hostname) or not self.is_online(dst.hostname):
            return Packet(pid, source, destination, protocol, ttl, port,
                          PacketStatus.OFFLINE, (), 0.0, sequence, payload)

        # 3. No route.
        route = self.path(src.hostname, dst.hostname)
        if route is None:
            # Distinguish "different subnet & no gateway" vs "graph
            # disconnected". The former is the classic Windows/Linux
            # 'Network Unreachable' error and future firewall labs
            # rely on it being emitted separately.
            if not same_subnet(src.ip, dst.ip) and not src.gateway:
                return Packet(pid, source, destination, protocol, ttl, port,
                              PacketStatus.UNREACHABLE_NETWORK, (), 0.0,
                              sequence, payload)
            return Packet(pid, source, destination, protocol, ttl, port,
                          PacketStatus.UNREACHABLE_HOST, (), 0.0, sequence, payload)

        # 4. TTL exceeded (traceroute uses this deliberately with small TTLs).
        hops = len(route) - 1
        if hops > ttl:
            partial = tuple(route[: ttl + 1])
            return Packet(pid, source, destination, protocol, ttl, port,
                          PacketStatus.TTL_EXCEEDED, partial,
                          _leg_latency(source, destination, sequence, hops),
                          sequence, payload)

        # 5. Port closed (tcp/udp with a specific port on a reachable host).
        if protocol in ("tcp", "udp") and port is not None:
            if int(port) not in tuple(dst.open_ports or ()):
                return Packet(pid, source, destination, protocol, ttl, port,
                              PacketStatus.PORT_CLOSED, tuple(route),
                              _leg_latency(source, destination, sequence, hops),
                              sequence, payload)

        # 6. Delivered.
        return Packet(pid, source, destination, protocol, ttl, port,
                      PacketStatus.DELIVERED, tuple(route),
                      _leg_latency(source, destination, sequence, hops),
                      sequence, payload)

    def ping(self, source: str, destination: str, *,
             count: int = 4, ttl: int = DEFAULT_TTL) -> tuple[PingReply, ...]:
        """Simulated ICMP echo. Returns one :class:`PingReply` per
        attempt. Deterministic latency (seeded on flow identity) so
        labs can validate the exact millisecond figure if they need to."""
        replies = []
        for seq in range(1, count + 1):
            pkt = self.send_packet(source, destination,
                                    protocol="icmp", ttl=ttl, sequence=seq)
            replies.append(PingReply(
                sequence=seq, status=pkt.status,
                latency_ms=pkt.latency_ms, ttl=ttl - max(0, len(pkt.path) - 1),
                packet=pkt,
            ))
        return tuple(replies)

    def traceroute(self, source: str, destination: str, *,
                   max_hops: int = 30) -> TracerouteResult:
        """Full trace to ``destination`` using progressively larger TTLs.

        Each row is a real intermediate host (router, switch, endpoint)
        along the BFS path. Matches the shape a real ``traceroute``
        prints — hop number, hostname, IP, one latency figure.
        """
        route = self.path(source, destination)
        if not route:
            return TracerouteResult(destination=destination, hops=(),
                                    reached_destination=False)
        rows = []
        for i, hop_name in enumerate(route[1:], start=1):
            host = self.host(hop_name)
            if host is None:
                continue
            rows.append(TracerouteHop(
                hop=i, hostname=host.hostname, ip=host.ip or "*",
                latency_ms=_leg_latency(source, destination, i, i),
                reached=(hop_name == destination),
            ))
            if i >= max_hops:
                break
        return TracerouteResult(destination=destination, hops=tuple(rows),
                                reached_destination=bool(rows and rows[-1].reached))

    def scan_port(self, source: str, destination: str, port: int, *,
                  protocol: str = "tcp") -> PortState:
        """Nmap-style probe of a single port. The future Nmap simulator
        wraps this in a loop with output formatting; the raw state stays
        the ground truth."""
        pkt = self.send_packet(source, destination,
                                protocol=protocol, port=port, ttl=DEFAULT_TTL)
        if pkt.status == PacketStatus.FILTERED:
            return PortState.FILTERED
        if pkt.status == PacketStatus.DELIVERED:
            return PortState.OPEN
        return PortState.CLOSED

    # -------------------- summaries (UI helpers) ---------------------
    def status_snapshot(self) -> dict[str, dict[str, Any]]:
        """Compact per-host status keyed by hostname. Used by the
        network-map UI (green/red dots) so it doesn't have to poke each
        host individually."""
        return {
            h.hostname: {
                "online": self.is_online(h.hostname),
                "neighbours": list(self.neighbours(h.hostname)),
                "ip": getattr(h, "ip", ""),
                "os": getattr(h, "os", ""),
                "open_ports": list(getattr(h, "open_ports", ()) or ()),
                "services": [
                    {"port": p, "name": service_name_for(int(p))}
                    for p in (getattr(h, "open_ports", ()) or ())
                ],
            }
            for h in self._hosts.values()
        }


# ===========================================================================
# Factories.
# ===========================================================================
def make_engine(topology: Any, offline: Iterable[str] = ()) -> NetworkEngine:
    """Build an engine from a :class:`TopologyEngine`."""
    hosts = {d.hostname: d for d in topology.devices}
    adjacency: dict[str, set[str]] = {h: set() for h in hosts}
    for link in topology.links:
        adjacency[link.a].add(link.b)
        adjacency[link.b].add(link.a)
    return NetworkEngine(hosts, adjacency, offline=set(offline))


def make_engine_from_devices(devices: Iterable[HostLike],
                             links: Iterable[tuple[str, str]],
                             offline: Iterable[str] = ()) -> NetworkEngine:
    """Build an engine from raw host + link iterables (simulator world)."""
    host_dict = {d.hostname: d for d in devices}
    adjacency: dict[str, set[str]] = {h: set() for h in host_dict}
    for a, b in links:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    return NetworkEngine(host_dict, adjacency, offline=set(offline))


# ===========================================================================
# Internals.
# ===========================================================================
def _packet_id(source: str, destination: str,
               protocol: str, port: Optional[int], sequence: int) -> str:
    """Short stable ID for a flow — safe to use as an XML attr / URL fragment."""
    key = f"{source}|{destination}|{protocol}|{port}|{sequence}".encode()
    return hashlib.sha1(key).hexdigest()[:12]


def _leg_latency(source: str, destination: str, sequence: int, hops: int) -> float:
    """Deterministic-but-realistic latency in milliseconds.

    Keeps the ping/traceroute output stable across runs (so a lab
    objective can match on `time=1.42`) but varies enough between
    flows and sequences to look natural. Baseline is 0.6ms per hop
    plus a per-flow jitter of ±0.6ms and per-sequence 0.02ms.
    """
    key = f"{source}|{destination}|{sequence}".encode()
    digest = hashlib.sha1(key).digest()
    jitter = ((digest[0] / 255.0) * 1.2) - 0.6      # -0.6..+0.6
    return round(max(0.05, 0.6 * hops + 0.8 + jitter + 0.02 * sequence), 3)
