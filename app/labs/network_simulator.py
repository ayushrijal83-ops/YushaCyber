"""Networking simulator — a Lab Engine plugin (YC-013.0).

THE ONLY FILE IN THE CODEBASE THAT CONTAINS NETWORKING LOGIC. The engine,
the service layer, the routes and the models know nothing about `ping` or
`traceroute`; they only know "a simulator". Delete this file and the engine
still runs — the same architecture test the Linux simulator passes.

=== SAFETY ===
Nothing here executes. No sockets, no subprocess, no DNS lookups, no real
network I/O of any kind. `ping` walks a Python dict; `nslookup` reads a
seeded record table. Every response is computed from in-memory simulated
state — a pure function of (state, action).

=== VIRTUAL NETWORK ===
    netlab-pc (you)   192.168.1.10/24  eth0
      └── gateway.local   192.168.1.1   (router; the way out)
            ├── server.local   192.168.1.20  (web server, :80 :443)
            ├── db.local       192.168.1.30  (database server, :3306)
            └── INTERNET
                  ├── dns.google    8.8.8.8       (DNS resolver, :53)
                  └── example.com   93.184.216.34 (public web, :80 :443)

=== SUPPORTED COMMANDS ===
    ping  ip (addr|a|route|r)  hostname  ifconfig  arp  route  netstat
    nslookup  traceroute  curl  help  clear
Anything else returns a simulated "command not found".
"""

from __future__ import annotations

from typing import Any, Optional

from app.labs.registry import register_simulator
from app.labs.simulator_base import (
    CAP_TERMINAL,
    Action,
    ActionResult,
    Simulator,
)

# ---------------------------------------------------------------------------
# Topology — pure data. This is the simulator's "world", the same way the
# Linux simulator owns its process table. Labs never execute against it;
# commands merely read it.
# ---------------------------------------------------------------------------
_HOSTNAME = "netlab-pc"
_MY_IP = "192.168.1.10"
_NETMASK = "255.255.255.0"
_CIDR = 24
_MY_MAC = "02:42:c0:a8:01:0a"
_GATEWAY = "192.168.1.1"
_DNS = "8.8.8.8"
_BROADCAST = "192.168.1.255"

#: ip -> device record. ``local`` devices sit on 192.168.1.0/24 (1 hop);
#: everything else is reached through the gateway (3 hops).
_DEVICES: dict[str, dict[str, Any]] = {
    _GATEWAY: {
        "name": "gateway.local", "mac": "02:42:c0:a8:01:01",
        "local": True, "ports": {53: "domain", 80: "http"},
        "role": "Gateway / Router",
    },
    "192.168.1.20": {
        "name": "server.local", "mac": "02:42:c0:a8:01:14",
        "local": True, "ports": {80: "http", 443: "https"},
        "role": "Web Server",
    },
    "192.168.1.30": {
        "name": "db.local", "mac": "02:42:c0:a8:01:1e",
        "local": True, "ports": {3306: "mysql"},
        "role": "Database Server",
    },
    _DNS: {
        "name": "dns.google", "mac": None,
        "local": False, "ports": {53: "domain"},
        "role": "DNS Server",
    },
    "93.184.216.34": {
        "name": "example.com", "mac": None,
        "local": False, "ports": {80: "http", 443: "https"},
        "role": "Internet Host",
    },
}

#: DNS zone the simulated resolver answers from.
_DNS_RECORDS: dict[str, str] = {
    "gateway.local": _GATEWAY,
    "server.local": "192.168.1.20",
    "db.local": "192.168.1.30",
    "dns.google": _DNS,
    "example.com": "93.184.216.34",
    "netlab-pc": _MY_IP,
    "localhost": "127.0.0.1",
}

#: Deterministic latency samples (ms) — pure function, no random().
_LOCAL_TIMES = ("0.412", "0.386", "0.401", "0.395")
_WAN_TIMES = ("11.802", "11.654", "12.013", "11.788")

_HTTP_PAGES: dict[str, str] = {
    "server.local": (
        "<!DOCTYPE html>\n<html>\n<head><title>YushaCyber Internal Server</title></head>\n"
        "<body>\n  <h1>It works!</h1>\n"
        "  <p>server.local — internal web server on 192.168.1.20.</p>\n"
        "  <!-- YC{network_track_http} -->\n</body>\n</html>"
    ),
    "example.com": (
        "<!DOCTYPE html>\n<html>\n<head><title>Example Domain</title></head>\n"
        "<body>\n  <h1>Example Domain</h1>\n"
        "  <p>This domain is for use in illustrative examples in documents.</p>\n"
        "</body>\n</html>"
    ),
    "gateway.local": (
        "<!DOCTYPE html>\n<html><head><title>Router Admin</title></head>\n"
        "<body><h1>gateway.local</h1><p>Router administration portal.</p></body></html>"
    ),
}


def _key(value: str) -> str:
    """Flag-safe key: state_flag paths split on '.', so dots become '_'.

    '192.168.1.20' -> '192_168_1_20', 'example.com' -> 'example_com'.
    """
    return (value or "").replace(".", "_")


def _resolve_host(target: str) -> tuple[Optional[str], Optional[str]]:
    """(ip, display_name) for a target that may be a name or an IP."""
    target = (target or "").strip().rstrip(".")
    if not target:
        return None, None
    if target in _DNS_RECORDS:                       # name -> ip
        return _DNS_RECORDS[target], target
    if target == _MY_IP or target == "127.0.0.1":
        return target, _HOSTNAME if target == _MY_IP else "localhost"
    if target in _DEVICES:                           # already an ip
        return target, _DEVICES[target]["name"]
    # A syntactically plausible IPv4 that isn't in the topology is
    # "unreachable"; anything else fails name resolution.
    parts = target.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return target, target                         # unreachable ip
    return None, None                                 # NXDOMAIN


def _host_from_url(url: str) -> str:
    """Extract the host portion of a curl target ('http://a.b/x' -> 'a.b')."""
    host = (url or "").strip()
    for scheme in ("http://", "https://"):
        if host.startswith(scheme):
            host = host[len(scheme):]
            break
    return host.split("/", 1)[0].split(":", 1)[0].rstrip(".")


class _Cmd:
    """Parsed command: program + arguments. Parsing only — never execution."""

    def __init__(self, raw: str) -> None:
        self.raw = (raw or "").strip()
        parts = self.raw.split()
        self.program = parts[0] if parts else ""
        self.args = parts[1:] if len(parts) > 1 else []

    def positional(self) -> list[str]:
        return [a for a in self.args if not a.startswith("-")]


@register_simulator
class NetworkSimulator(Simulator):
    """Simulated network stack over a virtual, in-memory topology."""

    key = "network"

    # -- contract -------------------------------------------------------
    def capabilities(self) -> set[str]:
        return {CAP_TERMINAL}

    def bootstrap(self, lab: Any, content: dict[str, Any]) -> dict[str, Any]:
        """Fresh state for a networking lab.

        The topology is simulator-owned data (like the Linux simulator's
        process table); ``content`` is accepted for engine symmetry and
        future per-lab topology overrides, but nothing in it is required.
        """
        return self.new_state_envelope(
            hostname=_HOSTNAME,
            interfaces={
                "eth0": {"ip": _MY_IP, "netmask": _NETMASK, "cidr": _CIDR,
                         "mac": _MY_MAC, "up": True},
                "lo": {"ip": "127.0.0.1", "netmask": "255.0.0.0", "cidr": 8,
                       "mac": None, "up": True},
            },
            gateway=_GATEWAY,
            dns=_DNS,
            connected=True,
            # ARP cache starts EMPTY on purpose — talking to a device
            # (ping/curl) populates it, which is what Lab 3 teaches.
            arp={},
            # Established connections shown by netstat (grow after curl).
            connections=[],
            routes=[
                {"dest": "0.0.0.0", "gateway": _GATEWAY,
                 "genmask": "0.0.0.0", "flags": "UG", "iface": "eth0"},
                {"dest": "192.168.1.0", "gateway": "0.0.0.0",
                 "genmask": _NETMASK, "flags": "U", "iface": "eth0"},
            ],
            history=[],
            flags={},
            prompt=f"student@{_HOSTNAME}:~$ ",
        )

    def prompt(self, state: dict[str, Any]) -> str:
        return f"student@{state.get('hostname', _HOSTNAME)}:~$ "

    def welcome(self, state: dict[str, Any]) -> str:
        return (
            "YushaCyber simulated network shell.\n"
            "This is a safe simulation — no packets leave this page.\n"
            f"You are {_HOSTNAME} ({_MY_IP}) on 192.168.1.0/24.\n"
            "Type 'help' to see available commands.\n"
        )

    def describe_ui(self) -> dict[str, Any]:
        return {
            "capabilities": sorted(self.capabilities()),
            "title": f"student@{_HOSTNAME} — simulated network shell",
        }

    def status_panel(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        """Key/value pairs the workspace sidebar renders (engine-agnostic)."""
        eth0 = (state.get("interfaces") or {}).get("eth0", {})
        connected = bool(state.get("connected", True))
        return [
            {"label": "Current Host", "value": state.get("hostname", _HOSTNAME)},
            {"label": "Current IP", "value": eth0.get("ip", _MY_IP)},
            {"label": "Gateway", "value": state.get("gateway", _GATEWAY)},
            {"label": "DNS", "value": state.get("dns", _DNS)},
            {"label": "Status",
             "value": "Connected" if connected else "Disconnected",
             "state": "ok" if connected else "err"},
        ]

    # -- dispatch ---------------------------------------------------------
    def handle(self, state: dict[str, Any], action: Action) -> ActionResult:
        """Pure: (state, action) -> ActionResult. No side effects, no I/O."""
        if action.type != "command":
            return ActionResult(
                output="This lab only accepts terminal commands.",
                new_state=state,
            )

        state = dict(state)                     # never mutate the caller's dict
        state["arp"] = dict(state.get("arp", {}))
        state["flags"] = dict(state.get("flags", {}))
        state["connections"] = list(state.get("connections", []))

        cmd = _Cmd(action.command)
        if not cmd.program:
            return ActionResult(output="", new_state=state)

        history = list(state.get("history", []))[-99:]
        history.append(cmd.raw)
        state["history"] = history

        handler = {
            "ping": self._ping,
            "ip": self._ip,
            "hostname": self._hostname,
            "ifconfig": self._ifconfig,
            "arp": self._arp,
            "route": self._route,
            "netstat": self._netstat,
            "nslookup": self._nslookup,
            "traceroute": self._traceroute,
            "tracert": self._traceroute,       # windows-habit friendly alias
            "curl": self._curl,
            "help": self._help,
            "clear": self._clear,
        }.get(cmd.program)

        if handler is None:
            return ActionResult(
                output=f"{cmd.program}: command not found",
                new_state=state,
            )

        result = handler(state, cmd)
        result.new_state["prompt"] = self.prompt(result.new_state)
        return result

    # -- helpers (pure) ---------------------------------------------------
    @staticmethod
    def _learn_arp(state: dict, ip: str) -> None:
        """Talking to a LAN device teaches the ARP cache its MAC."""
        device = _DEVICES.get(ip)
        if device and device["local"] and device["mac"]:
            state["arp"][ip] = device["mac"]
        if ip == _GATEWAY or (device and not device["local"]):
            # Any off-LAN traffic goes through the gateway, so its MAC is
            # learned too.
            state["arp"][_GATEWAY] = _DEVICES[_GATEWAY]["mac"]

    @staticmethod
    def _set_flag(state: dict, group: str, key: str) -> None:
        flags = state["flags"]
        bucket = dict(flags.get(group, {}))
        bucket[_key(key)] = True
        flags[group] = bucket

    # -- command handlers (all pure) ---------------------------------------
    def _hostname(self, state: dict, cmd: _Cmd) -> ActionResult:
        return ActionResult(
            output=state.get("hostname", _HOSTNAME),
            new_state=state,
            events=[{"type": "hostname"}],
        )

    def _ping(self, state: dict, cmd: _Cmd) -> ActionResult:
        targets = cmd.positional()
        if not targets:
            return ActionResult(
                output="ping: usage error: Destination address required",
                new_state=state,
            )
        target = targets[0]
        ip, name = _resolve_host(target)
        if ip is None:
            return ActionResult(
                output=f"ping: {target}: Name or service not known",
                new_state=state,
                events=[{"type": "ping", "target": target, "reachable": False}],
            )

        reachable = ip in _DEVICES or ip in (_MY_IP, "127.0.0.1")
        if not reachable:
            lines = [f"PING {name} ({ip}) 56(84) bytes of data."]
            lines += [f"From {_MY_IP} icmp_seq={i} Destination Host Unreachable"
                      for i in (1, 2, 3, 4)]
            lines += [f"--- {name} ping statistics ---",
                      "4 packets transmitted, 0 received, +4 errors, "
                      "100% packet loss, time 3062ms"]
            return ActionResult(
                output="\n".join(lines),
                new_state=state,
                events=[{"type": "ping", "target": ip, "name": name,
                         "reachable": False}],
            )

        device = _DEVICES.get(ip, {})
        local = device.get("local", True)
        ttl = 64 if local else 56
        times = _LOCAL_TIMES if local else _WAN_TIMES
        self._learn_arp(state, ip)
        self._set_flag(state, "pinged", ip)
        if name != ip:
            self._set_flag(state, "pinged", name)

        lines = [f"PING {name} ({ip}) 56(84) bytes of data."]
        lines += [
            f"64 bytes from {ip}: icmp_seq={i} ttl={ttl} time={t} ms"
            for i, t in enumerate(times, start=1)
        ]
        lines += [
            f"--- {name} ping statistics ---",
            "4 packets transmitted, 4 received, 0% packet loss, time 3004ms",
        ]
        return ActionResult(
            output="\n".join(lines),
            new_state=state,
            events=[{"type": "ping", "target": ip, "name": name,
                     "reachable": True}],
        )

    def _ip(self, state: dict, cmd: _Cmd) -> ActionResult:
        obj = cmd.args[0] if cmd.args else ""
        if obj in ("addr", "a", "address"):
            state["flags"]["ip_addr_shown"] = True
            eth0 = state["interfaces"]["eth0"]
            lo = state["interfaces"]["lo"]
            output = "\n".join([
                "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN",
                f"    inet {lo['ip']}/{lo['cidr']} scope host lo",
                "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP",
                f"    link/ether {eth0['mac']} brd ff:ff:ff:ff:ff:ff",
                f"    inet {eth0['ip']}/{eth0['cidr']} brd {_BROADCAST} scope global eth0",
            ])
            return ActionResult(output=output, new_state=state,
                                events=[{"type": "ip_addr"}])
        if obj in ("route", "r"):
            output = "\n".join([
                f"default via {state['gateway']} dev eth0 proto static",
                f"192.168.1.0/24 dev eth0 proto kernel scope link src {_MY_IP}",
            ])
            return ActionResult(output=output, new_state=state,
                                events=[{"type": "ip_route"}])
        if not obj:
            return ActionResult(
                output='Usage: ip [ OPTIONS ] OBJECT { COMMAND }\n'
                       'where  OBJECT := { addr | route }',
                new_state=state,
            )
        return ActionResult(
            output=f'Object "{obj}" is unknown, try "ip help".',
            new_state=state,
        )

    def _ifconfig(self, state: dict, cmd: _Cmd) -> ActionResult:
        state["flags"]["ifconfig_shown"] = True
        eth0 = state["interfaces"]["eth0"]
        lo = state["interfaces"]["lo"]
        output = "\n".join([
            "eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500",
            f"        inet {eth0['ip']}  netmask {eth0['netmask']}  broadcast {_BROADCAST}",
            f"        ether {eth0['mac']}  txqueuelen 1000  (Ethernet)",
            "        RX packets 4821  bytes 5031842 (5.0 MB)",
            "        TX packets 3210  bytes 402193 (402.1 KB)",
            "",
            "lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536",
            f"        inet {lo['ip']}  netmask {lo['netmask']}",
            "        loop  txqueuelen 1000  (Local Loopback)",
        ])
        return ActionResult(output=output, new_state=state,
                            events=[{"type": "ifconfig"}])

    def _arp(self, state: dict, cmd: _Cmd) -> ActionResult:
        entries = state.get("arp", {})
        if not entries:
            return ActionResult(
                output="arp: the ARP cache is empty — communicate with a "
                       "device first (try: ping 192.168.1.1)",
                new_state=state,
                events=[{"type": "arp", "entries": 0, "populated": False}],
            )
        lines = []
        for ip in sorted(entries):
            name = _DEVICES.get(ip, {}).get("name", "?")
            lines.append(f"{name} ({ip}) at {entries[ip]} [ether] on eth0")
        return ActionResult(
            output="\n".join(lines),
            new_state=state,
            events=[{"type": "arp", "entries": len(entries),
                     "populated": True}],
        )

    def _route(self, state: dict, cmd: _Cmd) -> ActionResult:
        header = (
            "Kernel IP routing table\n"
            "Destination     Gateway         Genmask         Flags Metric Ref    Use Iface"
        )
        rows = [
            f"{r['dest']:<15} {r['gateway']:<15} {r['genmask']:<15} "
            f"{r['flags']:<5} 100    0        0 {r['iface']}"
            for r in state.get("routes", [])
        ]
        return ActionResult(
            output="\n".join([header] + rows),
            new_state=state,
            events=[{"type": "route"}],
        )

    def _netstat(self, state: dict, cmd: _Cmd) -> ActionResult:
        lines = [
            "Active Internet connections (servers and established)",
            "Proto Recv-Q Send-Q Local Address           Foreign Address         State",
            "tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN",
            "udp        0      0 0.0.0.0:68              0.0.0.0:*",
        ]
        for conn in state.get("connections", []):
            lines.append(
                f"tcp        0      0 {conn['local']:<23} {conn['remote']:<23} "
                f"{conn['state']}"
            )
        return ActionResult(
            output="\n".join(lines),
            new_state=state,
            events=[{"type": "netstat"}],
        )

    def _nslookup(self, state: dict, cmd: _Cmd) -> ActionResult:
        targets = cmd.positional()
        if not targets:
            return ActionResult(
                output="nslookup: usage: nslookup NAME", new_state=state
            )
        name = targets[0].rstrip(".")
        dns = state.get("dns", _DNS)
        header = f"Server:\t\t{dns}\nAddress:\t{dns}#53\n"
        ip = _DNS_RECORDS.get(name)
        if ip is None:
            return ActionResult(
                output=header + f"\n** server can't find {name}: NXDOMAIN",
                new_state=state,
                events=[{"type": "nslookup", "domain": name, "resolved": False}],
            )
        self._set_flag(state, "resolved", name)
        return ActionResult(
            output=header + f"\nNon-authoritative answer:\nName:\t{name}\nAddress: {ip}",
            new_state=state,
            events=[{"type": "nslookup", "domain": name, "resolved": True}],
        )

    def _traceroute(self, state: dict, cmd: _Cmd) -> ActionResult:
        targets = cmd.positional()
        if not targets:
            return ActionResult(
                output="Usage: traceroute HOST", new_state=state
            )
        target = targets[0]
        ip, name = _resolve_host(target)
        if ip is None:
            return ActionResult(
                output=f"traceroute: unknown host {target}",
                new_state=state,
                events=[{"type": "traceroute", "target": target,
                         "reachable": False}],
            )
        device = _DEVICES.get(ip)
        header = (f"traceroute to {name} ({ip}), 30 hops max, "
                  "60 byte packets")
        gw_name = _DEVICES[_GATEWAY]["name"]

        if ip in (_MY_IP, "127.0.0.1"):
            hops = [f" 1  {name} ({ip})  0.041 ms  0.038 ms  0.036 ms"]
        elif device and device["local"]:
            self._learn_arp(state, ip)
            hops = [f" 1  {name} ({ip})  0.412 ms  0.398 ms  0.401 ms"]
        elif device:  # internet host: pc -> gateway -> isp -> target
            self._learn_arp(state, ip)
            hops = [
                f" 1  {gw_name} ({_GATEWAY})  0.311 ms  0.302 ms  0.298 ms",
                " 2  isp-core.net (10.10.0.1)  4.211 ms  4.187 ms  4.190 ms",
                f" 3  {name} ({ip})  11.802 ms  11.654 ms  11.788 ms",
            ]
        else:  # plausible but unreachable ip
            hops = [
                f" 1  {gw_name} ({_GATEWAY})  0.311 ms  0.302 ms  0.298 ms",
                " 2  * * *",
                " 3  * * *",
            ]
        self._set_flag(state, "traced", ip)
        return ActionResult(
            output="\n".join([header] + hops),
            new_state=state,
            events=[{"type": "traceroute", "target": ip, "name": name,
                     "reachable": device is not None}],
        )

    def _curl(self, state: dict, cmd: _Cmd) -> ActionResult:
        targets = cmd.positional()
        if not targets:
            return ActionResult(
                output="curl: try 'curl http://server.local'", new_state=state
            )
        host = _host_from_url(targets[0])
        ip, name = _resolve_host(host)
        if ip is None:
            return ActionResult(
                output=f"curl: (6) Could not resolve host: {host}",
                new_state=state,
                events=[{"type": "curl", "host": host, "status": 0}],
            )
        device = _DEVICES.get(ip)
        if device is None and ip not in (_MY_IP, "127.0.0.1"):
            return ActionResult(
                output=f"curl: (7) Failed to connect to {host} port 80: "
                       "No route to host",
                new_state=state,
                events=[{"type": "curl", "host": host, "status": 0}],
            )
        if device is not None and 80 not in device["ports"] \
                and 443 not in device["ports"]:
            return ActionResult(
                output=f"curl: (7) Failed to connect to {host} port 80: "
                       "Connection refused",
                new_state=state,
                events=[{"type": "curl", "host": host, "status": 0}],
            )

        page = _HTTP_PAGES.get(name) or _HTTP_PAGES.get(host) or (
            "<!DOCTYPE html>\n<html><body><h1>200 OK</h1></body></html>"
        )
        self._learn_arp(state, ip)
        self._set_flag(state, "curled", name)
        conn = {"local": f"{_MY_IP}:52210", "remote": f"{ip}:80",
                "state": "ESTABLISHED"}
        if conn not in state["connections"]:
            state["connections"].append(conn)
        return ActionResult(
            output=page,
            new_state=state,
            events=[{"type": "curl", "host": name, "status": 200}],
        )

    def _help(self, state: dict, cmd: _Cmd) -> ActionResult:
        output = "\n".join([
            "Available commands (all simulated):",
            "  hostname              show this machine's name",
            "  ip addr | ip a        show interface addresses",
            "  ip route | ip r       show the routing table (iproute2 style)",
            "  ifconfig              show interfaces (classic style)",
            "  ping HOST             test reachability (name or IP)",
            "  traceroute HOST       show the path packets take",
            "  nslookup NAME         resolve a name via DNS",
            "  arp                   show the ARP cache (IP -> MAC)",
            "  route                 show the kernel routing table",
            "  netstat               show listening ports and connections",
            "  curl URL              fetch a web page",
            "  clear                 clear the screen",
            "",
            "Known hosts: gateway.local, server.local, db.local, "
            "dns.google, example.com",
        ])
        return ActionResult(output=output, new_state=state,
                            events=[{"type": "help"}])

    def _clear(self, state: dict, cmd: _Cmd) -> ActionResult:
        return ActionResult(output="", new_state=state, clear=True)
