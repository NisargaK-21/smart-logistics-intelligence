"""Dataset checks Person 1 needs before the graph is trusted.

Runs on the fixture by default. Point ROUTING_DATA_PATH at roads_final.gpkg
to validate the full extracted network without committing it to Git.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from routing.geo import linestring_length_km
from routing.graph import graph_from_features
from routing.loader import load_features, default_data_path

REQUIRED_PROPERTIES = (
    "road_id",
    "road_type",
    "road_class",
    "length_km",
)


def _geometry_coords(geometry: dict) -> list[list[float]] | None:
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates")
    if geom_type == "LineString" and isinstance(coords, list) and len(coords) >= 2:
        return coords
    if geom_type == "MultiLineString" and coords:
        flat: list[list[float]] = []
        for part in coords:
            flat.extend(part)
        return flat if len(flat) >= 2 else None
    return None


def _undirected_components(graph) -> int:
    parent = {node: node for node in graph.nodes}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    seen = set()
    for node, edges in graph.adjacency.items():
        for edge in edges:
            key = tuple(sorted((edge.from_node, edge.to_node))) + (edge.segment_id,)
            if key in seen:
                continue
            seen.add(key)
            union(edge.from_node, edge.to_node)
    return len({find(node) for node in graph.nodes})


def validate_features(features: list[dict]) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    oneway = 0
    invalid_geom = 0
    missing_props: dict[str, int] = defaultdict(int)
    classes: dict[str, int] = defaultdict(int)
    geom_types: dict[str, int] = defaultdict(int)
    ids: list[str] = []
    lats: list[float] = []
    lngs: list[float] = []

    for index, feature in enumerate(features):
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        geom_types[str(geometry.get("type"))] += 1
        coords = _geometry_coords(geometry)
        if coords is None:
            invalid_geom += 1
            continue

        for key in REQUIRED_PROPERTIES:
            if key not in props or props[key] in (None, ""):
                missing_props[key] += 1

        road_id = props.get("road_id")
        if road_id:
            ids.append(str(road_id))

        is_oneway = props.get("is_oneway", props.get("oneway"))
        if str(is_oneway).lower() in {"1", "true", "yes"} or is_oneway is True:
            oneway += 1

        road_class = str(props.get("road_class") or "unknown")
        classes[road_class] += 1

        for lng, lat in coords:
            lngs.append(float(lng))
            lats.append(float(lat))

        length = props.get("length_km")
        try:
            length_val = float(length) if length is not None else linestring_length_km(coords)
            if length_val <= 0:
                errors.append(f"Feature {index} ({road_id}) has non-positive length.")
        except (TypeError, ValueError):
            errors.append(f"Feature {index} ({road_id}) has invalid length_km.")

    if not features:
        errors.append("Dataset is empty.")
    if invalid_geom:
        errors.append(f"Invalid or non-line geometries: {invalid_geom}.")
    if missing_props:
        warnings.append(f"Missing required attributes: {dict(missing_props)}")

    duplicate_ids = len(ids) - len(set(ids))
    if duplicate_ids:
        errors.append(f"Duplicate road_id values: {duplicate_ids}.")

    crs_ok = True
    if lats and (min(lats) < -90 or max(lats) > 90 or min(lngs) < -180 or max(lngs) > 180):
        crs_ok = False
        errors.append("Coordinates fall outside WGS84 lat/lng ranges. Expected EPSG:4326.")

    graph = graph_from_features(features)
    components = _undirected_components(graph) if graph.nodes else 0
    if components > 1:
        warnings.append(
            f"{components} weakly connected components. Routing will fail across gaps."
        )

    report = {
        "feature_count": len(features),
        "segment_count": len(graph.segments),
        "node_count": len(graph.nodes),
        "oneway_count": oneway,
        "connected_components": components,
        "crs_epsg4326": crs_ok,
        "bbox": graph.bbox,
        "road_classes": dict(classes),
        "geometry_types": dict(geom_types),
        "errors": errors,
        "warnings": warnings,
        "ok": not errors,
    }
    return report


def validate_path(path: Path | None = None) -> dict:
    path = path or default_data_path()
    report = validate_features(load_features(path))
    report["path"] = str(path)
    return report


def main() -> int:
    report = validate_path()
    print("=" * 60)
    print("GIS DATASET VALIDATION")
    print("=" * 60)
    print(f"Path: {report['path']}")
    print(f"Features: {report['feature_count']:,}")
    print(f"Graph segments: {report['segment_count']:,}")
    print(f"Graph nodes: {report['node_count']:,}")
    print(f"CRS EPSG:4326: {report['crs_epsg4326']}")
    print(f"One-way segments: {report['oneway_count']:,}")
    print(f"Connected components: {report['connected_components']}")
    print(f"BBox [minLng, minLat, maxLng, maxLat]: {report['bbox']}")
    print(f"Road classes: {report['road_classes']}")
    print(f"Geometry types: {report['geometry_types']}")
    if report["warnings"]:
        print("\nWarnings:")
        for item in report["warnings"]:
            print(f"- {item}")
    print("\n" + "=" * 60)
    if report["ok"]:
        print("VALIDATION PASSED")
        return 0
    print("VALIDATION FAILED")
    for item in report["errors"]:
        print(f"- {item}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
