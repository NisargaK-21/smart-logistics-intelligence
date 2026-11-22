"""Integration tests for FastAPI ML Prediction endpoints and Route Integration.

Tests:
- GET /api/v1/predict/model-info (transparency, benchmarks, and spatial buffer metrics)
- POST /api/v1/predict/landslide-susceptibility (valid, out-of-bounds, invalid schema, RSSI & LSS fields)
- POST /api/v1/predict/batch-landslide-susceptibility
- Route planning integration (ensuring ML predictions are attached without breaking deterministic risk)
"""

from __future__ import annotations

import pytest


def test_get_model_info_endpoint(client):
    response = client.get("/api/v1/predict/model-info")
    assert response.status_code == 200
    data = response.json()

    assert data["available"] is True
    assert data["status"] == "operational"
    assert "Calibrated Random Forest" in data["model_type"]
    assert "holdout_test_metrics" in data
    metrics = data["holdout_test_metrics"]
    assert metrics["macro_f1"] >= 0.80
    assert metrics["roc_auc"] >= 0.85
    assert "confusion_matrix" in metrics

    assert "feature_importances" in data
    assert "slope_deg" in data["feature_importances"]
    assert "road_distance_m" in data["feature_importances"]

    # Verify scientific transparency and multi-strategy benchmarks
    assert "scientific_framework" in data
    assert "benchmarks" in data
    assert "bias_analysis" in data

    # Verify spatial buffer validation design metadata
    assert "spatial_validation_design" in data
    spatial_design = data["spatial_validation_design"]
    assert spatial_design["buffer_km"] == 10.0
    assert spatial_design["split_latitude"] == 25.50
    assert spatial_design["verified_min_separation_km"] >= 10.0


def test_predict_landslide_susceptibility_valid_point(client):
    payload = {
        "latitude": 25.60,
        "longitude": 91.90,
        "slope_deg": 18.5,
        "ruggedness": 9.2,
        "elevation_m": 1150.0,
        "road_distance_m": 45.0,
        "road_class": "national_highway",
    }
    response = client.post("/api/v1/predict/landslide-susceptibility", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert 0 <= data["susceptibility_score"] <= 100
    assert 0 <= data["landslide_susceptibility_score"] <= 100
    assert 0.0 <= data["relative_spatial_susceptibility_index"] <= 1.0
    assert 0.0 <= data["calibrated_probability"] <= 1.0
    assert data["susceptibility_level"] in {"low", "moderate", "high", "very_high"}
    assert data["model_source"] == "calibrated_random_forest"
    assert data["data_quality"] == "complete"
    assert len(data["contributing_factors"]) > 0

    factor_names = [f["factor"] for f in data["contributing_factors"]]
    assert any("slope" in name for name in factor_names)


def test_predict_landslide_susceptibility_samples_dem_when_omitted(client):
    # Pass only coordinates inside DEM raster coverage
    payload = {
        "latitude": 25.60,
        "longitude": 91.90,
    }
    response = client.post("/api/v1/predict/landslide-susceptibility", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert 0 <= data["susceptibility_score"] <= 100
    assert 0.0 <= data["relative_spatial_susceptibility_index"] <= 1.0
    assert data["data_quality"] == "complete"


def test_predict_landslide_susceptibility_out_of_bounds(client):
    payload = {
        "latitude": 13.0827,
        "longitude": 80.2707,  # Chennai
    }
    response = client.post("/api/v1/predict/landslide-susceptibility", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["data_quality"] == "partial"
    assert data["model_source"] == "heuristic_fallback"
    assert len(data["warnings"]) > 0
    assert any("DEM raster coverage" in w for w in data["warnings"])
    assert "relative_spatial_susceptibility_index" in data


def test_predict_landslide_susceptibility_invalid_coordinates(client):
    # Latitude > 90.0
    payload = {
        "latitude": 125.0,
        "longitude": 91.8,
    }
    response = client.post("/api/v1/predict/landslide-susceptibility", json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_batch_landslide_prediction_endpoint(client):
    payload = {
        "points": [
            {
                "latitude": 25.60,
                "longitude": 91.90,
                "slope_deg": 20.0,
                "ruggedness": 10.0,
            },
            {
                "latitude": 26.15,
                "longitude": 91.75,
                "slope_deg": 1.5,
                "ruggedness": 0.5,
            },
        ]
    }
    response = client.post("/api/v1/predict/batch-landslide-susceptibility", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_points"] == 2
    assert len(data["predictions"]) == 2
    assert data["predictions"][0]["susceptibility_score"] > data["predictions"][1]["susceptibility_score"]
    assert data["predictions"][0]["relative_spatial_susceptibility_index"] > data["predictions"][1]["relative_spatial_susceptibility_index"]


def test_route_planning_contains_ml_susceptibility_summary(client):
    payload = {
        "origin": {"lat": 26.1801, "lng": 91.7001},
        "destination": {"lat": 26.1401, "lng": 91.7399},
        "vehicle_type": "truck",
    }
    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "routes" in data
    for route in data["routes"]:
        # Verify route-level ML susceptibility summary
        assert "ml_landslide_susceptibility_summary" in route
        if route["ml_landslide_susceptibility_summary"] is not None:
            summary = route["ml_landslide_susceptibility_summary"]
            assert "average_susceptibility_score" in summary
            assert "max_segment_susceptibility_score" in summary

        # Verify segment-level ML susceptibility metrics
        for seg in route["segments"]:
            assert "landslide_susceptibility" in seg
            if seg["landslide_susceptibility"] is not None:
                susc = seg["landslide_susceptibility"]
                assert "susceptibility_score" in susc
                assert "calibrated_probability" in susc
                assert "susceptibility_level" in susc
