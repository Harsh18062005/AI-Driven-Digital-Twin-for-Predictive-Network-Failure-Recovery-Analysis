"""Unit tests for PrescriptiveRecoveryEngine."""

from __future__ import annotations

import pytest
from ml.recovery_engine import PrescriptiveRecoveryEngine


@pytest.fixture
def engine() -> PrescriptiveRecoveryEngine:
    return PrescriptiveRecoveryEngine()


def test_recommend_link_recovery_redundant_wan(engine: PrescriptiveRecoveryEngine):
    """Redundant WAN link must find alternate path and yield 100% traffic restoration."""
    rec = engine.recommend_link_recovery("WAN-HQ-BR1")

    assert rec["target_id"] == "WAN-HQ-BR1"
    assert rec["recovery_strategy"] == "DYNAMIC_REROUTE"
    assert rec["traffic_restored_pct"] == 100.0
    assert rec["optimal_alternate_path"] is not None

    path = rec["optimal_alternate_path"]["path"]
    assert path[0] == "HQ-R1"
    assert path[-1] == "BR1-R1"
    assert len(path) >= 3  # Routed through intermediary branch router (e.g. BR2-R1)

    assert len(rec["cisco_ios_commands"]) > 5
    assert any("ip ospf cost 65535" in cmd for cmd in rec["cisco_ios_commands"])


def test_recommend_link_recovery_bridge_access_link(engine: PrescriptiveRecoveryEngine):
    """Bridge link to leaf host has no alternate path and requires manual dispatch."""
    rec = engine.recommend_link_recovery("LINK-BR1-PC1")

    assert rec["target_id"] == "LINK-BR1-PC1"
    assert rec["recovery_strategy"] == "MANUAL_DISPATCH"
    assert rec["traffic_restored_pct"] == 0.0
    assert rec["optimal_alternate_path"] is None
    assert rec["priority"] == "P1-CRITICAL"


def test_recommend_device_recovery_router(engine: PrescriptiveRecoveryEngine):
    """Core router recovery prescription must identify severed links and partition state."""
    rec = engine.recommend_device_recovery("HQ-R1")

    assert rec["target_id"] == "HQ-R1"
    assert rec["device_type"] == "Router"
    assert rec["priority"] == "P1-CRITICAL"
    assert rec["is_partitioned"]
    assert rec["severed_links_count"] == 5
    assert len(rec["cisco_ios_commands"]) > 0


def test_recommend_device_recovery_server(engine: PrescriptiveRecoveryEngine):
    """Server recovery prescription must recommend secondary helper-address migration."""
    rec = engine.recommend_device_recovery("HQ-SRV1")

    assert rec["target_id"] == "HQ-SRV1"
    assert rec["device_type"] == "Server"
    assert rec["recovery_strategy"] == "SERVICE_FAILOVER_TO_SECONDARY"
    assert any("ip helper-address" in cmd for cmd in rec["cisco_ios_commands"])
