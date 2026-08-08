"""Simulated network — YC-034.5 Networking Fundamentals + future networking missions.

A small, deterministic, read-only educational LAN model. Like VirtualFS,
this never touches a real socket, DNS resolver, ARP table, or the host's
network stack — `ping`/`nslookup`/`ss`/etc. are pure string-formatting
functions over an in-memory topology built from a mission's declarative
``"network"`` config dict (see mission_loader.py). Future networking
missions (Nmap Fundamentals, Network Troubleshooting, Recon) reuse this
same module by supplying their own config — hosts are never hardcoded
into objectives or command handlers.
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
    """A small, deterministic, read-only educational LAN."""

    def __init__(self, student_ip: str, hosts: dict[str, VirtualHost],
                 dns_records: list[DNSRecord], dns_server_ip: str | None = None) -> None:
        self.student_ip = student_ip
        self.hosts = hosts
        self.dns_records = dns_records
        self.dns_server_ip = dns_server_ip

    @property
    def student(self) -> VirtualHost:
        return self.hosts[self.student_ip]

    def ping(self, target: str) -> tuple[bool, str]:
        """Returns (reachable, formatted ping output) — never a real ICMP call."""
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
        for rec in self.dns_records:
            if rec.hostname == hostname:
                return rec.ip
        return None

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
    )
