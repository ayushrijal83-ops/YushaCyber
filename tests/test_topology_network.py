"""YC-026.3 — Virtual Network Services Engine tests.

Pure-function tests: no Flask app, no database. The topology JSON files
in ``app/labs/topology/data/`` are the only fixtures. Every assertion is
exact because the engine is deterministic by design.

Run:  python -m pytest tests/test_topology_network.py -v
"""

from __future__ import annotations

import threading

import pytest

from app.labs.topology import (
    DeviceRuntime,
    PacketFlow,
    Subnet,
    SubnetIndex,
    load_topology,
    network_status,
    ping,
    probe_port,
    route_to,
    same_subnet,
    scan_ports,
    traceroute,
)


@pytest.fixture()
def office():
    return load_topology("small-office")


@pytest.fixture()
def dmz():
    return load_topology("dmz-blueteam")


# ---------------------------------------------------------------------------
# Subnet — CIDR arithmetic
# ---------------------------------------------------------------------------
class TestSubnet:
    def test_from_cidr_normalises_host_bits(self):
        s = Subnet.from_cidr("192.168.1.37/24")
        assert s.network == "192.168.1.0"
        assert s.prefix == 24
        assert s.cidr == "192.168.1.0/24"

    def test_from_ip_and_mask(self):
        s = Subnet.from_ip_and_mask("10.10.0.50", "255.255.255.0")
        assert s == Subnet.from_cidr("10.10.0.0/24")

    def test_non_slash24_arithmetic(self):
        s = Subnet.from_cidr("172.16.10.130/26")
        assert s.network == "172.16.10.128"
        assert s.netmask == "255.255.255.192"
        assert s.broadcast == "172.16.10.191"
        assert s.first_host == "172.16.10.129"
        assert s.last_host == "172.16.10.190"
        assert s.usable_hosts == 62

    def test_slash30_point_to_point(self):
        s = Subnet.from_cidr("10.0.0.4/30")
        assert s.usable_hosts == 2
        assert s.first_host == "10.0.0.5"
        assert s.last_host == "10.0.0.6"
        assert s.broadcast == "10.0.0.7"

    def test_contains(self):
        s = Subnet.from_cidr("192.168.1.0/24")
        assert s.contains("192.168.1.1")
        assert s.contains("192.168.1.254")
        assert not s.contains("192.168.2.1")
        assert not s.contains("not-an-ip")

    def test_mask_prefix_round_trip(self):
        assert Subnet.mask_to_prefix("255.255.255.0") == 24
        assert Subnet.mask_to_prefix("255.255.255.192") == 26
        assert Subnet.prefix_to_mask(26) == "255.255.255.192"
        assert Subnet.prefix_to_mask(0) == "0.0.0.0"

    def test_rejects_garbage(self):
        with pytest.raises(ValueError):
            Subnet.from_cidr("192.168.1.0")           # no prefix
        with pytest.raises(ValueError):
            Subnet.from_cidr("300.1.1.1/24")          # bad octet
        with pytest.raises(ValueError):
            Subnet.mask_to_prefix("255.0.255.0")      # non-contiguous
        with pytest.raises(ValueError):
            Subnet(network="192.168.1.5", prefix=24)  # host bits set

    def test_to_dict_shape(self):
        d = Subnet.from_cidr("192.168.1.0/24").to_dict()
        assert d["cidr"] == "192.168.1.0/24"
        assert d["broadcast"] == "192.168.1.255"
        assert d["usable_hosts"] == 254


# ---------------------------------------------------------------------------
# SubnetIndex
# ---------------------------------------------------------------------------
class TestSubnetIndex:
    def test_office_subnets(self, office):
        index = SubnetIndex(office)
        cidrs = [s.cidr for s in index.subnets]
        assert "192.168.1.0/24" in cidrs        # LAN
        assert "203.0.113.0/24" in cidrs        # internet edge

    def test_subnet_of_by_hostname_and_ip(self, office):
        index = SubnetIndex(office)
        assert index.subnet_of("pc-1").cidr == "192.168.1.0/24"
        assert index.subnet_of("192.168.1.20").cidr == "192.168.1.0/24"
        assert index.subnet_of("no-such-host") is None

    def test_devices_in(self, office):
        index = SubnetIndex(office)
        hosts = [d.hostname for d in index.devices_in("192.168.1.0/24")]
        assert hosts == ["edge-router", "pc-1", "pc-2", "web-server", "db-server"]

    def test_switch_without_ip_is_excluded(self, office):
        index = SubnetIndex(office)
        assert index.subnet_of("core-switch") is None

    def test_share_subnet(self, office):
        index = SubnetIndex(office)
        assert index.share_subnet("pc-1", "db-server")
        assert not index.share_subnet("pc-1", "internet")

    def test_same_subnet_uses_real_masks(self, office, dmz):
        assert same_subnet(office, "pc-1", "web-server")
        assert not same_subnet(office, "pc-1", "internet")
        # DMZ topology: analyst network vs DMZ network
        assert same_subnet(dmz, "analyst-pc", "ids-1")
        assert not same_subnet(dmz, "analyst-pc", "dmz-web")


# ---------------------------------------------------------------------------
# DeviceRuntime — online/offline overlay
# ---------------------------------------------------------------------------
class TestDeviceRuntime:
    def test_defaults_follow_topology(self, office):
        rt = DeviceRuntime(office)
        assert rt.is_online("web-server")
        assert rt.is_online("pc-1")

    def test_set_offline_and_reset(self, office):
        rt = DeviceRuntime(office)
        assert rt.set_offline("web-server")
        assert not rt.is_online("web-server")
        rt.reset("web-server")
        assert rt.is_online("web-server")

    def test_toggle(self, office):
        rt = DeviceRuntime(office)
        assert rt.toggle("db-server") is False
        assert rt.toggle("db-server") is True
        assert rt.toggle("ghost-host") is None

    def test_unknown_host(self, office):
        rt = DeviceRuntime(office)
        assert not rt.set_offline("ghost-host")
        assert not rt.is_online("ghost-host")

    def test_snapshot_round_trip(self, office):
        rt = DeviceRuntime(office)
        rt.set_offline("pc-2")
        snap = rt.snapshot()
        assert snap["pc-2"] is False and snap["pc-1"] is True

        rt2 = DeviceRuntime(office)
        rt2.load_snapshot(snap)
        assert not rt2.is_online("pc-2")
        assert rt2.is_online("pc-1")

    def test_topology_object_never_mutated(self, office):
        rt = DeviceRuntime(office)
        rt.set_offline("web-server")
        assert office.device("web-server").online is True  # frozen source

    def test_thread_safety_smoke(self, office):
        rt = DeviceRuntime(office)

        def hammer():
            for _ in range(200):
                rt.toggle("pc-1")
                rt.snapshot()

        threads = [threading.Thread(target=hammer) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert isinstance(rt.is_online("pc-1"), bool)


# ---------------------------------------------------------------------------
# Runtime integration with ping / traceroute / ports / status
# ---------------------------------------------------------------------------
class TestRuntimeIntegration:
    def test_ping_offline_destination(self, office):
        rt = DeviceRuntime(office)
        rt.set_offline("db-server")
        result = ping(office, "pc-1", "db-server", runtime=rt)
        assert not result.ok
        assert result.reason == "destination offline"
        assert result.loss_pct == 100
        assert result.packets[0].status == "timeout"

    def test_ping_recovers_after_reset(self, office):
        rt = DeviceRuntime(office)
        rt.set_offline("db-server")
        rt.reset()
        result = ping(office, "pc-1", "db-server", runtime=rt)
        assert result.ok and result.received == 4 and result.loss_pct == 0

    def test_traceroute_offline_source(self, office):
        rt = DeviceRuntime(office)
        rt.set_offline("pc-1")
        result = traceroute(office, "pc-1", "web-server", runtime=rt)
        assert not result.ok and result.reason == "source offline"

    def test_port_probe_filtered_when_offline(self, office):
        rt = DeviceRuntime(office)
        assert probe_port(office, "pc-1", "web-server", 80).state == "open"
        rt.set_offline("web-server")
        assert probe_port(office, "pc-1", "web-server", 80,
                          runtime=rt).state == "filtered"

    def test_scan_ports_with_runtime(self, office):
        rt = DeviceRuntime(office)
        rt.set_offline("db-server")
        results = scan_ports(office, "pc-1", "db-server",
                             [3306, 3389, 8080], runtime=rt)
        assert [r.state for r in results] == ["filtered"] * 3

    def test_network_status_reflects_runtime(self, office):
        rt = DeviceRuntime(office)
        rt.set_offline("pc-2")
        status = network_status(office, runtime=rt)
        by_host = {d["hostname"]: d for d in status["devices"]}
        assert by_host["pc-2"]["status"] == "Offline"
        assert status["offline"] == 1
        assert status["online"] == status["total"] - 1

    def test_route_to_without_runtime_unchanged(self, office):
        """Backwards compatibility: every pre-YC-026.3 call site passes
        no runtime and must behave exactly as before."""
        route = route_to(office, "pc-1", "web-server")
        assert route.ok
        assert route.hops == ("pc-1", "core-switch", "web-server")


# ---------------------------------------------------------------------------
# PacketFlow
# ---------------------------------------------------------------------------
class TestPacketFlow:
    def test_from_ping(self, office):
        result = ping(office, "pc-1", "web-server", count=3)
        flow = PacketFlow.from_ping(result)
        assert flow is not None
        assert flow.protocol == "icmp"
        assert flow.source == "pc-1" and flow.destination == "web-server"
        assert flow.packet_count == 3
        assert flow.delivered == 3
        assert flow.loss_pct == 0
        assert flow.ok

    def test_flow_id_deterministic(self, office):
        r1 = ping(office, "pc-1", "web-server")
        r2 = ping(office, "pc-1", "web-server")
        f1, f2 = PacketFlow.from_ping(r1), PacketFlow.from_ping(r2)
        assert f1.flow_id == f2.flow_id == "icmp:pc-1>web-server#0"
        assert PacketFlow.from_ping(r1, discriminator=7).flow_id \
            == "icmp:pc-1>web-server#7"

    def test_failed_ping_flow(self, office):
        rt = DeviceRuntime(office)
        rt.set_offline("web-server")
        result = ping(office, "pc-1", "web-server", runtime=rt)
        flow = PacketFlow.from_ping(result)
        assert flow is not None
        assert not flow.ok
        assert flow.loss_pct == 100

    def test_unknown_host_produces_no_flow(self, office):
        result = ping(office, "pc-1", "ghost-host")
        assert PacketFlow.from_ping(result) is None

    def test_from_packets_rejects_mixed_endpoints(self, office):
        a = ping(office, "pc-1", "web-server", count=1).packets
        b = ping(office, "pc-1", "db-server", count=1).packets
        with pytest.raises(ValueError):
            PacketFlow.from_packets(list(a) + list(b))
        with pytest.raises(ValueError):
            PacketFlow.from_packets([])

    def test_to_dict_shape(self, office):
        flow = PacketFlow.from_ping(ping(office, "pc-1", "web-server", count=2))
        d = flow.to_dict()
        assert d["flow_id"] == "icmp:pc-1>web-server#0"
        assert d["packet_count"] == 2 and d["ok"] is True
        assert len(d["packets"]) == 2
        assert d["packets"][0]["protocol"] == "icmp"
