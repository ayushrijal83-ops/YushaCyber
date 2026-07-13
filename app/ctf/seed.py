"""CTF seed.

Inserts categories and challenges using SQLAlchemy models only. Flags are
hashed via the model's set_flag (raw values never persisted). Idempotent:
if any category exists the seeder does nothing, so re-running never
duplicates.

Run via the Flask CLI (registered in the app factory):

    flask --app app seed-ctf
"""

from __future__ import annotations

from app.ctf.models import Challenge, ChallengeCategory, ChallengeHint
from app.extensions import db

# (name, slug, description, icon)
CATEGORIES: list[tuple] = [
    ("Web Security", "web-security",
     "Exploit web application vulnerabilities.", "globe"),
    ("Cryptography", "cryptography",
     "Break ciphers and cryptographic schemes.", "lock"),
    ("Reverse Engineering", "reverse-engineering",
     "Analyze and understand compiled programs.", "cpu"),
    ("Forensics", "forensics",
     "Recover and investigate hidden data.", "search"),
    ("OSINT", "osint",
     "Open-source intelligence gathering.", "eye"),
    ("Binary Exploitation", "binary-exploitation",
     "Exploit memory-corruption vulnerabilities.", "terminal"),
    ("Steganography", "steganography",
     "Uncover data hidden inside media.", "image"),
    ("Misc", "misc",
     "Everything that doesn't fit elsewhere.", "flag"),
]

# Per category: 3 (title, difficulty, xp_reward, points) challenges.
# Difficulties cover Easy / Medium / Hard / Insane across the set.
_CHALLENGE_TEMPLATES = [
    ("Warmup", "Easy", 50, 100),
    ("Deeper Dive", "Medium", 100, 250),
    ("Final Boss", "Hard", 200, 500),
]

_AUTHOR = "YushaCyber"


def _hint_templates(category_name: str, difficulty: str) -> list[tuple]:
    """Three increasingly specific hints for a challenge."""
    return [
        ("Hint #1 — Getting Started",
         f"Start by understanding what the challenge is asking. Review the "
         f"core {category_name} concepts before digging in."),
        ("Hint #2 — Narrow It Down",
         f"Most {difficulty.lower()} {category_name} challenges hinge on one "
         f"key observation. Look carefully at what the challenge gives you "
         f"and ask what stands out."),
        ("Hint #3 — Almost There",
         "The flag follows the standard format. Once you've found the value, "
         "submit it exactly as it appears — no extra spaces."),
    ]


def seed_ctf() -> dict[str, int]:
    """Insert CTF categories and challenges if none exist. Idempotent.

    Returns a summary; makes no changes if any category already exists.
    """
    if ChallengeCategory.query.first() is not None:
        return {
            "created": 0,
            "categories": ChallengeCategory.query.count(),
            "challenges": Challenge.query.count(),
            "hints": ChallengeHint.query.count(),
        }

    challenge_count = 0
    hint_count = 0
    for c_order, (name, slug, desc, icon) in enumerate(CATEGORIES, start=1):
        category = ChallengeCategory(
            name=name, slug=slug, description=desc, icon=icon,
            display_order=c_order, is_active=True,
        )
        db.session.add(category)
        db.session.flush()  # assign category.id

        for ch_order, (suffix, difficulty, xp, pts) in enumerate(
            _CHALLENGE_TEMPLATES, start=1
        ):
            challenge = Challenge(
                category_id=category.id,
                title=f"{name}: {suffix}",
                slug=f"{slug}-{suffix.lower().replace(' ', '-')}",
                description=(
                    f"A {difficulty.lower()} {name} challenge. "
                    f"Find the flag and submit it."
                ),
                difficulty=difficulty,
                xp_reward=xp,
                points=pts,
                hint=f"Think about {name.lower()} fundamentals.",
                author=_AUTHOR,
                estimated_minutes=15 * ch_order,
                display_order=ch_order,
                is_active=True,
            )
            # Deterministic placeholder flag per challenge (hashed on store).
            challenge.set_flag(f"YC{{{slug}_{suffix.lower().replace(' ', '_')}}}")
            db.session.add(challenge)
            db.session.flush()  # assign challenge.id for its hints

            # Three hints per challenge, increasingly specific.
            for h_order, (h_title, h_body) in enumerate(
                _hint_templates(name, difficulty), start=1
            ):
                db.session.add(ChallengeHint(
                    challenge_id=challenge.id,
                    title=h_title,
                    content=h_body,
                    display_order=h_order,
                    is_free=True,
                ))
                hint_count += 1

            challenge_count += 1

    db.session.commit()
    return {
        "created": 1,
        "categories": len(CATEGORIES),
        "challenges": challenge_count,
        "hints": hint_count,
    }
