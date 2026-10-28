"""Fixture-only tests. Do not require the full OSM extract or geopandas."""

from __future__ import annotations

import unittest

from routing.exceptions import InvalidRequestError, NoRouteFoundError, OutOfCoverageError
from routing.graph import graph_from_features
from routing.loader import FIXTURE_PATH, load_features, load_graph
from routing.service import GisService
from routing.validate import validate_features


class DatasetTests(unittest.TestCase):
    def test_fixture_validation_passes(self):
        report = validate_features(load_features(FIXTURE_PATH))
        self.assertTrue(report["ok"], report["errors"])
        self.assertTrue(report["crs_epsg4326"])
        self.assertGreaterEqual(report["oneway_count"], 1)
        self.assertGreaterEqual(report["connected_components"], 2)

    def test_graph_builds_from_fixture(self):
        graph = load_graph(FIXTURE_PATH)
        self.assertGreaterEqual(len(graph.segments), 12)
        self.assertEqual(len(graph.bbox), 4)


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.gis = GisService(load_graph(FIXTURE_PATH))
        self.origin = {"lat": 26.1801, "lng": 91.7001}
        self.destination = {"lat": 26.1401, "lng": 91.7399}

    def test_find_routes_returns_one_to_three_candidates(self):
        routes = self.gis.find_routes(self.origin, self.destination, "truck")
        self.assertGreaterEqual(len(routes), 1)
        self.assertLessEqual(len(routes), 3)
        first = routes[0]
        self.assertEqual(first.route_id, "route-1")
        self.assertGreater(first.distance_km, 0)
        self.assertGreater(first.duration_min, 0)
        self.assertEqual(first.geometry["type"], "LineString")
        lng, lat = first.geometry["coordinates"][0]
        self.assertTrue(-180 <= lng <= 180)
        self.assertTrue(-90 <= lat <= 90)
        self.assertGreaterEqual(len(first.segment_ids), 1)

    def test_second_route_is_meaningfully_different(self):
        routes = self.gis.find_routes(self.origin, self.destination, "car", max_routes=2)
        self.assertGreaterEqual(len(routes), 2)
        a = set(routes[0].segment_ids)
        b = set(routes[1].segment_ids)
        self.assertTrue(a - b or b - a)

    def test_get_segments_returns_risk_attributes(self):
        routes = self.gis.find_routes(self.origin, self.destination, "van")
        records = self.gis.get_segments(routes[0].segment_ids)
        self.assertEqual(len(records), len(routes[0].segment_ids))
        sample = records[0].as_dict()
        self.assertIn("length_km", sample)
        self.assertIn("road_class", sample)
        self.assertIn("slope_deg", sample)
        self.assertIn("is_oneway", sample)
        self.assertIn("coordinates", sample)

    def test_coverage_bbox(self):
        coverage = self.gis.get_coverage()
        self.assertEqual(len(coverage["bbox"]), 4)
        self.assertEqual(coverage["vehicle_types"], ["truck", "van", "car"])

    def test_same_origin_and_destination_rejected(self):
        with self.assertRaises(InvalidRequestError) as ctx:
            self.gis.find_routes(self.origin, self.origin, "car")
        self.assertEqual(ctx.exception.code, "INVALID_REQUEST")

    def test_invalid_coordinates_rejected(self):
        with self.assertRaises(InvalidRequestError):
            self.gis.find_routes({"lat": 200, "lng": 91.7}, self.destination, "car")

    def test_invalid_vehicle_rejected(self):
        with self.assertRaises(InvalidRequestError):
            self.gis.find_routes(self.origin, self.destination, "bike")

    def test_out_of_coverage(self):
        with self.assertRaises(OutOfCoverageError) as ctx:
            self.gis.find_routes(
                {"lat": 28.6, "lng": 77.2},
                self.destination,
                "car",
            )
        self.assertEqual(ctx.exception.code, "OUT_OF_COVERAGE")

    def test_no_route_to_disconnected_island(self):
        with self.assertRaises(NoRouteFoundError) as ctx:
            self.gis.find_routes(
                self.origin,
                {"lat": 26.3001, "lng": 91.9001},
                "car",
            )
        self.assertEqual(ctx.exception.code, "NO_ROUTE_FOUND")

    def test_oneway_is_respected(self):
        # AB and BC are eastbound only. Westbound C -> A along that corridor
        # must not use those reverse edges.
        westbound = self.gis.find_routes(
            {"lat": 26.1800, "lng": 91.7400},
            {"lat": 26.1800, "lng": 91.7000},
            "car",
        )
        used = set(westbound[0].segment_ids)
        self.assertNotIn("seg-ab", used)
        self.assertNotIn("seg-bc", used)


class GraphUnitTests(unittest.TestCase):
    def test_empty_linestring_skipped(self):
        graph = graph_from_features(
            [
                {
                    "type": "Feature",
                    "properties": {"road_id": "x"},
                    "geometry": {"type": "LineString", "coordinates": [[91.7, 26.1]]},
                }
            ]
        )
        self.assertEqual(graph.segments, {})


if __name__ == "__main__":
    unittest.main()
