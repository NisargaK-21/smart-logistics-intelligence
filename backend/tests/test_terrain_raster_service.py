"""Automated tests for DEM raster querying, spatial index, and route risk integration.

Covers:
- Native DEM resolution preservation and spatial indexing.
- Accurate elevation, slope, and ruggedness sampling.
- Out-of-coverage and missing-tile handling (never substitutes mock/synthetic values).
- Route segment integration and data_quality status (complete vs partial).
"""

from __future__ import annotations

from pathlib import Path
import pytest

from backend.app.core.config import settings
from backend.app.services.gis_service import GISService, gis_service
from backend.app.services.risk_service import risk_service
from backend.app.services.terrain_service import TerrainService, terrain_service
from ml.scripts.bootstrap_terrain import verify_tile, tiles_for_bbox, format_tile_name


def test_copernicus_dem_native_resolution_and_indexing():
    """Verify DEM tile metadata and native resolution without downsampling."""
    terrain_service._ensure_indexed()
    tile = terrain_service.get_tile_for_point(91.7001, 26.1801)
    assert tile is not None, "Guwahati tile N26_E091 should be indexed."
    assert tile.valid is True
    assert tile.width == 3600
    assert tile.height == 3600
    # Native 1 arc-second resolution (~0.00027778 degrees per pixel)
    assert abs(tile.res_x_deg - (1.0 / 3600.0)) < 1e-6
    assert abs(tile.res_y_deg - (1.0 / 3600.0)) < 1e-6
    assert tile.min_lon <= 91.7001 <= tile.max_lon
    assert tile.min_lat <= 26.1801 <= tile.max_lat


def test_point_sampling_within_coverage():
    """Sample known coordinates in Guwahati for elevation, slope, and ruggedness."""
    result = terrain_service.sample_point(91.7001, 26.1801)
    assert result["elevation_m"] is not None
    assert result["slope_deg"] is not None
    assert result["ruggedness"] is not None
    assert 30.0 <= result["elevation_m"] <= 100.0
    assert result["slope_deg"] >= 0.0
    assert result["ruggedness"] >= 0.0

    # Ridge/hill coordinate (higher elevation & slope)
    ridge = terrain_service.sample_point(91.7200, 26.1600)
    assert ridge["elevation_m"] is not None
    assert ridge["elevation_m"] > result["elevation_m"]
    assert ridge["slope_deg"] > 5.0
    assert ridge["ruggedness"] > 0.0


def test_point_sampling_out_of_coverage_returns_none_never_mock():
    """Coordinates outside indexed tiles must return None and never mock values."""
    # Delhi coordinate (outside indexed NER tiles)
    result = terrain_service.sample_point(77.2090, 28.6139)
    assert result["elevation_m"] is None
    assert result["slope_deg"] is None
    assert result["ruggedness"] is None

    # Ocean / coordinate outside bounding box
    result_ocean = terrain_service.sample_point(0.0, 0.0)
    assert result_ocean["elevation_m"] is None
    assert result_ocean["slope_deg"] is None
    assert result_ocean["ruggedness"] is None


def test_linestring_query_full_coverage():
    """Linestring inside tile coverage returns complete aggregated metrics."""
    coords = [[91.7001, 26.1801], [91.7200, 26.1600], [91.7399, 26.1401]]
    query = terrain_service.query_linestring(coords)
    assert query["terrain_available"] is True
    assert query["elevation_m"] is not None
    assert query["slope_deg"] is not None
    assert query["ruggedness"] is not None
    assert query["elevation_m"] > 0
    assert query["slope_deg"] >= 0
    assert query["ruggedness"] >= 0


def test_linestring_query_crosses_into_missing_coverage():
    """Linestring that leaves tile coverage must fail safe with terrain_available=False."""
    coords = [[91.7001, 26.1801], [77.2090, 28.6139]]
    query = terrain_service.query_linestring(coords)
    assert query["terrain_available"] is False
    assert query["elevation_m"] is None
    assert query["slope_deg"] is None
    assert query["ruggedness"] is None


def test_osrm_step_segments_enriched_with_terrain_attributes():
    """OSRM route steps should receive genuine terrain attributes from DEM tiles."""
    mock_payload = {
        "code": "Ok",
        "routes": [
            {
                "distance": 6000.0,
                "duration": 480.0,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[91.7001, 26.1801], [91.7200, 26.1600]],
                },
                "legs": [
                    {
                        "steps": [
                            {
                                "distance": 6000.0,
                                "geometry": {
                                    "coordinates": [[91.7001, 26.1801], [91.7200, 26.1600]]
                                },
                            }
                        ]
                    }
                ],
            }
        ],
    }

    gis = GISService(router_url="http://mock-osrm-service")
    gis._request_osrm = lambda o, d: mock_payload

    routes = gis.find_routes(
        {"lat": 26.1801, "lng": 91.7001}, {"lat": 26.1600, "lng": 91.7200}, "truck"
    )
    assert len(routes) == 1
    segments = gis.get_segments(routes[0]["segment_ids"])
    seg = list(segments.values())[0]

    assert seg["slope_deg"] is not None
    assert seg["elevation_m"] is not None
    assert seg["ruggedness"] is not None
    assert seg["slope_deg"] > 0
    assert seg["elevation_m"] > 0


def test_route_plan_integration_complete_data_quality(client):
    """When both weather and genuine DEM terrain are available, data_quality is complete."""
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True

    response = client.post(
        "/api/v1/routes/plan",
        json={
            "origin": {"lat": 26.1801, "lng": 91.7001},
            "destination": {"lat": 26.1401, "lng": 91.7399},
            "vehicle_type": "truck",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) >= 1
    top_route = data["routes"][0]

    # Data quality must be complete because both weather and terrain attributes are present
    assert top_route["data_quality"] == "complete"
    assert "terrain_unavailable" not in {f["name"] for f in top_route["risk_factors"]}

    # Segments must have populated terrain attributes
    for segment in top_route["segments"]:
        assert segment.get("slope_deg") is not None
        assert segment.get("elevation_m") is not None
        assert segment.get("ruggedness") is not None


def test_route_plan_integration_missing_terrain_yields_partial(client, monkeypatch):
    """When DEM terrain is missing/unavailable, data_quality is partial and terrain_unavailable factor is attached."""
    settings.GIS_SERVICE_ENABLED = True
    settings.RISK_SERVICE_ENABLED = True
    settings.WEATHER_AVAILABLE = True

    # Simulate missing terrain data by querying out of coverage or returning None
    monkeypatch.setattr(
        terrain_service,
        "query_linestring",
        lambda coords, **kwargs: {
            "terrain_available": False,
            "elevation_m": None,
            "slope_deg": None,
            "ruggedness": None,
        },
    )

    response = client.post(
        "/api/v1/routes/plan",
        json={
            "origin": {"lat": 26.1801, "lng": 91.7001},
            "destination": {"lat": 26.1401, "lng": 91.7399},
            "vehicle_type": "truck",
        },
    )

    assert response.status_code == 200
    data = response.json()
    for route in data["routes"]:
        assert route["data_quality"] == "partial"
        factor_names = {f["name"] for f in route["risk_factors"]}
        assert "terrain_unavailable" in factor_names


def test_bootstrap_tile_naming_and_bbox():
    """Verify tile naming convention for Copernicus DEM GLO-30."""
    name = format_tile_name(26, 91)
    assert name == "Copernicus_DSM_COG_10_N26_00_E091_00_DEM"

    bbox_tiles = tiles_for_bbox(91.2, 26.1, 91.8, 26.9)
    assert bbox_tiles == ["Copernicus_DSM_COG_10_N26_00_E091_00_DEM"]


def test_guwahati_shillong_complete_corridor_coverage():
    """Verify both N25_E091 and N26_E091 together cover the complete Guwahati-Shillong corridor."""
    terrain_service.refresh_index()
    tile_names = {t.filename for t in terrain_service._tiles}
    assert "Copernicus_DSM_COG_10_N25_00_E091_00_DEM.tif" in tile_names
    assert "Copernicus_DSM_COG_10_N26_00_E091_00_DEM.tif" in tile_names

    # Guwahati in N26
    guwahati = terrain_service.sample_point(91.7362, 26.1445)
    assert guwahati["elevation_m"] is not None
    assert 40.0 <= guwahati["elevation_m"] <= 100.0

    # Shillong in N25
    shillong = terrain_service.sample_point(91.8933, 25.5788)
    assert shillong["elevation_m"] is not None
    assert 1300.0 <= shillong["elevation_m"] <= 1600.0

    # Continuous corridor query across N26 into N25
    corridor = [
        [91.7362, 26.1445],  # Guwahati
        [91.8600, 26.0900],  # Jorabat
        [91.8800, 25.9000],  # Nongpoh (N25)
        [91.8800, 25.7500],  # Umsning (N25)
        [91.8900, 25.6600],  # Umiam (N25)
        [91.8933, 25.5788],  # Shillong (N25)
    ]
    query = terrain_service.query_linestring(corridor)
    assert query["terrain_available"] is True
    assert query["elevation_m"] is not None
    assert query["slope_deg"] is not None
    assert query["ruggedness"] is not None
    assert query["min_elevation_m"] >= 40.0
    assert query["max_elevation_m"] >= 1400.0
