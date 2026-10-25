# Team Handover & API Integration Contract

**Project Title:** AI-Driven Network Digital Twin for Failure Prediction and Recovery  
**Module:** Network Topology & NetworkX Graph Engine (`python/`)  
**Target Consumers:** Digital Twin Simulator & Streamlit Dashboard (`dashboard/`), ML Failure Predictor (`ml/`)  

---

## 1. Executive Summary for Teammates

This module provides the baseline topology and graph-theoretic failure simulation core for our project. It defines an enterprise 5-branch organization network (Headquarters + 4 branches) with 22 devices, 24 links, VLANs, and redundant WAN paths.

You do not need to implement raw network graph construction or topology traversal. You can directly import the verified functions documented below.

---

## 2. Quickstart Code Snippet for Streamlit Dashboard

```python
import sys
from pathlib import Path

# Add python directory to path if importing from dashboard/
sys.path.append(str(Path(__file__).resolve().parent.parent / "python"))

from inventory_loader import load_inventory
from topology import build_graph, get_topology_summary
from graph_analysis import (
    check_connectivity,
    find_path,
    simulate_device_failure,
    simulate_link_failure,
)

# 1. Load validated baseline network
inventory = load_inventory()
G = build_graph(inventory)

# 2. Get quick metrics for dashboard KPI cards
summary = get_topology_summary(G)
print(f"Total Nodes: {summary['node_count']}")
print(f"Total Links: {summary['edge_count']}")

# 3. Simulate What-If Link Failure from user dropdown
result = simulate_link_failure(G, link_id="WAN-HQ-BR1")
if result["alternate_path_found"]:
    print(f"Rerouted via: {' -> '.join(result['alternate_path'])}")
else:
    print("WARNING: Network partitioned!")
```

---

## 3. Quickstart Code Snippet for ML Feature Engineering

```python
import sys
from pathlib import Path
import networkx as nx

sys.path.append(str(Path(__file__).resolve().parent.parent / "python"))
from inventory_loader import load_inventory
from topology import build_graph

# Build baseline graph
G = build_graph(load_inventory())

# Extract Graph-Theoretic ML Features for each node
node_features = {}
degree_centrality = nx.degree_centrality(G)
betweenness_centrality = nx.betweenness_centrality(G)
closeness_centrality = nx.closeness_centrality(G)

for node in G.nodes():
    node_features[node] = {
        "device_type": G.nodes[node]["device_type"],
        "degree": G.degree[node],
        "degree_centrality": degree_centrality[node],
        "betweenness_centrality": betweenness_centrality[node],
        "closeness_centrality": closeness_centrality[node],
        "is_router": int(G.nodes[node]["device_type"] == "Router"),
    }
```

---

## 4. Key Guarantees
1. **Immutability:** Calling `simulate_device_failure` or `simulate_link_failure` **never** alters the baseline graph `G`. You can reuse `G` indefinitely.
2. **Referential Integrity:** Every link strictly connects existing devices. No dangling edges.
3. **Cross-Platform:** Works on Windows, Linux, and macOS across Python 3.10 through 3.13+.
