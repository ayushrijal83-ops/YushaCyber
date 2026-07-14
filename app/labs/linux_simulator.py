"""Linux simulator — a Lab Engine plugin.

THE ONLY FILE IN THE CODEBASE THAT CONTAINS LINUX LOGIC. The engine, the
service layer, the routes and the models know nothing about `ls` or `cd`;
they only know "a simulator". Delete this file and the engine still runs —
that is the test of the architecture.

=== SAFETY ===
Nothing here executes. No subprocess, no os.system, no shell, no eval, no
real filesystem access. `ls` walks a Python dict; `cat` reads a string that
was seeded into the database. Every response is computed from in-memory
simulated state.

=== SUPPORTED COMMANDS (Phase 1) ===
    pwd  ls  cd  cat  mkdir  touch  clear  help
Anything else returns a simulated "command not found".
"""

from __future__ import annotations

from typing import Any

from app.labs.registry import register_simulator
from app.labs.simulator_base import (
    CAP_TERMINAL,
    Action,
    ActionResult,
    Simulator,
)

_ROOT = "/"
_HOME = "/home/student"


# ---------------------------------------------------------------------------
# Virtual filesystem helpers — pure dict manipulation, no OS involved.
# The tree is: {"/": {"type":"dir","children":{...}}, ...} flattened to a
# path->node map, which keeps lookups trivial and JSON-serialisable.
# ---------------------------------------------------------------------------
def _normalise(path: str) -> str:
    """Collapse '.', '..' and duplicate slashes inside the VIRTUAL tree.

    Traversal is meaningless here: there is no real filesystem to escape to.
    '../../..' simply lands on '/'.
    """
    parts: list[str] = []
    for part in (path or "").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/" + "/".join(parts) if parts else _ROOT


def _resolve(cwd: str, target: str) -> str:
    """Resolve a possibly-relative target against the current directory."""
    target = (target or "").strip()
    if not target or target == "~":
        return _HOME
    if target.startswith("~/"):
        return _normalise(_HOME + "/" + target[2:])
    if target.startswith("/"):
        return _normalise(target)
    return _normalise(f"{cwd}/{target}")


def _parent(path: str) -> str:
    if path == _ROOT:
        return _ROOT
    return _normalise(path.rsplit("/", 1)[0] or _ROOT)


def _basename(path: str) -> str:
    return path.rstrip("/").rsplit("/", 1)[-1] or _ROOT


def _children(fs: dict, path: str) -> list[str]:
    """Immediate children of a directory path."""
    path = path.rstrip("/") or _ROOT
    out: list[str] = []
    for p in fs:
        if p == path or p == _ROOT:
            continue
        if _parent(p) == (path if path != _ROOT else _ROOT):
            out.append(p)
    return sorted(out)


class _Cmd:
    """Parsed command: program + arguments. Parsing only — never execution."""

    def __init__(self, raw: str) -> None:
        self.raw = (raw or "").strip()
        parts = self.raw.split()
        self.program = parts[0] if parts else ""
        self.args = parts[1:] if len(parts) > 1 else []


@register_simulator
class LinuxSimulator(Simulator):
    """Simulated Linux shell over a virtual, database-seeded filesystem."""

    key = "linux"

    # -- contract -------------------------------------------------------
    def capabilities(self) -> set[str]:
        return {CAP_TERMINAL}

    def bootstrap(self, lab: Any, content: dict[str, Any]) -> dict[str, Any]:
        """Build fresh state from the lab's seeded filesystem nodes."""
        fs: dict[str, dict[str, Any]] = {
            _ROOT: {"type": "dir", "content": None,
                    "permissions": "rwxr-xr-x", "owner": "root"},
        }
        for node in content.get("filesystem", []):
            path = _normalise(node.get("path", ""))
            fs[path] = {
                "type": "dir" if node.get("node_type") == "dir" else "file",
                "content": node.get("content"),
                "permissions": node.get("permissions", "rw-r--r--"),
                "owner": node.get("owner", "user"),
            }
        # Ensure home exists even if a lab forgot to seed it.
        if _HOME not in fs:
            fs[_HOME] = {"type": "dir", "content": None,
                         "permissions": "rwxr-xr-x", "owner": "user"}

        return self.new_state_envelope(
            cwd=_HOME if _HOME in fs else _ROOT,
            fs=fs,
            env={"USER": "student", "HOME": _HOME, "SHELL": "/bin/bash"},
            history=[],
            flags={},
            prompt="student@linux-lab:~$ ",
        )

    def prompt(self, state: dict[str, Any]) -> str:
        cwd = state.get("cwd", _HOME)
        shown = "~" if cwd == _HOME else (
            "~" + cwd[len(_HOME):] if cwd.startswith(_HOME + "/") else cwd
        )
        return f"student@linux-lab:{shown}$ "

    def welcome(self, state: dict[str, Any]) -> str:
        return (
            "YushaCyber simulated Linux shell.\n"
            "This is a safe simulation — no commands run on any real system.\n"
            "Type 'help' to see available commands.\n"
        )

    def handle(self, state: dict[str, Any], action: Action) -> ActionResult:
        """Pure: (state, action) -> ActionResult. No side effects, no I/O."""
        if action.type != "command":
            return ActionResult(
                output="This lab only accepts terminal commands.",
                new_state=state,
            )

        state = dict(state)                     # never mutate the caller's dict
        state["fs"] = dict(state.get("fs", {}))
        state["flags"] = dict(state.get("flags", {}))

        cmd = _Cmd(action.command)
        if not cmd.program:
            return ActionResult(output="", new_state=state)

        history = list(state.get("history", []))[-99:]
        history.append(cmd.raw)
        state["history"] = history

        handler = {
            "pwd": self._pwd,
            "ls": self._ls,
            "cd": self._cd,
            "cat": self._cat,
            "mkdir": self._mkdir,
            "touch": self._touch,
            "clear": self._clear,
            "help": self._help,
        }.get(cmd.program)

        if handler is None:
            return ActionResult(
                output=f"{cmd.program}: command not found",
                new_state=state,
            )

        result = handler(state, cmd)
        result.new_state["prompt"] = self.prompt(result.new_state)
        return result

    # -- command handlers (all pure) -------------------------------------
    def _pwd(self, state: dict, cmd: _Cmd) -> ActionResult:
        return ActionResult(output=state.get("cwd", _HOME), new_state=state)

    def _ls(self, state: dict, cmd: _Cmd) -> ActionResult:
        fs = state["fs"]
        target = _resolve(state["cwd"], cmd.args[0]) if cmd.args else state["cwd"]
        node = fs.get(target)
        if node is None:
            return ActionResult(
                output=f"ls: cannot access '{cmd.args[0] if cmd.args else target}':"
                       " No such file or directory",
                new_state=state,
            )
        if node["type"] == "file":
            return ActionResult(output=_basename(target), new_state=state)

        names = []
        for child in _children(fs, target):
            name = _basename(child)
            names.append(name + ("/" if fs[child]["type"] == "dir" else ""))
        return ActionResult(output="  ".join(names), new_state=state)

    def _cd(self, state: dict, cmd: _Cmd) -> ActionResult:
        fs = state["fs"]
        target = _resolve(state["cwd"], cmd.args[0] if cmd.args else "~")
        node = fs.get(target)
        if node is None:
            return ActionResult(
                output=f"cd: {cmd.args[0] if cmd.args else '~'}:"
                       " No such file or directory",
                new_state=state,
            )
        if node["type"] != "dir":
            return ActionResult(
                output=f"cd: {cmd.args[0]}: Not a directory", new_state=state
            )
        state["cwd"] = target
        return ActionResult(output="", new_state=state)

    def _cat(self, state: dict, cmd: _Cmd) -> ActionResult:
        if not cmd.args:
            return ActionResult(output="cat: missing operand", new_state=state)
        fs = state["fs"]
        target = _resolve(state["cwd"], cmd.args[0])
        node = fs.get(target)
        if node is None:
            return ActionResult(
                output=f"cat: {cmd.args[0]}: No such file or directory",
                new_state=state,
            )
        if node["type"] == "dir":
            return ActionResult(
                output=f"cat: {cmd.args[0]}: Is a directory", new_state=state
            )
        return ActionResult(output=node.get("content") or "", new_state=state)

    def _mkdir(self, state: dict, cmd: _Cmd) -> ActionResult:
        if not cmd.args:
            return ActionResult(output="mkdir: missing operand", new_state=state)
        fs = state["fs"]
        target = _resolve(state["cwd"], cmd.args[0])
        if target in fs:
            return ActionResult(
                output=f"mkdir: cannot create directory '{cmd.args[0]}':"
                       " File exists",
                new_state=state,
            )
        if _parent(target) not in fs:
            return ActionResult(
                output=f"mkdir: cannot create directory '{cmd.args[0]}':"
                       " No such file or directory",
                new_state=state,
            )
        fs[target] = {"type": "dir", "content": None,
                      "permissions": "rwxr-xr-x", "owner": "user"}
        state["flags"][f"created_dir:{_basename(target)}"] = True
        return ActionResult(
            output="", new_state=state,
            events=[{"type": "fs_created", "path": target, "node_type": "dir"}],
        )

    def _touch(self, state: dict, cmd: _Cmd) -> ActionResult:
        if not cmd.args:
            return ActionResult(output="touch: missing file operand",
                                new_state=state)
        fs = state["fs"]
        target = _resolve(state["cwd"], cmd.args[0])
        if _parent(target) not in fs:
            return ActionResult(
                output=f"touch: cannot touch '{cmd.args[0]}':"
                       " No such file or directory",
                new_state=state,
            )
        if target not in fs:
            fs[target] = {"type": "file", "content": "",
                          "permissions": "rw-r--r--", "owner": "user"}
        state["flags"][f"created_file:{_basename(target)}"] = True
        return ActionResult(
            output="", new_state=state,
            events=[{"type": "fs_created", "path": target, "node_type": "file"}],
        )

    def _clear(self, state: dict, cmd: _Cmd) -> ActionResult:
        return ActionResult(output="", new_state=state, clear=True)

    def _help(self, state: dict, cmd: _Cmd) -> ActionResult:
        return ActionResult(
            output=(
                "Available commands:\n"
                "  pwd            print the current directory\n"
                "  ls [path]      list directory contents\n"
                "  cd <dir>       change directory\n"
                "  cat <file>     show a file's contents\n"
                "  mkdir <dir>    create a directory\n"
                "  touch <file>   create an empty file\n"
                "  clear          clear the screen\n"
                "  help           show this message\n"
                "\nThis is a simulation — nothing runs on a real system."
            ),
            new_state=state,
        )
