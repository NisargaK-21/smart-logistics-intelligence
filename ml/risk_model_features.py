"""Centralized feature schema, allowlists, and leakage guardrails for ML models.

GitHub Issue #32: Empirical Disaster Ground Truth and Class Imbalance.
Provides the single source of truth for:
1. Legitimate antecedent predictive features (weather, road infrastructure, terrain).
2. Strictly prohibited post-event, identifier, and target-leakage metadata columns.
3. Separation of target labels (is_disaster, disaster_type) from predictive inputs.
4. Robust feature validation and extraction for training, evaluation, and inference.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd


# ---------------------------------------------------------------------------
# 1. Baseline Synthetic-Label Weather Features (Backward Compatible)
# ---------------------------------------------------------------------------

WEATHER_FEATURE_COLUMNS = (
    "precipitation_mm",
    "precipitation_sum_3h_mm",
    "precipitation_sum_6h_mm",
    "precipitation_sum_24h_mm",
    "wind_speed_kmh",
)


# ---------------------------------------------------------------------------
# 2. Legitimate Antecedent Predictive Features (Allowlist)
# ---------------------------------------------------------------------------

# Meteorological features available prior to or at the observation timestamp
EMPIRICAL_METEOROLOGICAL_FEATURES = (
    "precipitation_mm",
    "precipitation_sum_3h_mm",
    "precipitation_sum_6h_mm",
    "precipitation_sum_24h_mm",
    "temperature_c",
    "wind_speed_kmh",
)

# Physical road and infrastructure characteristics
# Note for future model training: 'matched_road_class' is a categorical feature
# (e.g., 'national_highway', 'state_highway', 'primary', 'secondary', 'tertiary', 'residential').
# For linear models and neural networks, use OneHotEncoder(handle_unknown='ignore') or
# an ordinal hazard mapping based on road hierarchy. For gradient boosted trees (LightGBM/CatBoost),
# cast to pandas category dtype.
EMPIRICAL_ROAD_FEATURES = (
    "matched_road_class",
)

# Standard road classification hierarchy for ordinal encoding or category validation
ROAD_CLASS_HIERARCHY = (
    "expressway",
    "national_highway",
    "major",
    "primary",
    "state_highway",
    "secondary",
    "collector",
    "tertiary",
    "local",
    "residential",
    "unclassified",
    "unknown",
)

# Physical terrain and topography characteristics (Copernicus DEM rasters)
# Supports both canonical and suffixed naming conventions
EMPIRICAL_TERRAIN_FEATURES = (
    "elevation",
    "slope",
    "ruggedness",
    "elevation_m",
    "slope_deg",
    "ruggedness_tri",
)

# Core empirical features currently available in empirical_ground_truth_ml.csv
CORE_EMPIRICAL_PREDICTIVE_FEATURES = (
    *EMPIRICAL_METEOROLOGICAL_FEATURES,
    *EMPIRICAL_ROAD_FEATURES,
)

# Comprehensive allowlist of all legitimate antecedent predictive features
LEGITIMATE_FEATURE_ALLOWLIST = (
    *EMPIRICAL_METEOROLOGICAL_FEATURES,
    *EMPIRICAL_ROAD_FEATURES,
    *EMPIRICAL_TERRAIN_FEATURES,
)


# ---------------------------------------------------------------------------
# 3. Strictly Prohibited Columns (Target Leakage & Post-Event Metadata)
# ---------------------------------------------------------------------------

PROHIBITED_LEAKING_COLUMNS = frozenset({
    # 1. Critical target leakage: road_distance_km is 0.0 for all negative controls
    # (sampled on road network) and >0.0 for all positive disaster events (spatial proximity match).
    # Inclusion yields 100% artificial accuracy and invalidates the model.
    "road_distance_km",

    # 2. Post-event outcome consequence: fatalities occur as a result of a disaster,
    # not as an antecedent risk predictor. Always 0.0 for negative controls.
    "fatalities",

    # 3. Direct identifier and source cues that correlate 1:1 with ground-truth labels:
    "event_id",
    "source",
    "sample_type",
    "provenance",

    # 4. Raw temporal timestamps: induces rote temporal memorization across historical gaps:
    "event_date",
    "event_timestamp",
    "time",
    "weather_time",
    "matched_weather_time",

    # 5. Matching pipeline metadata and audit flags:
    "road_matched",
    "weather_matched",
    "coordinate_valid",
    "is_corridor",
    "nearest_station_id",
    "era5_grid_distance_km",
    "station_distance_km",

    # 6. Specific spatial IDs and raw coordinates (preventing rote spatial memorization):
    "matched_road_id",
    "matched_road_name",
    "state",
    "latitude",
    "longitude",
})


# ---------------------------------------------------------------------------
# 4. Target Label Columns (Must never enter the feature matrix as predictors)
# ---------------------------------------------------------------------------

TARGET_LABEL_COLUMNS = frozenset({
    "is_disaster",
    "disaster_type",
    "synthetic_label",
    "label",
})


# ---------------------------------------------------------------------------
# 5. Leakage Exceptions
# ---------------------------------------------------------------------------

class TargetLeakageError(ValueError):
    """Raised when target labels, post-event metadata, or leakage columns enter feature selection."""


# ---------------------------------------------------------------------------
# 6. Feature Validation & Guardrails
# ---------------------------------------------------------------------------

def validate_feature_allowlist(feature_names: Iterable[str]) -> list[str]:
    """Validate that every feature is on the legitimate allowlist and free of target leakage.

    Raises:
        TargetLeakageError: If any prohibited leaking column or target label is present.
        ValueError: If any column is not in the legitimate predictive feature allowlist.
    """
    feature_list = list(feature_names)
    if not feature_list:
        raise ValueError("Feature list cannot be empty.")

    for feature in feature_list:
        # Check target leakage and post-event prohibited columns
        if feature in PROHIBITED_LEAKING_COLUMNS:
            raise TargetLeakageError(
                f"Prohibited leaking feature detected: '{feature}'. "
                f"This column conveys post-event or target-matching metadata and must never enter the feature matrix."
            )

        # Check target labels
        if feature in TARGET_LABEL_COLUMNS:
            raise TargetLeakageError(
                f"Target column '{feature}' cannot be used as a predictor feature."
            )

        # Check legitimate allowlist
        if feature not in LEGITIMATE_FEATURE_ALLOWLIST:
            raise ValueError(
                f"Feature '{feature}' is not in the legitimate predictive feature allowlist. "
                f"Allowed features: {sorted(LEGITIMATE_FEATURE_ALLOWLIST)}"
            )

    return feature_list


def extract_empirical_features_and_target(
    df: pd.DataFrame,
    target_column: str = "is_disaster",
    feature_columns: Iterable[str] | None = None,
    *,
    allow_terrain: bool = True,
) -> tuple[pd.DataFrame, pd.Series]:
    """Extract a safe predictor matrix X and label vector y from an empirical ground-truth DataFrame.

    Guarantees:
    - Target column is strictly separated into y and never present in X.
    - Prohibited leaking columns (road_distance_km, fatalities, event_id, etc.) are strictly excluded.
    - Only features on the legitimate allowlist enter X.
    - Original DataFrame is not mutated; audit metadata is preserved on disk.

    Parameters:
        df: Input DataFrame (e.g. loaded from empirical_ground_truth_ml.csv).
        target_column: Column name to extract as target vector y (default: 'is_disaster').
        feature_columns: Optional explicit list of features to extract. If None, auto-selects
                         all legitimate allowlisted features present in df.
        allow_terrain: Whether to include terrain features if present in df (default: True).

    Returns:
        (X, y) tuple where X is a DataFrame of safe predictors and y is a Series of target labels.
    """
    import pandas as pd

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("Input DataFrame contains no rows.")
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' is missing from DataFrame.")

    # 1. Determine feature columns
    if feature_columns is not None:
        selected_cols = validate_feature_allowlist(feature_columns)
        missing_cols = [c for c in selected_cols if c not in df.columns]
        if missing_cols:
            raise ValueError(f"Requested feature columns missing from DataFrame: {missing_cols}")
    else:
        # Auto-select all available legitimate features
        selected_cols = [
            col for col in df.columns
            if col in LEGITIMATE_FEATURE_ALLOWLIST
            and (allow_terrain or col not in EMPIRICAL_TERRAIN_FEATURES)
        ]
        if not selected_cols:
            raise ValueError("No legitimate antecedent features found in DataFrame.")

    # 2. Strict guardrail assertions
    if target_column in selected_cols:
        raise TargetLeakageError(
            f"Target column '{target_column}' was detected in selected predictor features."
        )

    for col in selected_cols:
        if col in PROHIBITED_LEAKING_COLUMNS:
            raise TargetLeakageError(
                f"Critical leakage: prohibited column '{col}' cannot enter the feature matrix."
            )
        if col in TARGET_LABEL_COLUMNS:
            raise TargetLeakageError(
                f"Critical leakage: target column '{col}' cannot enter the feature matrix."
            )
        if col not in LEGITIMATE_FEATURE_ALLOWLIST:
            raise ValueError(
                f"Feature '{col}' is not authorized on the predictive feature allowlist."
            )

    X = df.loc[:, selected_cols].copy()
    y = df.loc[:, target_column].copy()

    # Final assertion: target and prohibited columns must never be in X
    assert target_column not in X.columns, f"Target '{target_column}' leaked into feature matrix!"
    assert not any(c in PROHIBITED_LEAKING_COLUMNS for c in X.columns), "Prohibited columns leaked into X!"
    assert len(X) == len(y), "Feature matrix X and target y row counts do not match!"

    return X, y


def get_safe_feature_matrix(
    df: pd.DataFrame,
    feature_columns: Iterable[str] | None = None,
    *,
    allow_terrain: bool = True,
) -> pd.DataFrame:
    """Extract a validated predictor matrix X, ensuring no target or prohibited columns are present."""
    import pandas as pd

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("Input DataFrame contains no rows.")

    if feature_columns is not None:
        selected_cols = validate_feature_allowlist(feature_columns)
        missing_cols = [c for c in selected_cols if c not in df.columns]
        if missing_cols:
            raise ValueError(f"Requested feature columns missing from DataFrame: {missing_cols}")
    else:
        selected_cols = [
            col for col in df.columns
            if col in LEGITIMATE_FEATURE_ALLOWLIST
            and (allow_terrain or col not in EMPIRICAL_TERRAIN_FEATURES)
        ]
        if not selected_cols:
            raise ValueError("No legitimate antecedent features found in DataFrame.")

    # Guardrails
    for col in selected_cols:
        if col in PROHIBITED_LEAKING_COLUMNS:
            raise TargetLeakageError(f"Prohibited column '{col}' in feature matrix.")
        if col in TARGET_LABEL_COLUMNS:
            raise TargetLeakageError(f"Target column '{col}' in feature matrix.")
        if col not in LEGITIMATE_FEATURE_ALLOWLIST:
            raise ValueError(f"Unauthorized feature '{col}'.")

    return df.loc[:, selected_cols].copy()


# ---------------------------------------------------------------------------
# 7. Legacy Weather Feature Preparation (Preserved for Baseline Model)
# ---------------------------------------------------------------------------

def prepare_weather_features(
    values: Mapping[str, Any] | pd.DataFrame,
    *,
    allow_missing: bool = False,
) -> pd.DataFrame:
    """Validate weather values and return columns in the model's canonical order."""
    import numpy as np
    import pandas as pd

    if isinstance(values, Mapping):
        frame = pd.DataFrame([values])
    elif isinstance(values, pd.DataFrame):
        frame = values
    else:
        raise TypeError("Weather features must be a mapping or pandas DataFrame.")

    missing_columns = [column for column in WEATHER_FEATURE_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"Missing required weather features: {', '.join(missing_columns)}")
    if frame.empty:
        raise ValueError("Weather feature input contains no rows.")

    features = frame.loc[:, list(WEATHER_FEATURE_COLUMNS)].copy()
    for column in WEATHER_FEATURE_COLUMNS:
        original = features[column]
        numeric = pd.to_numeric(original, errors="coerce")
        malformed = original.notna() & numeric.isna()
        if malformed.any():
            raise ValueError(f"Weather feature '{column}' contains non-numeric values.")
        values_array = numeric.to_numpy(dtype=float, na_value=np.nan)
        if np.isinf(values_array).any():
            raise ValueError(f"Weather feature '{column}' cannot contain infinite values.")
        if (numeric.dropna() < 0).any():
            raise ValueError(f"Weather feature '{column}' cannot contain negative values.")
        features[column] = numeric

    if not allow_missing and features.isna().any().any():
        missing = [
            column
            for column in WEATHER_FEATURE_COLUMNS
            if features[column].isna().any()
        ]
        raise ValueError(f"Weather feature values are missing: {', '.join(missing)}")
    return features
