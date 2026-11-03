from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
import pytest
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml import risk_assessment
from ml.risk_model_features import WEATHER_FEATURE_COLUMNS
from backend.app.core.config import settings
from backend.app.services.risk_service import RiskService


def _accepted_payload(feature_columns: list[str] | None = None) -> dict:
    rows = pd.DataFrame(
        [
            [0, 0, 0, 0, 5],
            [10, 25, 40, 75, 20],
            [25, 60, 100, 180, 65],
        ] * 10,
        columns=WEATHER_FEATURE_COLUMNS,
    )
    labels = ["LOW", "MEDIUM", "HIGH"] * 10
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    pipeline.fit(rows, labels)
    thresholds = dict(risk_assessment.MODEL_ACCEPTANCE_THRESHOLDS)
    acceptance = {
        **thresholds,
        "test_support_adequate": True,
        "macro_f1_threshold_met": True,
        "accuracy_threshold_met": True,
        "majority_baseline_improvement_met": True,
        "experimental_criteria_met": True,
        "production_acceptance": False,
    }
    return {
        "pipeline": pipeline,
        "metadata": {
            "feature_columns": feature_columns or list(WEATHER_FEATURE_COLUMNS),
            "class_labels": ["LOW", "MEDIUM", "HIGH"],
            "label_provenance": {
                "type": "synthetic_heuristic",
                "generation": "calculate_weather_risk(features)['risk_level'] for every row",
                "per_row_marker": "label_provenance",
            },
            "random_seed": 42,
            "acceptance_criteria": acceptance,
            "data_provenance": {
                "source_path": "test_weather.csv",
                "source_sha256": "a" * 64,
            },
            "evaluation": {
                "test_class_distribution": {"LOW": 20, "MEDIUM": 20, "HIGH": 20},
                "metrics": {
                    "logistic_regression": {"accuracy": 0.9, "macro_f1": 0.9},
                    "majority_class_baseline": {"accuracy": 0.7, "macro_f1": 0.3},
                },
            },
            "production_eligible": False,
            "task": "weather-risk classification, not road-disruption prediction",
        },
    }


def _weather_context() -> dict:
    return {
        "risk_source": "experimental_model",
        "departure_time": "2026-10-02T12:00:00Z",
        "weather_locations": [
            {"location_id": "station-1", "latitude": 26.1445, "longitude": 91.7362}
        ],
        "weather_records": [{
            "location_id": "station-1",
            "time": pd.Timestamp("2026-10-02T11:00:00Z"),
            "precipitation_mm": 0.0,
            "precipitation_sum_3h_mm": 0.0,
            "precipitation_sum_6h_mm": 0.0,
            "precipitation_sum_24h_mm": 0.0,
            "wind_speed_kmh": 5.0,
        }],
    }


def _segment(segment_id: str = "seg-model") -> dict:
    return {
        "segment_id": segment_id,
        "coordinates": [[91.7362, 26.1445], [91.7400, 26.1500]],
        "road_class": "secondary",
        "slope_deg": 4.0,
    }


def _patch_artifact(monkeypatch, path: Path) -> None:
    monkeypatch.setattr(risk_assessment, "EXPERIMENTAL_MODEL_PATH", path)
    risk_assessment._load_experimental_weather_model.cache_clear()


def test_missing_artifact_is_rejected(monkeypatch, tmp_path: Path):
    _patch_artifact(monkeypatch, tmp_path / "missing.joblib")
    with pytest.raises(RuntimeError, match="artifact is missing"):
        risk_assessment.score_segment_model(_segment(), _weather_context())


def test_corrupt_artifact_is_rejected(monkeypatch, tmp_path: Path):
    path = tmp_path / "corrupt.joblib"
    path.write_bytes(b"not a joblib artifact")
    _patch_artifact(monkeypatch, path)
    with pytest.raises(RuntimeError, match="could not be loaded|corrupt or incompatible"):
        risk_assessment.score_segment_model(_segment(), _weather_context())


def test_incompatible_feature_schema_is_rejected(monkeypatch, tmp_path: Path):
    path = tmp_path / "wrong-schema.joblib"
    payload = _accepted_payload(["wind_speed_kmh", *WEATHER_FEATURE_COLUMNS[:-1]])
    joblib.dump(payload, path)
    _patch_artifact(monkeypatch, path)
    with pytest.raises(RuntimeError, match="feature schema is incompatible"):
        risk_assessment.score_segment_model(_segment(), _weather_context())


def test_incomplete_metadata_and_failed_acceptance_are_rejected(monkeypatch, tmp_path: Path):
    path = tmp_path / "failed-acceptance.joblib"
    payload = _accepted_payload()
    acceptance = payload["metadata"]["acceptance_criteria"]
    acceptance["macro_f1_threshold_met"] = False
    acceptance["experimental_criteria_met"] = False
    payload["metadata"]["evaluation"]["metrics"]["logistic_regression"]["macro_f1"] = 0.684
    payload["metadata"]["evaluation"]["metrics"]["majority_class_baseline"]["macro_f1"] = 0.333
    joblib.dump(payload, path)
    _patch_artifact(monkeypatch, path)
    with pytest.raises(RuntimeError, match="failed the predefined evaluation acceptance criteria"):
        risk_assessment.score_segment_model(_segment(), _weather_context())

    payload["metadata"].pop("label_provenance")
    joblib.dump(payload, path)
    risk_assessment._load_experimental_weather_model.cache_clear()
    with pytest.raises(RuntimeError, match="provenance is missing or invalid"):
        risk_assessment.score_segment_model(_segment(), _weather_context())


@pytest.mark.parametrize(
    ("record_overrides", "error"),
    [
        ({"precipitation_sum_24h_mm": None}, "complete, fresh, nearby"),
        ({"wind_speed_kmh": -1}, "complete, fresh, nearby"),
        ({"precipitation_mm": "invalid"}, "complete, fresh, nearby"),
    ],
)
def test_missing_or_invalid_weather_fails_closed(
    monkeypatch, tmp_path: Path, record_overrides: dict, error: str
):
    path = tmp_path / "accepted.joblib"
    joblib.dump(_accepted_payload(), path)
    _patch_artifact(monkeypatch, path)
    context = _weather_context()
    context["weather_records"][0].update(record_overrides)
    with pytest.raises(ValueError, match=error):
        risk_assessment.score_segment_model(_segment(), context)


def test_model_requires_explicit_experimental_opt_in(monkeypatch):
    monkeypatch.setattr(
        risk_assessment,
        "_load_experimental_weather_model",
        lambda _: pytest.fail("Model loader must not run without opt-in."),
    )
    with pytest.raises(RuntimeError, match="requires explicit opt-in"):
        risk_assessment.score_segment_model(_segment(), {"risk_source": "model"})


def test_explicit_experimental_model_inference_uses_schema(monkeypatch, tmp_path: Path):
    path = tmp_path / "accepted.joblib"
    joblib.dump(_accepted_payload(), path)
    _patch_artifact(monkeypatch, path)

    result = risk_assessment.score_segment_model(_segment(), _weather_context())

    assert result["risk_source"] == "model"
    assert result["experimental"] is True
    assert result["data_quality"] == "partial"
    assert result["risk_level"] == "low"
    assert "synthetic rule-generated labels" in result["factors"][0]["detail"]


def test_partial_model_results_are_discarded_on_inference_failure(monkeypatch):
    segments = [_segment("first"), _segment("second")]
    calls = []

    def fail_after_one(segment, context):
        calls.append(segment["segment_id"])
        if segment["segment_id"] == "second":
            raise RuntimeError("simulated inference failure")
        return {"score": 99, "risk_level": "high", "risk_source": "model"}

    monkeypatch.setattr(risk_assessment, "score_segment_model", fail_after_one)
    experimental_context = {**_weather_context(), "risk_source": "experimental_model"}
    actual = risk_assessment.score(segments, experimental_context)
    expected = {
        segment["segment_id"]: risk_assessment.score_segment_baseline(segment, experimental_context)
        for segment in segments
    }

    assert calls == ["first", "second"]
    assert actual == expected
    assert all(result["risk_source"] == "baseline" for result in actual.values())


def test_default_production_source_stays_baseline(monkeypatch):
    monkeypatch.setattr(
        risk_assessment,
        "_load_experimental_weather_model",
        lambda _: pytest.fail("Default scoring must not load a model."),
    )
    result = risk_assessment.score([_segment()])
    assert result["seg-model"]["risk_source"] == "baseline"


def test_current_failed_artifact_is_rejected(monkeypatch):
    _patch_artifact(
        monkeypatch,
        risk_assessment.MODEL_DIR / "weather_risk_logistic_regression.joblib",
    )
    with pytest.raises(RuntimeError, match="data provenance is missing or invalid"):
        risk_assessment.score_segment_model(_segment(), _weather_context())


def test_backend_clears_partial_model_scores_and_returns_baseline(monkeypatch):
    service = RiskService()
    monkeypatch.setattr(settings, "RISK_SOURCE", "model")
    monkeypatch.setattr(settings, "RISK_SERVICE_ENABLED", True)
    monkeypatch.setattr(settings, "WEATHER_AVAILABLE", True)
    calls = []

    def fail_after_one(segment_id, segment, context):
        calls.append(segment_id)
        if segment_id == "second":
            raise RuntimeError("simulated model failure")
        return {"score": 99, "factors": [], "data_quality": "complete"}

    monkeypatch.setattr(service, "_score_segment_model", fail_after_one)
    segments = [_segment("first"), _segment("second")]
    actual, source = service.score(segments, {})
    expected = {
        segment["segment_id"]: service._score_segment_baseline(
            segment["segment_id"], segment, {}
        )
        for segment in segments
    }

    assert calls == ["first", "second"]
    assert source == "baseline"
    assert actual == expected


def test_backend_default_source_never_calls_model(monkeypatch):
    service = RiskService()
    monkeypatch.setattr(settings, "RISK_SOURCE", "baseline")
    monkeypatch.setattr(settings, "RISK_SERVICE_ENABLED", True)
    monkeypatch.setattr(
        service,
        "_score_segment_model",
        lambda *_: pytest.fail("Production default must not call model inference."),
    )

    results, source = service.score([_segment()], {})

    assert source == "baseline"
    assert results["seg-model"]["score"] >= 0
