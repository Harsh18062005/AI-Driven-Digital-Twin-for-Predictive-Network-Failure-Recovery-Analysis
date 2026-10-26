"""Predictive Inference Engine for Network Links and Devices.

Loads trained classifiers, regressors, and scalers to perform real-time
failure risk prediction, health scoring, anomaly attribution, and blast
radius estimation for all 22 devices and 24 links in the digital twin.
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

from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np

from ml.anomaly_detector import TelemetryAnomalyDetector
from ml.config import (
    ALL_DEVICE_IDS,
    ALL_LINK_IDS,
    ANOMALY_DETECTOR_PATH,
    BLAST_RADIUS_MODEL_PATH,
    DEVICE_FAILURE_MODEL_PATH,
    DEVICE_NUMERICAL_FEATURES,
    DEVICE_SCALER_PATH,
    HEALTH_STATE_CRITICAL,
    HEALTH_STATE_NORMAL,
    HEALTH_STATE_WARNING,
    LINK_FAILURE_MODEL_PATH,
    LINK_NUMERICAL_FEATURES,
    LINK_SCALER_PATH,
    RISK_LEVEL_HIGH,
    RISK_LEVEL_LOW,
    RISK_LEVEL_MEDIUM,
    THRESHOLDS,
)
from ml.feature_engineering import NetworkFeatureExtractor


class FailurePredictor:
    """Predictive failure engine for the Network Digital Twin."""

    def __init__(
        self,
        extractor: Optional[NetworkFeatureExtractor] = None,
        load_artifacts: bool = True,
    ):
        """Initialize predictor with feature extractor and load model artifacts."""
        self.extractor = extractor or NetworkFeatureExtractor()
        self.link_clf = None
        self.link_scaler = None
        self.dev_clf = None
        self.dev_scaler = None
        self.blast_reg = None
        self.anomaly_detector = None

        if load_artifacts:
            self.load_models()

    def load_models(self) -> None:
        """Load trained model artifacts and scalers from disk."""
        if not LINK_FAILURE_MODEL_PATH.exists() or not DEVICE_FAILURE_MODEL_PATH.exists():
            raise FileNotFoundError(
                "Trained models not found in ml/models/. Run 'python ml/train.py' first."
            )

        self.link_clf = joblib.load(LINK_FAILURE_MODEL_PATH)
        self.link_scaler = joblib.load(LINK_SCALER_PATH)
        self.dev_clf = joblib.load(DEVICE_FAILURE_MODEL_PATH)
        self.dev_scaler = joblib.load(DEVICE_SCALER_PATH)

        if BLAST_RADIUS_MODEL_PATH.exists():
            self.blast_reg = joblib.load(BLAST_RADIUS_MODEL_PATH)

        if ANOMALY_DETECTOR_PATH.exists():
            try:
                self.anomaly_detector = TelemetryAnomalyDetector.load(ANOMALY_DETECTOR_PATH)
            except Exception:
                self.anomaly_detector = None

    def _determine_link_risk_factors(
        self,
        features: Dict[str, Any],
        prob: float,
    ) -> List[str]:
        """Explain why a link was flagged with failure risk."""
        factors = []
        loss = features.get("packet_loss_pct", 0.0)
        q_depth = features.get("queue_depth_pct", 0.0)
        util = features.get("utilization_pct", 0.0)
        lat = features.get("latency_ms", 0.0)
        jit = features.get("jitter_ms", 0.0)
        err = features.get("error_rate", 0.0)
        is_br = features.get("is_bridge", 0)
        alt_exists = features.get("alternate_path_exists", 1)

        if loss >= THRESHOLDS["packet_loss_pct"]["critical"]:
            factors.append(f"Severe packet drop: {loss:.2f}% (critical threshold: 5.0%)")
        elif loss >= THRESHOLDS["packet_loss_pct"]["warning"]:
            factors.append(f"Elevated packet loss: {loss:.2f}% (warning threshold: 2.0%)")

        if q_depth >= 85.0:
            factors.append(f"Buffer queue saturation: {q_depth:.1f}%")

        if util >= THRESHOLDS["utilization_pct"]["critical"]:
            factors.append(f"Link bandwidth saturation: {util:.1f}%")

        if jit >= THRESHOLDS["jitter_ms"]["critical"]:
            factors.append(f"High jitter variance: {jit:.2f}ms")

        if err >= THRESHOLDS["error_rate_per_min"]["critical"]:
            factors.append(f"High physical/CRC error rate: {err:.1f}/min")

        if is_br:
            factors.append("Single Point of Failure: Link is a topological bridge (loss partitions network)")

        if not alt_exists:
            factors.append("Zero Redundancy: No alternate path exists if link collapses")

        if not factors and prob > 0.4:
            factors.append("Elevated composite congestion and edge centrality stress")

        return factors

    def _determine_device_risk_factors(
        self,
        features: Dict[str, Any],
        state_idx: int,
    ) -> List[str]:
        """Explain why a device was flagged with warning or critical risk."""
        factors = []
        cpu = features.get("cpu_pct", 0.0)
        mem = features.get("mem_pct", 0.0)
        temp = features.get("temperature_c", 0.0)
        buf = features.get("buffer_utilization_pct", 0.0)
        err = features.get("interface_error_count", 0.0)
        is_art = features.get("is_articulation_point", 0)
        pot_blast = features.get("blast_radius_potential", 0)

        if cpu >= THRESHOLDS["cpu_pct"]["critical"]:
            factors.append(f"Critical CPU saturation: {cpu:.1f}% (> 85%)")
        elif cpu >= THRESHOLDS["cpu_pct"]["warning"]:
            factors.append(f"Elevated CPU load: {cpu:.1f}% (> 70%)")

        if mem >= THRESHOLDS["mem_pct"]["critical"]:
            factors.append(f"Memory exhaustion: {mem:.1f}% (> 90%)")

        if temp >= THRESHOLDS["temp_celsius"]["critical"]:
            factors.append(f"Hardware thermal alert: {temp:.1f}°C (> 72°C)")

        if buf >= 85.0:
            factors.append(f"Packet buffer overflow risk: {buf:.1f}%")

        if err >= 20.0:
            factors.append(f"Interface packet drop rate: {err:.1f} drops/min")

        if is_art:
            factors.append(f"Articulation Node: Failure isolates {pot_blast} devices")

        if not factors and state_idx > 0:
            factors.append("High multi-dimensional resource stress index")

        return factors

    def predict_link(
        self,
        link_id: str,
        telemetry: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Predict failure risk and health score for a specific network link.

        Args:
            link_id: Unique link identifier (e.g., 'WAN-HQ-BR1').
            telemetry: Optional real-time telemetry dict.

        Returns:
            Structured prediction dictionary.
        """
        if self.link_clf is None:
            raise RuntimeError("Models not loaded. Call load_models() first.")

        feat_dict = self.extractor.extract_link_features(link_id, telemetry)
        
        # Build vector in exact feature order
        vector = [feat_dict[k] for k in LINK_NUMERICAL_FEATURES]
        X = np.array([vector])
        X_scaled = self.link_scaler.transform(X)

        prob = float(self.link_clf.predict_proba(X_scaled)[0, 1])
        is_fail = bool(prob >= 0.50)

        # Risk level categorization
        if prob < 0.35:
            risk = RISK_LEVEL_LOW
        elif prob < 0.70:
            risk = RISK_LEVEL_MEDIUM
        else:
            risk = RISK_LEVEL_HIGH

        health_score = round(max(0.0, (1.0 - prob) * 100.0), 1)
        risk_factors = self._determine_link_risk_factors(feat_dict, prob)

        # Anomaly Detection check
        anomaly_info = None
        if self.anomaly_detector:
            anomaly_info = self.anomaly_detector.score_sample(feat_dict)

        return {
            "link_id": link_id,
            "source_device": feat_dict["source_device"],
            "target_device": feat_dict["target_device"],
            "link_type": feat_dict["link_type"],
            "bandwidth_mbps": feat_dict["bandwidth_mbps"],
            "failure_probability": round(prob, 4),
            "failure_predicted": is_fail,
            "risk_level": risk,
            "health_score": health_score,
            "is_bridge": bool(feat_dict["is_bridge"]),
            "alternate_path_exists": bool(feat_dict["alternate_path_exists"]),
            "alternate_path_hops": feat_dict["alternate_path_hops"],
            "risk_factors": risk_factors,
            "anomaly_analysis": anomaly_info,
            "telemetry_snapshot": {
                "packet_loss_pct": feat_dict["packet_loss_pct"],
                "latency_ms": feat_dict["latency_ms"],
                "jitter_ms": feat_dict["jitter_ms"],
                "utilization_pct": feat_dict["utilization_pct"],
                "error_rate": feat_dict["error_rate"],
                "queue_depth_pct": feat_dict["queue_depth_pct"],
                "congestion_index": round(feat_dict["congestion_index"], 3),
            },
        }

    def predict_device(
        self,
        device_id: str,
        telemetry: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Predict health state and blast radius impact for a network device.

        Args:
            device_id: Unique device identifier (e.g., 'HQ-R1').
            telemetry: Optional real-time telemetry dict.

        Returns:
            Structured prediction dictionary.
        """
        if self.dev_clf is None:
            raise RuntimeError("Models not loaded. Call load_models() first.")

        feat_dict = self.extractor.extract_device_features(device_id, telemetry)
        
        vector = [feat_dict[k] for k in DEVICE_NUMERICAL_FEATURES]
        X = np.array([vector])
        X_scaled = self.dev_scaler.transform(X)

        probs = self.dev_clf.predict_proba(X_scaled)[0]
        state_idx = int(np.argmax(probs))
        
        state_labels = ["HEALTHY", "WARNING", "CRITICAL"]
        predicted_state = state_labels[state_idx]

        # Calculate continuous health score (100 = optimal, 0 = critical)
        prob_healthy = float(probs[HEALTH_STATE_NORMAL])
        prob_warning = float(probs[HEALTH_STATE_WARNING])
        prob_critical = float(probs[HEALTH_STATE_CRITICAL])
        health_score = round(max(0.0, prob_healthy * 100.0 + prob_warning * 45.0), 1)

        if prob_critical >= 0.4 or state_idx == HEALTH_STATE_CRITICAL:
            risk = RISK_LEVEL_HIGH
        elif prob_warning >= 0.4 or state_idx == HEALTH_STATE_WARNING:
            risk = RISK_LEVEL_MEDIUM
        else:
            risk = RISK_LEVEL_LOW

        # Predict blast radius (number of affected nodes)
        if self.blast_reg:
            pred_blast = max(0, int(round(float(self.blast_reg.predict(X_scaled)[0]))))
        else:
            pred_blast = feat_dict["blast_radius_potential"] if state_idx > 0 else 0

        risk_factors = self._determine_device_risk_factors(feat_dict, state_idx)

        return {
            "device_id": device_id,
            "hostname": feat_dict["hostname"],
            "device_type": feat_dict["device_type"],
            "branch": feat_dict["branch"],
            "role": feat_dict["role"],
            "health_state": predicted_state,
            "risk_level": risk,
            "health_score": health_score,
            "state_probabilities": {
                "HEALTHY": round(prob_healthy, 4),
                "WARNING": round(prob_warning, 4),
                "CRITICAL": round(prob_critical, 4),
            },
            "is_articulation_point": bool(feat_dict["is_articulation_point"]),
            "blast_radius_potential": feat_dict["blast_radius_potential"],
            "predicted_blast_radius": pred_blast,
            "risk_factors": risk_factors,
            "telemetry_snapshot": {
                "cpu_pct": feat_dict["cpu_pct"],
                "mem_pct": feat_dict["mem_pct"],
                "temperature_c": feat_dict["temperature_c"],
                "interface_error_count": feat_dict["interface_error_count"],
                "buffer_utilization_pct": feat_dict["buffer_utilization_pct"],
                "device_stress_score": round(feat_dict["device_stress_score"], 3),
            },
        }

    def predict_all_links(
        self,
        telemetry_map: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> List[Dict[str, Any]]:
        """Run failure inference across all 24 enterprise links."""
        telem_map = telemetry_map or {}
        results = []
        for link_id in sorted(self.extractor.link_static_features.keys()):
            results.append(self.predict_link(link_id, telem_map.get(link_id)))
        return results

    def predict_all_devices(
        self,
        telemetry_map: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> List[Dict[str, Any]]:
        """Run health state inference across all 22 enterprise devices."""
        telem_map = telemetry_map or {}
        results = []
        for dev_id in sorted(self.extractor.device_static_features.keys()):
            results.append(self.predict_device(dev_id, telem_map.get(dev_id)))
        return results

    def get_network_risk_summary(
        self,
        link_telemetry: Optional[Dict[str, Dict[str, float]]] = None,
        device_telemetry: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> Dict[str, Any]:
        """Aggregate enterprise-wide health KPIs for dashboard consumption."""
        links = self.predict_all_links(link_telemetry)
        devices = self.predict_all_devices(device_telemetry)

        link_risks = {RISK_LEVEL_LOW: 0, RISK_LEVEL_MEDIUM: 0, RISK_LEVEL_HIGH: 0}
        for l in links:
            link_risks[l["risk_level"]] += 1

        dev_states = {"HEALTHY": 0, "WARNING": 0, "CRITICAL": 0}
        for d in devices:
            dev_states[d["health_state"]] += 1

        # Calculate global enterprise health index (weighted average)
        avg_link_health = float(np.mean([l["health_score"] for l in links]))
        avg_dev_health = float(np.mean([d["health_score"] for d in devices]))
        overall_health = round((avg_link_health * 0.5) + (avg_dev_health * 0.5), 1)

        # Sort highest risk elements
        sorted_links = sorted(links, key=lambda x: x["failure_probability"], reverse=True)
        sorted_devices = sorted(devices, key=lambda x: x["state_probabilities"]["CRITICAL"], reverse=True)

        return {
            "overall_network_health_score": overall_health,
            "link_counts": {
                "total": len(links),
                "healthy": link_risks[RISK_LEVEL_LOW],
                "warning": link_risks[RISK_LEVEL_MEDIUM],
                "critical": link_risks[RISK_LEVEL_HIGH],
            },
            "device_counts": {
                "total": len(devices),
                "healthy": dev_states["HEALTHY"],
                "warning": dev_states["WARNING"],
                "critical": dev_states["CRITICAL"],
            },
            "top_vulnerable_links": sorted_links[:3],
            "top_vulnerable_devices": sorted_devices[:3],
        }
