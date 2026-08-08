"""Terminal commands — realistic educational Linux command simulation."""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Callable

from app.core.terminal.filesystem import VirtualFS
from app.core.terminal.network import VirtualNetwork
from app.core.terminal.packets import PacketLab
from app.core.terminal.web import WebLab

CommandFn = Callable[["Shell", list[str]], str]
_COMMANDS: dict[str, CommandFn] = {}


def cmd(name: str):
    """Decorator to register a command."""
    def wrap(fn: CommandFn) -> CommandFn:
        _COMMANDS[name] = fn
        return fn
    return wrap


def get_commands() -> dict[str, CommandFn]:
    return dict(_COMMANDS)


def autocomplete(partial: str, fs: VirtualFS) -> list[str]:
    """Basic tab-autocomplete."""
    matches: list[str] = []
    # Command names.
    for name in _COMMANDS:
        if name.startswith(partial):
            matches.append(name)
    # Files in cwd.
    for item in fs.listdir("."):
        if item.startswith(partial):
            matches.append(item)
    return sorted(matches)[:10]


# ── Shell class (forward ref for type hints) ──
class Shell:
    """Minimal shell reference for command functions."""
    fs: VirtualFS
    env: dict[str, str]
    vars: dict[str, str]
    history: list[str]
    _pipe_input: str | None
    network: VirtualNetwork | None
    packet_lab: PacketLab | None
    web_lab: WebLab | None


# ══════════════════════════════════════════════════════
# Commands
# ══════════════════════════════════════════════════════

@cmd("pwd")
def _pwd(sh: Shell, args: list[str]) -> str:
    return sh.fs.cwd


def _ls_long_line(fs: VirtualFS, full: str, name: str) -> str:
    is_dir = fs.isdir(full)
    perm = fs.mode_to_symbolic(fs.get_mode(full), is_dir)
    owner = fs.get_owner(full)
    group = fs.get_group(full)
    size = 4096 if is_dir else len(fs.read(full) or "")
    return f"{perm}  1 {owner} {group}  {size:>5}  Jan  5 08:00  {name}"


@cmd("ls")
def _ls(sh: Shell, args: list[str]) -> str:
    show_all = any(a in args for a in ("-a", "-la", "-al"))
    long_fmt = any(a in args for a in ("-l", "-la", "-al"))
    path_args = [a for a in args if not a.startswith("-")]
    path = path_args[0] if path_args else "."
    full = sh.fs.abspath(path)
    if not sh.fs.exists(path):
        return f"ls: cannot access '{path}': No such file or directory"
    if sh.fs.isfile(full):
        name = path.rstrip("/").split("/")[-1] or path
        return _ls_long_line(sh.fs, full, name) if long_fmt else name
    items = sh.fs.listdir(path)
    if show_all:
        items = [".", ".."] + items
    if long_fmt:
        lines = [f"total {len(items)}"]
        for item in items:
            item_full = full if item in (".", "..") else sh.fs.abspath(path.rstrip("/") + "/" + item)
            lines.append(_ls_long_line(sh.fs, item_full, item))
        return "\n".join(lines)
    # One entry per line — makes `ls | grep ...` filter meaningfully.
    return "\n".join(items)


@cmd("cd")
def _cd(sh: Shell, args: list[str]) -> str:
    target = args[0] if args else sh.fs.home
    if target == "~":
        target = sh.fs.home
    if not sh.fs.cd(target):
        return f"bash: cd: {target}: No such file or directory"
    return ""


@cmd("cat")
def _cat(sh: Shell, args: list[str]) -> str:
    if not args:
        return "cat: missing operand"
    path = args[0]
    if sh.fs.isdir(sh.fs.abspath(path)):
        return f"cat: {path}: Is a directory"
    if not sh.fs.exists(path):
        return f"cat: {path}: No such file or directory"
    if not sh.fs.can_read(path, sh.env.get("USER", "student")):
        return f"cat: {path}: Permission denied"
    content = sh.fs.read(path)
    return content.rstrip("\n") if content else ""


@cmd("echo")
def _echo(sh: Shell, args: list[str]) -> str:
    if ">" in args:
        idx = args.index(">")
        text = " ".join(args[:idx])
        if idx + 1 < len(args):
            sh.fs.write(args[idx + 1], text + "\n")
            return ""
    if ">>" in args:
        idx = args.index(">>")
        text = " ".join(args[:idx])
        if idx + 1 < len(args):
            existing = sh.fs.read(args[idx + 1]) or ""
            sh.fs.write(args[idx + 1], existing + text + "\n")
            return ""
    return " ".join(args)


@cmd("mkdir")
def _mkdir(sh: Shell, args: list[str]) -> str:
    if not args:
        return "mkdir: missing operand"
    for d in args:
        if d.startswith("-"):
            continue
        if not sh.fs.mkdir(d):
            return f"mkdir: cannot create directory '{d}': File exists or parent missing"
    return ""


@cmd("touch")
def _touch(sh: Shell, args: list[str]) -> str:
    if not args:
        return "touch: missing operand"
    for f in args:
        if not sh.fs.exists(f):
            sh.fs.touch(f)
    return ""


@cmd("rm")
def _rm(sh: Shell, args: list[str]) -> str:
    targets = [a for a in args if not a.startswith("-")]
    if not targets:
        return "rm: missing operand"
    for t in targets:
        if not sh.fs.rm(t):
            return f"rm: cannot remove '{t}': No such file or directory"
    return ""


@cmd("clear")
def _clear(sh: Shell, args: list[str]) -> str:
    return "\x1b[clear]"


@cmd("help")
def _help(sh: Shell, args: list[str]) -> str:
    cmds = sorted(_COMMANDS.keys())
    return "Available commands:\n  " + "  ".join(cmds)


@cmd("whoami")
def _whoami(sh: Shell, args: list[str]) -> str:
    return sh.env.get("USER", "student")


@cmd("hostname")
def _hostname(sh: Shell, args: list[str]) -> str:
    return sh.env.get("HOSTNAME", "yushacyber-lab")


@cmd("date")
def _date(sh: Shell, args: list[str]) -> str:
    return time.strftime("Mon Jan  5 08:30:00 UTC 2026")


@cmd("history")
def _history(sh: Shell, args: list[str]) -> str:
    return "\n".join(f"  {i+1}  {c}" for i, c in enumerate(sh.history[-20:]))


@cmd("tree")
def _tree(sh: Shell, args: list[str]) -> str:
    path = args[0] if args else "."
    return sh.fs.tree(path, depth=3)


@cmd("grep")
def _grep(sh: Shell, args: list[str]) -> str:
    if not args:
        return "Usage: grep PATTERN [FILE]"
    pattern = args[0]
    if len(args) >= 2:
        content = sh.fs.read(args[1])
        if content is None:
            return f"grep: {args[1]}: No such file or directory"
    elif getattr(sh, "_pipe_input", None) is not None:
        content = sh._pipe_input
    else:
        return "Usage: grep PATTERN [FILE]"
    matches = [l for l in content.splitlines() if pattern.lower() in l.lower()]
    return "\n".join(matches) if matches else ""


@cmd("find")
def _find(sh: Shell, args: list[str]) -> str:
    path = args[0] if args else "."
    name_filter = ""
    if "-name" in args:
        idx = args.index("-name")
        if idx + 1 < len(args):
            name_filter = args[idx + 1].strip("'\"*")
    results: list[str] = []
    _find_r(sh.fs, path, name_filter, results)
    return "\n".join(results)


def _find_r(fs: VirtualFS, path: str, filt: str, out: list[str]) -> None:
    for item in fs.listdir(path):
        full = fs.abspath(path + "/" + item)
        if not filt or filt in item:
            out.append(full)
        if fs.isdir(full):
            _find_r(fs, full, filt, out)


@cmd("id")
def _id(sh: Shell, args: list[str]) -> str:
    return "uid=1000(student) gid=1000(student) groups=1000(student),27(sudo)"


@cmd("groups")
def _groups(sh: Shell, args: list[str]) -> str:
    return "student sudo"


@cmd("chmod")
def _chmod(sh: Shell, args: list[str]) -> str:
    args = [a for a in args if not a.startswith("--")]
    if len(args) < 2:
        return "chmod: missing operand"
    mode, target = args[0], args[1]
    if not sh.fs.exists(target):
        return f"chmod: cannot access '{target}': No such file or directory"
    if mode in ("+x", "-x"):
        current = sh.fs.get_mode(target).rjust(3, "0")[-3:]
        new_digits = []
        for d in current:
            n = int(d) if d.isdigit() else 0
            n = (n | 1) if mode == "+x" else (n & ~1)
            new_digits.append(str(n))
        sh.fs.set_mode(target, "".join(new_digits))
        return ""
    if not mode.isdigit() or not (1 <= len(mode) <= 4):
        return f"chmod: invalid mode: '{mode}'"
    sh.fs.set_mode(target, mode)
    return ""


@cmd("export")
def _export(sh: Shell, args: list[str]) -> str:
    if not args:
        return "export: usage: export NAME=VALUE"
    for a in args:
        if "=" in a:
            name, _, value = a.partition("=")
            sh.env[name] = value
        elif a in sh.vars:
            sh.env[a] = sh.vars[a]
    return ""


@cmd("chown")
def _chown(sh: Shell, args: list[str]) -> str:
    if len(args) < 2:
        return "chown: missing operand"
    spec, target = args[0], args[1]
    owner, _, group = spec.partition(":")
    if not sh.fs.exists(target):
        return f"chown: cannot access '{target}': No such file or directory"
    sh.fs.set_owner(target, owner, group or None)
    return ""


@cmd("uname")
def _uname(sh: Shell, args: list[str]) -> str:
    if "-a" in args:
        return "Linux yushacyber-lab 5.15.0 #1 SMP x86_64 GNU/Linux"
    return "Linux"


# ══════════════════════════════════════════════════════
# Networking commands (YC-034.5) — fully simulated, reads
# from sh.network only. Never opens a real socket, resolves
# real DNS, or touches the host's network stack.
# ══════════════════════════════════════════════════════

def _ip_arg_after(args: list[str], keyword: str) -> str | None:
    if keyword in args:
        idx = args.index(keyword)
        if idx + 1 < len(args):
            return args[idx + 1]
    return None


@cmd("ip")
def _ip(sh: Shell, args: list[str]) -> str:
    if sh.network is None:
        return "ip: no network configured for this session"
    if not args:
        return "Usage: ip {addr|route|link}"
    sub = args[0]

    # ── Simulated fixes (YC-034.6) — mutate sh.network only. ──
    if sub == "link" and len(args) >= 4 and args[1] == "set":
        iface, state = args[2], args[3]
        if sh.network.set_interface_state(iface, state):
            return ""
        return f"ip: link {iface} not found"

    if sub == "addr" and len(args) >= 3 and args[1] == "add":
        spec = args[2]
        if "/" not in spec:
            return "ip: usage: ip addr add IP/CIDR dev IFACE"
        ip, _, cidr = spec.partition("/")
        iface = _ip_arg_after(args, "dev") or "eth0"
        if not cidr.isdigit():
            return f"ip: invalid prefix length '{cidr}'"
        if sh.network.set_interface_address(iface, ip, int(cidr)):
            return ""
        return f"ip: link {iface} not found"

    if sub == "route" and len(args) >= 3 and args[1] == "add":
        gateway = _ip_arg_after(args, "via")
        if not gateway:
            return "ip: usage: ip route add default via GATEWAY [dev IFACE]"
        iface = _ip_arg_after(args, "dev") or "eth0"
        sh.network.set_default_gateway(gateway, iface)
        return ""

    # ── Read-only inspection ──
    if sub in ("addr", "a"):
        return sh.network.interfaces_text()
    if sub in ("route", "r"):
        return sh.network.route_text()
    if sub == "link":
        return sh.network.link_text()
    return f"ip: unknown sub-command '{sub}'"


@cmd("ping")
def _ping(sh: Shell, args: list[str]) -> str:
    if sh.network is None:
        return "ping: no network configured for this session"
    targets = [a for a in args if not a.startswith("-")]
    if not targets:
        return "ping: usage error: Destination address required"
    target = sh.network.resolve(targets[0]) or targets[0]
    _, output = sh.network.ping(target)
    return output


@cmd("ss")
def _ss(sh: Shell, args: list[str]) -> str:
    if sh.network is None:
        return "ss: no network configured for this session"
    return sh.network.services_text()


@cmd("nslookup")
def _nslookup(sh: Shell, args: list[str]) -> str:
    if sh.network is None:
        return "nslookup: no network configured for this session"
    if not args:
        return "Usage: nslookup HOSTNAME"
    hostname = args[0]
    ip = sh.network.resolve(hostname)
    server = sh.network.dns_server_ip or "unknown"
    if ip is None:
        return f"Server:\t\t{server}\n\n** server can't find {hostname}: NXDOMAIN"
    return f"Server:\t\t{server}\n\nName:\t{hostname}\nAddress: {ip}"


@cmd("host")
def _host(sh: Shell, args: list[str]) -> str:
    if sh.network is None:
        return "host: no network configured for this session"
    if not args:
        return "Usage: host HOSTNAME"
    hostname = args[0]
    ip = sh.network.resolve(hostname)
    if ip is None:
        return f"Host {hostname} not found: 3(NXDOMAIN)"
    return f"{hostname} has address {ip}"


def _parse_port_spec(spec: str) -> list[int]:
    """Parse an nmap-style -p spec: '22,80,443' or '20-25' or a mix."""
    ports: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, _, hi = part.partition("-")
            if lo.isdigit() and hi.isdigit():
                ports.extend(range(int(lo), int(hi) + 1))
        elif part.isdigit():
            ports.append(int(part))
    return ports


@cmd("nmap")
def _nmap(sh: Shell, args: list[str]) -> str:
    """Simulated Nmap (YC-034.7) — reads sh.network only. Never invokes
    the real nmap binary, a subprocess, or a socket of any kind."""
    if sh.network is None:
        return "nmap: no network configured for this session"
    if not args:
        return "Usage: nmap [options] target"

    ports: list[int] | None = None
    scan_all_ports = False
    proto = "tcp"
    service_detection = False
    os_detection = False
    skip_discovery = False
    host_discovery = False  # -sn (YC-034.8)
    positional: list[str] = []

    i = 0
    while i < len(args):
        t = args[i]
        if t == "-p" and i + 1 < len(args):
            ports = _parse_port_spec(args[i + 1])
            i += 1
        elif t == "-p-":
            scan_all_ports = True
        elif t == "-sn":
            host_discovery = True
        elif t == "-sV":
            service_detection = True
        elif t == "-sU":
            proto = "udp"
        elif t == "-sT":
            proto = "tcp"
        elif t == "-O":
            os_detection = True
        elif t == "-Pn":
            skip_discovery = True
        elif t == "-sC" or t.startswith("-"):
            pass  # accepted (or silently ignored if unrecognized) — no extra simulated behavior
        else:
            positional.append(t)
        i += 1

    if not positional:
        return "nmap: no target specified"
    target = positional[0]

    if host_discovery:
        results = sh.network.discover(target)
        return sh.network.format_discovery(target, results)

    if scan_all_ports:
        ports = None  # default scan already covers every known port on the host

    result = sh.network.scan(target, ports=ports, proto=proto,
                             service_detection=service_detection,
                             skip_discovery=skip_discovery)
    return sh.network.format_nmap(result, show_version=service_detection, show_os=os_detection)


# ══════════════════════════════════════════════════════
# Packet analysis (YC-034.9) — reads sh.packet_lab only. Every capture is
# a fixed, deterministic in-memory dataset (see packets.py); nothing here
# opens a socket, captures traffic, or shells out to a real tool.
# ══════════════════════════════════════════════════════

@cmd("capture")
def _capture(sh: Shell, args: list[str]) -> str:
    if sh.packet_lab is None:
        return "capture: no packet lab configured for this session"
    if not args:
        names = ", ".join(sorted(sh.packet_lab.captures.keys())) or "(none)"
        active = sh.packet_lab.active.name if sh.packet_lab.active else "none"
        return f"Available captures: {names}\nActive capture: {active}"
    name = args[0]
    if sh.packet_lab.open_capture(name):
        cap = sh.packet_lab.active
        return f"{len(cap.packets)} packets loaded from '{name}'.\nType 'packets' to list them."
    return f"capture: unknown capture '{name}'"


@cmd("packets")
def _packets(sh: Shell, args: list[str]) -> str:
    if sh.packet_lab is None or sh.packet_lab.active is None:
        return "No capture loaded. Use 'capture NAME' first."
    return sh.packet_lab.active.list_text()


@cmd("show")
def _show_packet(sh: Shell, args: list[str]) -> str:
    if sh.packet_lab is None or sh.packet_lab.active is None:
        return "No capture loaded. Use 'capture NAME' first."
    if not args or not args[0].isdigit():
        return "Usage: show PACKET_NUMBER"
    pkt = sh.packet_lab.active.get(int(args[0]))
    if pkt is None:
        return f"show: packet {args[0]} not found"
    sh.packet_lab.selected_packet = pkt.number
    return sh.packet_lab.active.detail_text(pkt)


@cmd("follow")
def _follow(sh: Shell, args: list[str]) -> str:
    if sh.packet_lab is None or sh.packet_lab.active is None:
        return "No capture loaded. Use 'capture NAME' first."
    if not args:
        return "Usage: follow CONVERSATION_ID (or a packet number)"
    cap = sh.packet_lab.active
    token = args[0]
    conv_id = token
    if token.isdigit():
        pkt = cap.get(int(token))
        if pkt is None or not pkt.conversation_id:
            return f"follow: packet {token} has no conversation"
        conv_id = pkt.conversation_id
    matched = cap.conversation(conv_id)
    if not matched:
        return f"follow: no conversation '{conv_id}' found"
    return cap.conversation_text(conv_id, matched)


@cmd("filter")
def _filter(sh: Shell, args: list[str]) -> str:
    if sh.packet_lab is None or sh.packet_lab.active is None:
        return "No capture loaded. Use 'capture NAME' first."
    if not args:
        return "Usage: filter EXPRESSION"
    expr = " ".join(args)
    sh.packet_lab.last_filter = expr
    results = sh.packet_lab.active.filter(expr)
    if not results:
        return f"No packets matched filter '{expr}'."
    return sh.packet_lab.active.list_text(results)


_COMMANDS["packet"] = _show_packet  # alias, matches the ticket's 'packet <n>' form too


# ══════════════════════════════════════════════════════
# Simulated web / HTTP inspection (YC-035.0) — reads sh.web_lab only.
# Every request is handled entirely in-memory by WebApp (web.py); there is
# no outbound HTTP client anywhere in this codepath, so a non-simulated
# host is rejected here before any dispatch is even attempted.
# ══════════════════════════════════════════════════════

def _parse_open_args(args: list[str]) -> tuple[str, str | None, str | None, dict[str, str]]:
    """Parse `open [-X METHOD] [-H "Key: Value"] [-d DATA] URL` (curl-like).
    `-H` is repeatable, mirroring curl, and lets a student set/override any
    request header — Authorization, Referer, or a custom Content-Type for
    a JSON body (YC-035.1)."""
    method = "GET"
    data: str | None = None
    url: str | None = None
    headers: dict[str, str] = {}
    i = 0
    while i < len(args):
        t = args[i]
        if t == "-X" and i + 1 < len(args):
            method = args[i + 1].upper()
            i += 1
        elif t == "-d" and i + 1 < len(args):
            data = args[i + 1]
            i += 1
        elif t == "-H" and i + 1 < len(args):
            header_str = args[i + 1]
            if ":" in header_str:
                name, _, value = header_str.partition(":")
                headers[name.strip()] = value.strip()
            i += 1
        elif not t.startswith("-"):
            url = t
        i += 1
    if data and method == "GET":
        method = "POST"
    return method, data, url, headers


@cmd("open")
def _open(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None:
        return "open: no simulated web environment configured for this session"
    method, data, url, headers = _parse_open_args(args)
    if not url:
        return 'Usage: open [-X METHOD] [-H "Key: Value"] [-d DATA] URL'
    from app.core.terminal.web import (
        HOST,
        build_request,
        parse_url,
        render_exchange,
        render_request,
    )
    parsed = parse_url(url)
    if parsed.host != HOST:
        # Out-of-scope host (YC-035.2) — never even builds a request, let
        # alone opens a connection; the counter lets the proxy-scope
        # objective be validated structurally instead of matching this
        # exact rejection string.
        sh.web_lab.proxy.blocked_count += 1
        return "External hosts are not available in the training environment."
    req = build_request(method, parsed, body=data or "", cookies=sh.web_lab.session.cookies,
                        extra_headers=headers)
    if sh.web_lab.proxy.intercept_enabled:
        # Intercept ON (YC-035.2): queue the request instead of handling
        # it — the same request the student would otherwise have gotten a
        # response for, now held for 'forward'/'drop'/'edit'. When OFF
        # (the default, and the only state YC-035.0/YC-035.1 ever use),
        # this branch never runs and 'open' behaves exactly as before.
        sh.web_lab.proxy.pending = req
        sh.web_lab.proxy.intercepted_count += 1
        return ("Request intercepted:\n" + render_request(req) +
                "\n\nUse 'forward', 'drop', or 'edit <field> ...' before it reaches the server.")
    resp = sh.web_lab.app.handle(req)
    sh.web_lab.session.record(req, resp)
    return render_exchange(req, resp)


@cmd("request")
def _request(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None:
        return "request: no simulated web environment configured for this session"
    if len(args) < 2:
        return "Usage: request METHOD PATH"
    method, path = args[0].upper(), args[1]
    from app.core.terminal.web import HOST
    return _open(sh, ["-X", method, f"https://{HOST}{path}"])


@cmd("web")
def _web(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None:
        return "web: no simulated web environment configured for this session"
    from app.core.terminal.web import HOST
    sid = sh.web_lab.session.cookies.get("session_id")
    username = sh.web_lab.app.sessions.get(sid) if sid else None
    status = f"Logged in as {username}" if username else "Not logged in"
    return (f"Simulated site: {HOST}\n{status}\n"
           f"Routes: / /products /search /login /auth/login /profile /logout "
           f"/api/login /api/profile /api/me\n"
           f"Type 'open URL' or 'request METHOD PATH' to make a request.\n"
           f"Proxy: 'intercept on|off', 'forward', 'drop', 'edit ...', "
           f"'repeater [N]', 'repeater send', 'compare N M'.")


@cmd("requests")
def _requests(sh: Shell, args: list[str]) -> str:
    """List every HTTP request/response this session has made so far, in
    order — the request-history view (YC-035.1). Distinct from the shell's
    own 'history' command (which lists typed commands, not HTTP traffic).
    """
    if sh.web_lab is None:
        return "requests: no simulated web environment configured for this session"
    hist = sh.web_lab.session.history
    if not hist:
        return "No requests made yet. Use 'open URL' first."
    lines = ["Request history:"]
    for i, (req, resp) in enumerate(hist, start=1):
        lines.append(f"  #{i}  {req.method} {req.path}  -> {resp.status_code} {resp.reason}")
    return "\n".join(lines)


@cmd("evidence")
def _evidence(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None:
        return "evidence: no simulated web environment configured for this session"
    lines = ["Investigation log:"]
    for i, (req, resp) in enumerate(sh.web_lab.investigation_log, start=1):
        lines.append(f"  #{i}  {req.method} {req.path}  -> {resp.status_code} {resp.reason}")
    return "\n".join(lines)


@cmd("inspect")
def _inspect(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None:
        return "inspect: no simulated web environment configured for this session"
    from app.core.terminal.web import render_exchange
    if args and args[0].isdigit():
        idx = int(args[0]) - 1
        log = sh.web_lab.investigation_log
        if not (0 <= idx < len(log)):
            return f"inspect: entry {args[0]} not found"
        return render_exchange(*log[idx])
    if sh.web_lab.session.last_request is None:
        return "No request made yet. Use 'open URL' first."
    return render_exchange(sh.web_lab.session.last_request, sh.web_lab.session.last_response)


@cmd("headers")
def _web_headers(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None or sh.web_lab.session.last_request is None:
        return "No request made yet. Use 'open URL' first."
    req, resp = sh.web_lab.session.last_request, sh.web_lab.session.last_response
    lines = ["Request headers:"]
    for k, v in req.headers.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("Response headers:")
    for k, v in resp.headers.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


@cmd("cookies")
def _web_cookies(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None:
        return "cookies: no simulated web environment configured for this session"
    if not sh.web_lab.session.cookies:
        return "No cookies stored."
    return "\n".join(f"{k}={v}" for k, v in sh.web_lab.session.cookies.items())


@cmd("response")
def _web_response(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None or sh.web_lab.session.last_response is None:
        return "No request made yet. Use 'open URL' first."
    from app.core.terminal.web import render_response
    return render_response(sh.web_lab.session.last_response)


# ══════════════════════════════════════════════════════
# Intercepting proxy (YC-035.2 — Burp Suite Fundamentals). Reuses
# sh.web_lab.app/session exactly like open/request above; adds a
# pending-request queue (ProxyState, web.py) that sits between 'open'
# and the simulated server. No new HTTP client, no new host allowlist —
# _open's existing 'host != HOST' rejection is still the only place a
# request can be refused, for both intercepted and direct traffic.
# ══════════════════════════════════════════════════════

@cmd("proxy")
def _proxy_status(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None:
        return "proxy: no simulated web environment configured for this session"
    from app.core.terminal.web import HOST
    p = sh.web_lab.proxy
    state = "ON" if p.intercept_enabled else "OFF"
    return (f"Browser --> Proxy --> Server\n"
           f"Intercept: {state}\n"
           f"Scope: {HOST}\n"
           f"Requests outside scope are never proxied — they're rejected before "
           f"a request object even exists.")


@cmd("intercept")
def _intercept(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None:
        return "intercept: no simulated web environment configured for this session"
    p = sh.web_lab.proxy
    if not args:
        return f"Intercept is {'ON' if p.intercept_enabled else 'OFF'}."
    mode = args[0].lower()
    if mode == "on":
        p.intercept_enabled = True
        return "Intercept is now ON. Your next request will be held before it reaches the server."
    if mode == "off":
        p.intercept_enabled = False
        return "Intercept is now OFF. Requests will pass straight through."
    return "Usage: intercept [on|off]"


@cmd("forward")
def _forward(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None:
        return "forward: no simulated web environment configured for this session"
    p = sh.web_lab.proxy
    if p.pending is None:
        return "No intercepted request to forward. Turn intercept on and make a request first."
    from app.core.terminal.web import render_exchange
    req = p.pending
    resp = sh.web_lab.app.handle(req)
    sh.web_lab.session.record(req, resp)
    p.pending = None
    p.forwarded_count += 1
    return "Request forwarded.\n" + render_exchange(req, resp)


@cmd("drop")
def _drop(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None:
        return "drop: no simulated web environment configured for this session"
    p = sh.web_lab.proxy
    if p.pending is None:
        return "No intercepted request to drop. Turn intercept on and make a request first."
    p.pending = None
    p.dropped_count += 1
    return "Request dropped. It never reached the simulated server."


def _active_editable_request(sh: Shell):
    """The request 'edit' mutates: the intercepted pending request if one
    is queued, else the Repeater's loaded request. None if neither exists."""
    p = sh.web_lab.proxy
    return p.pending if p.pending is not None else p.repeater_request


@cmd("edit")
def _edit(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None:
        return "edit: no simulated web environment configured for this session"
    req = _active_editable_request(sh)
    if req is None:
        return ("Nothing to edit. Intercept a request ('intercept on', then make a request) "
                "or load one into Repeater ('repeater') first.")
    if len(args) < 2:
        return "Usage: edit method|path|query|header|body ..."
    field = args[0].lower()
    if field == "method":
        req.method = args[1].upper()
        return f"Method set to {req.method}."
    if field == "path":
        req.path = args[1]
        return f"Path set to {req.path}."
    if field == "query":
        if len(args) < 3:
            return "Usage: edit query KEY VALUE"
        req.query[args[1]] = args[2]
        return f"Query parameter '{args[1]}' set to '{args[2]}'."
    if field == "header":
        if len(args) < 3:
            return "Usage: edit header NAME VALUE"
        req.headers[args[1]] = " ".join(args[2:])
        return f"Header '{args[1]}' set to '{req.headers[args[1]]}'."
    if field == "body":
        req.body = " ".join(args[1:])
        req.headers["Content-Length"] = str(len(req.body))
        return "Body updated."
    return "Usage: edit method|path|query|header|body ..."


def _copy_request(req):
    """A genuine independent copy of an HttpRequest — dataclasses.replace()
    alone only shallow-copies, so query/headers/cookies dicts would stay
    shared with the original (mutating a Repeater copy would silently
    corrupt the History entry it came from). Copy the mutable fields
    explicitly."""
    return dataclasses.replace(req, query=dict(req.query), headers=dict(req.headers),
                               cookies=dict(req.cookies))


@cmd("repeater")
def _repeater(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None:
        return "repeater: no simulated web environment configured for this session"
    p = sh.web_lab.proxy
    hist = sh.web_lab.session.history
    if args and args[0].lower() == "send":
        if p.repeater_request is None:
            return "Nothing loaded in Repeater. Use 'repeater' or 'repeater N' first."
        from app.core.terminal.web import render_exchange
        req = _copy_request(p.repeater_request)
        resp = sh.web_lab.app.handle(req)
        sh.web_lab.session.record(req, resp)
        p.repeater_sent_count += 1
        return "Repeater: request sent.\n" + render_exchange(req, resp)
    if not hist:
        return "No requests in history yet. Make a request first."
    if args and args[0].isdigit():
        idx = int(args[0]) - 1
        if not (0 <= idx < len(hist)):
            return f"repeater: entry {args[0]} not found"
    else:
        idx = len(hist) - 1
    req, _ = hist[idx]
    p.repeater_request = _copy_request(req)
    p.repeater_loaded_count += 1
    from app.core.terminal.web import render_request
    return f"Sent to Repeater (from history #{idx + 1}):\n" + render_request(p.repeater_request)


@cmd("compare")
def _compare(sh: Shell, args: list[str]) -> str:
    if sh.web_lab is None:
        return "compare: no simulated web environment configured for this session"
    hist = sh.web_lab.session.history
    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        return "Usage: compare N M  (history entry numbers)"
    i, j = int(args[0]) - 1, int(args[1]) - 1
    if not (0 <= i < len(hist)) or not (0 <= j < len(hist)):
        return "compare: one or both entries not found in history."
    from app.core.terminal.web import render_response
    a_lines = render_response(hist[i][1]).split("\n")
    b_lines = render_response(hist[j][1]).split("\n")
    width = max(len(a_lines), len(b_lines))
    a_lines += [""] * (width - len(a_lines))
    b_lines += [""] * (width - len(b_lines))
    out = [f"Comparing #{args[0]} vs #{args[1]} responses:"]
    diff_found = False
    for a, b in zip(a_lines, b_lines):
        if a == b:
            out.append(f"  {a}")
        else:
            diff_found = True
            out.append(f"! #{args[0]}: {a}")
            out.append(f"! #{args[1]}: {b}")
    sh.web_lab.proxy.compared_count += 1
    if not diff_found:
        out.append("(no differences)")
    return "\n".join(out)
