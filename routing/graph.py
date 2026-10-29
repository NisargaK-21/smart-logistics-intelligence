"""Road graph: nodes at segment endpoints, directed edges, nearest-node snap."""

from __future__ import annotations

from dataclasses import dataclass, field

from routing.geo import haversine_km, linestring_length_km, node_id, node_key
from routing.models import SPEED_KMH, SegmentRecord, VEHICLE_TYPES


@dataclass
class GraphEdge:
    from_node: str
    to_node: str
    segment_id: str
    length_km: float
    reversed: bool
    road_class: str


@dataclass
class RoadGraph:
    nodes: dict[str, tuple[float, float]] = field(default_factory=dict)
    adjacency: dict[str, list[GraphEdge]] = field(default_factory=dict)
    segments: dict[str, SegmentRecord] = field(default_factory=dict)
    bbox: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])

    def add_node(self, lng: float, lat: float) -> str:
        nid = node_id(lng, lat)
        if nid not in self.nodes:
            self.nodes[nid] = node_key(lng, lat)
            self.adjacency.setdefault(nid, [])
        return nid

    def add_edge(self, edge: GraphEdge) -> None:
        self.adjacency.setdefault(edge.from_node, []).append(edge)

    def snap(self, lng: float, lat: float) -> tuple[str, float]:
        """Return (node_id, distance_km) for the nearest graph node."""
        best_id = ""
        best_km = float("inf")
        for nid, (n_lng, n_lat) in self.nodes.items():
            dist = haversine_km(lng, lat, n_lng, n_lat)
            if dist < best_km:
                best_km = dist
                best_id = nid
        return best_id, best_km

    def duration_min(self, segment_ids: list[str], vehicle_type: str) -> float:
        speeds = SPEED_KMH[vehicle_type]
        total = 0.0
        for sid in segment_ids:
            segment = self.segments[sid]
            speed = speeds.get(segment.road_class, speeds["unknown"])
            total += (segment.length_km / max(speed, 1.0)) * 60.0
        return total


def _coords_from_geometry(geometry: dict) -> list[list[float]]:
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates")
    if geom_type == "LineString":
        return [[float(c[0]), float(c[1])] for c in coords]
    if geom_type == "MultiLineString":
        merged: list[list[float]] = []
        for part in coords:
            for c in part:
                point = [float(c[0]), float(c[1])]
                if not merged or merged[-1] != point:
                    merged.append(point)
        return merged
    raise ValueError(f"Unsupported geometry type: {geom_type}")


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _as_optional_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def graph_from_features(features: list[dict]) -> RoadGraph:
    graph = RoadGraph()
    min_lng = min_lat = float("inf")
    max_lng = max_lat = float("-inf")

    for feature in features:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coords = _coords_from_geometry(geometry)
        if len(coords) < 2:
            continue

        segment_id = str(props.get("road_id") or props.get("segment_id") or "")
        if not segment_id:
            continue

        length_km = _as_optional_float(props.get("length_km"))
        if length_km is None or length_km <= 0:
            length_km = linestring_length_km(coords)

        record = SegmentRecord(
            segment_id=segment_id,
            length_km=length_km,
            road_class=str(props.get("road_class") or "unknown"),
            road_type=str(props.get("road_type") or "unknown"),
            slope_deg=_as_optional_float(props.get("slope_deg")),
            is_oneway=_as_bool(props.get("is_oneway") if "is_oneway" in props else props.get("oneway")),
            coordinates=coords,
            surface=props.get("surface"),
        )
        graph.segments[segment_id] = record

        start_lng, start_lat = coords[0]
        end_lng, end_lat = coords[-1]
        start = graph.add_node(start_lng, start_lat)
        end = graph.add_node(end_lng, end_lat)

        forward = GraphEdge(
            from_node=start,
            to_node=end,
            segment_id=segment_id,
            length_km=length_km,
            reversed=False,
            road_class=record.road_class,
        )
        graph.add_edge(forward)
        if not record.is_oneway:
            graph.add_edge(
                GraphEdge(
                    from_node=end,
                    to_node=start,
                    segment_id=segment_id,
                    length_km=length_km,
                    reversed=True,
                    road_class=record.road_class,
                )
            )

        for lng, lat in coords:
            min_lng = min(min_lng, lng)
            max_lng = max(max_lng, lng)
            min_lat = min(min_lat, lat)
            max_lat = max(max_lat, lat)

    pad_lng = max((max_lng - min_lng) * 0.05, 0.01)
    pad_lat = max((max_lat - min_lat) * 0.05, 0.01)
    graph.bbox = [
        min_lng - pad_lng,
        min_lat - pad_lat,
        max_lng + pad_lng,
        max_lat + pad_lat,
    ]
    return graph


def vehicle_type_ok(vehicle_type: str) -> bool:
    return vehicle_type in VEHICLE_TYPES
