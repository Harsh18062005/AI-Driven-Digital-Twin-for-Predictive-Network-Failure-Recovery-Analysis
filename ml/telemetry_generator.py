"""Synthetic Telemetry and Failure Injection Dataset Generator.

Generates physically realistic time-series network telemetry for all 22 devices
and 24 links across the enterprise digital twin, incorporating baseline diurnal cycles,
congestion spikes, hardware degradation, serial line noise, and failure states.
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

import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from ml.config import (
    ALL_DEVICE_IDS,
    ALL_LINK_IDS,
    DEVICE_DATASET_CSV,
    HEALTH_STATE_CRITICAL,
    HEALTH_STATE_NORMAL,
    HEALTH_STATE_WARNING,
    LINK_DATASET_CSV,
    RANDOM_SEED,
    SERIAL_LINKS,
    WAN_LINK_IDS,
)
from ml.feature_engineering import NetworkFeatureExtractor


class TelemetryDataGenerator:
    """Generates synthetic telemetry datasets labeled with ground-truth failure states."""

    def __init__(
        self,
        extractor: Optional[NetworkFeatureExtractor] = None,
        seed: int = RANDOM_SEED,
    ):
        """Initialize data generator with feature extractor and fixed RNG seed."""
        self.extractor = extractor or NetworkFeatureExtractor()
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def _generate_link_sample(
        self,
        link_id: str,
        is_failure: bool,
        failure_mode: str = "NORMAL",
        hour_of_day: float = 12.0,
    ) -> Dict[str, Any]:
        """Generate a single telemetry sample for a specific link."""
        static = self.extractor.link_static_features[link_id]
        bw = static["bandwidth_mbps"]
        is_serial = link_id in SERIAL_LINKS
        is_wan = static["link_type"] == "WAN"

        # Baseline diurnal multiplier (higher traffic during 09:00 - 18:00)
        diurnal = 0.5 + 0.4 * max(0.0, math.sin((hour_of_day - 6.0) * math.pi / 12.0))

        if not is_failure:
            # Normal operating conditions
            loss = float(self.rng.exponential(scale=0.08))
            loss = min(loss, 0.45)  # Under 0.5% for healthy link

            if is_serial:
                base_lat = 30.0 + 8.0 * diurnal
                lat = float(self.rng.normal(loc=base_lat, scale=3.0))
                jit = float(self.rng.uniform(1.0, 3.5))
            elif is_wan:
                base_lat = 12.0 + 5.0 * diurnal
                lat = float(self.rng.normal(loc=base_lat, scale=1.5))
                jit = float(self.rng.uniform(0.5, 2.0))
            else:
                base_lat = 1.0 + 0.5 * diurnal
                lat = float(self.rng.normal(loc=base_lat, scale=0.3))
                jit = float(self.rng.uniform(0.1, 0.8))

            util = float(self.rng.normal(loc=30.0 + 35.0 * diurnal, scale=7.0))
            util = float(np.clip(util, 5.0, 78.0))
            err = float(self.rng.poisson(lam=0.1 if is_serial else 0.01))
            q_depth = float(np.clip(util * 0.4 + self.rng.normal(0, 3), 1.0, 45.0))
            mode = "NORMAL"

        else:
            # Degraded / Failure operating conditions
            mode = failure_mode if failure_mode != "NORMAL" else self.rng.choice([
                "CONGESTION_COLLAPSE",
                "SERIAL_NOISE",
                "BUFFER_OVERFLOW",
                "LINK_FLAP",
            ])

            if mode == "CONGESTION_COLLAPSE":
                util = float(self.rng.uniform(88.0, 99.8))
                q_depth = float(self.rng.uniform(82.0, 99.0))
                loss = float(self.rng.uniform(4.5, 18.0))
                lat_mult = self.rng.uniform(3.0, 6.0)
                lat = float((45.0 if is_serial else 15.0) * lat_mult)
                jit = float(self.rng.uniform(8.0, 22.0))
                err = float(self.rng.poisson(lam=6))

            elif mode == "SERIAL_NOISE":
                util = float(self.rng.uniform(40.0, 75.0))
                q_depth = float(self.rng.uniform(30.0, 65.0))
                loss = float(self.rng.uniform(6.0, 25.0))
                lat = float(self.rng.uniform(70.0, 180.0) if is_serial else self.rng.uniform(35.0, 95.0))
                jit = float(self.rng.uniform(10.0, 28.0))
                err = float(self.rng.poisson(lam=18))

            elif mode == "BUFFER_OVERFLOW":
                util = float(self.rng.uniform(82.0, 96.0))
                q_depth = float(self.rng.uniform(92.0, 100.0))
                loss = float(self.rng.uniform(8.0, 32.0))
                lat = float(self.rng.uniform(50.0, 140.0))
                jit = float(self.rng.uniform(12.0, 30.0))
                err = float(self.rng.poisson(lam=12))

            else:  # LINK_FLAP
                util = float(self.rng.uniform(20.0, 60.0))
                q_depth = float(self.rng.uniform(50.0, 90.0))
                loss = float(self.rng.uniform(15.0, 60.0))
                lat = float(self.rng.uniform(80.0, 250.0))
                jit = float(self.rng.uniform(18.0, 45.0))
                err = float(self.rng.poisson(lam=28))

        telem = {
            "packet_loss_pct": round(max(0.0, loss), 3),
            "latency_ms": round(max(0.5, lat), 2),
            "jitter_ms": round(max(0.1, jit), 2),
            "utilization_pct": round(util, 2),
            "error_rate": round(max(0.0, err), 1),
            "queue_depth_pct": round(max(0.0, q_depth), 2),
        }

        # Extract full feature vector using the FeatureExtractor
        features = self.extractor.extract_link_features(link_id, telem)
        features["failure_imminent"] = 1 if is_failure else 0
        features["failure_mode"] = mode
        features["hour_of_day"] = round(hour_of_day, 1)

        return features

    def _generate_device_sample(
        self,
        device_id: str,
        health_state: int,
        failure_mode: str = "NORMAL",
        hour_of_day: float = 12.0,
    ) -> Dict[str, Any]:
        """Generate a single telemetry sample for a specific device."""
        static = self.extractor.device_static_features[device_id]
        dev_type = static["device_type"]
        is_router = dev_type == "Router"
        is_switch = dev_type == "Switch"

        # Baseline diurnal multiplier
        diurnal = 0.5 + 0.4 * max(0.0, math.sin((hour_of_day - 6.0) * math.pi / 12.0))

        if health_state == HEALTH_STATE_NORMAL:
            base_cpu = (35.0 if is_router else (25.0 if is_switch else 20.0)) * diurnal
            cpu = float(np.clip(self.rng.normal(loc=base_cpu + 10, scale=6.0), 5.0, 58.0))
            mem = float(np.clip(self.rng.normal(loc=38.0 + 12.0 * diurnal, scale=4.0), 15.0, 62.0))
            temp = float(np.clip(self.rng.normal(loc=38.0 + 5.0 * diurnal, scale=2.0), 32.0, 48.0))
            err = float(self.rng.poisson(lam=0.05))
            buf = float(np.clip(cpu * 0.35 + self.rng.normal(0, 2), 2.0, 40.0))
            mode = "NORMAL"

        elif health_state == HEALTH_STATE_WARNING:
            cpu = float(self.rng.uniform(62.0, 82.0))
            mem = float(self.rng.uniform(68.0, 84.0))
            temp = float(self.rng.uniform(52.0, 66.0))
            err = float(self.rng.poisson(lam=6.0))
            buf = float(self.rng.uniform(55.0, 78.0))
            mode = failure_mode if failure_mode != "NORMAL" else "RESOURCE_WARNING"

        else:  # HEALTH_STATE_CRITICAL
            mode = failure_mode if failure_mode != "NORMAL" else self.rng.choice([
                "CPU_SATURATION",
                "MEMORY_LEAK",
                "THERMAL_SPIKE",
                "INTERFACE_OVERRUN",
            ])

            if mode == "CPU_SATURATION":
                cpu = float(self.rng.uniform(88.0, 99.5))
                mem = float(self.rng.uniform(70.0, 92.0))
                temp = float(self.rng.uniform(62.0, 78.0))
                err = float(self.rng.poisson(lam=18.0))
                buf = float(self.rng.uniform(80.0, 98.0))

            elif mode == "MEMORY_LEAK":
                cpu = float(self.rng.uniform(65.0, 88.0))
                mem = float(self.rng.uniform(90.0, 99.8))
                temp = float(self.rng.uniform(55.0, 70.0))
                err = float(self.rng.poisson(lam=12.0))
                buf = float(self.rng.uniform(85.0, 99.0))

            elif mode == "THERMAL_SPIKE":
                cpu = float(self.rng.uniform(75.0, 96.0))
                mem = float(self.rng.uniform(60.0, 85.0))
                temp = float(self.rng.uniform(72.0, 86.0))
                err = float(self.rng.poisson(lam=22.0))
                buf = float(self.rng.uniform(70.0, 95.0))

            else:  # INTERFACE_OVERRUN
                cpu = float(self.rng.uniform(82.0, 95.0))
                mem = float(self.rng.uniform(75.0, 92.0))
                temp = float(self.rng.uniform(58.0, 74.0))
                err = float(self.rng.poisson(lam=45.0))
                buf = float(self.rng.uniform(90.0, 100.0))

        telem = {
            "cpu_pct": round(cpu, 2),
            "mem_pct": round(mem, 2),
            "temperature_c": round(temp, 2),
            "interface_error_count": round(max(0.0, err), 1),
            "buffer_utilization_pct": round(buf, 2),
        }

        features = self.extractor.extract_device_features(device_id, telem)
        features["health_state"] = health_state
        features["is_critical"] = 1 if health_state == HEALTH_STATE_CRITICAL else 0
        features["failure_mode"] = mode
        features["hour_of_day"] = round(hour_of_day, 1)

        # Target for Blast Radius Regressor: actual disconnected nodes
        # If normal, actual blast radius impact is 0; if critical, it unleashes potential
        if health_state == HEALTH_STATE_CRITICAL:
            features["actual_blast_radius"] = features["blast_radius_potential"]
        elif health_state == HEALTH_STATE_WARNING:
            features["actual_blast_radius"] = int(round(features["blast_radius_potential"] * 0.3))
        else:
            features["actual_blast_radius"] = 0

        return features

    def generate_link_dataset(
        self,
        samples_per_link: int = 120,
        failure_ratio: float = 0.20,
    ) -> pd.DataFrame:
        """Generate a balanced synthetic time-series telemetry dataset for all 24 links.

        Args:
            samples_per_link: Number of historical readings to generate per link.
            failure_ratio: Proportion of samples simulating degraded/failing states.

        Returns:
            Pandas DataFrame containing training samples.
        """
        records = []
        for link_id in sorted(self.extractor.link_static_features.keys()):
            for s in range(samples_per_link):
                # Cycle through 24-hour day
                hour = (s * 0.2) % 24.0
                is_fail = bool(self.rng.random() < failure_ratio)
                records.append(self._generate_link_sample(link_id, is_fail, hour_of_day=hour))

        df = pd.DataFrame(records)
        return df

    def generate_device_dataset(
        self,
        samples_per_device: int = 120,
        warning_ratio: float = 0.15,
        critical_ratio: float = 0.10,
    ) -> pd.DataFrame:
        """Generate a balanced synthetic time-series telemetry dataset for all 22 devices.

        Args:
            samples_per_device: Number of historical readings to generate per device.
            warning_ratio: Proportion of samples with WARNING health state.
            critical_ratio: Proportion of samples with CRITICAL health state.

        Returns:
            Pandas DataFrame containing training samples.
        """
        records = []
        for dev_id in sorted(self.extractor.device_static_features.keys()):
            for s in range(samples_per_device):
                hour = (s * 0.2) % 24.0
                roll = self.rng.random()
                if roll < critical_ratio:
                    state = HEALTH_STATE_CRITICAL
                elif roll < (critical_ratio + warning_ratio):
                    state = HEALTH_STATE_WARNING
                else:
                    state = HEALTH_STATE_NORMAL

                records.append(self._generate_device_sample(dev_id, state, hour_of_day=hour))

        df = pd.DataFrame(records)
        return df

    def save_datasets(
        self,
        link_samples: int = 120,
        device_samples: int = 120,
    ) -> Tuple[Path, Path]:
        """Generate and persist link and device CSV datasets to ml/data/.

        Returns:
            Tuple of (link_dataset_path, device_dataset_path).
        """
        LINK_DATASET_CSV.parent.mkdir(parents=True, exist_ok=True)
        
        link_df = self.generate_link_dataset(samples_per_link=link_samples)
        link_df.to_csv(LINK_DATASET_CSV, index=False)

        dev_df = self.generate_device_dataset(samples_per_device=device_samples)
        dev_df.to_csv(DEVICE_DATASET_CSV, index=False)

        return LINK_DATASET_CSV, DEVICE_DATASET_CSV
