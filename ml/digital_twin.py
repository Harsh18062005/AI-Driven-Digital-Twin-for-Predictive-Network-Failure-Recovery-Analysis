"""Unified Network Digital Twin Engine.

Orchestrates NetworkX topology graphs, real-time ML failure prediction,
unsupervised telemetry anomaly detection, what-if fault simulations, and
prescriptive Cisco IOS self-healing recovery recommendations.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root and python/ to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
PYTHON_DIR = PROJECT_ROOT / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from typing import Any, Dict, List, Optional, Tuple, Union

from inventory_loader import load_inventory
from topology import build_graph, get_topology_summary, list_devices_by_branch
from graph_analysis import simulate_device_failure, simulate_link_failure

from ml.config import (
    ALL_DEVICE_IDS,
    ALL_LINK_IDS,
    BRANCHES,
    NETWORK_JSON_PATH,
    ROUTER_IDS,
    SWITCH_IDS,
    WAN_LINK_IDS,
)
from ml.feature_engineering import NetworkFeatureExtractor
from ml.predictor import FailurePredictor
from ml.recovery_engine import PrescriptiveRecoveryEngine


class NetworkDigitalTwin:
    """Unified Facade for AI-Driven Network Digital Twin operations."""

    def __init__(
        self,
        inventory_path: Optional[Path] = None,
        load_models: bool = True,
    ):
        """Initialize the Digital Twin with topology, feature extractor, predictor, and recovery engine."""
        self.inventory_path = inventory_path or NETWORK_JSON_PATH
        self.inventory = load_inventory(self.inventory_path)
        self.graph = build_graph(self.inventory)
        
        self.extractor = NetworkFeatureExtractor(self.inventory_path)
        self.predictor = FailurePredictor(self.extractor, load_artifacts=load_models)
        self.recovery_engine = PrescriptiveRecoveryEngine(self.inventory_path)

    def get_topology_overview(self) -> Dict[str, Any]:
        """Return structural topology overview from verified graph."""
        summary = get_topology_summary(self.graph)
        branch_map = list_devices_by_branch(self.graph)
        return {
            "network_name": summary["network_name"],
            "total_nodes": summary["node_count"],
            "total_edges": summary["edge_count"],
            "is_connected": summary["is_connected"],
            "connected_components_count": summary["connected_components_count"],
            "device_types": summary["device_types"],
            "link_types": summary["link_types"],
            "branches": branch_map,
        }

    def get_enterprise_health_matrix(
        self,
        link_telemetry: Optional[Dict[str, Dict[str, float]]] = None,
        device_telemetry: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> Dict[str, Any]:
        """Retrieve unified health matrix with ML risk predictions for all 22 devices and 24 links."""
        link_predictions = self.predictor.predict_all_links(link_telemetry)
        device_predictions = self.predictor.predict_all_devices(device_telemetry)
        risk_summary = self.predictor.get_network_risk_summary(link_telemetry, device_telemetry)

        return {
            "overall_health_score": risk_summary["overall_network_health_score"],
            "kpis": risk_summary,
            "links": link_predictions,
            "devices": device_predictions,
        }

    def predict_and_mitigate(
        self,
        target_id: str,
        telemetry: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """End-to-end diagnosis: Predict failure probability, detect anomalies, and prescribe recovery.

        Args:
            target_id: Link ID (e.g. 'WAN-HQ-BR1') or Device ID (e.g. 'HQ-R1').
            telemetry: Optional custom telemetry dictionary.

        Returns:
            Comprehensive diagnosis and mitigation report.
        """
        is_link = target_id in ALL_LINK_IDS or (
            target_id in self.extractor.link_static_features
        )
        is_device = target_id in ALL_DEVICE_IDS or (
            target_id in self.extractor.device_static_features
        )

        if not is_link and not is_device:
            raise KeyError(
                f"Target ID '{target_id}' is neither a recognized link nor device. "
                f"Available devices: {len(ALL_DEVICE_IDS)}, Available links: {len(ALL_LINK_IDS)}."
            )

        if is_link:
            pred = self.predictor.predict_link(target_id, telemetry)
            recovery = self.recovery_engine.recommend_link_recovery(target_id, pred)
            
            return {
                "target_type": "LINK",
                "target_id": target_id,
                "prediction": pred,
                "recovery_plan": recovery,
                "summary": (
                    f"Link {target_id} ({pred['link_type']}) - Risk: {pred['risk_level']} "
                    f"(Failure Probability: {pred['failure_probability']:.1%}, Health: {pred['health_score']}/100). "
                    f"Recovery Strategy: {recovery['action_title']}."
                ),
            }

        else:
            pred = self.predictor.predict_device(target_id, telemetry)
            recovery = self.recovery_engine.recommend_device_recovery(target_id, pred)

            return {
                "target_type": "DEVICE",
                "target_id": target_id,
                "prediction": pred,
                "recovery_plan": recovery,
                "summary": (
                    f"Device {target_id} ({pred['device_type']} in {pred['branch']}) - "
                    f"State: {pred['health_state']} (Risk: {pred['risk_level']}, Health: {pred['health_score']}/100). "
                    f"Blast Radius Potential: {pred['predicted_blast_radius']} devices. "
                    f"Recovery Strategy: {recovery['recovery_strategy']}."
                ),
            }

    def simulate_what_if_scenario(
        self,
        target_id: str,
    ) -> Dict[str, Any]:
        """Execute a non-destructive what-if failure simulation in the digital twin.

        Args:
            target_id: Link ID or Device ID to fail.

        Returns:
            Simulation report with impact metrics, partition analysis, and recovery prescription.
        """
        is_link = target_id in self.extractor.link_static_features
        is_device = target_id in self.extractor.device_static_features

        if is_link:
            sim_result = simulate_link_failure(self.graph, link_id=target_id)
            recovery = self.recovery_engine.recommend_link_recovery(target_id)
            return {
                "scenario_type": "LINK_FAILURE",
                "target_id": target_id,
                "simulation": sim_result,
                "recovery_prescription": recovery,
            }
        elif is_device:
            sim_result = simulate_device_failure(self.graph, failed_device_id=target_id)
            recovery = self.recovery_engine.recommend_device_recovery(target_id)
            return {
                "scenario_type": "DEVICE_FAILURE",
                "target_id": target_id,
                "simulation": sim_result,
                "recovery_prescription": recovery,
            }
        else:
            raise KeyError(f"Unknown target identifier '{target_id}'.")

    def export_dashboard_snapshot(self) -> Dict[str, Any]:
        """Export a clean JSON-serializable snapshot optimized for Streamlit dashboard rendering."""
        matrix = self.get_enterprise_health_matrix()
        topo = self.get_topology_overview()

        return {
            "network_name": topo["network_name"],
            "total_devices": topo["total_nodes"],
            "total_links": topo["total_edges"],
            "overall_health_score": matrix["overall_health_score"],
            "kpis": matrix["kpis"],
            "devices": matrix["devices"],
            "links": matrix["links"],
            "top_vulnerable_links": matrix["kpis"]["top_vulnerable_links"],
            "top_vulnerable_devices": matrix["kpis"]["top_vulnerable_devices"],
        }
