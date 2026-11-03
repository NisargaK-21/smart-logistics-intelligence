"""Train and evaluate an experimental classifier against synthetic weather-risk labels.

The labels are generated from the existing deterministic weather rules, not from
observed road disruptions. Metrics therefore measure rule imitation only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.risk_model_features import (
    WEATHER_FEATURE_COLUMNS,
    prepare_weather_features,
)
from ml.weather_risk_baseline import calculate_weather_risk

DEFAULT_DATASET = ROOT / "ml" / "data" / "processed" / "weather_features.csv"
DEFAULT_REPORT = ROOT / "ml" / "data" / "processed" / "weather_risk_model_evaluation.json"
DEFAULT_ARTIFACT = ROOT / "ml" / "models" / "weather_risk_logistic_regression.joblib"
CLASS_LABELS = ("LOW", "MEDIUM", "HIGH")
SYNTHETIC_LABEL_PROVENANCE = (
    "synthetic_heuristic: generated per row by calculate_weather_risk from the "
    "same five weather features; not an observed disruption outcome"
)

# Set before training: require at least 20 held-out examples per class, macro-F1
# >= 0.80, accuracy >= 0.80, and a 0.10 macro-F1 gain over a majority classifier.
ACCEPTANCE_CRITERIA = {
    "minimum_test_support_per_class": 20,
    "minimum_macro_f1": 0.80,
    "minimum_accuracy": 0.80,
    "minimum_macro_f1_improvement_over_majority": 0.10,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def load_weather_dataset(path: Path) -> tuple[pd.DataFrame, pd.Series, dict[str, Any]]:
    """Load and validate weather rows before generating disclosed synthetic labels."""
    if not path.is_file():
        raise FileNotFoundError(f"Weather feature dataset does not exist: {path}")
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ValueError(f"Could not read weather feature dataset '{path}': {error}") from error

    if frame.empty:
        raise ValueError("Weather feature dataset contains no rows.")

    required_columns = {"time", *WEATHER_FEATURE_COLUMNS}
    missing_columns = sorted(required_columns - set(frame.columns))
    if missing_columns:
        raise ValueError(
            "Weather dataset is missing required columns: "
            + ", ".join(missing_columns)
        )

    timestamps = pd.to_datetime(
        frame["time"], format="mixed", errors="coerce", utc=True
    )
    if timestamps.isna().any():
        invalid_rows = int(timestamps.isna().sum())
        raise ValueError(
            f"Weather dataset contains {invalid_rows} missing or invalid timestamps."
        )
    frame = frame.copy()
    frame["time"] = timestamps

    # A timestamp occurs once per station in the real dataset. Those cross-station
    # repeats are valid and must stay in the same chronological split.
    if "location_id" in frame.columns and frame.duplicated(["location_id", "time"]).any():
        raise ValueError("Weather dataset contains duplicate location/time records.")

    features = prepare_weather_features(frame, allow_missing=True)

    valid_rows = features.notna().all(axis=1)
    features = features.loc[valid_rows].reset_index(drop=True)
    times = frame.loc[valid_rows, "time"].reset_index(drop=True)
    if features.empty:
        raise ValueError(
            "Weather dataset has no rows with all required feature values."
        )

    labels = pd.Series(
        [
            calculate_weather_risk(row)["risk_level"]
            for row in features.to_dict(orient="records")
        ],
        name="synthetic_label",
    )
    _validate_synthetic_labels(labels, expected_rows=len(features))

    labeled = features.copy()
    labeled["time"] = times
    labeled["synthetic_label"] = labels
    labeled["label_provenance"] = SYNTHETIC_LABEL_PROVENANCE
    provenance = {
        "source_path": _display_path(path),
        "source_sha256": _sha256(path),
        "source_rows": int(len(frame)),
        "labeled_rows": int(len(labeled)),
        "rows_dropped_for_missing_features": int(len(frame) - len(labeled)),
        "time_start_utc": times.min().isoformat(),
        "time_end_utc": times.max().isoformat(),
        "label_provenance": SYNTHETIC_LABEL_PROVENANCE,
    }
    return labeled, labels, provenance


def _validate_synthetic_labels(labels: pd.Series, *, expected_rows: int) -> None:
    """Ensure every retained feature row received one supported heuristic label."""
    if len(labels) != expected_rows:
        raise ValueError(
            "Synthetic risk labels do not match the number of retained feature rows."
        )
    if labels.empty:
        raise ValueError("Weather dataset produced no synthetic risk labels.")
    if labels.isna().any():
        raise ValueError("Synthetic risk labels contain missing values.")
    invalid_labels = sorted(set(labels.unique()) - set(CLASS_LABELS))
    if invalid_labels:
        raise ValueError(
            "Heuristic label generation produced unsupported risk labels: "
            + ", ".join(map(str, invalid_labels))
        )


def _metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, Any]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=CLASS_LABELS, average="macro", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=CLASS_LABELS).tolist(),
    }


def _chronological_split(
    frame: pd.DataFrame, test_size: float
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    if not 0 < test_size < 1:
        raise ValueError("test_size must be greater than 0 and less than 1.")
    if frame.empty:
        raise ValueError("Cannot create a chronological split from an empty dataset.")
    if "time" not in frame.columns:
        raise ValueError("Chronological split requires a 'time' column.")

    timestamps = pd.to_datetime(
        frame["time"], format="mixed", errors="coerce", utc=True
    )
    if timestamps.isna().any():
        raise ValueError("Chronological split requires valid, non-missing timestamps.")
    frame = frame.copy()
    frame["time"] = timestamps

    unique_times = pd.Index(timestamps.drop_duplicates()).sort_values()
    if len(unique_times) < 2:
        raise ValueError("At least two distinct timestamps are required for a chronological split.")
    cutoff_index = min(max(int(len(unique_times) * (1 - test_size)), 1), len(unique_times) - 1)
    cutoff = unique_times[cutoff_index]
    train = frame.loc[frame["time"] < cutoff]
    test = frame.loc[frame["time"] >= cutoff]
    if train.empty or test.empty:
        raise ValueError("Chronological split produced an empty train or test set.")
    if train["time"].max() >= test["time"].min():
        raise ValueError("Chronological split has overlapping or out-of-order timestamps.")
    return train, test, cutoff.isoformat()


def _class_counts(labels: pd.Series) -> dict[str, int]:
    counts = labels.value_counts()
    return {label: int(counts.get(label, 0)) for label in CLASS_LABELS}


def train_and_evaluate(
    dataset_path: Path = DEFAULT_DATASET,
    report_path: Path = DEFAULT_REPORT,
    artifact_path: Path = DEFAULT_ARTIFACT,
    *,
    random_seed: int = 42,
    test_size: float = 0.20,
) -> dict[str, Any]:
    """Run the predeclared temporal evaluation and save a non-production artifact."""
    dataset_path = Path(dataset_path)
    report_path = Path(report_path)
    artifact_path = Path(artifact_path)
    labeled, labels, provenance = load_weather_dataset(dataset_path)
    train, test, cutoff = _chronological_split(labeled, test_size)
    y_train = train["synthetic_label"]
    y_test = test["synthetic_label"]

    missing_train_classes = sorted(set(CLASS_LABELS) - set(y_train.unique()))
    if missing_train_classes:
        raise ValueError(
            "Training split is missing risk classes: " + ", ".join(missing_train_classes)
        )

    features_train = prepare_weather_features(train, allow_missing=False)
    features_test = prepare_weather_features(test, allow_missing=False)
    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=random_seed,
                ),
            ),
        ]
    )
    model.fit(features_train, y_train)
    model_predictions = model.predict(features_test)

    majority = DummyClassifier(strategy="most_frequent")
    majority.fit(features_train, y_train)
    majority_predictions = majority.predict(features_test)

    rule_predictions = np.asarray(
        [
            calculate_weather_risk(row)["risk_level"]
            for row in features_test.to_dict(orient="records")
        ]
    )
    class_distribution = {
        "all": _class_counts(labels),
        "train": _class_counts(y_train),
        "test": _class_counts(y_test),
    }
    metrics = {
        "logistic_regression": _metrics(y_test, model_predictions),
        "majority_class_baseline": _metrics(y_test, majority_predictions),
        "deterministic_weather_rule_baseline": _metrics(y_test, rule_predictions),
    }

    test_counts = class_distribution["test"]
    adequate_test_support = all(
        test_counts[label] >= ACCEPTANCE_CRITERIA["minimum_test_support_per_class"]
        for label in CLASS_LABELS
    )
    model_metrics = metrics["logistic_regression"]
    majority_metrics = metrics["majority_class_baseline"]
    acceptance = {
        "test_support_adequate": adequate_test_support,
        "macro_f1_threshold_met": model_metrics["macro_f1"] >= ACCEPTANCE_CRITERIA["minimum_macro_f1"],
        "accuracy_threshold_met": model_metrics["accuracy"] >= ACCEPTANCE_CRITERIA["minimum_accuracy"],
        "majority_baseline_improvement_met": (
            model_metrics["macro_f1"] - majority_metrics["macro_f1"]
            >= ACCEPTANCE_CRITERIA["minimum_macro_f1_improvement_over_majority"]
        ),
    }
    acceptance["experimental_criteria_met"] = all(acceptance.values())
    inadequate_test_classes = [
        label
        for label in CLASS_LABELS
        if test_counts[label] < ACCEPTANCE_CRITERIA["minimum_test_support_per_class"]
    ]

    classifier = model.named_steps["classifier"]
    coefficients = [
        {
            "class": class_label,
            "feature": feature,
            "coefficient": float(coefficient),
            "absolute_coefficient": float(abs(coefficient)),
        }
        for class_label, row in zip(classifier.classes_, classifier.coef_)
        for feature, coefficient in zip(WEATHER_FEATURE_COLUMNS, row)
    ]
    report: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "weather-risk classification, not road-disruption prediction",
        "real_world_predictive_evidence": False,
        "production_activation_allowed": False,
        "evaluation_suitable_for_real_world_claims": False,
        "evaluation_suitability_reason": (
            "Labels are generated from the same deterministic rules being approximated; "
            "the held-out split also has insufficient support for: "
            + (", ".join(inadequate_test_classes) if inadequate_test_classes else "none")
        ),
        "data_provenance": provenance,
        "label_provenance": {
            "type": "synthetic_heuristic",
            "description": SYNTHETIC_LABEL_PROVENANCE,
            "generation": "calculate_weather_risk(features)['risk_level'] for every row",
            "per_row_marker": "label_provenance",
        },
        "feature_columns": list(WEATHER_FEATURE_COLUMNS),
        "evaluation_protocol": {
            "split": "chronological by unique observation timestamp; earlier rows train, later rows test",
            "test_size_fraction": test_size,
            "cutoff_utc_inclusive_for_test": cutoff,
            "random_seed": random_seed,
            "model": "StandardScaler + median SimpleImputer + class-weighted LogisticRegression",
            "comparison_baselines": [
                "most-frequent training class DummyClassifier",
                "deterministic weather rules that generated the synthetic labels",
            ],
            "limitations": [
                "Rows are repeated hourly observations from a small set of weather locations.",
                "Heuristic labels are not observed disaster or road-disruption outcomes.",
                "The deterministic rule baseline is an oracle for these generated labels.",
                "Temporal evaluation covers known locations at later times, not unseen regions.",
                (
                    "Held-out classes below the predeclared minimum support: "
                    + (", ".join(inadequate_test_classes) if inadequate_test_classes else "none")
                    + "."
                ),
            ],
        },
        "acceptance_criteria": {
            **ACCEPTANCE_CRITERIA,
            **acceptance,
            "production_acceptance": False,
            "production_acceptance_reason": "Real-world segment-level disruption labels and validation are absent.",
        },
        "class_distribution": class_distribution,
        "split_sizes": {"train": int(len(train)), "test": int(len(test))},
        "metrics": metrics,
        "coefficients": coefficients,
        "versions": {
            "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "artifact": {
            "path": _display_path(artifact_path),
            "saved": False,
            "production_eligible": False,
        },
    }

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_payload = {
        "pipeline": model,
        "metadata": {
            "feature_columns": list(WEATHER_FEATURE_COLUMNS),
            "class_labels": list(CLASS_LABELS),
            "label_provenance": report["label_provenance"],
            "random_seed": random_seed,
            "acceptance_criteria": report["acceptance_criteria"],
            "data_provenance": report["data_provenance"],
            "evaluation": {
                "test_class_distribution": class_distribution["test"],
                "metrics": metrics,
            },
            "production_eligible": False,
            "task": report["task"],
        },
    }
    try:
        with artifact_path.open("xb") as handle:
            joblib.dump(artifact_payload, handle)
        report["artifact"]["saved"] = True
    except FileExistsError:
        report["artifact"]["not_saved_reason"] = "Artifact already exists and was not overwritten."

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.20)
    args = parser.parse_args()
    report = train_and_evaluate(
        args.dataset,
        args.report,
        args.artifact,
        random_seed=args.seed,
        test_size=args.test_size,
    )
    print(json.dumps({
        "report": str(args.report),
        "artifact": report["artifact"],
        "class_distribution": report["class_distribution"],
        "split_sizes": report["split_sizes"],
        "metrics": report["metrics"],
        "acceptance": report["acceptance_criteria"],
        "production_activation_allowed": report["production_activation_allowed"],
    }, indent=2))


if __name__ == "__main__":
    main()
