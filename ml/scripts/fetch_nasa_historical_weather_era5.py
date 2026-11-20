"""Fetch Historical ERA5 Weather for NASA Global Landslide Catalog (2007-2016).

GitHub Issue #32 — Phase 5: Historical Weather Acquisition.

Queries Open-Meteo Historical Weather API (ERA5 reanalysis) for actual coordinates
and dates of the 442 NASA GLC landslide events in Northeast India, Assam, Meghalaya,
and the Guwahati-Shillong corridor.

Requirements & Standards:
- Preserves raw NASA source catalog unchanged.
- Caches raw JSON responses locally in ml/data/cache/open_meteo_era5/ to avoid duplicate API requests.
- Supports resuming interrupted downloads seamlessly.
- Computes hourly variables: temperature_c, relative_humidity_pct, precipitation_mm,
  wind_speed_kmh, wind_gusts_kmh, cloud_cover_pct, elevation_m.
- Computes rolling precipitation totals (3h, 6h, 24h) from continuous hourly series.
- Preserves exact nearest grid cell coordinates and Haversine distance in km.
- Explicitly documents temporal matching method: 'exact_reported_hour' vs 'daily_peak_precipitation_hour'.
- Maintains separate priority flags for Corridor, Assam/Meghalaya, and Wider NER.
- Generates structured CSV dataset and machine-readable audit report.
"""

from __future__ import annotations

import json
import logging
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fetch_nasa_era5")

ROOT = Path(__file__).resolve().parents[2]
RAW_NASA_PATH = ROOT / "ml" / "data" / "raw" / "landslides" / "nasa_global_landslide_catalog.csv"
MATCHED_EVENTS_PATH = ROOT / "ml" / "data" / "processed" / "disaster" / "empirical_events_matched.csv"
CACHE_DIR = ROOT / "ml" / "data" / "cache" / "open_meteo_era5"
OUTPUT_CSV_PATH = ROOT / "ml" / "data" / "processed" / "disaster" / "nasa_glc_historical_weather_era5.csv"
OUTPUT_REPORT_PATH = ROOT / "ml" / "data" / "processed" / "disaster" / "nasa_glc_era5_audit_report.json"

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Spatial bounding boxes
CORRIDOR_LAT_MIN, CORRIDOR_LAT_MAX = 25.50, 26.30
CORRIDOR_LON_MIN, CORRIDOR_LON_MAX = 91.50, 92.20

MAX_GRID_DISTANCE_KM_THRESHOLD = 30.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great Circle distance in km between two decimal coordinates."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def is_in_corridor(lat: float, lon: float) -> bool:
    """Return True if coordinates fall strictly in Guwahati-Shillong corridor box."""
    return (CORRIDOR_LAT_MIN <= lat <= CORRIDOR_LAT_MAX) and (CORRIDOR_LON_MIN <= lon <= CORRIDOR_LON_MAX)


def fetch_open_meteo_era5_with_retry(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    max_retries: int = 4,
    backoff_factor: float = 1.5,
) -> dict[str, Any]:
    """Fetch hourly historical ERA5 weather from Open-Meteo with retry and exponential backoff."""
    params = {
        "latitude": f"{lat:.5f}",
        "longitude": f"{lon:.5f}",
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_gusts_10m,cloud_cover",
        "timezone": "UTC",
        "wind_speed_unit": "kmh",
    }
    url = f"{OPEN_METEO_ARCHIVE_URL}?{urllib.parse.urlencode(params)}"

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "AntigravitySmartLogistics/1.0 (historical-weather-ground-truth)"},
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data
                raise urllib.error.HTTPError(url, resp.status, "Non-200 status", resp.headers, None)
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429:
                wait_time = backoff_factor * (2 ** attempt) + 1.0
                logger.warning("HTTP 429 rate limit. Waiting %.1fs (attempt %d/%d)...", wait_time, attempt + 1, max_retries)
                time.sleep(wait_time)
            elif e.code in (500, 502, 503, 504):
                wait_time = backoff_factor * (2 ** attempt)
                logger.warning("HTTP %d server error. Waiting %.1fs (attempt %d/%d)...", e.code, wait_time, attempt + 1, max_retries)
                time.sleep(wait_time)
            else:
                logger.error("HTTP %d error for %s: %s", e.code, url, e)
                raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_error = e
            wait_time = backoff_factor * (2 ** attempt) + 0.5
            logger.warning("Connection error (%s). Retrying in %.1fs (attempt %d/%d)...", type(e).__name__, wait_time, attempt + 1, max_retries)
            time.sleep(wait_time)

    raise RuntimeError(f"Failed to fetch ERA5 weather after {max_retries} attempts: {last_error}")


def get_era5_for_event(
    event: dict[str, Any],
    cache_dir: Path,
) -> dict[str, Any]:
    """Retrieve ERA5 data for an event, loading from cache if present or querying API."""
    event_id = str(event["event_id"])
    cache_file = cache_dir / f"{event_id}.json"

    # Check disk cache
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            if "hourly" in cached_data and "time" in cached_data["hourly"] and len(cached_data["hourly"]["time"]) > 0:
                cached_data["from_cache"] = True
                return cached_data
        except Exception as e:
            logger.warning("Corrupted cache file %s: %s. Re-fetching.", cache_file, e)

    # Date range: start 24h before event date to allow rolling 24h accumulation
    event_timestamp = pd.to_datetime(event["event_date"], utc=True)
    target_date = event_timestamp.date()
    start_date = (target_date - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = target_date.strftime("%Y-%m-%d")

    data = fetch_open_meteo_era5_with_retry(
        lat=float(event["latitude"]),
        lon=float(event["longitude"]),
        start_date=start_date,
        end_date=end_date,
    )
    data["from_cache"] = False

    # Save to disk cache
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    temp_cache = cache_file.with_suffix(".tmp")
    with open(temp_cache, "w", encoding="utf-8") as f:
        json.dump(data, f)
    temp_cache.replace(cache_file)

    return data


def extract_weather_features_for_event(
    event: dict[str, Any],
    era5_data: dict[str, Any],
) -> dict[str, Any]:
    """Process hourly ERA5 series into verified event weather attributes."""
    event_id = str(event["event_id"])
    event_lat = float(event["latitude"])
    event_lon = float(event["longitude"])
    event_timestamp = pd.to_datetime(event["event_date"], utc=True)

    grid_lat = float(era5_data.get("latitude", np.nan))
    grid_lon = float(era5_data.get("longitude", np.nan))
    grid_elev = float(era5_data.get("elevation", np.nan))

    grid_dist_km = haversine_km(event_lat, event_lon, grid_lat, grid_lon) if (pd.notna(grid_lat) and pd.notna(grid_lon)) else np.nan

    result: dict[str, Any] = {
        "event_id": event_id,
        "original_id": str(event.get("original_id", event_id.replace("NASA_GLC_", ""))),
        "source": "NASA_GLC",
        "disaster_type": "landslide",
        "event_date": event["event_date"],
        "event_timestamp": event_timestamp.isoformat(),
        "state": event.get("state", "Unknown"),
        "district": event.get("district", "Unknown"),
        "latitude": event_lat,
        "longitude": event_lon,
        "coordinate_valid": True,
        "is_corridor": is_in_corridor(event_lat, event_lon),
        "is_assam_meghalaya": event.get("state", "") in ("Assam", "Meghalaya") or is_in_corridor(event_lat, event_lon),
        "is_wider_ner": event.get("state", "") not in ("Assam", "Meghalaya") and not is_in_corridor(event_lat, event_lon),
        "era5_grid_latitude": grid_lat,
        "era5_grid_longitude": grid_lon,
        "era5_grid_elevation_m": grid_elev,
        "era5_grid_distance_km": round(grid_dist_km, 4) if pd.notna(grid_dist_km) else np.nan,
        "weather_matched": False,
        "weather_match_status": "unmatched_unknown",
        "temporal_matching_method": "none",
        "is_reported_time_exact": False,
        "matched_weather_time": None,
        "precipitation_mm": np.nan,
        "precipitation_sum_3h_mm": np.nan,
        "precipitation_sum_6h_mm": np.nan,
        "precipitation_sum_24h_mm": np.nan,
        "temperature_c": np.nan,
        "relative_humidity_pct": np.nan,
        "wind_speed_kmh": np.nan,
        "wind_gusts_kmh": np.nan,
        "cloud_cover_pct": np.nan,
        "daily_precipitation_total_mm": np.nan,
        "daily_max_hourly_precipitation_mm": np.nan,
        "provenance": "NASA_GLC + Open-Meteo ERA5 Reanalysis (0.1 deg grid)",
    }

    # Verify spatial grid distance
    if np.isnan(grid_dist_km) or grid_dist_km > MAX_GRID_DISTANCE_KM_THRESHOLD:
        result["weather_match_status"] = "unmatched_spatial_grid_too_far"
        return result

    hourly = era5_data.get("hourly")
    if not hourly or "time" not in hourly or not hourly["time"]:
        result["weather_match_status"] = "unmatched_api_empty_hourly"
        return result

    df_h = pd.DataFrame(hourly)
    df_h["time"] = pd.to_datetime(df_h["time"], utc=True)
    df_h = df_h.sort_values("time").reset_index(drop=True)

    # Compute continuous rolling antecedent sums
    df_h["p3h"] = df_h["precipitation"].rolling(3, min_periods=1).sum()
    df_h["p6h"] = df_h["precipitation"].rolling(6, min_periods=1).sum()
    df_h["p24h"] = df_h["precipitation"].rolling(24, min_periods=1).sum()

    target_date = event_timestamp.date()
    df_day = df_h[df_h["time"].dt.date == target_date]

    if df_day.empty:
        result["weather_match_status"] = "unmatched_target_date_missing"
        return result

    # Daily macro context
    daily_total = float(df_day["precipitation"].sum())
    daily_max_h = float(df_day["precipitation"].max())
    result["daily_precipitation_total_mm"] = round(daily_total, 2)
    result["daily_max_hourly_precipitation_mm"] = round(daily_max_h, 2)

    # Temporal matching strategy
    has_explicit_hour = not (event_timestamp.hour == 0 and event_timestamp.minute == 0 and event_timestamp.second == 0)

    if has_explicit_hour:
        # Match nearest hour on that date
        rounded_time = event_timestamp.round("h")
        hour_matches = df_h[df_h["time"] == rounded_time]
        if not hour_matches.empty:
            match_row = hour_matches.iloc[0]
            result["temporal_matching_method"] = "exact_reported_hour"
            result["is_reported_time_exact"] = True
        else:
            # Fallback to closest hour on target date
            diffs = (df_day["time"] - event_timestamp).abs()
            match_row = df_day.loc[diffs.idxmin()]
            result["temporal_matching_method"] = "nearest_hourly_timestamp"
            result["is_reported_time_exact"] = False
    else:
        # Date-level reporting (midnight 00:00:00)
        # Select hour of peak precipitation intensity on event date, or 12:00 UTC if dry
        if daily_max_h > 0.0:
            peak_idx = df_day["precipitation"].idxmax()
            match_row = df_day.loc[peak_idx]
            result["temporal_matching_method"] = "daily_peak_precipitation_hour"
        else:
            # Noon observation as representative midday sample
            noon_matches = df_day[df_day["time"].dt.hour == 12]
            match_row = noon_matches.iloc[0] if not noon_matches.empty else df_day.iloc[len(df_day) // 2]
            result["temporal_matching_method"] = "daily_midday_dry_day"
        result["is_reported_time_exact"] = False

    # Populate matched hourly features
    result["weather_matched"] = True
    result["weather_match_status"] = "matched"
    result["matched_weather_time"] = match_row["time"].isoformat()
    result["precipitation_mm"] = round(float(match_row.get("precipitation", 0.0)), 2)
    result["precipitation_sum_3h_mm"] = round(float(match_row.get("p3h", 0.0)), 2)
    result["precipitation_sum_6h_mm"] = round(float(match_row.get("p6h", 0.0)), 2)
    result["precipitation_sum_24h_mm"] = round(float(match_row.get("p24h", 0.0)), 2)
    result["temperature_c"] = round(float(match_row.get("temperature_2m", np.nan)), 2)
    result["relative_humidity_pct"] = round(float(match_row.get("relative_humidity_2m", np.nan)), 2)
    result["wind_speed_kmh"] = round(float(match_row.get("wind_speed_10m", np.nan)), 2)
    result["wind_gusts_kmh"] = round(float(match_row.get("wind_gusts_10m", np.nan)), 2)
    result["cloud_cover_pct"] = round(float(match_row.get("cloud_cover", np.nan)), 2)

    return result


def run_historical_weather_acquisition() -> tuple[pd.DataFrame, dict[str, Any]]:
    """Execute download, caching, feature extraction and verification for all 442 NASA events."""
    logger.info("Starting Historical ERA5 Weather Acquisition for NASA GLC (2007-2016)...")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load 442 NASA events from matched events table (or fallback to raw NASA)
    if MATCHED_EVENTS_PATH.exists():
        logger.info("Loading events from %s...", MATCHED_EVENTS_PATH)
        df_matched = pd.read_csv(MATCHED_EVENTS_PATH)
        nasa_events_df = df_matched[df_matched["source"] == "NASA_GLC"].copy()
    else:
        raise FileNotFoundError(f"Matched events file missing: {MATCHED_EVENTS_PATH}")

    total_events = len(nasa_events_df)
    logger.info("Loaded %d NASA GLC events.", total_events)

    # Sort to prioritise: 1) Corridor, 2) Assam & Meghalaya, 3) Wider NER
    def get_priority(row: pd.Series) -> int:
        lat, lon = float(row["latitude"]), float(row["longitude"])
        st = str(row.get("state", "")).lower()
        if is_in_corridor(lat, lon):
            return 1
        if "assam" in st or "meghalaya" in st:
            return 2
        return 3

    nasa_events_df["priority"] = nasa_events_df.apply(get_priority, axis=1)
    nasa_events_df = nasa_events_df.sort_values(["priority", "event_date"]).reset_index(drop=True)

    event_dicts = nasa_events_df.to_dict(orient="records")

    # 2. Concurrently fetch and cache ERA5 weather
    logger.info("Querying Open-Meteo ERA5 archive with caching in %s...", CACHE_DIR)
    t_start = time.time()
    results: list[dict[str, Any]] = []

    # Use ThreadPoolExecutor with controlled concurrency (4 workers) and polite rate pacing
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_event = {
            executor.submit(get_era5_for_event, ev, CACHE_DIR): ev
            for ev in event_dicts
        }

        completed_count = 0
        from_cache_count = 0
        for future in as_completed(future_to_event):
            ev = future_to_event[future]
            completed_count += 1
            try:
                era5_data = future.result()
                if era5_data.get("from_cache", False):
                    from_cache_count += 1
                features = extract_weather_features_for_event(ev, era5_data)
                results.append(features)
            except Exception as e:
                logger.error("Failed processing event %s: %s", ev.get("event_id"), e)
                fallback = {
                    "event_id": str(ev.get("event_id")),
                    "original_id": str(ev.get("original_id")),
                    "source": "NASA_GLC",
                    "disaster_type": "landslide",
                    "event_date": ev.get("event_date"),
                    "latitude": float(ev.get("latitude")),
                    "longitude": float(ev.get("longitude")),
                    "weather_matched": False,
                    "weather_match_status": f"unmatched_error: {type(e).__name__}",
                }
                results.append(fallback)

            if completed_count % 50 == 0 or completed_count == total_events:
                logger.info(
                    "Progress: %d / %d events processed (%d from cache, elapsed: %.1fs)",
                    completed_count,
                    total_events,
                    from_cache_count,
                    time.time() - t_start,
                )

    df_out = pd.DataFrame(results)

    # Reorder according to priority and event_date
    df_out["priority"] = df_out.apply(
        lambda r: 1 if r["is_corridor"] else (2 if r["is_assam_meghalaya"] else 3),
        axis=1,
    )
    df_out = df_out.sort_values(["priority", "event_date"]).drop(columns=["priority"]).reset_index(drop=True)

    # 3. Save CSV
    df_out.to_csv(OUTPUT_CSV_PATH, index=False)
    logger.info("Saved ERA5 matched dataset with %d rows to %s", len(df_out), OUTPUT_CSV_PATH)

    # 4. Generate comprehensive audit report
    matched_count = int(df_out["weather_matched"].sum())
    unmatched_count = int((~df_out["weather_matched"]).sum())

    temporal_methods = df_out["temporal_matching_method"].value_counts().to_dict()
    grid_distances = df_out["era5_grid_distance_km"].dropna()

    audit_report = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "task": "Issue #32 — Phase 5: Historical ERA5 Weather Acquisition for NASA GLC (2007-2016)",
        "source_catalog": str(RAW_NASA_PATH.relative_to(ROOT)),
        "output_dataset": str(OUTPUT_CSV_PATH.relative_to(ROOT)),
        "cache_directory": str(CACHE_DIR.relative_to(ROOT)),
        "api_endpoint": OPEN_METEO_ARCHIVE_URL,
        "total_nasa_events": total_events,
        "successfully_weather_matched": matched_count,
        "unmatched_events": unmatched_count,
        "matching_success_rate_pct": round(matched_count / total_events * 100.0, 2),
        "geographic_breakdown": {
            "guwahati_shillong_corridor": int(df_out["is_corridor"].sum()),
            "assam_and_meghalaya": int(df_out["is_assam_meghalaya"].sum()),
            "wider_northeast_india": int(df_out["is_wider_ner"].sum()),
        },
        "temporal_matching_methods": temporal_methods,
        "reported_time_exactness": {
            "exact_reported_hour": int(df_out["is_reported_time_exact"].sum()),
            "date_level_daily_peak_hour": int((~df_out["is_reported_time_exact"] & df_out["weather_matched"]).sum()),
        },
        "spatial_grid_matching": {
            "min_grid_distance_km": round(float(grid_distances.min()), 4) if not grid_distances.empty else None,
            "max_grid_distance_km": round(float(grid_distances.max()), 4) if not grid_distances.empty else None,
            "median_grid_distance_km": round(float(grid_distances.median()), 4) if not grid_distances.empty else None,
            "mean_grid_distance_km": round(float(grid_distances.mean()), 4) if not grid_distances.empty else None,
            "within_10km_pct": round(float((grid_distances <= 10.0).mean() * 100.0), 2) if not grid_distances.empty else None,
            "within_20km_pct": round(float((grid_distances <= 20.0).mean() * 100.0), 2) if not grid_distances.empty else None,
        },
        "weather_feature_completeness": {
            "precipitation_mm": int(df_out["precipitation_mm"].notna().sum()),
            "precipitation_sum_3h_mm": int(df_out["precipitation_sum_3h_mm"].notna().sum()),
            "precipitation_sum_6h_mm": int(df_out["precipitation_sum_6h_mm"].notna().sum()),
            "precipitation_sum_24h_mm": int(df_out["precipitation_sum_24h_mm"].notna().sum()),
            "temperature_c": int(df_out["temperature_c"].notna().sum()),
            "relative_humidity_pct": int(df_out["relative_humidity_pct"].notna().sum()),
            "wind_speed_kmh": int(df_out["wind_speed_kmh"].notna().sum()),
            "wind_gusts_kmh": int(df_out["wind_gusts_kmh"].notna().sum()),
            "cloud_cover_pct": int(df_out["cloud_cover_pct"].notna().sum()),
        },
        "year_distribution": df_out["event_date"].str[:4].value_counts().sort_index().to_dict(),
        "unmatched_reasons": df_out[~df_out["weather_matched"]]["weather_match_status"].value_counts().to_dict(),
    }

    with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)
    logger.info("Audit report written to %s", OUTPUT_REPORT_PATH)

    return df_out, audit_report


if __name__ == "__main__":
    df, rpt = run_historical_weather_acquisition()
    print("\n=== NASA GLC ERA5 Weather Acquisition Completed ===")
    print(f"Total events: {rpt['total_nasa_events']}")
    print(f"Successfully matched: {rpt['successfully_weather_matched']}")
    print(f"Unmatched: {rpt['unmatched_events']}")
    print(f"Corridor events: {rpt['geographic_breakdown']['guwahati_shillong_corridor']}")
    print(f"Assam/Meghalaya: {rpt['geographic_breakdown']['assam_and_meghalaya']}")
    print(f"Median grid distance: {rpt['spatial_grid_matching']['median_grid_distance_km']} km")
    print(f"Dataset: {rpt['output_dataset']}")
