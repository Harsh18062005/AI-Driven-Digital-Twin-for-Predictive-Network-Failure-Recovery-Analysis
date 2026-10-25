"""Unit tests for TelemetryAnomalyDetector."""

from __future__ import annotations

import pandas as pd
import pytest
from ml.anomaly_detector import TelemetryAnomalyDetector
from ml.telemetry_generator import TelemetryDataGenerator


@pytest.fixture
def fitted_detector() -> TelemetryAnomalyDetector:
    gen = TelemetryDataGenerator(seed=42)
    df = gen.generate_link_dataset(samples_per_link=10)
    det = TelemetryAnomalyDetector(contamination=0.05, seed=42)
    det.fit(df)
    return det


def test_detector_fit_and_attributes(fitted_detector: TelemetryAnomalyDetector):
    """Verify that detector correctly fits and records feature baseline statistics."""
    assert fitted_detector.is_fitted
    assert len(fitted_detector.feature_means) == len(TelemetryAnomalyDetector.FEATURES)
    assert len(fitted_detector.feature_stds) == len(TelemetryAnomalyDetector.FEATURES)
    assert fitted_detector.feature_means["packet_loss_pct"] >= 0.0


def test_score_nominal_vs_anomalous(fitted_detector: TelemetryAnomalyDetector):
    """Verify that nominal telemetry produces low anomaly score and extreme values trigger alert."""
    nominal_telem = {
        "packet_loss_pct": 0.05,
        "latency_ms": 2.0,
        "jitter_ms": 0.3,
        "utilization_pct": 35.0,
        "error_rate": 0.0,
        "queue_depth_pct": 12.0,
    }
    nom_result = fitted_detector.score_sample(nominal_telem)
    assert not nom_result["is_anomaly"]
    assert nom_result["anomaly_confidence"] < 0.5

    anomalous_telem = {
        "packet_loss_pct": 45.0,
        "latency_ms": 320.0,
        "jitter_ms": 65.0,
        "utilization_pct": 99.5,
        "error_rate": 80.0,
        "queue_depth_pct": 100.0,
    }
    anom_result = fitted_detector.score_sample(anomalous_telem)
    assert anom_result["is_anomaly"]
    assert anom_result["anomaly_confidence"] > 0.6
    assert len(anom_result["deviant_features"]) > 0


def test_detector_serialization(fitted_detector: TelemetryAnomalyDetector, tmp_path):
    """Verify that detector can be saved and loaded accurately."""
    save_file = tmp_path / "test_detector.joblib"
    fitted_detector.save(save_file)
    assert save_file.exists()

    loaded = TelemetryAnomalyDetector.load(save_file)
    assert loaded.is_fitted
    assert loaded.feature_means == fitted_detector.feature_means
