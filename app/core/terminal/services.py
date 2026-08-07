"""Terminal services — public API + lab engine integration."""

from __future__ import annotations

from typing import Any

from app.core.terminal.shell import Shell

# Active shells: {(user_id, lab_slug): Shell}
_shells: dict[tuple[int, str], Shell] = {}


def start_shell(user_id: int, lab_slug: str = "terminal",
                fs_tree: dict[str, Any] | None = None) -> dict[str, Any]:
    """Start or resume a shell session."""
    key = (user_id, lab_slug)
    if key in _shells:
        sh = _shells[key]
    else:
        from app.core.terminal.filesystem import VirtualFS
        fs = VirtualFS(tree=fs_tree) if fs_tree else VirtualFS()
        sh = Shell(fs=fs)
        _shells[key] = sh
    return {"prompt": sh.prompt, "cwd": sh.fs.cwd}


def execute(user_id: int, lab_slug: str,
            command: str) -> dict[str, Any]:
    """Execute a command in the user's shell."""
    key = (user_id, lab_slug)
    sh = _shells.get(key)
    if sh is None:
        start_shell(user_id, lab_slug)
        sh = _shells[key]
    output = sh.execute(command)
    return {
        "output": output,
        "prompt": sh.prompt,
        "cwd": sh.fs.cwd,
        "command": command,
    }


def complete(user_id: int, lab_slug: str,
             partial: str) -> list[str]:
    sh = _shells.get((user_id, lab_slug))
    if sh is None:
        return []
    return sh.complete(partial)


def get_shell(user_id: int, lab_slug: str) -> Shell | None:
    return _shells.get((user_id, lab_slug))


def reset_shell(user_id: int, lab_slug: str) -> dict[str, Any]:
    _shells.pop((user_id, lab_slug), None)
    return start_shell(user_id, lab_slug)


def shell_context(user_id: int, lab_slug: str) -> dict[str, Any]:
    """Context for AI mentor."""
    sh = _shells.get((user_id, lab_slug))
    if sh is None:
        return {}
    return {
        "cwd": sh.fs.cwd,
        "last_command": sh.history[-1] if sh.history else "",
        "recent_commands": sh.history[-5:],
        "files_in_cwd": sh.fs.listdir("."),
    }
