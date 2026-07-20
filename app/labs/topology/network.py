"""Virtual Network Services & Connectivity Engine (YC-026.3).

The reusable networking backbone. Every future simulator -- Ping,
Traceroute, Nmap, Wireshark, Firewall, Active Directory, SOC -- lives
on top of this module so the *behaviour* of the virtual network is
defined once, cleanly separated from any particular UI or simulator.

Design principles:

  · **Pure functions of the topology.** Nothing here talks to a socket,
    subprocess or filesystem. The single input to every helper is a
    :class:`~app.labs.topology.engine.TopologyEngine`; every output is
    either a plain dataclass or a plain dict.

  · **One canonical Packet.** Ping, traceroute and (future) Wireshark
    all emit the same :class:`Packet` shape. Once Wireshark lands it
    just consumes the same objects -- no duplicated packet model.

  · **Deterministic.** Latency, TTL, MAC learning and so on are derived
    from stable inputs (link count, endpoint identity) so lab tests can
    assert exact values.

  · **Composable.** :func:`ping` builds a plan out of :func:`route_to`
    which itself uses :meth:`TopologyEngine.path`. Adding a new
    behaviour (e.g. mtr) is a wrapper, not a rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from app.labs.topology.engine import Device, TopologyEngine


# ---------------------------------------------------------------------------
# Service catalogue
# ---------------------------------------------------------------------------
# The mandated "well-known ports" set. The service NAME lives here so
# every simulator (nmap output, netstat, wireshark protocol column)
# uses the same string. Devices can still override the name in their
# JSON ``services`` map -- this catalogue is the fallback + reverse
# lookup, not the source of truth.
SERVICES: dict[int, dict[str, str]] = {
    21:   {"name": "ftp",    "protocol": "tcp", "description": "File Transfer Protocol"},
    22:   {"name": "ssh",    "protocol": "tcp", "description": "Secure Shell"},
    23:   {"name": "telnet", "protocol": "tcp", "description": "Telnet (unencrypted)"},
    25:   {"name": "smtp",   "protocol": "tcp", "description": "Simple Mail Transfer Protocol"},
    53:   {"name": "dns",    "protocol": "udp", "description": "Domain Name System"},
    80:   {"name": "http",   "protocol": "tcp", "description": "HyperText Transfer Protocol"},
    110:  {"name": "pop3",   "protocol": "tcp", "description": "Post Office Protocol v3"},
    143:  {"name": "imap",   "protocol": "tcp", "description": "Internet Message Access Protocol"},
    443:  {"name": "https",  "protocol": "tcp", "description": "HTTP over TLS"},
    445:  {"name": "smb",    "protocol": "tcp", "description": "SMB / CIFS"},
    3306: {"name": "mysql",  "protocol": "tcp", "description": "MySQL"},
    3389: {"name": "rdp",    "protocol": "tcp", "description": "Remote Desktop Protocol"},
    5432: {"name": "postgres","protocol":"tcp", "description": "PostgreSQL"},
    6379: {"name": "redis",  "protocol": "tcp", "description": "Redis"},
}


def service_name(port: int) -> str:
    """Return the well-known service name for ``port``, or ``"unknown"``."""
    return SERVICES.get(port, {}).get("name", "unknown")


# ---------------------------------------------------------------------------
# Packet — the canonical unit every simulator emits and consumes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Packet:
    """One simulated packet.

    Deliberately protocol-agnostic: the same shape carries ICMP echoes,
    TCP SYNs from an Nmap scan, or an application-layer HTTP request.
    Wireshark labs later consume :class:`Packet` streams directly.
    """

    seq: int              # per-flow sequence number (0-based)
    source: str           # source hostname
    destination: str      # destination hostname
    src_ip: str = ""
    dst_ip: str = ""
    protocol: str = "icmp"   # icmp | tcp | udp
    src_port: int = 0
    dst_port: int = 0
    ttl: int = 64
    latency_ms: float = 0.0
    status: str = "reply"   # reply | timeout | unreachable | rejected | filtered
    payload: str = ""
    hops: tuple[str, ...] = ()   # hostnames traversed, ordered src -> dst

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "source": self.source,
            "destination": self.destination,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "protocol": self.protocol,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "ttl": self.ttl,
            "latency_ms": round(self.latency_ms, 2),
            "status": self.status,
            "payload": self.payload,
            "hops": list(self.hops),
        }


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Route:
    """The plan for a single flow from source to destination.

    :attr:`hops` is the list of intermediate device hostnames including
    both endpoints. :attr:`ok` is False iff the source and destination
    are disconnected OR the destination is offline OR the source is
    offline. :attr:`reason` gives a human string; simulators can
    translate that into whatever wording their terminal wants.
    """

    ok: bool
    hops: tuple[str, ...]
    reason: str = ""

    @property
    def hop_count(self) -> int:
        return max(0, len(self.hops) - 1)


def route_to(topology: TopologyEngine, source: str, destination: str) -> Route:
    """Compute the route source → destination.

    Rules (kept intentionally simple for the current lab set; add
    metrics/ECMP/policy routing when a future lab actually needs them):

      · Source or destination unknown          → ``ok=False``, reason="no such host"
      · Source is offline                       → ``ok=False``, reason="source offline"
      · Destination is offline                  → ``ok=False``, reason="destination offline"
      · No path through the topology graph      → ``ok=False``, reason="host unreachable"
      · Otherwise                               → ``ok=True``, hops = BFS shortest path
    """
    src = topology.find_device(source)
    dst = topology.find_device(destination)
    if src is None or dst is None:
        return Route(ok=False, hops=(), reason="no such host")
    if not src.online:
        return Route(ok=False, hops=(), reason="source offline")
    if not dst.online:
        return Route(ok=False, hops=(), reason="destination offline")

    hops = topology.path(src.hostname, dst.hostname)
    if hops is None:
        return Route(ok=False, hops=(), reason="host unreachable")
    return Route(ok=True, hops=tuple(hops))


def same_subnet(topology: TopologyEngine, a: str, b: str) -> bool:
    """True when both devices are in the same /24 subnet."""
    da = topology.find_device(a)
    db = topology.find_device(b)
    if da is None or db is None or not da.ip or not db.ip:
        return False
    return da.subnet == db.subnet


# ---------------------------------------------------------------------------
# Latency model
# ---------------------------------------------------------------------------
# Deterministic and stable across process boundaries -- crucial so lab
# assertions can be "the reply is 1.4ms" rather than "the reply is
# somewhere in a plausible range."
_HOP_BASE_MS = 0.6      # min inter-hop cost
_HOP_JITTER_MS = 0.25   # tiny per-hop increment so 3 hops > 2 hops


def _latency_for(hops: Iterable[str], seq: int) -> float:
    """Latency for one packet on one route.

    Sum of a fixed per-hop cost + jitter that depends on the packet's
    sequence number, so ping runs show a small realistic wobble (1.42,
    1.51, 1.48) instead of every reply being identical. Zero external
    randomness -- pass the same (hops, seq) twice and get the same
    number twice.
    """
    hop_count = max(0, len(list(hops)) - 1)
    if hop_count == 0:
        return 0.05  # loopback-ish
    stride = hop_count * (_HOP_BASE_MS + _HOP_JITTER_MS * ((seq * 7 + 3) % 5) / 5)
    return round(stride + 0.9, 2)


# ---------------------------------------------------------------------------
# Ping engine
# ---------------------------------------------------------------------------
@dataclass
class PingResult:
    """The outcome of :func:`ping`.

    ``packets`` is the ordered list of :class:`Packet` objects emitted
    (one per echo request). ``sent/received/loss_pct`` are the stats a
    real ping's tail line would print.
    """

    ok: bool
    packets: list[Packet] = field(default_factory=list)
    reason: str = ""
    sent: int = 0
    received: int = 0
    loss_pct: int = 0
    min_ms: float = 0.0
    avg_ms: float = 0.0
    max_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "sent": self.sent,
            "received": self.received,
            "loss_pct": self.loss_pct,
            "min_ms": round(self.min_ms, 2),
            "avg_ms": round(self.avg_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "packets": [p.to_dict() for p in self.packets],
        }


def ping(topology: TopologyEngine, source: str, destination: str,
         count: int = 4) -> PingResult:
    """Simulate ``count`` ICMP echoes from ``source`` to ``destination``.

    Failure modes are packet-shaped, not exceptions, so the terminal
    can render them uniformly:

      · destination offline  → ``packets=[]`` and ``reason="destination offline"``
      · unreachable in graph → ``packets`` of ``status="unreachable"``
      · normal reply         → ``packets`` of ``status="reply"``
    """
    route = route_to(topology, source, destination)
    src = topology.find_device(source)
    dst = topology.find_device(destination)

    result = PingResult(ok=route.ok, reason=route.reason, sent=count)

    if src is None or dst is None:
        return result

    # No path — still emit one "unreachable" packet so downstream
    # consumers (event validators, Wireshark viewer) see the attempt.
    if not route.ok:
        result.packets.append(Packet(
            seq=0,
            source=src.hostname, destination=dst.hostname,
            src_ip=src.ip, dst_ip=dst.ip,
            protocol="icmp",
            ttl=src_ttl_for(src),
            latency_ms=0.0,
            status="unreachable" if route.reason != "destination offline" else "timeout",
            hops=(src.hostname,),
        ))
        result.received = 0
        result.loss_pct = 100
        return result

    latencies = []
    for seq in range(count):
        latency = _latency_for(route.hops, seq)
        latencies.append(latency)
        result.packets.append(Packet(
            seq=seq,
            source=src.hostname, destination=dst.hostname,
            src_ip=src.ip, dst_ip=dst.ip,
            protocol="icmp",
            ttl=src_ttl_for(src) - route.hop_count,
            latency_ms=latency,
            status="reply",
            hops=route.hops,
        ))
    result.received = count
    result.loss_pct = 0
    result.min_ms = min(latencies)
    result.max_ms = max(latencies)
    result.avg_ms = sum(latencies) / len(latencies)
    return result


def src_ttl_for(device: Device) -> int:
    """Initial TTL a source stack sets. Linux/router = 64, Windows = 128 —
    matches what a real tcpdump would show and lets fingerprinting labs
    tell the two apart. Everything else falls back to 64."""
    os = (device.os or "").lower()
    if "windows" in os:
        return 128
    return 64


# ---------------------------------------------------------------------------
# Traceroute engine
# ---------------------------------------------------------------------------
@dataclass
class TracerouteResult:
    ok: bool
    hops: list[dict[str, Any]] = field(default_factory=list)  # per-hop dicts
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "reason": self.reason, "hops": self.hops}


def traceroute(topology: TopologyEngine, source: str,
               destination: str) -> TracerouteResult:
    """Return the hop path from ``source`` to ``destination``.

    Each hop dict carries the fields a real traceroute prints:
    ``hop`` (1-based), ``hostname``, ``ip``, ``device_type``,
    ``rtt_ms``. Unreachable / offline destinations produce an ``ok=False``
    result with the ``reason`` filled in.
    """
    route = route_to(topology, source, destination)
    if not route.ok:
        return TracerouteResult(ok=False, reason=route.reason)

    hops: list[dict[str, Any]] = []
    for i, hostname in enumerate(route.hops[1:], start=1):
        dev = topology.device(hostname)
        if dev is None:
            continue
        # Per-hop RTT grows roughly linearly — deterministic, small.
        rtt = round(0.7 * i + 0.5, 2)
        hops.append({
            "hop": i,
            "hostname": dev.hostname,
            "label": dev.label,
            "ip": dev.ip,
            "device_type": dev.device_type,
            "rtt_ms": rtt,
        })
    return TracerouteResult(ok=True, hops=hops)


# ---------------------------------------------------------------------------
# Port / service probes — the Nmap surface
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PortResult:
    port: int
    state: str        # open | closed | filtered
    service: str

    def to_dict(self) -> dict[str, Any]:
        return {"port": self.port, "state": self.state, "service": self.service}


def probe_port(topology: TopologyEngine, source: str, destination: str,
               port: int) -> PortResult:
    """Simulate a single TCP connect probe.

    Rules (Nmap-ish):

      · Route fails                 → state="filtered"  (nothing gets there)
      · Destination offline         → state="filtered"
      · Port is in ``open_ports``   → state="open"
      · Otherwise                   → state="closed"    (host is up, port isn't)
    """
    route = route_to(topology, source, destination)
    if not route.ok:
        return PortResult(port=port, state="filtered", service=service_name(port))
    dst = topology.find_device(destination)
    if dst is None:
        return PortResult(port=port, state="filtered", service=service_name(port))
    if port in dst.open_ports:
        # Prefer the device's own service label if it provides one --
        # e.g. "http-admin" on a router beats the generic "http".
        name = dst.services.get(port) or service_name(port)
        return PortResult(port=port, state="open", service=name)
    return PortResult(port=port, state="closed", service=service_name(port))


def scan_ports(topology: TopologyEngine, source: str, destination: str,
               ports: Iterable[int]) -> list[PortResult]:
    """Probe a batch of ports and return them ordered ascending."""
    return sorted((probe_port(topology, source, destination, p) for p in ports),
                  key=lambda r: r.port)


# ---------------------------------------------------------------------------
# Whole-network status snapshot (for UIs and dashboards)
# ---------------------------------------------------------------------------
def network_status(topology: TopologyEngine) -> dict[str, Any]:
    """A JSON-ready summary of every device's status. The Interactive
    Network map layer, a future SIEM dashboard and admin tools all
    consume the same shape."""
    devices = []
    online_count = 0
    for dev in topology.devices:
        if dev.online:
            online_count += 1
        devices.append({
            "hostname": dev.hostname,
            "label": dev.label,
            "device_type": dev.device_type,
            "ip": dev.ip,
            "online": dev.online,
            "status": "Online" if dev.online else "Offline",
        })
    return {
        "total": len(devices),
        "online": online_count,
        "offline": len(devices) - online_count,
        "devices": devices,
    }
