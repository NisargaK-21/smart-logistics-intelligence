# Person 2 — Risk & Machine Learning Module (NER-ResQ)

**Module Owner:** Person 2 (Risk & ML)\
**Branch:** `feature/risk-ml-module`\
**System:** AI-Based Smart Logistics and Accessibility Intelligence Platform for Northeast India\

---

## 1. Overview & Responsibilities

The **Risk & ML Module** evaluates transportation disruption risk across road network segments in the Northeast Region (NER) of India. It ingests:
- Geometric and infrastructural road attributes (slope, classification, surface, one-way status) from Person 1 (GIS & Routing).
- Meteorological observations and rolling rainfall aggregations (hourly, 3-hour, 6-hour, 24-hour precipitation and wind speed).
- Historical disaster inventory data (Geological Survey of India landslide records and Central Water Commission flood data).

The module produces segment-level risk assessments adhering to the backend orchestrator's contract (`docs/api-contract.md` §4.2), quantifying risk into integer scores (0–100), standard risk levels, explanatory risk factors, and explicit data-quality states.

---

## 2. Interface Contract Specification

### Primary Function: `score(segments, context)`

```python
from ml.risk_assessment import score

scores = score(segments=segments_payload, context=context_payload)
```

#### Inputs
- `segments`: List of segment dictionaries (or objects conforming to `SegmentRecord`) containing:
  - `segment_id` (str): Unique segment identifier.
  - `coordinates` (list[list[float]]): Array of `[longitude, latitude]` coordinate pairs.
  - `slope_deg` or `slope` (float, optional): Gradient angle or percentage.
  - `road_class` (str): e.g. `"national_highway"`, `"state_highway"`, `"secondary"`, `"major"`, `"local"`.
  - `surface` (str, optional): e.g. `"asphalt"`, `"paved"`, `"gravel"`, `"dirt"`.
  - `length_km` (float): Segment length in kilometers.
- `context`: Dictionary containing operational parameters:
  - `vehicle_type` (str): `"truck"`, `"van"`, or `"car"` (defaults to `"truck"`).
  - `departure_time` or `as_of` (str): ISO 8601 timestamp with offset (e.g. `"2026-10-28T10:00:00+05:30"`).
  - `weather_available` (bool, optional): Allows upstream orchestrator to indicate weather service status.
  - `risk_source` (str, optional): `"baseline"` or `"model"` (defaults to `"baseline"`).

#### Output Format
Returns a dictionary mapping each `segment_id` to its risk breakdown:
```python
{
  "seg-ab": {
    "score": 38,
    "risk_level": "medium",
    "factors": [
      {
        "name": "steep_terrain",
        "contribution": 18.0,
        "detail": "Terrain slope is 6.0%, elevating rollover and brake wear risk."
      },
      {
        "name": "road_infrastructure",
        "contribution": 12.0,
        "detail": "Road classification 'national_highway' carries baseline infrastructure risk."
      },
      {
        "name": "past_disruptions",
        "contribution": 10.0,
        "detail": "Segment is near historical landslide zones (24.3 km away)."
      }
    ],
    "data_quality": "complete",
    "risk_source": "baseline"
  }
}
```

### Backward-Compatible Functions
For compatibility with earlier internal scripts and route evaluation fixtures:
- `score_segments(segments, context) -> list[dict]`: Preserves legacy dictionary schema with `hazard_indicators`, `component_scores`, `reasons`, and boolean `data_quality` flags.
- `score_route(route, context) -> dict`: Evaluates route-segment associations.
- `score_routes(routes, context) -> list[dict]`: Evaluates multiple routes.

---

## 3. Risk Thresholds

All risk levels are aligned with the backend contract:

| Risk Level | Score Range | Description |
| :--- | :--- | :--- |
| **LOW** | `0 – 33` | Minimal hazard; standard transit speeds and normal operational procedures. |
| **MEDIUM** | `34 – 66` | Elevated hazard; caution recommended (reduced speed, heightened monitoring). |
| **HIGH** | `67 – 100` | Severe hazard; significant disruption probability (washout, landslide, vehicle immobilization). Re-routing strongly advised. |

*Note: In code, `score()` emits lowercase string levels (`"low"`, `"medium"`, `"high"`) matching API JSON schemas, while legacy `score_segments()` preserves uppercase strings (`"LOW"`, `"MEDIUM"`, `"HIGH"`).*

---

## 4. Safety & Incomplete Data Quality Handling

The platform enforces a core safety principle: **Missing data is never treated as evidence of safety.**

### Data Quality States
1. `"complete"`: All required attributes (coordinates, slope, weather, historical exposure) are fresh and valid.
2. `"partial"`: One or more data streams are degraded or missing (e.g. slope unavailable, weather station distant, future observations only). The score is calculated from remaining available factors with explicit uncertainty factors.
3. `"stale"`: Weather observation is older than 24.0 hours relative to departure time (`DEFAULT_MAX_STALE_HOURS`).
4. `"unavailable"`: Core coordinates or identifiers are completely missing, preventing geospatial correlation.

### Edge Case Protections
- **Missing Weather:** If the weather provider is unreachable, or if only future observations exist relative to the departure time, `data_quality` is flagged `"partial"` and the factor `{"name": "weather_unavailable", "contribution": 0.0, "detail": "Weather data could not be fetched..."}` is attached. The road baseline infrastructure and terrain risks are preserved.
- **Distant Weather Stations:** In mountainous terrain, micro-climates vary rapidly. If the nearest weather station is $> 50\text{ km}$ away, a `distant_weather_station` factor is attached and data quality is degraded to `"partial"`. If $> 150\text{ km}$, weather is deemed unusable.
- **Stale Observations:** If weather records are $> 24.0\text{ hours}$ old, data quality is flagged `"stale"` and a `stale_weather` factor is added.
- **Missing Slope:** If `slope_deg` is missing (`None`), slope is not assumed to be $0^\circ$ (flat). `terrain_unavailable` is attached and `data_quality` is degraded to `"partial"`.
- **Invalid / Negative Sensor Readings:** Negative precipitation or wind values, NaNs, and infinite values are rejected as sensor failures (`"UNKNOWN"` status).
- **Vehicle Sensitivity Scaling:** Vehicle multipliers reflect real transport physics:
  - Heavy trucks (`vehicle_type="truck"`): $1.2\times$ sensitivity to steep terrain, road roughness, and heavy rain.
  - Light commercial vans (`vehicle_type="van"`): $1.0\times$ sensitivity.
  - Passenger cars (`vehicle_type="car"`): $0.8\times$ sensitivity.

---

## 5. Data Sources & Provenance

| Dataset | File Path | Records | Time Period | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Historical Weather** | `ml/data/processed/weather_processed.csv` | 561,024 | 2022-01-01 to 2025-12-31 | Hourly meteorological records (temperature, humidity, precipitation, wind, cloud cover) from 16 Open-Meteo stations in NER. |
| **Rolling Rainfall Features** | `ml/data/processed/weather_features.csv` | 561,024 | 2022-01-01 to 2025-12-31 | Separately computed rolling precipitation sums (3h, 6h, 24h) per station. |
| **Recent Weather** | `ml/data/processed/weather_recent_oct2026_features.csv` | 1,152 | 2026-10-01 to 2026-10-03 | High-resolution hourly recent observations with rolling rainfall sums. |
| **Weather Stations** | `ml/data/processed/weather_locations.csv` | 16 stations | Static | Geographic coordinates, elevations, and timezones covering the 8 NER states. |
| **Validated Landslides** | `ml/data/final/historical/gsi_landslides_ner_validated.csv` | 10,983 points | Historical | Validated Geological Survey of India (GSI) landslide inventory across all 8 NER states. |
| **District Flood Impact** | `ml/data/final/historical/cwc_floods_ner_clean.csv` | 116 records | 1986–2022 | Central Water Commission (CWC) district-level flood affected area and historical severity. |
| **Field Incident Reports** | `ml/data/raw/field_reports/field_reports.csv` | 15 reports | 2026-10-01 to 2026-10-03 | Sample incident reports from operators along the Guwahati–Shillong corridor. |

---

## 6. Machine Learning Feasibility & Model Adapter

### Dataset Feasibility Evaluation
The project permits synthetic labels for a clearly disclosed, reproducible pipeline demonstration. This permission does not make synthetic labels real incident outcomes or support real-world accuracy claims.

The current data has **no verified segment-time disruption labels or negative road-traversal controls**. The 15 field reports are not sufficient for real-world supervised training; historical landslide points and district flood aggregates are not synchronized segment-time outcomes. Real-world supervised disruption prediction is therefore not currently feasible.

The historical weather feature table can support a **synthetic weather-risk classification demonstration**. `ml/scripts/train_weather_risk_model.py` generates each row's label by applying `calculate_weather_risk` to the same five weather features used by the rule-based baseline. These are heuristic-generated labels, not observed outcomes. The classifier can only demonstrate reproducibility and approximation of the existing rules; its test metrics are not evidence of real-world predictive accuracy.

The training script uses a chronological 80/20 split, reports class counts and metrics for Logistic Regression, a majority-class baseline, and the deterministic rule baseline, and writes a machine-readable evaluation report. Acceptance criteria are declared before evaluation and require at least 20 held-out examples per class, macro-F1 of 0.80, accuracy of 0.80, and a 0.10 macro-F1 improvement over the majority baseline. Regardless of synthetic evaluation results, production activation is disabled.

Install the ML dependencies and run the experiment with:

```bash
python -m pip install -r ml/requirements.txt
python ml/scripts/train_weather_risk_model.py
```

By default, the report is written to `ml/data/processed/weather_risk_model_evaluation.json` and the experimental pipeline artifact to `ml/models/weather_risk_logistic_regression.joblib`. Existing artifacts are never overwritten. The shared feature schema is defined in `ml/risk_model_features.py`; the production weather baseline consumes the same schema.

On the current historical feature file, 368 rows with incomplete rolling windows were excluded. The chronological split had 448,512 training rows and 112,144 test rows; the test set contained 112,063 LOW, 79 MEDIUM, and 2 HIGH heuristic labels. Logistic Regression scored 99.89% accuracy and 0.684 macro-F1, versus 99.93% accuracy and 0.333 macro-F1 for a majority-class classifier. The rule baseline scored 100% on its own generated labels, as expected. The predeclared minimum of 20 held-out samples per class was not met, so the experiment failed its support criterion. These figures measure rule imitation on synthetic labels only and are not real-world predictive metrics.

### Pluggable Model Adapter
The experimental adapter (`score_segment_model`) loads only the weather classifier artifact, checks its feature schema, preprocessing pipeline, synthetic label and dataset provenance, and recomputes the declared evaluation gates from its embedded test metrics. It is callable only through the explicit `risk_source="experimental_model"` opt-in. The artifact currently fails these gates and is rejected; the public scorer discards any partial model results and recomputes every segment with deterministic rules. The backend route service does not opt in, and its normal source remains `baseline`.

Even a future synthetic artifact passing the demonstration gates remains experimental and must never be treated as production road-disruption prediction. Production model activation requires real-world segment-time labels, independent validation, and separate acceptance review. Missing, invalid, stale, distant, or incomplete weather inputs are rejected for classifier inference and cause baseline fallback.

---

## 7. How to Run Tests & Verification

All tests can be executed directly inside the repository without external network dependencies:

### 1. Run Risk & ML, Backend, and Routing Tests
```bash
python -m pytest ml/test_risk_assessment.py ml/test_weather_risk_baseline.py ml/test_risk_module_contract.py ml/test_weather_risk_model_training.py ml/test_risk_model_inference.py backend/tests routing/tests -v
```

`ml/scripts/test_boundary_repair.py` is a GIS-specific test and requires the optional GeoPandas dependency; it is not part of the Risk & ML, backend, and routing test command above.

### 2. Run Pipeline Data Validation
```bash
python ml/validate_weather_pipeline.py
```

### 3. Run Geographic Coverage Verification
```bash
python ml/check_northeast_coverage.py
```

### 4. Run Dataset Feasibility Evaluation
```bash
python ml/scripts/evaluate_dataset_feasibility.py
```

### 5. Verify GIS & Routing Compatibility
```bash
python -m pytest routing/tests -v
```

### Model Readiness and Fallback

The training report is `ml/data/processed/weather_risk_model_evaluation.json`; the experimental classifier and preprocessing pipeline are stored together at `ml/models/weather_risk_logistic_regression.joblib`. Artifact loading checks the feature schema, pipeline types, label/data provenance, and embedded evaluation results. Runtime acceptance checks enforce the recorded thresholds (at least 20 held-out samples per class, macro-F1 >= 0.80, accuracy >= 0.80, and macro-F1 improvement >= 0.10 over the majority baseline).

The current artifact fails acceptance and is rejected. The default scorer and backend remain on deterministic baseline rules. A model inference failure discards partial model scores and recomputes all requested scores with the baseline. Only the module-level explicit `risk_source="experimental_model"` option can request the experimental weather classifier; the backend route service does not enable that option.

All reported classifier metrics are based on synthetic labels generated from the deterministic weather rules. They demonstrate rule imitation only, not real-world predictive accuracy. Verified segment-time disruption labels and non-incident traversal controls are still required for real-world model validation.
