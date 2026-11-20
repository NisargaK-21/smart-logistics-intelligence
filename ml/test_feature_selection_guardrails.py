"""Automated tests for ML feature allowlist and target leakage prevention.

GitHub Issue #32: Empirical Disaster Ground Truth and Class Imbalance.
Verifies that:
1. All legitimate antecedent weather, road, and terrain features are allowlisted.
2. Target leakage columns (road_distance_km, fatalities, event_id, source, sample_type,
   provenance, event_date, etc.) are strictly prohibited from entering feature matrices.
3. The target column 'is_disaster' is strictly isolated as the label and cannot be used as a predictor.
4. The empirical ground-truth dataset preserves all audit and matching metadata on disk.
5. Any accidental attempt by a future developer to leak targets or prohibited metadata raises TargetLeakageError.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from ml.risk_model_features import (
    CORE_EMPIRICAL_PREDICTIVE_FEATURES,
    EMPIRICAL_METEOROLOGICAL_FEATURES,
    EMPIRICAL_ROAD_FEATURES,
    EMPIRICAL_TERRAIN_FEATURES,
    LEGITIMATE_FEATURE_ALLOWLIST,
    PROHIBITED_LEAKING_COLUMNS,
    TARGET_LABEL_COLUMNS,
    WEATHER_FEATURE_COLUMNS,
    TargetLeakageError,
    extract_empirical_features_and_target,
    get_safe_feature_matrix,
    validate_feature_allowlist,
)

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH_PATH = ROOT / "ml" / "data" / "processed" / "disaster" / "empirical_ground_truth_ml.csv"


def test_allowlist_contains_all_legitimate_weather_and_terrain_features():
    """Verify that all legitimate antecedent features are present in the allowlist."""
    # Meteorological features
    expected_weather = {
        "precipitation_mm",
        "precipitation_sum_3h_mm",
        "precipitation_sum_6h_mm",
        "precipitation_sum_24h_mm",
        "temperature_c",
        "wind_speed_kmh",
    }
    assert expected_weather.issubset(set(EMPIRICAL_METEOROLOGICAL_FEATURES))
    assert expected_weather.issubset(set(LEGITIMATE_FEATURE_ALLOWLIST))

    # Road features
    assert "matched_road_class" in EMPIRICAL_ROAD_FEATURES
    assert "matched_road_class" in LEGITIMATE_FEATURE_ALLOWLIST
    from ml.risk_model_features import ROAD_CLASS_HIERARCHY
    assert "national_highway" in ROAD_CLASS_HIERARCHY
    assert "state_highway" in ROAD_CLASS_HIERARCHY

    # Terrain features (Copernicus DEM rasters)
    expected_terrain = {"elevation", "slope", "ruggedness", "elevation_m", "slope_deg", "ruggedness_tri"}
    assert expected_terrain.issubset(set(EMPIRICAL_TERRAIN_FEATURES))
    assert expected_terrain.issubset(set(LEGITIMATE_FEATURE_ALLOWLIST))

    # Baseline weather features must remain a subset of the allowlist
    assert set(WEATHER_FEATURE_COLUMNS).issubset(set(LEGITIMATE_FEATURE_ALLOWLIST))


def test_prohibited_columns_disallowlist_completeness():
    """Verify that all target-leaking, outcome-consequence, and metadata columns are strictly banned."""
    # Critical target leakage: road_distance_km (0.0 for negatives, >0.0 for positives)
    assert "road_distance_km" in PROHIBITED_LEAKING_COLUMNS

    # Post-event outcome consequence: fatalities
    assert "fatalities" in PROHIBITED_LEAKING_COLUMNS

    # Identifiers, provenance, and sample type
    assert "event_id" in PROHIBITED_LEAKING_COLUMNS
    assert "source" in PROHIBITED_LEAKING_COLUMNS
    assert "sample_type" in PROHIBITED_LEAKING_COLUMNS
    assert "provenance" in PROHIBITED_LEAKING_COLUMNS

    # Raw temporal timestamps
    assert "event_date" in PROHIBITED_LEAKING_COLUMNS
    assert "event_timestamp" in PROHIBITED_LEAKING_COLUMNS
    assert "time" in PROHIBITED_LEAKING_COLUMNS
    assert "weather_time" in PROHIBITED_LEAKING_COLUMNS
    assert "matched_weather_time" in PROHIBITED_LEAKING_COLUMNS

    # Spatial identifiers and matching flags
    assert "matched_road_id" in PROHIBITED_LEAKING_COLUMNS
    assert "matched_road_name" in PROHIBITED_LEAKING_COLUMNS
    assert "state" in PROHIBITED_LEAKING_COLUMNS
    assert "latitude" in PROHIBITED_LEAKING_COLUMNS
    assert "longitude" in PROHIBITED_LEAKING_COLUMNS
    assert "road_matched" in PROHIBITED_LEAKING_COLUMNS
    assert "weather_matched" in PROHIBITED_LEAKING_COLUMNS
    assert "coordinate_valid" in PROHIBITED_LEAKING_COLUMNS
    assert "is_corridor" in PROHIBITED_LEAKING_COLUMNS
    assert "nearest_station_id" in PROHIBITED_LEAKING_COLUMNS

    # Strict disjointness: no feature can be both allowlisted and prohibited
    overlap = set(LEGITIMATE_FEATURE_ALLOWLIST) & set(PROHIBITED_LEAKING_COLUMNS)
    assert overlap == set(), f"Contradiction: columns both allowed and prohibited: {overlap}"


def test_target_label_columns_disjoint_from_predictors():
    """Verify target columns are identified and completely disjoint from predictive features."""
    assert "is_disaster" in TARGET_LABEL_COLUMNS
    assert "disaster_type" in TARGET_LABEL_COLUMNS

    # Target columns must never be in the predictor allowlist
    target_overlap = set(LEGITIMATE_FEATURE_ALLOWLIST) & set(TARGET_LABEL_COLUMNS)
    assert target_overlap == set(), f"Target column found in predictor allowlist: {target_overlap}"


def test_validate_feature_allowlist_accepts_valid_features():
    """Verify that legitimate antecedent features validate without error."""
    valid_subset = [
        "precipitation_mm",
        "precipitation_sum_3h_mm",
        "temperature_c",
        "matched_road_class",
        "slope",
    ]
    result = validate_feature_allowlist(valid_subset)
    assert result == valid_subset


def test_validate_feature_allowlist_rejects_every_prohibited_column():
    """Verify that EVERY column in PROHIBITED_LEAKING_COLUMNS raises TargetLeakageError."""
    for col in PROHIBITED_LEAKING_COLUMNS:
        with pytest.raises(TargetLeakageError, match="Prohibited leaking feature detected"):
            validate_feature_allowlist([col])

        # Test combined with legitimate features
        with pytest.raises(TargetLeakageError, match="Prohibited leaking feature detected"):
            validate_feature_allowlist(["precipitation_mm", col])


def test_validate_feature_allowlist_rejects_target_columns():
    """Verify that target columns raise TargetLeakageError when proposed as features."""
    for col in TARGET_LABEL_COLUMNS:
        with pytest.raises(TargetLeakageError, match="Target column .* cannot be used as a predictor"):
            validate_feature_allowlist([col])


def test_validate_feature_allowlist_rejects_unauthorized_columns():
    """Verify that unauthorized columns not on the allowlist raise ValueError."""
    unauthorized = ["traffic_density_unverified", "driver_fatigue_level", "sensor_random_feature"]
    for col in unauthorized:
        with pytest.raises(ValueError, match="not in the legitimate predictive feature allowlist"):
            validate_feature_allowlist([col])


def test_extract_empirical_features_from_actual_ground_truth_csv():
    """Verify feature extraction on the real empirical_ground_truth_ml.csv dataset."""
    assert GROUND_TRUTH_PATH.is_file(), f"Ground-truth dataset missing: {GROUND_TRUTH_PATH}"

    df = pd.read_csv(GROUND_TRUTH_PATH)
    assert len(df) == 1402
    assert "road_distance_km" in df.columns
    assert "fatalities" in df.columns
    assert "is_disaster" in df.columns
    original_columns = list(df.columns)

    # Extract features and target
    X, y = extract_empirical_features_and_target(df, target_column="is_disaster")

    # Verify target vector y
    assert isinstance(y, pd.Series)
    assert len(y) == 1402
    assert set(y.unique()) == {0, 1}
    assert int((y == 1).sum()) == 402
    assert int((y == 0).sum()) == 1000

    # Verify predictor matrix X
    assert isinstance(X, pd.DataFrame)
    assert len(X) == 1402

    # Assert target column is NOT in X
    assert "is_disaster" not in X.columns
    assert "disaster_type" not in X.columns

    # Assert critical leakage features are NOT in X
    assert "road_distance_km" not in X.columns
    assert "fatalities" not in X.columns
    assert "event_id" not in X.columns
    assert "source" not in X.columns
    assert "sample_type" not in X.columns
    assert "provenance" not in X.columns
    assert "event_date" not in X.columns

    # Assert NO prohibited column is in X
    for col in PROHIBITED_LEAKING_COLUMNS:
        assert col not in X.columns, f"Prohibited column '{col}' leaked into feature matrix!"

    # Assert all columns in X are legitimate allowlisted features
    for col in X.columns:
        assert col in LEGITIMATE_FEATURE_ALLOWLIST, f"Unauthorized column '{col}' found in X!"

    # Verify the 7 core features present in empirical_ground_truth_ml.csv are in X
    expected_in_dataset = [
        "precipitation_mm",
        "precipitation_sum_3h_mm",
        "precipitation_sum_6h_mm",
        "precipitation_sum_24h_mm",
        "wind_speed_kmh",
        "temperature_c",
        "matched_road_class",
    ]
    assert set(expected_in_dataset).issubset(set(X.columns))

    # Verify original DataFrame was NOT mutated (metadata preserved on disk)
    assert list(df.columns) == original_columns
    assert "road_distance_km" in df.columns
    assert "fatalities" in df.columns


def test_extract_features_raises_if_prohibited_column_explicitly_requested():
    """Verify that explicitly requesting a prohibited column raises TargetLeakageError."""
    df = pd.DataFrame({
        "precipitation_mm": [10.0, 0.0],
        "road_distance_km": [0.45, 0.0],
        "fatalities": [2.0, 0.0],
        "is_disaster": [1, 0],
    })

    with pytest.raises(TargetLeakageError, match="Prohibited leaking feature detected: 'road_distance_km'"):
        extract_empirical_features_and_target(df, feature_columns=["precipitation_mm", "road_distance_km"])

    with pytest.raises(TargetLeakageError, match="Prohibited leaking feature detected: 'fatalities'"):
        extract_empirical_features_and_target(df, feature_columns=["precipitation_mm", "fatalities"])


def test_extract_features_raises_if_target_column_requested_as_predictor():
    """Verify that explicitly requesting is_disaster as a feature raises TargetLeakageError."""
    df = pd.DataFrame({
        "precipitation_mm": [10.0, 0.0],
        "is_disaster": [1, 0],
    })

    with pytest.raises(TargetLeakageError, match="Target column 'is_disaster' cannot be used as a predictor"):
        extract_empirical_features_and_target(df, feature_columns=["precipitation_mm", "is_disaster"])


def test_extract_features_with_terrain_columns():
    """Verify that terrain columns from DEM rasters are extracted when allowed and excluded when disabled."""
    df = pd.DataFrame({
        "precipitation_mm": [15.0, 2.0],
        "wind_speed_kmh": [20.0, 5.0],
        "elevation": [850.0, 120.0],
        "slope": [18.5, 3.2],
        "ruggedness": [24.0, 4.1],
        "road_distance_km": [0.32, 0.0],
        "is_disaster": [1, 0],
    })

    # When allow_terrain=True: terrain features should be included in X
    X_terrain, y_terrain = extract_empirical_features_and_target(df, allow_terrain=True)
    assert "elevation" in X_terrain.columns
    assert "slope" in X_terrain.columns
    assert "ruggedness" in X_terrain.columns
    assert "road_distance_km" not in X_terrain.columns
    assert "is_disaster" not in X_terrain.columns

    # When allow_terrain=False: terrain features should be excluded from X
    X_no_terrain, y_no_terrain = extract_empirical_features_and_target(df, allow_terrain=False)
    assert "elevation" not in X_no_terrain.columns
    assert "slope" not in X_no_terrain.columns
    assert "ruggedness" not in X_no_terrain.columns
    assert "precipitation_mm" in X_no_terrain.columns


def test_get_safe_feature_matrix_filters_prohibited_and_target_columns():
    """Verify get_safe_feature_matrix extracts only allowed predictors."""
    df = pd.DataFrame({
        "precipitation_mm": [10.0, 25.0],
        "wind_speed_kmh": [12.0, 30.0],
        "temperature_c": [22.0, 18.0],
        "road_distance_km": [0.5, 1.2],
        "fatalities": [0.0, 1.0],
        "event_id": ["E1", "E2"],
        "is_disaster": [1, 1],
    })

    safe_X = get_safe_feature_matrix(df)
    assert set(safe_X.columns) == {"precipitation_mm", "wind_speed_kmh", "temperature_c"}
    assert "road_distance_km" not in safe_X.columns
    assert "fatalities" not in safe_X.columns
    assert "event_id" not in safe_X.columns
    assert "is_disaster" not in safe_X.columns


def test_future_developer_guardrail_fails_on_accidental_leakage():
    """Simulate a developer accidentally trying to add a new post-event column to the model."""
    df = pd.DataFrame({
        "precipitation_mm": [10.0, 0.0],
        "damage_cost_lakhs": [50.0, 0.0],  # Post-event outcome
        "is_disaster": [1, 0],
    })

    # Attempting to auto-extract will safely ignore damage_cost_lakhs
    X, _ = extract_empirical_features_and_target(df)
    assert "damage_cost_lakhs" not in X.columns

    # Attempting to explicitly pass damage_cost_lakhs will fail with ValueError
    with pytest.raises(ValueError, match="not in the legitimate predictive feature allowlist"):
        extract_empirical_features_and_target(df, feature_columns=["precipitation_mm", "damage_cost_lakhs"])
