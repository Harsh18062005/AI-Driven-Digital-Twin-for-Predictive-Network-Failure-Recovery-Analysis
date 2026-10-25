"""Unit tests for NetworkX graph construction and topology queries (topology.py).

Tests node/edge attributes, branch listing, link retrieval, error handling,
and graph summary generation using both real inventory and small synthetic graphs.
"""

from __future__ import annotations

import networkx as nx
import pytest

from inventory_loader import load_inventory
from topology import (
    build_graph,
    get_device_details,
    get_link_details,
    get_link_by_id,
    list_devices_by_branch,
    get_node_and_edge_counts,
    device_exists,
    link_exists,
    validate_graph,
    get_topology_summary,
    DeviceNotFoundError,
    LinkNotFoundError,
    TopologyError,
)


@pytest.fixture
def enterprise_graph() -> nx.Graph:
    """Fixture providing the built enterprise topology graph."""
    inv = load_inventory()
    return build_graph(inv)


@pytest.fixture
def toy_graph() -> nx.Graph:
    """Small synthetic graph for isolated unit testing."""
    toy_inv = {
        "metadata": {"network_name": "Toy Net", "version": "1.0"},
        "devices": [
            {"device_id": "R1", "hostname": "R1", "device_type": "Router", "branch": "B1", "role": "GW", "status": "active"},
            {"device_id": "SW1", "hostname": "SW1", "device_type": "Switch", "branch": "B1", "role": "SW", "status": "active"},
            {"device_id": "PC1", "hostname": "PC1", "device_type": "PC", "branch": "B1", "role": "EndHost", "status": "active"},
        ],
        "links": [
            {"link_id": "L1", "source_device": "R1", "source_interface": "G0/0", "target_device": "SW1", "target_interface": "G0/1", "link_type": "Trunk", "bandwidth_mbps": 1000, "status": "up"},
            {"link_id": "L2", "source_device": "SW1", "source_interface": "F0/1", "target_device": "PC1", "target_interface": "F0", "link_type": "Access", "bandwidth_mbps": 100, "status": "up"},
        ],
    }
    return build_graph(toy_inv)


def test_build_enterprise_graph_counts(enterprise_graph: nx.Graph):
    """Verify exact node and edge counts on the enterprise network graph."""
    nodes, edges = get_node_and_edge_counts(enterprise_graph)
    assert nodes == 22
    assert edges == 24
    assert nx.is_connected(enterprise_graph) is True


def test_device_attributes_preserved(enterprise_graph: nx.Graph):
    """Verify node attributes are stored accurately."""
    r1_data = get_device_details(enterprise_graph, "HQ-R1")
    assert r1_data["device_type"] == "Router"
    assert r1_data["branch"] == "Headquarters"
    assert r1_data["role"] == "Core Gateway"
    assert r1_data["management_ip"] == "10.10.10.1"
    assert 10 in r1_data["vlans"]
    assert 20 in r1_data["vlans"]
    assert 30 in r1_data["vlans"]


def test_link_attributes_preserved(enterprise_graph: nx.Graph):
    """Verify edge attributes are stored accurately."""
    link_data = get_link_details(enterprise_graph, "HQ-R1", "HQ-SW1")
    assert link_data["link_id"] == "LINK-HQ-SW1"
    assert link_data["link_type"] == "Trunk"
    assert link_data["bandwidth_mbps"] == 1000


def test_get_link_by_id(enterprise_graph: nx.Graph):
    """Verify finding an edge by its link_id."""
    u, v, data = get_link_by_id(enterprise_graph, "WAN-HQ-BR1")
    assert {u, v} == {"HQ-R1", "BR1-R1"}
    assert data["link_type"] == "WAN"
    assert data["subnet"] == "172.16.1.0/30"


def test_get_link_by_id_not_found(enterprise_graph: nx.Graph):
    """Verify exception when querying a non-existent link_id."""
    with pytest.raises(LinkNotFoundError):
        get_link_by_id(enterprise_graph, "LINK-NON-EXISTENT")


def test_device_exists(enterprise_graph: nx.Graph):
    """Verify device existence checks."""
    assert device_exists(enterprise_graph, "HQ-R1") is True
    assert device_exists(enterprise_graph, "UNKNOWN-DEVICE-XYZ") is False


def test_link_exists(enterprise_graph: nx.Graph):
    """Verify link existence checks."""
    assert link_exists(enterprise_graph, "HQ-R1", "HQ-SW1") is True
    assert link_exists(enterprise_graph, "HQ-SW1", "HQ-R1") is True  # Undirected
    assert link_exists(enterprise_graph, "HQ-PC1", "BR4-PC2") is False


def test_device_not_found_error(enterprise_graph: nx.Graph):
    """Verify querying non-existent device raises DeviceNotFoundError."""
    with pytest.raises(DeviceNotFoundError):
        get_device_details(enterprise_graph, "GHOST-NODE")


def test_link_not_found_error(enterprise_graph: nx.Graph):
    """Verify querying non-existent link raises LinkNotFoundError."""
    with pytest.raises(LinkNotFoundError):
        get_link_details(enterprise_graph, "HQ-PC1", "BR1-PC1")


def test_list_devices_by_branch(enterprise_graph: nx.Graph):
    """Verify grouping of devices by branch."""
    branches = list_devices_by_branch(enterprise_graph)
    assert len(branches) == 5
    assert len(branches["Headquarters"]) == 6
    assert len(branches["Branch 1 (North)"]) == 4

    # Test single branch filter
    filtered = list_devices_by_branch(enterprise_graph, branch_name="Branch 2 (South)")
    assert len(filtered) == 1
    assert "BR2-R1" in filtered["Branch 2 (South)"]


def test_validate_graph_empty_raises():
    """Verify that an empty graph fails validation."""
    empty_g = nx.Graph()
    with pytest.raises(TopologyError, match="zero nodes"):
        validate_graph(empty_g)


def test_toy_graph_summary(toy_graph: nx.Graph):
    """Verify topology summary on small test graph."""
    summary = get_topology_summary(toy_graph)
    assert summary["node_count"] == 3
    assert summary["edge_count"] == 2
    assert summary["is_connected"] is True
    assert summary["connected_components_count"] == 1
    assert summary["device_types"] == {"Router": 1, "Switch": 1, "PC": 1}
