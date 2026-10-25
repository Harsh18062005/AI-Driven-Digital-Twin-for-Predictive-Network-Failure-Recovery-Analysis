"""Unit tests for TelemetryDataGenerator."""

from __future__ import annotations

import pytest
from ml.config import DEVICE_NUMERICAL_FEATURES, LINK_NUMERICAL_FEATURES
from ml.telemetry_generator import TelemetryDataGenerator


@pytest.fixture
def generator() -> TelemetryDataGenerator:
    return TelemetryDataGenerator(seed=42)


def test_generate_link_dataset_structure(generator: TelemetryDataGenerator):
    """Verify that generated link dataset has expected columns and non-null values."""
    df = generator.generate_link_dataset(samples_per_link=5, failure_ratio=0.2)
    # 24 links * 5 samples = 120 rows
    assert len(df) == 120

    for col in LINK_NUMERICAL_FEATURES:
        assert col in df.columns
        assert not df[col].isnull().any()

    assert "failure_imminent" in df.columns
    assert set(df["failure_imminent"].unique()).issubset({0, 1})


def test_generate_device_dataset_structure(generator: TelemetryDataGenerator):
    """Verify that generated device dataset has expected columns and valid health states."""
    df = generator.generate_device_dataset(samples_per_device=5, warning_ratio=0.2, critical_ratio=0.2)
    # 22 devices * 5 samples = 110 rows
    assert len(df) == 110

    for col in DEVICE_NUMERICAL_FEATURES:
        assert col in df.columns
        assert not df[col].isnull().any()

    assert "health_state" in df.columns
    assert set(df["health_state"].unique()).issubset({0, 1, 2})


def test_telemetry_physical_ranges(generator: TelemetryDataGenerator):
    """Verify that simulated measurements obey physical boundaries."""
    link_df = generator.generate_link_dataset(samples_per_link=10)
    assert (link_df["packet_loss_pct"] >= 0.0).all()
    assert (link_df["packet_loss_pct"] <= 100.0).all()
    assert (link_df["latency_ms"] > 0.0).all()
    assert (link_df["utilization_pct"] >= 0.0).all()
    assert (link_df["utilization_pct"] <= 100.0).all()

    dev_df = generator.generate_device_dataset(samples_per_device=10)
    assert (dev_df["cpu_pct"] >= 0.0).all()
    assert (dev_df["cpu_pct"] <= 100.0).all()
    assert (dev_df["mem_pct"] >= 0.0).all()
    assert (dev_df["mem_pct"] <= 100.0).all()
    assert (dev_df["temperature_c"] >= 20.0).all()
