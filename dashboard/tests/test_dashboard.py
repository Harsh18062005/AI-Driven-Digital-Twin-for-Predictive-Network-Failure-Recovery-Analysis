"""Automated tests for Dashboard components and visualizer functions."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root and python/ to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
PYTHON_DIR = PROJECT_ROOT / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

import networkx as nx
import plotly.graph_objects as go
import pytest

from inventory_loader import load_inventory
from topology import build_graph
from dashboard.app import (
    TOPOLOGY_COORDINATES,
    BRANCH_COLORS,
    DEVICE_SYMBOLS,
    render_network_figure,
)


@pytest.fixture
def graph() -> nx.Graph:
    inv = load_inventory(PYTHON_DIR / "network.json")
    return build_graph(inv)


def test_topology_coordinates_cover_all_22_devices(graph: nx.Graph):
    """Verify that every device in the verified graph has 2D visual layout coordinates."""
    for node in graph.nodes():
        assert node in TOPOLOGY_COORDINATES, f"Missing coordinates for {node}"
        x, y = TOPOLOGY_COORDINATES[node]
        assert isinstance(x, (int, float))
        assert isinstance(y, (int, float))


def test_render_network_figure_baseline(graph: nx.Graph):
    """Verify that render_network_figure generates a valid Plotly Figure."""
    fig = render_network_figure(graph, title="Baseline Test")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0  # Contains edge lines and node scatter markers


def test_render_network_figure_with_failed_link_and_alternate_path(graph: nx.Graph):
    """Verify rendering with a severed link and a green highlighted alternate path."""
    fig = render_network_figure(
        graph,
        failed_link_id="WAN-HQ-BR1",
        highlight_path=["HQ-R1", "BR2-R1", "BR1-R1"],
        title="Failure Test",
    )
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0


def test_render_network_figure_with_failed_node(graph: nx.Graph):
    """Verify rendering with a failed node marker."""
    fig = render_network_figure(
        graph,
        failed_node="HQ-R1",
        title="Node Crash Test",
    )
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0


def test_branch_colors_and_symbols_cover_all_types():
    """Verify that branch color mapping and device symbol dictionary are complete."""
    assert len(BRANCH_COLORS) == 5
    for dtype in ("Router", "Switch", "Server", "PC"):
        assert dtype in DEVICE_SYMBOLS


def test_render_network_figure_light_theme_layout(graph: nx.Graph):
    """Verify that the Plotly figure uses light neutral background styling."""
    fig = render_network_figure(graph, title="Theme Test")
    assert fig.layout.paper_bgcolor == "#ffffff"
    assert fig.layout.plot_bgcolor == "#f8fafc"
    assert fig.layout.title.font.color == "#0f172a"
