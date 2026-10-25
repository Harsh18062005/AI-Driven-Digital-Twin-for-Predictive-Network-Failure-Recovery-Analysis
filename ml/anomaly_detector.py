"""Unsupervised Telemetry Anomaly Detector.

Uses Isolation Forest and robust statistical Z-score dispersion to detect
zero-day telemetry anomalies, abnormal jitter drift, and impending outages
without requiring pre-labeled failure ground truth.
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

from typing import Any, Dict, List, Optional
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ml.config import ANOMALY_DETECTOR_PATH, RANDOM_SEED


class TelemetryAnomalyDetector:
    """Unsupervised anomaly detection sentinel for network digital twin telemetry."""

    FEATURES: List[str] = [
        "packet_loss_pct",
        "latency_ms",
        "jitter_ms",
        "utilization_pct",
        "error_rate",
        "queue_depth_pct",
    ]

    def __init__(self, contamination: float = 0.05, seed: int = RANDOM_SEED):
        """Initialize Isolation Forest anomaly detector."""
        self.contamination = contamination
        self.seed = seed
        self.model = IsolationForest(
            contamination=contamination,
            random_state=seed,
            n_estimators=100,
        )
        self.is_fitted = False
        self.feature_means: Dict[str, float] = {}
        self.feature_stds: Dict[str, float] = {}

    def fit(self, df: pd.DataFrame) -> TelemetryAnomalyDetector:
        """Fit Isolation Forest on baseline healthy telemetry samples.

        Args:
            df: DataFrame containing the training samples.

        Returns:
            Self (fitted instance).
        """
        # Filter for normal/healthy records if label column exists
        if "failure_imminent" in df.columns:
            training_df = df[df["failure_imminent"] == 0]
        else:
            training_df = df

        X = training_df[self.FEATURES].dropna().values
        self.model.fit(X)
        self.is_fitted = True

        # Compute baseline statistical moments for Z-score feature attributions
        for col in self.FEATURES:
            self.feature_means[col] = float(training_df[col].mean())
            std_val = float(training_df[col].std())
            self.feature_stds[col] = std_val if std_val > 1e-6 else 1.0

        return self

    def score_sample(self, telemetry: Dict[str, float]) -> Dict[str, Any]:
        """Evaluate a single telemetry observation for anomalous behavior.

        Args:
            telemetry: Dict mapping feature names to telemetry values.

        Returns:
            Dictionary with anomaly detection results and feature attributions.
        """
        if not self.is_fitted:
            raise RuntimeError("Anomaly detector is not fitted. Call fit() or load() first.")

        # Build feature vector
        vector = []
        for col in self.FEATURES:
            val = float(telemetry.get(col, self.feature_means.get(col, 0.0)))
            vector.append(val)

        X = np.array([vector])
        raw_score = float(self.model.decision_function(X)[0])
        pred = int(self.model.predict(X)[0])  # -1 = anomaly, 1 = normal
        is_anomaly = (pred == -1)

        # Normalize score into [0.0, 1.0] severity scale where 1.0 is most anomalous
        # decision_function typically ranges from ~ -0.3 (highly anomalous) to +0.25 (typical)
        anomaly_confidence = float(np.clip((0.15 - raw_score) / 0.45, 0.0, 1.0))

        # Calculate Z-score deviations to identify which features triggered the anomaly
        deviations = {}
        deviant_features = []
        for col, val in zip(self.FEATURES, vector):
            mean = self.feature_means.get(col, 0.0)
            std = self.feature_stds.get(col, 1.0)
            z = (val - mean) / std
            deviations[col] = round(float(z), 2)
            if abs(z) >= 2.0:
                deviant_features.append({
                    "feature": col,
                    "observed": round(val, 2),
                    "baseline_mean": round(mean, 2),
                    "z_score": round(float(z), 2),
                })

        return {
            "is_anomaly": is_anomaly,
            "anomaly_confidence": round(anomaly_confidence, 4),
            "raw_decision_score": round(raw_score, 4),
            "deviant_features": deviant_features,
            "z_scores": deviations,
        }

    def save(self, path: Optional[Path] = None) -> Path:
        """Serialize fitted model to disk."""
        target_path = path or ANOMALY_DETECTOR_PATH
        target_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "feature_means": self.feature_means,
                "feature_stds": self.feature_stds,
                "contamination": self.contamination,
                "is_fitted": self.is_fitted,
            },
            target_path,
        )
        return target_path

    @classmethod
    def load(cls, path: Optional[Path] = None) -> TelemetryAnomalyDetector:
        """Load fitted model artifact from disk."""
        target_path = path or ANOMALY_DETECTOR_PATH
        if not target_path.exists():
            raise FileNotFoundError(f"Anomaly detector artifact not found: {target_path}")

        payload = joblib.load(target_path)
        detector = cls(contamination=payload.get("contamination", 0.05))
        detector.model = payload["model"]
        detector.feature_means = payload["feature_means"]
        detector.feature_stds = payload["feature_stds"]
        detector.is_fitted = payload["is_fitted"]
        return detector
