"""Virtual filesystem — in-memory isolated file tree."""

from __future__ import annotations

import copy
from typing import Any

_DEFAULT_FILE_MODE = "644"
_DEFAULT_DIR_MODE = "755"
_DEFAULT_OWNER = "student"
_DEFAULT_GROUP = "student"
_PERM_BITS = {"7": "rwx", "6": "rw-", "5": "r-x", "4": "r--",
              "3": "-wx", "2": "-w-", "1": "--x", "0": "---"}


class VirtualFS:
    """Simulated filesystem. No real OS access."""

    def __init__(self, tree: dict[str, Any] | None = None,
                 home: str = "/home/student",
                 permissions: dict[str, dict[str, str]] | None = None) -> None:
        # Deep-copy: callers pass shared mission-template dicts (mission_loader
        # .MISSIONS). Without copying, mutating commands (touch/mkdir/chmod/
        # chown) would edit the shared template in place and leak state
        # across every future session for that mission.
        self._tree: dict[str, Any] = copy.deepcopy(tree) if tree else self._default()
        self.cwd = home
        self.home = home
        # Per-path permission/ownership metadata: {abspath: {mode, owner, group}}.
        # Paths with no entry fall back to the defaults below.
        self._meta: dict[str, dict[str, str]] = copy.deepcopy(permissions) if permissions else {}

    @staticmethod
    def _default() -> dict[str, Any]:
        return {
            "home": {"student": {
                "Documents": {"readme.txt": "Welcome to YushaCyber labs.\n"},
                "Downloads": {},
                "Desktop": {},
                ".bashrc": "# ~/.bashrc\nexport PS1='student@lab:~$ '\n",
            }},
            "etc": {
                "passwd": "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000::/home/student:/bin/bash\n",
                "hostname": "yushacyber-lab\n",
                "hosts": "127.0.0.1 localhost\n10.0.0.1 gateway\n",
            },
            "var": {"log": {
                "syslog": "Jan  5 08:12:01 lab sshd[2841]: Accepted password for admin from 192.168.1.50\nJan  5 08:15:33 lab sudo: student : TTY=pts/0 ; COMMAND=/usr/bin/apt update\n",
                "auth.log": "Jan  5 08:12:01 lab sshd[2841]: pam_unix(sshd:session): session opened\n",
            }},
            "tmp": {},
            "root": {".flag": "flag{y0u_f0und_th3_r00t_fl4g}\n"},
        }

    def _resolve(self, path: str) -> list[str]:
        if not path.startswith("/"):
            path = self.cwd.rstrip("/") + "/" + path
        parts: list[str] = []
        for p in path.split("/"):
            if p in ("", "."):
                continue
            elif p == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(p)
        return parts

    def _get(self, parts: list[str]) -> Any:
        node: Any = self._tree
        for p in parts:
            if isinstance(node, dict) and p in node:
                node = node[p]
            else:
                return None
        return node

    def _parent(self, parts: list[str]):
        if not parts:
            return None, ""
        parent = self._get(parts[:-1])
        return (parent, parts[-1]) if isinstance(parent, dict) else (None, "")

    def abspath(self, path: str) -> str:
        p = self._resolve(path)
        return "/" + "/".join(p) if p else "/"

    def exists(self, path: str) -> bool:
        return self._get(self._resolve(path)) is not None

    def isdir(self, path: str) -> bool:
        return isinstance(self._get(self._resolve(path)), dict)

    def isfile(self, path: str) -> bool:
        n = self._get(self._resolve(path))
        return n is not None and not isinstance(n, dict)

    def listdir(self, path: str = ".") -> list[str]:
        n = self._get(self._resolve(path))
        return sorted(n.keys()) if isinstance(n, dict) else []

    def read(self, path: str) -> str | None:
        n = self._get(self._resolve(path))
        return n if isinstance(n, str) else None

    def write(self, path: str, content: str) -> bool:
        parent, name = self._parent(self._resolve(path))
        if parent is not None:
            parent[name] = content
            return True
        return False

    def mkdir(self, path: str) -> bool:
        parent, name = self._parent(self._resolve(path))
        if parent is not None and name and name not in parent:
            parent[name] = {}
            return True
        return False

    def touch(self, path: str) -> bool:
        parent, name = self._parent(self._resolve(path))
        if parent is not None and name and name not in parent:
            parent[name] = ""
            return True
        return False

    def rm(self, path: str) -> bool:
        parent, name = self._parent(self._resolve(path))
        if parent is not None and name in parent:
            del parent[name]
            return True
        return False

    def cd(self, path: str) -> bool:
        target = self.abspath(path)
        if self.isdir(target):
            self.cwd = target
            return True
        return False

    # ── Permissions / ownership ──
    def get_mode(self, path: str) -> str:
        entry = self._meta.get(self.abspath(path))
        if entry and "mode" in entry:
            return entry["mode"]
        return _DEFAULT_DIR_MODE if self.isdir(path) else _DEFAULT_FILE_MODE

    def set_mode(self, path: str, mode: str) -> bool:
        if not self.exists(path):
            return False
        self._meta.setdefault(self.abspath(path), {})["mode"] = mode
        return True

    def get_owner(self, path: str) -> str:
        entry = self._meta.get(self.abspath(path))
        return (entry or {}).get("owner", _DEFAULT_OWNER)

    def get_group(self, path: str) -> str:
        entry = self._meta.get(self.abspath(path))
        return (entry or {}).get("group", _DEFAULT_GROUP)

    def set_owner(self, path: str, owner: str, group: str | None = None) -> bool:
        if not self.exists(path):
            return False
        entry = self._meta.setdefault(self.abspath(path), {})
        entry["owner"] = owner
        entry["group"] = group or owner
        return True

    def can_read(self, path: str, user: str = "student") -> bool:
        """Whether ``user`` can read this node, per its mode/owner bits."""
        if not self.exists(path):
            return False
        mode = self.get_mode(path).rjust(3, "0")[-3:]
        bit = mode[0] if self.get_owner(path) == user else mode[-1]
        return bit.isdigit() and int(bit) & 4 != 0

    @staticmethod
    def mode_to_symbolic(mode: str, is_dir: bool) -> str:
        mode = mode.rjust(3, "0")[-3:]
        return ("d" if is_dir else "-") + "".join(
            _PERM_BITS.get(c, "---") for c in mode)

    def tree(self, path: str = ".", depth: int = 3, _indent: int = 0) -> str:
        parts = self._resolve(path)
        node = self._get(parts)
        if not isinstance(node, dict):
            return ""
        lines: list[str] = []
        if _indent == 0:
            lines.append(self.abspath(path))
        for name in sorted(node.keys()):
            pfx = "│   " * _indent + "├── "
            if isinstance(node[name], dict):
                lines.append(f"{pfx}{name}/")
                if depth > 1:
                    sub = self.tree(self.abspath(path) + "/" + name, depth - 1, _indent + 1)
                    if sub:
                        lines.append(sub)
            else:
                lines.append(f"{pfx}{name}")
        return "\n".join(l for l in lines if l)

    def to_dict(self) -> dict[str, Any]:
        return {"tree": copy.deepcopy(self._tree), "cwd": self.cwd, "home": self.home,
                "meta": copy.deepcopy(self._meta)}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VirtualFS:
        fs = cls(tree=d.get("tree"), home=d.get("home", "/home/student"),
                  permissions=d.get("meta"))
        fs.cwd = d.get("cwd", fs.home)
        return fs
