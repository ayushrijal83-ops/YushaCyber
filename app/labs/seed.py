"""Cyber Labs seed.

Inserts categories, labs, objectives, and files using SQLAlchemy models
only. Idempotent: if any category exists the seeder does nothing, so
re-running never duplicates.

Run via the Flask CLI (registered in the app factory):

    flask --app app seed-labs
"""

from __future__ import annotations

from app.extensions import db
from app.labs.models import Lab, LabCategory, LabFile, LabObjective

# (name, slug, description, icon)
CATEGORIES: list[tuple] = [
    ("Linux", "linux",
     "Hands-on labs for the Linux command line and system administration.",
     "terminal"),
    ("Networking", "networking",
     "Practical networking labs: analysis, scanning and services.",
     "share-2"),
    ("Web Security", "web-security",
     "Explore common web application vulnerabilities safely.",
     "globe"),
    ("Digital Forensics", "digital-forensics",
     "Investigate artifacts and recover evidence.",
     "search"),
    ("SOC", "soc",
     "Security Operations Center labs: monitoring and triage.",
     "shield"),
]

# Three labs per category: (suffix, difficulty, minutes, xp).
_LAB_TEMPLATES = [
    ("Fundamentals", "Easy", 30, 50),
    ("Applied", "Medium", 45, 100),
    ("Advanced", "Hard", 60, 200),
]


def _objectives_for(lab_title: str) -> list[tuple]:
    """Three objectives for a lab: (title, description)."""
    return [
        ("Set up the environment",
         f"Prepare everything you need to begin the {lab_title} lab."),
        ("Complete the core task",
         f"Work through the main exercise of the {lab_title} lab."),
        ("Verify your results",
         f"Confirm your solution and review what you learned in {lab_title}."),
    ]


def _files_for(slug: str) -> list[tuple]:
    """Two files for a lab: (filename, filepath)."""
    return [
        ("instructions.md", f"labs/{slug}/instructions.md"),
        ("starter.zip", f"labs/{slug}/starter.zip"),
    ]


def seed_labs() -> dict[str, int]:
    """Insert lab content if none exists. Idempotent.

    Returns a summary; makes no changes if any category already exists.
    """
    if LabCategory.query.first() is not None:
        # Catalogue exists; still ensure engine content is present (idempotent).
        from app.labs.linux_track_seed import seed_linux_track
        from app.labs.networking_track_seed import seed_networking_track
        from app.labs.interactive_network_seed import seed_interactive_network
        engine = seed_linux_track()
        network = seed_networking_track()
        interactive = seed_interactive_network()
        from app.labs.nmap_seed import seed_nmap_labs
        nmap = seed_nmap_labs()
        from app.labs.wireshark_seed import seed_wireshark_labs
        ws = seed_wireshark_labs()
        from app.labs.websec_seed import seed_websec_labs
        websec = seed_websec_labs()
        from app.labs.soc_seed import seed_soc_labs
        soc = seed_soc_labs()
        from app.labs.ad.seed import seed_ad_labs
        ad = seed_ad_labs()
        from app.labs.cloud.seed import seed_cloud_labs
        cloud = seed_cloud_labs()
        from app.labs.forensics.seed import seed_forensics_labs
        forensics = seed_forensics_labs()
        return {
            "created": network["labs"] + interactive["labs"],
            "categories": LabCategory.query.count(),
            "labs": Lab.query.count(),
            "objectives": LabObjective.query.count(),
            "files": LabFile.query.count(),
            "fs_nodes": engine["fs_nodes"],
            "networking_labs": network["labs"] + interactive["labs"],
            "networking_achievements": network["achievements"] + interactive["achievements"],
            "ad_labs": ad["labs"],
            "cloud_labs": cloud["labs"],
            "forensics_labs": forensics["labs"],
        }

    labs = objectives = files = 0

    for c_order, (name, slug, desc, icon) in enumerate(CATEGORIES, start=1):
        category = LabCategory(
            name=name, slug=slug, description=desc, icon=icon,
            display_order=c_order, is_active=True,
        )
        db.session.add(category)
        db.session.flush()  # assign category.id

        for l_order, (suffix, difficulty, minutes, xp) in enumerate(
            _LAB_TEMPLATES, start=1
        ):
            lab_title = f"{name}: {suffix}"
            lab_slug = f"{slug}-{suffix.lower()}"
            lab = Lab(
                category_id=category.id,
                title=lab_title,
                slug=lab_slug,
                description=(
                    f"A {difficulty.lower()} {name} lab covering "
                    f"{suffix.lower()} skills."
                ),
                difficulty=difficulty,
                estimated_minutes=minutes,
                xp_reward=xp,
                display_order=l_order,
                is_active=True,
            )
            db.session.add(lab)
            db.session.flush()  # assign lab.id

            for o_order, (o_title, o_desc) in enumerate(
                _objectives_for(lab_title), start=1
            ):
                db.session.add(LabObjective(
                    lab_id=lab.id, title=o_title, description=o_desc,
                    display_order=o_order,
                ))
                objectives += 1

            for f_order, (fname, fpath) in enumerate(
                _files_for(lab_slug), start=1
            ):
                db.session.add(LabFile(
                    lab_id=lab.id, filename=fname, filepath=fpath,
                    display_order=f_order,
                ))
                files += 1

            labs += 1

    db.session.commit()

    # Seed the full interactive Linux track (idempotent).
    from app.labs.linux_track_seed import seed_linux_track
    engine = seed_linux_track()

    # Seed the interactive Networking track (idempotent) — YC-013.0.
    from app.labs.networking_track_seed import seed_networking_track
    from app.labs.interactive_network_seed import seed_interactive_network
    network = seed_networking_track()
    interactive = seed_interactive_network()
    from app.labs.nmap_seed import seed_nmap_labs
    nmap = seed_nmap_labs()
    from app.labs.wireshark_seed import seed_wireshark_labs
    ws = seed_wireshark_labs()
    from app.labs.websec_seed import seed_websec_labs
    websec = seed_websec_labs()
    from app.labs.soc_seed import seed_soc_labs
    soc = seed_soc_labs()
    from app.labs.ad.seed import seed_ad_labs
    ad = seed_ad_labs()
    from app.labs.cloud.seed import seed_cloud_labs
    cloud = seed_cloud_labs()

    return {
        "created": 1,
        "categories": len(CATEGORIES),
        "labs": labs + engine["labs"] + network["labs"],
        "objectives": objectives + engine["objectives"] + network["objectives"],
        "files": files,
        "fs_nodes": engine["fs_nodes"],
        "networking_labs": network["labs"] + interactive["labs"],
        "networking_achievements": network["achievements"] + interactive["achievements"],
        "ad_labs": ad["labs"],
        "cloud_labs": cloud["labs"],
    }


# ===========================================================================
# Lab Engine seed (YC-012.1) — the interactive "Linux Basics" lab.
#
# NOTE: all Linux-specific content lives HERE (data) and in the Linux
# simulator plugin (behaviour). The engine seeds nothing lab-specific.
# ===========================================================================
SIMULATOR_ENGINES = [
    ("linux", "Linux Terminal",
     "Simulated Linux shell over a virtual filesystem.", "terminal"),
]

# (path, node_type, content)
LINUX_BASICS_FS = [
    ("/home", "dir", None),
    ("/home/student", "dir", None),
    ("/home/student/Documents", "dir", None),
    ("/home/student/Downloads", "dir", None),
    ("/home/student/readme.txt", "file",
     "Welcome to the YushaCyber Linux lab.\n"
     "Everything here is simulated — nothing runs on a real machine.\n"
     "Use 'help' to list the commands you can try."),
    ("/home/student/Documents/note.txt", "file",
     "Well done — you found the note!\n\n"
     "The Linux filesystem is a tree starting at /.\n"
     "Your home directory is /home/user (shortcut: ~).\n\n"
     "Next: create a directory called 'projects' with mkdir."),
    ("/home/student/Documents/todo.md", "file",
     "- learn pwd\n- learn ls\n- learn cd\n- learn cat\n- learn mkdir"),
    ("/etc", "dir", None),
    ("/etc/hostname", "file", "yushacyber-lab"),
]

# (title, instruction, validator_type, validator_data, hints, xp)
LINUX_BASICS_OBJECTIVES = [
    ("Print the working directory",
     "Find out where you are in the filesystem. Run: pwd",
     "exact_command", {"command": "pwd"},
     ("Every shell has a 'current directory'.",
      "The command is three letters: p-w-d.",
      "Type: pwd"), 10),

    ("List the directory contents",
     "See what files and folders are here. Run: ls",
     "exact_command", {"command": "ls"},
     ("You need to 'list' what's around you.",
      "The command is two letters.",
      "Type: ls"), 10),

    ("Change into the Documents directory",
     "Move into the Documents folder. Run: cd Documents",
     "state_flag", {"path": "cwd", "equals": "/home/student/Documents"},
     ("Use 'cd' — change directory.",
      "Pass the folder name as an argument.",
      "Type: cd Documents"), 15),

    ("Read the note file",
     "Display the contents of note.txt. Run: cat note.txt",
     "output_contains", {"text": "you found the note"},
     ("'cat' prints a file's contents.",
      "The file is called note.txt, inside Documents.",
      "Type: cat note.txt"), 15),

    ("Create a projects directory",
     "Make a new directory called projects. Run: mkdir projects",
     "regex_command", {"pattern": r"^mkdir\s+projects/?$", "flags": "i"},
     ("'mkdir' makes a directory.",
      "Give it the name you want to create.",
      "Type: mkdir projects"), 20),
]


def seed_lab_engine() -> dict[str, int]:
    """Seed simulator engines + the interactive Linux Basics lab. Idempotent."""
    from app.labs.models import (
        Lab, LabCategory, LabFileSystemNode, LabObjective, SimulatorEngine,
    )

    created = {"engines": 0, "labs": 0, "objectives": 0, "fs_nodes": 0}

    # --- simulator engine catalogue ---
    for key, name, desc, caps in SIMULATOR_ENGINES:
        if SimulatorEngine.query.filter_by(key=key).first() is None:
            db.session.add(SimulatorEngine(
                key=key, name=name, description=desc,
                capabilities=caps, is_active=True,
            ))
            created["engines"] += 1

    # --- the interactive lab ---
    if Lab.query.filter_by(slug="linux-basics").first() is None:
        category = LabCategory.query.filter_by(slug="linux").first()
        if category is None:
            category = LabCategory(
                name="Linux", slug="linux",
                description="Hands-on Linux command line labs.",
                icon="terminal", display_order=1, is_active=True,
            )
            db.session.add(category)
            db.session.flush()

        lab = Lab(
            category_id=category.id,
            title="Linux Basics",
            slug="linux-basics",
            description=(
                "Learn to navigate a Linux filesystem in a fully simulated "
                "terminal. Complete each objective to earn XP."
            ),
            difficulty="Easy",
            estimated_minutes=20,
            xp_reward=100,
            display_order=0,
            is_active=True,
            simulator_key="linux",     # <- the only lab-type coupling: a string
            is_interactive=True,
        )
        db.session.add(lab)
        db.session.flush()
        created["labs"] += 1

        for path, node_type, content in LINUX_BASICS_FS:
            db.session.add(LabFileSystemNode(
                lab_id=lab.id, path=path, node_type=node_type, content=content,
                permissions="rwxr-xr-x" if node_type == "dir" else "rw-r--r--",
                owner="user",
            ))
            created["fs_nodes"] += 1

        for order, (title, instruction, vtype, vdata, hints, xp) in enumerate(
            LINUX_BASICS_OBJECTIVES, start=1
        ):
            objective = LabObjective(
                lab_id=lab.id, title=title, description=instruction,
                instruction=instruction, display_order=order,
                validator_type=vtype, xp_reward=xp, is_optional=False,
                hint1=hints[0], hint2=hints[1], hint3=hints[2],
            )
            objective.set_validator_data(vdata)
            db.session.add(objective)
            created["objectives"] += 1

    db.session.commit()
    return created
