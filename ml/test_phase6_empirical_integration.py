"""Automated test suite for Phase 6: Integrate Historical ERA5 Weather into Empirical Ground Truth.

GitHub Issue #32 — Phase 6:
Tests dataset schemas, event-level vs segment-level road match distinction,
temporal balancing of negative controls (2007-2016 and 2022-2025),
spatial-temporal non-overlap exclusion buffers, field report provenance isolation,
and district flood aggregate quarantine.
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "ml" / "data" / "processed" / "disaster"

MATCHED_PATH = DATA_DIR / "empirical_events_matched.csv"
DISTRICT_PATH = DATA_DIR / "district_flood_events.csv"
NEGATIVE_PATH = DATA_DIR / "empirical_negative_controls.csv"
ML_DATASET_PATH = DATA_DIR / "empirical_ground_truth_ml.csv"
AUDIT_REPORT_PATH = DATA_DIR / "empirical_disaster_audit_report.json"


def test_matched_events_integrity_and_road_distinction():
    assert MATCHED_PATH.is_file()
    df = pd.read_csv(MATCHED_PATH)
    assert len(df) == 457, f"Expected 457 point events, got {len(df)}"

    # Source breakdown
    assert (df["source"] == "NASA_GLC").sum() == 442
    assert (df["source"] == "field_reports").sum() == 15

    # 100% weather matched (NASA via ERA5, Field via station)
    assert (df["weather_matched"] == True).all()

    # Road matching distinction
    matched_roads = df["road_matched"] == True
    assert matched_roads.sum() == 402, f"Expected 402 road-matched events, got {matched_roads.sum()}"

    # 55 events exceeded 10km threshold
    unmatched_roads = df["road_matched"] == False
    assert unmatched_roads.sum() == 55
    unmatched_df = df[unmatched_roads]
    assert (unmatched_df["source"] == "NASA_GLC").all()
    assert (unmatched_df["road_match_status"] == "unmatched_exceeds_spatial_threshold").all()
    assert (unmatched_df["road_distance_km"] > 10.0).all()


def test_ml_ground_truth_dataset_composition_and_zero_nulls():
    assert ML_DATASET_PATH.is_file()
    df = pd.read_csv(ML_DATASET_PATH)
    assert len(df) == 1402, f"Expected 1402 rows, got {len(df)}"

    # Binary split: 402 positives, 1000 negatives
    positives = df[df["is_disaster"] == 1]
    negatives = df[df["is_disaster"] == 0]
    assert len(positives) == 402
    assert len(negatives) == 1000
    assert (positives["sample_type"] == "empirical_disaster_event").all()
    assert (negatives["sample_type"] == "background_non_event").all()

    # Zero nulls across all 25 features
    null_counts = df.isnull().sum()
    assert null_counts.sum() == 0, f"Found unexpected nulls in ML dataset: {null_counts[null_counts > 0].to_dict()}"

    # Disaster type counts
    dt_counts = df["disaster_type"].value_counts().to_dict()
    assert dt_counts["none"] == 1000
    assert dt_counts["landslide"] == 390  # 387 NASA + 3 Field
    assert dt_counts["flood"] == 3
    assert dt_counts["road_blockage"] == 3
    assert dt_counts["heavy_rainfall"] == 2
    assert dt_counts["road_damage"] == 2
    assert dt_counts["bridge_damage"] == 2


def test_event_vs_segment_label_distinction():
    df_matched = pd.read_csv(MATCHED_PATH)
    df_ml = pd.read_csv(ML_DATASET_PATH)

    nasa_matched_ids = set(df_matched[df_matched["source"] == "NASA_GLC"]["event_id"])
    nasa_ml_ids = set(df_ml[df_ml["source"] == "NASA_GLC"]["event_id"])

    # Event catalog must retain all 442 NASA events
    assert len(nasa_matched_ids) == 442

    # Segment ML labels must strictly retain only the 387 road-matched events
    assert len(nasa_ml_ids) == 387
    assert nasa_ml_ids.issubset(nasa_matched_ids)

    # Excluded 55 remote events must not be in ML labels
    excluded_ids = nasa_matched_ids - nasa_ml_ids
    assert len(excluded_ids) == 55
    for eid in excluded_ids:
        assert eid not in nasa_ml_ids


def test_field_reports_provenance_isolated():
    df_ml = pd.read_csv(ML_DATASET_PATH)

    field_subset = df_ml[df_ml["source"] == "field_reports"]
    assert len(field_subset) == 15
    assert (field_subset["provenance"] == "field_reports: empirically verified disaster incident").all()

    nasa_subset = df_ml[df_ml["source"] == "NASA_GLC"]
    assert len(nasa_subset) == 387
    assert (nasa_subset["provenance"] == "NASA_GLC: empirical disaster event + Open-Meteo ERA5 Reanalysis").all()


def test_negative_controls_expanded_temporal_balance():
    assert NEGATIVE_PATH.is_file()
    df_neg = pd.read_csv(NEGATIVE_PATH)
    assert len(df_neg) == 1000, f"Expected 1000 negative controls, got {len(df_neg)}"

    years = df_neg["event_date"].str[:4].astype(int)
    hist_count = (years <= 2016).sum()
    recent_count = (years >= 2022).sum()

    assert hist_count == 500, f"Expected 500 negative controls from 2007-2016, got {hist_count}"
    assert recent_count == 500, f"Expected 500 negative controls from 2022-2025, got {recent_count}"

    # Verify no duplicates
    duplicates = df_neg.duplicated(subset=["matched_road_id", "event_date"]).sum()
    assert duplicates == 0, f"Found {duplicates} duplicate road-time pairs in negative controls"

    # Verify 150mm rainfall guardrail
    assert (df_neg["precipitation_sum_24h_mm"] <= 150.0).all()


def test_district_floods_strictly_quarantined():
    assert DISTRICT_PATH.is_file()
    df_dist = pd.read_csv(DISTRICT_PATH)
    assert len(df_dist) == 965

    # Coordinates strictly quarantined
    assert df_dist["latitude"].isna().all()
    assert df_dist["longitude"].isna().all()
    assert not df_dist["coordinate_valid"].any()

    # Zero district flood records in ML segment ground truth
    df_ml = pd.read_csv(ML_DATASET_PATH)
    assert df_ml["source"].isin(["IFI-Impacts", "IFI_Impacts", "CWC"]).sum() == 0


def test_audit_report_consistency():
    assert AUDIT_REPORT_PATH.is_file()
    with open(AUDIT_REPORT_PATH, "r", encoding="utf-8") as f:
        rpt = json.load(f)

    assert rpt["sample_counts"]["total_point_events"] == 457
    assert rpt["sample_counts"]["nasa_glc_events"] == 442
    assert rpt["sample_counts"]["field_report_events"] == 15
    assert rpt["sample_counts"]["road_matched_positive_events"] == 402
    assert rpt["sample_counts"]["combined_ml_rows"] == 1402
    assert rpt["sample_counts"]["negative_background_controls"] == 1000
    assert rpt["ml_dataset_binary_distribution"]["class_ratio"] == "1 : 2.49"
    assert rpt["cross_source_duplicates"]["detected_overlap_count"] == 0
    assert rpt["missing_values_and_coordinate_validity"]["ml_dataset_null_features"] == {}
