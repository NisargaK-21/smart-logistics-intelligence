"""Shortest path (Dijkstra) plus penalised alternatives."""

from __future__ import annotations

import heapq

from routing.graph import GraphEdge, RoadGraph
from routing.models import RouteCandidate


def _dijkstra(
    graph: RoadGraph,
    source: str,
    target: str,
    penalties: dict[str, float] | None = None,
) -> list[GraphEdge] | None:
    penalties = penalties or {}
    dist = {source: 0.0}
    prev: dict[str, GraphEdge] = {}
    heap: list[tuple[float, str]] = [(0.0, source)]

    while heap:
        cost, node = heapq.heappop(heap)
        if cost > dist.get(node, float("inf")):
            continue
        if node == target:
            break
        for edge in graph.adjacency.get(node, []):
            weight = edge.length_km * penalties.get(edge.segment_id, 1.0)
            next_cost = cost + weight
            if next_cost < dist.get(edge.to_node, float("inf")):
                dist[edge.to_node] = next_cost
                prev[edge.to_node] = edge
                heapq.heappush(heap, (next_cost, edge.to_node))

    if source == target:
        return []
    if target not in prev:
        return None

    path: list[GraphEdge] = []
    node = target
    while node != source:
        edge = prev[node]
        path.append(edge)
        node = edge.from_node
    path.reverse()
    return path


def _collapse_segment_ids(path: list[GraphEdge]) -> list[str]:
    ids: list[str] = []
    for edge in path:
        if not ids or ids[-1] != edge.segment_id:
            ids.append(edge.segment_id)
    return ids


def _route_geometry(graph: RoadGraph, path: list[GraphEdge]) -> dict:
    coords: list[list[float]] = []
    for edge in path:
        segment = graph.segments[edge.segment_id]
        part = list(segment.coordinates)
        if edge.reversed:
            part.reverse()
        if coords and coords[-1] == part[0]:
            coords.extend(part[1:])
        else:
            coords.extend(part)
    return {"type": "LineString", "coordinates": coords}


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def find_k_paths(
    graph: RoadGraph,
    source: str,
    target: str,
    vehicle_type: str,
    max_routes: int = 3,
) -> list[RouteCandidate]:
    """Return 1–3 routes. Later routes penalise segments already used."""
    routes: list[RouteCandidate] = []
    penalties: dict[str, float] = {}

    for index in range(max_routes):
        path = _dijkstra(graph, source, target, penalties)
        if path is None:
            break
        segment_ids = _collapse_segment_ids(path)
        if not segment_ids:
            break
        if any(_jaccard(segment_ids, existing.segment_ids) > 0.8 for existing in routes):
            for sid in segment_ids:
                penalties[sid] = penalties.get(sid, 1.0) * 5.0
            continue

        distance = sum(graph.segments[sid].length_km for sid in segment_ids)
        routes.append(
            RouteCandidate(
                route_id=f"route-{len(routes) + 1}",
                distance_km=distance,
                duration_min=graph.duration_min(segment_ids, vehicle_type),
                geometry=_route_geometry(graph, path),
                segment_ids=segment_ids,
            )
        )
        for sid in segment_ids:
            penalties[sid] = penalties.get(sid, 1.0) * 4.0

        if index == 0 and max_routes == 1:
            break

    return routes
