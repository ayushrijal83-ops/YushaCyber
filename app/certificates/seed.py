"""Certificate seed.

Inserts the initial certificate definitions using SQLAlchemy models only.
Idempotent: if any certificate already exists the seeder does nothing, so
re-running never duplicates.

Run via the Flask CLI (registered in the app factory):

    flask --app app seed-certificates
"""

from __future__ import annotations

from app.certificates.models import Certificate
from app.extensions import db

# (title, slug, description, category, icon, certificate_type,
#  required_modules, required_quizzes, required_xp)
CERTIFICATES: list[tuple] = [
    ("Linux Fundamentals", "linux-fundamentals",
     "Awarded for mastering the fundamentals of Linux.",
     "foundations", "terminal", "course",
     "linux-fundamentals", "linux-fundamentals", 0),
    ("Networking Fundamentals", "networking-fundamentals",
     "Awarded for mastering core computer networking concepts.",
     "foundations", "share-2", "course",
     "computer-networking", "computer-networking", 0),
    ("Python Basics", "python-basics",
     "Awarded for learning the basics of Python programming.",
     "foundations", "code", "course",
     "python-basics", "python-basics", 0),
    ("Web Security", "web-security",
     "Awarded for understanding common web application security topics.",
     "offensive", "globe", "course",
     "web-security", "web-security", 0),
    ("Cryptography", "cryptography",
     "Awarded for grasping essential cryptography concepts.",
     "foundations", "lock", "course",
     "cryptography", "cryptography", 0),
    ("Privilege Escalation", "privilege-escalation",
     "Awarded for learning privilege escalation techniques.",
     "offensive", "trending-up", "course",
     "privilege-escalation", "privilege-escalation", 0),
    ("Digital Forensics", "digital-forensics",
     "Awarded for foundational digital forensics skills.",
     "defensive", "search", "course",
     "digital-forensics", "digital-forensics", 0),
    ("Blue Team Foundations", "blue-team-foundations",
     "Awarded for foundational defensive security skills.",
     "defensive", "shield", "track",
     None, None, 500),
    ("Red Team Foundations", "red-team-foundations",
     "Awarded for foundational offensive security skills.",
     "offensive", "crosshair", "track",
     None, None, 500),
    ("Completionist", "completionist",
     "Awarded for completing the entire YushaCyber roadmap.",
     "special", "trophy", "special",
     None, None, 2000),
]


def seed_certificates() -> dict[str, int]:
    """Insert certificate definitions if none exist. Returns a summary.

    Idempotent: if any certificate already exists the function makes no
    changes and reports the existing count.
    """
    if Certificate.query.first() is not None:
        return {"created": 0, "certificates": Certificate.query.count()}

    for order, (
        title, slug, desc, category, icon, ctype, req_mods, req_quiz, req_xp
    ) in enumerate(CERTIFICATES, start=1):
        db.session.add(Certificate(
            title=title,
            slug=slug,
            description=desc,
            category=category,
            icon=icon,
            certificate_type=ctype,
            required_modules=req_mods,
            required_quizzes=req_quiz,
            required_xp=req_xp,
            is_active=True,
            display_order=order,
        ))

    db.session.commit()
    return {"created": 1, "certificates": len(CERTIFICATES)}
