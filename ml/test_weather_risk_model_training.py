from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import pytest

pytest.importorskip("sklearn")

from ml.risk_model_features import WEATHER_FEATURE_COLUMNS, prepare_weather_features
from ml.scripts import train_weather_risk_model as training
from ml.scripts.train_weather_risk_model import (
    CLASS_LABELS,
    _chronological_split,
    _validate_synthetic_labels,
    load_weather_dataset,
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


@pytest.mark.parametrize("missing_column", ["time", "wind_speed_kmh"])
def test_training_rejects_missing_required_dataset_columns(
    tmp_path: Path, missing_column: str
):
    dataset_path = tmp_path / "missing-column.csv"
    _weather_rows().drop(columns=[missing_column]).to_csv(dataset_path, index=False)

    with pytest.raises(
        ValueError, match=f"missing required columns: {missing_column}"
    ):
        load_weather_dataset(dataset_path)


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("", "Could not read weather feature dataset"),
        (
            ",".join(["time", *WEATHER_FEATURE_COLUMNS]) + "\n",
            "contains no rows",
        ),
    ],
)
def test_empty_datasets_are_rejected(tmp_path: Path, contents: str, message: str):
    dataset_path = tmp_path / "empty.csv"
    dataset_path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_weather_dataset(dataset_path)


def test_missing_feature_rows_are_dropped_and_counted(tmp_path: Path):
    dataset_path = tmp_path / "missing-features.csv"
    frame = _weather_rows()
    frame.loc[0, "precipitation_sum_24h_mm"] = None
    frame.to_csv(dataset_path, index=False)

    labeled, labels, provenance = load_weather_dataset(dataset_path)

    assert len(labeled) == len(labels) == len(frame) - 1
    assert provenance["rows_dropped_for_missing_features"] == 1
    assert labels.notna().all()


def test_dataset_with_no_complete_feature_rows_is_rejected(tmp_path: Path):
    dataset_path = tmp_path / "all-missing-features.csv"
    frame = _weather_rows(3)
    frame.loc[:, list(WEATHER_FEATURE_COLUMNS)] = float("nan")
    frame.to_csv(dataset_path, index=False)

    with pytest.raises(ValueError, match="no rows with all required feature values"):
        load_weather_dataset(dataset_path)


@pytest.mark.parametrize(
    ("column", "bad_value", "message"),
    [
        ("precipitation_mm", "rain", "non-numeric"),
        ("wind_speed_kmh", float("inf"), "infinite"),
        ("precipitation_sum_6h_mm", -1, "cannot contain negative"),
    ],
)
def test_invalid_dataset_feature_values_are_rejected(
    tmp_path: Path, column: str, bad_value: float | str, message: str
):
    dataset_path = tmp_path / "invalid-feature.csv"
    frame = _weather_rows()
    frame[column] = frame[column].astype(object)
    frame.loc[0, column] = bad_value
    frame.to_csv(dataset_path, index=False)

    with pytest.raises(ValueError, match=message):
        load_weather_dataset(dataset_path)


@pytest.mark.parametrize(
    ("label_result", "message"),
    [
        ({"risk_level": None}, "labels contain missing values"),
        ({"risk_level": "UNKNOWN"}, "unsupported risk labels: UNKNOWN"),
    ],
)
def test_missing_or_invalid_generated_risk_labels_are_rejected(
    tmp_path: Path, monkeypatch, label_result: dict, message: str
):
    dataset_path = tmp_path / "invalid-label.csv"
    _weather_rows(3).to_csv(dataset_path, index=False)
    monkeypatch.setattr(training, "calculate_weather_risk", lambda _: label_result)

    with pytest.raises(ValueError, match=message):
        load_weather_dataset(dataset_path)


def test_synthetic_label_validator_rejects_count_mismatch_and_empty_labels():
    with pytest.raises(ValueError, match="do not match"):
        _validate_synthetic_labels(pd.Series(["LOW"]), expected_rows=2)
    with pytest.raises(ValueError, match="no synthetic risk labels"):
        _validate_synthetic_labels(pd.Series(dtype=str), expected_rows=0)


@pytest.mark.parametrize("timestamp", ["", "not-a-timestamp"])
def test_missing_or_invalid_timestamps_are_rejected(tmp_path: Path, timestamp: str):
    dataset_path = tmp_path / "invalid-time.csv"
    frame = _weather_rows(3)
    frame["time"] = frame["time"].astype(object)
    frame.loc[0, "time"] = timestamp
    frame.to_csv(dataset_path, index=False)

    with pytest.raises(ValueError, match="missing or invalid timestamps"):
        load_weather_dataset(dataset_path)


def test_duplicate_location_timestamp_pairs_are_rejected(tmp_path: Path):
    dataset_path = tmp_path / "duplicate-station-time.csv"
    frame = _weather_rows(3)
    frame["location_id"] = "station-1"
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    frame.to_csv(dataset_path, index=False)

    with pytest.raises(ValueError, match="duplicate location/time"):
        load_weather_dataset(dataset_path)


def test_same_timestamp_for_distinct_locations_is_valid(tmp_path: Path):
    dataset_path = tmp_path / "multiple-stations.csv"
    frame = _weather_rows(120)
    second_station = frame.copy()
    frame["location_id"] = "station-1"
    second_station["location_id"] = "station-2"
    pd.concat([frame, second_station], ignore_index=True).to_csv(dataset_path, index=False)

    labeled, _, provenance = load_weather_dataset(dataset_path)

    assert len(labeled) == 240
    assert provenance["rows_dropped_for_missing_features"] == 0


def test_training_rejects_insufficient_samples_for_training_classes(tmp_path: Path):
    dataset_path = tmp_path / "too-few-samples.csv"
    _weather_rows(3).to_csv(dataset_path, index=False)

    with pytest.raises(ValueError, match="Training split is missing risk classes"):
        train_and_evaluate(
            dataset_path,
            tmp_path / "report.json",
            tmp_path / "model.joblib",
        )


def test_chronological_split_has_no_timestamp_leakage():
    rows = _weather_rows(10)
    rows = pd.concat([rows, rows.iloc[[8]]], ignore_index=True)

    train, test, _ = _chronological_split(rows, 0.20)

    train_times = set(train["time"])
    test_times = set(test["time"])
    assert train_times.isdisjoint(test_times)
    assert train["time"].max() < test["time"].min()
    assert len(test.loc[test["time"] == test["time"].min()]) == 2


def test_chronological_split_rejects_invalid_timestamps():
    with pytest.raises(ValueError, match="valid, non-missing timestamps"):
        _chronological_split(pd.DataFrame({"time": ["2022-01-01", "invalid"]}), 0.20)
