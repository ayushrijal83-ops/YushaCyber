"""Cyber Resources seed.

Inserts categories and reference resources using SQLAlchemy models only.
Idempotent: if any category exists the seeder does nothing.

    flask --app app seed-resources
"""

from __future__ import annotations

from app.extensions import db
from app.resources.models import Resource, ResourceCategory

# (name, slug, description, icon) — 10 categories per the seed command.
CATEGORIES: list[tuple] = [
    ("Linux", "linux",
     "Command line, permissions, processes and system administration.", "terminal"),
    ("Networking", "networking",
     "Protocols, the OSI model, scanning and packet analysis.", "share-2"),
    ("Web Security", "web-security",
     "Web application vulnerabilities and how to defend against them.", "globe"),
    ("Python", "python",
     "Scripting and automation for security tasks.", "code"),
    ("PowerShell", "powershell",
     "Windows automation and offensive/defensive PowerShell.", "terminal"),
    ("Bash", "bash",
     "Shell scripting for the Linux command line.", "terminal"),
    ("Digital Forensics", "digital-forensics",
     "Evidence acquisition, analysis and incident investigation.", "search"),
    ("SOC", "soc",
     "Security operations, monitoring, detection and triage.", "shield"),
    ("Cloud", "cloud",
     "Securing cloud platforms and their shared-responsibility model.", "cloud"),
    ("Active Directory", "active-directory",
     "Windows domain structure, authentication and common attacks.", "layers"),
]

_DIFFS = ["Beginner", "Beginner", "Intermediate", "Intermediate", "Advanced"]

# Per-category resource titles (5 each).
_RESOURCES: dict[str, list[str]] = {
    "linux": [
        "Linux File System Hierarchy Explained",
        "Understanding Linux File Permissions",
        "Essential Command Line Tools",
        "Managing Processes and Services",
        "Bash Environment and Shell Basics",
    ],
    "networking": [
        "The OSI Model in Practice",
        "TCP vs UDP: When to Use Which",
        "Subnetting Made Simple",
        "Reading Packet Captures with Wireshark",
        "Common Network Services and Ports",
    ],
    "web-security": [
        "The OWASP Top 10 Overview",
        "Understanding SQL Injection",
        "Cross-Site Scripting (XSS) Explained",
        "Authentication and Session Security",
        "Securing HTTP Headers",
    ],
    "python": [
        "Python for Security Automation",
        "Working with Sockets in Python",
        "Parsing Data with Regular Expressions",
        "Interacting with Web APIs",
        "Building a Simple Port Scanner",
    ],
    "powershell": [
        "PowerShell Fundamentals for Defenders",
        "Enumerating Systems with PowerShell",
        "PowerShell Remoting Basics",
        "Logging and Detection in PowerShell",
        "Common Offensive PowerShell Techniques",
    ],
    "bash": [
        "Bash Scripting Fundamentals",
        "Variables, Loops and Conditionals",
        "Text Processing with grep, sed and awk",
        "Automating Tasks with Cron",
        "Writing Safe and Portable Scripts",
    ],
    "digital-forensics": [
        "Introduction to Digital Forensics",
        "Acquiring Disk and Memory Images",
        "Analyzing Windows Artifacts",
        "Timeline Analysis Basics",
        "Chain of Custody and Reporting",
    ],
    "soc": [
        "What a SOC Analyst Actually Does",
        "Understanding SIEM Fundamentals",
        "Triaging Security Alerts",
        "Threat Intelligence Basics",
        "Incident Response Lifecycle",
    ],
    "cloud": [
        "Cloud Shared Responsibility Model",
        "Securing Identity and Access Management",
        "Common Cloud Misconfigurations",
        "Logging and Monitoring in the Cloud",
        "Introduction to Container Security",
    ],
    "active-directory": [
        "Active Directory Core Concepts",
        "Kerberos Authentication Explained",
        "Enumerating a Domain",
        "Common Active Directory Attacks",
        "Hardening Active Directory",
    ],
}


def _summary(title: str, category: str) -> str:
    return (
        f"A concise reference on {title.lower()} within {category}. "
        f"Covers the key concepts you need and where to go deeper."
    )


def _content(title: str, category: str) -> str:
    return (
        f"# {title}\n\n"
        f"This reference introduces {title.lower()} as part of the "
        f"{category} track.\n\n"
        f"## Overview\n\n"
        f"Understand the core ideas, why they matter in cybersecurity, and "
        f"how they connect to real-world practice.\n\n"
        f"## Key Points\n\n"
        f"- The fundamentals you must know\n"
        f"- Common pitfalls and misconceptions\n"
        f"- How this applies on the job\n\n"
        f"## Going Further\n\n"
        f"Pair this reference with the hands-on labs and challenges on the "
        f"platform to turn theory into skill."
    )


def seed_resources() -> dict[str, int]:
    """Insert categories and resources if none exist. Idempotent."""
    if ResourceCategory.query.first() is not None:
        return {
            "created": 0,
            "categories": ResourceCategory.query.count(),
            "resources": Resource.query.count(),
        }

    resources = 0
    for c_order, (name, slug, desc, icon) in enumerate(CATEGORIES, start=1):
        category = ResourceCategory(
            name=name, slug=slug, description=desc, icon=icon,
            display_order=c_order, is_active=True,
        )
        db.session.add(category)
        db.session.flush()  # assign category.id

        for r_order, title in enumerate(_RESOURCES[slug], start=1):
            # Build a slug from the title, prefixed with the category.
            base = "".join(
                ch if ch.isalnum() or ch == " " else "" for ch in title.lower()
            )
            r_slug = f"{slug}-" + "-".join(base.split())
            db.session.add(Resource(
                category_id=category.id,
                title=title,
                slug=r_slug[:200],
                summary=_summary(title, name),
                content=_content(title, name),
                difficulty=_DIFFS[r_order - 1],
                estimated_read_minutes=4 + r_order * 2,
                is_featured=(r_order == 1),   # first of each category featured
                display_order=r_order,
                is_active=True,
            ))
            resources += 1

    db.session.commit()
    return {"created": 1, "categories": len(CATEGORIES), "resources": resources}
