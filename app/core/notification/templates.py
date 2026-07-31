"""Notification templates — message builders for auto-events.

Each function returns (title, message, type, link) for a
specific event. The services layer calls these when auto-firing.
"""

from __future__ import annotations


def achievement_unlocked(title: str, xp: int = 0
                         ) -> tuple[str, str, str, str]:
    msg = f"You unlocked '{title}'"
    if xp:
        msg += f" and earned +{xp} bonus XP"
    return (f"🏆 Achievement: {title}", f"{msg}!",
            "achievement", "/dashboard/achievements")


def level_up(new_level: int) -> tuple[str, str, str, str]:
    return (f"⬆️ Level {new_level}!",
            f"You reached level {new_level}. Keep going!",
            "level_up", "/dashboard/")


def certificate_earned(cert_title: str) -> tuple[str, str, str, str]:
    return (f"📜 Certificate: {cert_title}",
            f"You earned the {cert_title} certificate.",
            "certificate", "/dashboard/certificates")


def track_completed(track_name: str) -> tuple[str, str, str, str]:
    return (f"✅ Track Complete: {track_name}",
            f"You completed the {track_name} learning track!",
            "track_completed", "/labs/")


def lab_completed(lab_title: str, xp: int = 0
                  ) -> tuple[str, str, str, str]:
    msg = f"You completed {lab_title}"
    if xp:
        msg += f" (+{xp} XP)"
    return (f"✅ {lab_title}", f"{msg}.",
            "lab_completed", "/labs/")


def assessment_passed(title: str, grade: str = ""
                      ) -> tuple[str, str, str, str]:
    msg = f"You passed {title}"
    if grade:
        msg += f" with grade {grade}"
    return (f"🎯 Passed: {title}", f"{msg}!",
            "assessment_passed", "/labs/")


def assessment_failed(title: str) -> tuple[str, str, str, str]:
    return (f"❌ {title}",
            f"You didn't pass {title} this time. Try again!",
            "assessment_failed", "/labs/")


def daily_streak(days: int) -> tuple[str, str, str, str]:
    return (f"🔥 {days}-day streak!",
            f"You've been learning for {days} days in a row!",
            "achievement", "/dashboard/")


def xp_earned(amount: int, reason: str = ""
              ) -> tuple[str, str, str, str]:
    msg = f"You earned +{amount} XP"
    if reason:
        msg += f" for {reason}"
    return (f"+{amount} XP", f"{msg}.",
            "xp_earned", "/dashboard/")
