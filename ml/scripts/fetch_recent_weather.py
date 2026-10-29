from pathlib import Path

import pandas as pd
import requests


# Project paths
ROOT = Path(__file__).resolve().parents[2]

LOCATIONS_FILE = ROOT / "ml" / "data" / "processed" / "weather_locations.csv"
OUTPUT_FILE = ROOT / "ml" / "data" / "processed" / "weather_recent_oct2026.csv"

# Open-Meteo historical weather API
URL = "https://archive-api.open-meteo.com/v1/archive"

START_DATE = "2026-10-01"
END_DATE = "2026-10-03"


def main():
    # Check the locations file
    if not LOCATIONS_FILE.exists():
        print(f"ERROR: Locations file not found: {LOCATIONS_FILE}")
        return

    locations = pd.read_csv(LOCATIONS_FILE)

    required_columns = {"latitude", "longitude"}
    if not required_columns.issubset(locations.columns):
        print("ERROR: Locations file must contain latitude and longitude.")
        return

    if locations.empty:
        print("ERROR: No weather locations were found.")
        return

    print(f"Requesting weather for {len(locations)} locations...")
    print(f"Date range: {START_DATE} to {END_DATE}")

    params = {
        "latitude": ",".join(locations["latitude"].astype(str)),
        "longitude": ",".join(locations["longitude"].astype(str)),
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "cloud_cover,"
            "wind_speed_10m"
        ),
        "timezone": "Asia/Kolkata",
        "wind_speed_unit": "kmh",
    }

    try:
        response = requests.get(URL, params=params, timeout=120)

        print("HTTP status:", response.status_code)
        response.raise_for_status()

        data = response.json()

    except requests.RequestException as error:
        print("ERROR: Weather API request failed.")
        print(str(error))
        return

    except ValueError:
        print("ERROR: The API did not return valid JSON.")
        return

    # Open-Meteo may return a list when multiple locations are requested.
    if isinstance(data, list):
        location_data = data
    elif isinstance(data, dict) and "hourly" in data:
        location_data = [data]
    else:
        print("ERROR: No hourly weather data was returned.")
        print(data.get("reason", "Unexpected API response format.")
              if isinstance(data, dict) else "Unexpected response.")
        return

    frames = []

    for location_id, item in enumerate(location_data):
        hourly = item.get("hourly")

        if not hourly or "time" not in hourly:
            print(f"WARNING: No hourly data for location {location_id}.")
            continue

        frame = pd.DataFrame(hourly)
        frame["location_id"] = location_id
        frames.append(frame)

    if not frames:
        print("ERROR: No usable hourly weather records were returned.")
        return

    result = pd.concat(frames, ignore_index=True)

    # Standardize column names to match the project's weather data.
    result = result.rename(
        columns={
            "temperature_2m": "temperature_c",
            "relative_humidity_2m": "relative_humidity_pct",
            "precipitation": "precipitation_mm",
            "cloud_cover": "cloud_cover_pct",
            "wind_speed_10m": "wind_speed_kmh",
        }
    )

    result["time"] = pd.to_datetime(result["time"], errors="coerce")
    result = result.dropna(subset=["time"])
    result = result.sort_values(
        ["location_id", "time"]
    ).reset_index(drop=True)

    if result.empty:
        print("ERROR: No valid timestamps were returned.")
        return

    # Save the CSV once, after all records have been prepared.
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False)

    # Print a short summary, not the full weather data.
    print("\nWeather fetch completed.")
    print("Locations returned:", result["location_id"].nunique())
    print("Total records:", len(result))
    print("First timestamp:", result["time"].min())
    print("Last timestamp:", result["time"].max())
    print("CSV saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
