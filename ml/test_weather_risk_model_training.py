from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import pytest

pytest.importorskip("sklearn")

from ml.risk_model_features import WEATHER_FEATURE_COLUMNS, prepare_weather_features
from ml.scripts.train_weather_risk_model import (
    CLASS_LABELS,
    train_and_evaluate,
)
from ml.risk_assessment import _sanitize_weather_payload
from ml.weather_risk_baseline import calculate_weather_risk


def _weather_rows(count: int = 120) -> pd.DataFrame:
    patterns = [
        {
            "precipitation_mm": 0.0,
            "precipitation_sum_3h_mm": 0.0,
            "precipitation_sum_6h_mm": 0.0,
            "precipitation_sum_24h_mm": 0.0,
            "wind_speed_kmh": 5.0,
        },
        {
            "precipitation_mm": 12.0,
            "precipitation_sum_3h_mm": 30.0,
            "precipitation_sum_6h_mm": 45.0,
            "precipitation_sum_24h_mm": 90.0,
            "wind_speed_kmh": 20.0,
        },
        {
            "precipitation_mm": 25.0,
            "precipitation_sum_3h_mm": 60.0,
            "precipitation_sum_6h_mm": 100.0,
            "precipitation_sum_24h_mm": 180.0,
            "wind_speed_kmh": 65.0,
        },
    ]
    return pd.DataFrame([
        {
            "time": pd.Timestamp("2022-01-01", tz="UTC") + pd.Timedelta(hours=index),
            **patterns[index % len(patterns)],
        }
        for index in range(count)
    ])


def test_feature_schema_matches_weather_baseline_and_order():
    features = prepare_weather_features({
        "wind_speed_kmh": 5,
        "precipitation_sum_24h_mm": 0,
        "precipitation_sum_6h_mm": 0,
        "precipitation_sum_3h_mm": 0,
        "precipitation_mm": 0,
        "ignored_extra_feature": 12,
    })
    assert tuple(features.columns) == WEATHER_FEATURE_COLUMNS
    assert calculate_weather_risk(features.iloc[0].to_dict())["risk_level"] == "LOW"
    assert tuple(_sanitize_weather_payload(features.iloc[0].to_dict())) == WEATHER_FEATURE_COLUMNS


def test_training_is_reproducible_and_report_has_required_metrics(tmp_path: Path):
    dataset_path = tmp_path / "weather.csv"
    _weather_rows().to_csv(dataset_path, index=False)
    first = train_and_evaluate(
        dataset_path,
        tmp_path / "first-report.json",
        tmp_path / "first-model.joblib",
        random_seed=17,
    )
    second = train_and_evaluate(
        dataset_path,
        tmp_path / "second-report.json",
        tmp_path / "second-model.joblib",
        random_seed=17,
    )

    assert first["feature_columns"] == list(WEATHER_FEATURE_COLUMNS)
    assert first["class_distribution"] == second["class_distribution"]
    assert first["split_sizes"] == second["split_sizes"]
    assert first["metrics"] == second["metrics"]
    assert first["coefficients"] == second["coefficients"]
    assert first["artifact"]["saved"] is True
    assert first["production_activation_allowed"] is False
    assert first["label_provenance"]["type"] == "synthetic_heuristic"
    assert first["metrics"]["logistic_regression"]["confusion_matrix"]
    assert len(first["metrics"]["logistic_regression"]["confusion_matrix"]) == len(CLASS_LABELS)
    assert first["class_distribution"]["all"] == {"LOW": 40, "MEDIUM": 40, "HIGH": 40}
    assert json.loads((tmp_path / "first-report.json").read_text(encoding="utf-8"))["artifact"]["saved"]
    artifact = joblib.load(tmp_path / "first-model.joblib")
    assert tuple(artifact["metadata"]["feature_columns"]) == WEATHER_FEATURE_COLUMNS
    assert tuple(artifact["pipeline"].feature_names_in_) == WEATHER_FEATURE_COLUMNS
    assert artifact["metadata"]["production_eligible"] is False


def test_existing_artifact_is_not_overwritten(tmp_path: Path):
    dataset_path = tmp_path / "weather.csv"
    artifact_path = tmp_path / "existing.joblib"
    dataset = _weather_rows()
    dataset.to_csv(dataset_path, index=False)
    artifact_path.write_bytes(b"preserve-existing-content")

    report = train_and_evaluate(
        dataset_path,
        tmp_path / "report.json",
        artifact_path,
    )

    assert report["artifact"]["saved"] is False
    assert "not overwritten" in report["artifact"]["not_saved_reason"]
    assert artifact_path.read_bytes() == b"preserve-existing-content"


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"precipitation_mm": 1}, "Missing required weather features"),
        ({
            "precipitation_mm": -1,
            "precipitation_sum_3h_mm": 0,
            "precipitation_sum_6h_mm": 0,
            "precipitation_sum_24h_mm": 0,
            "wind_speed_kmh": 0,
        }, "cannot contain negative"),
        ({
            "precipitation_mm": "rain",
            "precipitation_sum_3h_mm": 0,
            "precipitation_sum_6h_mm": 0,
            "precipitation_sum_24h_mm": 0,
            "wind_speed_kmh": 0,
        }, "non-numeric"),
    ],
)
def test_invalid_weather_features_are_rejected(values: dict, message: str):
    with pytest.raises(ValueError, match=message):
        prepare_weather_features(values)


def test_missing_dataset_is_reported(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="does not exist"):
        train_and_evaluate(
            tmp_path / "missing.csv",
            tmp_path / "report.json",
            tmp_path / "model.joblib",
        )


def test_chronological_split_requires_distinct_times(tmp_path: Path):
    dataset_path = tmp_path / "one-time.csv"
    frame = _weather_rows(3)
    frame["time"] = pd.Timestamp("2022-01-01", tz="UTC")
    frame.to_csv(dataset_path, index=False)
    with pytest.raises(ValueError, match="distinct timestamps"):
        train_and_evaluate(
            dataset_path,
            tmp_path / "report.json",
            tmp_path / "model.joblib",
        )
