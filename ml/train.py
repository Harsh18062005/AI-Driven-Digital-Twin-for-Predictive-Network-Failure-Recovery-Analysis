"""Model Training, Validation, and Evaluation Pipeline.

Trains multi-model classifiers and regressors for network failure prediction,
evaluates cross-validated performance, extracts feature importances, and
persists model artifacts for the Network Digital Twin.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root and python/ to sys.path so modules resolve whether executed from root or ml/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
PYTHON_DIR = PROJECT_ROOT / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

import json
from datetime import datetime
from typing import Any, Dict, List, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
)
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

from ml.anomaly_detector import TelemetryAnomalyDetector
from ml.config import (
    ANOMALY_DETECTOR_PATH,
    BLAST_RADIUS_MODEL_PATH,
    DEVICE_DATASET_CSV,
    DEVICE_FAILURE_MODEL_PATH,
    DEVICE_NUMERICAL_FEATURES,
    DEVICE_SCALER_PATH,
    LINK_DATASET_CSV,
    LINK_FAILURE_MODEL_PATH,
    LINK_NUMERICAL_FEATURES,
    LINK_SCALER_PATH,
    METADATA_PATH,
    MODELS_DIR,
    RANDOM_SEED,
)
from ml.telemetry_generator import TelemetryDataGenerator


class NetworkModelTrainer:
    """Trains, benchmarks, and saves machine learning models for the network digital twin."""

    def __init__(self, seed: int = RANDOM_SEED):
        """Initialize trainer with seed and create artifacts directory."""
        self.seed = seed
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        self.metadata: Dict[str, Any] = {
            "trained_at": datetime.now().isoformat(),
            "models": {},
        }

    def load_or_generate_data(
        self,
        samples_per_link: int = 150,
        samples_per_device: int = 150,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Ensure datasets exist, generating high-fidelity synthetic telemetry if needed."""
        generator = TelemetryDataGenerator(seed=self.seed)

        if not LINK_DATASET_CSV.exists() or not DEVICE_DATASET_CSV.exists():
            print("[INFO] Generating synthetic time-series telemetry datasets...")
            generator.save_datasets(
                link_samples=samples_per_link,
                device_samples=samples_per_device,
            )

        link_df = pd.read_csv(LINK_DATASET_CSV)
        dev_df = pd.read_csv(DEVICE_DATASET_CSV)
        print(f"[INFO] Loaded link dataset: {len(link_df)} records.")
        print(f"[INFO] Loaded device dataset: {len(dev_df)} records.")
        return link_df, dev_df

    def train_link_failure_classifier(
        self,
        link_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Train and evaluate the Link Failure Classifier."""
        print("\n" + "=" * 60)
        print(" TRAINING: Link Failure Classifier (RandomForest vs GradientBoosting)")
        print("=" * 60)

        X = link_df[LINK_NUMERICAL_FEATURES].values
        y = link_df["failure_imminent"].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=self.seed, stratify=y
        )

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        joblib.dump(scaler, LINK_SCALER_PATH)

        # Candidate models
        candidates = {
            "RandomForest": RandomForestClassifier(
                n_estimators=120,
                max_depth=12,
                min_samples_split=4,
                random_state=self.seed,
                class_weight="balanced",
            ),
            "GradientBoosting": GradientBoostingClassifier(
                n_estimators=120,
                learning_rate=0.08,
                max_depth=5,
                random_state=self.seed,
            ),
        }

        best_model = None
        best_f1 = -1.0
        best_name = ""
        results = {}

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.seed)

        for name, clf in candidates.items():
            cv_scores = cross_val_score(clf, X_train_scaled, y_train, cv=cv, scoring="f1")
            clf.fit(X_train_scaled, y_train)
            y_pred = clf.predict(X_test_scaled)
            y_prob = clf.predict_proba(X_test_scaled)[:, 1]

            test_f1 = float(f1_score(y_test, y_pred))
            test_acc = float(accuracy_score(y_test, y_pred))
            test_prec = float(precision_score(y_test, y_pred, zero_division=0))
            test_rec = float(recall_score(y_test, y_pred))
            test_roc = float(roc_auc_score(y_test, y_prob))

            results[name] = {
                "cv_f1_mean": float(np.mean(cv_scores)),
                "cv_f1_std": float(np.std(cv_scores)),
                "test_f1": test_f1,
                "test_accuracy": test_acc,
                "test_precision": test_prec,
                "test_recall": test_rec,
                "test_roc_auc": test_roc,
            }
            print(f"  [{name}] 5-Fold CV F1: {np.mean(cv_scores):.4f} (+/- {np.std(cv_scores):.4f}) | Test F1: {test_f1:.4f} | ROC-AUC: {test_roc:.4f}")

            if test_f1 > best_f1:
                best_f1 = test_f1
                best_model = clf
                best_name = name

        # Persist champion model
        joblib.dump(best_model, LINK_FAILURE_MODEL_PATH)
        print(f"[CHAMPION] Selected {best_name} (F1: {best_f1:.4f}) -> {LINK_FAILURE_MODEL_PATH.name}")

        # Extract Feature Importances
        importances = best_model.feature_importances_
        feature_importance_map = {
            feat: float(imp)
            for feat, imp in sorted(
                zip(LINK_NUMERICAL_FEATURES, importances),
                key=lambda x: x[1],
                reverse=True,
            )
        }

        y_pred_best = best_model.predict(X_test_scaled)
        cm = confusion_matrix(y_test, y_pred_best).tolist()

        metadata_entry = {
            "model_type": best_name,
            "artifact": str(LINK_FAILURE_MODEL_PATH.name),
            "features": LINK_NUMERICAL_FEATURES,
            "metrics": results[best_name],
            "confusion_matrix": cm,
            "feature_importance": feature_importance_map,
        }
        self.metadata["models"]["link_failure_classifier"] = metadata_entry
        return metadata_entry

    def train_device_health_classifier(
        self,
        dev_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Train and evaluate the Multi-Class Device Health Classifier."""
        print("\n" + "=" * 60)
        print(" TRAINING: Device Health Classifier (HEALTHY vs WARNING vs CRITICAL)")
        print("=" * 60)

        X = dev_df[DEVICE_NUMERICAL_FEATURES].values
        y = dev_df["health_state"].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=self.seed, stratify=y
        )

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        joblib.dump(scaler, DEVICE_SCALER_PATH)

        clf = RandomForestClassifier(
            n_estimators=120,
            max_depth=10,
            random_state=self.seed,
            class_weight="balanced",
        )

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.seed)
        cv_scores = cross_val_score(clf, X_train_scaled, y_train, cv=cv, scoring="f1_weighted")

        clf.fit(X_train_scaled, y_train)
        y_pred = clf.predict(X_test_scaled)

        test_acc = float(accuracy_score(y_test, y_pred))
        test_f1 = float(f1_score(y_test, y_pred, average="weighted"))
        cm = confusion_matrix(y_test, y_pred).tolist()

        print(f"  5-Fold CV Weighted F1: {np.mean(cv_scores):.4f} (+/- {np.std(cv_scores):.4f})")
        print(f"  Test Accuracy: {test_acc:.4f} | Test Weighted F1: {test_f1:.4f}")

        joblib.dump(clf, DEVICE_FAILURE_MODEL_PATH)
        print(f"[CHAMPION] Device Health Model -> {DEVICE_FAILURE_MODEL_PATH.name}")

        feature_importance_map = {
            feat: float(imp)
            for feat, imp in sorted(
                zip(DEVICE_NUMERICAL_FEATURES, clf.feature_importances_),
                key=lambda x: x[1],
                reverse=True,
            )
        }

        metadata_entry = {
            "model_type": "RandomForestClassifier",
            "artifact": str(DEVICE_FAILURE_MODEL_PATH.name),
            "features": DEVICE_NUMERICAL_FEATURES,
            "classes": ["HEALTHY", "WARNING", "CRITICAL"],
            "metrics": {
                "cv_f1_weighted_mean": float(np.mean(cv_scores)),
                "cv_f1_weighted_std": float(np.std(cv_scores)),
                "test_accuracy": test_acc,
                "test_f1_weighted": test_f1,
            },
            "confusion_matrix": cm,
            "feature_importance": feature_importance_map,
        }
        self.metadata["models"]["device_health_classifier"] = metadata_entry
        return metadata_entry

    def train_blast_radius_regressor(
        self,
        dev_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Train the Blast Radius Impact Regressor."""
        print("\n" + "=" * 60)
        print(" TRAINING: Blast Radius Impact Regressor (Gradient Boosting)")
        print("=" * 60)

        X = dev_df[DEVICE_NUMERICAL_FEATURES].values
        y = dev_df["actual_blast_radius"].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=self.seed
        )

        scaler = joblib.load(DEVICE_SCALER_PATH)
        X_train_scaled = scaler.transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        reg = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.08,
            max_depth=4,
            random_state=self.seed,
        )
        reg.fit(X_train_scaled, y_train)

        y_pred = reg.predict(X_test_scaled)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))

        print(f"  Test MAE: {mae:.4f} nodes | RMSE: {rmse:.4f} nodes | R² Score: {r2:.4f}")

        joblib.dump(reg, BLAST_RADIUS_MODEL_PATH)
        print(f"[CHAMPION] Blast Radius Regressor -> {BLAST_RADIUS_MODEL_PATH.name}")

        metadata_entry = {
            "model_type": "GradientBoostingRegressor",
            "artifact": str(BLAST_RADIUS_MODEL_PATH.name),
            "features": DEVICE_NUMERICAL_FEATURES,
            "metrics": {
                "test_mae": mae,
                "test_rmse": rmse,
                "test_r2": r2,
            },
        }
        self.metadata["models"]["blast_radius_regressor"] = metadata_entry
        return metadata_entry

    def train_anomaly_detector(
        self,
        link_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Fit and persist the Unsupervised Isolation Forest Anomaly Detector."""
        print("\n" + "=" * 60)
        print(" TRAINING: Unsupervised Telemetry Anomaly Detector (Isolation Forest)")
        print("=" * 60)

        detector = TelemetryAnomalyDetector(contamination=0.05, seed=self.seed)
        detector.fit(link_df)
        detector.save(ANOMALY_DETECTOR_PATH)
        print(f"[SAVED] Telemetry Anomaly Detector -> {ANOMALY_DETECTOR_PATH.name}")

        metadata_entry = {
            "model_type": "IsolationForest",
            "artifact": str(ANOMALY_DETECTOR_PATH.name),
            "features": detector.FEATURES,
            "contamination": detector.contamination,
            "baseline_means": detector.feature_means,
            "baseline_stds": detector.feature_stds,
        }
        self.metadata["models"]["anomaly_detector"] = metadata_entry
        return metadata_entry

    def save_metadata(self) -> Path:
        """Persist full training metrics and model metadata to JSON."""
        with open(METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)
        print(f"\n[INFO] Model metadata saved to {METADATA_PATH.name}")
        return METADATA_PATH

    def run_full_pipeline(
        self,
        samples_per_link: int = 150,
        samples_per_device: int = 150,
    ) -> Dict[str, Any]:
        """Execute complete end-to-end data generation, training, and benchmarking pipeline."""
        link_df, dev_df = self.load_or_generate_data(
            samples_per_link=samples_per_link,
            samples_per_device=samples_per_device,
        )

        self.train_link_failure_classifier(link_df)
        self.train_device_health_classifier(dev_df)
        self.train_blast_radius_regressor(dev_df)
        self.train_anomaly_detector(link_df)
        self.save_metadata()

        print("\n" + "=" * 60)
        print(" [SUCCESS] Full Digital Twin ML Training Pipeline Completed!")
        print("=" * 60)
        return self.metadata


if __name__ == "__main__":
    trainer = NetworkModelTrainer()
    trainer.run_full_pipeline()
