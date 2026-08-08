"""Terminal commands — realistic educational Linux command simulation."""

from __future__ import annotations

import time
from collections.abc import Callable

from app.core.terminal.filesystem import VirtualFS
from app.core.terminal.network import VirtualNetwork

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
