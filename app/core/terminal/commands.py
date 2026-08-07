"""Terminal commands — realistic educational Linux command simulation."""

from __future__ import annotations

import time
from collections.abc import Callable

from app.core.terminal.filesystem import VirtualFS

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
    history: list[str]


# ══════════════════════════════════════════════════════
# Commands
# ══════════════════════════════════════════════════════

@cmd("pwd")
def _pwd(sh: Shell, args: list[str]) -> str:
    return sh.fs.cwd


@cmd("ls")
def _ls(sh: Shell, args: list[str]) -> str:
    show_all = any(a in args for a in ("-a", "-la", "-al", "-l"))
    path_args = [a for a in args if not a.startswith("-")]
    path = path_args[0] if path_args else "."
    if not sh.fs.isdir(sh.fs.abspath(path)):
        return f"ls: cannot access '{path}': No such file or directory"
    items = sh.fs.listdir(path)
    if show_all:
        items = [".", ".."] + items
    if any(a in args for a in ("-l", "-la", "-al")):
        lines = [f"total {len(items)}"]
        for item in items:
            full = sh.fs.abspath(path + "/" + item) if item not in (".", "..") else sh.fs.abspath(path)
            is_dir = sh.fs.isdir(full) if item not in (".", "..") else True
            perm = "drwxr-xr-x" if is_dir else "-rw-r--r--"
            size = len(sh.fs.read(full) or "") if not is_dir else 4096
            lines.append(f"{perm}  1 student student  {size:>5}  Jan  5 08:00  {item}")
        return "\n".join(lines)
    return "  ".join(items)


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
    content = sh.fs.read(path)
    if content is None:
        return f"cat: {path}: No such file or directory"
    return content.rstrip("\n")


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
    if len(args) < 2:
        return "Usage: grep PATTERN FILE"
    pattern, filepath = args[0], args[1]
    content = sh.fs.read(filepath)
    if content is None:
        return f"grep: {filepath}: No such file or directory"
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


@cmd("uname")
def _uname(sh: Shell, args: list[str]) -> str:
    if "-a" in args:
        return "Linux yushacyber-lab 5.15.0 #1 SMP x86_64 GNU/Linux"
    return "Linux"
