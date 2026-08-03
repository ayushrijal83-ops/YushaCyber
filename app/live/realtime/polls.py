"""Live polls — create, vote, close, results."""

from __future__ import annotations

import time
from typing import Any

_polls: dict[str, list[dict[str, Any]]] = {}


def create_poll(class_slug: str, question: str,
                options: list[str],
                poll_type: str = "multiple_choice"
                ) -> dict[str, Any]:
    key = f"classroom:{class_slug}"
    poll = {
        "id": f"poll-{time.time_ns()}",
        "question": question[:300],
        "options": options[:10],
        "poll_type": poll_type,
        "votes": {},  # user_id → option_index
        "created_at": time.time(),
        "closed": False,
    }
    if key not in _polls:
        _polls[key] = []
    _polls[key].append(poll)
    return poll


def vote(class_slug: str, poll_id: str,
         user_id: int, choice: int) -> bool:
    key = f"classroom:{class_slug}"
    for poll in (_polls.get(key) or []):
        if poll["id"] == poll_id and not poll["closed"]:
            if user_id not in poll["votes"]:
                if 0 <= choice < len(poll["options"]):
                    poll["votes"][user_id] = choice
                    return True
    return False


def results(class_slug: str,
            poll_id: str) -> dict[str, Any] | None:
    key = f"classroom:{class_slug}"
    for poll in (_polls.get(key) or []):
        if poll["id"] == poll_id:
            totals = [0] * len(poll["options"])
            for choice in poll["votes"].values():
                if 0 <= choice < len(totals):
                    totals[choice] += 1
            total_votes = sum(totals)
            return {
                "id": poll["id"],
                "question": poll["question"],
                "options": poll["options"],
                "totals": totals,
                "total_votes": total_votes,
                "percentages": [
                    round(t / max(1, total_votes) * 100)
                    for t in totals],
                "closed": poll["closed"],
            }
    return None


def close_poll(class_slug: str, poll_id: str) -> bool:
    key = f"classroom:{class_slug}"
    for poll in (_polls.get(key) or []):
        if poll["id"] == poll_id:
            poll["closed"] = True
            return True
    return False


def active_polls(class_slug: str) -> list[dict[str, Any]]:
    key = f"classroom:{class_slug}"
    return [p for p in (_polls.get(key) or [])
            if not p["closed"]]
