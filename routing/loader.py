"""Load the fixture GeoJSON, or the full road GeoPackage when present."""

from __future__ import annotations

import json
import os
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


def _features_from_gpkg(path: Path) -> list[dict]:
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise RuntimeError(
            "geopandas is required to load the full road GeoPackage. "
            "Install routing/requirements.txt or keep using the fixture network."
        ) from exc

    frame = gpd.read_file(path)
    if frame.crs is None:
        frame = frame.set_crs(4326)
    else:
        frame = frame.to_crs(4326)
    return json.loads(frame.to_json())["features"]


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
    return graph_from_features(load_features(path))
