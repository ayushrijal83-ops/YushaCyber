"""Roadmap curriculum seed.

Inserts the initial YushaCyber learning curriculum (categories -> modules
-> lessons) using SQLAlchemy models only — no raw SQL. The seed is
idempotent: it does nothing if any roadmap category already exists, so
running it repeatedly never duplicates data and never touches users or
XP.

Run it via the Flask CLI (registered in the app factory):

    flask --app app seed-roadmap
"""

from __future__ import annotations

from app.extensions import db
from app.roadmap.models import Lesson, RoadmapCategory, RoadmapModule

# ---------------------------------------------------------------------------
# Curriculum definition (data, not logic).
# Each category: (title, color, icon, [module titles...]) in display order.
# ---------------------------------------------------------------------------
CURRICULUM: list[dict[str, object]] = [
    {
        "title": "Beginner",
        "color": "green",
        "icon": "shield",
        "difficulty": "beginner",
        "modules": [
            "Linux Fundamentals",
            "Computer Networking",
            "Python Programming",
            "Web Fundamentals",
            "Git & GitHub",
            "Operating Systems",
            "Cryptography Basics",
            "Virtualization",
        ],
    },
    {
        "title": "Intermediate",
        "color": "blue",
        "icon": "layers",
        "difficulty": "intermediate",
        "modules": [
            "Nmap",
            "Wireshark",
            "Burp Suite",
            "OWASP Top 10",
            "Active Directory Basics",
            "Metasploit",
            "Windows Privilege Escalation",
            "Linux Privilege Escalation",
        ],
    },
    {
        "title": "Red Team",
        "color": "orange",
        "icon": "target",
        "difficulty": "advanced",
        "modules": [
            "Reconnaissance",
            "Enumeration",
            "Exploitation",
            "Web Pentesting",
            "Active Directory Attacks",
            "Pivoting",
            "Persistence",
            "Evasion Techniques",
        ],
    },
    {
        "title": "AI Security",
        "color": "purple",
        "icon": "cpu",
        "difficulty": "advanced",
        "modules": [
            "AI Fundamentals",
            "Prompt Injection",
            "LLM Security",
            "AI Red Teaming",
            "Secure AI Applications",
            "Model Attacks",
            "AI Threat Detection",
            "Agent Security",
        ],
    },
]

# Three placeholder lessons per module: (title, estimated_minutes, xp_reward).
LESSON_TEMPLATE: list[tuple[str, int, int]] = [
    ("Introduction", 10, 25),
    ("Core Concepts", 20, 50),
    ("Hands-on Practice", 30, 100),
]

# Module XP reward = sum of its lessons' XP (25 + 50 + 100).
_MODULE_XP = sum(xp for _, _, xp in LESSON_TEMPLATE)


def _slugify(text: str) -> str:
    """Lowercase, hyphenated slug (e.g. 'Git & GitHub' -> 'git-github')."""
    cleaned = [c.lower() if c.isalnum() else " " for c in text]
    return "-".join("".join(cleaned).split())


def seed_roadmap() -> dict[str, int]:
    """Insert the curriculum if the roadmap is empty. Returns a count summary.

    Idempotent: if any category already exists the function makes no
    changes and reports the existing counts.
    """
    if RoadmapCategory.query.first() is not None:
        return {
            "created": 0,
            "categories": RoadmapCategory.query.count(),
            "modules": RoadmapModule.query.count(),
            "lessons": Lesson.query.count(),
        }

    categories = 0
    modules = 0
    lessons = 0

    for cat_order, cat_def in enumerate(CURRICULUM, start=1):
        category = RoadmapCategory(
            title=cat_def["title"],
            description=f"{cat_def['title']} track — structured path through "
                        f"{len(cat_def['modules'])} modules.",
            icon=cat_def["icon"],
            color=cat_def["color"],
            display_order=cat_order,
            is_active=True,
        )
        categories += 1

        for mod_order, module_title in enumerate(cat_def["modules"], start=1):
            module = RoadmapModule(
                title=module_title,
                slug=_slugify(module_title),
                description=f"{module_title} — part of the {cat_def['title']} track.",
                difficulty=cat_def["difficulty"],
                estimated_hours=max(1, sum(m for _, m, _ in LESSON_TEMPLATE) // 60 or 1),
                xp_reward=_MODULE_XP,
                display_order=mod_order,
                # First module of the first category is open; the rest start
                # locked until the (future) unlock system opens them.
                is_locked=not (cat_order == 1 and mod_order == 1),
                is_active=True,
            )
            modules += 1

            for les_order, (title, minutes, xp) in enumerate(LESSON_TEMPLATE, start=1):
                module.lessons.append(Lesson(
                    title=title,
                    slug=_slugify(title),
                    content_path=f"roadmap/{category.title and _slugify(cat_def['title'])}/"
                                 f"{_slugify(module_title)}/{_slugify(title)}.md",
                    lesson_type="reading",
                    estimated_minutes=minutes,
                    xp_reward=xp,
                    display_order=les_order,
                    # The first lesson of each module is a free preview.
                    is_preview=(les_order == 1),
                ))
                lessons += 1

            category.modules.append(module)

        db.session.add(category)

    db.session.commit()
    return {"created": 1, "categories": categories,
            "modules": modules, "lessons": lessons}
