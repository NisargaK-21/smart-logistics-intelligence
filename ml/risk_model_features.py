"""Shared weather feature schema for experimental risk-model training and inference."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

WEATHER_FEATURE_COLUMNS = (
    "precipitation_mm",
    "precipitation_sum_3h_mm",
    "precipitation_sum_6h_mm",
    "precipitation_sum_24h_mm",
    "wind_speed_kmh",
)


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
