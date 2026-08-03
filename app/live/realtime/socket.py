"""Socket integration layer — Flask-SocketIO event handlers.

This module only activates when Flask-SocketIO is installed.
All logic lives in the other modules; this just wires socket
events to them. If SocketIO is not available, the REST API
in routes.py provides the same functionality via polling.
"""

from __future__ import annotations

from typing import Any

_socketio = None


def init_socketio(app) -> bool:
    """Try to initialize SocketIO. Returns True if available."""
    global _socketio
    try:
        from flask_socketio import SocketIO  # noqa: F401
        _socketio = SocketIO(app, cors_allowed_origins="*",
                             async_mode="threading")
        _register_events()
        return True
    except ImportError:
        return False


def is_available() -> bool:
    return _socketio is not None


def broadcast_to_room(class_slug: str, event: str,
                      data: dict[str, Any]) -> None:
    """Broadcast an event to all members of a classroom room."""
    if _socketio is None:
        return
    from flask_socketio import emit as sio_emit
    room = f"classroom:{class_slug}"
    sio_emit(event, data, room=room, namespace="/classroom")


def _register_events() -> None:
    """Register all SocketIO event handlers."""
    if _socketio is None:
        return
    from flask_socketio import emit, join_room, leave_room

    @_socketio.on("join", namespace="/classroom")
    def on_join(data):
        slug = data.get("slug", "")
        user_id = data.get("user_id", 0)
        username = data.get("username", "")
        room = f"classroom:{slug}"
        join_room(room)
        from app.live.realtime import rooms, presence, events
        rooms.join(slug, user_id, username)
        presence.update(slug, user_id, "online")
        events.emit(slug, "student_joined", user_id, username)
        emit("user_joined", {"user_id": user_id,
                              "username": username},
             room=room)

    @_socketio.on("leave", namespace="/classroom")
    def on_leave(data):
        slug = data.get("slug", "")
        user_id = data.get("user_id", 0)
        room = f"classroom:{slug}"
        leave_room(room)
        from app.live.realtime import rooms, presence, events
        rooms.leave(slug, user_id)
        presence.remove(slug, user_id)
        events.emit(slug, "student_left", user_id)
        emit("user_left", {"user_id": user_id}, room=room)

    @_socketio.on("chat_message", namespace="/classroom")
    def on_chat(data):
        slug = data.get("slug", "")
        from app.live.realtime import chat
        msg = chat.send(slug, data.get("user_id", 0),
                        data.get("username", ""),
                        data.get("message", ""))
        emit("new_message", msg, room=f"classroom:{slug}")

    @_socketio.on("heartbeat", namespace="/classroom")
    def on_heartbeat(data):
        from app.live.realtime import heartbeat
        heartbeat.beat(data.get("slug", ""),
                       data.get("user_id", 0))

    @_socketio.on("raise_hand", namespace="/classroom")
    def on_raise(data):
        slug = data.get("slug", "")
        from app.live.realtime import handraise
        handraise.raise_hand(slug, data.get("user_id", 0),
                             data.get("username", ""))
        emit("hand_raised", data, room=f"classroom:{slug}")

    @_socketio.on("lower_hand", namespace="/classroom")
    def on_lower(data):
        slug = data.get("slug", "")
        from app.live.realtime import handraise
        handraise.lower_hand(slug, data.get("user_id", 0))
        emit("hand_lowered", data, room=f"classroom:{slug}")
