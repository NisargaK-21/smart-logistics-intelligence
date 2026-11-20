"""Automated test suite for NASA GLC Historical ERA5 Weather Acquisition.

GitHub Issue #32 — Phase 5: Historical Weather Acquisition.
Verifies schema, spatial grid cell accuracy, temporal matching methods,
meteorological physical constraints, geographic breakdowns, and offline
feature extraction logic.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.scripts import fetch_nasa_historical_weather_era5 as fetcher

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "ml" / "data" / "processed" / "disaster" / "nasa_glc_historical_weather_era5.csv"
REPORT_PATH = ROOT / "ml" / "data" / "processed" / "disaster" / "nasa_glc_era5_audit_report.json"
CACHE_DIR = ROOT / "ml" / "data" / "cache" / "open_meteo_era5"
RAW_NASA_PATH = ROOT / "ml" / "data" / "raw" / "landslides" / "nasa_global_landslide_catalog.csv"


def test_era5_dataset_schema_and_completeness():
    assert CSV_PATH.is_file(), f"Expected CSV file at {CSV_PATH}"
    df = pd.read_csv(CSV_PATH)
    assert len(df) == 442, f"Expected 442 records, got {len(df)}"

    expected_cols = {
        "event_id",
        "original_id",
        "source",
        "disaster_type",
        "event_date",
        "event_timestamp",
        "state",
        "district",
        "latitude",
        "longitude",
        "coordinate_valid",
        "is_corridor",
        "is_assam_meghalaya",
        "is_wider_ner",
        "era5_grid_latitude",
        "era5_grid_longitude",
        "era5_grid_elevation_m",
        "era5_grid_distance_km",
        "weather_matched",
        "weather_match_status",
        "temporal_matching_method",
        "is_reported_time_exact",
        "matched_weather_time",
        "precipitation_mm",
        "precipitation_sum_3h_mm",
        "precipitation_sum_6h_mm",
        "precipitation_sum_24h_mm",
        "temperature_c",
        "relative_humidity_pct",
        "wind_speed_kmh",
        "wind_gusts_kmh",
        "cloud_cover_pct",
        "daily_precipitation_total_mm",
        "daily_max_hourly_precipitation_mm",
        "provenance",
    }
    assert expected_cols.issubset(df.columns), f"Missing columns: {expected_cols - set(df.columns)}"

    # Confirm 0 missing values across all 35 columns
    null_counts = df.isnull().sum()
    assert null_counts.sum() == 0, f"Found unexpected null values: {null_counts[null_counts > 0].to_dict()}"

    # Confirm 100% matched
    assert df["weather_matched"].all() is np.True_ or df["weather_matched"].all() is True
    assert (df["source"] == "NASA_GLC").all()
    assert (df["disaster_type"] == "landslide").all()


def test_era5_spatial_grid_matching_accuracy():
    df = pd.read_csv(CSV_PATH)
    grid_dists = df["era5_grid_distance_km"]

    # All distances must be within 30 km threshold
    assert (grid_dists <= 30.0).all()
    assert grid_dists.max() < 20.0, f"Expected max distance < 20km, got {grid_dists.max()}"
    assert grid_dists.median() < 6.0, f"Expected median distance < 6km, got {grid_dists.median()}"

    # Verify grid coordinates are geographically plausible
    assert df["era5_grid_latitude"].between(20.0, 32.0).all()
    assert df["era5_grid_longitude"].between(87.0, 98.0).all()
    assert df["era5_grid_elevation_m"].between(-50.0, 6000.0).all()


def test_era5_temporal_matching_methods():
    df = pd.read_csv(CSV_PATH)
    valid_methods = {
        "exact_reported_hour",
        "daily_peak_precipitation_hour",
        "daily_midday_dry_day",
        "nearest_hourly_timestamp",
    }
    assert set(df["temporal_matching_method"].unique()).issubset(valid_methods)

    # 110 events with explicit hour should have is_reported_time_exact == True
    exact_subset = df[df["is_reported_time_exact"]]
    assert len(exact_subset) == 110
    assert (exact_subset["temporal_matching_method"] == "exact_reported_hour").all()

    # Midnight events should be marked is_reported_time_exact == False
    non_exact = df[~df["is_reported_time_exact"]]
    assert len(non_exact) == 332
    assert set(non_exact["temporal_matching_method"].unique()).issubset({
        "daily_peak_precipitation_hour",
        "daily_midday_dry_day",
        "nearest_hourly_timestamp",
    })


def test_era5_meteorological_physical_ranges():
    df = pd.read_csv(CSV_PATH)

    # Precipitation non-negative
    assert (df["precipitation_mm"] >= 0.0).all()
    assert (df["precipitation_sum_3h_mm"] >= 0.0).all()
    assert (df["precipitation_sum_6h_mm"] >= 0.0).all()
    assert (df["precipitation_sum_24h_mm"] >= 0.0).all()

    # Antecedent precipitation accumulation consistency: 24h >= hourly
    assert (df["precipitation_sum_24h_mm"] >= df["precipitation_mm"] - 1e-5).all()

    # Physical ranges
    assert df["temperature_c"].between(-10.0, 50.0).all()
    assert df["relative_humidity_pct"].between(0.0, 100.0).all()
    assert df["wind_speed_kmh"].between(0.0, 150.0).all()
    assert (df["wind_gusts_kmh"] >= 0.0).all()
    assert df["cloud_cover_pct"].between(0.0, 100.0).all()

    # Wind gusts must be >= sustained wind speed (within small floating tolerance)
    assert (df["wind_gusts_kmh"] >= df["wind_speed_kmh"] - 0.1).all()


def test_era5_geographic_breakdowns():
    df = pd.read_csv(CSV_PATH)

    corridor_count = int(df["is_corridor"].sum())
    assam_megh_count = int(df["is_assam_meghalaya"].sum())
    wider_ner_count = int(df["is_wider_ner"].sum())

    assert corridor_count == 44
    assert assam_megh_count == 111
    assert wider_ner_count == 331
    assert assam_megh_count + wider_ner_count == 442


def test_era5_offline_feature_extraction():
    # Unit test feature extraction logic with synthetic payload
    event = {
        "event_id": "TEST_EV_001",
        "original_id": "001",
        "event_date": "2012-07-15T09:00:00+00:00",
        "state": "Assam",
        "latitude": 26.14,
        "longitude": 91.73,
    }

    # Generate 48 hours of dummy hourly data (day-1 to day)
    times = [
        (pd.to_datetime("2012-07-14T00:00:00+00:00") + pd.Timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M")
        for i in range(48)
    ]
    precips = [0.0] * 33 + [15.0] + [0.0] * 14  # peak at hour 33 (09:00 on 2012-07-15)

    era5_payload = {
        "latitude": 26.15,
        "longitude": 91.75,
        "elevation": 55.0,
        "hourly": {
            "time": times,
            "temperature_2m": [28.0] * 48,
            "relative_humidity_2m": [85.0] * 48,
            "precipitation": precips,
            "wind_speed_10m": [8.0] * 48,
            "wind_gusts_10m": [18.0] * 48,
            "cloud_cover": [90.0] * 48,
        },
    }

    features = fetcher.extract_weather_features_for_event(event, era5_payload)
    assert features["weather_matched"] is True
    assert features["weather_match_status"] == "matched"
    assert features["temporal_matching_method"] == "exact_reported_hour"
    assert features["precipitation_mm"] == 15.0
    assert features["precipitation_sum_24h_mm"] == 15.0
    assert features["era5_grid_distance_km"] < 5.0


def test_era5_spatial_rejection_beyond_threshold():
    # Event with coordinate far from returned grid cell (> 30 km)
    event = {
        "event_id": "TEST_EV_FAR",
        "original_id": "FAR",
        "event_date": "2012-07-15T09:00:00+00:00",
        "latitude": 26.14,
        "longitude": 91.73,
    }
    era5_far_payload = {
        "latitude": 28.50,  # > 200 km away
        "longitude": 91.75,
        "elevation": 500.0,
        "hourly": {"time": []},
    }
    features = fetcher.extract_weather_features_for_event(event, era5_far_payload)
    assert features["weather_matched"] is False
    assert features["weather_match_status"] == "unmatched_spatial_grid_too_far"


def test_era5_cache_preservation():
    assert CACHE_DIR.is_dir(), f"Cache dir not found: {CACHE_DIR}"
    cache_files = list(CACHE_DIR.glob("*.json"))
    assert len(cache_files) == 442, f"Expected 442 cached JSON files, found {len(cache_files)}"


def test_raw_nasa_catalog_preserved():
    assert RAW_NASA_PATH.is_file(), f"Raw NASA file missing: {RAW_NASA_PATH}"
    df_raw = pd.read_csv(RAW_NASA_PATH, low_memory=False)
    assert len(df_raw) > 10000, "Raw NASA catalog should contain full global records"
    assert "event_id" in df_raw.columns
    assert "event_date" in df_raw.columns
