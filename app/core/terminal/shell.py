"""Shell — the main terminal session integrating filesystem + commands."""

from __future__ import annotations

import shlex
from typing import Any

from app.core.terminal.commands import autocomplete, get_commands
from app.core.terminal.filesystem import VirtualFS


class Shell:
    """Interactive shell session — one per student per lab."""

    def __init__(self, fs: VirtualFS | None = None) -> None:
        self.fs = fs or VirtualFS()
        self.env: dict[str, str] = {
            "USER": "student",
            "HOME": self.fs.home,
            "HOSTNAME": "yushacyber-lab",
            "PATH": "/usr/local/bin:/usr/bin:/bin",
        }
        self.history: list[str] = []
        self._commands = get_commands()

    @property
    def prompt(self) -> str:
        cwd = self.fs.cwd
        if cwd == self.fs.home:
            cwd = "~"
        elif cwd.startswith(self.fs.home + "/"):
            cwd = "~/" + cwd[len(self.fs.home) + 1:]
        return f"student@lab:{cwd}$ "

    def execute(self, line: str) -> str:
        """Execute a command line. Returns output."""
        line = line.strip()
        if not line:
            return ""
        self.history.append(line)

        # Handle pipes (simplified: just run last command).
        if "|" in line:
            parts = line.split("|")
            line = parts[-1].strip()

        try:
            tokens = shlex.split(line)
        except ValueError:
            tokens = line.split()

        cmd = tokens[0].lower()
        args = tokens[1:]

        handler = self._commands.get(cmd)
        if handler is None:
            return f"bash: {cmd}: command not found"

        try:
            return handler(self, args)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            return f"bash: {cmd}: {exc}"

    def complete(self, partial: str) -> list[str]:
        return autocomplete(partial, self.fs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fs": self.fs.to_dict(),
            "env": self.env,
            "history": self.history[-50:],
            "prompt": self.prompt,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Shell:
        fs = VirtualFS.from_dict(d.get("fs", {}))
        sh = cls(fs=fs)
        sh.env = d.get("env", sh.env)
        sh.history = d.get("history", [])
        return sh
