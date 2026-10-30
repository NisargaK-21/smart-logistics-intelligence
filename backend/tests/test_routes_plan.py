import asyncio
from pathlib import Path

from starlette.requests import Request

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.route_plan import RoutePlanResponse
from backend.app.services.gis_service import gis_service


FIXTURES_DIR = Path(__file__).parent / "fixtures"
CONTRACT_QUERY = {
    "origin": {"lat": 26.1445, "lng": 91.7362},
    "destination": {"lat": 26.1801, "lng": 91.7001},
    "vehicle_type": "truck",
}


def test_plan_routes_success(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True
    settings.RISK_SOURCE = "baseline"

    payload = {
        "origin": {"lat": 26.1801, "lng": 91.7001},
        "destination": {"lat": 26.1401, "lng": 91.7399},
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


def test_plan_routes_valid_contract_query(client):
    """The documented frontend query is covered by the fixture network."""
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True
    settings.RISK_SOURCE = "baseline"

    response = client.post("/api/v1/routes/plan", json=CONTRACT_QUERY)

    assert response.status_code == 200
    data = response.json()
    assert data["routes"]
    assert data["recommended_route_id"] == data["routes"][0]["route_id"]


def test_route_score_aggregation_formula(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True

    payload = {
        "origin": {"lat": 26.1801, "lng": 91.7001},
        "destination": {"lat": 26.1401, "lng": 91.7399},
        "vehicle_type": "van",
    }

    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 200
    data = response.json()

    for route in data["routes"]:
        segments = gis_service.get_segments(
            [segment["segment_id"] for segment in route["segments"]]
        )
        total_length = sum(segments[sid]["length_km"] for sid in segments)
        weighted_mean = sum(
            segments[segment["segment_id"]]["length_km"] * segment["risk_score"]
            for segment in route["segments"]
        ) / total_length
        expected_score = round(
            0.7 * weighted_mean
            + 0.3 * max(segment["risk_score"] for segment in route["segments"])
        )
        assert route["risk_score"] == expected_score

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
    assert data["error"]["message"] == "Destination must differ from origin"
    assert data["error"]["details"] == {"field": "destination"}


def test_validation_error_invalid_coordinates(client):
    # Latitude > 90
    payload = {
        "origin": {"lat": 200.0, "lng": 91.7362},
        "destination": {"lat": 26.1401, "lng": 91.7399},
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
        "vehicle_type": "bike",
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
        "origin": {"lat": 10.0, "lng": 80.0},
        "destination": {"lat": 11.0, "lng": 81.0},
        "vehicle_type": "truck",
    }
    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "OUT_OF_COVERAGE"
    assert "origin" in data["error"]["details"]["point"]


def test_missing_vehicle_type_uses_contract_error_shape(client):
    payload = {
        "origin": {"lat": 26.1445, "lng": 91.7362},
        "destination": {"lat": 26.19, "lng": 91.77},
    }

    response = client.post("/api/v1/routes/plan", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_REQUEST"
    assert data["error"]["details"] == {"vehicle_type": "Field required"}
    assert "detail" not in data


def test_route_plan_openapi_declares_error_responses(client):
    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    expected = {
        "/api/v1/routes/plan": ("post", ("400", "404", "422", "500", "503")),
        "/api/v1/health": ("get", ("500", "503")),
        "/api/v1/meta/coverage": ("get", ("500", "503")),
    }
    for path, (method, status_codes) in expected.items():
        operation = paths[path][method]
        for status_code in status_codes:
            assert operation["responses"][status_code]["content"]["application/json"]["schema"]["$ref"].endswith(
                "/ErrorResponse"
            )


def test_unhandled_exception_uses_contract_error_shape():
    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/api/v1/routes/plan",
        "headers": [],
    })
    handler = app.exception_handlers[Exception]
    response = asyncio.run(handler(request, RuntimeError("internal implementation detail")))

    assert response.status_code == 500
    body = ErrorResponse.model_validate_json(response.body)
    assert body.error.code == "INTERNAL_ERROR"
    assert body.error.message == "An unexpected internal server error occurred."
    assert body.error.details == {"error_type": "RuntimeError"}


def test_published_mock_responses_match_contract():
    for filename in ("route-success.json", "route-partial.json"):
        response = RoutePlanResponse.model_validate_json(
            (FIXTURES_DIR / filename).read_text(encoding="utf-8")
        )
        assert response.routes
        assert response.recommended_route_id in {
            route.route_id for route in response.routes
        }

    error = ErrorResponse.model_validate_json(
        (FIXTURES_DIR / "error-no-route.json").read_text(encoding="utf-8")
    )
    assert error.error.code == "NO_ROUTE_FOUND"


def test_no_connected_route_404(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True

    # Coordinates set to simulate disconnected graph node
    payload = {
        "origin": {"lat": 26.1801, "lng": 91.7001},
        "destination": {"lat": 26.3001, "lng": 91.9001},
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
        "origin": {"lat": 26.1801, "lng": 91.7001},
        "destination": {"lat": 26.1401, "lng": 91.7399},
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
        "origin": {"lat": 26.1801, "lng": 91.7001},
        "destination": {"lat": 26.1401, "lng": 91.7399},
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
        "origin": {"lat": 26.1801, "lng": 91.7001},
        "destination": {"lat": 26.1401, "lng": 91.7399},
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


def test_heavy_rain_can_change_recommended_route(client, monkeypatch):
    """Verify recommendation changes when the risk module reports heavy rain."""
    from backend.app.services.gis_service import gis_service
    from backend.app.services.risk_service import risk_service

    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True
    settings.RISK_SOURCE = "baseline"

    candidates = gis_service.find_routes(
        origin=CONTRACT_QUERY["origin"],
        destination=CONTRACT_QUERY["destination"],
        vehicle_type=CONTRACT_QUERY["vehicle_type"],
    )
    assert len(candidates) >= 2
    safest_route_segments = set(candidates[0]["segment_ids"])

    weather_scenario = {"heavy_rain": False}

    def score_for_weather(segments, context):
        scores = {}
        for segment in segments:
            is_safest_route = segment["segment_id"] in safest_route_segments
            if weather_scenario["heavy_rain"]:
                score = 90 if is_safest_route else 20
                factor = "heavy_rainfall"
            else:
                score = 20 if is_safest_route else 70
                factor = "moderate_rainfall"
            scores[segment["segment_id"]] = {
                "score": score,
                "factors": [{"name": factor, "contribution": score}],
                "data_quality": "complete",
            }
        return scores, "baseline"

    monkeypatch.setattr(risk_service, "score", score_for_weather)

    normal_response = client.post("/api/v1/routes/plan", json=CONTRACT_QUERY)
    assert normal_response.status_code == 200
    normal_data = normal_response.json()
    normal_recommendation = normal_data["recommended_route_id"]
    assert normal_recommendation == candidates[0]["route_id"]

    weather_scenario["heavy_rain"] = True
    rainy_response = client.post("/api/v1/routes/plan", json=CONTRACT_QUERY)
    assert rainy_response.status_code == 200
    rainy_data = rainy_response.json()
    assert rainy_data["recommended_route_id"] != normal_recommendation
    assert rainy_data["recommended_route_id"] == candidates[1]["route_id"]
    recommended = next(
        route
        for route in rainy_data["routes"]
        if route["route_id"] == rainy_data["recommended_route_id"]
    )
    assert "heavy_rainfall" in {
        factor["name"] for factor in recommended["risk_factors"]
    }


def test_missing_terrain_data_is_partial_not_silently_safe(client, monkeypatch):
    from backend.app.services.gis_service import gis_service

    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True
    original_get_segments = gis_service.get_segments

    def get_segments_without_slope(segment_ids):
        segments = original_get_segments(segment_ids)
        for segment in segments.values():
            segment["slope_deg"] = None
        return segments

    monkeypatch.setattr(gis_service, "get_segments", get_segments_without_slope)
    response = client.post("/api/v1/routes/plan", json={
        "origin": {"lat": 26.1801, "lng": 91.7001},
        "destination": {"lat": 26.1401, "lng": 91.7399},
        "vehicle_type": "truck",
    })

    assert response.status_code == 200
    for route in response.json()["routes"]:
        assert route["data_quality"] == "partial"
        assert "terrain_unavailable" in {factor["name"] for factor in route["risk_factors"]}


def test_model_source_switch(client):
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True
    settings.RISK_SOURCE = "model"

    payload = {
        "origin": {"lat": 26.1801, "lng": 91.7001},
        "destination": {"lat": 26.1401, "lng": 91.7399},
        "vehicle_type": "car",
    }
    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_source"] == "baseline"

    # Reset
    settings.RISK_SOURCE = "baseline"


def test_validation_error_departure_time_without_offset(client):
    payload = {
        "origin": {"lat": 26.1801, "lng": 91.7001},
        "destination": {"lat": 26.1401, "lng": 91.7399},
        "vehicle_type": "truck",
        "departure_time": "2026-10-28T10:00:00",
    }

    response = client.post("/api/v1/routes/plan", json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
