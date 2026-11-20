"""Automated tests for Empirical Disaster Ground-Truth Matching Pipeline.

GitHub Issue #32: Empirical Disaster Ground Truth and Class Imbalance.
Tests ingestion, filtering, spatial road matching, weather matching,
cross-source duplicate detection, background negative sampling guardrails,
and preservation of the production deterministic baseline.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.scripts import prepare_empirical_disaster_ground_truth as pipeline
from ml import risk_assessment
from backend.app.core.config import settings
from backend.app.services.risk_service import RiskService


def test_is_in_corridor_and_ner_range():
    # Guwahati
    assert pipeline.is_in_corridor(26.1445, 91.7362) is True
    # Shillong
    assert pipeline.is_in_corridor(25.5788, 91.8933) is True
    # Delhi (outside corridor and NER)
    assert pipeline.is_in_corridor(28.6139, 77.2090) is False
    assert pipeline.is_in_ner_range(28.6139, 77.2090) is False
    # Dibrugarh (inside NER, outside corridor)
    assert pipeline.is_in_corridor(27.4728, 94.9119) is False
    assert pipeline.is_in_ner_range(27.4728, 94.9119) is True
    # Invalid coordinates
    assert pipeline.is_in_corridor(np.nan, 91.7) is False
    assert pipeline.is_in_ner_range(25.5, np.nan) is False


def test_normalize_state_name():
    assert pipeline.normalize_state_name("Meghālaya") == "Meghalaya"
    assert pipeline.normalize_state_name("Nāgāland") == "Nagaland"
    assert pipeline.normalize_state_name("Assam") == "Assam"
    assert pipeline.normalize_state_name(None) == "Unknown"
    assert pipeline.normalize_state_name(np.nan) == "Unknown"


def test_haversine_km_accuracy():
    # Guwahati to Shillong straight-line distance is ~65-75 km
    dist = pipeline.haversine_km(26.1445, 91.7362, 25.5788, 91.8933)
    assert 60.0 < dist < 80.0
    # Zero distance
    assert pipeline.haversine_km(26.0, 91.0, 26.0, 91.0) == 0.0


def test_nasa_glc_loading_and_filtering():
    df = pipeline.load_nasa_glc(states={"Assam", "Meghalaya"})
    assert not df.empty
    assert "source" in df.columns
    assert (df["source"] == "NASA_GLC").all()
    assert (df["disaster_type"] == "landslide").all()
    assert df["coordinate_valid"].all()
    assert (df["latitude"].notna() & df["longitude"].notna()).all()
    # Check that events have valid timestamps
    assert df["event_timestamp"].notna().sum() > 0
    # Check corridor presence
    assert df["is_corridor"].sum() > 0


def test_field_reports_loading():
    df = pipeline.load_field_reports()
    assert len(df) == 15
    assert (df["source"] == "field_reports").all()
    assert set(df["disaster_type"].unique()).issuperset({"landslide", "flood", "road_blockage"})
    assert df["coordinate_valid"].all()
    assert df["is_corridor"].sum() == 8


def test_ifi_floods_loading_and_year_resolution():
    df = pipeline.load_ifi_floods(states={"Assam", "Meghalaya"})
    assert not df.empty
    assert (df["source"] == "IFI_Impacts").all()
    assert (df["disaster_type"] == "flood").all()
    assert (df["granularity"] == "district_level_aggregate").all()
    # Verify that coordinates are strictly NaN (quarantined district aggregates)
    assert df["latitude"].isna().all()
    assert df["longitude"].isna().all()
    assert not df["coordinate_valid"].any()

    # Verify that UEI year resolution prevents century ambiguity (> 2030)
    valid_times = df["event_timestamp"].dropna()
    assert (valid_times.dt.year <= 2026).all(), "2-digit years must not parse into future centuries (> 2026)"


def test_match_events_to_roads_within_and_exceeding_threshold():
    # Synthetic roads
    roads_df = pd.DataFrame([
        {"road_id": "road_1", "road_class": "major", "road_name": "GS Road", "lat": 26.1440, "lon": 91.7360},
        {"road_id": "road_2", "road_class": "secondary", "road_name": "Shillong Way", "lat": 25.5780, "lon": 91.8930},
    ])

    events_df = pd.DataFrame([
        # Near road_1 (~0.06 km)
        {
            "event_id": "EV1",
            "source": "test",
            "coordinate_valid": True,
            "latitude": 26.1445,
            "longitude": 91.7362,
        },
        # Far from both (> 200 km, e.g. Silchar)
        {
            "event_id": "EV2",
            "source": "test",
            "coordinate_valid": True,
            "latitude": 24.7800,
            "longitude": 92.8000,
        },
        # Missing coordinates
        {
            "event_id": "EV3",
            "source": "test",
            "coordinate_valid": False,
            "latitude": np.nan,
            "longitude": np.nan,
        },
    ])

    matched = pipeline.match_events_to_roads(events_df, roads_df, max_distance_km=10.0)

    # EV1 should match road_1
    ev1 = matched[matched["event_id"] == "EV1"].iloc[0]
    assert bool(ev1["road_matched"]) is True
    assert ev1["matched_road_id"] == "road_1"
    assert ev1["road_distance_km"] < 1.0

    # EV2 should exceed spatial threshold
    ev2 = matched[matched["event_id"] == "EV2"].iloc[0]
    assert bool(ev2["road_matched"]) is False
    assert ev2["road_match_status"] == "unmatched_exceeds_spatial_threshold"

    # EV3 missing coords
    ev3 = matched[matched["event_id"] == "EV3"].iloc[0]
    assert bool(ev3["road_matched"]) is False
    assert ev3["road_match_status"] == "unmatched_missing_coordinates"


def test_match_events_to_weather_within_and_outside_window():
    stations_df = pd.DataFrame([
        {"location_id": 3, "latitude": 26.186, "longitude": 91.678},
    ])
    weather_df = pd.DataFrame([
        {
            "location_id": 3,
            "time": pd.Timestamp("2026-10-01 08:00:00", tz="UTC"),
            "precipitation_mm": 5.0,
            "precipitation_sum_3h_mm": 10.0,
            "precipitation_sum_6h_mm": 15.0,
            "precipitation_sum_24h_mm": 30.0,
            "wind_speed_kmh": 12.0,
            "temperature_c": 22.0,
        }
    ])

    events_df = pd.DataFrame([
        # Contemporary event
        {
            "event_id": "E_CONTEMP",
            "coordinate_valid": True,
            "latitude": 26.1445,
            "longitude": 91.7362,
            "event_timestamp": pd.Timestamp("2026-10-01 08:15:00", tz="UTC"),
        },
        # Historical event out of range (2010)
        {
            "event_id": "E_OLD",
            "coordinate_valid": True,
            "latitude": 26.1445,
            "longitude": 91.7362,
            "event_timestamp": pd.Timestamp("2010-06-15 12:00:00", tz="UTC"),
        },
    ])

    matched = pipeline.match_events_to_weather(events_df, stations_df, weather_df)

    contemp = matched[matched["event_id"] == "E_CONTEMP"].iloc[0]
    assert bool(contemp["weather_matched"]) is True
    assert contemp["precipitation_mm"] == 5.0
    assert contemp["nearest_station_id"] == 3

    old = matched[matched["event_id"] == "E_OLD"].iloc[0]
    assert bool(old["weather_matched"]) is False
    assert old["weather_match_status"] == "unmatched_temporal_out_of_range"


def test_cross_source_duplicate_detection():
    # Two events from different sources on the same date and 1 km apart
    events_df = pd.DataFrame([
        {
            "event_id": "NASA_1",
            "source": "NASA_GLC",
            "disaster_type": "landslide",
            "coordinate_valid": True,
            "latitude": 26.1445,
            "longitude": 91.7362,
            "event_timestamp": pd.Timestamp("2026-10-01 08:00:00", tz="UTC"),
        },
        {
            "event_id": "FIELD_1",
            "source": "field_reports",
            "disaster_type": "landslide",
            "coordinate_valid": True,
            "latitude": 26.1450,
            "longitude": 91.7370,
            "event_timestamp": pd.Timestamp("2026-10-01 09:30:00", tz="UTC"),
        },
        # Distinct event 100 km away
        {
            "event_id": "NASA_2",
            "source": "NASA_GLC",
            "disaster_type": "landslide",
            "coordinate_valid": True,
            "latitude": 25.0000,
            "longitude": 93.0000,
            "event_timestamp": pd.Timestamp("2026-10-01 08:00:00", tz="UTC"),
        },
    ])

    duplicates = pipeline.detect_cross_source_duplicates(events_df, max_dist_km=5.0, max_hours=24.0)
    assert len(duplicates) == 1
    assert duplicates[0]["event_1"] == "NASA_1"
    assert duplicates[0]["event_2"] == "FIELD_1"
    assert duplicates[0]["distance_km"] < 2.0


def test_negative_background_sampling_guardrails():
    roads_df = pd.DataFrame([
        {"road_id": f"road_{i}", "road_class": "major", "road_name": "Test Road", "lat": 26.0 + i * 0.01, "lon": 91.7 + i * 0.01}
        for i in range(20)
    ])
    weather_df = pd.DataFrame([
        {
            "location_id": 3,
            "time": pd.Timestamp("2025-06-01 10:00:00", tz="UTC") + pd.Timedelta(hours=i),
            "precipitation_mm": float(i % 5),
            "precipitation_sum_3h_mm": 5.0,
            "precipitation_sum_6h_mm": 10.0,
            "precipitation_sum_24h_mm": float((i % 10) * 5),
            "wind_speed_kmh": 10.0,
            "temperature_c": 25.0,
        }
        for i in range(50)
    ])
    stations_df = pd.DataFrame([
        {"location_id": 3, "latitude": 26.186, "longitude": 91.678}
    ])
    # Disaster event near road_0 at 2025-06-01 12:00:00
    pos_events = pd.DataFrame([
        {
            "event_id": "DISASTER_1",
            "coordinate_valid": True,
            "latitude": 26.0,
            "longitude": 91.7,
            "event_timestamp": pd.Timestamp("2025-06-01 12:00:00", tz="UTC"),
        }
    ])

    samples = pipeline.sample_background_negative_controls(
        roads_df,
        weather_df,
        stations_df,
        pos_events,
        n_samples=25,
        exclusion_radius_km=25.0,
        exclusion_hours=72.0,
    )

    assert len(samples) > 0
    assert (samples["is_disaster"] == 0).all()
    assert (samples["sample_type"] == "background_non_event").all()
    assert (samples["disaster_type"] == "none").all()
    # Check that provenance contains non-event disclaimer
    assert "not verified safe road traversal" in samples["provenance"].iloc[0]


def test_district_aggregates_isolated_from_road_labels():
    audit_path = pipeline.OUTPUT_DIR / "empirical_disaster_audit_report.json"
    assert audit_path.is_file(), "Audit report must exist"

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["sample_counts"]["district_flood_events_ifi"] > 0
    assert audit["sample_counts"]["total_point_events"] > 0

    # Read ML ground truth dataset
    ml_path = pipeline.OUTPUT_DIR / "empirical_ground_truth_ml.csv"
    assert ml_path.is_file()
    ml_df = pd.read_csv(ml_path)

    # Confirm all rows in empirical_ground_truth_ml have valid coordinates
    assert ml_df["coordinate_valid"].all()
    assert ml_df["latitude"].notna().all()
    assert ml_df["longitude"].notna().all()
    # Confirm no IFI district aggregate has been forced into the segment-level dataset
    assert not (ml_df["source"] == "IFI_Impacts").any()


def test_production_baseline_and_deterministic_scoring_preserved():
    # Production scorer must remain baseline
    service = RiskService()
    assert settings.RISK_SOURCE == "baseline"
    segment = {
        "segment_id": "seg-test",
        "coordinates": [[91.7362, 26.1445], [91.7400, 26.1500]],
        "road_class": "national_highway",
        "slope_deg": 5.0,
    }
    scores, source = service.score([segment], {})
    assert source == "baseline"
    assert "seg-test" in scores
    assert scores["seg-test"]["score"] >= 0
    assert "factors" in scores["seg-test"]
    assert "data_quality" in scores["seg-test"]

    # Direct module-level score contract check
    ml_scores = risk_assessment.score([segment], {})
    assert "seg-test" in ml_scores
    assert ml_scores["seg-test"]["risk_level"] in ("low", "medium", "high")
    assert ml_scores["seg-test"]["risk_source"] == "baseline"
