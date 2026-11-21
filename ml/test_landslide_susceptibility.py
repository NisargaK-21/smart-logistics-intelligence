"""Tests for ML Landslide Susceptibility Prediction Service, Spatial Separation, and Multi-Strategy Benchmarking.

Objective 1: Strengthen genuine ML-based hazard prediction for NER-ResQ.
Task A: Landslide Susceptibility Estimation using historical landslide locations and geographical features.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ml.landslide_susceptibility import LandslideSusceptibilityService, landslide_service

ML_ROOT = Path(__file__).resolve().parent
DATASET_PATH_A = ML_ROOT / "data" / "processed" / "landslides" / "landslide_susceptibility_dataset.csv"
DATASET_PATH_B = ML_ROOT / "data" / "processed" / "landslides" / "landslide_susceptibility_hard_negatives.csv"
REPORT_PATH = ML_ROOT / "data" / "processed" / "landslides" / "landslide_model_evaluation.json"


def test_sampling_constraints_unconstrained_vs_hard_slope():
    """Verify negative sampling constraints under Strategy A and Strategy B."""
    assert DATASET_PATH_A.is_file(), f"Strategy A dataset missing at {DATASET_PATH_A}"
    assert DATASET_PATH_B.is_file(), f"Strategy B dataset missing at {DATASET_PATH_B}"

    df_a = pd.read_csv(DATASET_PATH_A)
    df_b = pd.read_csv(DATASET_PATH_B)

    pos_a = df_a[df_a["is_landslide"] == 1]
    neg_a = df_a[df_a["is_landslide"] == 0]
    neg_b = df_b[df_b["is_landslide"] == 0]

    # Verify Strategy A: Unconstrained background controls DO NOT artificially filter slope < 5.0 deg
    max_neg_slope_a = neg_a["slope_deg"].max()
    assert max_neg_slope_a > 15.0, f"Strategy A negative slope is artificially clamped: max={max_neg_slope_a}"
    assert (neg_a["slope_deg"] >= 5.0).sum() > 50, "Strategy A should contain natural unfailed hillslopes"

    # Verify Strategy B: Hard negatives are strictly in moderate-to-steep range [5.0, 35.0]
    assert (neg_b["slope_deg"] >= 5.0).all(), "Strategy B negatives must have slope >= 5.0 deg"
    assert (neg_b["slope_deg"] <= 35.0).all(), "Strategy B negatives must have slope <= 35.0 deg"

    # Verify positive integrity: 100% matched GSI records
    assert len(pos_a) == 794
    assert (pos_a["point_type"] == "gsi_confirmed_landslide").all()


def test_geographic_buffer_spatial_separation():
    """Verify strict geographic buffer separation between training and holdout test partitions."""
    df = pd.read_csv(DATASET_PATH_A)
    assert "is_train" in df.columns
    assert "is_holdout_test" in df.columns
    assert "is_buffer_excluded" in df.columns

    train_df = df[df["is_train"]]
    test_df = df[df["is_holdout_test"]]
    buffer_df = df[df["is_buffer_excluded"]]

    assert len(train_df) > 0
    assert len(test_df) > 0
    assert len(buffer_df) > 0  # Buffer samples must be explicitly excluded

    # Compute planar distance between all train and test points
    train_coords_rad = np.column_stack([np.radians(train_df["latitude"]), np.radians(train_df["longitude"])])
    test_coords_rad = np.column_stack([np.radians(test_df["latitude"]), np.radians(test_df["longitude"])])
    tree = cKDTree(train_coords_rad)
    dists_rad, _ = tree.query(test_coords_rad)
    min_dist_km = float((dists_rad * 6371.0).min())

    # Minimum separation must strictly exceed the 10.0 km buffer threshold
    assert min_dist_km >= 10.0, f"Spatial buffer leak detected! Min train-test distance is {min_dist_km:.2f} km (< 10.0 km)"


def test_model_evaluation_report_and_acceptance_gates():
    assert REPORT_PATH.is_file(), f"Evaluation report missing at {REPORT_PATH}"
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert report["task"] == "Landslide Susceptibility Estimation (Task A)"
    assert "production_model_evaluation" in report
    assert "benchmarks" in report

    # Verify production model metrics on independent spatial holdout (10 km buffer)
    metrics = report["production_model_evaluation"]["metrics"]
    assert metrics["accuracy"] >= 0.80
    assert metrics["precision"] >= 0.80
    assert metrics["recall"] >= 0.80
    assert metrics["macro_f1"] >= 0.80
    assert metrics["roc_auc"] >= 0.85
    assert metrics["pr_auc"] >= 0.85
    assert metrics["brier_score"] <= 0.15

    # Verify confusion matrix
    cm = metrics["confusion_matrix"]
    assert set(cm.keys()) == {"tn", "fp", "fn", "tp"}
    assert cm["tp"] >= 100
    assert cm["tn"] >= 50

    # Verify benchmarks include both Strategy A and Strategy B across buffer distances
    benchmarks = report["benchmarks"]
    assert "strategy_a_unconstrained_5km_buffer" in benchmarks
    assert "strategy_a_unconstrained_10km_buffer" in benchmarks
    assert "strategy_b_hard_negatives_5km_buffer" in benchmarks
    assert "strategy_b_hard_negatives_10km_buffer" in benchmarks


def test_model_service_availability_and_info():
    service = LandslideSusceptibilityService()
    assert service.is_available is True

    info = service.get_model_info()
    assert info["available"] is True
    assert info["status"] == "operational"
    assert "scientific_framework" in info
    assert "benchmarks" in info
    assert "bias_analysis" in info

    assert "feature_importances" in info
    importances = info["feature_importances"]
    assert "slope_deg" in importances
    assert "ruggedness" in importances
    assert "road_distance_m" in importances

    # Verify spatial buffer and validation design metadata
    assert "spatial_validation_design" in info
    spatial_design = info["spatial_validation_design"]
    assert spatial_design["buffer_km"] == 10.0
    assert spatial_design["split_latitude"] == 25.50
    assert spatial_design["verified_min_separation_km"] >= 10.0
    assert spatial_design["train_samples"] > 0
    assert spatial_design["test_samples"] > 0
    assert spatial_design["excluded_buffer_samples"] > 0


def test_point_prediction_relative_susceptibility():
    service = LandslideSusceptibilityService()

    # Steep relief terrain (slope 28 deg, ruggedness 15.0)
    steep_pred = service.predict_point(
        lat=25.6,
        lon=91.9,
        slope_deg=28.0,
        ruggedness=15.0,
        elevation_m=1100.0,
        road_distance_m=30.0,
        road_class="secondary",
    )
    assert steep_pred["susceptibility_score"] >= 60
    assert steep_pred["relative_spatial_susceptibility_index"] >= 0.60
    assert steep_pred["susceptibility_level"] in {"high", "very_high"}

    # Flat valley terrain (slope 1.5 deg, ruggedness 0.5)
    flat_pred = service.predict_point(
        lat=26.15,
        lon=91.75,
        slope_deg=1.5,
        ruggedness=0.5,
        elevation_m=50.0,
        road_distance_m=800.0,
        road_class="secondary",
    )
    assert flat_pred["susceptibility_score"] <= 40
    assert flat_pred["relative_spatial_susceptibility_index"] <= 0.40
    assert flat_pred["susceptibility_level"] in {"low", "moderate"}


def test_out_of_bounds_point_graceful_handling():
    service = LandslideSusceptibilityService()

    # Coordinates outside Northeast DEM coverage (e.g. Bangalore)
    oob_pred = service.predict_point(lat=12.9716, lon=77.5946)
    assert oob_pred["data_quality"] == "partial"
    assert oob_pred["model_source"] == "heuristic_fallback"
    assert len(oob_pred["warnings"]) > 0
    assert any("DEM raster coverage" in w for w in oob_pred["warnings"])
    assert "relative_spatial_susceptibility_index" in oob_pred
    assert 0 <= oob_pred["susceptibility_score"] <= 100


def test_segment_batch_prediction():
    service = LandslideSusceptibilityService()
    test_segments = [
        {
            "segment_id": "seg-test-1",
            "coordinates": [[91.80, 25.60], [91.81, 25.61]],
            "slope_deg": 22.0,
            "elevation_m": 850.0,
            "ruggedness": 12.0,
            "road_class": "state_highway",
        },
        {
            "segment_id": "seg-test-2",
            "coordinates": [[91.72, 26.18], [91.73, 26.19]],
            "slope_deg": 2.0,
            "elevation_m": 55.0,
            "ruggedness": 0.8,
            "road_class": "primary",
        },
    ]

    results = service.predict_segments(test_segments)
    assert "seg-test-1" in results
    assert "seg-test-2" in results
    assert results["seg-test-1"]["susceptibility_score"] > results["seg-test-2"]["susceptibility_score"]
    assert results["seg-test-1"]["relative_spatial_susceptibility_index"] > results["seg-test-2"]["relative_spatial_susceptibility_index"]
