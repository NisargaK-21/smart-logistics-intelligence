
from pathlib import Path

import pandas as pd


REPORTS_PATH = Path(
    "ml/data/processed/field_reports/field_reports_processed.csv"
)
WEATHER_PATH = Path(
    "ml/data/processed/weather_recent_sep30_oct03_2026_features.csv"
)
OUTPUT_PATH = Path(
    "ml/data/final/field_reports_with_weather_features.csv"
)


def main():
    reports = pd.read_csv(REPORTS_PATH, parse_dates=["timestamp"])
    weather = pd.read_csv(WEATHER_PATH, parse_dates=["time"])

    reports["timestamp"] = pd.to_datetime(reports["timestamp"])
    weather["time"] = pd.to_datetime(weather["time"])

    # Load the weather-location coordinates.
    locations = pd.read_csv(
        "ml/data/processed/weather_locations.csv"
    )

    # Confirm the expected coordinate columns exist.
    required = {"location_id", "latitude", "longitude"}
    if not required.issubset(locations.columns):
        raise ValueError(
            f"Location metadata must contain {sorted(required)}. "
            f"Found: {list(locations.columns)}"
        )

    weather = weather.merge(
        locations[["location_id", "latitude", "longitude"]],
        on="location_id",
        how="left",
        validate="many_to_one",
    )

    if weather[["latitude", "longitude"]].isna().any().any():
        raise ValueError("Some weather locations have no coordinates.")

    def haversine_km(lat1, lon1, lat2, lon2):
        import numpy as np

        earth_radius_km = 6371.0
        lat1, lon1, lat2, lon2 = map(
            np.radians, [lat1, lon1, lat2, lon2]
        )
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (
            np.sin(dlat / 2) ** 2
            + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        )
        return 2 * earth_radius_km * np.arcsin(np.sqrt(a))

    matched_rows = []

    for _, report in reports.iterrows():
        candidates = weather[
            weather["time"].dt.date == report["timestamp"].date()
        ].copy()

        if candidates.empty:
            raise ValueError(
                f"No weather records for report {report['report_id']} date."
            )

        candidates["distance_km"] = haversine_km(
            report["latitude"],
            report["longitude"],
            candidates["latitude"],
            candidates["longitude"],
        )

        # Choose the nearest station, then the nearest hour at that station.
        nearest_location_id = (
            candidates.sort_values("distance_km")
            .iloc[0]["location_id"]
        )
        station_rows = candidates[
            candidates["location_id"] == nearest_location_id
        ].copy()

        station_rows["time_difference_minutes"] = (
            station_rows["time"] - report["timestamp"]
        ).abs().dt.total_seconds() / 60

        nearest = station_rows.sort_values(
            "time_difference_minutes"
        ).iloc[0]

        row = report.to_dict()
        row["nearest_location_id"] = nearest_location_id
        row["weather_time"] = nearest["time"]
        row["nearest_distance_km"] = nearest["distance_km"]

        for column in [
            "temperature_c",
            "relative_humidity_pct",
            "precipitation_mm",
            "cloud_cover_pct",
            "wind_speed_kmh",
            "precipitation_sum_3h_mm",
            "precipitation_sum_6h_mm",
            "precipitation_sum_24h_mm",
        ]:
            row[column] = nearest[column]

        row["time_difference_minutes"] = nearest[
            "time_difference_minutes"
        ]
        matched_rows.append(row)

    result = pd.DataFrame(matched_rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved: {OUTPUT_PATH}")
    print(f"Reports: {len(result)}")
    print("\nMissing values in rolling features:")
    print(
        result[
            [
                "precipitation_sum_3h_mm",
                "precipitation_sum_6h_mm",
                "precipitation_sum_24h_mm",
            ]
        ].isna().sum()
    )
    print("\nMatching distances (km):")
    print(result["nearest_distance_km"].describe())
    print("\nTime differences (minutes):")
    print(result["time_difference_minutes"].describe())


if __name__ == "__main__":
    main()
