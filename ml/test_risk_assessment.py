from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from routing.service import find_routes, get_segments
from ml.risk_assessment import score_route, score_segments


def _route_segment():
    origin = {"lat": 26.1801, "lng": 91.7001}
    destination = {"lat": 26.1401, "lng": 91.7399}
    route = find_routes(origin, destination, "car", max_routes=1)[0]
    return route, get_segments(route.segment_ids)[0]


def test_score_segments_preserves_segment_ids():
    route, _ = _route_segment()
    segments = get_segments(route.segment_ids)
    risks = score_segments(segments, {"as_of": "2026-10-02T12:00:00Z"})
    assert len(risks) == len(route.segment_ids)
    assert {item["segment_id"] for item in risks} == set(route.segment_ids)
    for item in risks:
        assert item["risk_score"] is None or item["risk_score"] >= 0
        assert item["risk_level"] in {"LOW", "MEDIUM", "HIGH", "UNKNOWN"}


def test_recent_weather_data_selection():
    _, segment = _route_segment()
    result = score_segments([segment], {"as_of": "2026-10-02T12:00:00Z"})[0]
    assert result["data_quality"]["source_dataset"] == "recent_weather_features"
    assert result["data_quality"]["weather_time"] is not None
    assert result["data_quality"]["weather_time"].year == 2026


def test_stale_observation_is_marked_and_incomplete():
    segment = {
        "segment_id": "seg-stale",
        "coordinates": [[91.7000, 26.1800], [91.7100, 26.1900]],
        "road_class": "major",
        "slope_deg": 7,
        "surface": "asphalt",
    }
    records = [{
        "location_id": "station-1",
        "time": datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc),
        "precipitation_mm": 15.0,
        "precipitation_sum_3h_mm": 30.0,
        "precipitation_sum_6h_mm": 40.0,
        "precipitation_sum_24h_mm": 80.0,
        "wind_speed_kmh": 25.0,
    }]
    context = {
        "as_of": "2026-10-03T12:00:00Z",
        "weather_locations": [{"location_id": "station-1", "latitude": 26.1800, "longitude": 91.7000}],
        "weather_records": records,
    }
    result = score_segments([segment], context)[0]
    assert result["data_quality"]["stale"] is True
    assert result["risk_complete"] is False
    assert result["risk_score"] is None


def test_future_observation_relative_to_as_of_is_ignored():
    segment = {
        "segment_id": "seg-future",
        "coordinates": [[91.7000, 26.1800], [91.7100, 26.1900]],
        "road_class": "major",
    }
    records = [{
        "location_id": "station-1",
        "time": datetime(2026, 10, 4, 8, 0, tzinfo=timezone.utc),
        "precipitation_mm": 10.0,
        "precipitation_sum_3h_mm": 20.0,
        "precipitation_sum_6h_mm": 30.0,
        "precipitation_sum_24h_mm": 50.0,
        "wind_speed_kmh": 10.0,
    }]
    result = score_segments([segment], {
        "as_of": "2026-10-03T12:00:00Z",
        "weather_locations": [{"location_id": "station-1", "latitude": 26.1800, "longitude": 91.7000}],
        "weather_records": records,
    })[0]
    assert result["matching"]["weather_status"] == "future_only"
    assert result["risk_complete"] is False
    assert result["risk_score"] is None


def test_missing_rolling_rainfall_totals_are_incomplete():
    segment = {
        "segment_id": "seg-missing-rolling",
        "coordinates": [[91.7000, 26.1800], [91.7100, 26.1900]],
        "road_class": "major",
    }
    records = [{
        "location_id": "station-1",
        "time": datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
        "precipitation_mm": 25.0,
        "precipitation_sum_3h_mm": None,
        "precipitation_sum_6h_mm": None,
        "precipitation_sum_24h_mm": None,
        "wind_speed_kmh": 20.0,
    }]
    result = score_segments([segment], {
        "as_of": "2026-10-02T12:30:00Z",
        "weather_locations": [{"location_id": "station-1", "latitude": 26.1800, "longitude": 91.7000}],
        "weather_records": records,
    })[0]
    assert result["hazard_indicators"]["weather"]["risk_level"] == "UNKNOWN"
    assert result["risk_complete"] is False
    assert result["risk_score"] is None


def test_missing_coordinates_are_explicitly_incomplete():
    result = score_segments([{"segment_id": "seg-missing-coords", "road_class": "local"}])[0]
    assert result["matching"]["weather_status"] == "missing_coordinates"
    assert result["risk_complete"] is False
    assert result["risk_score"] is None


def test_unavailable_weather_files_are_explicitly_incomplete():
    segment = {
        "segment_id": "seg-unavailable",
        "coordinates": [[91.7000, 26.1800], [91.7100, 26.1900]],
        "road_class": "major",
    }
    result = score_segments([segment], {"weather_locations": [], "weather_records": []})[0]
    assert result["data_quality"]["weather_data_available"] is False
    assert result["risk_complete"] is False
    assert result["risk_score"] is None


def test_empty_routes_and_incomplete_assessments():
    empty_route = score_route({"route_id": "route-empty", "segment_ids": []}, {"segments": []})
    assert empty_route["risk_score"] is None
    assert empty_route["risk_level"] == "UNKNOWN"
    assert empty_route["overall_risk_complete"] is False

    incomplete = score_route(
        {"route_id": "route-incomplete", "segment_ids": ["seg-incomplete"]},
        {"segments": [{"segment_id": "seg-incomplete", "road_class": "local"}]},
    )
    assert incomplete["overall_risk_complete"] is False
    assert incomplete["risk_score"] is None


def test_route_assessment_returns_route_score_and_segments():
    origin = {"lat": 26.1801, "lng": 91.7001}
    destination = {"lat": 26.1401, "lng": 91.7399}
    route = find_routes(origin, destination, "van", max_routes=1)[0]
    assessment = score_route(route, {"as_of": "2026-10-02T12:00:00Z"})
    assert assessment["route_id"] == route.route_id
    assert assessment["segment_ids"] == route.segment_ids
    assert assessment["risk_score"] is None or assessment["risk_score"] >= 0
    assert assessment["risk_level"] in {"LOW", "MEDIUM", "HIGH", "UNKNOWN"}
    assert len(assessment["segments"]) == len(route.segment_ids)


if __name__ == "__main__":
    test_score_segments_preserves_segment_ids()
    test_recent_weather_data_selection()
    test_stale_observation_is_marked_and_incomplete()
    test_future_observation_relative_to_as_of_is_ignored()
    test_missing_rolling_rainfall_totals_are_incomplete()
    test_missing_coordinates_are_explicitly_incomplete()
    test_unavailable_weather_files_are_explicitly_incomplete()
    test_empty_routes_and_incomplete_assessments()
    test_route_assessment_returns_route_score_and_segments()
    print("All risk assessment tests passed.")
