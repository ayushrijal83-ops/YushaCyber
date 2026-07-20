"""Interactive multi-host networking simulator (YC-026.0).

Foundation for every future networking lab (Nmap, Wireshark, packet
analysis, firewall labs, routing labs, SOC labs). Design goals:

  · **Reuse everything.** Plugs into the existing Simulator base
    (:mod:`app.labs.simulator_base`), the SimulatorRegistry, the
    validator/objective engine, XP awards and achievement unlocks --
    unchanged. The engine still calls one ``handle(state, action)`` per
    interaction; the difference is that state is a *dict of per-host
    envelopes* instead of a single-host envelope, and each command
    carries a ``host`` field so it addresses the right device.

  · **Modular & extensible.** A concrete simulator subclasses
    :class:`MultiHostSimulator`, declares its topology as data
    (routers/switches/PCs/servers, their addresses, the links between
    them), and gets working ``ipconfig``/``ping``/``traceroute``/etc.
    for free. New device types (firewall today, SOC endpoint tomorrow)
    just extend the topology data and, if needed, override
    ``_execute_command`` for device-class-specific behaviour.

  · **Pure functions of state.** No sockets, no subprocess, no
    filesystem. Every reply is derived from the seeded topology and
    the in-memory state envelope.

The concrete simulator defined here is :class:`InteractiveNetworkSimulator`
(``key="net-interactive"``) with the topology mandated by the ticket:
Internet --- Router --- Switch --- {PC-1, PC-2, Web Server, DB Server}.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from app.labs.registry import register_simulator
from app.labs.simulator_base import (
    CAP_TERMINAL,
    Action,
    ActionResult,
    Simulator,
)


# ---------------------------------------------------------------------------
# Topology data model
# ---------------------------------------------------------------------------
@dataclass
class Host:
    """One device in the simulated network.

    Everything a host needs to answer commands is captured here so a
    subclass can build a network entirely as data.
    """

    hostname: str            # displayed name (e.g. "pc-1", "web-server")
    label: str               # human display name (e.g. "PC-1")
    device_type: str         # router | switch | pc | server | firewall
    os: str                  # displayed OS string
    ip: str = ""             # primary IP (empty for a pure L2 switch)
    mac: str = ""            # primary MAC
    gateway: str = ""        # default gateway
    dns: str = "8.8.8.8"     # DNS
    interface: str = "eth0"  # interface name
    open_ports: list[int] = field(default_factory=list)
    services: dict[int, str] = field(default_factory=dict)


def _is_windows(host: "Host") -> bool:
    """True if the host runs a Windows OS (used by prompt + shell commands).

    We look at the OS string rather than the device_type because a PC or
    a server can be either flavour, and the topology data is the source
    of truth."""
    return "windows" in (host.os or "").lower()


def _broadcast(ip: str) -> str:
    """Infer the /24 broadcast address from a dotted-quad IP.
    Returns '—' for empty/invalid IPs."""
    if not ip or ip.count(".") != 3:
        return "—"
    parts = ip.split(".")
    return f"{parts[0]}.{parts[1]}.{parts[2]}.255"


# ---------------------------------------------------------------------------
# Multi-host base
# ---------------------------------------------------------------------------
class MultiHostSimulator(Simulator):
    """A simulator that hosts *many* devices in one session.

    Subclasses declare :attr:`topology` (list of :class:`Host`) and
    :attr:`links` (list of ``(hostname_a, hostname_b)`` pairs). The base
    then supplies device selection, per-host state envelopes, and a
    default command dispatch table so all common commands work out of
    the box.

    The action contract stays 100% compatible with the single-host
    engine — every action just carries an optional ``host`` field
    telling us which device the terminal is currently attached to.
    """

    #: Concrete topology, filled by subclasses.
    topology: list[Host] = []
    #: Bidirectional links. A switch appearing in the pair implies the
    #: hosts on both sides can reach each other.
    links: list[tuple[str, str]] = []

    capabilities_set: tuple[str, ...] = (CAP_TERMINAL,)

    # ------------------------------------------------------------------
    # Simulator interface
    # ------------------------------------------------------------------
    def capabilities(self) -> list[str]:
        return list(self.capabilities_set)

    def bootstrap(self, lab: Any, content: dict[str, Any]) -> dict[str, Any]:
        """Fresh session state: per-host history + which host is selected."""
        return {
            # ``sim`` is required by session_manager.load_state so it can
            # detect state written by a different simulator; without it,
            # every action would re-bootstrap and lose the selected host.
            "sim": self.key,
            "selected": self._default_host(),
            "hosts": {h.hostname: self._new_host_state(h) for h in self.topology},
            "flags": {},
        }

    def prompt(self, state: dict[str, Any]) -> str:
        host = self._get_host(state.get("selected", self._default_host()))
        if host is None:
            return "$ "
        # YC-026.2 — Windows devices get a native-feeling cmd.exe prompt.
        if _is_windows(host):
            return f"C:\\Users\\Student> "
        # Linux/router/switch keep the "student@<host>:~$" convention.
        return f"student@{host.hostname}:~$ "

    def welcome(self, state: dict[str, Any]) -> str:
        return (
            "Interactive Networking Simulator (simulated only).\n"
            f"Devices: {', '.join(h.label for h in self.topology)}.\n"
            "Click a device on the map to switch to its terminal.\n"
            "Type `help` for available commands."
        )

    def describe_ui(self) -> dict[str, Any]:
        """Payload used by the frontend to draw the topology diagram."""
        return {
            "title": "Interactive Network — select a device",
            "topology": {
                "nodes": [
                    {
                        "hostname": h.hostname,
                        "label": h.label,
                        "device_type": h.device_type,
                        "ip": h.ip,
                        "os": h.os,
                    }
                    for h in self.topology
                ],
                "links": [{"a": a, "b": b} for a, b in self.links],
            },
        }

    def status_panel(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        selected = state.get("selected", self._default_host())
        host = self._get_host(selected)
        if host is None:
            return []
        connected = ", ".join(sorted(self._neighbours_of(selected))) or "—"
        return [
            {"label": "Current Host", "value": host.label},
            {"label": "IP Address", "value": host.ip or "—"},
            {"label": "MAC Address", "value": host.mac or "—"},
            {"label": "Gateway", "value": host.gateway or "—"},
            {"label": "OS", "value": host.os},
            {"label": "Connected", "value": connected},
            {"label": "Status", "value": "Online", "state": "ok"},
        ]

    # ------------------------------------------------------------------
    # Action handling
    # ------------------------------------------------------------------
    def handle(self, state: dict[str, Any], action: Action) -> ActionResult:
        """Dispatch by action type; unknown types are a no-op."""
        state = dict(state) if state else self.bootstrap(None, {})
        if not state.get("hosts"):
            state = self.bootstrap(None, {})

        if action.type == "select":
            return self._select_host(state, action)
        if action.type == "command":
            return self._handle_command(state, action)
        return ActionResult(new_state=state)

    # -- select --------------------------------------------------------
    def _select_host(self, state: dict[str, Any], action: Action) -> ActionResult:
        target = action.payload.get("host") or action.payload.get("asset_id", "")
        if not self._get_host(target):
            return ActionResult(
                output=f"Unknown device: {target!r}",
                new_state=state,
                events=[{"type": "device_selection_failed", "host": target}],
            )
        state["selected"] = target
        # Track which hosts have been explored — the objective engine
        # can validate on this via state_flag or event_emitted.
        visited = set(state.get("flags", {}).get("visited", []))
        visited.add(target)
        state.setdefault("flags", {})["visited"] = sorted(visited)
        host = self._get_host(target)
        return ActionResult(
            output=f"Switched to {host.label} ({host.ip or 'no IP'})",
            new_state=state,
            events=[{"type": "device_selected", "host": target,
                     "device_type": host.device_type}],
            clear=True,
        )

    # -- command -------------------------------------------------------
    def _handle_command(self, state: dict[str, Any], action: Action) -> ActionResult:
        raw = action.command.strip()
        if not raw:
            return ActionResult(new_state=state)

        # Optional host override (e.g. an autograder submits directly).
        host_key = action.payload.get("host") or state.get("selected")
        host = self._get_host(host_key)
        if host is None:
            return ActionResult(output="No device selected.", new_state=state)

        # YC-026.5: count commands for the results screen.
        state.setdefault("flags", {})
        state["flags"]["commands_used"] = state["flags"].get("commands_used", 0) + 1

        parts = raw.split()
        cmd, args = parts[0].lower(), parts[1:]

        handler = self._dispatch_table().get(cmd)
        if handler is None:
            # Realistic error message per OS (YC-026.2).
            if _is_windows(host):
                msg = (f"'{cmd}' is not recognized as an internal or "
                       f"external command,\noperable program or batch file.")
            else:
                msg = f"{cmd}: command not found"
            return ActionResult(
                output=msg,
                new_state=state,
                events=[{"type": "unknown_command", "cmd": cmd}],
            )
        return handler(state, host, args)

    # ------------------------------------------------------------------
    # Command dispatch — subclasses may override any single command.
    # ------------------------------------------------------------------
    def _dispatch_table(self) -> dict[str, Callable]:
        return {
            "help":       self._cmd_help,
            "ipconfig":   self._cmd_ipconfig,
            "ifconfig":   self._cmd_ipconfig,
            "hostname":   self._cmd_hostname,
            "ping":       self._cmd_ping,
            "traceroute": self._cmd_traceroute,
            "tracert":    self._cmd_traceroute,
            "arp":        self._cmd_arp,
            "netstat":    self._cmd_netstat,
            "route":      self._cmd_route,
            "nslookup":   self._cmd_nslookup,
            "dig":        self._cmd_nslookup,
            "nmap":       self._cmd_nmap,
            "wireshark":  self._cmd_wireshark,
            "capture":    self._cmd_wireshark,
            "tshark":     self._cmd_wireshark,
            # YC-026.2 — foundation shell commands, device-context aware.
            "pwd":        self._cmd_pwd,
            "cd":         self._cmd_cd,
            "whoami":     self._cmd_whoami,
            "date":       self._cmd_date,
            "echo":       self._cmd_echo,
            "history":    self._cmd_history,
            "clear":      self._cmd_clear,
            "cls":        self._cmd_clear,   # Windows alias
            "exit":       self._cmd_exit,
        }

    # -- individual command handlers ----------------------------------
    def _cmd_help(self, state, host, args):
        text = (
            "Available (simulated) commands:\n"
            "  help                 show this list\n"
            "  hostname             print device hostname\n"
            "  pwd                  print current directory\n"
            "  whoami               print current user\n"
            "  date                 print date/time\n"
            "  echo <text>          print text\n"
            "  history              show shell-history hint\n"
            "  ipconfig / ifconfig  interface + IP + MAC + gateway + subnet\n"
            "  ping <host|ip>       reachability check (via engine)\n"
            "  traceroute <target>  hop path to the target (via engine)\n"
            "  nslookup <host|ip>   DNS lookup (forward + reverse)\n"
            "  nmap <target>        network scanner (try nmap -h)\n"
            "  wireshark [filter]   packet capture viewer\n"
            "  arp                  ARP cache for this device\n"
            "  netstat              listening ports + established connections\n"
            "  route                routing table\n"
            "  clear / cls          clear the terminal\n"
            "  exit                 detach from this device"
        )
        return ActionResult(output=text, new_state=state,
                            events=[{"type": "help_shown"}])

    def _cmd_hostname(self, state, host, args):
        state.setdefault("flags", {})["hostname_shown"] = True
        return ActionResult(output=host.hostname, new_state=state,
                            events=[{"type": "hostname", "host": host.hostname}])

    def _cmd_ipconfig(self, state, host, args):
        """Show interface details. Output format is OS-aware (YC-026.4):
        Windows shows ipconfig-style, Linux shows ifconfig-style."""
        # Subnet mask: infer /24 for any assigned IP (all our topologies
        # use /24). Future labs with multiple subnets can override.
        subnet = "255.255.255.0" if host.ip else "—"

        if _is_windows(host):
            text = (
                f"Windows IP Configuration\n"
                f"\n"
                f"Ethernet adapter {host.interface}:\n"
                f"\n"
                f"   Connection-specific DNS Suffix  . :\n"
                f"   IPv4 Address. . . . . . . . . . : {host.ip or 'unassigned'}\n"
                f"   Subnet Mask . . . . . . . . . . : {subnet}\n"
                f"   Default Gateway . . . . . . . . : {host.gateway or ''}\n"
                f"   DNS Servers . . . . . . . . . . : {host.dns}\n"
                f"   Physical Address. . . . . . . . : {(host.mac or '00:00:00:00:00:00').replace(':', '-').upper()}\n"
                f"   Media State . . . . . . . . . . : Media connected"
            )
        else:
            text = (
                f"{host.interface}: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n"
                f"        inet {host.ip or 'unassigned'}  netmask {subnet}  broadcast {_broadcast(host.ip)}\n"
                f"        ether {host.mac or '00:00:00:00:00:00'}  txqueuelen 1000\n"
                f"        RX packets 14832  bytes 12740158\n"
                f"        TX packets 9614   bytes 1148602\n"
                f"\n"
                f"  default gateway: {host.gateway or 'none'}\n"
                f"  dns: {host.dns}"
            )
        state.setdefault("flags", {}).setdefault("ipconfig_hosts", [])
        if host.hostname not in state["flags"]["ipconfig_hosts"]:
            state["flags"]["ipconfig_hosts"].append(host.hostname)
        return ActionResult(output=text, new_state=state,
                            events=[{"type": "ipconfig", "host": host.hostname,
                                     "ip": host.ip}])

    def _cmd_ping(self, state, host, args):
        if not args:
            return ActionResult(output="usage: ping <host or ip>", new_state=state)
        target = args[0]
        peer = self._resolve(target)

        # YC-026.3: route the packet through the shared engine instead of
        # doing a hand-rolled reachability probe here.
        from app.labs.net_engine import NetworkEngine, make_engine_from_devices, PacketStatus

        offline = tuple(state.get("flags", {}).get("offline", ()))
        engine: NetworkEngine = make_engine_from_devices(
            self.topology, self.links, offline=offline,
        )

        replies = engine.ping(host.hostname, peer.hostname, count=2) if peer else ()
        reachable = bool(replies and replies[0].status == PacketStatus.DELIVERED)

        if peer is None:
            output = f"ping: cannot resolve {target}: Name or service not known"
        elif reachable:
            lines = [f"PING {peer.hostname} ({peer.ip}) 56(84) bytes of data."]
            for r in replies:
                lines.append(
                    f"64 bytes from {peer.ip}: icmp_seq={r.sequence} "
                    f"ttl={r.ttl} time={r.latency_ms:.2f} ms"
                )
            lines.append("")
            lines.append(f"--- {peer.hostname} ping statistics ---")
            lines.append(f"{len(replies)} packets transmitted, {len(replies)} "
                         f"received, 0% packet loss")
            output = "\n".join(lines)
        elif replies and replies[0].status == PacketStatus.OFFLINE:
            output = f"From {host.ip}: Destination Host Unreachable (host offline)"
        else:
            output = f"From {host.ip}: Destination Host Unreachable"

        if peer is not None:
            self._learn_arp(state, host.hostname, peer)
            # YC-026.3: record the packets into a session-level capture
            # buffer so the future Wireshark simulator can read a real
            # packet feed instead of re-deriving it.
            self._capture(state, [r.packet for r in replies])

        pinged = state.setdefault("flags", {}).setdefault("pinged", [])
        if peer is not None and peer.hostname not in pinged:
            pinged.append(peer.hostname)
        return ActionResult(output=output, new_state=state,
                            events=[{"type": "ping",
                                     "from": host.hostname,
                                     "target": target,
                                     "resolved": peer.hostname if peer else None,
                                     "reachable": bool(reachable)}])

    def _cmd_traceroute(self, state, host, args):
        if not args:
            return ActionResult(output="usage: traceroute <host or ip>", new_state=state)
        target = args[0]
        peer = self._resolve(target)
        if peer is None:
            return ActionResult(output=f"traceroute: unknown host {target}",
                                new_state=state)

        from app.labs.net_engine import make_engine_from_devices
        offline = tuple(state.get("flags", {}).get("offline", ()))
        engine = make_engine_from_devices(self.topology, self.links, offline=offline)
        result = engine.traceroute(host.hostname, peer.hostname)

        if not result.hops:
            return ActionResult(
                output=f"traceroute to {peer.hostname} ({peer.ip}): no route",
                new_state=state,
                events=[{"type": "traceroute", "from": host.hostname,
                         "target": target, "reachable": False}])
        lines = [f"traceroute to {peer.hostname} ({peer.ip}), 30 hops max"]
        for row in result.hops:
            lines.append(f"{row.hop:>2}  {row.hostname} ({row.ip})  {row.latency_ms:.2f} ms")
        # Capture the per-hop TTL probes for the future Wireshark lane.
        trace_pkts = [
            engine.send_packet(host.hostname, peer.hostname,
                               protocol="icmp", ttl=row.hop)
            for row in result.hops
        ]
        self._capture(state, trace_pkts)
        return ActionResult(
            output="\n".join(lines), new_state=state,
            events=[{"type": "traceroute", "from": host.hostname,
                     "target": target,
                     "reachable": bool(result.reached_destination),
                     "hops": len(result.hops)}])

    def _cmd_arp(self, state, host, args):
        arp = state.get("flags", {}).get("arp", {}).get(host.hostname, {})
        if not arp:
            return ActionResult(
                output="No ARP entries yet — try pinging a neighbour first.",
                new_state=state,
                events=[{"type": "arp", "host": host.hostname, "entries": 0}])
        lines = ["Address          HWtype  HWaddress           Iface"]
        for ip, mac in sorted(arp.items()):
            lines.append(f"{ip:<16} ether   {mac:<20}{host.interface}")
        return ActionResult(
            output="\n".join(lines), new_state=state,
            events=[{"type": "arp", "host": host.hostname, "entries": len(arp),
                     "populated": True}])

    def _cmd_netstat(self, state, host, args):
        """Display listening ports + simulated established connections.

        YC-026.4 enhancements: fake PIDs, OS-aware formatting, simulated
        ESTABLISHED connections from peers that have pinged this host.
        All data routes through the shared SERVICE_CATALOGUE (YC-026.3).
        """
        from app.labs.net_engine import SERVICE_CATALOGUE

        lines = []
        if _is_windows(host):
            lines.append("Active Connections")
            lines.append("")
            lines.append(f"  {'Proto':<7}{'Local Address':<24}{'Foreign Address':<24}{'State':<16}{'PID'}")
        else:
            lines.append(f"{'Proto':<7}{'Local Address':<24}{'Foreign Address':<24}{'State':<16}{'PID/Program'}")

        # Listening ports (from the host's own configuration).
        base_pid = hash(host.hostname) % 9000 + 1000
        for i, port in enumerate(sorted(host.open_ports or [])):
            svc = host.services.get(port) or (
                SERVICE_CATALOGUE.get(port, {}).get("name", "-"))
            proto = SERVICE_CATALOGUE.get(port, {}).get("protocol", "tcp")
            local = f"{host.ip}:{port}"
            pid = base_pid + i * 4
            if _is_windows(host):
                lines.append(f"  {proto:<7}{local:<24}{'0.0.0.0:0':<24}{'LISTENING':<16}{pid}")
            else:
                lines.append(f"{proto:<7}{local:<24}{'0.0.0.0:*':<24}{'LISTEN':<16}{pid}/{svc}")

        # Simulated ESTABLISHED connections: if any peer has pinged THIS
        # host (tracked in the session ARP table), show a connection from
        # that peer to one of our listening ports.
        arp_table = state.get("flags", {}).get("arp", {})
        for peer_name, entries in arp_table.items():
            if peer_name == host.hostname:
                continue
            peer_host = self._get_host(peer_name)
            if peer_host is None or not host.open_ports:
                continue
            # Pick the first listening port as the connection target.
            target_port = sorted(host.open_ports)[0]
            svc = host.services.get(target_port) or (
                SERVICE_CATALOGUE.get(target_port, {}).get("name", "-"))
            local = f"{host.ip}:{target_port}"
            foreign = f"{peer_host.ip}:{49152 + hash(peer_name) % 1000}"
            pid = base_pid + len(host.open_ports) * 4 + 1
            if _is_windows(host):
                lines.append(f"  {'tcp':<7}{local:<24}{foreign:<24}{'ESTABLISHED':<16}{pid}")
            else:
                lines.append(f"{'tcp':<7}{local:<24}{foreign:<24}{'ESTABLISHED':<16}{pid}/{svc}")

        if len(lines) <= 2 and not host.open_ports:
            return ActionResult(output="No active connections.", new_state=state,
                                events=[{"type": "netstat", "host": host.hostname, "ports": []}])

        return ActionResult(
            output="\n".join(lines), new_state=state,
            events=[{"type": "netstat", "host": host.hostname,
                     "ports": sorted(host.open_ports or [])}])

    # -- wireshark (YC-028.0) --------------------------------------------
    def _cmd_wireshark(self, state, host, args):
        """Open the Wireshark capture viewer or apply a filter.

        Usage:
          wireshark              — show all captured packets
          wireshark http         — filter by protocol
          wireshark ip.addr == x — field filter
          wireshark clear        — clear the capture buffer
          wireshark stats        — show capture statistics
        """
        from app.labs.wireshark_engine import (
            PacketGenerator, FilterEngine,
        )

        packets_raw = state.get("flags", {}).get("packets", [])

        # Build host lookup from topology
        host_map = {
            h.hostname: {"ip": h.ip, "mac": h.mac, "hostname": h.hostname,
                         "os": h.os, "gateway": h.gateway,
                         "dns": h.dns, "open_ports": h.open_ports,
                         "services": h.services}
            for h in self.topology
        }

        if args and args[0].lower() == "clear":
            state.setdefault("flags", {})["packets"] = []
            return ActionResult(
                output="Capture buffer cleared.",
                new_state=state,
                events=[{"type": "wireshark", "action": "clear"}])

        if args and args[0].lower() == "stats":
            gen = PacketGenerator(host_map)
            enriched = gen.generate_capture(packets_raw, include_background=False)
            protos = {}
            for p in enriched:
                protos[p.protocol] = protos.get(p.protocol, 0) + 1
            lines = [f"Capture Statistics: {len(enriched)} packets"]
            for proto, count in sorted(protos.items(), key=lambda x: -x[1]):
                lines.append(f"  {proto:<12} {count}")
            return ActionResult(
                output="\n".join(lines),
                new_state=state,
                events=[{"type": "wireshark", "action": "stats",
                         "total_packets": len(enriched)}])

        # Generate enriched packets
        gen = PacketGenerator(host_map)
        enriched = gen.generate_capture(packets_raw, include_background=True)

        # Apply filter if provided
        filter_str = " ".join(args) if args else ""
        if filter_str:
            try:
                pred = FilterEngine.parse(filter_str)
                enriched = [p for p in enriched if pred(p)]
            except Exception:
                return ActionResult(
                    output=f"Invalid display filter: {filter_str}",
                    new_state=state,
                    events=[{"type": "wireshark", "action": "filter_error"}])

        # Format output like tshark text mode
        if not enriched:
            output = f"0 packets captured (filter: {filter_str or 'none'})"
        else:
            lines = [f"Capturing on 'eth0' — {len(enriched)} packets"
                     + (f" (filter: {filter_str})" if filter_str else "")]
            lines.append("")
            lines.append(f"{'No.':<6}{'Time':<12}{'Source':<18}{'Destination':<18}{'Proto':<8}{'Len':<6}{'Info'}")
            for p in enriched[:50]:  # Cap display at 50 rows
                lines.append(
                    f"{p.number:<6}{p.timestamp:<12.6f}{p.source_ip:<18}"
                    f"{p.dest_ip:<18}{p.protocol:<8}{p.length:<6}"
                    f"{p.info[:50]}")
            if len(enriched) > 50:
                lines.append(f"... and {len(enriched) - 50} more packets")
            lines.append("")
            lines.append(f"{len(enriched)} packets captured")
            output = "\n".join(lines)

        # Track for objectives
        state.setdefault("flags", {}).setdefault("wireshark_filters", [])
        if filter_str and filter_str not in state["flags"]["wireshark_filters"]:
            state["flags"]["wireshark_filters"].append(filter_str)

        protos_seen = list(set(p.protocol for p in enriched))
        return ActionResult(
            output=output,
            new_state=state,
            events=[{
                "type": "wireshark",
                "action": "capture",
                "filter": filter_str,
                "packet_count": len(enriched),
                "protocols": protos_seen,
                "has_packets": len(enriched) > 0,
            }])

    # -- nslookup (YC-026.4) -------------------------------------------
    def _cmd_nslookup(self, state, host, args):
        """Simulate DNS resolution against the virtual topology.

        Resolves hostnames → IPs and IPs → hostnames using the
        topology's device list as the authoritative zone. Uses the
        shared ``_resolve()`` lookup so it stays consistent with ping,
        traceroute, and every other command that resolves names.
        """
        if not args:
            return ActionResult(
                output="usage: nslookup <hostname or ip>",
                new_state=state)
        query = args[0]
        dns_server = host.dns or "8.8.8.8"

        target = self._resolve(query)
        if target is None:
            output = (
                f"Server:  {dns_server}\n"
                f"Address: {dns_server}#53\n"
                f"\n"
                f"** server can't find {query}: NXDOMAIN"
            )
            return ActionResult(
                output=output, new_state=state,
                events=[{"type": "nslookup", "host": host.hostname,
                         "query": query, "resolved": False}])

        # Forward lookup (hostname → IP) or reverse (IP → hostname).
        is_reverse = query == target.ip
        if is_reverse:
            answer = (
                f"Server:  {dns_server}\n"
                f"Address: {dns_server}#53\n"
                f"\n"
                f"{query}\tname = {target.hostname}"
            )
        else:
            answer = (
                f"Server:  {dns_server}\n"
                f"Address: {dns_server}#53\n"
                f"\n"
                f"Name:    {target.hostname}\n"
                f"Address: {target.ip or '(no IP assigned)'}"
            )

        state.setdefault("flags", {}).setdefault("nslookup_hosts", [])
        if target.hostname not in state["flags"]["nslookup_hosts"]:
            state["flags"]["nslookup_hosts"].append(target.hostname)

        return ActionResult(
            output=answer, new_state=state,
            events=[{"type": "nslookup", "host": host.hostname,
                     "query": query, "resolved": True,
                     "target": target.hostname, "ip": target.ip}])

    # -- nmap (YC-027.0) ------------------------------------------------
    def _cmd_nmap(self, state, host, args):
        """Simulated Nmap scan — parses flags, runs through the shared
        connectivity engine, formats output to look like real Nmap CLI.

        Everything is data-driven: port results come from ``scan_port``,
        service versions from ``SERVICE_VERSIONS``, OS fingerprints from
        ``OS_FINGERPRINTS``. No hardcoded terminal output.
        """
        from app.labs.nmap_simulator import (
            parse_nmap_args, run_scan, format_output,
        )
        from app.labs.net_engine import make_engine_from_devices

        nmap_args = parse_nmap_args(args)
        if nmap_args.error:
            if nmap_args.error == "no target specified":
                return ActionResult(
                    output="usage: nmap [options] <target>\n"
                           "  -sV  service/version detection\n"
                           "  -O   OS detection\n"
                           "  -A   aggressive (sV + O)\n"
                           "  -sS  SYN stealth scan\n"
                           "  -Pn  skip host discovery\n"
                           "  -p   port specification (e.g. -p 22,80,443)\n"
                           "  -F   fast scan (top 100 ports)\n"
                           "  -T4  timing template (0-5)",
                    new_state=state)
            return ActionResult(
                output=f"nmap: {nmap_args.error}",
                new_state=state)

        offline = tuple(state.get("flags", {}).get("offline", ()))
        engine = make_engine_from_devices(self.topology, self.links, offline=offline)

        outputs = []
        events = []
        for target_str in nmap_args.targets:
            target_host = self._resolve(target_str)
            if target_host is None:
                outputs.append(
                    f"Failed to resolve \"{target_str}\".\n"
                    f"WARNING: No targets were specified, so 0 hosts scanned.")
                events.append({"type": "nmap", "target": target_str,
                               "resolved": False})
                continue

            result = run_scan(engine, target_host, nmap_args)
            output_text = format_output(result, nmap_args)
            outputs.append(output_text)

            # Emit rich events for the objective validator.
            port_list = [p.port for p in result.ports if p.state == "open"]
            services_found = [p.service for p in result.ports if p.state == "open"]
            events.append({
                "type": "nmap",
                "target": target_host.hostname,
                "ip": target_host.ip,
                "resolved": True,
                "host_up": result.host_up,
                "open_ports": port_list,
                "services": services_found,
                "os_detected": bool(result.os_detail),
                "os_detail": result.os_detail,
                "service_version": nmap_args.service_version,
                "flags": {
                    "sV": nmap_args.service_version,
                    "O": nmap_args.os_detect,
                    "A": nmap_args.aggressive,
                    "sS": nmap_args.syn_scan,
                    "Pn": nmap_args.no_ping,
                    "F": nmap_args.fast,
                },
            })

        # Track nmap targets for objectives.
        scanned = state.setdefault("flags", {}).setdefault("nmap_targets", [])
        for e in events:
            t = e.get("target", "")
            if t and t not in scanned:
                scanned.append(t)

        return ActionResult(
            output="\n".join(outputs),
            new_state=state,
            events=events)

    def _cmd_route(self, state, host, args):
        default = host.gateway or "0.0.0.0"
        lines = [
            "Destination     Gateway         Iface",
            f"default         {default:<16}{host.interface}",
        ]
        if host.ip:
            subnet = ".".join(host.ip.split(".")[:3]) + ".0/24"
            lines.append(f"{subnet:<16}0.0.0.0         {host.interface}")
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "route", "host": host.hostname}])

    def _cmd_clear(self, state, host, args):
        return ActionResult(output="", new_state=state, clear=True)

    # -- YC-026.2 shell command handlers --------------------------------
    def _cmd_pwd(self, state, host, args):
        """Print working directory. Windows shows the prompt's directory,
        Linux/Unix shows the student home. Both are simulated."""
        if _is_windows(host):
            output = "C:\\Users\\Student"
        else:
            output = "/home/student"
        return ActionResult(output=output, new_state=state,
                            events=[{"type": "pwd", "host": host.hostname}])

    def _cmd_cd(self, state, host, args):
        """A no-op stub — future labs can add a filesystem. For now
        we just confirm the intent so students don't get 'command not
        found' on such a common command."""
        if not args:
            return ActionResult(output="", new_state=state)
        target = args[0]
        return ActionResult(
            output=f"cd: {target}: filesystem not implemented in this simulator",
            new_state=state,
            events=[{"type": "cd", "host": host.hostname, "target": target}])

    def _cmd_whoami(self, state, host, args):
        """The student is 'student' on Linux, 'Student' on Windows —
        matching the prompts above."""
        user = "Student" if _is_windows(host) else "student"
        return ActionResult(output=user, new_state=state,
                            events=[{"type": "whoami", "host": host.hostname,
                                     "user": user}])

    def _cmd_date(self, state, host, args):
        """Deterministic simulated time — same shape across all devices.
        We don't pull the wall clock because reproducible lab output
        makes objectives easier to validate and demos easier to write."""
        stamp = "Fri Jul 17 09:15:42 UTC 2026"
        if _is_windows(host):
            # Windows `date /t` prints a locale date; approximate that.
            stamp = "Fri 07/17/2026"
        return ActionResult(output=stamp, new_state=state,
                            events=[{"type": "date", "host": host.hostname}])

    def _cmd_echo(self, state, host, args):
        """Echoes exactly what was passed. Empty echo prints a blank line."""
        text = " ".join(args)
        return ActionResult(output=text, new_state=state,
                            events=[{"type": "echo", "host": host.hostname}])

    def _cmd_history(self, state, host, args):
        """Server-side history is not tracked (it's a client concern);
        this handler explains that so the command doesn't feel broken.
        The browser terminal already supports ↑/↓ history browsing."""
        return ActionResult(
            output="history is browsed with the ↑ and ↓ arrow keys.",
            new_state=state,
            events=[{"type": "history", "host": host.hostname}])

    def _cmd_exit(self, state, host, args):
        state["selected"] = self._default_host()
        return ActionResult(
            output=f"Detached from {host.label}. Select a device to continue.",
            new_state=state, clear=True,
            events=[{"type": "exit", "host": host.hostname}])

    # ------------------------------------------------------------------
    # Topology helpers
    # ------------------------------------------------------------------
    def _get_host(self, key: str) -> Optional[Host]:
        for h in self.topology:
            if h.hostname == key or h.ip == key or h.label.lower() == str(key).lower():
                return h
        return None

    def _resolve(self, target: str) -> Optional[Host]:
        return self._get_host(target)

    def _default_host(self) -> str:
        pcs = [h for h in self.topology if h.device_type == "pc"]
        return (pcs[0] if pcs else self.topology[0]).hostname

    def _neighbours_of(self, hostname: str) -> set[str]:
        n = set()
        for a, b in self.links:
            if a == hostname:
                n.add(b)
            elif b == hostname:
                n.add(a)
        return n

    def _reachable(self, a: str, b: str) -> bool:
        return self._path(a, b) is not None

    def _path(self, start: str, end: str) -> Optional[list[str]]:
        """Shortest-path BFS through the link graph. Returns node list
        including start and end, or ``None`` if disconnected."""
        if start == end:
            return [start]
        seen = {start}
        queue = [[start]]
        while queue:
            path = queue.pop(0)
            for n in self._neighbours_of(path[-1]):
                if n in seen:
                    continue
                new_path = path + [n]
                if n == end:
                    return new_path
                seen.add(n)
                queue.append(new_path)
        return None

    def _learn_arp(self, state: dict, from_host: str, peer: Host) -> None:
        arp = state.setdefault("flags", {}).setdefault("arp", {})
        arp.setdefault(from_host, {})[peer.ip] = peer.mac

    def _capture(self, state: dict, packets: list) -> None:
        """Append packet dicts to a bounded session capture buffer.

        This is the seam the future Wireshark simulator reads from — it
        never has to re-run the engine, it just renders the captured
        feed. Bounded to the most recent 200 packets so a long session
        can't bloat the session row.
        """
        if not packets:
            return
        cap = state.setdefault("flags", {}).setdefault("packets", [])
        for pkt in packets:
            # Packets are frozen dataclasses with a to_dict(); tolerate
            # anything already dict-shaped too.
            cap.append(pkt.to_dict() if hasattr(pkt, "to_dict") else dict(pkt))
        # Keep only the newest 200.
        if len(cap) > 200:
            del cap[: len(cap) - 200]

    def _new_host_state(self, host: Host) -> dict[str, Any]:
        return {"visited": False}


# ---------------------------------------------------------------------------
# Concrete topology for YC-026.0
# ---------------------------------------------------------------------------
# Internet
#   │
# router          (router.local, 192.168.1.1, gateway to the internet)
#   │
# switch          (switch.local, L2 only — no IP)
#   ├── pc-1        (192.168.1.10)  Ubuntu 22.04
#   ├── pc-2        (192.168.1.11)  Windows 11
#   ├── web-server  (192.168.1.20)  Debian, ports 80/443
#   └── db-server   (192.168.1.30)  Debian, port 3306
# firewall class exists but is not instantiated in this topology (future).
# ---------------------------------------------------------------------------
_TOPOLOGY: list[Host] = [
    Host("router",     "Router",       "router", "RouterOS 7",
         ip="192.168.1.1", mac="02:42:c0:a8:01:01", gateway="203.0.113.1",
         open_ports=[22, 80],
         services={22: "ssh", 80: "http-admin"}),
    Host("switch",     "Switch",       "switch", "SwitchOS 3",
         ip="", mac="02:42:c0:a8:01:02"),
    Host("pc-1",       "PC-1",         "pc", "Ubuntu 22.04 LTS",
         ip="192.168.1.10", mac="02:42:c0:a8:01:0a", gateway="192.168.1.1"),
    Host("pc-2",       "PC-2",         "pc", "Windows 11",
         ip="192.168.1.11", mac="02:42:c0:a8:01:0b", gateway="192.168.1.1"),
    Host("web-server", "Web Server",   "server", "Debian 12",
         ip="192.168.1.20", mac="02:42:c0:a8:01:14", gateway="192.168.1.1",
         open_ports=[80, 443],
         services={80: "http", 443: "https"}),
    Host("db-server",  "DB Server",    "server", "Debian 12",
         ip="192.168.1.30", mac="02:42:c0:a8:01:1e", gateway="192.168.1.1",
         open_ports=[3306],
         services={3306: "mysql"}),
]

# Each end host connects through the switch. Router connects to switch too
# (its LAN side) — that's what "the router is the gateway" actually means.
_LINKS: list[tuple[str, str]] = [
    ("router", "switch"),
    ("switch", "pc-1"),
    ("switch", "pc-2"),
    ("switch", "web-server"),
    ("switch", "db-server"),
]


@register_simulator
class InteractiveNetworkSimulator(MultiHostSimulator):
    """The concrete simulator seeded by :func:`seed_interactive_network`."""

    key = "net-interactive"
    topology = _TOPOLOGY
    links = _LINKS


# Firewall class — declared here so future labs can drop it into a topology
# without touching the base class. Behaviour parity with a router but with
# an ACL list on the state envelope. Kept as a simple factory instead of a
# dataclass subclass so we don't have to redeclare Host's fields.
def make_firewall(hostname: str, label: str, **kwargs) -> Host:  # pragma: no cover
    """Convenience factory for future firewall-topology labs (YC-026.0)."""
    return Host(hostname=hostname, label=label, device_type="firewall",
                os=kwargs.pop("os", "PfSense 2.7"), **kwargs)


# Backwards-compatible alias — some future tests may import this name.
FirewallHost = make_firewall  # pragma: no cover
