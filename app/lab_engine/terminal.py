"""Terminal — command parser + executor for simulated environments.

Supports Linux and Windows command sets. All execution is sandboxed
inside VirtualFS — no real OS access.
"""

from __future__ import annotations

import shlex
from typing import Any

from app.lab_engine.filesystem import VirtualFS


class Terminal:
    """Simulated terminal session."""

    def __init__(self, fs: VirtualFS | None = None,
                 mode: str = "linux") -> None:
        self.fs = fs or VirtualFS()
        self.mode = mode  # "linux" | "windows"
        self.history: list[str] = []
        self.env: dict[str, str] = {
            "USER": "student", "HOME": self.fs.home,
            "HOSTNAME": "yushacyber-lab",
        }
        self._commands = _LINUX_COMMANDS if mode == "linux" \
            else _WINDOWS_COMMANDS

    @property
    def prompt(self) -> str:
        if self.mode == "windows":
            return f"{self.fs.cwd}> "
        return f"student@lab:{self.fs.cwd}$ "

    def execute(self, command_line: str) -> str:
        """Parse and execute a command. Returns output string."""
        command_line = command_line.strip()
        if not command_line:
            return ""
        self.history.append(command_line)
        try:
            parts = shlex.split(command_line)
        except ValueError:
            parts = command_line.split()
        cmd = parts[0].lower()
        args = parts[1:]
        handler = self._commands.get(cmd)
        if handler is None:
            return f"{cmd}: command not found"
        try:
            return handler(self, args)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            return f"{cmd}: error — {exc}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "fs": self.fs.to_dict(),
            "mode": self.mode,
            "history": self.history[-50:],
            "env": self.env,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Terminal:
        fs = VirtualFS.from_dict(data.get("fs", {}))
        t = cls(fs=fs, mode=data.get("mode", "linux"))
        t.history = data.get("history", [])
        t.env = data.get("env", t.env)
        return t


# ── Linux commands ──
def _ls(term: Terminal, args: list[str]) -> str:
    path = args[0] if args else "."
    show_all = "-a" in args or "-la" in args or "-al" in args
    if "-la" in args or "-al" in args:
        args = [a for a in args if a not in ("-la", "-al")]
        path = args[0] if args else "."
    elif "-a" in args:
        args = [a for a in args if a != "-a"]
        path = args[0] if args else "."
    items = term.fs.listdir(path)
    if not items and not term.fs.isdir(term.fs.abspath(path)):
        return f"ls: cannot access '{path}': No such file or directory"
    if show_all:
        items = [".", ".."] + items
    return "  ".join(items)


def _pwd(term: Terminal, args: list[str]) -> str:
    return term.fs.cwd


def _cd(term: Terminal, args: list[str]) -> str:
    target = args[0] if args else term.fs.home
    if target == "~":
        target = term.fs.home
    if not term.fs.cd(target):
        return f"cd: {target}: No such file or directory"
    return ""


def _cat(term: Terminal, args: list[str]) -> str:
    if not args:
        return "cat: missing operand"
    content = term.fs.read(args[0])
    if content is None:
        if term.fs.isdir(term.fs.abspath(args[0])):
            return f"cat: {args[0]}: Is a directory"
        return f"cat: {args[0]}: No such file or directory"
    return content


def _grep(term: Terminal, args: list[str]) -> str:
    if len(args) < 2:
        return "Usage: grep PATTERN FILE"
    pattern, filepath = args[0], args[1]
    content = term.fs.read(filepath)
    if content is None:
        return f"grep: {filepath}: No such file or directory"
    matches = [line for line in content.splitlines()
               if pattern.lower() in line.lower()]
    return "\n".join(matches) if matches else ""


def _find(term: Terminal, args: list[str]) -> str:
    path = args[0] if args else "."
    name_filter = ""
    if "-name" in args:
        idx = args.index("-name")
        if idx + 1 < len(args):
            name_filter = args[idx + 1].strip("'\"*")
    results: list[str] = []
    _find_recursive(term.fs, path, name_filter, results)
    return "\n".join(results) if results else ""


def _find_recursive(fs: VirtualFS, path: str, name_filter: str,
                    results: list[str]) -> None:
    for item in fs.listdir(path):
        full = fs.abspath(path + "/" + item)
        if not name_filter or name_filter in item:
            results.append(full)
        if fs.isdir(full):
            _find_recursive(fs, full, name_filter, results)


def _chmod(term: Terminal, args: list[str]) -> str:
    if len(args) < 2:
        return "chmod: missing operand"
    return ""  # simulated — no real permissions


def _mkdir(term: Terminal, args: list[str]) -> str:
    if not args:
        return "mkdir: missing operand"
    if not term.fs.mkdir(args[0]):
        return f"mkdir: cannot create directory '{args[0]}'"
    return ""


def _rm(term: Terminal, args: list[str]) -> str:
    targets = [a for a in args if not a.startswith("-")]
    if not targets:
        return "rm: missing operand"
    for t in targets:
        if not term.fs.remove(t):
            return f"rm: cannot remove '{t}': No such file or directory"
    return ""


def _cp(term: Terminal, args: list[str]) -> str:
    actual = [a for a in args if not a.startswith("-")]
    if len(actual) < 2:
        return "cp: missing operand"
    if not term.fs.copy(actual[0], actual[1]):
        return f"cp: cannot copy '{actual[0]}'"
    return ""


def _mv(term: Terminal, args: list[str]) -> str:
    if len(args) < 2:
        return "mv: missing operand"
    if not term.fs.move(args[0], args[1]):
        return f"mv: cannot move '{args[0]}'"
    return ""


def _echo(term: Terminal, args: list[str]) -> str:
    text = " ".join(args)
    # Handle > redirect.
    if ">" in args:
        idx = args.index(">")
        text = " ".join(args[:idx])
        if idx + 1 < len(args):
            term.fs.write(args[idx + 1], text + "\n")
            return ""
    return text


def _history(term: Terminal, args: list[str]) -> str:
    return "\n".join(f"  {i+1}  {c}" for i, c in
                     enumerate(term.history[-20:]))


def _clear(term: Terminal, args: list[str]) -> str:
    return "\x1b[clear]"


def _whoami(term: Terminal, args: list[str]) -> str:
    return term.env.get("USER", "student")


def _hostname(term: Terminal, args: list[str]) -> str:
    return term.env.get("HOSTNAME", "lab")


_LINUX_COMMANDS = {
    "ls": _ls, "pwd": _pwd, "cd": _cd, "cat": _cat,
    "grep": _grep, "find": _find, "chmod": _chmod,
    "mkdir": _mkdir, "rm": _rm, "cp": _cp, "mv": _mv,
    "echo": _echo, "history": _history, "clear": _clear,
    "whoami": _whoami, "hostname": _hostname,
}

# ── Windows commands (aliases to same logic) ──
def _dir(term: Terminal, args: list[str]) -> str:
    return _ls(term, args)

def _type_cmd(term: Terminal, args: list[str]) -> str:
    return _cat(term, args)

def _copy_cmd(term: Terminal, args: list[str]) -> str:
    return _cp(term, args)

def _move_cmd(term: Terminal, args: list[str]) -> str:
    return _mv(term, args)

def _tree_cmd(term: Terminal, args: list[str]) -> str:
    path = args[0] if args else "."
    return term.fs.tree(path)

def _findstr(term: Terminal, args: list[str]) -> str:
    return _grep(term, args)

def _ipconfig(term: Terminal, args: list[str]) -> str:
    return ("Ethernet adapter Ethernet:\n"
            "   IPv4 Address. . . . : 10.0.0.50\n"
            "   Subnet Mask . . . . : 255.255.255.0\n"
            "   Default Gateway . . : 10.0.0.1\n")

def _cls(term: Terminal, args: list[str]) -> str:
    return "\x1b[clear]"


_WINDOWS_COMMANDS = {
    "dir": _dir, "cd": _cd, "type": _type_cmd,
    "copy": _copy_cmd, "move": _move_cmd, "tree": _tree_cmd,
    "findstr": _findstr, "ipconfig": _ipconfig,
    "whoami": _whoami, "cls": _cls, "mkdir": _mkdir,
    "echo": _echo,
}
