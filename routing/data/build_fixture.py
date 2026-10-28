"""Regenerate fixture_network.geojson. Run from repo root:

    python routing/data/build_fixture.py
"""

from __future__ import annotations

import json
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

R = 6371.0


def haversine(lng1, lat1, lng2, lat2) -> float:
    p1, p2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlmb = radians(lng2 - lng1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlmb / 2) ** 2
    return 2 * R * asin(sqrt(a))


def feature(road_id, osm_id, a, b, road_type, road_class, oneway=False, slope=4.0, surface="asphalt"):
    length = round(haversine(a[0], a[1], b[0], b[1]), 6)
    return {
        "type": "Feature",
        "properties": {
            "road_id": road_id,
            "osm_id": osm_id,
            "road_type": road_type,
            "road_class": road_class,
            "length_km": length,
            "is_oneway": oneway,
            "oneway": oneway,
            "slope_deg": slope,
            "surface": surface,
            "lat": round((a[1] + b[1]) / 2, 6),
            "lon": round((a[0] + b[0]) / 2, 6),
        },
        "geometry": {"type": "LineString", "coordinates": [list(a), list(b)]},
    }


def main() -> None:
    A, B, C = (91.70, 26.18), (91.72, 26.18), (91.74, 26.18)
    D, E, F = (91.70, 26.16), (91.72, 26.16), (91.74, 26.16)
    G, H, I = (91.70, 26.14), (91.72, 26.14), (91.74, 26.14)
    J, K = (91.90, 26.30), (91.91, 26.30)

    features = [
        feature("seg-ab", 1, A, B, "primary", "major", oneway=True, slope=2.0),
        feature("seg-bc", 2, B, C, "primary", "major", oneway=True, slope=2.5),
        feature("seg-de", 3, D, E, "secondary", "major", slope=5.0),
        feature("seg-ef", 4, E, F, "secondary", "major", slope=6.0),
        feature("seg-gh", 5, G, H, "tertiary", "collector", slope=8.0, surface="compacted"),
        feature("seg-hi", 6, H, I, "tertiary", "collector", slope=7.0, surface="compacted"),
        feature("seg-ad", 7, A, D, "residential", "local", slope=9.0),
        feature("seg-dg", 8, D, G, "residential", "local", slope=11.0, surface="gravel"),
        feature("seg-be", 9, B, E, "secondary", "major", slope=4.0),
        feature("seg-eh", 10, E, H, "tertiary", "collector", slope=10.0),
        feature("seg-cf", 11, C, F, "primary", "major", slope=3.0),
        feature("seg-fi", 12, F, I, "primary", "major", slope=3.5),
        # Isolated island so validation reports more than one component.
        feature("seg-isolated", 99, J, K, "service", "local", slope=1.0, surface="dirt"),
    ]

    payload = {
        "type": "FeatureCollection",
        "name": "fixture_network",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
        "features": features,
    }
    out = Path(__file__).with_name("fixture_network.geojson")
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(features)} segments)")


if __name__ == "__main__":
    main()
