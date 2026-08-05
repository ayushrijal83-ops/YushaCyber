"""Realtime services — the public API for the classroom engine."""

from __future__ import annotations

from typing import Any

from app.live.realtime import (
    announcements,
    chat,
    events,
    handraise,
    heartbeat,
    polls,
    presence,
    rooms,
)


# ── Room management ──
def join_classroom(slug: str, user_id: int,
                   username: str = "",
                   role: str = "student") -> dict[str, Any]:
    rooms.join(slug, user_id, username)
    presence.update(slug, user_id, "online")
    heartbeat.beat(slug, user_id)
    events.emit(slug, "student_joined", user_id, username)
    return {"joined": True, "members": rooms.count(slug)}


def leave_classroom(slug: str, user_id: int) -> dict[str, Any]:
    rooms.leave(slug, user_id)
    presence.remove(slug, user_id)
    heartbeat.remove(slug, user_id)
    handraise.lower_hand(slug, user_id)
    events.emit(slug, "student_left", user_id)
    return {"left": True, "members": rooms.count(slug)}


# ── Chat ──
def send_chat(slug: str, user_id: int, username: str,
              message: str) -> dict[str, Any]:
    result = chat.send(slug, user_id, username, message)
    # Normalize key for API consumers.
    if "text" in result and "message" not in result:
        result["message"] = result["text"]
    return result


def chat_history(slug: str, limit: int = 50) -> list[dict[str, Any]]:
    return chat.history(slug, limit)


def delete_chat(slug: str, msg_id: str,
                user_id: int = 0,
                is_instructor: bool = False) -> bool:
    return chat.delete_message(slug, msg_id, user_id, is_instructor)


# ── Presence ──
def get_presence(slug: str) -> list[dict[str, Any]]:
    return presence.all_presence(slug)


def heartbeat_ping(slug: str, user_id: int) -> None:
    heartbeat.beat(slug, user_id)
    presence.update(slug, user_id, "online")


# ── Hand raise ──
def raise_hand(slug: str, user_id: int,
               username: str = "") -> dict[str, Any]:
    events.emit(slug, "hand_raised", user_id, username)
    return handraise.raise_hand(slug, user_id, username)


def lower_hand(slug: str, user_id: int) -> bool:
    events.emit(slug, "hand_lowered", user_id)
    return handraise.lower_hand(slug, user_id)


def hand_queue(slug: str) -> list[dict[str, Any]]:
    return handraise.get_queue(slug)


def clear_hands(slug: str) -> int:
    return handraise.clear_queue(slug)


# ── Polls ──
def create_poll(slug: str, question: str,
                options: list[str],
                poll_type: str = "multiple_choice"
                ) -> dict[str, Any]:
    poll = polls.create_poll(slug, question, options, poll_type)
    events.emit(slug, "poll_opened", data={"poll_id": poll["id"]})
    return poll


def vote_poll(slug: str, poll_id: str,
              user_id: int, choice: str | int) -> bool:
    # Convert string choice to index if needed.
    if isinstance(choice, str):
        # Find the poll to look up option index.
        active = polls.active_polls(slug)
        for p in active:
            if p["id"] == poll_id:
                opts = p.get("options", [])
                if choice in opts:
                    choice = opts.index(choice)
                    break
                else:
                    return False
    return polls.vote(slug, poll_id, user_id, choice)


def poll_results(slug: str, poll_id: str) -> dict[str, Any] | None:
    return polls.results(slug, poll_id)


def close_poll_service(slug: str, poll_id: str) -> bool:
    events.emit(slug, "poll_closed", data={"poll_id": poll_id})
    return polls.close_poll(slug, poll_id)


# ── Announcements ──
def make_announcement(slug: str, text: str,
                      author: str = "") -> dict[str, Any]:
    ann = announcements.broadcast(slug, text, author)
    events.emit(slug, "announcement", data={"text": text})
    return ann


def pin_announcement(slug: str, ann_id: str) -> bool:
    return announcements.pin(slug, ann_id)


def unpin_announcement(slug: str, ann_id: str) -> bool:
    return announcements.unpin(slug, ann_id)


def get_announcements(slug: str) -> list[dict[str, Any]]:
    return announcements.get_all(slug)


# ── Events / Timeline ──
def timeline(slug: str, limit: int = 20) -> list[dict[str, Any]]:
    return events.recent(slug, limit)


# ── Classroom state (for AI context) ──
def classroom_state(slug: str) -> dict[str, Any]:
    return {
        "members": rooms.count(slug),
        "presence": presence.all_presence(slug),
        "hand_queue": handraise.get_queue(slug),
        "active_polls": polls.active_polls(slug),
        "pinned_announcements": announcements.get_pinned(slug),
        "recent_chat": chat.history(slug, 10),
        "recent_events": events.recent(slug, 10),
    }
