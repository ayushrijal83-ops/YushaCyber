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
    vars: dict[str, str]
    history: list[str]
    _pipe_input: str | None


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
