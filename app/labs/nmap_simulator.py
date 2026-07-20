"""Simulated Nmap command (YC-027.0).

A self-contained module that plugs into the existing
:class:`MultiHostSimulator` dispatch table with one line::

    "nmap": self._cmd_nmap,

Everything here consumes the shared :mod:`net_engine` — no duplicated
networking logic. The module is structured as a mini-pipeline:

  1. **Parser** — reads argv-style flags from the terminal input.
  2. **Scanner** — drives the engine's ``scan_port`` / ``reachable`` /
     ``ping`` to collect per-port results.
  3. **Enrichers** — service-version detection (``-sV``) and OS
     fingerprinting (``-O``) look up data from the static databases
     below, keyed on the host's declared ``services`` and ``os`` string.
  4. **Formatter** — renders the results in Nmap's distinctive output
     style so students can read it the same way they'd read real output.

Future NSE support: the ``ScanResult`` dataclass carries a ``scripts``
slot that today stays empty. A future ticket can populate it with
simulated NSE output without changing the pipeline.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Service-version database — what ``-sV`` reports.
# Keyed on (port, service_name). Entries not found here fall back to a
# generic "service_name" with no version string (same as real Nmap when
# it can't fingerprint).
# ---------------------------------------------------------------------------
SERVICE_VERSIONS: dict[tuple[int, str], dict[str, str]] = {
    (22, "ssh"):     {"product": "OpenSSH",      "version": "8.9p1", "extra": "Ubuntu-3ubuntu0.6"},
    (21, "ftp"):     {"product": "vsftpd",        "version": "3.0.5", "extra": ""},
    (25, "smtp"):    {"product": "Postfix",        "version": "",      "extra": "smtpd"},
    (53, "dns"):     {"product": "ISC BIND",       "version": "9.18",  "extra": ""},
    (80, "http"):    {"product": "Apache httpd",   "version": "2.4.58", "extra": "(Debian)"},
    (443, "https"):  {"product": "Apache httpd",   "version": "2.4.58", "extra": "(Debian) OpenSSL/3.0"},
    (3306, "mysql"): {"product": "MySQL",          "version": "8.0.36", "extra": ""},
    (3389, "rdp"):   {"product": "Microsoft Terminal Services", "version": "", "extra": ""},
    (445, "smb"):    {"product": "Samba smbd",     "version": "4.18",  "extra": ""},
    (5432, "postgresql"): {"product": "PostgreSQL", "version": "16.2", "extra": ""},
    (8080, "http-alt"): {"product": "Apache Tomcat", "version": "10.1", "extra": ""},
    (80, "http-admin"): {"product": "RouterOS admin", "version": "7.x", "extra": ""},
}

# ---------------------------------------------------------------------------
# OS fingerprint database — what ``-O`` reports.
# Keyed on substrings of the host.os field. First match wins.
# ---------------------------------------------------------------------------
OS_FINGERPRINTS: list[tuple[str, dict[str, str]]] = [
    ("ubuntu",   {"os_name": "Linux", "os_detail": "Linux 5.15 - 6.5 (Ubuntu)", "os_accuracy": "96"}),
    ("debian",   {"os_name": "Linux", "os_detail": "Linux 5.10 - 6.1 (Debian)", "os_accuracy": "95"}),
    ("kali",     {"os_name": "Linux", "os_detail": "Linux 6.1 (Kali)",          "os_accuracy": "94"}),
    ("centos",   {"os_name": "Linux", "os_detail": "Linux 4.15 - 5.8 (CentOS)", "os_accuracy": "92"}),
    ("windows 11",    {"os_name": "Windows", "os_detail": "Microsoft Windows 11 22H2",  "os_accuracy": "95"}),
    ("windows 10",    {"os_name": "Windows", "os_detail": "Microsoft Windows 10 21H2",  "os_accuracy": "93"}),
    ("windows server", {"os_name": "Windows", "os_detail": "Microsoft Windows Server 2022", "os_accuracy": "94"}),
    ("routeros", {"os_name": "Linux",   "os_detail": "MikroTik RouterOS 7.x",  "os_accuracy": "90"}),
    ("switchos", {"os_name": "Linux",   "os_detail": "Linux 4.x (embedded)",   "os_accuracy": "85"}),
    ("pfsense",  {"os_name": "FreeBSD", "os_detail": "FreeBSD 13 (pfSense)",   "os_accuracy": "91"}),
    ("suricata", {"os_name": "Linux",   "os_detail": "Linux 5.15 (IDS appliance)", "os_accuracy": "88"}),
    ("wazuh",    {"os_name": "Linux",   "os_detail": "Linux 5.15 (SIEM appliance)", "os_accuracy": "87"}),
]

# The 100 most common ports (used by ``-F``). Real Nmap's ``-F`` scans the
# top 100; we use a curated subset that covers the service catalogue.
FAST_PORTS = (
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139,
    143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900,
    8080, 8443,
)

# Full default port list (top 1000). We abbreviate to keep the module
# reasonable — the formatter only shows ports with a result, so the user
# sees the same output shape as real Nmap.
DEFAULT_PORTS = tuple(range(1, 1025))


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class PortResult:
    """One port's scan result."""
    port: int
    protocol: str     # tcp | udp
    state: str        # open | closed | filtered
    service: str      # e.g. "http", "ssh"
    version: str = "" # e.g. "Apache httpd 2.4.58 (Debian)" (only with -sV)


@dataclass
class ScanResult:
    """Full scan result for one target host."""
    target: str
    ip: str
    mac: str
    os_name: str
    host_up: bool
    latency_ms: float
    ports: list[PortResult] = field(default_factory=list)
    os_detail: str = ""
    os_accuracy: str = ""
    scripts: list[dict[str, Any]] = field(default_factory=list)  # future NSE


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
@dataclass
class NmapArgs:
    """Parsed nmap command-line arguments."""
    targets: list[str] = field(default_factory=list)
    service_version: bool = False     # -sV
    os_detect: bool = False           # -O
    aggressive: bool = False          # -A (implies -sV -O)
    syn_scan: bool = False            # -sS
    no_ping: bool = False             # -Pn
    fast: bool = False                # -F
    timing: int = 3                   # -T0..T5
    ports: Optional[list[int]] = None # -p 22,80,443
    error: str = ""


def parse_nmap_args(argv: list[str]) -> NmapArgs:
    """Parse nmap-style arguments from the terminal input."""
    args = NmapArgs()
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "-sV":
            args.service_version = True
        elif tok == "-sS":
            args.syn_scan = True
        elif tok == "-O":
            args.os_detect = True
        elif tok == "-A":
            args.aggressive = True
            args.service_version = True
            args.os_detect = True
        elif tok == "-Pn":
            args.no_ping = True
        elif tok == "-F":
            args.fast = True
        elif tok.startswith("-T") and len(tok) == 3 and tok[2].isdigit():
            args.timing = int(tok[2])
        elif tok == "-p" and i + 1 < len(argv):
            i += 1
            try:
                args.ports = _parse_ports(argv[i])
            except ValueError as e:
                args.error = str(e)
                return args
        elif tok.startswith("-p") and len(tok) > 2:
            try:
                args.ports = _parse_ports(tok[2:])
            except ValueError as e:
                args.error = str(e)
                return args
        elif tok.startswith("-"):
            args.error = f"unrecognized option: {tok}"
            return args
        else:
            args.targets.append(tok)
        i += 1

    if not args.targets:
        args.error = "no target specified"
    return args


def _parse_ports(spec: str) -> list[int]:
    """Parse port specs: '22', '80,443', '1-100', '22,80-90'."""
    ports = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            lo, hi = int(lo), int(hi)
            if lo > hi or lo < 1 or hi > 65535:
                raise ValueError(f"invalid port range: {part}")
            ports.extend(range(lo, hi + 1))
        else:
            p = int(part)
            if p < 1 or p > 65535:
                raise ValueError(f"invalid port: {p}")
            ports.append(p)
    return sorted(set(ports))


# ---------------------------------------------------------------------------
# Scanner — drives the shared engine
# ---------------------------------------------------------------------------
def run_scan(engine, host_obj, args: NmapArgs) -> ScanResult:
    """Execute a simulated scan against one host using the shared engine.

    ``engine`` is a :class:`net_engine.NetworkEngine`.
    ``host_obj`` is the resolved Host/Device (duck-typed HostLike).
    """
    from app.labs.net_engine import SERVICE_CATALOGUE, PortState

    # Host-up check (unless -Pn skips it).
    host_up = engine.is_online(host_obj.hostname)
    latency = 0.0
    if host_up and not args.no_ping:
        replies = engine.ping("pc-1", host_obj.hostname, count=1)
        if replies:
            latency = replies[0].latency_ms

    result = ScanResult(
        target=host_obj.hostname,
        ip=host_obj.ip or "*",
        mac=getattr(host_obj, "mac", "") or "",
        os_name="",
        host_up=host_up or args.no_ping,
        latency_ms=latency or 1.42,
    )

    if not result.host_up:
        return result

    # Determine which ports to scan.
    if args.ports is not None:
        scan_ports = args.ports
    elif args.fast:
        scan_ports = list(FAST_PORTS)
    else:
        # Default: scan the host's declared open ports + a handful of
        # common closed ones so the output looks realistic.
        open_ports = list(getattr(host_obj, "open_ports", []) or [])
        extra = [p for p in [21, 22, 23, 25, 80, 110, 443, 3306, 3389, 8080]
                 if p not in open_ports][:6]
        scan_ports = sorted(set(open_ports + extra))

    # Scan each port via the shared engine.
    for port in scan_ports:
        state = engine.scan_port(host_obj.hostname, host_obj.hostname, port)
        if state == PortState.OPEN:
            state_str = "open"
        elif state == PortState.FILTERED:
            state_str = "filtered"
        else:
            state_str = "closed"

        svc_name = (getattr(host_obj, "services", {}) or {}).get(port, "")
        if not svc_name:
            cat = SERVICE_CATALOGUE.get(port)
            svc_name = cat["name"] if cat else "unknown"

        version_str = ""
        if args.service_version and state_str == "open":
            version_str = _version_string(port, svc_name)

        # Only include open/filtered ports in results (matches real Nmap
        # default behaviour — closed ports are omitted unless there are
        # very few results).
        if state_str in ("open", "filtered"):
            result.ports.append(PortResult(
                port=port, protocol="tcp", state=state_str,
                service=svc_name, version=version_str,
            ))

    # OS detection.
    if args.os_detect:
        fp = _os_fingerprint(getattr(host_obj, "os", "") or "")
        if fp:
            result.os_name = fp["os_name"]
            result.os_detail = fp["os_detail"]
            result.os_accuracy = fp["os_accuracy"]

    return result


def _version_string(port: int, service: str) -> str:
    """Build the version column for ``-sV`` output."""
    key = (port, service)
    entry = SERVICE_VERSIONS.get(key)
    if entry is None:
        return ""
    parts = [entry.get("product", "")]
    if entry.get("version"):
        parts.append(entry["version"])
    if entry.get("extra"):
        parts.append(entry["extra"])
    return " ".join(parts)


def _os_fingerprint(os_str: str) -> Optional[dict[str, str]]:
    """First-match lookup against OS_FINGERPRINTS."""
    lower = os_str.lower()
    for substring, fp in OS_FINGERPRINTS:
        if substring in lower:
            return fp
    return None


# ---------------------------------------------------------------------------
# Formatter — renders ScanResult as Nmap-style text
# ---------------------------------------------------------------------------
def format_output(result: ScanResult, args: NmapArgs,
                  scan_time: float = 0.42) -> str:
    """Produce output that closely resembles real ``nmap`` CLI output."""
    lines: list[str] = []

    lines.append(f"Starting Nmap 7.94 ( https://nmap.org ) at 2026-07-17 09:15 UTC")
    if args.syn_scan:
        lines.append("Initiating SYN Stealth Scan")
    lines.append(f"Nmap scan report for {result.target} ({result.ip})")

    if not result.host_up:
        lines.append("Note: Host seems down. If it is really up, but blocking our ping")
        lines.append("probes, try -Pn")
        lines.append("")
        lines.append(f"Nmap done: 1 IP address (0 hosts up) scanned in {scan_time:.2f} seconds")
        return "\n".join(lines)

    lines.append(f"Host is up ({result.latency_ms / 1000:.4f}s latency).")

    if result.ports:
        # Closed-port summary (the ports we scanned but didn't list).
        scanned = len(args.ports) if args.ports else (
            len(FAST_PORTS) if args.fast else 1000)
        not_shown = max(0, scanned - len(result.ports))
        if not_shown > 0:
            lines.append(f"Not shown: {not_shown} closed tcp ports (conn-refused)")
        lines.append("")

        # Port table header.
        if args.service_version:
            lines.append(f"{'PORT':<12}{'STATE':<10}{'SERVICE':<16}VERSION")
        else:
            lines.append(f"{'PORT':<12}{'STATE':<10}SERVICE")

        for pr in sorted(result.ports, key=lambda p: p.port):
            port_str = f"{pr.port}/{pr.protocol}"
            if args.service_version and pr.version:
                lines.append(f"{port_str:<12}{pr.state:<10}{pr.service:<16}{pr.version}")
            else:
                lines.append(f"{port_str:<12}{pr.state:<10}{pr.service}")
    else:
        lines.append("All scanned ports are closed or filtered.")

    # MAC address.
    if result.mac:
        mac_upper = result.mac.upper().replace(":", ":")
        lines.append(f"MAC Address: {mac_upper}")

    # OS detection.
    if args.os_detect and result.os_detail:
        lines.append("")
        lines.append("OS detection performed.")
        lines.append(f"OS details: {result.os_detail}")
        lines.append(f"Aggressive OS guesses: {result.os_detail} ({result.os_accuracy}%)")

    # Footer.
    lines.append("")
    lines.append(f"Nmap done: 1 IP address (1 host up) scanned in {scan_time:.2f} seconds")

    return "\n".join(lines)
