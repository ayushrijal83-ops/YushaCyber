"""Linux learning track seed (YC-012.3).

Nine sequential Linux labs, each an interactive terminal lab driven by the
existing Lab Engine + Linux simulator. All Linux content lives here (data)
and in the simulator plugin (behaviour) — the engine is untouched.

Progression: each lab's ``prerequisite_lab_id`` points at the previous lab,
so labs unlock in order. Idempotent: guarded on the track's category.
"""

from __future__ import annotations

from app.extensions import db
from app.labs.models import (
    Lab, LabCategory, LabFileSystemNode, LabObjective, SimulatorEngine,
)

# ---------------------------------------------------------------------------
# Shared virtual filesystem for the whole track (per-lab labs get a copy).
# Expanded home per the ticket: Documents/Downloads/Projects/Scripts/Pictures
# + notes.txt / secret.txt / backup.tar, plus /var/log/auth.log for the logs
# lab and a few extras the objectives reference.
# ---------------------------------------------------------------------------
_AUTH_LOG = "\n".join(
    [f"Jul 14 08:0{i} linux-lab sshd[{1200+i}]: Accepted password for student from 10.10.14.7" for i in range(1, 4)]
    + [f"Jul 14 08:1{i} linux-lab sshd[{1300+i}]: Failed password for root from 45.83.{i}.66" for i in range(0, 5)]
    + [f"Jul 14 08:2{i} linux-lab sshd[{1400+i}]: Failed password for admin from 45.83.{i}.66" for i in range(0, 3)]
)

TRACK_FS = [
    ("/home", "dir", None),
    ("/home/student", "dir", None),
    ("/home/student/Documents", "dir", None),
    ("/home/student/Downloads", "dir", None),
    ("/home/student/Projects", "dir", None),
    ("/home/student/Scripts", "dir", None),
    ("/home/student/Pictures", "dir", None),
    ("/home/student/notes.txt", "file",
     "Linux notes\n-----------\nThe filesystem is a tree rooted at /.\nYour home is /home/student (~).\nUse 'help' to list commands."),
    ("/home/student/secret.txt", "file",
     "TOP SECRET\nThe flag is: YC{linux_track_secret}\nKeep this file private — try chmod 600 on it."),
    ("/home/student/backup.tar", "file", "Documents\nDocuments/report.txt\nnotes.txt"),
    ("/home/student/Documents/report.txt", "file",
     "Quarterly Report\nRevenue is up 20%.\nSee todo.md for next steps."),
    ("/home/student/Documents/todo.md", "file",
     "- learn navigation\n- learn permissions\n- learn searching\n- pass the challenge"),
    ("/home/student/Downloads/archive.zip", "file", "report.txt\ntodo.md"),
    ("/home/student/Scripts/deploy.sh", "file",
     "#!/bin/bash\necho deploying...\n# TODO: add error handling"),
    ("/home/student/Projects/app.py", "file",
     "import os\nprint('hello world')\n# password = 'hunter2'  # do not commit secrets!"),
    ("/etc", "dir", None),
    ("/etc/hostname", "file", "linux-lab"),
    ("/etc/passwd", "file",
     "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000:Student:/home/student:/bin/bash"),
    ("/var", "dir", None),
    ("/var/log", "dir", None),
    ("/var/log/auth.log", "file", _AUTH_LOG),
    ("/var/log/syslog", "file",
     "Jul 14 08:00 linux-lab systemd: Started Session 1 of user student.\nJul 14 08:05 linux-lab CRON: job ran"),
]


def _obj(title, instruction, vtype, vdata, hints, xp, optional=False):
    return {
        "title": title, "instruction": instruction,
        "validator_type": vtype, "validator_data": vdata,
        "hints": hints, "xp": xp, "optional": optional,
    }


# ---------------------------------------------------------------------------
# The nine labs. (slug, title, difficulty, minutes, xp_reward, [objectives])
# ---------------------------------------------------------------------------
LABS = [
    ("linux-basics", "Linux Basics", "Easy", 20, 100, [
        _obj("Print the working directory", "Find out where you are. Run: pwd",
             "exact_command", {"command": "pwd"},
             ("Every shell tracks a current directory.", "It's three letters.", "Type: pwd"), 10),
        _obj("List the directory", "List what's here. Run: ls",
             "exact_command", {"command": "ls"},
             ("You need to 'list'.", "Two letters.", "Type: ls"), 10),
        _obj("Enter Documents", "Move into Documents. Run: cd Documents",
             "state_flag", {"path": "cwd", "equals": "/home/student/Documents"},
             ("Use 'cd'.", "Pass the folder name.", "Type: cd Documents"), 15),
        _obj("Read a file", "Read report.txt. Run: cat report.txt",
             "output_contains", {"text": "Quarterly Report"},
             ("'cat' prints a file.", "The file is report.txt.", "Type: cat report.txt"), 15),
        _obj("Create a directory", "Make a directory called work. Run: mkdir work",
             "regex_command", {"pattern": r"^mkdir\s+work/?$", "flags": "i"},
             ("'mkdir' makes directories.", "Name it 'work'.", "Type: mkdir work"), 20),
    ]),

    ("linux-files", "Files & Directories", "Easy", 25, 120, [
        _obj("Copy a file", "Copy notes.txt to notes.bak. Run: cp notes.txt notes.bak",
             "regex_command", {"pattern": r"^cp\s+notes\.txt\s+notes\.bak$", "flags": "i"},
             ("'cp SOURCE DEST' copies.", "Source is notes.txt.", "Type: cp notes.txt notes.bak"), 15),
        _obj("Move a file", "Move notes.bak into Documents. Run: mv notes.bak Documents/",
             "event_emitted", {"event": "fs_moved"},
             ("'mv SOURCE DEST' moves/renames.", "Destination is Documents/.", "Type: mv notes.bak Documents/"), 20),
        _obj("Make a directory", "Create a directory called temp. Run: mkdir temp",
             "regex_command", {"pattern": r"^mkdir\s+temp/?$", "flags": "i"},
             ("Use mkdir.", "Name it 'temp'.", "Type: mkdir temp"), 15),
        _obj("Remove a directory", "Remove the empty temp directory. Run: rmdir temp",
             "event_emitted", {"event": "fs_removed"},
             ("'rmdir' removes EMPTY directories.", "Target 'temp'.", "Type: rmdir temp"), 20),
        _obj("View the tree", "Show the directory tree. Run: tree",
             "exact_command", {"command": "tree"},
             ("'tree' draws the structure.", "No arguments needed.", "Type: tree"), 20),
        _obj("Delete a file", "Delete the copied file in Documents. Run: rm Documents/notes.bak",
             "regex_command", {"pattern": r"^rm\s+Documents/notes\.bak$", "flags": "i"},
             ("'rm' removes files.", "It's inside Documents.", "Type: rm Documents/notes.bak"), 30),
    ]),

    ("linux-permissions", "Permissions", "Medium", 25, 140, [
        _obj("Long listing", "Show a detailed listing. Run: ls -l",
             "event_emitted", {"event": "ls", "key": "long", "equals": True},
             ("Add the -l flag.", "'ls -l' shows permissions.", "Type: ls -l"), 20),
        _obj("Find yourself", "Print your username. Run: whoami",
             "exact_command", {"command": "whoami"},
             ("One word command.", "Who am i?", "Type: whoami"), 15),
        _obj("Lock down the secret", "Make secret.txt owner-only (600). Run: chmod 600 secret.txt",
             "state_flag", {"path": "flags.chmod.secret_txt", "equals": "600"},
             ("chmod uses octal.", "600 = rw for owner only.", "Type: chmod 600 secret.txt"), 30),
        _obj("Make a script executable", "Give deploy.sh 755. Run: chmod 755 Scripts/deploy.sh",
             "state_flag", {"path": "flags.chmod.deploy_sh", "equals": "755"},
             ("755 = rwxr-xr-x.", "The file is in Scripts/.", "Type: chmod 755 Scripts/deploy.sh"), 35),
        _obj("Change ownership", "Set root as owner of notes.txt. Run: chown root notes.txt",
             "event_emitted", {"event": "chown"},
             ("chown OWNER FILE.", "Owner is root.", "Type: chown root notes.txt"), 40),
    ]),

    ("linux-searching", "Searching", "Medium", 30, 160, [
        _obj("Find text files", "Find all .txt files under /home. Run: find /home -name *.txt",
             "output_contains", {"text": "notes.txt"},
             ("'find PATH -name PATTERN'.", "Pattern is *.txt.", "Type: find /home -name *.txt"), 30),
        _obj("Search inside a file", "Find 'Failed' in the auth log. Run: grep Failed /var/log/auth.log",
             "state_flag", {"path": "flags.grep_matched", "equals": True},
             ("'grep PATTERN FILE'.", "Look for 'Failed'.", "Type: grep Failed /var/log/auth.log"), 35),
        _obj("Locate the command", "Locate the grep binary. Run: which grep",
             "event_emitted", {"event": "which", "key": "program", "equals": "grep"},
             ("'which' shows a program's path.", "Ask about grep.", "Type: which grep"), 25),
        _obj("Locate a file", "Locate auth.log. Run: locate auth.log",
             "output_contains", {"text": "auth.log"},
             ("'locate NAME' searches paths.", "Search for auth.log.", "Type: locate auth.log"), 30),
        _obj("Case-insensitive search", "Find 'accepted' ignoring case. Run: grep -i accepted /var/log/auth.log",
             "output_contains", {"text": "Accepted", "case_sensitive": True},
             ("Add -i for case-insensitive.", "Search 'accepted'.", "Type: grep -i accepted /var/log/auth.log"), 40),
    ]),

    ("linux-archives", "Archives", "Medium", 25, 160, [
        _obj("Create a tar archive", "Archive Documents into docs.tar. Run: tar -cf docs.tar Documents",
             "event_emitted", {"event": "tar_create"},
             ("'tar -cf NAME FILES'.", "Archive the Documents dir.", "Type: tar -cf docs.tar Documents"), 30),
        _obj("List archive contents", "List what's in docs.tar. Run: tar -tf docs.tar",
             "event_emitted", {"event": "tar_list"},
             ("'tar -tf NAME' lists.", "Your archive is docs.tar.", "Type: tar -tf docs.tar"), 30),
        _obj("Extract an archive", "Extract backup.tar. Run: tar -xf backup.tar",
             "event_emitted", {"event": "tar_extract"},
             ("'tar -xf NAME' extracts.", "Extract backup.tar.", "Type: tar -xf backup.tar"), 40),
        _obj("Create a zip", "Zip notes.txt into notes.zip. Run: zip notes.zip notes.txt",
             "event_emitted", {"event": "zip_create"},
             ("'zip ARCHIVE FILES'.", "Zip notes.txt.", "Type: zip notes.zip notes.txt"), 30),
        _obj("Unzip an archive", "Unzip Downloads/archive.zip. Run: unzip Downloads/archive.zip",
             "event_emitted", {"event": "unzip"},
             ("'unzip ARCHIVE'.", "It's in Downloads.", "Type: unzip Downloads/archive.zip"), 30),
    ]),

    ("linux-processes", "Processes", "Medium", 25, 160, [
        _obj("List processes", "Show running processes. Run: ps",
             "event_emitted", {"event": "ps"},
             ("'ps' lists processes.", "No args needed.", "Type: ps"), 25),
        _obj("Monitor resources", "Show resource usage. Run: top",
             "event_emitted", {"event": "top"},
             ("'top' shows live usage.", "No args needed.", "Type: top"), 30),
        _obj("Kill the runaway process", "Stop the stress_test process (PID 1337). Run: kill 1337",
             "event_emitted", {"event": "kill", "key": "pid", "equals": 1337},
             ("'kill PID'.", "The runaway PID is 1337.", "Type: kill 1337"), 45),
        _obj("List background jobs", "Show background jobs. Run: jobs",
             "event_emitted", {"event": "jobs"},
             ("'jobs' lists background tasks.", "No args needed.", "Type: jobs"), 25),
        _obj("Confirm the kill", "List processes again to confirm. Run: ps",
             "event_emitted", {"event": "ps"},
             ("Re-run the process list.", "Same command as before.", "Type: ps"), 35),
    ]),

    ("linux-networking", "Networking Basics", "Medium", 30, 180, [
        _obj("Show the hostname", "Print the machine name. Run: hostname",
             "event_emitted", {"event": "hostname"},
             ("One-word command.", "What's my host name?", "Type: hostname"), 25),
        _obj("Check connectivity", "Ping google.com. Run: ping google.com",
             "event_emitted", {"event": "ping"},
             ("'ping HOST'.", "Ping google.com.", "Type: ping google.com"), 35),
        _obj("Show IP configuration", "Show your addresses. Run: ip a",
             "state_flag", {"path": "flags.ip_addr_shown", "equals": True},
             ("'ip a' (or 'ip addr').", "Show interface addresses.", "Type: ip a"), 40),
        _obj("Fetch a web page", "Curl a URL. Run: curl http://lab.local",
             "event_emitted", {"event": "curl"},
             ("'curl URL' fetches content.", "Any http:// URL works.", "Type: curl http://lab.local"), 40),
        _obj("Find the flag in the response", "The curl output hides a flag — read it. Run: curl http://lab.local",
             "output_contains", {"text": "YC{simulated_http_response}"},
             ("Look at what curl returned.", "There's a flag: YC{...}.", "Run curl and read the body."), 40),
    ]),

    ("linux-logs", "Logs", "Hard", 30, 200, [
        _obj("Read the auth log", "Show the auth log. Run: cat /var/log/auth.log",
             "output_contains", {"text": "sshd"},
             ("'cat FILE'.", "The log is /var/log/auth.log.", "Type: cat /var/log/auth.log"), 30),
        _obj("Find failed logins", "Filter failed logins. Run: grep Failed /var/log/auth.log",
             "state_flag", {"path": "flags.grep_matched", "equals": True},
             ("'grep PATTERN FILE'.", "Search for 'Failed'.", "Type: grep Failed /var/log/auth.log"), 40),
        _obj("Show the first lines", "Show the first 5 lines. Run: head -n 5 /var/log/auth.log",
             "event_emitted", {"event": "head"},
             ("'head -n N FILE'.", "Use N = 5.", "Type: head -n 5 /var/log/auth.log"), 35),
        _obj("Show the last lines", "Show the last 5 lines. Run: tail -n 5 /var/log/auth.log",
             "event_emitted", {"event": "tail"},
             ("'tail -n N FILE'.", "Use N = 5.", "Type: tail -n 5 /var/log/auth.log"), 35),
        _obj("Count the log lines", "Count lines in the auth log. Run: wc -l /var/log/auth.log",
             "regex_command", {"pattern": r"^wc\s+-l\s+/var/log/auth\.log$"},
             ("'wc -l FILE' counts lines.", "Target the auth log.", "Type: wc -l /var/log/auth.log"), 60),
    ]),

    # Final challenge — NO hints, mixed commands, biggest reward.
    ("linux-challenge", "Linux Challenge", "Insane", 40, 400, [
        _obj("Locate the secret", "Somewhere in your home is a file holding a flag. Find and read it.",
             "output_contains", {"text": "YC{linux_track_secret}"},
             ("", "", ""), 80),
        _obj("Secure the secret", "Make that secret file readable only by its owner (chmod 600).",
             "state_flag", {"path": "flags.chmod.secret_txt", "equals": "600"},
             ("", "", ""), 80),
        _obj("Investigate the breach", "The auth log shows attacks. Filter the failed root logins.",
             "state_flag", {"path": "flags.grep_matched", "equals": True},
             ("", "", ""), 80),
        _obj("Stop the attacker's process", "A malicious process (PID 1337) is running. Terminate it.",
             "event_emitted", {"event": "kill", "key": "pid", "equals": 1337},
             ("", "", ""), 80),
        _obj("Archive the evidence", "Create a tar archive of your Documents for the report.",
             "event_emitted", {"event": "tar_create"},
             ("", "", ""), 80),
    ]),
]


def seed_linux_track() -> dict[str, int]:
    """Seed the full Linux track. Idempotent on the 'linux' category's labs."""
    # Ensure the linux simulator engine row + category exist.
    if SimulatorEngine.query.filter_by(key="linux").first() is None:
        db.session.add(SimulatorEngine(
            key="linux", name="Linux Terminal",
            description="Simulated Linux shell over a virtual filesystem.",
            capabilities="terminal", is_active=True,
        ))

    category = LabCategory.query.filter_by(slug="linux").first()
    if category is None:
        category = LabCategory(
            name="Linux", slug="linux",
            description="A complete beginner-to-intermediate Linux command-line track.",
            icon="terminal", display_order=1, is_active=True,
        )
        db.session.add(category)
        db.session.flush()

    created = {"labs": 0, "objectives": 0, "fs_nodes": 0}
    prev_lab_id = None

    for order, (slug, title, diff, minutes, xp, objectives) in enumerate(LABS, start=1):
        existing = Lab.query.filter_by(slug=slug).first()
        if existing is not None:
            prev_lab_id = existing.id
            continue

        lab = Lab(
            category_id=category.id, title=title, slug=slug,
            description=f"{title} — an interactive, fully simulated Linux lab.",
            difficulty=diff, estimated_minutes=minutes, xp_reward=xp,
            display_order=order, is_active=True,
            simulator_key="linux", is_interactive=True,
            prerequisite_lab_id=prev_lab_id,   # sequential unlock
        )
        db.session.add(lab)
        db.session.flush()
        created["labs"] += 1

        # Each lab gets its own copy of the track filesystem.
        for path, node_type, content in TRACK_FS:
            db.session.add(LabFileSystemNode(
                lab_id=lab.id, path=path, node_type=node_type, content=content,
                permissions="rwxr-xr-x" if node_type == "dir" else "rw-r--r--",
                owner="student",
            ))
            created["fs_nodes"] += 1

        for o_order, o in enumerate(objectives, start=1):
            objective = LabObjective(
                lab_id=lab.id, title=o["title"], description=o["instruction"],
                instruction=o["instruction"], display_order=o_order,
                validator_type=o["validator_type"], xp_reward=o["xp"],
                is_optional=o["optional"],
                hint1=o["hints"][0] or None,
                hint2=o["hints"][1] or None,
                hint3=o["hints"][2] or None,
            )
            objective.set_validator_data(o["validator_data"])
            db.session.add(objective)
            created["objectives"] += 1

        prev_lab_id = lab.id

    db.session.commit()
    return created
