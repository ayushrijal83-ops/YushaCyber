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

import re

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
                "owner": node.get("owner", "student"),
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
            # Lab 1 — basics
            "pwd": self._pwd, "ls": self._ls, "cd": self._cd, "cat": self._cat,
            "mkdir": self._mkdir, "touch": self._touch,
            "clear": self._clear, "help": self._help,
            # Lab 2 — files & directories
            "cp": self._cp, "mv": self._mv, "rm": self._rm,
            "rmdir": self._rmdir, "tree": self._tree,
            # Lab 3 — permissions
            "chmod": self._chmod, "chown": self._chown, "whoami": self._whoami,
            # Lab 4 — searching
            "find": self._find, "grep": self._grep,
            "which": self._which, "locate": self._locate,
            # Lab 5 — archives
            "tar": self._tar, "zip": self._zip, "unzip": self._unzip,
            # Lab 6 — processes
            "ps": self._ps, "top": self._top, "kill": self._kill, "jobs": self._jobs,
            # Lab 7 — networking
            "ping": self._ping, "hostname": self._hostname,
            "ip": self._ip, "curl": self._curl,
            # Lab 8 — logs
            "tail": self._tail, "head": self._head, "wc": self._wc,
            # misc
            "echo": self._echo,
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
        long_fmt = any(a.startswith("-") and "l" in a for a in cmd.args)
        show_all = any(a.startswith("-") and "a" in a for a in cmd.args)
        positional = [a for a in cmd.args if not a.startswith("-")]
        target = _resolve(state["cwd"], positional[0]) if positional else state["cwd"]
        node = fs.get(target)
        if node is None:
            return ActionResult(
                output=f"ls: cannot access '{cmd.args[0] if cmd.args else target}':"
                       " No such file or directory",
                new_state=state,
            )
        if node["type"] == "file":
            if long_fmt:
                return ActionResult(output=self._long_line(node, _basename(target)),
                                    new_state=state,
                                    events=[{"type": "ls", "long": True}])
            return ActionResult(output=_basename(target), new_state=state)

        kids = _children(fs, target)

        if long_fmt:
            lines = [f"total {len(kids)}"]
            for child in kids:
                lines.append(self._long_line(fs[child], _basename(child)))
            return ActionResult(output="\n".join(lines), new_state=state,
                                events=[{"type": "ls", "long": True}])

        names = []
        for child in kids:
            name = _basename(child)
            names.append(name + ("/" if fs[child]["type"] == "dir" else ""))
        return ActionResult(output="  ".join(names), new_state=state,
                            events=[{"type": "ls", "long": False}])

    @staticmethod
    def _long_line(node: dict, name: str) -> str:
        """One `ls -l` row, rendered from the node's simulated metadata."""
        kind = "d" if node["type"] == "dir" else "-"
        perms = node.get("permissions", "rw-r--r--")
        owner = node.get("owner", "student")
        size = len(node.get("content") or "") if node["type"] == "file" else 4096
        return f"{kind}{perms} 1 {owner} {owner} {size:>6} Jul 14 09:12 {name}"

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


    # ======================================================================
    # Lab 2 — Files & Directories
    # ======================================================================
    def _cp(self, state: dict, cmd: _Cmd) -> ActionResult:
        args = [a for a in cmd.args if not a.startswith("-")]
        recursive = any(a in ("-r", "-R", "--recursive") for a in cmd.args)
        if len(args) < 2:
            return ActionResult(output="cp: missing file operand", new_state=state)
        fs = state["fs"]
        src = _resolve(state["cwd"], args[0])
        dst = _resolve(state["cwd"], args[1])
        node = fs.get(src)
        if node is None:
            return ActionResult(output=f"cp: cannot stat '{args[0]}': No such file or directory", new_state=state)
        if node["type"] == "dir" and not recursive:
            return ActionResult(output=f"cp: -r not specified; omitting directory '{args[0]}'", new_state=state)

        # copying INTO an existing directory keeps the basename
        if dst in fs and fs[dst]["type"] == "dir" and node["type"] == "file":
            dst = _normalise(f"{dst}/{_basename(src)}")
        if _parent(dst) not in fs:
            return ActionResult(output=f"cp: cannot create '{args[1]}': No such file or directory", new_state=state)

        fs[dst] = dict(node)
        if node["type"] == "dir":  # copy the subtree
            for path in [p for p in list(fs) if p.startswith(src + "/")]:
                fs[_normalise(dst + path[len(src):])] = dict(fs[path])
        state["flags"][f"copied:{_basename(dst)}"] = True
        return ActionResult(output="", new_state=state,
                            events=[{"type": "fs_copied", "src": src, "dst": dst}])

    def _mv(self, state: dict, cmd: _Cmd) -> ActionResult:
        args = [a for a in cmd.args if not a.startswith("-")]
        if len(args) < 2:
            return ActionResult(output="mv: missing file operand", new_state=state)
        fs = state["fs"]
        src = _resolve(state["cwd"], args[0])
        dst = _resolve(state["cwd"], args[1])
        if src not in fs:
            return ActionResult(output=f"mv: cannot stat '{args[0]}': No such file or directory", new_state=state)
        if dst in fs and fs[dst]["type"] == "dir" and fs[src]["type"] == "file":
            dst = _normalise(f"{dst}/{_basename(src)}")
        if _parent(dst) not in fs:
            return ActionResult(output=f"mv: cannot move '{args[0]}': No such file or directory", new_state=state)

        moved = [src] + [p for p in list(fs) if p.startswith(src + "/")]
        for path in moved:
            fs[_normalise(dst + path[len(src):])] = fs.pop(path)
        state["flags"][f"moved:{_basename(dst)}"] = True
        return ActionResult(output="", new_state=state,
                            events=[{"type": "fs_moved", "src": src, "dst": dst}])

    def _rm(self, state: dict, cmd: _Cmd) -> ActionResult:
        args = [a for a in cmd.args if not a.startswith("-")]
        recursive = any(a in ("-r", "-R", "-rf", "-fr", "--recursive") for a in cmd.args)
        if not args:
            return ActionResult(output="rm: missing operand", new_state=state)
        fs = state["fs"]
        target = _resolve(state["cwd"], args[0])
        node = fs.get(target)
        if node is None:
            return ActionResult(output=f"rm: cannot remove '{args[0]}': No such file or directory", new_state=state)
        if node["type"] == "dir" and not recursive:
            return ActionResult(output=f"rm: cannot remove '{args[0]}': Is a directory", new_state=state)
        for path in [target] + [p for p in list(fs) if p.startswith(target + "/")]:
            fs.pop(path, None)
        state["flags"][f"removed:{_basename(target)}"] = True
        return ActionResult(output="", new_state=state,
                            events=[{"type": "fs_removed", "path": target}])

    def _rmdir(self, state: dict, cmd: _Cmd) -> ActionResult:
        if not cmd.args:
            return ActionResult(output="rmdir: missing operand", new_state=state)
        fs = state["fs"]
        target = _resolve(state["cwd"], cmd.args[0])
        node = fs.get(target)
        if node is None:
            return ActionResult(output=f"rmdir: failed to remove '{cmd.args[0]}': No such file or directory", new_state=state)
        if node["type"] != "dir":
            return ActionResult(output=f"rmdir: failed to remove '{cmd.args[0]}': Not a directory", new_state=state)
        if _children(fs, target):
            return ActionResult(output=f"rmdir: failed to remove '{cmd.args[0]}': Directory not empty", new_state=state)
        fs.pop(target)
        state["flags"][f"removed:{_basename(target)}"] = True
        return ActionResult(output="", new_state=state,
                            events=[{"type": "fs_removed", "path": target}])

    def _tree(self, state: dict, cmd: _Cmd) -> ActionResult:
        fs = state["fs"]
        root = _resolve(state["cwd"], cmd.args[0]) if cmd.args else state["cwd"]
        if root not in fs:
            return ActionResult(output=f"tree: {cmd.args[0] if cmd.args else root}: No such file or directory", new_state=state)

        lines = ["."]
        dirs = files = 0

        def walk(path: str, prefix: str) -> None:
            nonlocal dirs, files
            kids = _children(fs, path)
            for i, child in enumerate(kids):
                last = (i == len(kids) - 1)
                branch = "`-- " if last else "|-- "
                lines.append(prefix + branch + _basename(child))
                if fs[child]["type"] == "dir":
                    dirs += 1
                    walk(child, prefix + ("    " if last else "|   "))
                else:
                    files += 1

        walk(root, "")
        lines.append("")
        lines.append(f"{dirs} directories, {files} files")
        return ActionResult(output="\n".join(lines), new_state=state)

    # ======================================================================
    # Lab 3 — Permissions
    # ======================================================================
    _PERM_MAP = {"7": "rwx", "6": "rw-", "5": "r-x", "4": "r--",
                 "3": "-wx", "2": "-w-", "1": "--x", "0": "---"}

    def _chmod(self, state: dict, cmd: _Cmd) -> ActionResult:
        if len(cmd.args) < 2:
            return ActionResult(output="chmod: missing operand", new_state=state)
        mode, target_name = cmd.args[0], cmd.args[1]
        fs = state["fs"]
        target = _resolve(state["cwd"], target_name)
        if target not in fs:
            return ActionResult(output=f"chmod: cannot access '{target_name}': No such file or directory", new_state=state)
        if len(mode) == 3 and all(c in self._PERM_MAP for c in mode):
            fs[target] = dict(fs[target])
            fs[target]["permissions"] = "".join(self._PERM_MAP[c] for c in mode)
            state["flags"].setdefault("chmod", {})[_basename(target).replace(".", "_")] = mode
            return ActionResult(output="", new_state=state,
                                events=[{"type": "chmod", "path": target, "mode": mode}])
        return ActionResult(output=f"chmod: invalid mode: '{mode}'", new_state=state)

    def _chown(self, state: dict, cmd: _Cmd) -> ActionResult:
        if len(cmd.args) < 2:
            return ActionResult(output="chown: missing operand", new_state=state)
        owner, target_name = cmd.args[0], cmd.args[1]
        fs = state["fs"]
        target = _resolve(state["cwd"], target_name)
        if target not in fs:
            return ActionResult(output=f"chown: cannot access '{target_name}': No such file or directory", new_state=state)
        fs[target] = dict(fs[target])
        fs[target]["owner"] = owner.split(":")[0]
        state["flags"].setdefault("chown", {})[_basename(target).replace(".", "_")] = owner
        return ActionResult(output="", new_state=state,
                            events=[{"type": "chown", "path": target, "owner": owner}])

    def _whoami(self, state: dict, cmd: _Cmd) -> ActionResult:
        return ActionResult(output=state.get("env", {}).get("USER", "student"), new_state=state)

    # ======================================================================
    # Lab 4 — Searching
    # ======================================================================
    def _find(self, state: dict, cmd: _Cmd) -> ActionResult:
        fs = state["fs"]
        root = state["cwd"]
        name = None
        args = list(cmd.args)
        if args and not args[0].startswith("-"):
            root = _resolve(state["cwd"], args.pop(0))
        if "-name" in args:
            i = args.index("-name")
            if i + 1 < len(args):
                name = args[i + 1].strip("'\"")
        if root not in fs:
            return ActionResult(output=f"find: '{root}': No such file or directory", new_state=state)

        hits = [p for p in sorted(fs) if p == root or p.startswith(root.rstrip("/") + "/")]
        if name:
            pat = "^" + re.escape(name).replace(r"\*", ".*").replace(r"\?", ".") + "$"
            hits = [p for p in hits if re.match(pat, _basename(p))]
        return ActionResult(output="\n".join(hits) if hits else "", new_state=state)

    def _grep(self, state: dict, cmd: _Cmd) -> ActionResult:
        args = [a for a in cmd.args if not a.startswith("-")]
        ignore_case = any(a in ("-i",) for a in cmd.args)
        recursive = any(a in ("-r", "-R") for a in cmd.args)
        if len(args) < 2:
            return ActionResult(output="usage: grep [OPTION]... PATTERN [FILE]...", new_state=state)

        pattern, target_name = args[0].strip("'\""), args[1]
        fs = state["fs"]
        target = _resolve(state["cwd"], target_name)
        flags = re.IGNORECASE if ignore_case else 0

        targets = []
        if target in fs and fs[target]["type"] == "dir":
            if not recursive:
                return ActionResult(output=f"grep: {target_name}: Is a directory", new_state=state)
            targets = [p for p in sorted(fs)
                       if p.startswith(target.rstrip("/") + "/") and fs[p]["type"] == "file"]
        elif target in fs:
            targets = [target]
        else:
            return ActionResult(output=f"grep: {target_name}: No such file or directory", new_state=state)

        out = []
        for path in targets:
            for ln in (fs[path].get("content") or "").split("\n"):
                try:
                    if re.search(pattern, ln, flags):
                        out.append(f"{path}:{ln}" if len(targets) > 1 else ln)
                except re.error:
                    return ActionResult(output=f"grep: invalid pattern: {pattern}", new_state=state)
        if out:
            state["flags"]["grep_matched"] = True
        return ActionResult(output="\n".join(out), new_state=state,
                            events=[{"type": "grep", "pattern": pattern, "hits": len(out)}])

    def _which(self, state: dict, cmd: _Cmd) -> ActionResult:
        if not cmd.args:
            return ActionResult(output="", new_state=state)
        known = {"ls": "/bin/ls", "cat": "/bin/cat", "grep": "/usr/bin/grep",
                 "find": "/usr/bin/find", "python3": "/usr/bin/python3",
                 "bash": "/bin/bash", "tar": "/bin/tar", "curl": "/usr/bin/curl",
                 "ping": "/bin/ping", "ps": "/bin/ps", "chmod": "/bin/chmod"}
        prog = cmd.args[0]
        path = known.get(prog)
        if path:
            return ActionResult(output=path, new_state=state,
                                events=[{"type": "which", "program": prog}])
        return ActionResult(output=f"which: no {prog} in (/usr/bin:/bin)", new_state=state)

    def _locate(self, state: dict, cmd: _Cmd) -> ActionResult:
        if not cmd.args:
            return ActionResult(output="locate: no pattern to search for specified", new_state=state)
        needle = cmd.args[0].strip("'\"")
        fs = state["fs"]
        hits = [p for p in sorted(fs) if needle.lower() in p.lower() and p != _ROOT]
        return ActionResult(output="\n".join(hits) if hits else "", new_state=state)

    # ======================================================================
    # Lab 5 — Archives
    # ======================================================================
    def _tar(self, state: dict, cmd: _Cmd) -> ActionResult:
        if not cmd.args:
            return ActionResult(output="tar: You must specify one of the '-Acdtrux' options", new_state=state)
        flags = cmd.args[0].lstrip("-")
        rest = cmd.args[1:]
        fs = state["fs"]

        # create:  tar -cf archive.tar files...
        if "c" in flags:
            if not rest:
                return ActionResult(output="tar: Cowardly refusing to create an empty archive", new_state=state)
            archive = _resolve(state["cwd"], rest[0])
            members = [_resolve(state["cwd"], m) for m in rest[1:]] or [state["cwd"]]
            listed = []
            for m in members:
                if m in fs:
                    listed.append(_basename(m))
                    listed += [p[len(m) + 1:] for p in sorted(fs) if p.startswith(m + "/")]
            fs[archive] = {"type": "file", "content": "\n".join(listed),
                           "permissions": "rw-r--r--", "owner": "student",
                           "archive": listed}
            state["flags"][f"tar_created:{_basename(archive)}"] = True
            out = "\n".join(listed) if "v" in flags else ""
            return ActionResult(output=out, new_state=state,
                                events=[{"type": "tar_create", "archive": archive}])

        # list:  tar -tf archive.tar
        if "t" in flags:
            if not rest:
                return ActionResult(output="tar: Refusing to read archive contents", new_state=state)
            archive = _resolve(state["cwd"], rest[0])
            node = fs.get(archive)
            if node is None:
                return ActionResult(output=f"tar: {rest[0]}: Cannot open: No such file or directory", new_state=state)
            return ActionResult(output=node.get("content") or "", new_state=state,
                                events=[{"type": "tar_list", "archive": archive}])

        # extract:  tar -xf archive.tar
        if "x" in flags:
            if not rest:
                return ActionResult(output="tar: Refusing to read archive contents", new_state=state)
            archive = _resolve(state["cwd"], rest[0])
            node = fs.get(archive)
            if node is None:
                return ActionResult(output=f"tar: {rest[0]}: Cannot open: No such file or directory", new_state=state)
            names = [n for n in (node.get("content") or "").split("\n") if n.strip()]
            for name in names:
                path = _resolve(state["cwd"], name)
                if path not in fs:
                    is_dir = "." not in _basename(path)
                    fs[path] = {"type": "dir" if is_dir else "file",
                                "content": None if is_dir else "restored from archive",
                                "permissions": "rw-r--r--", "owner": "student"}
            state["flags"][f"tar_extracted:{_basename(archive)}"] = True
            out = "\n".join(names) if "v" in flags else ""
            return ActionResult(output=out, new_state=state,
                                events=[{"type": "tar_extract", "archive": archive}])

        return ActionResult(output=f"tar: unknown option -- '{flags}'", new_state=state)

    def _zip(self, state: dict, cmd: _Cmd) -> ActionResult:
        args = [a for a in cmd.args if not a.startswith("-")]
        if len(args) < 2:
            return ActionResult(output="zip: nothing to do!", new_state=state)
        fs = state["fs"]
        archive = _resolve(state["cwd"], args[0] if args[0].endswith(".zip") else args[0] + ".zip")
        members, out = [], []
        for name in args[1:]:
            path = _resolve(state["cwd"], name)
            if path in fs:
                members.append(_basename(path))
                out.append(f"  adding: {_basename(path)} (stored 0%)")
        fs[archive] = {"type": "file", "content": "\n".join(members),
                       "permissions": "rw-r--r--", "owner": "student"}
        state["flags"][f"zip_created:{_basename(archive)}"] = True
        return ActionResult(output="\n".join(out), new_state=state,
                            events=[{"type": "zip_create", "archive": archive}])

    def _unzip(self, state: dict, cmd: _Cmd) -> ActionResult:
        if not cmd.args:
            return ActionResult(output="UnZip: missing archive", new_state=state)
        fs = state["fs"]
        archive = _resolve(state["cwd"], cmd.args[0])
        node = fs.get(archive)
        if node is None:
            return ActionResult(output=f"unzip:  cannot find or open {cmd.args[0]}", new_state=state)
        names = [n for n in (node.get("content") or "").split("\n") if n.strip()]
        out = [f"Archive:  {_basename(archive)}"]
        for name in names:
            path = _resolve(state["cwd"], name)
            if path not in fs:
                fs[path] = {"type": "file", "content": "restored from archive",
                            "permissions": "rw-r--r--", "owner": "student"}
            out.append(f"  inflating: {name}")
        state["flags"][f"unzipped:{_basename(archive)}"] = True
        return ActionResult(output="\n".join(out), new_state=state,
                            events=[{"type": "unzip", "archive": archive}])

    # ======================================================================
    # Lab 6 — Processes (simulated process table in state)
    # ======================================================================
    def _procs(self, state: dict) -> list:
        if "procs" not in state:
            state["procs"] = [
                {"pid": 1, "user": "root", "cpu": 0.0, "mem": 0.1, "cmd": "/sbin/init"},
                {"pid": 412, "user": "root", "cpu": 0.1, "mem": 0.4, "cmd": "/usr/sbin/sshd"},
                {"pid": 883, "user": "student", "cpu": 0.0, "mem": 0.2, "cmd": "-bash"},
                {"pid": 1204, "user": "student", "cpu": 12.6, "mem": 3.1, "cmd": "python3 train.py"},
                {"pid": 1337, "user": "student", "cpu": 88.2, "mem": 6.7, "cmd": "./stress_test"},
            ]
        return state["procs"]

    def _ps(self, state: dict, cmd: _Cmd) -> ActionResult:
        procs = self._procs(state)
        lines = ["  PID TTY          TIME CMD"]
        for p in procs:
            lines.append(f"{p['pid']:>5} pts/0    00:00:0{p['pid'] % 9} {p['cmd']}")
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "ps"}])

    def _top(self, state: dict, cmd: _Cmd) -> ActionResult:
        procs = self._procs(state)
        lines = [
            "top - 09:41:02 up 2:13,  1 user,  load average: 0.42, 0.31, 0.28",
            f"Tasks: {len(procs)} total,   1 running,  {len(procs)-1} sleeping",
            "%Cpu(s): 14.2 us,  2.1 sy,  0.0 ni, 83.1 id",
            "",
            "  PID USER      %CPU  %MEM  COMMAND",
        ]
        for p in sorted(procs, key=lambda x: -x["cpu"]):
            lines.append(f"{p['pid']:>5} {p['user']:<9} {p['cpu']:>4} {p['mem']:>5}  {p['cmd']}")
        lines.append("")
        lines.append("(simulated snapshot — press q to quit in a real terminal)")
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "top"}])

    def _kill(self, state: dict, cmd: _Cmd) -> ActionResult:
        args = [a for a in cmd.args if not a.startswith("-")]
        if not args:
            return ActionResult(output="kill: usage: kill [-signal] pid", new_state=state)
        try:
            pid = int(args[0])
        except ValueError:
            return ActionResult(output=f"kill: {args[0]}: arguments must be process IDs", new_state=state)
        procs = self._procs(state)
        match = next((p for p in procs if p["pid"] == pid), None)
        if match is None:
            return ActionResult(output=f"kill: ({pid}) - No such process", new_state=state)
        state["procs"] = [p for p in procs if p["pid"] != pid]
        state["flags"][f"killed:{pid}"] = True
        return ActionResult(output="", new_state=state,
                            events=[{"type": "kill", "pid": pid, "cmd": match["cmd"]}])

    def _jobs(self, state: dict, cmd: _Cmd) -> ActionResult:
        return ActionResult(
            output="[1]+  Running                 python3 train.py &",
            new_state=state, events=[{"type": "jobs"}],
        )

    # ======================================================================
    # Lab 7 — Networking (all simulated; no sockets are ever opened)
    # ======================================================================
    def _ping(self, state: dict, cmd: _Cmd) -> ActionResult:
        args = [a for a in cmd.args if not a.startswith("-")]
        if not args:
            return ActionResult(output="ping: usage error: Destination address required", new_state=state)
        host = args[0]
        ip = "93.184.216.34" if host != "localhost" else "127.0.0.1"
        lines = [f"PING {host} ({ip}) 56(84) bytes of data."]
        for i in range(1, 4):
            lines.append(f"64 bytes from {ip}: icmp_seq={i} ttl=56 time={10 + i * 3}.{i} ms")
        lines += ["", f"--- {host} ping statistics ---",
                  "3 packets transmitted, 3 received, 0% packet loss"]
        state["flags"][f"pinged:{host}"] = True
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "ping", "host": host}])

    def _hostname(self, state: dict, cmd: _Cmd) -> ActionResult:
        return ActionResult(output="linux-lab", new_state=state,
                            events=[{"type": "hostname"}])

    def _ip(self, state: dict, cmd: _Cmd) -> ActionResult:
        sub = cmd.args[0] if cmd.args else ""
        if sub.startswith("a"):   # ip a / ip addr
            out = (
                "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536\n"
                "    inet 127.0.0.1/8 scope host lo\n"
                "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500\n"
                "    inet 10.10.14.7/24 brd 10.10.14.255 scope global eth0"
            )
            state["flags"]["ip_addr_shown"] = True
            return ActionResult(output=out, new_state=state,
                                events=[{"type": "ip", "sub": "addr"}])
        if sub.startswith("r"):   # ip route
            return ActionResult(
                output="default via 10.10.14.1 dev eth0\n10.10.14.0/24 dev eth0 proto kernel scope link",
                new_state=state, events=[{"type": "ip", "sub": "route"}])
        return ActionResult(output="Usage: ip [ addr | route ]", new_state=state)

    def _curl(self, state: dict, cmd: _Cmd) -> ActionResult:
        args = [a for a in cmd.args if not a.startswith("-")]
        if not args:
            return ActionResult(output="curl: try 'curl --help' for more information", new_state=state)
        url = args[0]
        state["flags"][f"curled:{url}"] = True
        body = (
            "<!DOCTYPE html>\n<html>\n<head><title>YushaCyber Lab</title></head>\n"
            "<body>\n  <h1>It works!</h1>\n  <p>flag: YC{simulated_http_response}</p>\n"
            "</body>\n</html>"
        )
        return ActionResult(output=body, new_state=state,
                            events=[{"type": "curl", "url": url}])

    # ======================================================================
    # Lab 8 — Logs
    # ======================================================================
    def _head(self, state: dict, cmd: _Cmd) -> ActionResult:
        return self._head_tail(state, cmd, head=True)

    def _tail(self, state: dict, cmd: _Cmd) -> ActionResult:
        return self._head_tail(state, cmd, head=False)

    def _head_tail(self, state: dict, cmd: _Cmd, head: bool) -> ActionResult:
        name = "head" if head else "tail"
        n = 10
        args = list(cmd.args)
        if "-n" in args:
            i = args.index("-n")
            if i + 1 < len(args):
                try:
                    n = int(args[i + 1])
                except ValueError:
                    pass
                args = args[:i] + args[i + 2:]
        args = [a for a in args if not a.startswith("-")]
        if not args:
            return ActionResult(output=f"{name}: missing operand", new_state=state)

        fs = state["fs"]
        target = _resolve(state["cwd"], args[0])
        node = fs.get(target)
        if node is None:
            return ActionResult(output=f"{name}: cannot open '{args[0]}': No such file or directory", new_state=state)
        if node["type"] == "dir":
            return ActionResult(output=f"{name}: error reading '{args[0]}': Is a directory", new_state=state)
        lines = (node.get("content") or "").split("\n")
        chosen = lines[:n] if head else lines[-n:]
        return ActionResult(output="\n".join(chosen), new_state=state,
                            events=[{"type": name, "path": target}])

    def _wc(self, state: dict, cmd: _Cmd) -> ActionResult:
        args = [a for a in cmd.args if not a.startswith("-")]
        lines_only = "-l" in cmd.args
        if not args:
            return ActionResult(output="wc: missing operand", new_state=state)
        fs = state["fs"]
        target = _resolve(state["cwd"], args[0])
        node = fs.get(target)
        if node is None:
            return ActionResult(output=f"wc: {args[0]}: No such file or directory", new_state=state)
        content = node.get("content") or ""
        n_lines = len(content.split("\n")) if content else 0
        if lines_only:
            return ActionResult(output=f"{n_lines} {_basename(target)}", new_state=state)
        words = len(content.split())
        return ActionResult(output=f"{n_lines} {words} {len(content)} {_basename(target)}",
                            new_state=state)

    def _echo(self, state: dict, cmd: _Cmd) -> ActionResult:
        return ActionResult(output=" ".join(cmd.args).strip("'\""), new_state=state)

    def _clear(self, state: dict, cmd: _Cmd) -> ActionResult:
        return ActionResult(output="", new_state=state, clear=True)

    def _help(self, state: dict, cmd: _Cmd) -> ActionResult:
        return ActionResult(
            output=(
                "Available commands:\n"
                "  Navigation : pwd, ls [-l], cd, tree\n"
                "  Files      : cat, touch, mkdir, cp, mv, rm, rmdir, echo\n"
                "  Permissions: chmod, chown, whoami\n"
                "  Searching  : find, grep, which, locate\n"
                "  Archives   : tar, zip, unzip\n"
                "  Processes  : ps, top, kill, jobs\n"
                "  Networking : ping, hostname, ip, curl\n"
                "  Logs       : head, tail, wc\n"
                "  Shell      : clear, help\n"
                "\nThis is a simulation — nothing runs on a real system."
            ),
            new_state=state,
        )
