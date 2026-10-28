"""Enterprise Network Digital Twin & What-If Failure Simulator.

Interactive Streamlit web application providing topological visualization,
non-destructive what-if failure simulations, end-to-end path reachability inspection,
and predictive machine learning risk analytics with prescriptive recovery playbooks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import pandas as pd
import streamlit as st

# Direct integration with upstream python/ topology engine
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON_DIR = PROJECT_ROOT / "python"
ML_DIR = PROJECT_ROOT / "ml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from inventory_loader import load_inventory
from topology import (
    build_graph,
    get_device_details,
    get_link_by_id,
    get_link_details,
    get_node_and_edge_counts,
    get_topology_summary,
    list_devices_by_branch,
)
from graph_analysis import (
    check_connectivity,
    find_all_paths,
    find_alternative_paths,
    find_path,
    get_branch_inventory,
    get_connected_components,
    get_graph_summary,
    simulate_device_failure,
    simulate_link_failure,
)

# Optional ML module imports
try:
    from ml.digital_twin import NetworkDigitalTwin
    HAS_ML_MODULE = True
except Exception:
    HAS_ML_MODULE = False

# ==============================================================================
# STREAMLIT PAGE CONFIGURATION & THEME STYLING
# ==============================================================================
st.set_page_config(
    page_title="Network Digital Twin Simulator",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Global Neutral Light Theme Overrides */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
    }

    /* Metric Cards - Clean Slate Container */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 18px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0f172a;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.88rem;
        font-weight: 600;
        color: #475569;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 0.82rem;
        color: #64748b;
    }

    /* Professional Button Styling - Clean Neutral / Blue */
    div.stButton > button[kind="primary"] {
        background-color: #2563eb;
        color: #ffffff;
        border: 1px solid #1d4ed8;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.92rem;
        padding: 0.45rem 1.1rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        transition: all 0.15s ease-in-out;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #1d4ed8;
        border-color: #1e40af;
        color: #ffffff;
    }
    div.stButton > button[kind="secondary"], .stButton > button:not([kind="primary"]) {
        background-color: #ffffff;
        color: #334155;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.88rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        transition: all 0.15s ease-in-out;
    }
    div.stButton > button[kind="secondary"]:hover, .stButton > button:not([kind="primary"]):hover {
        background-color: #f1f5f9;
        border-color: #94a3b8;
        color: #0f172a;
    }

    /* Clean Card Container */
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 18px;
        color: #0f172a;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
    }

    /* Refined Severity Badges (Pastel Chips) */
    .badge-critical {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #fca5a5;
        padding: 2px 8px;
        border-radius: 5px;
        font-weight: 600;
        font-size: 0.78rem;
        display: inline-block;
    }
    .badge-warning {
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fcd34d;
        padding: 2px 8px;
        border-radius: 5px;
        font-weight: 600;
        font-size: 0.78rem;
        display: inline-block;
    }
    .badge-healthy {
        background-color: #dcfce7;
        color: #166534;
        border: 1px solid #86efac;
        padding: 2px 8px;
        border-radius: 5px;
        font-weight: 600;
        font-size: 0.78rem;
        display: inline-block;
    }

    /* Clean Hop-by-Hop Breadcrumb */
    .breadcrumb-step {
        display: inline-block;
        background: #ffffff;
        border: 1px solid #cbd5e1;
        padding: 5px 12px;
        border-radius: 6px;
        margin: 3px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.88rem;
        color: #1e293b;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# CONSTANTS & TOPOLOGY COORDINATE LAYOUT
# ==============================================================================
BRANCH_COLORS: Dict[str, str] = {
    "Headquarters": "#1d4ed8",         # Refined Royal Navy
    "Branch 1 (North)": "#059669",     # Refined Forest Green
    "Branch 2 (South)": "#d97706",     # Refined Warm Amber
    "Branch 3 (East)": "#7c3aed",      # Refined Violet/Purple
    "Branch 4 (West)": "#dc2626",      # Refined Crimson Red
}

DEVICE_SYMBOLS: Dict[str, str] = {
    "Router": "diamond",
    "Switch": "square",
    "Server": "triangle-up",
    "PC": "circle",
}

# High-fidelity 2D coordinates matching Packet Tracer enterprise physical geometry
TOPOLOGY_COORDINATES: Dict[str, Tuple[float, float]] = {
    # Headquarters (Hub & Data Center) - Center
    "HQ-R1": (0.0, 0.0),
    "HQ-SW1": (0.0, -0.9),
    "HQ-SRV1": (-0.6, -1.8),
    "HQ-SRV2": (0.6, -1.8),
    "HQ-PC1": (-1.3, -1.8),
    "HQ-PC2": (1.3, -1.8),
    # Branch 1 (North Office) - Top
    "BR1-R1": (0.0, 3.2),
    "BR1-SW1": (0.0, 4.4),
    "BR1-PC1": (-0.8, 5.3),
    "BR1-PC2": (0.8, 5.3),
    # Branch 2 (South R&D) - Bottom
    "BR2-R1": (0.0, -3.4),
    "BR2-SW1": (0.0, -4.6),
    "BR2-PC1": (-0.8, -5.5),
    "BR2-PC2": (0.8, -5.5),
    # Branch 3 (East Sales) - Right
    "BR3-R1": (3.4, 0.0),
    "BR3-SW1": (4.6, 0.0),
    "BR3-PC1": (5.5, 0.8),
    "BR3-PC2": (5.5, -0.8),
    # Branch 4 (West Logistics) - Left
    "BR4-R1": (-3.4, 0.0),
    "BR4-SW1": (-4.6, 0.0),
    "BR4-PC1": (-5.5, 0.8),
    "BR4-PC2": (-5.5, -0.8),
}

SERIAL_LINKS: Set[str] = {"WAN-HQ-BR3", "WAN-HQ-BR4", "WAN-BR2-BR3"}


# ==============================================================================
# DATA LOADING & GRAPH ENGINE CACHING
# ==============================================================================
@st.cache_resource(show_spinner="Loading verified enterprise topology graph...")
def get_base_network() -> Tuple[Dict[str, Any], nx.Graph]:
    """Load schema-validated network.json and build baseline NetworkX graph."""
    inv = load_inventory(PYTHON_DIR / "network.json")
    G = build_graph(inv)
    return inv, G


@st.cache_data(show_spinner="Loading machine learning risk predictions...")
def get_ml_predictions() -> Optional[Dict[str, Any]]:
    """Ingest ml/predictions.json if generated by ML pipeline."""
    pred_path = ML_DIR / "predictions.json"
    if pred_path.exists():
        try:
            with open(pred_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


inventory, G_base = get_base_network()
ml_predictions = get_ml_predictions()


# ==============================================================================
# PLOTLY TOPOLOGY GRAPH VISUALIZER BUILDER
# ==============================================================================
def render_network_figure(
    graph: nx.Graph,
    failed_node: Optional[str] = None,
    failed_link_id: Optional[str] = None,
    highlight_path: Optional[List[str]] = None,
    title: str = "Enterprise 5-Branch Network Topology",
    focus_branch: Optional[str] = None,
) -> Any:
    """Construct an interactive Plotly graph visualizing the digital twin topology.

    Args:
        graph: The NetworkX graph.
        failed_node: Optional device ID to display with failure marker.
        failed_link_id: Optional link ID to display with severed styling.
        highlight_path: Optional list of device IDs along active/alternate route.
        title: Chart title.
        focus_branch: Optional branch name filter.
    """
    import plotly.graph_objects as go

    # Identify edges on highlight path
    highlight_edges: Set[Tuple[str, str]] = set()
    if highlight_path and len(highlight_path) > 1:
        for i in range(len(highlight_path) - 1):
            u, v = highlight_path[i], highlight_path[i + 1]
            highlight_edges.add((u, v))
            highlight_edges.add((v, u))

    edge_traces = []

    # Iterate over all edges in the graph
    for u, v, data in graph.edges(data=True):
        link_id = data.get("link_id", "")
        link_type = data.get("link_type", "Access")
        bw = data.get("bandwidth_mbps", 100)
        is_wan = link_type == "WAN"

        x0, y0 = TOPOLOGY_COORDINATES.get(u, (0, 0))
        x1, y1 = TOPOLOGY_COORDINATES.get(v, (0, 0))

        is_failed = (failed_link_id and link_id == failed_link_id) or (
            failed_node and (u == failed_node or v == failed_node)
        )
        is_highlighted = (u, v) in highlight_edges

        # Determine styling
        if is_failed:
            color = "#dc2626"  # Professional Crimson Red
            width = 4.0
            dash = "dash"
            hover_status = "<b style='color:#dc2626;'>[FAILED / SEVERED LINK]</b>"
        elif is_highlighted:
            color = "#16a34a"  # Clear Emerald Green
            width = 5.0
            dash = "solid"
            hover_status = "<b style='color:#16a34a;'>[ACTIVE / REROUTED PATH]</b>"
        elif is_wan:
            color = "#d97706" if link_id in SERIAL_LINKS else "#2563eb"
            width = 3.2
            dash = "solid"
            hover_status = "WAN Redundant Route"
        elif link_type == "Trunk":
            color = "#475569"
            width = 2.4
            dash = "solid"
            hover_status = "Distribution Trunk (802.1Q)"
        else:
            color = "#94a3b8"
            width = 1.4
            dash = "dot"
            hover_status = "VLAN Access Host Link"

        hover_text = (
            f"<b>Link:</b> {link_id}<br>"
            f"<b>Endpoints:</b> {u} <--> {v}<br>"
            f"<b>Type:</b> {link_type} ({data.get('media', 'Copper')})<br>"
            f"<b>Bandwidth:</b> {bw} Mbps<br>"
            f"<b>Status:</b> {hover_status}"
        )

        trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode="lines",
            line=dict(width=width, color=color, dash=dash),
            hoverinfo="text",
            hovertext=hover_text,
            showlegend=False,
        )
        edge_traces.append(trace)

    # Build Node Traces grouped by device type for clean legend entries
    node_types = ["Router", "Switch", "Server", "PC"]
    node_traces = []

    for dtype in node_types:
        x_list, y_list, colors, texts, symbols, sizes = [], [], [], [], [], []

        for node, data in graph.nodes(data=True):
            if data.get("device_type") != dtype:
                continue

            branch = data.get("branch", "Headquarters")
            if focus_branch and focus_branch != "All Branches" and branch != focus_branch:
                continue

            x, y = TOPOLOGY_COORDINATES.get(node, (0, 0))
            is_node_failed = (failed_node and node == failed_node)

            if is_node_failed:
                node_color = "#dc2626"
                node_size = 28
                symbol = "x"
                status_label = "<b style='color:#dc2626;'>[SIMULATED FAILED]</b>"
            else:
                node_color = BRANCH_COLORS.get(branch, "#1d4ed8")
                node_size = 26 if dtype == "Router" else (22 if dtype == "Switch" else 18)
                symbol = DEVICE_SYMBOLS.get(dtype, "circle")
                status_label = "<b style='color:#16a34a;'>ACTIVE</b>"

            vlans_str = ", ".join(str(v) for v in data.get("vlans", [])) or "None"
            mgmt_ip = data.get("management_ip", "DHCP")

            hover_text = (
                f"<b>{node}</b> ({data.get('hostname', node)})<br>"
                f"<b>Type:</b> {dtype} | <b>Model:</b> {data.get('model', 'Cisco')}<br>"
                f"<b>Branch:</b> {branch}<br>"
                f"<b>Role:</b> {data.get('role', 'Node')}<br>"
                f"<b>Mgmt IP:</b> {mgmt_ip}<br>"
                f"<b>Active VLANs:</b> {vlans_str}<br>"
                f"<b>Interfaces:</b> {len(data.get('interfaces', []))}<br>"
                f"<b>Status:</b> {status_label}"
            )

            x_list.append(x)
            y_list.append(y)
            colors.append(node_color)
            texts.append(hover_text)
            symbols.append(symbol)
            sizes.append(node_size)

        if x_list:
            trace = go.Scatter(
                x=x_list,
                y=y_list,
                mode="markers+text",
                name=f"{dtype}s",
                text=[n for n, d in graph.nodes(data=True) if d.get("device_type") == dtype and (not focus_branch or focus_branch == "All Branches" or d.get("branch") == focus_branch)],
                textposition="top center",
                textfont=dict(size=10, color="#1e293b"),
                marker=dict(
                    symbol=symbols,
                    size=sizes,
                    color=colors,
                    line=dict(width=1.5, color="#ffffff"),
                ),
                hoverinfo="text",
                hovertext=texts,
            )
            node_traces.append(trace)

    fig = go.Figure(data=edge_traces + node_traces)

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#0f172a")),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#f8fafc",
        hovermode="closest",
        margin=dict(b=20, l=20, r=20, t=50),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#334155"),
        ),
        height=580,
    )
    return fig


# ==============================================================================
# HEADER & LIVE ENTERPRISE KPI CARDS
# ==============================================================================
summary = get_topology_summary(G_base)
branch_map = list_devices_by_branch(G_base)
all_devices = sorted(list(G_base.nodes()))
all_links = sorted([data["link_id"] for _, _, data in G_base.edges(data=True) if "link_id" in data])

st.title("AI-Driven Network Digital Twin & What-If Simulator")
st.markdown(
    "**Enterprise Five-Branch Topology:** Headquarters (Hub & Data Center) + 4 Regional Branches with redundant OSPF WAN rings."
)

# 4 Executive KPI Cards
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    st.metric(label="Total Network Devices", value=f"{summary['node_count']} Nodes", delta="5 Routers | 5 Switches")

with kpi_col2:
    st.metric(label="Total Network Links", value=f"{summary['edge_count']} Links", delta="7 WAN | 5 Trunk | 12 Access")

with kpi_col3:
    st.metric(label="Enterprise Branches", value="5 Branches", delta="Backbone OSPF Area 0")

with kpi_col4:
    if summary["is_connected"]:
        st.metric(label="Digital Twin Health", value="100% HEALTHY", delta="Fully Connected")
    else:
        st.metric(label="Digital Twin Health", value="PARTITIONED", delta=f"{summary['connected_components_count']} Islands")

st.divider()

# ==============================================================================
# TAB 1: INTERACTIVE NETWORK TOPOLOGY VISUALIZER
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "Interactive Topology Visualizer",
    "What-If Failure Simulator & Recovery",
    "End-to-End Path & Reachability Inspector",
    "ML Risk & Health Analytics",
])

with tab1:
    st.subheader("Enterprise 5-Branch Digital Twin Topology")
    
    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        branch_filter = st.selectbox(
            "Filter Topology by Branch:",
            options=["All Branches", "Headquarters", "Branch 1 (North)", "Branch 2 (South)", "Branch 3 (East)", "Branch 4 (West)"],
            index=0,
        )
    with top_col2:
        st.caption("Branch Legend Colors:")
        st.markdown(
            """
            <span style='color:#1d4ed8;'>■ HQ</span> | 
            <span style='color:#059669;'>■ BR1 (North)</span> | 
            <span style='color:#d97706;'>■ BR2 (South)</span> | 
            <span style='color:#7c3aed;'>■ BR3 (East)</span> | 
            <span style='color:#dc2626;'>■ BR4 (West)</span>
            """,
            unsafe_allow_html=True,
        )

    fig_topo = render_network_figure(G_base, focus_branch=branch_filter)
    st.plotly_chart(fig_topo, use_container_width=True)


# ==============================================================================
# TAB 2: WHAT-IF FAILURE SIMULATOR & RECOVERY ANALYSIS
# ==============================================================================
with tab2:
    st.subheader("Non-Destructive What-If Failure Simulator")
    st.markdown(
        "Simulate link disruptions or device crashes on an **isolated in-memory twin copy**. "
        "The verified baseline topology `G` is strictly preserved."
    )

    sim_col1, sim_col2 = st.columns([1, 2])

    with sim_col1:
        sim_mode = st.radio(
            "Select Failure Simulation Mode:",
            options=["Link Failure Simulation", "Device Failure Simulation"],
            horizontal=True,
        )

        if sim_mode == "Link Failure Simulation":
            # Highlight WAN links first
            target_link = st.selectbox(
                "Choose Link to Sever:",
                options=all_links,
                index=all_links.index("WAN-HQ-BR1") if "WAN-HQ-BR1" in all_links else 0,
                help="Test primary hub-spoke WAN, redundant inter-branch rings, or local distribution trunks.",
            )
            trigger_sim = st.button("Simulate Link Failure", type="primary", use_container_width=True)
        else:
            target_device = st.selectbox(
                "Choose Device to Crash:",
                options=all_devices,
                index=all_devices.index("HQ-R1") if "HQ-R1" in all_devices else 0,
                help="Test core gateway failure, branch router collapse, or access switch outage.",
            )
            trigger_sim = st.button("Simulate Device Failure", type="primary", use_container_width=True)

    with sim_col2:
        st.info(
            "**Digital Twin Immutability Contract:** Invocations of `simulate_link_failure` and `simulate_device_failure` "
            "perform isolated graph cloning without mutating baseline topology."
        )

    st.divider()

    # Session State for Failure Simulation Results
    if "sim_link_res" not in st.session_state:
        st.session_state.sim_link_res = None
    if "sim_dev_res" not in st.session_state:
        st.session_state.sim_dev_res = None

    if trigger_sim:
        if sim_mode == "Link Failure Simulation":
            st.session_state.sim_link_res = simulate_link_failure(G_base, link_id=target_link)
            st.session_state.sim_dev_res = None
        else:
            st.session_state.sim_dev_res = simulate_device_failure(G_base, failed_device_id=target_device)
            st.session_state.sim_link_res = None

    # Render Simulation Analysis
    if st.session_state.sim_link_res:
        res = st.session_state.sim_link_res
        u, v = res["endpoints"]
        link_id = res["failed_link_id"]
        alt_found = res["alternate_path_found"]
        alt_path = res["alternate_path"]

        # Status Banner
        if alt_found:
            st.success(
                f"**FAULT TOLERANCE VERIFIED:** Redundant WAN path discovered! Traffic between `{u}` and `{v}` reroutes successfully."
            )
        else:
            st.error(
                f"**NETWORK PARTITIONED:** Link `{link_id}` was a topological bridge! Partitioned into {res['post_failure_components_count']} disjoint components."
            )

        # Metric Cards
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Severed Endpoints", f"{u} <-> {v}")
        sc2.metric("Alternate Path Found?", "YES" if alt_found else "NO")
        sc3.metric("Alternate Hop Count", f"{res['alternate_path_hop_count']} hops" if alt_found else "N/A")
        sc4.metric("Post-Failure Islands", f"{res['post_failure_components_count']} Component(s)")

        # Side-by-Side Visual Comparison
        vis_col1, vis_col2 = st.columns(2)
        with vis_col1:
            st.markdown("#### Baseline Healthy Network")
            fig_healthy = render_network_figure(G_base, title=f"Normal Baseline (Link {link_id} Active)")
            st.plotly_chart(fig_healthy, use_container_width=True)

        with vis_col2:
            st.markdown("#### Degraded / Rerouted Network")
            fig_degraded = render_network_figure(
                G_base,
                failed_link_id=link_id,
                highlight_path=alt_path,
                title=f"Degraded State: {link_id} SEVERED (Rerouted in Green)",
            )
            st.plotly_chart(fig_degraded, use_container_width=True)

        # Prescriptive Self-Healing Playbook
        st.markdown("### Prescriptive Self-Healing Playbook")
        if alt_found:
            st.markdown(
                f"**Rerouted Traffic Path:** `{' -> '.join(alt_path)}`  \n"
                f"**Automated OSPF Convergence:** Cisco 2911 routers dynamically trigger Dijkstra SPF recalculation."
            )
            st.markdown("#### Cisco IOS Automated Remediation Snippet:")
            ios_code = (
                f"! --- Automated Failover Configuration on {u} ---\n"
                f"{u}# configure terminal\n"
                f"{u}(config)# interface {res['link_info'].get('source_interface', 'Gig0/1')}\n"
                f"{u}(config-if)# ip ospf cost 65535\n"
                f"{u}(config-if)# shutdown\n"
                f"{u}(config-if)# exit\n"
                f"{u}# clear ip ospf process\n"
                f"! Traffic will seamlessly divert to path: {' -> '.join(alt_path)}"
            )
            st.code(ios_code, language="cisco")
        else:
            st.warning("Immediate field technician dispatch required: physical cable, transceiver, or switch port failure.")

    elif st.session_state.sim_dev_res:
        res = st.session_state.sim_dev_res
        dev_id = res["failed_device_id"]
        dev_info = res["device_info"]

        if res["is_partitioned"]:
            st.error(
                f"**CRITICAL NETWORK PARTITION:** Device `{dev_id}` ({dev_info['device_type']}) was an articulation point! "
                f"Network fragmented into {res['post_failure_components_count']} disjoint islands."
            )
        else:
            st.warning(
                f"Device `{dev_id}` offline. Remaining {res['remaining_nodes_count']} nodes maintain reachability."
            )

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Failed Device", f"{dev_id} ({dev_info['device_type']})")
        sc2.metric("Severed Links Count", f"{res['severed_links_count']} Links")
        sc3.metric("Isolated Devices", f"{len(res['isolated_devices'])} Devices")
        sc4.metric("Post-Failure Components", f"{res['post_failure_components_count']} Islands")

        vis_col1, vis_col2 = st.columns(2)
        with vis_col1:
            st.markdown("#### Baseline Healthy Network")
            fig_healthy = render_network_figure(G_base, title=f"Baseline (Device {dev_id} Active)")
            st.plotly_chart(fig_healthy, use_container_width=True)

        with vis_col2:
            st.markdown("#### Post-Crash Topology")
            fig_crashed = render_network_figure(
                G_base,
                failed_node=dev_id,
                title=f"Post-Crash Topology: {dev_id} OFFLINE",
            )
            st.plotly_chart(fig_crashed, use_container_width=True)

        st.markdown("### Disaster Recovery & Incident Playbook")
        st.markdown(f"**Affected Branch:** `{dev_info['branch']}` | **Role:** `{dev_info['role']}`")
        if res["isolated_devices"]:
            st.markdown(f"**Isolated Unreachable Nodes:** `{', '.join(res['isolated_devices'])}`")

        ios_dev_code = (
            f"! --- Incident Response for Failed Device: {dev_id} ---\n"
            f"! 1. Quorum & OSPF Neighbor Dampening on adjacent peers\n"
        )
        for link in res["severed_links"]:
            nbr = link["neighbor"]
            ios_dev_code += (
                f"{nbr}# configure terminal\n"
                f"{nbr}(config)# router ospf 1\n"
                f"{nbr}(config-router)# passive-interface default\n"
                f"{nbr}(config-router)# exit\n"
            )
        st.code(ios_dev_code, language="cisco")


# ==============================================================================
# TAB 3: END-TO-END PATH & REACHABILITY INSPECTOR
# ==============================================================================
with tab3:
    st.subheader("End-to-End Hop-by-Hop Path Inspector")
    st.markdown(
        "Evaluate reachability, shortest paths, latency/bandwidth estimations, and all backup paths "
        "between any pair of hosts, switches, routers, or servers."
    )

    path_col1, path_col2, path_col3 = st.columns([2, 2, 1])

    with path_col1:
        src_node = st.selectbox(
            "Source Device:",
            options=all_devices,
            index=all_devices.index("BR1-PC1") if "BR1-PC1" in all_devices else 0,
        )
    with path_col2:
        dst_node = st.selectbox(
            "Destination Device:",
            options=all_devices,
            index=all_devices.index("HQ-SRV2") if "HQ-SRV2" in all_devices else 1,
        )
    with path_col3:
        st.write("")
        st.write("")
        find_btn = st.button("Trace Path", type="primary", use_container_width=True)

    # Quick presets
    st.caption("Quick Test Presets:")
    pr1, pr2, pr3 = st.columns(3)
    if pr1.button("Branch 1 PC1 -> HQ App Server"):
        src_node, dst_node = "BR1-PC1", "HQ-SRV2"
        find_btn = True
    if pr2.button("Branch 4 PC1 -> Branch 2 Lab PC"):
        src_node, dst_node = "BR4-PC1", "BR2-PC2"
        find_btn = True
    if pr3.button("Branch 3 PC1 -> HQ DNS Server"):
        src_node, dst_node = "BR3-PC1", "HQ-SRV1"
        find_btn = True

    if find_btn or src_node != dst_node:
        is_connected = check_connectivity(G_base, src_node, dst_node)

        if not is_connected:
            st.error(f"No path exists between `{src_node}` and `{dst_node}`.")
        else:
            primary_path = find_path(G_base, src_node, dst_node)
            all_simple = find_all_paths(G_base, src_node, dst_node, cutoff=8)

            # Calculate path metrics
            hop_count = len(primary_path) - 1
            min_bw = float("inf")
            est_latency = 0.0

            for i in range(len(primary_path) - 1):
                u_p, v_p = primary_path[i], primary_path[i + 1]
                edge_d = G_base.edges[u_p, v_p]
                bw_val = float(edge_d.get("bandwidth_mbps", 100))
                min_bw = min(min_bw, bw_val)

                lid = edge_d.get("link_id", "")
                if lid in SERIAL_LINKS:
                    est_latency += 35.0
                elif edge_d.get("link_type") == "WAN":
                    est_latency += 12.0
                else:
                    est_latency += 1.0

            # Metric Cards
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Path Reachability", "CONNECTED", delta="100% Active")
            m2.metric("Total Hops", f"{hop_count} Hops", delta=f"{len(primary_path)} Devices")
            m3.metric("Bottleneck Bandwidth", f"{min_bw:.0f} Mbps")
            m4.metric("Estimated Latency", f"~{est_latency:.1f} ms")

            # Breadcrumb Sequence
            st.markdown("#### Hop-by-Hop Transmission Sequence:")
            breadcrumb_html = ""
            for idx, dev in enumerate(primary_path):
                dev_d = G_base.nodes[dev]
                dtype = dev_d.get("device_type", "PC")
                b_color = BRANCH_COLORS.get(dev_d.get("branch", ""), "#1d4ed8")
                breadcrumb_html += f"<span class='breadcrumb-step' style='border-left: 4px solid {b_color};'><b>{dev}</b> ({dtype})</span>"
                if idx < len(primary_path) - 1:
                    breadcrumb_html += " &rarr; "
            st.markdown(breadcrumb_html, unsafe_allow_html=True)

            # Path Plotly Visualizer
            st.markdown("#### Active Route Visualizer:")
            fig_path = render_network_figure(
                G_base,
                highlight_path=primary_path,
                title=f"Shortest Path: {src_node} -> {dst_node} ({hop_count} hops)",
            )
            st.plotly_chart(fig_path, use_container_width=True)

            # Alternate Paths List
            if len(all_simple) > 1:
                with st.expander(f"All {len(all_simple)} Discovered Loop-Free Paths:", expanded=False):
                    for p_idx, alt_p in enumerate(all_simple):
                        is_prim = (alt_p == primary_path)
                        label = " (PRIMARY OSPF ROUTE)" if is_prim else ""
                        st.markdown(f"**Path {p_idx + 1}{label}:** `{' -> '.join(alt_p)}` ({len(alt_p) - 1} hops)")


# ==============================================================================
# TAB 4: ML FAILURE RISK INTEGRATION
# ==============================================================================
with tab4:
    st.subheader("Machine Learning Failure Risk Analytics")
    st.markdown(
        "Integrates predictive machine learning models (`ml/predictions.json` & `ml/models/`) "
        "trained on graph centralities and time-series telemetry."
    )

    if ml_predictions is not None:
        kpis = ml_predictions.get("kpis", {})
        overall_health = ml_predictions.get("overall_health_score", 100.0)

        # Health Gauge & Top Cards
        hc1, hc2, hc3 = st.columns([1, 1, 1])
        with hc1:
            st.metric("Enterprise AI Health Score", f"{overall_health:.1f} / 100", delta="Predictive Model")
        with hc2:
            st.metric(
                "Link Risk Breakdown",
                f"{kpis.get('link_counts', {}).get('total', 24)} Links",
                delta=f"{kpis.get('link_counts', {}).get('healthy', 24)} Healthy | {kpis.get('link_counts', {}).get('warning', 0)} Warn | {kpis.get('link_counts', {}).get('critical', 0)} Crit",
            )
        with hc3:
            st.metric(
                "Device Risk Breakdown",
                f"{kpis.get('device_counts', {}).get('total', 22)} Devices",
                delta=f"{kpis.get('device_counts', {}).get('healthy', 22)} Healthy | {kpis.get('device_counts', {}).get('warning', 0)} Warn | {kpis.get('device_counts', {}).get('critical', 0)} Crit",
            )

        # Top Vulnerable Elements
        top_v_col1, top_v_col2 = st.columns(2)
        with top_v_col1:
            st.markdown("#### Top Vulnerable Links (ML Risk Ranking)")
            top_links = kpis.get("top_vulnerable_links", [])
            for tl in top_links:
                risk_lvl = tl.get("risk_level", "LOW")
                badge_class = "badge-critical" if risk_lvl == "HIGH" else ("badge-warning" if risk_lvl == "MEDIUM" else "badge-healthy")
                st.markdown(
                    f"<div class='kpi-card'>"
                    f"<b>{tl['link_id']}</b> ({tl['link_type']}) | Endpoints: <code>{tl['source_device']} &lt;-&gt; {tl['target_device']}</code><br>"
                    f"Risk Level: <span class='{badge_class}'>{risk_lvl}</span> | "
                    f"Failure Probability: <b>{tl['failure_probability']:.1%}</b> | Health: <b>{tl['health_score']:.1f}/100</b><br>"
                    f"<small style='color:#64748b;'>{' • '.join(tl.get('risk_factors', ['Nominal']))}</small>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        with top_v_col2:
            st.markdown("#### Top Vulnerable Devices (ML Risk Ranking)")
            top_devs = kpis.get("top_vulnerable_devices", [])
            for td in top_devs:
                dev_state = td.get("health_state", "HEALTHY")
                badge_class = "badge-critical" if dev_state == "CRITICAL" else ("badge-warning" if dev_state == "WARNING" else "badge-healthy")
                st.markdown(
                    f"<div class='kpi-card'>"
                    f"<b>{td['device_id']}</b> ({td['device_type']}) | Branch: <code>{td['branch']}</code><br>"
                    f"Health State: <span class='{badge_class}'>{dev_state}</span> | "
                    f"Health Score: <b>{td['health_score']:.1f}/100</b> | Blast Radius: <b>{td['predicted_blast_radius']} Nodes</b><br>"
                    f"<small style='color:#64748b;'>{' • '.join(td.get('risk_factors', ['Nominal']))}</small>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # Full Data Tables
        st.markdown("### Complete Enterprise Device & Link Risk Tables")
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            dev_rows = []
            for d in ml_predictions.get("devices", []):
                dev_rows.append({
                    "Device": d["device_id"],
                    "Type": d["device_type"],
                    "Branch": d["branch"],
                    "State": d["health_state"],
                    "Risk": d["risk_level"],
                    "Health": d["health_score"],
                    "Blast Radius": d["predicted_blast_radius"],
                })
            st.dataframe(pd.DataFrame(dev_rows), use_container_width=True)

        with t_col2:
            link_rows = []
            for l in ml_predictions.get("links", []):
                link_rows.append({
                    "Link": l["link_id"],
                    "Type": l["link_type"],
                    "P(Fail)": f"{l['failure_probability']:.1%}",
                    "Risk": l["risk_level"],
                    "Health": l["health_score"],
                    "Bridge": "YES" if l["is_bridge"] else "NO",
                    "Alt Path": "YES" if l["alternate_path_exists"] else "NO",
                })
            st.dataframe(pd.DataFrame(link_rows), use_container_width=True)

    else:
        st.info("`ml/predictions.json` not found. Run `python ml/main.py --matrix` to generate fresh ML predictions.")

# Footer
st.divider()
st.caption(
    "AI-Driven Network Digital Twin & Predictive Failure Recovery Simulator | "
    "5 Branches • 22 Devices • 24 Links • OSPF Area 0 Backbone • Cisco Packet Tracer 9.0"
)
