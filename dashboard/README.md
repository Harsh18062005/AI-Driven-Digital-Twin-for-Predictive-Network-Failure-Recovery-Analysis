# Streamlit Network Digital Twin & What-If Failure Simulator

**Project:** AI-Driven Network Digital Twin for Predictive Network Failure Recovery Analysis  
**Module:** Interactive Web Dashboard (`dashboard/`)  
**Core Technologies:** Streamlit, NetworkX, Plotly, Pandas  
**Target Audience:** Network Operations Center (NOC) Engineers, Academic Evaluators, System Administrators  

---

## 1. Executive Summary & Capabilities

The `dashboard/` module provides a comprehensive, interactive, web-based graphical interface for the enterprise **Network Digital Twin**. It mirrors the 5-branch organization network (22 devices and 24 links) designed in Cisco Packet Tracer and NetworkX.

### Key Features:
1. **Live Network Health & KPI Telemetry:** Real-time visibility into active nodes, links, branch distributions, and connectivity state.
2. **Interactive Topology Visualizer (Tab 1):** Plotly-powered 2D digital twin canvas color-coded by branch, with distinct geometry for Routers, Switches, Servers, and PCs, rich hover cards, and deep element inspection.
3. **What-If Failure Simulator & Prescriptive Recovery (Tab 2):** Non-destructive failure injection for links or devices with side-by-side before-and-after visual comparisons, alternate path detection, and auto-generated Cisco IOS remediation configuration scripts.
4. **End-to-End Hop-by-Hop Path Inspector (Tab 3):** Reachability validation, shortest transmission paths, latency/bandwidth estimations, breadcrumb sequencing, and enumeration of all backup redundant paths.
5. **Machine Learning Risk Analytics (Tab 4):** Integration with `ml/predictions.json` displaying failure probability ratings, multi-dimensional stress scores, severity badges (High/Medium/Low), and proactive mitigation recommendations.

---

## 2. Directory Structure

```text
dashboard/
├── app.py              # Main interactive Streamlit Digital Twin application
├── requirements.txt    # Dashboard dependencies (streamlit, networkx, plotly, pandas)
├── README.md           # Installation, usage, and architectural documentation
└── .gitkeep
```

---

## 3. Installation & Prerequisites

Ensure Python 3.10+ (tested on Python 3.13) is installed.

### Install Dependencies:
```powershell
pip install -r dashboard/requirements.txt
```

---

## 4. How to Launch the Digital Twin Dashboard

Run the Streamlit application from the project root:

```powershell
streamlit run dashboard/app.py
```

Once launched, open your web browser at:
```text
http://localhost:8501
```

---

## 5. Dashboard Sections & Usage Guide

### Header: Live Enterprise KPI Telemetry
- **Total Devices (22 Nodes):** 5 Routers, 5 Switches, 2 Central Servers, 10 Workstations.
- **Total Physical/WAN Links (24 Links):** 7 WAN Hub-and-Spoke & Ring Cross-Ties, 5 Distribution Trunks, 12 Access Links.
- **Enterprise Branches:** Headquarters, Branch 1 (North), Branch 2 (South), Branch 3 (East), Branch 4 (West).
- **Digital Twin Health Status:** Real-time connectivity status (100% HEALTHY vs PARTITIONED).

### Tab 1: Interactive Topology Visualizer
- **Geographic 2D Layout:** Accurately reflects Packet Tracer topology with Headquarters at the center and regional branches arranged geographically.
- **Color Coding by Branch:**
  - Navy Blue (`#1D4ED8`): Headquarters
  - Forest Green (`#059669`): Branch 1 (North)
  - Warm Amber (`#D97706`): Branch 2 (South)
  - Violet (`#7C3AED`): Branch 3 (East)
  - Crimson Red (`#DC2626`): Branch 4 (West)
- **Node Shapes:**
  - Diamond: Routers (Cisco 2911)
  - Square: Distribution Switches (Cisco 2960)
  - Triangle: Central Servers (DNS, DHCP, Web/App)
  - Circle: Host Workstations (VLAN-tagged PCs)
- **Interactive Hover Cards:** Hover over any node or link to view hostname, management IP, active VLANs, interface counts, bandwidth, and status.
- **Branch Filtering:** Filter the view to inspect an individual branch or the entire enterprise backbone.

### Tab 2: What-If Failure Simulator & Recovery Analysis
- **Failure Injection Modes:**
  - **Link Failure Mode:** Select primary WAN links (e.g. `WAN-HQ-BR1`), secondary cross-ties (`WAN-BR1-BR2`), or access links.
  - **Device Failure Mode:** Crash core gateway `HQ-R1`, branch gateways, or distribution switches.
- **Immutability Contract:** Uses isolated graph copies from `python/graph_analysis.py`; the baseline graph `G` is never modified.
- **Side-by-Side Comparison:**
  - Left: Healthy baseline network.
  - Right: Degraded topology with severed links highlighted in red (`#DC2626`) and rerouted traffic highlighted in emerald green (`#16A34A`).
- **Prescriptive Recovery Playbook:**
  - Auto-generated Cisco IOS commands (`ip ospf cost 65535`, interface shutdown, `clear ip ospf process`).
  - Automated OSPF convergence time estimation (~30 seconds vs 45 minutes manual dispatch).

### Tab 3: End-to-End Path & Reachability Inspector
- **Source and Destination Selectors:** Select any pair of nodes (e.g., `BR1-PC1` to `HQ-SRV2`).
- **Quick Test Presets:** Test Branch 1 PC to HQ Server, Branch 4 PC to Branch 2 Lab PC, etc.
- **Metrics Calculated:**
  - Reachability Status (Connected / Partitioned)
  - Hop Count and sequence of devices
  - Bottleneck Bandwidth (Mbps)
  - Estimated Latency (ms) based on media type (Serial vs Gigabit WAN vs LAN)
- **Active Route Graph Highlighting:** Visually tracks the transmission path across the network.
- **Backup Paths Enumeration:** Lists all alternative loop-free paths available in the event of congestion.

### Tab 4: ML Failure Risk Integration
- Ingests `ml/predictions.json` generated by the Random Forest / Gradient Boosting models.
- Displays:
  - Overall Enterprise AI Health Score (0-100)
  - Top Vulnerable Links and Devices with severity badges (`HIGH`, `MEDIUM`, `LOW`)
  - Full sortable/filterable risk tables for all 22 devices and 24 links
  - Root cause risk factor explanations (e.g., "Single Point of Failure: Topological bridge", "Buffer queue saturation").

---

## 6. Integration Boundaries & Guarantees

- **Non-Destructive Integration:** Calls functions directly from `python/inventory_loader.py`, `python/topology.py`, and `python/graph_analysis.py`.
- **Zero Modifications:** Leaves `python/` and `packet_tracer/` code completely untouched.
- **Robust Fallbacks:** Gracefully falls back to real-time topological calculations if ML predictions are not pre-computed.
