"""Virtual Network Topology Engine — the core (YC-026.1).

Design principles:

  * **Data over code.** Topologies live in JSON files, not Python. Adding
    a network for a future lab means dropping a ``.json`` into
    ``app/labs/topology/data/`` and referencing it by name -- no code
    change, no new simulator class.

  * **Immutable at runtime.** Loaded topologies are cached by name. The
    engine never mutates them; simulator state stays in the existing
    per-session state envelope, cleanly separated from the topology
    definition.

  * **Schema-validated.** Every load runs the JSON through
    :func:`_validate_topology` -- device types are checked against
    :data:`DEVICE_TYPES`, links reference known devices, hostnames are
    unique, IPs are basic-format-valid. A malformed file raises
    :class:`TopologySchemaError` at load time (never at request time).

  * **Renderer-friendly.** :meth:`TopologyEngine.render_payload` shapes
    the data exactly like the SVG frontend expects, keeping the client
    dumb and swappable.

  * **Capability-agnostic.** No mention of ping/nmap/pcap here. Any
    simulator can consume the topology; behaviour lives with the
    simulator.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

# ---------------------------------------------------------------------------
# Device catalogue
# ---------------------------------------------------------------------------
# ``future_ready=True`` types have no dedicated behaviour yet but the
# renderer draws them and the schema accepts them -- lab authors can seed
# firewall/IDS/SIEM topologies now, and simulators for them will land in
# future tickets without any engine changes.
DEVICE_TYPES: dict[str, dict[str, Any]] = {
    "router":         {"label": "Router",         "glyph": "\U0001F4E1", "future_ready": False},
    "switch":         {"label": "Switch",         "glyph": "\u26A1",     "future_ready": False},
    "pc":             {"label": "PC",             "glyph": "\U0001F4BB", "future_ready": False},
    "linux-server":   {"label": "Linux Server",   "glyph": "\U0001F427", "future_ready": False},
    "windows-server": {"label": "Windows Server", "glyph": "\U0001F5A5", "future_ready": False},
    "firewall":       {"label": "Firewall",       "glyph": "\U0001F525", "future_ready": True},
    "ids":            {"label": "IDS",            "glyph": "\U0001F441", "future_ready": True},
    "siem":           {"label": "SIEM",           "glyph": "\U0001F4CA", "future_ready": True},
    "internet":       {"label": "Internet",       "glyph": "\U0001F310", "future_ready": False},
}


class TopologyError(RuntimeError):
    """Base class for topology-loading errors."""


class TopologyNotFound(TopologyError):
    """No topology file matches the requested name."""


class TopologySchemaError(TopologyError):
    """The topology JSON exists but fails validation."""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Device:
    """One immutable device inside a topology.

    Fields intentionally overlap with :class:`app.labs.interactive_network_simulator.Host`
    -- the topology engine is the source of truth for a *definition*,
    the simulator's Host is the source of truth for *behaviour*. A
    simulator can materialise Devices as Hosts one-to-one; a purely
    visual lab (Wireshark viewer, SIEM dashboard) can consume Devices
    directly.
    """

    hostname: str
    label: str
    device_type: str
    os: str = ""
    ip: str = ""
    mac: str = ""
    gateway: str = ""
    subnet_mask: str = "255.255.255.0"       # YC-026.3: /24 by default
    dns: str = "8.8.8.8"                     # YC-026.3
    online: bool = True                      # YC-026.3: hosts can be simulated down
    open_ports: tuple[int, ...] = ()
    services: dict[int, str] = field(default_factory=dict)
    x: Optional[float] = None      # optional pre-set layout coordinates
    y: Optional[float] = None
    tags: tuple[str, ...] = ()     # e.g. ("dmz",) -- used by future firewall lab

    def summary(self) -> dict[str, Any]:
        """The exact structure a clicked-device panel expects.

        Kept identical across every simulator so the frontend never has
        to branch on device type.
        """
        return {
            "hostname": self.hostname,
            "label": self.label,
            "device_type": self.device_type,
            "os": self.os or "—",
            "ip": self.ip or "—",
            "mac": self.mac or "—",
            "gateway": self.gateway or "—",
            "subnet_mask": self.subnet_mask,
            "dns": self.dns,
            "status": "Online" if self.online else "Offline",
            "online": self.online,
            "open_ports": [
                {"port": p, "service": self.services.get(p, "—")}
                for p in self.open_ports
            ],
            "tags": list(self.tags),
        }

    @property
    def subnet(self) -> str:
        """CIDR-style subnet of this device (``192.168.1.0/24`` for a
        192.168.1.x /24). Handy for reachability logic that has to
        know whether two hosts share a broadcast domain.

        Only handles /24 today because that's all every existing
        topology uses; wider mask support goes here when the first lab
        needs it.
        """
        if not self.ip:
            return ""
        parts = self.ip.split(".")
        if len(parts) != 4:
            return ""
        return ".".join(parts[:3]) + ".0/24"


@dataclass(frozen=True)
class Link:
    """A bidirectional connection between two devices."""

    a: str
    b: str
    kind: str = "ethernet"     # ethernet | wifi | wan  (renderer hint only)
    bandwidth_mbps: int = 1000
    latency_ms: float = 1.0

    def endpoints(self) -> tuple[str, str]:
        return (self.a, self.b) if self.a <= self.b else (self.b, self.a)


# ---------------------------------------------------------------------------
# Topology engine
# ---------------------------------------------------------------------------
class TopologyEngine:
    """Read-only view of one loaded topology.

    Construct via :func:`load_topology` (which caches by name);
    downstream code never instantiates this class directly.
    """

    def __init__(self, name: str, raw: dict[str, Any], source: Path) -> None:
        self.name: str = name
        self.title: str = raw.get("title", name.replace("-", " ").title())
        self.description: str = raw.get("description", "")
        self.source: Path = source

        self._devices: dict[str, Device] = {}
        for spec in raw.get("devices", []):
            device = _make_device(spec)
            self._devices[device.hostname] = device

        self._links: tuple[Link, ...] = tuple(
            Link(
                a=spec["a"], b=spec["b"],
                kind=spec.get("kind", "ethernet"),
                bandwidth_mbps=int(spec.get("bandwidth_mbps", 1000)),
                latency_ms=float(spec.get("latency_ms", 1.0)),
            )
            for spec in raw.get("links", [])
        )

        # Neighbour index — one scan at load time, O(1) lookups after.
        self._adjacency: dict[str, set[str]] = {h: set() for h in self._devices}
        for link in self._links:
            self._adjacency[link.a].add(link.b)
            self._adjacency[link.b].add(link.a)

    # ---- Public accessors --------------------------------------------
    @property
    def devices(self) -> tuple[Device, ...]:
        return tuple(self._devices.values())

    @property
    def links(self) -> tuple[Link, ...]:
        return self._links

    def device(self, hostname: str) -> Optional[Device]:
        return self._devices.get(hostname)

    def neighbours(self, hostname: str) -> tuple[str, ...]:
        return tuple(sorted(self._adjacency.get(hostname, set())))

    def path(self, start: str, end: str) -> Optional[list[str]]:
        """Shortest path via BFS, or ``None`` if disconnected. Reused by
        any simulator that needs reachability (ping, traceroute)."""
        if start not in self._devices or end not in self._devices:
            return None
        if start == end:
            return [start]
        seen, queue = {start}, [[start]]
        while queue:
            path = queue.pop(0)
            for n in self._adjacency.get(path[-1], ()):
                if n in seen:
                    continue
                new_path = path + [n]
                if n == end:
                    return new_path
                seen.add(n)
                queue.append(new_path)
        return None

    def reachable(self, a: str, b: str) -> bool:
        return self.path(a, b) is not None

    def find_device(self, key: str) -> Optional[Device]:
        """Match by hostname OR IP OR label (case-insensitive)."""
        if not key:
            return None
        for d in self._devices.values():
            if d.hostname == key or d.ip == key or d.label.lower() == key.lower():
                return d
        return None

    # ---- Renderer payload --------------------------------------------
    def render_payload(self) -> dict[str, Any]:
        """Shape consumed by the frontend SVG renderer.

        Kept minimal on purpose -- the client doesn't need to know about
        ports, ARP tables, or link bandwidth to *draw* the network.
        Clicking a node fetches ``describe_device()`` separately.
        """
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "nodes": [
                {
                    "hostname": d.hostname,
                    "label": d.label,
                    "device_type": d.device_type,
                    "ip": d.ip,
                    "os": d.os,
                    "x": d.x,
                    "y": d.y,
                    "future_ready": DEVICE_TYPES.get(
                        d.device_type, {"future_ready": False})["future_ready"],
                }
                for d in self._devices.values()
            ],
            "links": [
                {"a": l.a, "b": l.b, "kind": l.kind,
                 "bandwidth_mbps": l.bandwidth_mbps}
                for l in self._links
            ],
        }

    def describe_device(self, hostname: str) -> Optional[dict[str, Any]]:
        """Detail panel payload (Hostname / IP / MAC / OS / ports / neighbours).
        Returned when a user clicks a device."""
        device = self._devices.get(hostname)
        if device is None:
            return None
        summary = device.summary()
        summary["connected"] = [
            {"hostname": n, "label": self._devices[n].label,
             "device_type": self._devices[n].device_type}
            for n in sorted(self._adjacency.get(hostname, set()))
        ]
        return summary


# ---------------------------------------------------------------------------
# Loading & caching
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent / "data"
_CACHE: dict[str, TopologyEngine] = {}
_CACHE_LOCK = threading.Lock()


def load_topology(name: str, *, refresh: bool = False) -> TopologyEngine:
    """Load a topology by file-name stem (without ``.json``).

    Thread-safe cache: several requests hitting a lab in parallel will
    each get the same immutable engine object without re-parsing.
    Pass ``refresh=True`` to force a reload (used by tests).
    """
    if not refresh and name in _CACHE:
        return _CACHE[name]

    path = _DATA_DIR / f"{name}.json"
    if not path.is_file():
        raise TopologyNotFound(
            f"No topology named {name!r} in {_DATA_DIR}. "
            f"Add {name}.json to enable it."
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TopologySchemaError(f"{name}.json is not valid JSON: {exc}") from exc

    _validate_topology(name, raw)

    with _CACHE_LOCK:
        engine = TopologyEngine(name, raw, source=path)
        _CACHE[name] = engine
    return engine


def list_topologies() -> list[str]:
    """Names of every ``.json`` file the loader will accept.
    Useful for admin/debug UIs; not called on hot paths."""
    if not _DATA_DIR.is_dir():
        return []
    return sorted(p.stem for p in _DATA_DIR.glob("*.json"))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
_HOSTNAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_IP_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


def _make_device(spec: dict[str, Any]) -> Device:
    ports = tuple(int(p) for p in spec.get("open_ports", ()))
    services = {int(k): str(v) for k, v in spec.get("services", {}).items()}
    return Device(
        hostname=spec["hostname"],
        label=spec.get("label", spec["hostname"].upper()),
        device_type=spec["device_type"],
        os=spec.get("os", ""),
        ip=spec.get("ip", ""),
        mac=spec.get("mac", ""),
        gateway=spec.get("gateway", ""),
        subnet_mask=spec.get("subnet_mask", "255.255.255.0"),
        dns=spec.get("dns", "8.8.8.8"),
        online=bool(spec.get("online", True)),
        open_ports=ports,
        services=services,
        x=spec.get("x"),
        y=spec.get("y"),
        tags=tuple(spec.get("tags", ())),
    )


def _validate_topology(name: str, raw: dict[str, Any]) -> None:
    """Fail loudly at load-time if the JSON is bad — never at click-time."""
    if not isinstance(raw, dict) or "devices" not in raw or "links" not in raw:
        raise TopologySchemaError(f"{name}.json must contain 'devices' and 'links'.")

    seen: set[str] = set()
    for spec in raw.get("devices", []):
        hostname = spec.get("hostname")
        if not hostname or not _HOSTNAME_RE.match(hostname):
            raise TopologySchemaError(
                f"{name}: invalid hostname {hostname!r} "
                f"(lowercase, digits, hyphens; 1–63 chars)."
            )
        if hostname in seen:
            raise TopologySchemaError(f"{name}: duplicate hostname {hostname!r}.")
        seen.add(hostname)

        device_type = spec.get("device_type")
        if device_type not in DEVICE_TYPES:
            raise TopologySchemaError(
                f"{name}: unknown device_type {device_type!r} on {hostname!r}. "
                f"Allowed: {sorted(DEVICE_TYPES)}."
            )
        ip = spec.get("ip", "")
        if ip and not _IP_RE.match(ip):
            raise TopologySchemaError(
                f"{name}: invalid IP {ip!r} on {hostname!r}."
            )

    for link in raw.get("links", []):
        for endpoint in ("a", "b"):
            if link.get(endpoint) not in seen:
                raise TopologySchemaError(
                    f"{name}: link endpoint {link.get(endpoint)!r} "
                    f"is not a known device."
                )
        if link["a"] == link["b"]:
            raise TopologySchemaError(f"{name}: link has identical endpoints.")
