"""Simulated network — YC-034.5 Networking Fundamentals + future networking missions.

A small, deterministic educational LAN model. Like VirtualFS, this never
touches a real socket, DNS resolver, ARP table, or the host's network
stack — `ping`/`nslookup`/`ss`/etc. are pure string-formatting functions
over an in-memory topology built from a mission's declarative
``"network"`` config dict (see mission_loader.py). Future networking
missions (Nmap Fundamentals, Network Troubleshooting, Recon) reuse this
same module by supplying their own config — hosts are never hardcoded
into objectives or command handlers.

YC-034.6 (Network Troubleshooting) adds the mutation side: a handful of
simulated "fix" commands (`ip link set`, `ip addr add`, `ip route add`)
change interface/route state on the student's own host so a broken
topology can be diagnosed and repaired within one session. Everything
mutated stays inside this in-memory object graph — never the real OS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NetworkInterface:
    name: str
    ip: str
    cidr: int
    state: str = "UP"


@dataclass
class Route:
    destination: str
    via: str | None = None
    dev: str = "eth0"
    is_default: bool = False


@dataclass
class Service:
    port: int
    proto: str
    name: str
    state: str = "LISTEN"


@dataclass
class DNSRecord:
    hostname: str
    ip: str


@dataclass
class VirtualHost:
    hostname: str
    ip: str
    interfaces: list[NetworkInterface] = field(default_factory=list)
    routes: list[Route] = field(default_factory=list)
    services: list[Service] = field(default_factory=list)
    reachable: bool = True


class VirtualNetwork:
    """A small, deterministic educational LAN — read-only by default,
    mutable via the simulated "fix" commands (YC-034.6)."""

    def __init__(self, student_ip: str, hosts: dict[str, VirtualHost],
                 dns_records: list[DNSRecord], dns_server_ip: str | None = None,
                 dns_working: bool = True) -> None:
        self.student_ip = student_ip
        self.hosts = hosts
        self.dns_records = dns_records
        self.dns_server_ip = dns_server_ip
        # False simulates a DNS server outage independent of connectivity —
        # lets a mission teach "ping by IP works, but DNS still fails".
        self.dns_working = dns_working

    @property
    def student(self) -> VirtualHost:
        return self.hosts[self.student_ip]

    def _student_iface_up(self) -> bool:
        return any(i.state == "UP" for i in self.student.interfaces if i.name != "lo")

    def ping(self, target: str) -> tuple[bool, str]:
        """Returns (reachable, formatted ping output) — never a real ICMP call."""
        if not self._student_iface_up():
            return False, "connect: Network is unreachable"
        host = self.hosts.get(target)
        if host is None or not host.reachable:
            return False, (
                f"PING {target} ({target}) 56(84) bytes of data.\n"
                f"Request timeout for icmp_seq 1\n\n"
                f"--- {target} ping statistics ---\n"
                f"1 packets transmitted, 0 received, 100% packet loss"
            )
        latency = 1 if target == self.student_ip else 2
        return True, (
            f"PING {target} ({target}) 56(84) bytes of data.\n"
            f"64 bytes from {target}: icmp_seq=1 ttl=64 time={latency} ms\n\n"
            f"--- {target} ping statistics ---\n"
            f"1 packets transmitted, 1 received, 0% packet loss"
        )

    def resolve(self, hostname: str) -> str | None:
        if not self.dns_working:
            return None
        for rec in self.dns_records:
            if rec.hostname == hostname:
                return rec.ip
        return None

    # ── Simulated fixes (YC-034.6) — mutate only this in-memory object ──
    def set_interface_state(self, name: str, state: str) -> bool:
        for iface in self.student.interfaces:
            if iface.name == name:
                iface.state = state.upper()
                return True
        return False

    def set_interface_address(self, name: str, ip: str, cidr: int) -> bool:
        for iface in self.student.interfaces:
            if iface.name == name:
                iface.ip = ip
                iface.cidr = cidr
                return True
        return False

    def set_default_gateway(self, via: str, dev: str = "eth0") -> None:
        for r in self.student.routes:
            if r.is_default:
                r.via = via
                r.dev = dev
                return
        self.student.routes.append(Route(destination="default", via=via,
                                          dev=dev, is_default=True))

    # ── Persistence — mutable state only; static topology is always
    # rebuilt fresh from the mission's declarative config (see
    # MissionRunner._attach_network). ──
    def to_dict(self) -> dict[str, Any]:
        return {
            ip: {
                "interfaces": [{"name": i.name, "ip": i.ip, "cidr": i.cidr,
                                "state": i.state} for i in host.interfaces],
                "routes": [{"destination": r.destination, "via": r.via, "dev": r.dev,
                           "is_default": r.is_default} for r in host.routes],
                "services": [{"port": s.port, "proto": s.proto, "name": s.name,
                             "state": s.state} for s in host.services],
            }
            for ip, host in self.hosts.items()
        }

    def apply_state(self, snapshot: dict[str, Any]) -> None:
        """Overlay a previously-saved mutable-state snapshot onto this network."""
        for ip, hstate in snapshot.items():
            host = self.hosts.get(ip)
            if host is None:
                continue
            host.interfaces = [NetworkInterface(**i) for i in hstate.get("interfaces", [])]
            host.routes = [Route(**r) for r in hstate.get("routes", [])]
            host.services = [Service(**s) for s in hstate.get("services", [])]

    def is_port_open(self, ip: str, port: int) -> bool:
        host = self.hosts.get(ip)
        return bool(host) and any(s.port == port for s in host.services)

    def default_gateway(self) -> str | None:
        for r in self.student.routes:
            if r.is_default:
                return r.via
        return None

    def interfaces_text(self) -> str:
        lines: list[str] = []
        for iface in self.student.interfaces:
            lines.append(f"{iface.name}:")
            lines.append(f"    inet {iface.ip}/{iface.cidr}")
            lines.append(f"    state {iface.state}")
        return "\n".join(lines)

    def link_text(self) -> str:
        return "\n".join(f"{i.name}: state {i.state}" for i in self.student.interfaces)

    def route_text(self) -> str:
        lines: list[str] = []
        for r in self.student.routes:
            if r.is_default:
                lines.append(f"default via {r.via} dev {r.dev}")
            else:
                lines.append(f"{r.destination} dev {r.dev}")
        return "\n".join(lines)

    def services_text(self) -> str:
        lines = ["State   Local Address:Port"]
        for s in self.student.services:
            lines.append(f"{s.state}  {self.student_ip}:{s.port}  ({s.proto}/{s.name})")
        return "\n".join(lines)


def build_network(config: dict[str, Any]) -> VirtualNetwork:
    """Build a VirtualNetwork from a mission's declarative 'network' dict.

    Keeps mission_loader.py fully declarative (plain dicts, no behavior) —
    the same pattern already used for "filesystem"/"permissions".
    """
    hosts: dict[str, VirtualHost] = {}
    for ip, hc in config.get("hosts", {}).items():
        hosts[ip] = VirtualHost(
            hostname=hc.get("hostname", ip),
            ip=ip,
            interfaces=[NetworkInterface(**i) for i in hc.get("interfaces", [])],
            routes=[Route(**r) for r in hc.get("routes", [])],
            services=[Service(**s) for s in hc.get("services", [])],
            reachable=hc.get("reachable", True),
        )
    dns_records = [DNSRecord(**d) for d in config.get("dns_records", [])]
    return VirtualNetwork(
        student_ip=config["student_ip"], hosts=hosts,
        dns_records=dns_records, dns_server_ip=config.get("dns_server_ip"),
        dns_working=config.get("dns_working", True),
    )
