"""Graph-Theoretic and Telemetry Feature Engineering Engine.

Extracts structural topology metrics from NetworkX digital twin graphs and
combines them with dynamic telemetry metrics for predictive failure modeling.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import networkx as nx
import numpy as np
import pandas as pd

# Direct integration with python/ core APIs per project contract
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
PYTHON_DIR = PROJECT_ROOT / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from inventory_loader import load_inventory
from topology import build_graph, get_topology_summary, list_devices_by_branch
from graph_analysis import simulate_device_failure, simulate_link_failure

from ml.config import (
    DEVICE_NUMERICAL_FEATURES,
    LINK_NUMERICAL_FEATURES,
    NETWORK_JSON_PATH,
    ALL_DEVICE_IDS,
    ALL_LINK_IDS,
)


class NetworkFeatureExtractor:
    """Extracts topological and composite telemetry features for network digital twin nodes and links."""

    def __init__(self, inventory_path: Optional[Path] = None):
        """Initialize feature extractor with loaded graph and precomputed graph metrics."""
        self.inventory_path = inventory_path or NETWORK_JSON_PATH
        self.inventory = load_inventory(self.inventory_path)
        self.graph = build_graph(self.inventory)
        
        # Precompute static graph-theoretic metrics
        self._precompute_graph_metrics()

    def _precompute_graph_metrics(self) -> None:
        """Compute NetworkX centralities, articulation points, bridges, and path redundancies."""
        G = self.graph

        # Node Centralities
        self.node_degrees = dict(G.degree())
        self.degree_centrality = nx.degree_centrality(G)
        self.betweenness_centrality = nx.betweenness_centrality(G)
        self.closeness_centrality = nx.closeness_centrality(G)
        
        try:
            self.eigenvector_centrality = nx.eigenvector_centrality(G, max_iter=1000)
        except Exception:
            self.eigenvector_centrality = {node: 0.0 for node in G.nodes()}

        # Articulation points (nodes whose removal increases connected component count)
        self.articulation_points = set(nx.articulation_points(G))

        # Edge Centralities and Bridges
        self.edge_betweenness = nx.edge_betweenness_centrality(G)
        self.bridges = set(nx.bridges(G))

        # Static topological cache for all links
        self.link_static_features: Dict[str, Dict[str, Any]] = {}
        for u, v, data in G.edges(data=True):
            link_id = data.get("link_id")
            if not link_id:
                continue

            # Check if this edge is a bridge (u, v) or (v, u)
            is_br = (u, v) in self.bridges or (v, u) in self.bridges
            
            # Simulate link failure to query alternate path availability & hops
            sim_res = simulate_link_failure(G, link_id=link_id)
            alt_found = 1 if sim_res.get("alternate_path_found") else 0
            alt_hops = sim_res.get("alternate_path_hop_count")
            if alt_hops is None or alt_hops < 0:
                alt_hops = 99  # Large penalty if no alternate path exists

            # Redundancy factor (count of simple loop-free paths up to 6 hops)
            try:
                paths = list(nx.all_simple_paths(G, source=u, target=v, cutoff=6))
                redundancy = len(paths) - 1  # Subtract the direct edge itself
            except Exception:
                redundancy = 0

            bw = float(data.get("bandwidth_mbps", 100.0))
            u_deg = self.node_degrees.get(u, 1)
            v_deg = self.node_degrees.get(v, 1)

            # Look up normalized edge betweenness
            edge_key = (u, v) if (u, v) in self.edge_betweenness else (v, u)
            e_bet = self.edge_betweenness.get(edge_key, 0.0)

            self.link_static_features[link_id] = {
                "link_id": link_id,
                "source_device": u,
                "target_device": v,
                "link_type": data.get("link_type", "Access"),
                "media": data.get("media", "Copper Straight-Through"),
                "bandwidth_mbps": bw,
                "edge_betweenness": float(e_bet),
                "source_degree": int(u_deg),
                "target_degree": int(v_deg),
                "min_endpoint_degree": int(min(u_deg, v_deg)),
                "is_bridge": 1 if is_br else 0,
                "alternate_path_exists": int(alt_found),
                "alternate_path_hops": int(alt_hops),
                "redundancy_factor": int(redundancy),
            }

        # Static topological cache for all nodes
        self.device_static_features: Dict[str, Dict[str, Any]] = {}
        for node, data in G.nodes(data=True):
            dev_type = data.get("device_type", "PC")
            is_router = 1 if dev_type == "Router" else 0
            is_switch = 1 if dev_type == "Switch" else 0
            is_server = 1 if dev_type == "Server" else 0
            is_pc = 1 if dev_type == "PC" else 0
            is_art = 1 if node in self.articulation_points else 0

            # Compute blast radius potential (isolated/disconnected nodes if failed)
            sim_node = simulate_device_failure(G, failed_device_id=node)
            partitions = sim_node.get("partitions", [])
            if len(partitions) > 1:
                # Disconnected nodes = total nodes minus the largest partition and the failed node
                largest_part = max(len(p) for p in partitions)
                blast_radius = G.number_of_nodes() - 1 - largest_part
            else:
                blast_radius = 0

            self.device_static_features[node] = {
                "device_id": node,
                "hostname": data.get("hostname", node),
                "device_type": dev_type,
                "branch": data.get("branch", "Unknown"),
                "role": data.get("role", "Unknown"),
                "degree": int(self.node_degrees.get(node, 1)),
                "degree_centrality": float(self.degree_centrality.get(node, 0.0)),
                "betweenness_centrality": float(self.betweenness_centrality.get(node, 0.0)),
                "closeness_centrality": float(self.closeness_centrality.get(node, 0.0)),
                "eigenvector_centrality": float(self.eigenvector_centrality.get(node, 0.0)),
                "is_articulation_point": int(is_art),
                "is_router": int(is_router),
                "is_switch": int(is_switch),
                "is_server": int(is_server),
                "is_pc": int(is_pc),
                "blast_radius_potential": int(blast_radius),
            }

    @staticmethod
    def calculate_link_congestion_index(
        utilization_pct: float,
        queue_depth_pct: float,
        jitter_ms: float,
        packet_loss_pct: float,
    ) -> float:
        """Calculate composite link congestion score normalized between 0.0 and 1.0."""
        u_norm = np.clip(utilization_pct / 100.0, 0.0, 1.0)
        q_norm = np.clip(queue_depth_pct / 100.0, 0.0, 1.0)
        j_norm = np.clip(jitter_ms / 20.0, 0.0, 1.0)
        p_norm = np.clip(packet_loss_pct / 10.0, 0.0, 1.0)
        return float(u_norm * 0.4 + q_norm * 0.3 + j_norm * 0.2 + p_norm * 0.1)

    @staticmethod
    def calculate_link_health_index(
        packet_loss_pct: float,
        latency_ms: float,
        jitter_ms: float,
        error_rate: float,
        utilization_pct: float,
    ) -> float:
        """Calculate normalized healthy link index from 0.0 (failing) to 100.0 (optimal)."""
        loss_penalty = min(50.0, packet_loss_pct * 8.0)
        latency_penalty = min(25.0, (latency_ms / 30.0) * 10.0)
        jitter_penalty = min(15.0, jitter_ms * 2.5)
        error_penalty = min(20.0, error_rate * 2.0)
        util_penalty = max(0.0, (utilization_pct - 75.0) * 0.8)
        
        total_penalty = loss_penalty + latency_penalty + jitter_penalty + error_penalty + util_penalty
        return float(np.clip(100.0 - total_penalty, 0.0, 100.0))

    @staticmethod
    def calculate_device_stress_score(
        cpu_pct: float,
        mem_pct: float,
        temperature_c: float,
        interface_error_count: float,
        buffer_utilization_pct: float,
    ) -> float:
        """Calculate composite device stress index normalized between 0.0 and 1.0."""
        c_norm = np.clip(cpu_pct / 100.0, 0.0, 1.0)
        m_norm = np.clip(mem_pct / 100.0, 0.0, 1.0)
        t_norm = np.clip(max(0.0, temperature_c - 30.0) / 45.0, 0.0, 1.0)
        e_norm = np.clip(interface_error_count / 50.0, 0.0, 1.0)
        b_norm = np.clip(buffer_utilization_pct / 100.0, 0.0, 1.0)
        
        return float(c_norm * 0.30 + m_norm * 0.25 + t_norm * 0.20 + b_norm * 0.15 + e_norm * 0.10)

    @staticmethod
    def calculate_device_health_index(device_stress_score: float) -> float:
        """Calculate normalized device health score from 0.0 to 100.0."""
        return float(np.clip(100.0 - (device_stress_score * 100.0), 0.0, 100.0))

    def extract_link_features(
        self,
        link_id: str,
        telemetry: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Extract combined topological and telemetry features for a single link.

        Args:
            link_id: The unique link ID (e.g., 'WAN-HQ-BR1').
            telemetry: Optional dictionary with telemetry measurements.
                Keys: 'packet_loss_pct', 'latency_ms', 'jitter_ms',
                      'utilization_pct', 'error_rate', 'queue_depth_pct'.

        Returns:
            Dictionary containing all feature values.
        """
        if link_id not in self.link_static_features:
            raise KeyError(f"Link ID '{link_id}' is not in network topology.")

        feat = dict(self.link_static_features[link_id])
        
        # Default nominal telemetry if none supplied
        telem = telemetry or {}
        loss = float(telem.get("packet_loss_pct", 0.0))
        lat = float(telem.get("latency_ms", 2.0 if feat["bandwidth_mbps"] >= 1000 else 18.0))
        jit = float(telem.get("jitter_ms", 0.5))
        util = float(telem.get("utilization_pct", 35.0))
        err = float(telem.get("error_rate", 0.0))
        q_depth = float(telem.get("queue_depth_pct", 10.0))

        feat["packet_loss_pct"] = loss
        feat["latency_ms"] = lat
        feat["jitter_ms"] = jit
        feat["utilization_pct"] = util
        feat["error_rate"] = err
        feat["queue_depth_pct"] = q_depth

        # Composite indices
        feat["congestion_index"] = self.calculate_link_congestion_index(util, q_depth, jit, loss)
        feat["link_health_index"] = self.calculate_link_health_index(loss, lat, jit, err, util)

        return feat

    def extract_device_features(
        self,
        device_id: str,
        telemetry: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Extract combined topological and telemetry features for a single device.

        Args:
            device_id: The unique device ID (e.g., 'HQ-R1').
            telemetry: Optional dictionary with device telemetry measurements.
                Keys: 'cpu_pct', 'mem_pct', 'temperature_c',
                      'interface_error_count', 'buffer_utilization_pct'.

        Returns:
            Dictionary containing all feature values.
        """
        if device_id not in self.device_static_features:
            raise KeyError(f"Device ID '{device_id}' is not in network topology.")

        feat = dict(self.device_static_features[device_id])

        telem = telemetry or {}
        cpu = float(telem.get("cpu_pct", 25.0))
        mem = float(telem.get("mem_pct", 35.0))
        temp = float(telem.get("temperature_c", 38.0))
        err = float(telem.get("interface_error_count", 0.0))
        buf = float(telem.get("buffer_utilization_pct", 12.0))

        feat["cpu_pct"] = cpu
        feat["mem_pct"] = mem
        feat["temperature_c"] = temp
        feat["interface_error_count"] = err
        feat["buffer_utilization_pct"] = buf

        stress = self.calculate_device_stress_score(cpu, mem, temp, err, buf)
        feat["device_stress_score"] = stress
        feat["device_health_index"] = self.calculate_device_health_index(stress)

        return feat

    def get_all_links_features(
        self,
        telemetry_map: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> pd.DataFrame:
        """Extract features for all 24 links as a structured DataFrame."""
        rows = []
        telem_map = telemetry_map or {}
        for link_id in sorted(self.link_static_features.keys()):
            link_telem = telem_map.get(link_id)
            rows.append(self.extract_link_features(link_id, link_telem))
        return pd.DataFrame(rows)

    def get_all_devices_features(
        self,
        telemetry_map: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> pd.DataFrame:
        """Extract features for all 22 devices as a structured DataFrame."""
        rows = []
        telem_map = telemetry_map or {}
        for dev_id in sorted(self.device_static_features.keys()):
            dev_telem = telem_map.get(dev_id)
            rows.append(self.extract_device_features(dev_id, dev_telem))
        return pd.DataFrame(rows)
