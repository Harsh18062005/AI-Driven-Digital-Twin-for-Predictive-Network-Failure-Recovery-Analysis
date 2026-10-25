"""Unit tests for NetworkDigitalTwin unified facade."""

from __future__ import annotations

import pytest
from ml.digital_twin import NetworkDigitalTwin


@pytest.fixture
def twin() -> NetworkDigitalTwin:
    return NetworkDigitalTwin()


def test_topology_overview(twin: NetworkDigitalTwin):
    """Verify overview reflects verified 5-branch network."""
    overview = twin.get_topology_overview()
    assert overview["total_nodes"] == 22
    assert overview["total_edges"] == 24
    assert overview["is_connected"]
    assert len(overview["branches"]) == 5


def test_enterprise_health_matrix(twin: NetworkDigitalTwin):
    """Verify enterprise health matrix contains predictions for all elements."""
    matrix = twin.get_enterprise_health_matrix()
    assert "overall_health_score" in matrix
    assert len(matrix["links"]) == 24
    assert len(matrix["devices"]) == 22


def test_predict_and_mitigate_link(twin: NetworkDigitalTwin):
    """Verify unified prediction and mitigation on a link."""
    report = twin.predict_and_mitigate("WAN-HQ-BR1")
    assert report["target_type"] == "LINK"
    assert "prediction" in report
    assert "recovery_plan" in report
    assert "summary" in report


def test_predict_and_mitigate_device(twin: NetworkDigitalTwin):
    """Verify unified prediction and mitigation on a device."""
    report = twin.predict_and_mitigate("HQ-R1")
    assert report["target_type"] == "DEVICE"
    assert "prediction" in report
    assert "recovery_plan" in report


def test_predict_and_mitigate_invalid_target_raises(twin: NetworkDigitalTwin):
    """Unknown target ID must raise KeyError."""
    with pytest.raises(KeyError):
        twin.predict_and_mitigate("UNKNOWN_NODE_999")


def test_simulate_what_if_scenario_preserves_graph(twin: NetworkDigitalTwin):
    """What-if simulations must never mutate baseline graph."""
    node_count_before = twin.graph.number_of_nodes()
    edge_count_before = twin.graph.number_of_edges()

    sim = twin.simulate_what_if_scenario("WAN-HQ-BR1")
    assert sim["scenario_type"] == "LINK_FAILURE"

    sim_node = twin.simulate_what_if_scenario("HQ-R1")
    assert sim_node["scenario_type"] == "DEVICE_FAILURE"

    # Baseline graph immutability check
    assert twin.graph.number_of_nodes() == node_count_before
    assert twin.graph.number_of_edges() == edge_count_before


def test_export_dashboard_snapshot(twin: NetworkDigitalTwin):
    """Verify dashboard snapshot contains all keys needed by Streamlit UI."""
    snap = twin.export_dashboard_snapshot()
    for key in ("network_name", "total_devices", "total_links", "overall_health_score", "kpis", "devices", "links"):
        assert key in snap
