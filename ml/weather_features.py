
from pathlib import Path

import pandas as pd


INPUT_FILE = Path("ml/data/processed/weather_processed.csv")
OUTPUT_FILE = Path("ml/data/processed/weather_features.csv")

GROUP_COLUMN = "location_id"
TIME_COLUMN = "time"

WEATHER_COLUMNS = [
    "temperature_c",
    "relative_humidity_pct",
    "precipitation_mm",
    "cloud_cover_pct",
    "wind_speed_kmh",
]


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Weather input not found: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE, parse_dates=[TIME_COLUMN])

    required = [GROUP_COLUMN, TIME_COLUMN, *WEATHER_COLUMNS]
    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if df.duplicated([GROUP_COLUMN, TIME_COLUMN]).any():
        raise ValueError(
            "Duplicate location/time records found. "
            "Resolve duplicates before calculating rolling features."
        )

    df = df.sort_values([GROUP_COLUMN, TIME_COLUMN]).copy()

    # Confirm the data has hourly intervals within each location.
    hourly_gaps = (
        df.groupby(GROUP_COLUMN)[TIME_COLUMN]
        .diff()
        .dropna()
    )

    if not hourly_gaps.eq(pd.Timedelta(hours=1)).all():
        raise ValueError(
            "Non-hourly gaps found. Check the timestamps before "
            "calculating rolling rainfall features."
        )

    # Rolling precipitation totals, using the current hour and
    # preceding hours at the same location.
    for hours in (3, 6, 24):
        feature_name = f"precipitation_sum_{hours}h_mm"

        df[feature_name] = (
            df.groupby(GROUP_COLUMN)["precipitation_mm"]
            .transform(
                lambda series: series.rolling(
                    window=hours,
                    min_periods=hours,
                ).sum()
            )
        )

    # Save the engineered dataset separately.
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print("Weather feature engineering completed.")
    print(f"Input rows: {len(df):,}")
    print(f"Output rows: {len(df):,}")
    print(f"Output columns: {len(df.columns)}")
    print(f"Output file: {OUTPUT_FILE}")
    print("\nNew rainfall features:")
    print(" - precipitation_sum_3h_mm")
    print(" - precipitation_sum_6h_mm")
    print(" - precipitation_sum_24h_mm")
    print("\nMissing values in new features:")
    print(
        df[
            [
                "precipitation_sum_3h_mm",
                "precipitation_sum_6h_mm",
                "precipitation_sum_24h_mm",
            ]
        ].isna().sum().to_string()
    )


if __name__ == "__main__":
    main()
