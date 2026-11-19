"""Load the fixture GeoJSON, or the full road GeoPackage when present."""

from __future__ import annotations

import json
import os
import sqlite3
import struct
from pathlib import Path

from routing.graph import RoadGraph, graph_from_features

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = Path(__file__).resolve().parent
FIXTURE_PATH = PACKAGE_DIR / "data" / "fixture_network.geojson"
FULL_GPKG_PATH = ROOT / "ml" / "data" / "final" / "roads" / "roads_final.gpkg"


def default_data_path() -> Path:
    env_path = os.environ.get("ROUTING_DATA_PATH")
    if env_path:
        return Path(env_path)

    use_full = os.environ.get("ROUTING_USE_FULL", "").strip().lower() in {"1", "true", "yes"}
    if use_full and FULL_GPKG_PATH.exists():
        return FULL_GPKG_PATH
    return FIXTURE_PATH


def _features_from_geojson(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection":
        raise ValueError(f"{path} is not a GeoJSON FeatureCollection.")
    return payload.get("features") or []


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _iter_gpkg_features(path: Path):
    try:
        from shapely.geometry import mapping
        from shapely import wkb
    except ImportError as exc:
        raise RuntimeError(
            "Shapely is required to load the full road GeoPackage. "
            "Install routing/requirements.txt or keep using the fixture network."
        ) from exc

    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    with sqlite3.connect(path) as connection:
        geometry_info = connection.execute(
            "SELECT table_name, column_name, srs_id "
            "FROM gpkg_geometry_columns LIMIT 1"
        ).fetchone()
        if geometry_info is None:
            raise ValueError(f"{path} has no GeoPackage geometry table.")

        table_name, geometry_column, srs_id = geometry_info
        table_sql = _quote_identifier(table_name)
        geometry_sql = _quote_identifier(geometry_column)
        columns = [
            row[1]
            for row in connection.execute(f"PRAGMA table_info({table_sql})")
            if row[1] not in {geometry_column, "fid"}
        ]
        properties_sql = ", ".join(_quote_identifier(column) for column in columns)

        transformer = None
        if srs_id not in (None, 4326):
            try:
                from pyproj import Transformer
                from shapely.ops import transform
            except ImportError as exc:
                raise RuntimeError(
                    "pyproj is required to transform the road GeoPackage to WGS84."
                ) from exc
            transformer = Transformer.from_crs(srs_id, 4326, always_xy=True)

        query = (
            f"SELECT {properties_sql}, {geometry_sql} FROM {table_sql} "
            f"WHERE {geometry_sql} IS NOT NULL"
        )
        cursor = connection.execute(query)
        for row in cursor:
            properties = dict(zip(columns, row[:-1]))
            blob = row[-1]
            if len(blob) < 8 or blob[:2] != b"GP":
                raise ValueError(f"{path} contains an invalid GeoPackage geometry.")

            flags = blob[3]
            envelope_type = (flags >> 1) & 0x07
            if envelope_type not in envelope_sizes:
                raise ValueError(f"{path} contains an unsupported GeoPackage envelope.")
            geometry_offset = 8 + envelope_sizes[envelope_type]
            geometry = wkb.loads(blob[geometry_offset:])
            if transformer is not None:
                geometry = transform(transformer.transform, geometry)

            yield {
                "type": "Feature",
                "properties": properties,
                "geometry": mapping(geometry),
            }


def _features_from_gpkg(path: Path) -> list[dict]:
    return list(_iter_gpkg_features(path))


def load_features(path: Path | None = None) -> list[dict]:
    path = path or default_data_path()
    if not path.exists():
        raise FileNotFoundError(f"Routing dataset not found: {path}")
    if path.suffix.lower() in {".geojson", ".json"}:
        return _features_from_geojson(path)
    if path.suffix.lower() in {".gpkg", ".shp"}:
        return _features_from_gpkg(path)
    raise ValueError(f"Unsupported routing dataset format: {path.suffix}")


def load_graph(path: Path | None = None) -> RoadGraph:
    path = path or default_data_path()
    if not path.exists():
        raise FileNotFoundError(f"Routing dataset not found: {path}")
    if path.suffix.lower() in {".gpkg", ".shp"}:
        return graph_from_features(_iter_gpkg_features(path))
    return graph_from_features(load_features(path))
