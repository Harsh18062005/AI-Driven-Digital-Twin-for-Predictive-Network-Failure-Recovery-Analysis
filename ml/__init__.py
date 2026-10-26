"""AI-Driven Network Digital Twin - Machine Learning & Failure Recovery Module.

Provides predictive failure modeling, graph-theoretic feature extraction,
unsupervised anomaly detection, and automated self-healing recovery recommendations
for enterprise network digital twins.
"""

from ml.config import *
from ml.feature_engineering import NetworkFeatureExtractor
from ml.telemetry_generator import TelemetryDataGenerator
from ml.predictor import FailurePredictor
from ml.anomaly_detector import TelemetryAnomalyDetector
from ml.recovery_engine import PrescriptiveRecoveryEngine
from ml.digital_twin import NetworkDigitalTwin

__version__ = "1.0.0"

__all__ = [
    "NetworkFeatureExtractor",
    "TelemetryDataGenerator",
    "FailurePredictor",
    "TelemetryAnomalyDetector",
    "PrescriptiveRecoveryEngine",
    "NetworkDigitalTwin",
]
