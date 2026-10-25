"""Unit tests for FailurePredictor."""

from __future__ import annotations

import pytest
from ml.config import RISK_LEVEL_HIGH, RISK_LEVEL_LOW
from ml.predictor import FailurePredictor


@pytest.fixture
def predictor() -> FailurePredictor:
    return FailurePredictor()


def test_predict_link_nominal(predictor: FailurePredictor):
    """Predicting on nominal link returns LOW risk and healthy status."""
    res = predictor.predict_link("WAN-HQ-BR1")
    assert res["link_id"] == "WAN-HQ-BR1"
    assert res["risk_level"] == RISK_LEVEL_LOW
    assert not res["failure_predicted"]
    assert res["health_score"] >= 80.0
    assert res["failure_probability"] < 0.35


def test_predict_link_critical(predictor: FailurePredictor):
    """Predicting on link with severe telemetry returns HIGH risk and risk factors."""
    bad_telem = {
        "packet_loss_pct": 28.0,
        "latency_ms": 180.0,
        "jitter_ms": 32.0,
        "utilization_pct": 98.0,
        "error_rate": 25.0,
        "queue_depth_pct": 99.0,
    }
    res = predictor.predict_link("WAN-HQ-BR1", telemetry=bad_telem)
    assert res["risk_level"] == RISK_LEVEL_HIGH
    assert res["failure_predicted"]
    assert res["health_score"] < 40.0
    assert len(res["risk_factors"]) >= 2


def test_predict_device_nominal(predictor: FailurePredictor):
    """Predicting on nominal device returns HEALTHY state."""
    res = predictor.predict_device("HQ-R1")
    assert res["device_id"] == "HQ-R1"
    assert res["health_state"] == "HEALTHY"
    assert res["health_score"] >= 80.0
    assert res["state_probabilities"]["HEALTHY"] >= 0.70


def test_predict_device_overloaded(predictor: FailurePredictor):
    """Predicting on device with extreme CPU/mem returns WARNING or CRITICAL."""
    stress_telem = {
        "cpu_pct": 98.0,
        "mem_pct": 96.0,
        "temperature_c": 79.0,
        "interface_error_count": 40.0,
        "buffer_utilization_pct": 95.0,
    }
    res = predictor.predict_device("HQ-R1", telemetry=stress_telem)
    assert res["health_state"] in ("WARNING", "CRITICAL")
    assert res["risk_level"] in ("MEDIUM", "HIGH")
    assert len(res["risk_factors"]) > 0


def test_predict_all_links_and_devices(predictor: FailurePredictor):
    """Batch prediction must cover all 24 links and 22 devices."""
    links = predictor.predict_all_links()
    devices = predictor.predict_all_devices()

    assert len(links) == 24
    assert len(devices) == 22


def test_get_network_risk_summary(predictor: FailurePredictor):
    """Verify aggregated enterprise risk summary KPIs."""
    summary = predictor.get_network_risk_summary()

    assert "overall_network_health_score" in summary
    assert 0.0 <= summary["overall_network_health_score"] <= 100.0
    assert summary["link_counts"]["total"] == 24
    assert summary["device_counts"]["total"] == 22
    assert len(summary["top_vulnerable_links"]) <= 3
    assert len(summary["top_vulnerable_devices"]) <= 3
