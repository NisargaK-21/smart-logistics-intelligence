"""Automated test suite for Independent Ground-Truth Validation and Leakage Audit.

GitHub Issue #32 — Phase 7: Independent Validation & Leakage Audit.
Tests NASA road-impact evidence tiers, negative control buffer compliance,
target leakage prohibitions (road_distance_km, fatalities, metadata IDs),
cross-source meteorological consistency, and chronological evaluation splits.
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "ml" / "data" / "processed" / "disaster"

ML_DATASET_PATH = DATA_DIR / "empirical_ground_truth_ml.csv"
MATCHED_PATH = DATA_DIR / "empirical_events_matched.csv"
NEGATIVE_PATH = DATA_DIR / "empirical_negative_controls.csv"
AUDIT_JSON_PATH = DATA_DIR / "independent_ground_truth_leakage_audit.json"
RAW_NASA_PATH = ROOT / "ml" / "data" / "raw" / "landslides" / "nasa_global_landslide_catalog.csv"


def test_nasa_road_matching_evidence_tiers():
    raw_nasa = pd.read_csv(RAW_NASA_PATH, low_memory=False)
    ml_df = pd.read_csv(ML_DATASET_PATH)
    nasa_ml = ml_df[ml_df["source"] == "NASA_GLC"].copy()
    assert len(nasa_ml) == 387

    raw_sub = raw_nasa.copy()
    raw_sub["event_id_str"] = "NASA_GLC_" + raw_sub["event_id"].astype(str)
    merged = nasa_ml.merge(
        raw_sub[["event_id_str", "landslide_setting", "location_description", "event_title", "event_description"]],
        left_on="event_id",
        right_on="event_id_str",
        how="left",
    )

    text_combined = (
        merged["landslide_setting"].fillna("") + " " +
        merged["location_description"].fillna("") + " " +
        merged["event_title"].fillna("") + " " +
        merged["event_description"].fillna("")
    ).str.lower()

    road_keywords = ["road", "highway", "nh-", "nh ", "national highway", "state highway", "route", "traffic", "blocked", "vehicle", "car", "bus", "truck"]
    has_road_mention = text_combined.apply(lambda t: any(k in t for k in road_keywords))
    has_road_setting = merged["landslide_setting"].isin(["above_road", "below_road", "retaining_wall"])

    def categorize(row, mention, setting):
        d = row["road_distance_km"]
        if d <= 1.0 and (mention or setting):
            return "confirmed_road_impact"
        elif d <= 0.5:
            return "high_confidence_road_proximate"
        elif d <= 5.0 and (mention or setting):
            return "medium_confidence_road_corridor"
        else:
            return "regional_landscape_landslide_unconfirmed_road_impact"

    tiers = [categorize(row, has_road_mention.iloc[i], has_road_setting.iloc[i]) for i, row in merged.iterrows()]
    tier_counts = pd.Series(tiers).value_counts().to_dict()

    assert tier_counts["confirmed_road_impact"] == 160
    assert tier_counts["high_confidence_road_proximate"] == 89
    assert tier_counts["medium_confidence_road_corridor"] == 84
    assert tier_counts["regional_landscape_landslide_unconfirmed_road_impact"] == 54


def test_target_leakage_prohibition_road_distance_km():
    """Verify that road_distance_km is completely polarized and must never be a predictive feature."""
    df = pd.read_csv(ML_DATASET_PATH)
    pos = df[df["is_disaster"] == 1]
    neg = df[df["is_disaster"] == 0]

    # Every negative control was sampled on-segment (distance == 0.0)
    assert (neg["road_distance_km"] == 0.0).all()

    # Every positive event was matched via proximity (distance > 0.0)
    assert (pos["road_distance_km"] > 0.0).all()

    # Document that road_distance_km has 100% mutual separation
    min_pos_dist = pos["road_distance_km"].min()
    assert min_pos_dist > 0.0, "Positive event has 0.0 distance which contradicts proximity matching"


def test_target_leakage_prohibition_fatalities():
    """Verify that fatalities is an outcome consequence and must be excluded from feature matrix."""
    df = pd.read_csv(ML_DATASET_PATH)
    neg = df[df["is_disaster"] == 0]
    pos = df[df["is_disaster"] == 1]

    assert (neg["fatalities"] == 0.0).all()
    assert (pos["fatalities"] > 0.0).sum() > 0  # 109 NASA events have fatalities recorded


def test_negative_control_exclusion_and_guardrail():
    neg_df = pd.read_csv(NEGATIVE_PATH)
    matched_df = pd.read_csv(MATCHED_PATH)

    assert len(neg_df) == 1000

    # Max 24h precipitation below guardrail
    assert (neg_df["precipitation_sum_24h_mm"] <= 150.0).all()
    assert neg_df["precipitation_sum_24h_mm"].max() < 100.0

    # Zero duplicate road-time pairs
    assert neg_df.duplicated(subset=["matched_road_id", "event_date"]).sum() == 0

    # Spatial-temporal separation check
    pos_dt = pd.to_datetime(matched_df["event_date"], format="mixed", utc=True)
    neg_dt = pd.to_datetime(neg_df["event_date"], format="mixed", utc=True)

    # Convert coordinates to radians
    pos_coords_rad = np.radians(matched_df[["latitude", "longitude"]].values)
    neg_coords_rad = np.radians(neg_df[["latitude", "longitude"]].values)

    def haversine_vector(lat1, lon1, lat2, lon2):
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2
        return 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))

    violations = 0
    for i in range(len(neg_df)):
        t_neg = neg_dt.iloc[i]
        diff_h = np.abs((t_neg - pos_dt).dt.total_seconds().values) / 3600.0
        nearby_time_mask = diff_h <= 72.0
        if np.any(nearby_time_mask):
            sub_pos_rad = pos_coords_rad[nearby_time_mask]
            dists = haversine_vector(
                neg_coords_rad[i, 0], neg_coords_rad[i, 1],
                sub_pos_rad[:, 0], sub_pos_rad[:, 1]
            )
            if np.any(dists <= 25.0):
                violations += 1

    assert violations == 0, f"Found {violations} violations of 25km/72h buffer"


def test_cross_source_meteorological_consistency():
    df = pd.read_csv(ML_DATASET_PATH)

    neg_era5 = df[(df["is_disaster"] == 0) & (df["event_date"].str[:4].astype(int) <= 2016)]
    neg_station = df[(df["is_disaster"] == 0) & (df["event_date"].str[:4].astype(int) >= 2022)]

    assert len(neg_era5) == 500
    assert len(neg_station) == 500

    # Mean temperature difference < 1.0 C
    temp_diff = abs(neg_era5["temperature_c"].mean() - neg_station["temperature_c"].mean())
    assert temp_diff < 1.0, f"Temperature discrepancy too large: {temp_diff:.2f} C"

    # Mean hourly precipitation difference < 0.1 mm
    precip_diff = abs(neg_era5["precipitation_mm"].mean() - neg_station["precipitation_mm"].mean())
    assert precip_diff < 0.1, f"Precipitation discrepancy too large: {precip_diff:.2f} mm"

    # Mean wind speed difference < 0.5 km/h
    wind_diff = abs(neg_era5["wind_speed_kmh"].mean() - neg_station["wind_speed_kmh"].mean())
    assert wind_diff < 0.5, f"Wind speed discrepancy too large: {wind_diff:.2f} km/h"


def test_chronological_evaluation_split():
    df = pd.read_csv(ML_DATASET_PATH)
    years = df["event_date"].str[:4].astype(int)

    train = df[years <= 2013]
    val = df[(years >= 2014) & (years <= 2016)]
    test = df[years >= 2022]

    # Verify counts
    assert len(train) == 598
    assert len(val) == 289
    assert len(test) == 515
    assert len(train) + len(val) + len(test) == 1402

    # Verify positive and negative representation
    assert (train["is_disaster"] == 1).sum() == 255
    assert (train["is_disaster"] == 0).sum() == 343

    assert (val["is_disaster"] == 1).sum() == 132
    assert (val["is_disaster"] == 0).sum() == 157

    assert (test["is_disaster"] == 1).sum() == 15  # All 15 field reports
    assert (test["is_disaster"] == 0).sum() == 500

    # Complete temporal disjointness
    assert train["event_date"].max() < val["event_date"].min()
    assert val["event_date"].max() < test["event_date"].min()
