"""Discussion Engine (YC-034.0).

Every lab and lesson carries a discussion board: threads (optionally
marked as questions), replies, and a pinned answer chosen by the
thread author, a teacher, or an admin. Rendered as a partial included
at the bottom of the existing lab and lesson pages — those pages keep
their own logic untouched.
"""

from __future__ import annotations

from app.community.models import (
    DISCUSSION_SUBJECTS,
    DiscussionReply,
    DiscussionThread,
)
from app.extensions import db


class DiscussionError(ValueError):
    """User-facing discussion rule violation."""


def threads_for(subject_type: str,
                subject_id: int) -> list[DiscussionThread]:
    return (DiscussionThread.query
            .filter_by(subject_type=subject_type, subject_id=subject_id)
            .order_by(DiscussionThread.created_at.desc()).all())


def create_thread(author_id: int, subject_type: str, subject_id: int,
                  title: str, body: str = "",
                  is_question: bool = False) -> DiscussionThread:
    if subject_type not in DISCUSSION_SUBJECTS:
        raise DiscussionError("Discussions exist on labs and lessons.")
    title = (title or "").strip()
    if not 3 <= len(title) <= 160:
        raise DiscussionError("Give the thread a title (3–160 chars).")
    thread = DiscussionThread(
        author_id=author_id, subject_type=subject_type,
        subject_id=int(subject_id), title=title,
        body=(body or "").strip(), is_question=bool(is_question))
    db.session.add(thread)
    db.session.commit()
    return thread


def add_reply(thread: DiscussionThread, author_id: int,
              body: str) -> DiscussionReply:
    body = (body or "").strip()
    if not body:
        raise DiscussionError("A reply needs some text.")
    reply = DiscussionReply(thread_id=thread.id, author_id=author_id,
                            body=body)
    db.session.add(reply)
    db.session.commit()
    return reply


def can_moderate(user, thread: DiscussionThread) -> bool:
    return (user.is_admin or getattr(user, "role", "") == "mentor"
            or thread.author_id == user.id)


def pin_reply(thread: DiscussionThread, actor,
              reply_id: int) -> None:
    """Mark a reply as the accepted answer (author/teacher/admin)."""
    if not can_moderate(actor, thread):
        raise DiscussionError(
            "Only the author, a teacher or an admin can pin an answer.")
    reply = DiscussionReply.query.filter_by(id=reply_id,
                                            thread_id=thread.id).first()
    if not reply:
        raise DiscussionError("That reply does not belong to this thread.")
    # Toggle: pinning the pinned reply un-pins it.
    thread.pinned_reply_id = None if thread.pinned_reply_id == reply.id \
        else reply.id
    db.session.commit()
