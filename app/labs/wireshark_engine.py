"""Wireshark Packet Generator & Filter Engine (YC-028.0).

Transforms raw ``net_engine.Packet`` objects into multi-layer protocol
frames that look like real Wireshark captures. The filter engine parses
Wireshark-style display filters (``tcp.port == 80``, ``ip.addr == x``,
``http``, ``dns``, etc.) against these enriched packets.

Architecture:
  · PacketGenerator — takes session capture buffer + topology, enriches
    each raw packet dict into a WiresharkPacket with Ethernet/IP/
    TCP-UDP/Application layers. Also generates synthetic background
    traffic (ARP, DNS, DHCP) so the capture isn't empty before the
    student runs any commands.
  · FilterEngine — parses a display-filter string and returns a
    predicate function. Supports protocol shorthand (``http``), field
    comparison (``ip.src == x``), port filters (``tcp.port == 80``),
    and ``&&`` / ``||`` / ``!`` operators.
  · follow_stream — extracts all packets belonging to one TCP
    conversation (src:port ↔ dst:port pair).
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from app.labs.net_engine import SERVICE_CATALOGUE


# ---------------------------------------------------------------------------
# Enriched packet — what the Wireshark UI renders
# ---------------------------------------------------------------------------
@dataclass
class WiresharkPacket:
    """One row in the packet list pane."""
    number: int
    timestamp: float            # seconds since capture start
    source_ip: str
    dest_ip: str
    source_mac: str
    dest_mac: str
    protocol: str               # display protocol: ARP, ICMP, TCP, UDP, DNS, HTTP, etc.
    length: int                 # simulated frame length in bytes
    info: str                   # one-line summary (like Wireshark's Info column)
    ttl: int
    src_port: Optional[int]
    dst_port: Optional[int]
    flags: str                  # TCP flags string, e.g. "[SYN, ACK]"
    status: str                 # delivered, timeout, etc.
    # Layer details for the detail pane
    layers: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Raw hex for the bytes pane (simulated)
    hex_dump: str = ""
    # Stream identifier for Follow Stream
    stream_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "timestamp": round(self.timestamp, 6),
            "source_ip": self.source_ip,
            "dest_ip": self.dest_ip,
            "source_mac": self.source_mac,
            "dest_mac": self.dest_mac,
            "protocol": self.protocol,
            "length": self.length,
            "info": self.info,
            "ttl": self.ttl,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "flags": self.flags,
            "status": self.status,
            "layers": self.layers,
            "hex_dump": self.hex_dump,
            "stream_id": self.stream_id,
        }


# ---------------------------------------------------------------------------
# MAC lookup helper
# ---------------------------------------------------------------------------
def _mac_for(hostname: str, hosts: dict[str, Any]) -> str:
    h = hosts.get(hostname, {})
    return h.get("mac", "") or h.get("mac_address", "") or "00:00:00:00:00:00"

def _ip_for(hostname: str, hosts: dict[str, Any]) -> str:
    h = hosts.get(hostname, {})
    return h.get("ip", "") or h.get("ip_address", "") or "0.0.0.0"


# ---------------------------------------------------------------------------
# Packet Generator
# ---------------------------------------------------------------------------
class PacketGenerator:
    """Enriches raw engine packet dicts into WiresharkPackets and
    generates synthetic background traffic."""

    def __init__(self, hosts: dict[str, dict[str, Any]]):
        """hosts: {hostname: {ip, mac, os, open_ports, services, ...}}"""
        self.hosts = hosts

    def generate_capture(self, raw_packets: list[dict],
                         include_background: bool = True) -> list[WiresharkPacket]:
        """Build a complete capture from the session buffer + optional
        background traffic (ARP, DNS, DHCP)."""
        packets: list[WiresharkPacket] = []
        t0 = 0.0

        # Background traffic first (gives students something to filter)
        if include_background:
            packets.extend(self._background_traffic(t0))
            t0 = max((p.timestamp for p in packets), default=0) + 0.1

        # Enrich each raw packet from the engine
        for i, raw in enumerate(raw_packets):
            t0 += 0.001 + (hash(str(raw.get("id", i))) % 50) / 1000
            pkt = self._enrich(raw, t0)
            packets.append(pkt)

        # Renumber
        for i, p in enumerate(packets):
            p.number = i + 1

        return packets

    def _enrich(self, raw: dict, ts: float) -> WiresharkPacket:
        """Turn a raw engine packet dict into a full WiresharkPacket."""
        src_host = raw.get("source", "")
        dst_host = raw.get("destination", "")
        src_ip = _ip_for(src_host, self.hosts) or raw.get("source", "")
        dst_ip = _ip_for(dst_host, self.hosts) or raw.get("destination", "")
        src_mac = _mac_for(src_host, self.hosts)
        dst_mac = _mac_for(dst_host, self.hosts)
        proto = (raw.get("protocol") or "tcp").upper()
        port = raw.get("port")
        ttl = raw.get("ttl", 64)
        status = raw.get("status", "delivered")
        latency = raw.get("latency_ms", 1.0)
        seq = raw.get("sequence", 0)

        # Determine display protocol from port
        display_proto = proto
        if proto in ("TCP", "UDP") and port:
            if port == 80:
                display_proto = "HTTP"
            elif port == 443:
                display_proto = "TLS"
            elif port == 53:
                display_proto = "DNS"
            elif port == 21:
                display_proto = "FTP"
            elif port == 25:
                display_proto = "SMTP"
            elif port == 67 or port == 68:
                display_proto = "DHCP"

        # Info line
        info = self._info_line(display_proto, src_ip, dst_ip, port, seq, status, ttl)

        # TCP flags
        flags = ""
        if proto == "TCP":
            if status == "delivered":
                flags = "[SYN, ACK]" if seq == 0 else "[ACK]"
            elif status == "port-closed":
                flags = "[RST, ACK]"
            else:
                flags = "[SYN]"

        # Length (simulated)
        length = 54  # Ethernet header
        if proto == "ICMP":
            length = 98
        elif port and port in (80, 443):
            length = 60 + hash(f"{src_host}{dst_host}{port}") % 1400

        # Stream ID for Follow Stream
        stream_id = ""
        if proto == "TCP" and port:
            endpoints = sorted([(src_ip, port), (dst_ip, port)])
            stream_id = f"{endpoints[0][0]}:{endpoints[0][1]}-{endpoints[1][0]}:{endpoints[1][1]}"

        # Build layer details
        layers = self._build_layers(
            src_ip, dst_ip, src_mac, dst_mac, proto, display_proto,
            port, ttl, flags, length, seq, status
        )

        # Hex dump (simulated — first 3 rows)
        hex_dump = self._hex_dump(src_mac, dst_mac, src_ip, dst_ip, proto, port)

        return WiresharkPacket(
            number=0, timestamp=ts, source_ip=src_ip, dest_ip=dst_ip,
            source_mac=src_mac, dest_mac=dst_mac, protocol=display_proto,
            length=length, info=info, ttl=ttl, src_port=port if proto == "TCP" else None,
            dst_port=port, flags=flags, status=status, layers=layers,
            hex_dump=hex_dump, stream_id=stream_id,
        )

    def _info_line(self, proto, src, dst, port, seq, status, ttl):
        if proto == "ICMP":
            if status == "delivered":
                return f"Echo (ping) reply  id=0x{hash(src) % 0xFFFF:04x}  seq={seq}  ttl={ttl}"
            return f"Destination unreachable ({status})"
        if proto == "DNS":
            return f"Standard query A {dst}"
        if proto == "HTTP":
            return f"GET / HTTP/1.1"
        if proto == "TLS":
            return f"Client Hello → {dst}:{port}"
        if proto == "ARP":
            return f"Who has {dst}? Tell {src}"
        if proto == "DHCP":
            return f"DHCP Discover"
        if proto == "FTP":
            return f"Response: 220 Service ready"
        if proto == "SMTP":
            return f"EHLO {src}"
        svc = SERVICE_CATALOGUE.get(port, {}).get("name", "")
        return f"{src}:{port or '?'} → {dst}:{port or '?'} {svc} [{status}]"

    def _build_layers(self, src_ip, dst_ip, src_mac, dst_mac, proto,
                      display_proto, port, ttl, flags, length, seq, status):
        layers = {
            "Ethernet II": {
                "Source": src_mac,
                "Destination": dst_mac,
                "Type": "IPv4 (0x0800)" if proto != "ARP" else "ARP (0x0806)",
            },
            "Internet Protocol": {
                "Version": "4",
                "Source": src_ip,
                "Destination": dst_ip,
                "TTL": str(ttl),
                "Protocol": proto,
                "Total Length": str(length - 14),
            },
        }
        if proto == "TCP":
            layers["Transmission Control Protocol"] = {
                "Source Port": str(port or 0),
                "Destination Port": str(port or 0),
                "Flags": flags,
                "Sequence Number": str(seq),
                "Window Size": "65535",
            }
        elif proto == "UDP":
            layers["User Datagram Protocol"] = {
                "Source Port": str(port or 0),
                "Destination Port": str(port or 0),
                "Length": str(length - 34),
            }
        elif proto == "ICMP":
            layers["Internet Control Message Protocol"] = {
                "Type": "0 (Echo Reply)" if status == "delivered" else "3 (Dest Unreachable)",
                "Code": "0",
                "Sequence": str(seq),
            }
        # Application layer hints
        if display_proto == "HTTP":
            layers["Hypertext Transfer Protocol"] = {
                "Request Method": "GET",
                "Request URI": "/",
                "Host": dst_ip,
            }
        elif display_proto == "DNS":
            layers["Domain Name System"] = {
                "Transaction ID": f"0x{hash(dst_ip) % 0xFFFF:04x}",
                "Queries": f"A {dst_ip}",
                "Type": "A (Host Address)",
            }
        elif display_proto == "TLS":
            layers["Transport Layer Security"] = {
                "Content Type": "Handshake (22)",
                "Version": "TLS 1.3",
                "Handshake Type": "Client Hello",
            }
        return layers

    def _hex_dump(self, src_mac, dst_mac, src_ip, dst_ip, proto, port):
        """Generate a realistic-looking hex dump (first 48 bytes)."""
        def mac_bytes(m):
            return " ".join(m.replace("-", ":").split(":"))
        def ip_bytes(ip):
            return " ".join(f"{int(o):02x}" for o in ip.split(".")) if ip and "." in ip else "00 00 00 00"

        lines = []
        # Row 0: Ethernet header
        row0 = f"{dst_mac.replace(':', ' ')} {src_mac.replace(':', ' ')} 08 00"
        lines.append(f"0000   {row0}")
        # Row 1: IP header start
        row1 = f"45 00 00 54 {hash(src_ip) % 256:02x} {hash(dst_ip) % 256:02x} 40 00 40 {'01' if proto == 'ICMP' else '06'} 00 00 {ip_bytes(src_ip)} {ip_bytes(dst_ip)}"
        lines.append(f"0010   {row1[:48]}")
        # Row 2: port bytes
        if port:
            row2 = f"00 {port >> 8:02x} {port & 0xFF:02x} 00 {port >> 8:02x} {port & 0xFF:02x} 00 00 00 00 00 00 00 00 50 02"
            lines.append(f"0020   {row2}")
        return "\n".join(lines)

    def _background_traffic(self, t0: float) -> list[WiresharkPacket]:
        """Generate synthetic ARP, DNS, DHCP traffic that would appear
        on a real network capture even before the student does anything."""
        packets = []
        host_list = list(self.hosts.values())

        for i, h in enumerate(host_list):
            ip = h.get("ip", "")
            mac = h.get("mac", "00:00:00:00:00:00")
            if not ip:
                continue

            # ARP request + reply
            packets.append(WiresharkPacket(
                number=0, timestamp=t0 + i * 0.002,
                source_ip=ip, dest_ip="192.168.1.255",
                source_mac=mac, dest_mac="ff:ff:ff:ff:ff:ff",
                protocol="ARP", length=42,
                info=f"Who has {ip}? Tell {ip} (Gratuitous ARP)",
                ttl=0, src_port=None, dst_port=None,
                flags="", status="delivered",
                layers={
                    "Ethernet II": {"Source": mac, "Destination": "ff:ff:ff:ff:ff:ff", "Type": "ARP (0x0806)"},
                    "Address Resolution Protocol": {"Opcode": "request (1)", "Sender MAC": mac, "Sender IP": ip, "Target IP": ip},
                },
            ))

            # DNS query (simulated)
            if h.get("gateway"):
                packets.append(WiresharkPacket(
                    number=0, timestamp=t0 + i * 0.002 + 0.001,
                    source_ip=ip, dest_ip=h.get("dns", "8.8.8.8"),
                    source_mac=mac, dest_mac=_mac_for("router", self.hosts),
                    protocol="DNS", length=74,
                    info=f"Standard query A {h.get('hostname', 'unknown')}",
                    ttl=64, src_port=53, dst_port=53,
                    flags="", status="delivered",
                    layers={
                        "Ethernet II": {"Source": mac, "Destination": _mac_for("router", self.hosts), "Type": "IPv4 (0x0800)"},
                        "Internet Protocol": {"Source": ip, "Destination": h.get("dns", "8.8.8.8"), "TTL": "64"},
                        "User Datagram Protocol": {"Source Port": "53", "Destination Port": "53"},
                        "Domain Name System": {"Transaction ID": f"0x{hash(ip) % 0xFFFF:04x}", "Queries": f"A {h.get('hostname', '?')}"},
                    },
                ))

        return packets


# ---------------------------------------------------------------------------
# Filter Engine — parses Wireshark-style display filters
# ---------------------------------------------------------------------------
class FilterEngine:
    """Parses a display-filter string into a predicate function.

    Supported syntax:
      protocol shorthand: http, dns, tcp, udp, arp, icmp, tls, ftp, smtp, dhcp
      field comparisons:  ip.addr == x, ip.src == x, ip.dst == x
                          tcp.port == N, udp.port == N, tcp.dstport == N
      operators:          && (and), || (or), ! (not)
      contains:           tcp contains "GET"
    """

    @staticmethod
    def parse(filter_str: str) -> Callable[[WiresharkPacket], bool]:
        """Return a predicate function for the given filter string."""
        raw = filter_str.strip()
        if not raw:
            return lambda p: True

        # Handle ! (not) prefix
        if raw.startswith("!"):
            inner = FilterEngine.parse(raw[1:].strip())
            return lambda p, f=inner: not f(p)

        # Handle && and ||
        if " && " in raw:
            parts = raw.split(" && ", 1)
            left = FilterEngine.parse(parts[0])
            right = FilterEngine.parse(parts[1])
            return lambda p, l=left, r=right: l(p) and r(p)
        if " || " in raw:
            parts = raw.split(" || ", 1)
            left = FilterEngine.parse(parts[0])
            right = FilterEngine.parse(parts[1])
            return lambda p, l=left, r=right: l(p) or r(p)

        # Field comparison: ip.addr == x, tcp.port == N, etc.
        for op in ("==", "!=", ">=", "<=", ">", "<"):
            if op in raw:
                field, value = raw.split(op, 1)
                field = field.strip().lower()
                value = value.strip().strip('"').strip("'")
                return FilterEngine._field_filter(field, op, value)

        # Protocol shorthand
        proto = raw.lower().strip()
        return FilterEngine._protocol_filter(proto)

    @staticmethod
    def _protocol_filter(proto: str) -> Callable[[WiresharkPacket], bool]:
        mapping = {
            "http": lambda p: p.protocol == "HTTP",
            "dns": lambda p: p.protocol == "DNS",
            "tcp": lambda p: p.protocol in ("TCP", "HTTP", "TLS", "FTP", "SMTP"),
            "udp": lambda p: p.protocol in ("UDP", "DNS", "DHCP"),
            "arp": lambda p: p.protocol == "ARP",
            "icmp": lambda p: p.protocol == "ICMP",
            "tls": lambda p: p.protocol == "TLS",
            "ftp": lambda p: p.protocol == "FTP",
            "smtp": lambda p: p.protocol == "SMTP",
            "dhcp": lambda p: p.protocol == "DHCP",
        }
        return mapping.get(proto, lambda p: proto.upper() in p.protocol)

    @staticmethod
    def _field_filter(field: str, op: str, value: str) -> Callable[[WiresharkPacket], bool]:
        def get_field(p: WiresharkPacket) -> Any:
            if field == "ip.addr":
                return (p.source_ip, p.dest_ip)
            if field == "ip.src":
                return p.source_ip
            if field == "ip.dst":
                return p.dest_ip
            if field in ("tcp.port", "udp.port"):
                return (p.src_port, p.dst_port)
            if field == "tcp.srcport":
                return p.src_port
            if field in ("tcp.dstport", "udp.dstport"):
                return p.dst_port
            if field == "eth.src":
                return p.source_mac
            if field == "eth.dst":
                return p.dest_mac
            if field == "frame.len":
                return p.length
            return None

        def compare(pkt: WiresharkPacket) -> bool:
            v = get_field(pkt)
            if v is None:
                return False
            # Tuple fields (ip.addr, tcp.port) → match if either side matches
            if isinstance(v, tuple):
                return any(_compare_single(item, op, value) for item in v if item is not None)
            return _compare_single(v, op, value)
        return compare


def _compare_single(actual, op: str, expected: str) -> bool:
    # Try numeric comparison
    try:
        a = float(actual) if not isinstance(actual, (int, float)) else actual
        e = float(expected)
        if op == "==": return a == e
        if op == "!=": return a != e
        if op == ">=": return a >= e
        if op == "<=": return a <= e
        if op == ">":  return a > e
        if op == "<":  return a < e
    except (ValueError, TypeError):
        pass
    # String comparison
    a_str = str(actual).lower()
    e_str = expected.lower()
    if op == "==": return a_str == e_str
    if op == "!=": return a_str != e_str
    return False


# ---------------------------------------------------------------------------
# Follow Stream — extract a TCP conversation
# ---------------------------------------------------------------------------
def follow_stream(packets: list[WiresharkPacket],
                  stream_id: str) -> list[WiresharkPacket]:
    """Return all packets belonging to one TCP stream."""
    return [p for p in packets if p.stream_id == stream_id]
