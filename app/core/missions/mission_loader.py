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
        "learn": ["Navigating the filesystem", "Listing & revealing hidden files",
                  "Reading files with cat", "Creating files & directories",
                  "Command history"],
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
        "next_mission": "linux-permissions",
    },
    "linux-permissions": {
        "id": "linux-permissions",
        "title": "Linux Permissions",
        "description": "Master file permissions, ownership, and chmod/chown on a realistic Linux-style filesystem.",
        "difficulty": "Beginner",
        "category": "linux",
        "xp_total": 200,
        "estimated_minutes": 20,
        "learn": ["Linux permissions", "Users", "Groups", "chmod",
                  "Ownership", "Permission notation"],
        "objectives": [
            {
                "id": "lp-1",
                "title": "Read Permission Notation",
                "description": "List the contents of ~/permissions in long format to see permission bits, owners, and groups.",
                "hint": "Use 'ls -l' (try it inside the permissions folder: cd permissions).",
                "validate": {"type": "command", "match": "ls -l"},
                "xp": 20,
            },
            {
                "id": "lp-2",
                "title": "Identify Yourself",
                "description": "Find out which user you're currently logged in as.",
                "hint": "The command is 'whoami'.",
                "validate": {"type": "command", "match": "whoami"},
                "xp": 15,
            },
            {
                "id": "lp-3",
                "title": "Inspect Your Identity",
                "description": "Inspect your full user and group ID information.",
                "hint": "Type 'id'.",
                "validate": {"type": "command", "match": "id"},
                "xp": 15,
            },
            {
                "id": "lp-4",
                "title": "Check Your Groups",
                "description": "List the groups you belong to.",
                "hint": "Type 'groups'.",
                "validate": {"type": "command", "match": "groups"},
                "xp": 15,
            },
            {
                "id": "lp-5",
                "title": "Access Denied",
                "description": "Try to read private.txt in ~/permissions and see what happens when you don't have permission.",
                "hint": "Use 'cat private.txt' — it should be denied.",
                "validate": {"type": "output_contains", "match": "permission denied"},
                "xp": 25,
            },
            {
                "id": "lp-6",
                "title": "Grant Read Access",
                "description": "Use chmod to make challenge.txt readable by everyone (mode 644).",
                "hint": "Use 'chmod 644 challenge.txt'.",
                "validate": {"type": "file_mode", "match": "644",
                             "path": "/home/student/permissions/challenge.txt"},
                "xp": 30,
            },
            {
                "id": "lp-7",
                "title": "Verify the Change",
                "description": "Confirm challenge.txt now shows the new permission bits by listing it directly.",
                "hint": "Use 'ls -l challenge.txt' (from ~/permissions) and check it changed to read for everyone.",
                "validate": {"type": "file_mode", "match": "644",
                             "path": "/home/student/permissions/challenge.txt"},
                "xp": 25,
            },
            {
                "id": "lp-8",
                "title": "Take Ownership",
                "description": "Take ownership of private.txt so you can finally read it.",
                "hint": "Use 'chown student private.txt'.",
                "validate": {"type": "file_owner", "match": "student",
                             "path": "/home/student/permissions/private.txt"},
                "xp": 55,
            },
        ],
        "filesystem": {
            "home": {"student": {
                "permissions": {
                    "public.txt": "Anyone can read this file. Permissions are your first line of defense.\n",
                    "private.txt": "Only the owner should be able to read this. If you can see this, ownership matters.\n",
                    "challenge.txt": "Locked down until you grant yourself read access.\n",
                },
                "Documents": {},
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
        "permissions": {
            "/home/student/permissions/public.txt": {"mode": "644", "owner": "student", "group": "student"},
            "/home/student/permissions/private.txt": {"mode": "600", "owner": "root", "group": "root"},
            "/home/student/permissions/challenge.txt": {"mode": "000", "owner": "student", "group": "student"},
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
