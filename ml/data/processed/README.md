
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

## 11. Deterministic Risk Baseline

The production default is the deterministic segment scorer in `ml/risk_assessment.py`, not the Logistic Regression classifier. It combines road class, slope, and surface factors with the threshold-based weather score from `calculate_weather_risk` and proximity to validated historical landslide points; vehicle type also adjusts the score. It returns an explainable 0–100 risk index, a risk category, factors, and data-quality information. The score is a heuristic index, not a calibrated probability of a disruption.

Weather scoring requires hourly precipitation, 3-hour, 6-hour, and 24-hour rainfall totals, and wind speed. Missing or invalid required values remain incomplete/UNKNOWN rather than being replaced with zero. When weather is unavailable, the baseline reports degraded data quality and retains the available road and historical factors. Historical disaster inventories and sparse station observations provide context, not verified segment-time outcomes.

## 12. Synthetic Weather-Model Demonstration

The project permits explicitly disclosed synthetic labels for demonstrating a reproducible ML pipeline. The optional weather classifier in `ml/scripts/train_weather_risk_model.py` labels each historical weather row by applying the deterministic `calculate_weather_risk` rules to that row's precipitation and wind features. Each generated label is marked `synthetic_heuristic` in the training frame's `label_provenance` column and the saved model metadata.

These labels represent the existing rule's LOW/MEDIUM/HIGH categories, not observed incidents or road disruptions. Model metrics only measure approximation of that rule and must not be presented as evidence of real-world predictive accuracy. The 15 matched field reports do not provide adequate independent positive and negative segment-time outcomes.

The classifier uses the shared five-column schema in `ml/risk_model_features.py` and a chronological 80/20 split to evaluate a Logistic Regression pipeline against majority-class and deterministic-rule baselines. Its evaluation report records class counts, split sizes, metrics, rule provenance, and acceptance criteria.

Macro-F1 averages the F1 score for each class equally, helping reveal poor minority-class performance hidden by high overall accuracy. The predefined gates include macro-F1 >= 0.80 and at least 20 held-out records per class. The current classifier has macro-F1 0.684 and only 2 held-out HIGH examples, so it fails both gates; the accuracy and majority-baseline-improvement gates passing does not override those failures. The model remains experimental and is not used for production route scoring.

From the repository root, install the ML dependencies, train/evaluate the experiment, and run the relevant tests with:

```bash
python -m pip install -r ml/requirements.txt
python ml/scripts/train_weather_risk_model.py
python -m pytest ml/test_risk_assessment.py ml/test_weather_risk_baseline.py ml/test_risk_module_contract.py ml/test_weather_risk_model_training.py ml/test_risk_model_inference.py backend/tests routing/tests -v
```

The evaluation report is `ml/data/processed/weather_risk_model_evaluation.json`; the experimental model artifact is `ml/models/weather_risk_logistic_regression.joblib`. Inference requires explicit experimental opt-in and validates artifact schema, provenance, and the reported gates. Incomplete/invalid weather or artifact/inference failure is rejected; fallback discards partial model results and recomputes all requested segments with the deterministic baseline. Passing synthetic-label gates would still not establish real-world model validity.

## 13. Reproducibility

Retain the data collection, cleaning, feature-generation, matching and validation scripts in the repository. Record source URLs, retrieval dates, API parameters and any transformations used.
