"""CLI: python -m routing demo | python -m routing validate"""

from __future__ import annotations

import argparse
import json
import sys

from routing.service import get_service
from routing.validate import main as validate_main

DEMO_ORIGIN = {"lat": 26.1801, "lng": 91.7001}
DEMO_DESTINATION = {"lat": 26.1401, "lng": 91.7399}


def demo() -> int:
    service = get_service()
    coverage = service.get_coverage()
    print("Coverage:", json.dumps(coverage, indent=2))
    routes = service.find_routes(DEMO_ORIGIN, DEMO_DESTINATION, "truck")
    print(f"\nFound {len(routes)} route(s) for truck {DEMO_ORIGIN} -> {DEMO_DESTINATION}")
    for route in routes:
        print(
            f"  {route.route_id}: {route.distance_km:.2f} km, "
            f"{route.duration_min:.1f} min, {len(route.segment_ids)} segments"
        )
        segments = service.get_segments(route.segment_ids)
        print("    segments:", ", ".join(item.segment_id for item in segments))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smart Logistics GIS routing module")
    parser.add_argument("command", nargs="?", default="demo", choices=["demo", "validate"])
    args = parser.parse_args(argv)
    if args.command == "validate":
        return validate_main()
    return demo()


if __name__ == "__main__":
    sys.exit(main())
