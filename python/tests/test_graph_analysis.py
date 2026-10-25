"""Unit tests for graph analysis and failure simulation algorithms (graph_analysis.py).

Verifies connectivity checking, shortest-path discovery, alternative path calculation,
connected components, and non-destructive failure simulations (node & link cuts).
"""

from __future__ import annotations

import networkx as nx
import pytest

from inventory_loader import load_inventory
from topology import build_graph, DeviceNotFoundError, LinkNotFoundError
from graph_analysis import (
    check_connectivity,
    find_path,
    find_all_paths,
    find_alternative_paths,
    get_connected_components,
    simulate_device_failure,
    simulate_link_failure,
    get_branch_inventory,
    get_graph_summary,
)


@pytest.fixture
def enterprise_graph() -> nx.Graph:
    """Fixture providing the baseline enterprise topology graph."""
    inv = load_inventory()
    return build_graph(inv)


@pytest.fixture
def triangle_with_stub_graph() -> nx.Graph:
    r"""Explicitly labeled small test fixture: Triangle (A-B-C) with a stub host (H1-A).

    A --- B
     \   /
       C
       |
      H1
    """
    g = nx.Graph()
    g.add_node("A", device_type="Router", branch="B1", role="Core")
    g.add_node("B", device_type="Router", branch="B1", role="Core")
    g.add_node("C", device_type="Router", branch="B1", role="Core")
    g.add_node("H1", device_type="PC", branch="B1", role="Host")

    g.add_edge("A", "B", link_id="L-AB", link_type="WAN", bandwidth_mbps=1000)
    g.add_edge("B", "C", link_id="L-BC", link_type="WAN", bandwidth_mbps=1000)
    g.add_edge("A", "C", link_id="L-AC", link_type="WAN", bandwidth_mbps=1000)
    g.add_edge("C", "H1", link_id="L-CH1", link_type="Access", bandwidth_mbps=100)
    return g


def test_baseline_graph_connectivity(enterprise_graph: nx.Graph):
    """Verify that all end PCs can topologically reach headquarters servers."""
    assert check_connectivity(enterprise_graph, "BR1-PC1", "HQ-SRV1") is True
    assert check_connectivity(enterprise_graph, "BR2-PC1", "HQ-SRV2") is True
    assert check_connectivity(enterprise_graph, "BR3-PC1", "HQ-SRV1") is True
    assert check_connectivity(enterprise_graph, "BR4-PC1", "HQ-SRV2") is True


def test_connectivity_unknown_device_raises(enterprise_graph: nx.Graph):
    """Verify exception when checking connectivity with non-existent device ID."""
    with pytest.raises(DeviceNotFoundError):
        check_connectivity(enterprise_graph, "HQ-PC1", "UNKNOWN-HOST")


def test_find_path_returns_valid_sequence(enterprise_graph: nx.Graph):
    """Verify that find_path returns a valid consecutive chain of connected nodes."""
    path = find_path(enterprise_graph, "BR1-PC1", "HQ-SRV1")
    assert path is not None
    assert path[0] == "BR1-PC1"
    assert path[-1] == "HQ-SRV1"

    # Verify each consecutive pair is an edge in the graph
    for u, v in zip(path[:-1], path[1:]):
        assert enterprise_graph.has_edge(u, v)


def test_find_path_same_source_and_target(enterprise_graph: nx.Graph):
    """Verify path from a device to itself returns a single-item list."""
    path = find_path(enterprise_graph, "HQ-PC1", "HQ-PC1")
    assert path == ["HQ-PC1"]


def test_find_all_paths(triangle_with_stub_graph: nx.Graph):
    """Verify finding multiple loop-free paths in a redundant graph."""
    paths = find_all_paths(triangle_with_stub_graph, "A", "B")
    assert len(paths) == 2  # A-B and A-C-B
    assert ["A", "B"] in paths
    assert ["A", "C", "B"] in paths


def test_find_alternative_paths_excluding_link(enterprise_graph: nx.Graph):
    """Verify that excluding primary WAN link WAN-HQ-BR1 finds alternative paths through BR2."""
    alt_paths = find_alternative_paths(
        enterprise_graph,
        source_id="BR1-R1",
        target_id="HQ-R1",
        excluded_link=("HQ-R1", "BR1-R1"),
    )
    assert len(alt_paths) >= 1
    # Verify the direct edge is NOT present in any returned alternative path
    for p in alt_paths:
        assert not ("HQ-R1" in p and "BR1-R1" in p and abs(p.index("HQ-R1") - p.index("BR1-R1")) == 1)


def test_find_alternative_paths_excluding_device(enterprise_graph: nx.Graph):
    """Verify excluding intermediate router forces traffic across alternate route."""
    # When BR2-R1 is removed, path from BR1 to BR3 must traverse HQ
    alt_paths = find_alternative_paths(
        enterprise_graph,
        source_id="BR1-R1",
        target_id="BR3-R1",
        excluded_device="BR2-R1",
    )
    assert len(alt_paths) >= 1
    for p in alt_paths:
        assert "BR2-R1" not in p


def test_connected_components(enterprise_graph: nx.Graph):
    """Verify that the baseline enterprise topology has exactly 1 connected component."""
    comps = get_connected_components(enterprise_graph)
    assert len(comps) == 1
    assert len(comps[0]) == 22


def test_simulate_device_failure_preserves_baseline(enterprise_graph: nx.Graph):
    """Verify that failure simulations NEVER mutate the baseline graph."""
    initial_nodes = enterprise_graph.number_of_nodes()
    initial_edges = enterprise_graph.number_of_edges()

    # Run failure on Core Router HQ-R1
    sim_res = simulate_device_failure(enterprise_graph, "HQ-R1")

    # Baseline graph MUST remain 100% intact
    assert enterprise_graph.number_of_nodes() == initial_nodes
    assert enterprise_graph.number_of_edges() == initial_edges
    assert enterprise_graph.has_node("HQ-R1") is True

    # Simulation report assertions
    assert sim_res["failed_device_id"] == "HQ-R1"
    assert sim_res["severed_links_count"] == 5
    assert sim_res["post_failure_components_count"] == 2
    assert sim_res["is_partitioned"] is True


def test_simulate_leaf_device_failure(enterprise_graph: nx.Graph):
    """Verify that failing an end PC does not partition the rest of the network."""
    sim_res = simulate_device_failure(enterprise_graph, "HQ-PC1")
    assert sim_res["severed_links_count"] == 1
    assert sim_res["post_failure_components_count"] == 1
    assert sim_res["is_partitioned"] is False


def test_simulate_link_failure_redundant_wan(enterprise_graph: nx.Graph):
    """Verify link failure simulation on redundant WAN link WAN-HQ-BR1."""
    initial_edges = enterprise_graph.number_of_edges()

    sim_res = simulate_link_failure(enterprise_graph, link_id="WAN-HQ-BR1")

    # Baseline graph check
    assert enterprise_graph.number_of_edges() == initial_edges

    # Rerouting assertions
    assert sim_res["alternate_path_found"] is True
    assert sim_res["alternate_path"] == ["HQ-R1", "BR2-R1", "BR1-R1"]
    assert sim_res["is_bridge"] is False
    assert sim_res["post_failure_components_count"] == 1


def test_simulate_link_failure_bridge_access_link(enterprise_graph: nx.Graph):
    """Verify that failing a leaf access link partitions the leaf device from the network."""
    sim_res = simulate_link_failure(enterprise_graph, link_id="LINK-HQ-PC1")
    assert sim_res["alternate_path_found"] is False
    assert sim_res["alternate_path"] is None
    assert sim_res["is_bridge"] is True
    assert sim_res["post_failure_components_count"] == 2


def test_get_branch_inventory(enterprise_graph: nx.Graph):
    """Verify retrieving branch-scoped inventory and uplink connections."""
    b1_inv = get_branch_inventory(enterprise_graph, "Branch 1 (North)")
    assert b1_inv["device_count"] == 4
    assert b1_inv["internal_links_count"] == 3  # R1-SW1, SW1-PC1, SW1-PC2
    assert b1_inv["external_links_count"] == 2  # WAN to HQ, WAN to BR2


def test_get_graph_summary(enterprise_graph: nx.Graph):
    """Verify baseline graph summary dictionary."""
    summary = get_graph_summary(enterprise_graph)
    assert summary["total_nodes"] == 22
    assert summary["total_edges"] == 24
    assert summary["is_connected"] is True
    assert summary["components_count"] == 1
    assert len(summary["branches_represented"]) == 5
