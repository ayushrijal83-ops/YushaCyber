"""Simulated packet-analysis engine — YC-034.9 Wireshark Fundamentals.

Independent from (and never touches) VirtualNetwork/VirtualHost in
network.py — that module simulates network *state* (interfaces, routes,
services); this one simulates network *traffic* (a fixed, deterministic
sequence of Packet objects a student inspects, filters, and follows).
Both are pure in-memory data, never a real socket, capture library,
or subprocess.

Packet content lives in hand-written builder functions below (not the
mission's declarative dict, unlike VirtualNetwork's config) because a
30-60 packet capture with a dozen fields each is qualitatively more
data than the small key/value host configs elsewhere — expressing it
as nested dict literals in mission_loader.py would be far less
readable than the same data built with a small loop. A mission's
config just lists which capture *names* to load
(``"packet_captures": ["handshake", "dns", ...]``), keeping
mission_loader.py itself still fully declarative.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

_MAC_TABLE = {
    "10.10.10.20": "02:42:0a:0a:0a:14",
    "10.10.10.10": "02:42:0a:0a:0a:0a",
    "10.10.10.53": "02:42:0a:0a:0a:35",
    "10.10.10.1": "02:42:0a:0a:0a:01",
    "10.10.10.77": "02:42:0a:0a:0a:4d",
}


def _mac(ip: str) -> str:
    return _MAC_TABLE.get(ip, "02:42:00:00:00:00")


def _conv_id(ip_a: str, port_a: int | None, ip_b: str, port_b: int | None, proto: str) -> str:
    """A conversation id is order-independent — both directions of one
    exchange must map to the same id regardless of who's "source"."""
    a = f"{ip_a}:{port_a}" if port_a is not None else ip_a
    b = f"{ip_b}:{port_b}" if port_b is not None else ip_b
    lo, hi = sorted((a, b))
    return f"{proto.lower()}:{lo}<->{hi}"


@dataclass
class Packet:
    """One simulated frame. Purely structured data — never rendered as
    a hardcoded terminal string at construction time; PacketCapture's
    rendering methods format it on demand."""
    number: int
    timestamp: float
    length: int
    protocol: str
    src_mac: str
    dst_mac: str
    src_ip: str
    dst_ip: str
    src_port: int | None = None
    dst_port: int | None = None
    tcp_flags: str | None = None
    ttl: int = 64
    payload_summary: str = ""
    application_protocol: str | None = None
    conversation_id: str | None = None


def _pkt(seq: _Seq, protocol: str, src_ip: str, dst_ip: str,
         src_port: int | None = None, dst_port: int | None = None,
         flags: str | None = None, length: int = 74, payload: str = "",
         app_proto: str | None = None, conv: str | None = None,
         ttl: int = 64) -> Packet:
    number, timestamp = seq.next()
    return Packet(number=number, timestamp=timestamp, length=length, protocol=protocol,
                 src_mac=_mac(src_ip), dst_mac=_mac(dst_ip), src_ip=src_ip, dst_ip=dst_ip,
                 src_port=src_port, dst_port=dst_port, tcp_flags=flags, ttl=ttl,
                 payload_summary=payload, application_protocol=app_proto,
                 conversation_id=conv)


class _Seq:
    """Deterministic packet-number/timestamp generator for one capture
    builder. No randomness anywhere — captures must be reproducible."""

    def __init__(self, start_time: float = 0.001, step: float = 0.001) -> None:
        self.n = 0
        self.t = start_time
        self.step = step

    def next(self) -> tuple[int, float]:
        self.n += 1
        t = self.t
        self.t += self.step
        return self.n, t


class PacketCapture:
    """A fixed, deterministic list of packets plus read-only inspection
    (filter/get/conversation) and terminal-text rendering. Never mutated
    after construction."""

    def __init__(self, name: str, packets: list[Packet]) -> None:
        self.name = name
        self.packets = packets

    def get(self, number: int) -> Packet | None:
        return next((p for p in self.packets if p.number == number), None)

    def conversation(self, conv_id: str) -> list[Packet]:
        return [p for p in self.packets if p.conversation_id == conv_id]

    def filter(self, expr: str) -> list[Packet]:
        """A small, safe display-filter subset: bare protocol names
        (tcp/udp/dns/http/icmp) and `field == value` comparisons for
        tcp.port / udp.port / ip.addr / ip.src / ip.dst. Operates only
        on this capture's in-memory Packet list."""
        expr = expr.strip().lower()
        if "==" in expr:
            left, _, right = expr.partition("==")
            left, right = left.strip(), right.strip()
            if left == "tcp.port":
                return self._by_port("tcp", right)
            if left == "udp.port":
                return self._by_port("udp", right)
            if left == "ip.addr":
                return [p for p in self.packets if right in (p.src_ip, p.dst_ip)]
            if left == "ip.src":
                return [p for p in self.packets if p.src_ip == right]
            if left == "ip.dst":
                return [p for p in self.packets if p.dst_ip == right]
            return []
        if expr in ("dns", "http"):
            return [p for p in self.packets
                    if p.protocol.lower() == expr or (p.application_protocol or "").lower() == expr]
        if expr in ("tcp", "udp", "icmp"):
            return [p for p in self.packets if p.protocol.lower() == expr]
        return []

    def _by_port(self, proto: str, value: str) -> list[Packet]:
        if not value.isdigit():
            return []
        port = int(value)
        return [p for p in self.packets
                if p.protocol.lower() in (proto, "dns", "http")
                and port in (p.src_port, p.dst_port)]

    # ── Rendering — text formatting only, never how the data is stored ──
    def list_text(self, packets: list[Packet] | None = None) -> str:
        rows = self.packets if packets is None else packets
        if not rows:
            return "No packets to display."
        lines = [f"{'#':<5}{'TIME':<10}{'SOURCE':<16}{'DESTINATION':<16}{'PROTOCOL':<10}INFO"]
        for p in rows:
            lines.append(f"{p.number:<5}{p.timestamp:<10.3f}{p.src_ip:<16}"
                        f"{p.dst_ip:<16}{p.protocol:<10}{p.payload_summary}")
        return "\n".join(lines)

    def detail_text(self, p: Packet) -> str:
        lines = [f"Packet #{p.number}", f"Time: {p.timestamp:.6f}",
                 f"Length: {p.length} bytes", "", "Ethernet II",
                 f"    Source: {p.src_mac}", f"    Destination: {p.dst_mac}",
                 "", "IPv4", f"    Source: {p.src_ip}", f"    Destination: {p.dst_ip}",
                 f"    TTL: {p.ttl}", ""]
        proto = p.protocol.lower()
        if proto in ("tcp", "http"):
            lines += ["TCP", f"    Source Port: {p.src_port}",
                     f"    Destination Port: {p.dst_port}",
                     f"    Flags: {p.tcp_flags or ''}", ""]
        elif proto in ("udp", "dns"):
            lines += ["UDP", f"    Source Port: {p.src_port}",
                     f"    Destination Port: {p.dst_port}", ""]
        elif proto == "icmp":
            lines += ["ICMP", f"    Type: {p.payload_summary}", ""]
        if p.application_protocol:
            lines += [f"Application: {p.application_protocol}", f"    {p.payload_summary}", ""]
        if p.conversation_id:
            lines.append(f"Conversation: {p.conversation_id}")
        return "\n".join(lines).rstrip()

    def conversation_text(self, conv_id: str, packets: list[Packet]) -> str:
        lines = [f"Conversation: {conv_id}", "", "Packets:"]
        for p in packets:
            lines.append(f"  #{p.number}  {p.protocol:<6} {p.payload_summary}")
        return "\n".join(lines)


class PacketLab:
    """Holds every capture available to a mission session plus which one
    is currently "open" (like opening a .pcap file in Wireshark)."""

    def __init__(self, captures: dict[str, PacketCapture]) -> None:
        self.captures = captures
        self.active: PacketCapture | None = None
        self.selected_packet: int | None = None
        self.last_filter: str | None = None

    def open_capture(self, name: str) -> bool:
        cap = self.captures.get(name)
        if cap is None:
            return False
        self.active = cap
        self.selected_packet = None
        self.last_filter = None
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active.name if self.active else None,
            "selected_packet": self.selected_packet,
            "last_filter": self.last_filter,
        }

    def apply_state(self, snapshot: dict[str, Any]) -> None:
        active_name = snapshot.get("active")
        if active_name:
            self.open_capture(active_name)
        self.selected_packet = snapshot.get("selected_packet")
        self.last_filter = snapshot.get("last_filter")


# ═══════════════════════════════════════════════════════════
# Capture datasets — deterministic, hand-authored. Loops below build
# repeated background traffic predictably (fixed port/hostname
# increments), never with `random`, so every capture is reproducible.
# ═══════════════════════════════════════════════════════════
def _build_handshake() -> PacketCapture:
    seq = _Seq()
    c, s = "10.10.10.20", "10.10.10.10"
    cp, sp = 49152, 80
    conv = _conv_id(c, cp, s, sp, "tcp")
    pkts = [
        _pkt(seq, "TCP", c, s, cp, sp, flags="SYN", payload="SYN", conv=conv),
        _pkt(seq, "TCP", s, c, sp, cp, flags="SYN, ACK", payload="SYN, ACK", conv=conv),
        _pkt(seq, "TCP", c, s, cp, sp, flags="ACK", length=66, payload="ACK", conv=conv),
    ]
    return PacketCapture("handshake", pkts)


def _build_dns() -> PacketCapture:
    seq = _Seq()
    c, d = "10.10.10.20", "10.10.10.53"
    cp = 53412
    conv = _conv_id(c, cp, d, 53, "udp")
    pkts = [
        _pkt(seq, "DNS", c, d, cp, 53, length=70,
             payload="Standard query A example.training", app_proto="DNS", conv=conv),
        _pkt(seq, "DNS", d, c, 53, cp, length=86,
             payload="Standard query response A example.training 10.10.10.10",
             app_proto="DNS", conv=conv),
    ]
    return PacketCapture("dns", pkts)


def _build_http() -> PacketCapture:
    seq = _Seq()
    c, s = "10.10.10.20", "10.10.10.10"
    cp, sp = 49153, 80
    conv = _conv_id(c, cp, s, sp, "tcp")
    pkts = [
        _pkt(seq, "TCP", c, s, cp, sp, flags="SYN", payload="SYN", conv=conv),
        _pkt(seq, "TCP", s, c, sp, cp, flags="SYN, ACK", payload="SYN, ACK", conv=conv),
        _pkt(seq, "TCP", c, s, cp, sp, flags="ACK", length=66, payload="ACK", conv=conv),
        _pkt(seq, "HTTP", c, s, cp, sp, flags="PSH, ACK", length=210,
             payload="GET /index.html HTTP/1.1", app_proto="HTTP", conv=conv),
        _pkt(seq, "TCP", s, c, sp, cp, flags="ACK", length=66, payload="ACK", conv=conv),
        _pkt(seq, "HTTP", s, c, sp, cp, flags="PSH, ACK", length=512,
             payload="HTTP/1.1 200 OK  Content-Type: text/html", app_proto="HTTP", conv=conv),
        _pkt(seq, "TCP", c, s, cp, sp, flags="FIN, ACK", length=66, payload="FIN, ACK", conv=conv),
        _pkt(seq, "TCP", s, c, sp, cp, flags="ACK", length=66, payload="ACK", conv=conv),
    ]
    return PacketCapture("http", pkts)


def _build_icmp() -> PacketCapture:
    seq = _Seq()
    c, s = "10.10.10.20", "10.10.10.10"
    pkts = [
        _pkt(seq, "ICMP", c, s, length=98, payload="Echo (ping) request"),
        _pkt(seq, "ICMP", s, c, length=98, payload="Echo (ping) reply"),
    ]
    return PacketCapture("icmp", pkts)


def _build_mixed() -> PacketCapture:
    seq = _Seq()
    c, s, d, g = "10.10.10.20", "10.10.10.10", "10.10.10.53", "10.10.10.1"
    pkts: list[Packet] = []

    conv_dns = _conv_id(c, 53500, d, 53, "udp")
    pkts.append(_pkt(seq, "DNS", c, d, 53500, 53, length=70,
                     payload="Standard query A example.training", app_proto="DNS", conv=conv_dns))
    pkts.append(_pkt(seq, "DNS", d, c, 53, 53500, length=86,
                     payload="Standard query response A example.training 10.10.10.10",
                     app_proto="DNS", conv=conv_dns))

    conv_http = _conv_id(c, 49160, s, 80, "tcp")
    pkts.append(_pkt(seq, "TCP", c, s, 49160, 80, flags="SYN", payload="SYN", conv=conv_http))
    pkts.append(_pkt(seq, "TCP", s, c, 80, 49160, flags="SYN, ACK", payload="SYN, ACK", conv=conv_http))
    pkts.append(_pkt(seq, "TCP", c, s, 49160, 80, flags="ACK", length=66, payload="ACK", conv=conv_http))
    pkts.append(_pkt(seq, "HTTP", c, s, 49160, 80, flags="PSH, ACK", length=210,
                     payload="GET /index.html HTTP/1.1", app_proto="HTTP", conv=conv_http))
    pkts.append(_pkt(seq, "HTTP", s, c, 80, 49160, flags="PSH, ACK", length=512,
                     payload="HTTP/1.1 200 OK", app_proto="HTTP", conv=conv_http))

    for _ in range(5):
        pkts.append(_pkt(seq, "ICMP", c, g, length=98, payload="Echo (ping) request"))
        pkts.append(_pkt(seq, "ICMP", g, c, length=98, payload="Echo (ping) reply"))

    for i in range(5):
        pkts.append(_pkt(seq, "UDP", c, g, 40000 + i, 123, length=90, payload="NTP time sync"))

    for i in range(5):
        host = f"host{i}.training"
        cport = 54000 + i
        conv = _conv_id(c, cport, d, 53, "udp")
        pkts.append(_pkt(seq, "DNS", c, d, cport, 53, length=68,
                         payload=f"Standard query A {host}", app_proto="DNS", conv=conv))
        pkts.append(_pkt(seq, "DNS", d, c, 53, cport, length=84,
                         payload=f"Standard query response A {host} 10.10.10.10",
                         app_proto="DNS", conv=conv))

    return PacketCapture("mixed", pkts)


def _build_investigation() -> PacketCapture:
    seq = _Seq()
    c, s, d, g = "10.10.10.20", "10.10.10.10", "10.10.10.53", "10.10.10.1"
    pkts: list[Packet] = []

    conv_dns = _conv_id(c, 55000, d, 53, "udp")
    pkts.append(_pkt(seq, "DNS", c, d, 55000, 53, length=70,
                     payload="Standard query A example.training", app_proto="DNS", conv=conv_dns))
    pkts.append(_pkt(seq, "DNS", d, c, 53, 55000, length=86,
                     payload="Standard query response A example.training 10.10.10.10",
                     app_proto="DNS", conv=conv_dns))

    conv_http = _conv_id(c, 49170, s, 80, "tcp")
    pkts.append(_pkt(seq, "TCP", c, s, 49170, 80, flags="SYN", payload="SYN", conv=conv_http))
    pkts.append(_pkt(seq, "TCP", s, c, 80, 49170, flags="SYN, ACK", payload="SYN, ACK", conv=conv_http))
    pkts.append(_pkt(seq, "TCP", c, s, 49170, 80, flags="ACK", length=66, payload="ACK", conv=conv_http))
    pkts.append(_pkt(seq, "HTTP", c, s, 49170, 80, flags="PSH, ACK", length=210,
                     payload="GET /index.html HTTP/1.1", app_proto="HTTP", conv=conv_http))
    pkts.append(_pkt(seq, "HTTP", s, c, 80, 49170, flags="PSH, ACK", length=480,
                     payload="HTTP/1.1 200 OK", app_proto="HTTP", conv=conv_http))

    for _ in range(3):
        pkts.append(_pkt(seq, "ICMP", c, g, length=98, payload="Echo (ping) request"))
        pkts.append(_pkt(seq, "ICMP", g, c, length=98, payload="Echo (ping) reply"))

    for i in range(6):
        host = f"site{i}.training"
        cport = 56000 + i
        conv = _conv_id(c, cport, d, 53, "udp")
        pkts.append(_pkt(seq, "DNS", c, d, cport, 53, length=68,
                         payload=f"Standard query A {host}", app_proto="DNS", conv=conv))
        pkts.append(_pkt(seq, "DNS", d, c, 53, cport, length=84,
                         payload=f"Standard query response A {host} 10.10.10.10",
                         app_proto="DNS", conv=conv))

    for i in range(4):
        cport = 49200 + i
        conv = _conv_id(c, cport, s, 80, "tcp")
        pkts.append(_pkt(seq, "TCP", c, s, cport, 80, flags="SYN", payload="SYN", conv=conv))
        pkts.append(_pkt(seq, "TCP", s, c, 80, cport, flags="SYN, ACK", payload="SYN, ACK", conv=conv))
        pkts.append(_pkt(seq, "HTTP", c, s, cport, 80, flags="PSH, ACK", length=200,
                         payload=f"GET /page{i}.html HTTP/1.1", app_proto="HTTP", conv=conv))
        pkts.append(_pkt(seq, "HTTP", s, c, 80, cport, flags="PSH, ACK", length=420,
                         payload="HTTP/1.1 200 OK", app_proto="HTTP", conv=conv))

    # The anomaly: an uncommon destination/port outside normal training
    # traffic. Analysis-only — no exploit payload, just enough evidence
    # (unexpected host + unusual port) for the student to flag it.
    suspicious_ip = "10.10.10.77"
    conv_sus = _conv_id(c, 49999, suspicious_ip, 4444, "tcp")
    pkts.append(_pkt(seq, "TCP", c, suspicious_ip, 49999, 4444, flags="SYN",
                     payload="SYN", conv=conv_sus))
    pkts.append(_pkt(seq, "TCP", suspicious_ip, c, 4444, 49999, flags="SYN, ACK",
                     payload="SYN, ACK", conv=conv_sus))
    pkts.append(_pkt(seq, "TCP", c, suspicious_ip, 49999, 4444, flags="ACK",
                     length=66, payload="ACK", conv=conv_sus))
    pkts.append(_pkt(seq, "TCP", c, suspicious_ip, 49999, 4444, flags="PSH, ACK",
                     length=90, payload="Unrecognized binary payload", conv=conv_sus))

    return PacketCapture("investigation", pkts)


CAPTURE_REGISTRY: dict[str, Callable[[], PacketCapture]] = {
    "handshake": _build_handshake,
    "dns": _build_dns,
    "http": _build_http,
    "icmp": _build_icmp,
    "mixed": _build_mixed,
    "investigation": _build_investigation,
}


def build_packet_lab(capture_names: list[str]) -> PacketLab:
    """Build a PacketLab from a mission's declarative list of capture
    names. Each builder returns fresh Packet instances every call, so
    concurrent sessions never share mutable state."""
    captures: dict[str, PacketCapture] = {}
    for name in capture_names:
        builder = CAPTURE_REGISTRY.get(name)
        if builder is not None:
            captures[name] = builder()
    return PacketLab(captures)
