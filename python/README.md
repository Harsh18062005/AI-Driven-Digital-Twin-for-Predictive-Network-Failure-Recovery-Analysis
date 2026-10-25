# Python NetworkX Graph Analysis & Topology Module

**Project:** AI-Driven Network Digital Twin for Failure Prediction and Recovery  
**Target Environment:** Python 3.10+ (tested on Python 3.13.15)  
**Dependencies:** `networkx>=3.0`, `pytest>=7.0`  
**Authors:** Networking Team Member  

---

## 1. Module Overview & Purpose

This module serves as the **Graph Model Core** for the project. It ingests the verified five-branch enterprise network topology from [network.json](network.json) and instantiates an undirected NetworkX graph representing devices and physical/logical links.

It provides a clean, decoupled, and stable API for downstream consumers:
1. **Digital Twin Simulator (`dashboard/`):** Runs what-if failure simulations, computes rerouting paths, and visualizes network state.
2. **ML Failure Predictor (`ml/`):** Extracts topological features (degrees, centralities, bridge properties) to predict network vulnerabilities.

---

## 2. Directory Structure

```text
python/
├── network.json               # Machine-readable inventory derived from Packet Tracer
├── inventory_loader.py        # Strict schema, IP, CIDR, and referential validator
├── topology.py                # NetworkX graph builder and metadata query utilities
├── graph_analysis.py          # Non-destructive path-finding & failure simulation algorithms
├── main.py                    # Interactive and argument-driven CLI demonstration
├── requirements.txt           # Dependencies (networkx, pytest)
├── README.md                  # Complete technical reference and API documentation
└── tests/
    ├── __init__.py
    ├── test_inventory_loader.py  # 13 schema & validation tests
    ├── test_topology.py          # 12 graph construction & attribute tests
    └── test_graph_analysis.py    # 14 algorithmic & failure simulation tests
```

---

## 3. Installation & Setup

1. **Prerequisites:** Python 3.10 or higher.
2. **Install Dependencies:**
   ```bash
   pip install -r python/requirements.txt
   ```

---

## 4. How to Run

### A. Interactive Demonstration
Launch the interactive command-line interface:
```bash
python python/main.py
```
This presents a menu to inspect devices, query paths, check connectivity, and trigger node/link failure simulations interactively.

### B. Command-Line Arguments
Execute specific analysis queries directly from the command line:
```bash
# Print full topology summary
python python/main.py --summary

# List all devices grouped by branch
python python/main.py --devices

# Find shortest path between two devices
python python/main.py --path BR1-PC1 HQ-SRV2

# Simulate failure of a specific device (e.g. HQ-R1)
python python/main.py --fail-device HQ-R1

# Simulate failure of a specific link (e.g. WAN-HQ-BR1)
python python/main.py --fail-link WAN-HQ-BR1
```

### C. Running Automated Tests
Run the complete pytest test suite:
```powershell
$env:PYTHONPATH="python"
python -m pytest python/tests -v
```
All 39 automated tests pass with 100% test coverage over schema integrity, edge failures, node failures, and alternate path recalculation.

---

## 5. Stable Integration Contract (API for Teammates)

Downstream modules (`dashboard/` and `ml/`) should import functions directly from `python`:

```python
from inventory_loader import load_inventory
from topology import build_graph, get_device_details, get_link_details
from graph_analysis import (
    check_connectivity,
    find_path,
    find_alternative_paths,
    simulate_device_failure,
    simulate_link_failure,
    get_connected_components,
)
```

### Function Signatures & Specifications

#### 1. `load_inventory(file_path: Optional[str | Path] = None) -> dict`
- **Description:** Loads, validates, and parses `network.json`.
- **Returns:** Validated dictionary containing `metadata`, `devices`, and `links`.
- **Raises:** `FileNotFoundError`, `SchemaError`, `DuplicateIdError`, `ReferentialIntegrityError`, `InvalidIPAddressError`.

#### 2. `build_graph(inventory: dict) -> nx.Graph`
- **Description:** Constructs an undirected NetworkX graph with node and edge attributes.
- **Node Attributes:** `hostname`, `device_type`, `branch`, `role`, `model`, `management_ip`, `vlans`, `interfaces`, `status`.
- **Edge Attributes:** `link_id`, `link_type`, `media`, `subnet`, `bandwidth_mbps`, `status`, `role`.

#### 3. `check_connectivity(graph: nx.Graph, source_id: str, target_id: str) -> bool`
- **Description:** Checks if an active path exists between two devices.
- **Returns:** `True` if connected, `False` otherwise.
- **Raises:** `DeviceNotFoundError` if an endpoint ID is invalid.

#### 4. `find_path(graph: nx.Graph, source_id: str, target_id: str, weight: Optional[str] = None) -> Optional[List[str]]`
- **Description:** Calculates the shortest path between `source_id` and `target_id`.
- **Returns:** List of device IDs (e.g. `['BR1-PC1', 'BR1-SW1', 'BR1-R1', 'HQ-R1', 'HQ-SW1', 'HQ-SRV1']`) or `None` if partitioned.

#### 5. `find_alternative_paths(graph: nx.Graph, source_id: str, target_id: str, excluded_link: Optional[Tuple[str, str]] = None, excluded_device: Optional[str] = None) -> List[List[str]]`
- **Description:** Identifies alternative paths when a specific link or device is removed.
- **Guarantee:** **Never modifies the baseline graph.** Clones the graph before testing.

#### 6. `simulate_device_failure(graph: nx.Graph, failed_device_id: str) -> dict`
- **Description:** Simulates the complete outage of a network device.
- **Returns:** Dictionary detailing:
  - `failed_device_id`: Device identifier
  - `severed_links_count`: Number of severed connections
  - `severed_links`: List of disconnected links and neighbors
  - `is_partitioned`: Boolean indicating if the network fractured into disjoint components
  - `baseline_components_count`: Components before failure (default: 1)
  - `post_failure_components_count`: Components after failure
  - `isolated_devices`: List of devices left with 0 connections
  - `partitions`: Lists of devices remaining in each surviving partition

#### 7. `simulate_link_failure(graph: nx.Graph, device_a: Optional[str] = None, device_b: Optional[str] = None, link_id: Optional[str] = None) -> dict`
- **Description:** Simulates a physical cable cut or interface shutdown.
- **Returns:** Dictionary detailing:
  - `failed_link_id`: Link identifier
  - `endpoints`: `[source, target]`
  - `is_bridge`: Boolean (True if losing this link partitions the network)
  - `alternate_path_found`: Boolean (True if traffic between endpoints can reroute)
  - `alternate_path`: Rerouted path list (or `None` if severed)
  - `alternate_path_hop_count`: Number of hops in the rerouted path

---

## 6. Graph Model Assumptions & Limitations

1. **Topological vs. Layer 3/4 Reachability:**
   Graph path existence indicates physical and Layer 2/3 adjacency. In actual networks, traffic can also be blocked by VLAN boundary mismatches, access control lists (ACLs), or routing misconfigurations.
2. **Undirected Representation:**
   Ethernet and serial links are bidirectional at the physical layer. Asymmetric firewall rules or unidirectional rate limits are not modeled at this graph abstraction level.
3. **Immutability Principle:**
   All failure simulation functions clone the baseline graph before mutation. Downstream callers can safely execute thousands of failure scenarios without corrupting the baseline model.
