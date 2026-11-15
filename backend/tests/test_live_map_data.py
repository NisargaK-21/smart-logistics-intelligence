import pytest

from backend.app.core.errors import (
    DependencyUnavailableException,
    InvalidRequestException,
    OutOfCoverageException,
)
from backend.app.services.gis_service import GISService
from backend.app.services.open_data_service import OpenDataService
from backend.app.services.risk_service import RiskService


def test_osrm_route_conversion_and_segment_cache(monkeypatch):
    service = GISService(router_url="https://router.example")
    monkeypatch.setattr(
        service,
        "_request_osrm",
        lambda origin, destination: {
            "code": "Ok",
            "routes": [
                {
                    "distance": 12000,
                    "duration": 900,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[91.7, 26.1], [91.8, 26.2]],
                    },
                    "legs": [
                        {
                            "steps": [
                                {
                                    "distance": 12000,
                                    "geometry": {
                                        "coordinates": [[91.7, 26.1], [91.8, 26.2]]
                                    },
                                },
                                {
                                    "distance": 0,
                                    "geometry": {
                                        "coordinates": [[91.8, 26.2], [91.8, 26.2]]
                                    },
                                },
                            ]
                        }
                    ],
                }
            ],
        },
    )

    routes = service.find_routes(
        {"lat": 26.1, "lng": 91.7},
        {"lat": 26.2, "lng": 91.8},
        "truck",
    )

    assert routes[0]["distance_km"] == 12
    assert routes[0]["duration_min"] == 15
    segments = service.get_segments(routes[0]["segment_ids"])
    assert segments[routes[0]["segment_ids"][0]]["length_km"] == 12
    assert segments[routes[0]["segment_ids"][0]]["coordinates"] == [
        [91.7, 26.1],
        [91.8, 26.2],
    ]


def test_route_plan_accepts_osrm_route_response(client, monkeypatch):
    from backend.app.core.config import settings
    from backend.app.services.gis_service import gis_service

    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True
    settings.RISK_SOURCE = "baseline"
    monkeypatch.setattr(gis_service, "_use_osrm", True)
    monkeypatch.setattr(
        gis_service,
        "_request_osrm",
        lambda *_: {
            "code": "Ok",
            "routes": [
                {
                    "distance": 12000,
                    "duration": 900,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[91.7, 26.1], [91.8, 26.2]],
                    },
                    "legs": [
                        {
                            "steps": [
                                {
                                    "distance": 12000,
                                    "geometry": {
                                        "coordinates": [[91.7, 26.1], [91.8, 26.2]]
                                    },
                                }
                            ]
                        }
                    ],
                }
            ],
        },
    )

    response = client.post(
        "/api/v1/routes/plan",
        json={
            "origin": {"lat": 26.1, "lng": 91.7},
            "destination": {"lat": 26.2, "lng": 91.8},
            "vehicle_type": "truck",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["routes"][0]["distance_km"] == 12
    assert body["routes"][0]["estimated_duration_minutes"] == 15
    assert body["routes"][0]["data_quality"] == "partial"
    assert len(body["routes"][0]["segments"]) == 1


@pytest.mark.parametrize(
    ("origin", "destination", "vehicle_type", "error"),
    [
        (
            {"lat": 0, "lng": 0},
            {"lat": 26.2, "lng": 91.8},
            "truck",
            OutOfCoverageException,
        ),
        (
            {"lat": 26.1, "lng": 91.7},
            {"lat": 26.2, "lng": 91.8},
            "bicycle",
            InvalidRequestException,
        ),
    ],
)
def test_osrm_validates_coverage_and_vehicle(
    monkeypatch, origin, destination, vehicle_type, error
):
    service = GISService(router_url="https://router.example")
    monkeypatch.setattr(
        service,
        "_request_osrm",
        lambda *_: pytest.fail("Invalid request must not reach OSRM"),
    )

    with pytest.raises(error):
        service.find_routes(origin, destination, vehicle_type)


def test_place_search_caches_provider_results(monkeypatch):
    service = OpenDataService()
    requests = []
    monkeypatch.setattr(
        service,
        "_get_json",
        lambda *args: requests.append(args) or [
            {"display_name": "Shillong, Meghalaya", "lat": "25.58", "lon": "91.89"}
        ],
    )

    first = service.search_places("  Shillong ")
    second = service.search_places("Shillong")

    assert first == second == [
        {"display_name": "Shillong, Meghalaya", "lat": 25.58, "lng": 91.89}
    ]
    assert len(requests) == 1


def test_place_search_throttle_timestamp_updates_on_provider_failure(monkeypatch):
    service = OpenDataService()
    monkeypatch.setattr("backend.app.services.open_data_service.time.monotonic", lambda: 123.0)

    def fail_request(*_):
        raise DependencyUnavailableException(module="open_data")

    monkeypatch.setattr(service, "_get_json", fail_request)
    with pytest.raises(DependencyUnavailableException):
        service.search_places("Shillong")

    assert service._last_place_request == 123.0


def test_weather_parser_caches_current_provider_values(monkeypatch):
    service = OpenDataService()
    requests = []
    monkeypatch.setattr(
        service,
        "_get_json",
        lambda *args: requests.append(args)
        or {
            "latitude": 25.58,
            "longitude": 91.89,
            "elevation": 1496,
            "current": {
                "time": "2026-11-13T10:00",
                "temperature_2m": 22.5,
                "precipitation": 2.0,
                "rain": 1.5,
                "weather_code": 61,
                "wind_speed_10m": 8.0,
                "wind_gusts_10m": 12.0,
            },
        },
    )

    first = service.get_current_weather(25.58, 91.89)
    second = service.get_current_weather(25.58, 91.89)

    assert first["source"] == "Open-Meteo"
    assert first["precipitation_mm"] == 2.0
    assert first["rain_mm"] == 1.5
    assert first["weather_code"] == 61
    assert first == second
    assert len(requests) == 1


def test_baseline_risk_score_includes_fetched_precipitation():
    service = RiskService()
    segment = {"segment_id": "step-1", "slope_deg": 0, "road_class": "unknown"}
    dry, _ = service.score([segment], {"weather": {"precipitation_mm": 0, "weather_code": 0}})
    rainy, _ = service.score([segment], {"weather": {"precipitation_mm": 6, "weather_code": 63}})

    assert rainy["step-1"]["score"] > dry["step-1"]["score"]
    assert "heavy_rainfall" in {
        factor["name"] for factor in rainy["step-1"]["factors"]
    }
