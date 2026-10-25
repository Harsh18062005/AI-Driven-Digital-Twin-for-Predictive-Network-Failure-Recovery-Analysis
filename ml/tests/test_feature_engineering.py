"""Unit tests for NetworkFeatureExtractor."""

from __future__ import annotations

import pytest
from ml.feature_engineering import NetworkFeatureExtractor


@pytest.fixture
def extractor() -> NetworkFeatureExtractor:
    return NetworkFeatureExtractor()


def test_extractor_counts(extractor: NetworkFeatureExtractor):
    """Verify that all 22 devices and 24 links are indexed."""
    assert len(extractor.device_static_features) == 22
    assert len(extractor.link_static_features) == 24


def test_link_bridge_attributes(extractor: NetworkFeatureExtractor):
    """Verify bridge categorization: leaf access links are bridges, redundant WANs are not."""
    # Redundant WAN link WAN-HQ-BR1 has alternate paths through BR2
    wan_hq_br1 = extractor.link_static_features["WAN-HQ-BR1"]
    assert wan_hq_br1["is_bridge"] == 0
    assert wan_hq_br1["alternate_path_exists"] == 1
    assert wan_hq_br1["alternate_path_hops"] >= 2

    # Leaf access link to PC is a topological bridge
    access_pc1 = extractor.link_static_features["LINK-BR1-PC1"]
    assert access_pc1["is_bridge"] == 1
    assert access_pc1["alternate_path_exists"] == 0


def test_node_centrality_attributes(extractor: NetworkFeatureExtractor):
    """Verify node centralities and articulation points."""
    hq_r1 = extractor.device_static_features["HQ-R1"]
    assert hq_r1["is_router"] == 1
    assert hq_r1["is_articulation_point"] == 1
    assert hq_r1["degree"] == 5
    assert hq_r1["betweenness_centrality"] > 0.0

    pc1 = extractor.device_static_features["HQ-PC1"]
    assert pc1["is_pc"] == 1
    assert pc1["is_router"] == 0
    assert pc1["degree"] == 1
    assert pc1["betweenness_centrality"] == 0.0


def test_extract_link_nominal_and_custom(extractor: NetworkFeatureExtractor):
    """Test extracting link features with nominal and custom telemetry."""
    # Nominal telemetry
    nom = extractor.extract_link_features("WAN-HQ-BR1")
    assert nom["packet_loss_pct"] == 0.0
    assert nom["congestion_index"] < 0.3
    assert nom["link_health_index"] > 90.0

    # Stressed telemetry
    stressed = extractor.extract_link_features(
        "WAN-HQ-BR1",
        telemetry={
            "packet_loss_pct": 12.0,
            "latency_ms": 110.0,
            "jitter_ms": 25.0,
            "utilization_pct": 98.0,
            "error_rate": 15.0,
            "queue_depth_pct": 95.0,
        },
    )
    assert stressed["packet_loss_pct"] == 12.0
    assert stressed["congestion_index"] > 0.8
    assert stressed["link_health_index"] < 20.0


def test_extract_device_nominal_and_custom(extractor: NetworkFeatureExtractor):
    """Test extracting device features with nominal and custom telemetry."""
    nom = extractor.extract_device_features("HQ-R1")
    assert nom["cpu_pct"] == 25.0
    assert nom["device_stress_score"] < 0.35
    assert nom["device_health_index"] > 65.0

    stressed = extractor.extract_device_features(
        "HQ-R1",
        telemetry={
            "cpu_pct": 96.0,
            "mem_pct": 94.0,
            "temperature_c": 78.0,
            "interface_error_count": 35.0,
            "buffer_utilization_pct": 92.0,
        },
    )
    assert stressed["cpu_pct"] == 96.0
    assert stressed["device_stress_score"] > 0.80
    assert stressed["device_health_index"] < 25.0


def test_invalid_target_raises_key_error(extractor: NetworkFeatureExtractor):
    """Extracting features for an invalid ID must raise KeyError."""
    with pytest.raises(KeyError):
        extractor.extract_link_features("NON-EXISTENT-LINK")

    with pytest.raises(KeyError):
        extractor.extract_device_features("NON-EXISTENT-DEV")
