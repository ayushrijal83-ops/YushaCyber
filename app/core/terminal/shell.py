"""Shell — the main terminal session integrating filesystem + commands.

YC-034.4 extends this with just enough real Bash semantics — variable
assignment/expansion, command substitution, pipes, redirection, and
single-line if/for — to make the Bash Fundamentals mission's terminal
challenges behave like a real (sandboxed) shell rather than fake
string-matching. Everything still runs against the same VirtualFS;
nothing here touches the real OS.
"""

from __future__ import annotations

import re
import shlex
from typing import Any

from app.core.terminal.commands import autocomplete, get_commands
from app.core.terminal.filesystem import VirtualFS
from app.core.terminal.network import VirtualNetwork
from app.core.terminal.packets import PacketLab
from app.core.terminal.proxy import ProxyLab
from app.core.terminal.web import WebLab

_ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_REDIR_RE = re.compile(r"(>>|>)\s*(\S+)\s*$")
_CMDSUB_RE = re.compile(r"\$\(([^()]*)\)")
_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
_IF_RE = re.compile(r"^if\s+\[\s*(.+?)\s*\]\s*;\s*then\s+(.+?)\s*;\s*fi$")
_FOR_RE = re.compile(r"^for\s+(\w+)\s+in\s+(.+?)\s*;\s*do\s+(.+?)\s*;\s*done$")


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def expand_vars(text: str, shell: Shell) -> str:
    """Expand $(command substitution) then $VAR / ${VAR} references."""
    def _sub_cmd(m: re.Match) -> str:
        return shell.execute(m.group(1), record=False).strip()

    text = _CMDSUB_RE.sub(_sub_cmd, text)

    def _sub_var(m: re.Match) -> str:
        name = m.group(1) or m.group(2)
        if name in shell.vars:
            return shell.vars[name]
        return shell.env.get(name, "")

    return _VAR_RE.sub(_sub_var, text)


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
        self.vars: dict[str, str] = {}
        self.history: list[str] = []
        self._commands = get_commands()
        self._pipe_input: str | None = None
        # Attached by MissionRunner for networking missions; None (the
        # default) leaves every other mission/free-play session unaffected.
        self.network: VirtualNetwork | None = None
        # Set by from_dict() when resuming; consumed by
        # MissionRunner._attach_network() to replay saved mutations.
        self._pending_network_state: dict[str, Any] | None = None
        # Attached by MissionRunner for packet-analysis missions; None
        # (the default) leaves every other mission/free-play session
        # unaffected.
        self.packet_lab: PacketLab | None = None
        self._pending_packet_lab_state: dict[str, Any] | None = None
        # Attached by MissionRunner for web-fundamentals-style missions;
        # None (the default) leaves every other session unaffected.
        self.web_lab: WebLab | None = None
        self._pending_web_lab_state: dict[str, Any] | None = None
        # Attached by MissionRunner for the Burp Suite Fundamentals
        # mission (YC-035.2); None (the default) leaves every other
        # session unaffected.
        self.proxy_lab: ProxyLab | None = None
        self._pending_proxy_lab_state: dict[str, Any] | None = None

    @property
    def prompt(self) -> str:
        cwd = self.fs.cwd
        if cwd == self.fs.home:
            cwd = "~"
        elif cwd.startswith(self.fs.home + "/"):
            cwd = "~/" + cwd[len(self.fs.home) + 1:]
        return f"student@lab:{cwd}$ "

    def execute(self, line: str, record: bool = True) -> str:
        """Execute a command line. Returns output.

        Handles (in order): variable assignment, single-line if/for,
        output redirection, pipelines, and plain single commands.
        """
        line = line.strip()
        if not line:
            return ""
        if record:
            self.history.append(line)

        m = _ASSIGN_RE.match(line)
        if m:
            name, raw_value = m.group(1), m.group(2)
            self.vars[name] = expand_vars(_strip_quotes(raw_value), self)
            return ""

        if line.startswith("if "):
            return self._exec_if(line)
        if line.startswith("for "):
            return self._exec_for(line)

        work_line = line
        redir_target: str | None = None
        append = False
        rm = _REDIR_RE.search(work_line)
        if rm:
            append = rm.group(1) == ">>"
            redir_target = rm.group(2)
            work_line = work_line[:rm.start()].rstrip()

        output = self._exec_pipeline(work_line) if "|" in work_line else self._exec_single(work_line)

        if redir_target:
            content = (output or "") + "\n"
            if append:
                existing = self.fs.read(redir_target) or ""
                self.fs.write(redir_target, existing + content)
            else:
                self.fs.write(redir_target, content)
            return ""
        return output

    def _exec_single(self, line: str, use_pipe_input: bool = False) -> str:
        if not use_pipe_input:
            self._pipe_input = None
        try:
            tokens = shlex.split(line)
        except ValueError:
            tokens = line.split()
        if not tokens:
            return ""

        cmd = tokens[0]
        if cmd.startswith(("./", "/")):
            return self._run_script(cmd)

        args = [expand_vars(a, self) for a in tokens[1:]]
        handler = self._commands.get(cmd.lower())
        if handler is None:
            return f"bash: {cmd}: command not found"
        try:
            return handler(self, args)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            return f"bash: {cmd}: {exc}"

    def _exec_pipeline(self, line: str) -> str:
        stages = [s.strip() for s in line.split("|")]
        data: str | None = None
        output = ""
        for stage in stages:
            self._pipe_input = data
            output = self._exec_single(stage, use_pipe_input=True)
            data = output
        self._pipe_input = None
        return output

    def _run_script(self, path: str) -> str:
        target = path.removeprefix("./")
        if not self.fs.exists(target):
            return f"bash: {path}: No such file or directory"
        if self.fs.isdir(self.fs.abspath(target)):
            return f"bash: {path}: Is a directory"
        if not self.fs.can_execute(target, self.env.get("USER", "student")):
            return f"bash: {path}: Permission denied"
        content = self.fs.read(target) or ""
        outputs: list[str] = []
        for raw in content.splitlines():
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            out = self.execute(stripped, record=False)
            if out:
                outputs.append(out)
        return "\n".join(outputs)

    def _eval_test(self, cond: str) -> bool:
        try:
            parts = shlex.split(cond)
        except ValueError:
            parts = cond.split()
        parts = [expand_vars(p, self) for p in parts]
        if len(parts) == 2:
            flag, operand = parts
            if flag == "-f":
                return self.fs.isfile(operand)
            if flag == "-d":
                return self.fs.isdir(operand)
            if flag == "-e":
                return self.fs.exists(operand)
            if flag == "-z":
                return operand == ""
            if flag == "-n":
                return operand != ""
        if len(parts) == 3:
            a, op, b = parts
            if op in ("=", "=="):
                return a == b
            if op == "!=":
                return a != b
        return False

    def _exec_if(self, line: str) -> str:
        m = _IF_RE.match(line)
        if not m:
            return "bash: syntax error near unexpected token `if'"
        cond, body = m.group(1), m.group(2)
        if self._eval_test(cond):
            return self.execute(body, record=False)
        return ""

    def _exec_for(self, line: str) -> str:
        m = _FOR_RE.match(line)
        if not m:
            return "bash: syntax error near unexpected token `for'"
        var, items_raw, body = m.group(1), m.group(2), m.group(3)
        try:
            items = shlex.split(expand_vars(items_raw, self))
        except ValueError:
            items = expand_vars(items_raw, self).split()
        outputs: list[str] = []
        for item in items:
            self.vars[var] = item
            out = self.execute(body, record=False)
            if out:
                outputs.append(out)
        return "\n".join(outputs)

    def complete(self, partial: str) -> list[str]:
        return autocomplete(partial, self.fs)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "fs": self.fs.to_dict(),
            "env": self.env,
            "vars": self.vars,
            "history": self.history[-50:],
            "prompt": self.prompt,
        }
        if self.network is not None:
            d["network"] = self.network.to_dict()
        if self.packet_lab is not None:
            d["packet_lab"] = self.packet_lab.to_dict()
        if self.web_lab is not None:
            d["web_lab"] = self.web_lab.to_dict()
        if self.proxy_lab is not None:
            d["proxy_lab"] = self.proxy_lab.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Shell:
        fs = VirtualFS.from_dict(d.get("fs", {}))
        sh = cls(fs=fs)
        sh.env = d.get("env", sh.env)
        sh.vars = d.get("vars", {})
        sh.history = d.get("history", [])
        # A saved network *mutation* snapshot, if any — MissionRunner
        # rebuilds the static topology from the mission config and then
        # replays this onto it (see MissionRunner._attach_network).
        sh._pending_network_state = d.get("network")
        # Same idea for which capture was open / selected / last filtered
        # (see MissionRunner._attach_packet_lab).
        sh._pending_packet_lab_state = d.get("packet_lab")
        # Same idea for the web session's cookie jar / history / server-
        # side login state (see MissionRunner._attach_web_lab).
        sh._pending_web_lab_state = d.get("web_lab")
        # Same idea for the proxy's intercept/history/Repeater state (see
        # MissionRunner._attach_proxy_lab).
        sh._pending_proxy_lab_state = d.get("proxy_lab")
        return sh
