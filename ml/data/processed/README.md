
# Weather Dataset Documentation

## 1. Purpose
This folder contains processed weather data for the AI-Based Smart Logistics and Accessibility Intelligence Platform for North Eastern Region (NER).

Weather variables support analysis of rainfall and other conditions that may contribute to road disruption risk.

## 2. Data Sources
- Historical hourly weather: Open-Meteo historical/archive data.
- Recent weather: Open-Meteo archive API output for October 1–3, 2026.
- Location metadata: Coordinates and elevation associated with the 16 weather locations.

The exact data product and retrieval details should be retained with the project's source scripts and collection notes.

## 3. Files

| File | Description |
|---|---|
| `weather_processed.csv` | Cleaned and standardized historical hourly weather |
| `weather_features.csv` | Historical weather with rolling rainfall features |
| `weather_recent_oct2026.csv` | Recent hourly weather for October 1–3, 2026 |
| `weather_locations.csv` | Location IDs, coordinates, elevation and timezone |
| `field_reports/field_reports_weather_locations.csv` | Field reports matched to their nearest weather location |
| `field_reports/field_reports_with_weather.csv` | Field reports joined with hourly weather data |

## 4. Historical Weather

- Rows: 561,024
- Locations: 16
- Period: January 1, 2022 – December 31, 2025
- Frequency: Hourly
- Missing values in the validated file: 0
- Duplicate location/time pairs: 0

Standardized columns:
- `location_id`
- `time`
- `temperature_c`
- `relative_humidity_pct`
- `precipitation_mm`
- `cloud_cover_pct`
- `wind_speed_kmh`

## 5. Rainfall Features

The file `weather_features.csv` contains:
- `precipitation_sum_3h_mm`
- `precipitation_sum_6h_mm`
- `precipitation_sum_24h_mm`

These are rolling precipitation sums calculated separately for each location.

Initial missing values are expected because each rolling window requires sufficient preceding hourly records:
- 3-hour feature: 32 missing values
- 6-hour feature: 80 missing values
- 24-hour feature: 368 missing values

Do not replace these missing values with zero without a documented reason.

## 6. Recent Weather

- Period: October 1–3, 2026
- Locations: 16
- Rows: 1,152
- Expected frequency: Hourly
- Missing values in the validated file: 0

The source and data product should be checked before describing these records as finalized observations. API responses may contain model-derived or reanalysis data.

## 7. Field Report Matching

- Field reports: 15
- Reports with matched weather: 15
- Reports without matched weather: 0

Each report is associated with its nearest weather location and the nearest hourly timestamp.

Important limitations:
- Weather coordinates do not exactly match every report's GPS coordinates.
- Nearest-location matching uses straight-line distance, not road distance.
- Matching a timestamp to the nearest hour does not establish the exact weather conditions at the incident time.

## 8. Geographic Coverage

The dataset contains 16 weather locations intended to represent the Northeast Indian region.

State-level coverage must be verified against an authoritative geographic boundary dataset. Sixteen points do not establish complete coverage of all districts or roads.

## 9. Validation

The validation script is `ml/validate_weather_pipeline.py`.

The latest validation run confirmed:
- No missing values in historical or recent weather files.
- No duplicate historical location/time pairs.
- No negative rolling rainfall totals.
- All 15 field reports have matched weather records.

These checks verify basic data consistency, not scientific accuracy or predictive performance.

## 10. Limitations

- Weather locations are sparse relative to the full road network.
- Weather conditions may vary substantially between locations.
- Historical disaster records may not contain precise incident timestamps.
- Weather data alone cannot establish whether a disaster occurred.
- Training labels and model performance require separate validation.

## 11. Reproducibility

Retain the data collection, cleaning, feature-generation, matching and validation scripts in the repository. Record source URLs, retrieval dates, API parameters and any transformations used.
