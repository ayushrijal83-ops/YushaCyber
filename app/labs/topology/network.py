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

import threading
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
# PacketFlow — a first-class group of related packets
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PacketFlow:
    """An ordered, immutable group of :class:`Packet` objects that belong
    to one logical conversation (a ping run, one port probe burst, an
    HTTP exchange).

    Why a first-class object instead of ``list[Packet]``: the future
    Wireshark lab filters, colours and follows *flows*, and the SIEM
    dashboard counts *flows* — giving the grouping a stable identity and
    a canonical dict shape now means those labs consume this directly.
    """

    flow_id: str                    # deterministic, e.g. "icmp:pc-1>web-server"
    protocol: str                   # icmp | tcp | udp
    source: str                     # source hostname
    destination: str                # destination hostname
    packets: tuple[Packet, ...] = ()

    # ---- Construction -------------------------------------------------
    @staticmethod
    def make_id(protocol: str, source: str, destination: str,
                discriminator: int | str = 0) -> str:
        """Deterministic flow id — same inputs, same id, every process."""
        return f"{protocol}:{source}>{destination}#{discriminator}"

    @classmethod
    def from_packets(cls, packets: Iterable[Packet],
                     discriminator: int | str = 0) -> "PacketFlow":
        """Build a flow from an iterable of packets (must be non-empty
        and share protocol/endpoints — enforced, because a 'flow' with
        mixed endpoints is a bug upstream, not a valid flow)."""
        pkts = tuple(packets)
        if not pkts:
            raise ValueError("PacketFlow.from_packets: no packets given")
        first = pkts[0]
        for p in pkts[1:]:
            if (p.protocol, p.source, p.destination) != (
                    first.protocol, first.source, first.destination):
                raise ValueError(
                    "PacketFlow.from_packets: packets mix protocols or endpoints")
        return cls(
            flow_id=cls.make_id(first.protocol, first.source,
                                first.destination, discriminator),
            protocol=first.protocol,
            source=first.source,
            destination=first.destination,
            packets=pkts,
        )

    @classmethod
    def from_ping(cls, result: "PingResult",
                  discriminator: int | str = 0) -> Optional["PacketFlow"]:
        """Wrap a :class:`PingResult`'s packets as one ICMP flow, or
        ``None`` when the result produced no packets at all (unknown
        host — nothing ever hit the wire)."""
        if not result.packets:
            return None
        return cls.from_packets(result.packets, discriminator=discriminator)

    # ---- Derived stats ------------------------------------------------
    @property
    def packet_count(self) -> int:
        return len(self.packets)

    @property
    def delivered(self) -> int:
        return sum(1 for p in self.packets if p.status == "reply")

    @property
    def loss_pct(self) -> int:
        if not self.packets:
            return 0
        return round(100 * (1 - self.delivered / len(self.packets)))

    @property
    def ok(self) -> bool:
        return self.packet_count > 0 and self.delivered == self.packet_count

    @property
    def total_ms(self) -> float:
        return round(sum(p.latency_ms for p in self.packets), 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "flow_id": self.flow_id,
            "protocol": self.protocol,
            "source": self.source,
            "destination": self.destination,
            "packet_count": self.packet_count,
            "delivered": self.delivered,
            "loss_pct": self.loss_pct,
            "ok": self.ok,
            "total_ms": self.total_ms,
            "packets": [p.to_dict() for p in self.packets],
        }


# ---------------------------------------------------------------------------
# Subnet / SubnetIndex — real CIDR arithmetic
# ---------------------------------------------------------------------------
# Pure integer math, zero external deps, fully deterministic. Replaces
# the /24-only assumption baked into ``Device.subnet``: every helper
# here honours the device's actual ``subnet_mask``.
@dataclass(frozen=True)
class Subnet:
    """One IPv4 subnet in canonical form.

    ``network`` is always the *network address* (host bits zeroed), so
    ``Subnet.from_ip_and_mask("192.168.1.37", "255.255.255.0")`` and
    ``Subnet.from_cidr("192.168.1.0/24")`` compare equal — which is
    exactly what "same broadcast domain?" checks need.
    """

    network: str        # dotted network address, e.g. "192.168.1.0"
    prefix: int         # 0..32

    def __post_init__(self) -> None:
        if not 0 <= self.prefix <= 32:
            raise ValueError(f"invalid prefix /{self.prefix}")
        as_int = self.ip_to_int(self.network)     # validates format
        if as_int & self.host_mask(self.prefix):
            raise ValueError(
                f"{self.network}/{self.prefix} has host bits set — "
                f"use from_cidr()/from_ip_and_mask() to normalise")

    # ---- Integer plumbing ---------------------------------------------
    @staticmethod
    def ip_to_int(ip: str) -> int:
        parts = ip.split(".")
        if len(parts) != 4:
            raise ValueError(f"malformed IPv4 address: {ip!r}")
        value = 0
        for part in parts:
            if not part.isdigit() or not 0 <= int(part) <= 255:
                raise ValueError(f"malformed IPv4 address: {ip!r}")
            value = (value << 8) | int(part)
        return value

    @staticmethod
    def int_to_ip(value: int) -> str:
        return ".".join(str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0))

    @staticmethod
    def net_mask(prefix: int) -> int:
        return 0 if prefix == 0 else (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF

    @staticmethod
    def host_mask(prefix: int) -> int:
        return 0xFFFFFFFF ^ Subnet.net_mask(prefix)

    @staticmethod
    def mask_to_prefix(mask: str) -> int:
        """``255.255.255.0`` → 24. Rejects non-contiguous masks like
        255.0.255.0 — those are config errors, not subnets."""
        value = Subnet.ip_to_int(mask)
        prefix = bin(value).count("1")
        if value != Subnet.net_mask(prefix):
            raise ValueError(f"non-contiguous subnet mask: {mask}")
        return prefix

    @staticmethod
    def prefix_to_mask(prefix: int) -> str:
        return Subnet.int_to_ip(Subnet.net_mask(prefix))

    # ---- Constructors --------------------------------------------------
    @classmethod
    def from_cidr(cls, cidr: str) -> "Subnet":
        """``"192.168.1.37/24"`` → the ``192.168.1.0/24`` subnet."""
        try:
            ip, prefix_str = cidr.split("/")
            prefix = int(prefix_str)
        except ValueError as exc:
            raise ValueError(f"malformed CIDR: {cidr!r}") from exc
        network = cls.ip_to_int(ip) & cls.net_mask(prefix)
        return cls(network=cls.int_to_ip(network), prefix=prefix)

    @classmethod
    def from_ip_and_mask(cls, ip: str, mask: str) -> "Subnet":
        """The subnet a device with ``ip``/``mask`` lives in."""
        prefix = cls.mask_to_prefix(mask)
        network = cls.ip_to_int(ip) & cls.net_mask(prefix)
        return cls(network=cls.int_to_ip(network), prefix=prefix)

    # ---- Derived values -------------------------------------------------
    @property
    def cidr(self) -> str:
        return f"{self.network}/{self.prefix}"

    @property
    def netmask(self) -> str:
        return self.prefix_to_mask(self.prefix)

    @property
    def broadcast(self) -> str:
        return self.int_to_ip(self.ip_to_int(self.network) | self.host_mask(self.prefix))

    @property
    def size(self) -> int:
        """Total addresses including network + broadcast."""
        return 1 << (32 - self.prefix)

    @property
    def usable_hosts(self) -> int:
        """Assignable addresses (network/broadcast excluded; /31 and /32
        follow the conventional 0 for classic subnetting lessons)."""
        return max(0, self.size - 2)

    @property
    def first_host(self) -> str:
        if self.usable_hosts == 0:
            return self.network
        return self.int_to_ip(self.ip_to_int(self.network) + 1)

    @property
    def last_host(self) -> str:
        if self.usable_hosts == 0:
            return self.broadcast
        return self.int_to_ip(self.ip_to_int(self.broadcast) - 1)

    # ---- Queries --------------------------------------------------------
    def contains(self, ip: str) -> bool:
        try:
            return (self.ip_to_int(ip) & self.net_mask(self.prefix)) \
                == self.ip_to_int(self.network)
        except ValueError:
            return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "cidr": self.cidr,
            "network": self.network,
            "prefix": self.prefix,
            "netmask": self.netmask,
            "broadcast": self.broadcast,
            "first_host": self.first_host,
            "last_host": self.last_host,
            "usable_hosts": self.usable_hosts,
        }


class SubnetIndex:
    """All subnets of a topology, indexed once at construction.

    Answers the questions every networking lab keeps asking — "which
    subnet is this host in?", "who shares its broadcast domain?" — in
    O(1)/O(subnets) instead of re-deriving CIDR math per request.
    Devices without an IP (switches) simply don't appear.
    """

    def __init__(self, topology: TopologyEngine) -> None:
        self._topology = topology
        self._by_subnet: dict[Subnet, list[Device]] = {}
        self._device_subnet: dict[str, Subnet] = {}
        for dev in topology.devices:
            if not dev.ip:
                continue
            try:
                subnet = Subnet.from_ip_and_mask(
                    dev.ip, dev.subnet_mask or "255.255.255.0")
            except ValueError:
                continue    # malformed IP/mask in JSON — skip, don't crash
            self._by_subnet.setdefault(subnet, []).append(dev)
            self._device_subnet[dev.hostname] = subnet

    @property
    def subnets(self) -> tuple[Subnet, ...]:
        return tuple(sorted(self._by_subnet,
                            key=lambda s: (Subnet.ip_to_int(s.network), s.prefix)))

    def subnet_of(self, key: str) -> Optional[Subnet]:
        """Subnet for a hostname, label or IP — or ``None``."""
        dev = self._topology.find_device(key)
        if dev is not None:
            return self._device_subnet.get(dev.hostname)
        # Raw IP that isn't a device — match against known subnets.
        for subnet in self._by_subnet:
            if subnet.contains(key):
                return subnet
        return None

    def devices_in(self, cidr: str) -> tuple[Device, ...]:
        subnet = Subnet.from_cidr(cidr)
        return tuple(sorted(self._by_subnet.get(subnet, ()),
                            key=lambda d: Subnet.ip_to_int(d.ip)))

    def share_subnet(self, a: str, b: str) -> bool:
        sa, sb = self.subnet_of(a), self.subnet_of(b)
        return sa is not None and sa == sb

    def to_dict(self) -> dict[str, Any]:
        return {
            "subnets": [
                {**subnet.to_dict(),
                 "devices": [d.hostname for d in self.devices_in(subnet.cidr)]}
                for subnet in self.subnets
            ],
        }


# ---------------------------------------------------------------------------
# DeviceRuntime — mutable online/offline overlay
# ---------------------------------------------------------------------------
class DeviceRuntime:
    """Thread-safe runtime state layered *over* an immutable topology.

    Topologies are frozen and cached process-wide, so a lab that wants
    to "take db-server down" must not mutate them. Instead it holds a
    DeviceRuntime (one per lab session, stored in the session state
    envelope like every other simulator state) and passes it into
    :func:`ping` / :func:`traceroute` / :func:`probe_port` — those
    consult the overlay first and fall back to the device's static
    ``online`` flag.
    """

    def __init__(self, topology: TopologyEngine) -> None:
        self._topology = topology
        self._lock = threading.Lock()
        self._overrides: dict[str, bool] = {}

    # ---- Mutation ------------------------------------------------------
    def set_online(self, hostname: str, online: bool = True) -> bool:
        """Override a device's state. Returns False for unknown hosts
        (no exception — labs surface that as terminal output)."""
        dev = self._topology.find_device(hostname)
        if dev is None:
            return False
        with self._lock:
            self._overrides[dev.hostname] = bool(online)
        return True

    def set_offline(self, hostname: str) -> bool:
        return self.set_online(hostname, online=False)

    def toggle(self, hostname: str) -> Optional[bool]:
        """Flip a device's state; returns the new state, or ``None``
        for unknown hosts."""
        dev = self._topology.find_device(hostname)
        if dev is None:
            return None
        with self._lock:
            new_state = not self._overrides.get(dev.hostname, dev.online)
            self._overrides[dev.hostname] = new_state
        return new_state

    def reset(self, hostname: Optional[str] = None) -> None:
        """Drop one override, or all of them (back to topology defaults)."""
        with self._lock:
            if hostname is None:
                self._overrides.clear()
            else:
                dev = self._topology.find_device(hostname)
                if dev is not None:
                    self._overrides.pop(dev.hostname, None)

    # ---- Queries -------------------------------------------------------
    def is_online(self, device: "Device | str") -> bool:
        dev = device if isinstance(device, Device) \
            else self._topology.find_device(device)
        if dev is None:
            return False
        with self._lock:
            return self._overrides.get(dev.hostname, dev.online)

    def snapshot(self) -> dict[str, bool]:
        """Effective online state of every device — JSON/session ready."""
        with self._lock:
            return {
                dev.hostname: self._overrides.get(dev.hostname, dev.online)
                for dev in self._topology.devices
            }

    def load_snapshot(self, snapshot: dict[str, bool]) -> None:
        """Restore overrides saved by :meth:`snapshot` (session revival)."""
        with self._lock:
            self._overrides = {
                str(host): bool(state) for host, state in snapshot.items()
                if self._topology.device(str(host)) is not None
            }


def _effective_online(device: Optional[Device],
                      runtime: Optional[DeviceRuntime]) -> bool:
    """One rule for every engine: runtime override wins, static flag is
    the fallback, unknown devices are down."""
    if device is None:
        return False
    if runtime is not None:
        return runtime.is_online(device)
    return device.online


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


def route_to(topology: TopologyEngine, source: str, destination: str,
             runtime: Optional[DeviceRuntime] = None) -> Route:
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
    if not _effective_online(src, runtime):
        return Route(ok=False, hops=(), reason="source offline")
    if not _effective_online(dst, runtime):
        return Route(ok=False, hops=(), reason="destination offline")

    hops = topology.path(src.hostname, dst.hostname)
    if hops is None:
        return Route(ok=False, hops=(), reason="host unreachable")
    return Route(ok=True, hops=tuple(hops))


def same_subnet(topology: TopologyEngine, a: str, b: str) -> bool:
    """True when both devices share a broadcast domain — computed with
    real CIDR arithmetic from each device's actual ``subnet_mask``
    (YC-026.3 replaces the earlier /24-only shortcut)."""
    da = topology.find_device(a)
    db = topology.find_device(b)
    if da is None or db is None or not da.ip or not db.ip:
        return False
    try:
        sa = Subnet.from_ip_and_mask(da.ip, da.subnet_mask or "255.255.255.0")
        sb = Subnet.from_ip_and_mask(db.ip, db.subnet_mask or "255.255.255.0")
    except ValueError:
        return False
    return sa == sb


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
         count: int = 4,
         runtime: Optional[DeviceRuntime] = None) -> PingResult:
    """Simulate ``count`` ICMP echoes from ``source`` to ``destination``.

    Failure modes are packet-shaped, not exceptions, so the terminal
    can render them uniformly:

      · destination offline  → ``packets=[]`` and ``reason="destination offline"``
      · unreachable in graph → ``packets`` of ``status="unreachable"``
      · normal reply         → ``packets`` of ``status="reply"``
    """
    route = route_to(topology, source, destination, runtime=runtime)
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


def traceroute(topology: TopologyEngine, source: str, destination: str,
               runtime: Optional[DeviceRuntime] = None) -> TracerouteResult:
    """Return the hop path from ``source`` to ``destination``.

    Each hop dict carries the fields a real traceroute prints:
    ``hop`` (1-based), ``hostname``, ``ip``, ``device_type``,
    ``rtt_ms``. Unreachable / offline destinations produce an ``ok=False``
    result with the ``reason`` filled in.
    """
    route = route_to(topology, source, destination, runtime=runtime)
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
               port: int,
               runtime: Optional[DeviceRuntime] = None) -> PortResult:
    """Simulate a single TCP connect probe.

    Rules (Nmap-ish):

      · Route fails                 → state="filtered"  (nothing gets there)
      · Destination offline         → state="filtered"
      · Port is in ``open_ports``   → state="open"
      · Otherwise                   → state="closed"    (host is up, port isn't)
    """
    route = route_to(topology, source, destination, runtime=runtime)
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
               ports: Iterable[int],
               runtime: Optional[DeviceRuntime] = None) -> list[PortResult]:
    """Probe a batch of ports and return them ordered ascending."""
    return sorted(
        (probe_port(topology, source, destination, p, runtime=runtime)
         for p in ports),
        key=lambda r: r.port)


# ---------------------------------------------------------------------------
# Whole-network status snapshot (for UIs and dashboards)
# ---------------------------------------------------------------------------
def network_status(topology: TopologyEngine,
                   runtime: Optional[DeviceRuntime] = None) -> dict[str, Any]:
    """A JSON-ready summary of every device's status. The Interactive
    Network map layer, a future SIEM dashboard and admin tools all
    consume the same shape."""
    devices = []
    online_count = 0
    for dev in topology.devices:
        online = _effective_online(dev, runtime)
        if online:
            online_count += 1
        devices.append({
            "hostname": dev.hostname,
            "label": dev.label,
            "device_type": dev.device_type,
            "ip": dev.ip,
            "online": online,
            "status": "Online" if online else "Offline",
        })
    return {
        "total": len(devices),
        "online": online_count,
        "offline": len(devices) - online_count,
        "devices": devices,
    }
