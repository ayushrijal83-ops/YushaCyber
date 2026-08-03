"""Meeting provider abstraction — Jitsi default + pluggable adapters."""

from __future__ import annotations

import hashlib
from typing import Any


class BaseProvider:
    name: str = "base"

    def generate_url(self, room: str) -> str:
        raise NotImplementedError

    def health(self) -> dict[str, Any]:
        return {"provider": self.name, "status": "ok"}


class JitsiProvider(BaseProvider):
    name = "jitsi"
    base_url = "https://meet.jit.si"

    def generate_url(self, room: str) -> str:
        safe_room = hashlib.md5(room.encode()).hexdigest()[:12]
        return f"{self.base_url}/yushacyber-{safe_room}"


class ZoomProvider(BaseProvider):
    name = "zoom"

    def generate_url(self, room: str) -> str:
        return ""  # requires API integration


class GoogleMeetProvider(BaseProvider):
    name = "google_meet"

    def generate_url(self, room: str) -> str:
        return ""


class TeamsProvider(BaseProvider):
    name = "teams"

    def generate_url(self, room: str) -> str:
        return ""


PROVIDERS: dict[str, BaseProvider] = {
    "jitsi": JitsiProvider(),
    "zoom": ZoomProvider(),
    "google_meet": GoogleMeetProvider(),
    "teams": TeamsProvider(),
}


def get_provider(name: str) -> BaseProvider:
    return PROVIDERS.get(name, PROVIDERS["jitsi"])


def register_provider(name: str, provider: BaseProvider) -> None:
    PROVIDERS[name] = provider


def generate_url(live_class) -> str:
    provider = get_provider(live_class.meeting_provider)
    room = live_class.meeting_room or live_class.slug
    return provider.generate_url(room)
