
from pathlib import Path

import pandas as pd


INPUT_PATH = Path("ml/data/processed/weather_recent_oct2026.csv")
OUTPUT_PATH = Path(
    "ml/data/processed/weather_recent_oct2026_features.csv"
)


def main():
    df = pd.read_csv(INPUT_PATH, parse_dates=["time"])

    required = [
        "time",
        "location_id",
        "precipitation_mm",
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.sort_values(["location_id", "time"]).copy()

    if df.duplicated(["location_id", "time"]).any():
        raise ValueError("Duplicate location/time records found.")

    # Verify hourly continuity before calculating rolling totals.
    hourly_gaps = (
        df.groupby("location_id")["time"]
        .diff()
        .dropna()
    )
    if not hourly_gaps.eq(pd.Timedelta(hours=1)).all():
        raise ValueError("Weather records are not continuously hourly.")

    grouped = df.groupby("location_id")["precipitation_mm"]

    # Current hour plus the preceding 2, 5, or 23 hours.
    for hours in (3, 6, 24):
        column = f"precipitation_sum_{hours}h_mm"
        df[column] = grouped.transform(
            lambda series: series.rolling(
                window=hours,
                min_periods=hours,
            ).sum()
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved: {OUTPUT_PATH}")
    print(f"Rows: {len(df)}")
    print("\nMissing rolling values:")
    print(
        df[
            [
                "precipitation_sum_3h_mm",
                "precipitation_sum_6h_mm",
                "precipitation_sum_24h_mm",
            ]
        ].isna().sum()
    )


if __name__ == "__main__":
    main()
