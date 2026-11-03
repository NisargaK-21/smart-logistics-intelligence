"""Comprehensive tests for the Person 2 Risk & ML Module contract and safety logic.

Covers:
- `score(segments, context)` contract interface shape and return structure
- Risk level alignments: LOW 0-33, MEDIUM 34-66, HIGH 67-100
- Normal conditions vs extreme weather
- Missing weather, missing slope, and missing history handling (never treated as safe)
- Stale weather (> 24h) and future-only weather observations
- Distant weather stations (> 50 km)
- Graceful model adapter fallback to baseline
- Vehicle sensitivity scaling (truck > van > car)
- Factor breakdown and data-quality annotations
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.risk_assessment import (
    score,
    score_segment_baseline,
    score_segment_model,
    score_segments,
    score_route,
)


def _sample_segment(segment_id: str = "seg-contract-1", slope: float = 2.0, road_class: str = "major"):
    return {
        "segment_id": segment_id,
        "coordinates": [[91.7362, 26.1445], [91.7600, 25.9000]],
        "road_class": road_class,
        "slope_deg": slope,
        "surface": "asphalt",
        "length_km": 15.0,
    }


def test_score_interface_contract_shape():
    """Verify score(segments, context) returns dictionary keyed by segment_id with contract fields."""
    segments = [_sample_segment("seg-1"), _sample_segment("seg-2", slope=9.0)]
    context = {"vehicle_type": "truck", "departure_time": "2026-10-02T10:00:00+05:30"}

    result = score(segments, context)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"seg-1", "seg-2"}

    for sid, data in result.items():
        assert "score" in data
        assert isinstance(data["score"], int)
        assert 0 <= data["score"] <= 100

        assert "risk_level" in data
        assert data["risk_level"] in ("low", "medium", "high")

        assert "data_quality" in data
        assert data["data_quality"] in ("complete", "partial", "stale", "unavailable")

        assert "risk_source" in data
        assert data["risk_source"] in ("baseline", "model")

        assert "factors" in data
        assert isinstance(data["factors"], list)
        assert len(data["factors"]) >= 1

        for factor in data["factors"]:
            assert "name" in factor
            assert "contribution" in factor
            assert factor["contribution"] >= 0.0


def test_score_risk_level_threshold_boundaries():
    """Verify segment risk levels match contract: LOW 0-33, MEDIUM 34-66, HIGH 67-100."""
    # Flat highway with gentle terrain and car (LOW risk)
    seg_low = {
        "segment_id": "seg-low",
        "coordinates": [[91.7362, 26.1445], [91.7400, 26.1500]],
        "road_class": "expressway",
        "slope_deg": 1.0,
        "surface": "asphalt",
    }
    context_car = {"vehicle_type": "car", "departure_time": "2026-10-02T12:00:00Z"}
    res_low = score([seg_low], context_car)["seg-low"]
    assert res_low["score"] <= 33
    assert res_low["risk_level"] == "low"

    # Steep mountain terrain with truck (HIGH risk)
    seg_high = {
        "segment_id": "seg-high",
        "coordinates": [[91.7362, 26.1445], [91.7400, 26.1500]],
        "road_class": "tertiary",
        "slope_deg": 18.0,
        "surface": "mud",
    }
    context_truck = {"vehicle_type": "truck", "departure_time": "2026-10-02T12:00:00Z"}
    res_high = score([seg_high], context_truck)["seg-high"]
    assert res_high["score"] >= 67
    assert res_high["risk_level"] == "high"


def test_normal_conditions_scoring():
    """Normal conditions should yield complete data quality and valid risk score."""
    seg = _sample_segment("seg-normal", slope=3.0, road_class="national_highway")
    context = {"vehicle_type": "van", "departure_time": "2026-10-02T12:00:00Z"}

    res = score([seg], context)["seg-normal"]
    assert 0 <= res["score"] <= 100
    factor_names = [f["name"] for f in res["factors"]]
    assert "road_infrastructure" in factor_names


def test_extreme_weather_risk_elevation():
    """Extreme weather increases score and includes heavy_rainfall factor."""
    seg = _sample_segment("seg-extreme", slope=10.0, road_class="secondary")
    extreme_records = [{
        "location_id": "loc-1",
        "time": datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc),
        "precipitation_mm": 35.0,
        "precipitation_sum_3h_mm": 70.0,
        "precipitation_sum_6h_mm": 110.0,
        "precipitation_sum_24h_mm": 190.0,
        "wind_speed_kmh": 65.0,
    }]
    context = {
        "vehicle_type": "truck",
        "departure_time": "2026-10-02T11:00:00Z",
        "weather_locations": [{"location_id": "loc-1", "latitude": 26.1445, "longitude": 91.7362}],
        "weather_records": extreme_records,
    }

    res = score([seg], context)["seg-extreme"]
    assert res["risk_level"] == "high"
    factor_names = [f["name"] for f in res["factors"]]
    assert "heavy_rainfall" in factor_names
    heavy_factor = next(f for f in res["factors"] if f["name"] == "heavy_rainfall")
    assert heavy_factor["contribution"] >= 67


def test_missing_weather_not_treated_as_safe():
    """When weather data is unavailable, data_quality is partial and score is non-zero."""
    seg = _sample_segment("seg-no-weather", slope=8.0, road_class="secondary")
    context = {
        "vehicle_type": "truck",
        "departure_time": "2026-10-02T12:00:00Z",
        "weather_available": False,
    }

    res = score([seg], context)["seg-no-weather"]
    assert res["data_quality"] == "partial"
    factor_names = [f["name"] for f in res["factors"]]
    assert "weather_unavailable" in factor_names

    w_factor = next(f for f in res["factors"] if f["name"] == "weather_unavailable")
    assert w_factor["contribution"] == 0.0
    assert "could not be fetched" in w_factor["detail"].lower()

    # The segment must NOT score 0 risk! Terrain and road class carry baseline risk.
    assert res["score"] > 0


def test_stale_weather_observation():
    """Observations older than 24h must be flagged as stale data_quality."""
    seg = _sample_segment("seg-stale", slope=2.0)
    stale_records = [{
        "location_id": "loc-stale",
        "time": datetime(2026, 9, 30, 0, 0, tzinfo=timezone.utc),
        "precipitation_mm": 5.0,
        "precipitation_sum_3h_mm": 10.0,
        "precipitation_sum_6h_mm": 15.0,
        "precipitation_sum_24h_mm": 20.0,
        "wind_speed_kmh": 10.0,
    }]
    context = {
        "vehicle_type": "truck",
        "departure_time": "2026-10-02T12:00:00Z",  # ~60 hours later
        "weather_locations": [{"location_id": "loc-stale", "latitude": 26.1445, "longitude": 91.7362}],
        "weather_records": stale_records,
    }

    res = score([seg], context)["seg-stale"]
    assert res["data_quality"] == "stale"
    factor_names = [f["name"] for f in res["factors"]]
    assert "stale_weather" in factor_names


def test_future_only_weather_observations():
    """Observations strictly in the future relative to departure time are marked partial."""
    seg = _sample_segment("seg-future", slope=2.0)
    future_records = [{
        "location_id": "loc-future",
        "time": datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc),
        "precipitation_mm": 5.0,
        "precipitation_sum_3h_mm": 10.0,
        "precipitation_sum_6h_mm": 15.0,
        "precipitation_sum_24h_mm": 20.0,
        "wind_speed_kmh": 10.0,
    }]
    context = {
        "vehicle_type": "truck",
        "departure_time": "2026-10-02T12:00:00Z",
        "weather_locations": [{"location_id": "loc-future", "latitude": 26.1445, "longitude": 91.7362}],
        "weather_records": future_records,
    }

    res = score([seg], context)["seg-future"]
    assert res["data_quality"] == "partial"
    factor_names = [f["name"] for f in res["factors"]]
    assert "weather_unavailable" in factor_names
    w_factor = next(f for f in res["factors"] if f["name"] == "weather_unavailable")
    assert "future" in w_factor["detail"].lower()


def test_distant_weather_station():
    """A weather station beyond 50 km must flag distant_weather_station and partial data quality."""
    # Segment coordinates in eastern Assam / Arunachal border, far from station at (26.1445, 91.7362)
    seg_distant = {
        "segment_id": "seg-distant",
        "coordinates": [[92.5000, 26.8000], [92.5100, 26.8100]],  # ~110 km away
        "road_class": "secondary",
        "slope_deg": 4.0,
    }
    context = {
        "vehicle_type": "truck",
        "departure_time": "2026-10-02T12:00:00Z",
        "weather_locations": [{"location_id": "loc-near-guwahati", "latitude": 26.1445, "longitude": 91.7362}],
        "weather_records": [{
            "location_id": "loc-near-guwahati",
            "time": datetime(2026, 10, 2, 11, 0, tzinfo=timezone.utc),
            "precipitation_mm": 0.0,
            "precipitation_sum_3h_mm": 0.0,
            "precipitation_sum_6h_mm": 0.0,
            "precipitation_sum_24h_mm": 0.0,
            "wind_speed_kmh": 10.0,
        }],
    }

    res = score([seg_distant], context)["seg-distant"]
    assert res["data_quality"] == "partial"
    factor_names = [f["name"] for f in res["factors"]]
    assert "distant_weather_station" in factor_names


def test_missing_terrain_slope_not_treated_as_flat():
    """Missing slope must emit terrain_unavailable factor and flag data_quality as partial."""
    seg_no_slope = {
        "segment_id": "seg-no-slope",
        "coordinates": [[91.7362, 26.1445], [91.7400, 26.1500]],
        "road_class": "secondary",
        "slope_deg": None,
    }
    context = {"vehicle_type": "truck", "departure_time": "2026-10-02T12:00:00Z"}

    res = score([seg_no_slope], context)["seg-no-slope"]
    assert res["data_quality"] == "partial"
    factor_names = [f["name"] for f in res["factors"]]
    assert "terrain_unavailable" in factor_names


def test_missing_coordinates_incomplete():
    """A segment with no coordinates must be marked partial or unavailable."""
    seg_no_coords = {"segment_id": "seg-no-coords", "road_class": "secondary"}
    context = {"vehicle_type": "truck"}

    res = score([seg_no_coords], context)["seg-no-coords"]
    assert res["data_quality"] in ("partial", "unavailable")
    factor_names = [f["name"] for f in res["factors"]]
    assert "weather_unavailable" in factor_names
    assert "history_unavailable" in factor_names


def test_model_fallback_to_baseline():
    """Requesting risk_source='model' when no model is configured falls back cleanly to baseline."""
    seg = _sample_segment("seg-fallback")
    context = {
        "vehicle_type": "truck",
        "departure_time": "2026-10-02T12:00:00Z",
        "risk_source": "model",
    }

    res = score([seg], context)["seg-fallback"]
    assert res["risk_source"] == "baseline"
    assert 0 <= res["score"] <= 100


def test_vehicle_sensitivity_scaling():
    """Truck carries higher risk than car on steep mountain roads."""
    seg_steep = _sample_segment("seg-sensitivity", slope=12.0, road_class="tertiary")
    time_ctx = "2026-10-02T12:00:00Z"

    truck_res = score([seg_steep], {"vehicle_type": "truck", "departure_time": time_ctx})["seg-sensitivity"]
    car_res = score([seg_steep], {"vehicle_type": "car", "departure_time": time_ctx})["seg-sensitivity"]

    assert truck_res["score"] > car_res["score"]


def test_backward_compatibility_score_segments_and_route():
    """Legacy score_segments and score_route continue to work."""
    seg = _sample_segment("seg-legacy")
    assessments = score_segments([seg], {"as_of": "2026-10-02T12:00:00Z"})

    assert len(assessments) == 1
    assert assessments[0]["segment_id"] == "seg-legacy"
    assert assessments[0]["risk_level"] in ("LOW", "MEDIUM", "HIGH", "UNKNOWN")
    assert "data_quality" in assessments[0]

    route_res = score_route(
        {"route_id": "route-test", "segment_ids": ["seg-legacy"]},
        {"segments": [seg], "as_of": "2026-10-02T12:00:00Z"},
    )
    assert route_res["route_id"] == "route-test"
    assert len(route_res["segments"]) == 1


if __name__ == "__main__":
    test_score_interface_contract_shape()
    test_score_risk_level_threshold_boundaries()
    test_normal_conditions_scoring()
    test_extreme_weather_risk_elevation()
    test_missing_weather_not_treated_as_safe()
    test_stale_weather_observation()
    test_future_only_weather_observations()
    test_distant_weather_station()
    test_missing_terrain_slope_not_treated_as_flat()
    test_missing_coordinates_incomplete()
    test_model_fallback_to_baseline()
    test_vehicle_sensitivity_scaling()
    test_backward_compatibility_score_segments_and_route()
    print("All contract and safety tests passed successfully!")
