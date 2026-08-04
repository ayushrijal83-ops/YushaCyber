"""Virtual filesystem — isolated in-memory file tree.

No real system files are accessed. Everything lives in a dict.
"""

from __future__ import annotations

import copy
from typing import Any


class VirtualFS:
    """Simulated filesystem for lab exercises."""

    def __init__(self, tree: dict[str, Any] | None = None,
                 home: str = "/home/student") -> None:
        self._tree: dict[str, Any] = tree or self._default_tree()
        self.cwd = home
        self.home = home
        self.history: list[str] = []

    @staticmethod
    def _default_tree() -> dict[str, Any]:
        return {
            "/": {
                "home": {
                    "student": {
                        "notes.txt": "Lab notes go here.\n",
                        "Desktop": {},
                        "Documents": {},
                    }
                },
                "var": {"log": {"syslog": "Jan 1 00:00:01 host sshd[1234]: Accepted password for admin\n"}},
                "etc": {"passwd": "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000::/home/student:/bin/bash\n",
                        "shadow": "[Permission denied]\n",
                        "hosts": "127.0.0.1 localhost\n"},
                "tmp": {},
            }
        }

    def _resolve(self, path: str) -> list[str]:
        """Resolve a path string to a list of components."""
        if not path.startswith("/"):
            path = self.cwd.rstrip("/") + "/" + path
        parts: list[str] = []
        for p in path.split("/"):
            if p == "" or p == ".":
                continue
            elif p == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(p)
        return parts

    def _navigate(self, parts: list[str]) -> Any:
        node: Any = self._tree["/"]
        for p in parts:
            if isinstance(node, dict) and p in node:
                node = node[p]
            else:
                return None
        return node

    def _parent(self, parts: list[str]) -> tuple[dict | None, str]:
        if not parts:
            return None, ""
        parent = self._navigate(parts[:-1])
        if isinstance(parent, dict):
            return parent, parts[-1]
        return None, ""

    def abspath(self, path: str) -> str:
        parts = self._resolve(path)
        return "/" + "/".join(parts) if parts else "/"

    def exists(self, path: str) -> bool:
        return self._navigate(self._resolve(path)) is not None

    def isdir(self, path: str) -> bool:
        return isinstance(self._navigate(self._resolve(path)), dict)

    def isfile(self, path: str) -> bool:
        node = self._navigate(self._resolve(path))
        return node is not None and not isinstance(node, dict)

    def listdir(self, path: str = ".") -> list[str]:
        node = self._navigate(self._resolve(path))
        if isinstance(node, dict):
            return sorted(node.keys())
        return []

    def read(self, path: str) -> str | None:
        node = self._navigate(self._resolve(path))
        if isinstance(node, str):
            return node
        if isinstance(node, dict):
            return None  # is a directory
        return None

    def write(self, path: str, content: str) -> bool:
        parts = self._resolve(path)
        parent, name = self._parent(parts)
        if parent is not None:
            parent[name] = content
            return True
        return False

    def mkdir(self, path: str) -> bool:
        parts = self._resolve(path)
        parent, name = self._parent(parts)
        if parent is not None and name not in parent:
            parent[name] = {}
            return True
        return False

    def remove(self, path: str) -> bool:
        parts = self._resolve(path)
        parent, name = self._parent(parts)
        if parent is not None and name in parent:
            del parent[name]
            return True
        return False

    def copy(self, src: str, dst: str) -> bool:
        node = self._navigate(self._resolve(src))
        if node is None:
            return False
        parts = self._resolve(dst)
        parent, name = self._parent(parts)
        if parent is not None:
            parent[name] = copy.deepcopy(node) if isinstance(node, dict) else node
            return True
        return False

    def move(self, src: str, dst: str) -> bool:
        if self.copy(src, dst):
            return self.remove(src)
        return False

    def cd(self, path: str) -> bool:
        target = self.abspath(path)
        if self.isdir(target):
            self.cwd = target
            return True
        return False

    def tree(self, path: str = ".", depth: int = 3,
             _indent: int = 0) -> str:
        """Render a tree view."""
        parts = self._resolve(path)
        node = self._navigate(parts)
        if not isinstance(node, dict):
            return ""
        lines: list[str] = []
        if _indent == 0:
            lines.append(self.abspath(path))
        for name in sorted(node.keys()):
            prefix = "│   " * _indent + "├── "
            child = node[name]
            if isinstance(child, dict):
                lines.append(f"{prefix}{name}/")
                if depth > 1:
                    lines.append(self.tree(
                        self.abspath(path) + "/" + name,
                        depth - 1, _indent + 1))
            else:
                lines.append(f"{prefix}{name}")
        return "\n".join(line for line in lines if line)

    def to_dict(self) -> dict[str, Any]:
        return {"tree": self._tree, "cwd": self.cwd, "home": self.home}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VirtualFS:
        fs = cls(tree=data.get("tree"), home=data.get("home", "/home/student"))
        fs.cwd = data.get("cwd", fs.home)
        return fs
