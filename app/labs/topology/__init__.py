"""Virtual Network Topology Engine (YC-026.1).

Reusable, JSON-driven representation of a network. Powers every future
lab that needs a virtual network (Nmap, Wireshark, firewall, AD, IDS,
SIEM) without any simulator-specific code:

  · **Data**  — plain-JSON files in ``app/labs/topology/data/``. Each
    file declares devices (routers, switches, PCs, servers) and links.
  · **Loader** — :class:`TopologyEngine` reads, validates, indexes and
    exposes topologies with a clean read-only API.
  · **Renderer contract** — :meth:`TopologyEngine.render_payload`
    produces exactly what the frontend SVG renderer needs, so a
    simulator only has to answer "which topology am I on?".

Nothing in this package touches XP, achievements, auth or any engine
built in earlier tickets — it's a purely additive data layer.
"""

from __future__ import annotations

from app.labs.topology.engine import (
    DEVICE_TYPES,
    Device,
    Link,
    TopologyEngine,
    load_topology,
)
from app.labs.topology.network import (
    DeviceRuntime,
    Packet,
    PacketFlow,
    PingResult,
    PortResult,
    Route,
    SERVICES,
    Subnet,
    SubnetIndex,
    TracerouteResult,
    network_status,
    ping,
    probe_port,
    route_to,
    same_subnet,
    scan_ports,
    service_name,
    src_ttl_for,
    traceroute,
)

__all__ = [
    "DEVICE_TYPES",
    "Device",
    "DeviceRuntime",
    "Link",
    "TopologyEngine",
    "load_topology",
    "Packet",
    "PacketFlow",
    "PingResult",
    "PortResult",
    "Route",
    "SERVICES",
    "Subnet",
    "SubnetIndex",
    "TracerouteResult",
    "network_status",
    "ping",
    "probe_port",
    "route_to",
    "same_subnet",
    "scan_ports",
    "service_name",
    "src_ttl_for",
    "traceroute",
]
