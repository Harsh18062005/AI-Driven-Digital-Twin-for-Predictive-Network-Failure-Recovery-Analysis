"""Configuration and Constant Definitions for the ML Digital Twin Module.

Defines directory paths, network device/link inventories, operating thresholds,
feature column definitions, and model persistence constants.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

# ==============================================================================
# 1. Directory Structure and Paths
# ==============================================================================
ML_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ML_DIR.parent
PYTHON_DIR = PROJECT_ROOT / "python"
DATA_DIR = ML_DIR / "data"
MODELS_DIR = ML_DIR / "models"

NETWORK_JSON_PATH = PYTHON_DIR / "network.json"
LINK_INVENTORY_CSV_PATH = PROJECT_ROOT / "packet_tracer" / "link_inventory.csv"
DEVICE_INVENTORY_CSV_PATH = PROJECT_ROOT / "packet_tracer" / "device_inventory.csv"

# Model Artifact Filenames
LINK_FAILURE_MODEL_PATH = MODELS_DIR / "link_failure_model.joblib"
DEVICE_FAILURE_MODEL_PATH = MODELS_DIR / "device_failure_model.joblib"
BLAST_RADIUS_MODEL_PATH = MODELS_DIR / "blast_radius_model.joblib"
ANOMALY_DETECTOR_PATH = MODELS_DIR / "anomaly_detector.joblib"
LINK_SCALER_PATH = MODELS_DIR / "link_scaler.joblib"
DEVICE_SCALER_PATH = MODELS_DIR / "device_scaler.joblib"
METADATA_PATH = MODELS_DIR / "model_metadata.json"

# Generated Dataset Filenames
LINK_DATASET_CSV = DATA_DIR / "link_telemetry.csv"
DEVICE_DATASET_CSV = DATA_DIR / "device_telemetry.csv"

# ==============================================================================
# 2. Network Topology Structure Constants (from Verified 5-Branch Architecture)
# ==============================================================================
BRANCHES: List[str] = [
    "Headquarters",
    "Branch 1 (North)",
    "Branch 2 (South)",
    "Branch 3 (East)",
    "Branch 4 (West)",
]

# Total: 22 Devices
ROUTER_IDS: List[str] = ["HQ-R1", "BR1-R1", "BR2-R1", "BR3-R1", "BR4-R1"]
SWITCH_IDS: List[str] = ["HQ-SW1", "BR1-SW1", "BR2-SW1", "BR3-SW1", "BR4-SW1"]
SERVER_IDS: List[str] = ["HQ-SRV1", "HQ-SRV2"]
PC_IDS: List[str] = [
    "HQ-PC1", "HQ-PC2",
    "BR1-PC1", "BR1-PC2",
    "BR2-PC1", "BR2-PC2",
    "BR3-PC1", "BR3-PC2",
    "BR4-PC1", "BR4-PC2",
]
ALL_DEVICE_IDS: List[str] = ROUTER_IDS + SWITCH_IDS + SERVER_IDS + PC_IDS

# Total: 24 Links
# 7 Core WAN Links
WAN_LINK_IDS: List[str] = [
    "WAN-HQ-BR1",
    "WAN-HQ-BR2",
    "WAN-HQ-BR3",
    "WAN-HQ-BR4",
    "WAN-BR1-BR2",
    "WAN-BR2-BR3",
    "WAN-BR3-BR4",
]

# 5 Distribution Trunk Links
TRUNK_LINK_IDS: List[str] = [
    "LINK-HQ-SW1",
    "LINK-BR1-SW1",
    "LINK-BR2-SW1",
    "LINK-BR3-SW1",
    "LINK-BR4-SW1",
]

# 12 Access Links
ACCESS_LINK_IDS: List[str] = [
    "LINK-HQ-PC1", "LINK-HQ-PC2", "LINK-HQ-SRV1", "LINK-HQ-SRV2",
    "LINK-BR1-PC1", "LINK-BR1-PC2",
    "LINK-BR2-PC1", "LINK-BR2-PC2",
    "LINK-BR3-PC1", "LINK-BR3-PC2",
    "LINK-BR4-PC1", "LINK-BR4-PC2",
]
ALL_LINK_IDS: List[str] = WAN_LINK_IDS + TRUNK_LINK_IDS + ACCESS_LINK_IDS

# Serial Links with 1.544 Mbps (T1) Bandwidth
SERIAL_LINKS: Set[str] = {"WAN-HQ-BR3", "WAN-HQ-BR4", "WAN-BR2-BR3"}

# ==============================================================================
# 3. Telemetry Operating Thresholds & SLA Parameters
# ==============================================================================
THRESHOLDS = {
    "packet_loss_pct": {"normal": 0.5, "warning": 2.0, "critical": 5.0},
    "latency_ms_lan": {"normal": 2.0, "warning": 8.0, "critical": 20.0},
    "latency_ms_wan_fast": {"normal": 15.0, "warning": 40.0, "critical": 80.0},
    "latency_ms_wan_serial": {"normal": 35.0, "warning": 75.0, "critical": 150.0},
    "jitter_ms": {"normal": 2.0, "warning": 6.0, "critical": 12.0},
    "utilization_pct": {"normal": 60.0, "warning": 80.0, "critical": 92.0},
    "error_rate_per_min": {"normal": 0.0, "warning": 5.0, "critical": 20.0},
    "cpu_pct": {"normal": 45.0, "warning": 70.0, "critical": 85.0},
    "mem_pct": {"normal": 55.0, "warning": 75.0, "critical": 90.0},
    "temp_celsius": {"normal": 42.0, "warning": 58.0, "critical": 72.0},
}

# Risk categorization
RISK_LEVEL_LOW = "LOW"
RISK_LEVEL_MEDIUM = "MEDIUM"
RISK_LEVEL_HIGH = "HIGH"

# Device Health States
HEALTH_STATE_NORMAL = 0
HEALTH_STATE_WARNING = 1
HEALTH_STATE_CRITICAL = 2

# ==============================================================================
# 4. Feature Column Definitions
# ==============================================================================
LINK_NUMERICAL_FEATURES: List[str] = [
    "bandwidth_mbps",
    "edge_betweenness",
    "source_degree",
    "target_degree",
    "min_endpoint_degree",
    "is_bridge",
    "alternate_path_exists",
    "alternate_path_hops",
    "redundancy_factor",
    "packet_loss_pct",
    "latency_ms",
    "jitter_ms",
    "utilization_pct",
    "error_rate",
    "queue_depth_pct",
    "congestion_index",
]

DEVICE_NUMERICAL_FEATURES: List[str] = [
    "degree",
    "degree_centrality",
    "betweenness_centrality",
    "closeness_centrality",
    "eigenvector_centrality",
    "is_articulation_point",
    "is_router",
    "is_switch",
    "is_server",
    "blast_radius_potential",
    "cpu_pct",
    "mem_pct",
    "temperature_c",
    "interface_error_count",
    "buffer_utilization_pct",
    "device_stress_score",
]

# Random Seed for Reproducibility
RANDOM_SEED: int = 42
