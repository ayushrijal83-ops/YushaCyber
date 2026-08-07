"""Mission definitions — structured mission data.

Each mission is a dict with objectives. Missions are loaded by
the mission_loader and run by the mission_runner.
"""

from __future__ import annotations

from typing import Any

MISSIONS: dict[str, dict[str, Any]] = {
    "linux-basics": {
        "id": "linux-basics",
        "title": "Linux Basics",
        "description": "Learn essential Linux commands.",
        "difficulty": "Easy",
        "category": "linux",
        "xp_total": 200,
        "estimated_minutes": 15,
        "objectives": [
            {
                "id": "lb-1",
                "title": "Where am I?",
                "description": "Use the command that shows your current working directory.",
                "hint": "The command is three letters: p, w, d.",
                "validate": {"type": "command", "match": "pwd"},
                "xp": 20,
            },
            {
                "id": "lb-2",
                "title": "List Files",
                "description": "List the contents of the current directory.",
                "hint": "Use 'ls' to list files.",
                "validate": {"type": "command", "match": "ls"},
                "xp": 20,
            },
            {
                "id": "lb-3",
                "title": "Hidden Files",
                "description": "List ALL files including hidden ones (files starting with a dot).",
                "hint": "Add the -la flag to ls.",
                "validate": {"type": "command", "match": "ls -la"},
                "xp": 25,
            },
            {
                "id": "lb-4",
                "title": "Change Directory",
                "description": "Navigate into the Documents folder.",
                "hint": "Use 'cd Documents'.",
                "validate": {"type": "cwd", "match": "/home/student/Documents"},
                "xp": 25,
            },
            {
                "id": "lb-5",
                "title": "Read a File",
                "description": "Read the contents of welcome.txt inside Documents.",
                "hint": "Use 'cat welcome.txt' (make sure you're in Documents).",
                "validate": {"type": "command", "match": "cat welcome.txt"},
                "xp": 25,
            },
            {
                "id": "lb-6",
                "title": "Create a File",
                "description": "Create a new file called notes.txt.",
                "hint": "Use 'touch notes.txt'.",
                "validate": {"type": "file_exists", "match": "/home/student/notes.txt"},
                "xp": 30,
            },
            {
                "id": "lb-7",
                "title": "Create a Folder",
                "description": "Create a new directory called practice.",
                "hint": "Use 'mkdir practice'.",
                "validate": {"type": "dir_exists", "match": "/home/student/practice"},
                "xp": 30,
            },
            {
                "id": "lb-8",
                "title": "View History",
                "description": "View your command history.",
                "hint": "Type 'history'.",
                "validate": {"type": "command", "match": "history"},
                "xp": 25,
            },
        ],
        "filesystem": {
            "home": {"student": {
                "Documents": {
                    "welcome.txt": "Welcome to YushaCyber!\nYou're learning Linux. Keep going!\n",
                    "readme.txt": "Read the welcome file first.\n",
                },
                "Downloads": {},
                "Desktop": {},
                ".bashrc": "# ~/.bashrc\n",
                ".profile": "# ~/.profile\n",
            }},
            "etc": {
                "passwd": "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000::/home/student:/bin/bash\n",
                "hostname": "yushacyber-lab\n",
            },
            "var": {"log": {"syslog": "System log entries here.\n"}},
            "tmp": {},
        },
        "next_mission": None,
    },
}


def get_mission(mission_id: str) -> dict[str, Any] | None:
    return MISSIONS.get(mission_id)


def list_missions() -> list[dict[str, Any]]:
    return [{"id": m["id"], "title": m["title"],
             "difficulty": m["difficulty"], "xp_total": m["xp_total"],
             "objectives": len(m["objectives"])}
            for m in MISSIONS.values()]
