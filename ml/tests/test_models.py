"""Unit tests for trained model artifacts and performance metadata."""

from __future__ import annotations

import json
import joblib
import pytest
from ml.config import (
    ANOMALY_DETECTOR_PATH,
    BLAST_RADIUS_MODEL_PATH,
    DEVICE_FAILURE_MODEL_PATH,
    DEVICE_SCALER_PATH,
    LINK_FAILURE_MODEL_PATH,
    LINK_SCALER_PATH,
    METADATA_PATH,
)


def test_model_artifacts_exist():
    """Verify that all champion model artifacts and scalers exist on disk."""
    assert LINK_FAILURE_MODEL_PATH.exists()
    assert LINK_SCALER_PATH.exists()
    assert DEVICE_FAILURE_MODEL_PATH.exists()
    assert DEVICE_SCALER_PATH.exists()
    assert BLAST_RADIUS_MODEL_PATH.exists()
    assert ANOMALY_DETECTOR_PATH.exists()
    assert METADATA_PATH.exists()


def test_metadata_contents():
    """Verify that model_metadata.json contains metrics for all models."""
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert "trained_at" in meta
    models = meta["models"]
    assert "link_failure_classifier" in models
    assert "device_health_classifier" in models
    assert "blast_radius_regressor" in models
    assert "anomaly_detector" in models

    # Check metrics recorded
    link_meta = models["link_failure_classifier"]
    assert link_meta["metrics"]["test_f1"] >= 0.85
    assert link_meta["metrics"]["test_roc_auc"] >= 0.90


def test_link_model_inference():
    """Verify loading and predicting on sample feature vector with link model."""
    clf = joblib.load(LINK_FAILURE_MODEL_PATH)
    scaler = joblib.load(LINK_SCALER_PATH)

    # Dummy vector of 16 features
    sample_vec = [[1000.0, 0.05, 5, 3, 3, 0, 1, 2, 2, 0.0, 2.0, 0.5, 35.0, 0.0, 10.0, 0.15]]
    sample_scaled = scaler.transform(sample_vec)
    prob = clf.predict_proba(sample_scaled)[0]

    assert len(prob) == 2
    assert abs(sum(prob) - 1.0) < 1e-5
