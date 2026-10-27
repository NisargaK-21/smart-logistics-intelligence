
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

MATCHES_FILE = (
    ROOT / "ml/data/processed/field_reports/"
    "field_reports_weather_locations.csv"
)
WEATHER_FILE = ROOT / "ml/data/processed/weather_recent_oct2026.csv"
OUTPUT_FILE = (
    ROOT / "ml/data/processed/field_reports/"
    "field_reports_with_weather.csv"
)


def main():
    reports = pd.read_csv(MATCHES_FILE)
    weather = pd.read_csv(WEATHER_FILE)

    reports["timestamp"] = pd.to_datetime(
        reports["timestamp"], errors="coerce"
    )
    weather["time"] = pd.to_datetime(
        weather["time"], errors="coerce"
    )

    if reports["timestamp"].isna().any():
        raise ValueError("Invalid field report timestamps.")

    if weather["time"].isna().any():
        raise ValueError("Invalid weather timestamps.")

    reports["nearest_location_id"] = pd.to_numeric(
        reports["nearest_location_id"], errors="raise"
    )
    weather["location_id"] = pd.to_numeric(
        weather["location_id"], errors="raise"
    )

    # Round each report to its nearest hour.
    reports["weather_time"] = (
        reports["timestamp"].dt.round("h")
    )

    # Match using both weather location and rounded time.
    weather_for_merge = weather.rename(
        columns={"location_id": "nearest_location_id"}
    )

    result = reports.merge(
        weather_for_merge,
        left_on=["nearest_location_id", "weather_time"],
        right_on=["nearest_location_id", "time"],
        how="left",
        validate="many_to_one",
    )

    weather_columns = [
        "temperature_c",
        "relative_humidity_pct",
        "precipitation_mm",
        "cloud_cover_pct",
        "wind_speed_kmh",
    ]

    matched = result["temperature_c"].notna().sum()
    unmatched = len(result) - matched

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False)

    print("Field reports:", len(result))
    print("Reports with matching weather:", matched)
    print("Reports without matching weather:", unmatched)
    print(
        "Reports with missing weather values:",
        int(result[weather_columns].isna().any(axis=1).sum()),
    )
    print("Output saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
