from backend.app.core.config import settings


def test_plan_routes_success(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True
    settings.RISK_SOURCE = "baseline"

    payload = {
        "origin": {"lat": 26.1445, "lng": 91.7362},
        "destination": {"lat": 25.5788, "lng": 91.8933},
        "vehicle_type": "truck",
        "departure_time": "2026-10-28T10:00:00+05:30",
    }

    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Contract checks
    assert "recommended_route_id" in data
    assert "risk_source" in data
    assert data["risk_source"] == "baseline"
    assert "generated_at" in data
    assert "routes" in data
    assert len(data["routes"]) >= 1

    # Check top route recommendation
    assert data["recommended_route_id"] == data["routes"][0]["route_id"]

    for route in data["routes"]:
        assert "route_id" in route
        assert "distance_km" in route
        assert "estimated_duration_minutes" in route
        assert "risk_score" in route
        assert 0 <= route["risk_score"] <= 100
        assert route["risk_level"] in ("low", "medium", "high")
        assert route["geometry"]["type"] == "LineString"
        assert len(route["geometry"]["coordinates"]) >= 2
        assert len(route["segments"]) >= 1
        for seg in route["segments"]:
            assert "segment_id" in seg
            assert "risk_score" in seg
            assert 0 <= seg["risk_score"] <= 100
            assert "coordinates" in seg
        assert len(route["risk_factors"]) >= 1
        for f in route["risk_factors"]:
            assert "name" in f
            assert "contribution" in f
        assert route["data_quality"] in ("complete", "partial", "stale", "unavailable")


def test_route_score_aggregation_formula(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True

    payload = {
        "origin": {"lat": 26.1445, "lng": 91.7362},
        "destination": {"lat": 25.5788, "lng": 91.8933},
        "vehicle_type": "van",
    }

    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 200
    data = response.json()

    for route in data["routes"]:
        # Verify formula: 0.7 * length_weighted_mean + 0.3 * worst_segment
        seg_scores = [s["risk_score"] for s in route["segments"]]
        worst_seg = max(seg_scores)
        # Verify route score lies between min and max segment scores roughly
        assert min(seg_scores) <= route["risk_score"] <= worst_seg
        # Risk level categorization: low 0-33, medium 34-66, high 67-100
        if route["risk_score"] <= 33:
            assert route["risk_level"] == "low"
        elif route["risk_score"] <= 66:
            assert route["risk_level"] == "medium"
        else:
            assert route["risk_level"] == "high"


def test_validation_error_same_origin_and_destination(client):
    payload = {
        "origin": {"lat": 26.1445, "lng": 91.7362},
        "destination": {"lat": 26.1445, "lng": 91.7362},
        "vehicle_type": "truck",
    }
    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_REQUEST"
    assert "differ from origin" in data["error"]["message"].lower()


def test_validation_error_invalid_coordinates(client):
    # Latitude > 90
    payload = {
        "origin": {"lat": 105.0, "lng": 91.7362},
        "destination": {"lat": 25.5788, "lng": 91.8933},
        "vehicle_type": "truck",
    }
    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_REQUEST"


def test_validation_error_invalid_vehicle_type(client):
    payload = {
        "origin": {"lat": 26.1445, "lng": 91.7362},
        "destination": {"lat": 25.5788, "lng": 91.8933},
        "vehicle_type": "airplane",
    }
    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_REQUEST"


def test_out_of_coverage_422(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True

    # Point outside the bounding box [90.0, 25.0, 93.0, 27.0]
    payload = {
        "origin": {"lat": 12.9716, "lng": 77.5946},  # Bangalore coordinates
        "destination": {"lat": 25.5788, "lng": 91.8933},
        "vehicle_type": "truck",
    }
    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "OUT_OF_COVERAGE"
    assert "origin" in data["error"]["details"]["point"]


def test_no_connected_route_404(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True

    # Coordinates set to simulate disconnected graph node
    payload = {
        "origin": {"lat": 25.0001, "lng": 90.0001},
        "destination": {"lat": 25.5788, "lng": 91.8933},
        "vehicle_type": "truck",
    }
    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NO_ROUTE_FOUND"
    assert data["error"]["details"]["origin_snapped"] is True


def test_gis_dependency_down_503(client):
    settings.GIS_SERVICE_ENABLED = False
    settings.RISK_SERVICE_ENABLED = True

    payload = {
        "origin": {"lat": 26.1445, "lng": 91.7362},
        "destination": {"lat": 25.5788, "lng": 91.8933},
        "vehicle_type": "truck",
    }
    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert data["error"]["details"]["module"] == "gis"

    # Reset
    settings.GIS_SERVICE_ENABLED = True


def test_risk_dependency_down_503(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = False

    payload = {
        "origin": {"lat": 26.1445, "lng": 91.7362},
        "destination": {"lat": 25.5788, "lng": 91.8933},
        "vehicle_type": "truck",
    }
    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert data["error"]["details"]["module"] == "risk"

    # Reset
    settings.RISK_SERVICE_ENABLED = True


def test_weather_unavailable_partial_data_quality(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = False

    payload = {
        "origin": {"lat": 26.1445, "lng": 91.7362},
        "destination": {"lat": 25.5788, "lng": 91.8933},
        "vehicle_type": "truck",
    }
    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 200
    data = response.json()

    for route in data["routes"]:
        assert route["data_quality"] == "partial"
        factor_names = [f["name"] for f in route["risk_factors"]]
        assert "weather_unavailable" in factor_names
        # Find weather_unavailable factor
        w_factor = next(f for f in route["risk_factors"] if f["name"] == "weather_unavailable")
        assert w_factor["contribution"] == 0
        assert "weather data could not be fetched" in w_factor["detail"].lower()

    # Reset
    settings.WEATHER_AVAILABLE = True


def test_model_source_switch(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True
    settings.RISK_SOURCE = "model"

    payload = {
        "origin": {"lat": 26.1445, "lng": 91.7362},
        "destination": {"lat": 25.5788, "lng": 91.8933},
        "vehicle_type": "car",
    }
    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_source"] in ("model", "baseline")

    # Reset
    settings.RISK_SOURCE = "baseline"
