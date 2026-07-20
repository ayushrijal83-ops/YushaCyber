"""Virtual Network Services & Connectivity Engine (YC-026.3).

The single source of truth for how virtual devices *reach* each other.
Every future simulator (Nmap, Wireshark, firewall, AD, SOC) plugs into
this module — none of them owns its own reachability or packet code.

Public surface
--------------
    Packet                     — immutable simulated packet object
    NetworkEngine              — reachable/path/ping/traceroute/scan_port
    make_engine(topology)      — factory bound to a TopologyEngine
    make_engine_from_devices() — factory for simulator-owned host lists

Everything is a pure function of the topology snapshot passed in — no
sockets, no subprocess, no filesystem. Latency, TTL and hop timings are
deterministic (seeded pseudo-random) so labs and objectives can validate
exact output.
"""

from __future__ import annotations

from app.labs.net_engine.engine import (
    DEFAULT_TTL,
    NetworkEngine,
    Packet,
    PacketStatus,
    PingReply,
    PortState,
    SERVICE_CATALOGUE,
    TracerouteHop,
    TracerouteResult,
    make_engine,
    make_engine_from_devices,
    subnet_of,
    same_subnet,
)

__all__ = [
    "DEFAULT_TTL",
    "NetworkEngine",
    "Packet",
    "PacketStatus",
    "PingReply",
    "PortState",
    "SERVICE_CATALOGUE",
    "TracerouteHop",
    "TracerouteResult",
    "make_engine",
    "make_engine_from_devices",
    "subnet_of",
    "same_subnet",
]
