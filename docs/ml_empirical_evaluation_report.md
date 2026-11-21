# Empirical Machine Learning Risk Model Evaluation Report

**Issue:** #32 – Empirical Disaster Ground Truth and Class Imbalance Model Training & Evaluation  
**Status:** Completed  
**Artifact Generated:** `ml/data/processed/disaster/empirical_model_evaluation.json`

---

## 1. Executive Summary & Research Motivation

Prior machine learning experiments for NER-ResQ trained on synthetic labels derived from deterministic rule heuristics, achieving 99.89% training accuracy while masking complete failure on real-world disaster detection (with only 2 held-out high-risk events).

Under Issue #32, the project shifted to **empirical ground truth** by integrating:
1. **NASA Global Landslide Catalog (GLC)**: 387 landslide events (2007–2016) matched spatially to OSM road network segments and paired with ERA5 historical reanalysis weather.
2. **On-Ground Field Incident Reports**: 15 localized road disruption events (2026) across the Guwahati–Shillong transport corridor.
3. **Defensible Spatio-Temporal Background Negative Controls**: 1,000 non-event background observations sampled outside strict 25 km / 72-hour exclusion buffers from known disaster events.

---

## 2. Chronological Train / Validation / Holdout Split

To prevent temporal data leakage and benchmark true prospective generalization, data was strictly partitioned chronologically:

| Split | Timeframe | Positives | Negatives | Total | Purpose |
|---|---|:---:|:---:|:---:|---|
| **Training** | $\le 2013$ | 255 | 343 | 598 | Model training across historical NASA GLC events |
| **Validation** | $2014–2016$ | 132 | 157 | 289 | Hyperparameter tuning and model selection |
| **Holdout Test** | $2022–2026$ | 15 | 500 | 515 | Prospective evaluation on contemporary operational corridor data |

---

## 3. Strict Feature Selection & Leakage Audit

Per `ml/risk_model_features.py`:
- **Legitimate Antecedent Features (Allowlist):**
  - Meteorological: `precipitation_mm`, `precipitation_sum_3h_mm`, `precipitation_sum_6h_mm`, `precipitation_sum_24h_mm`, `temperature_c`, `wind_speed_kmh`
  - Road Infrastructure: `matched_road_class` (one-hot encoded)
- **Strictly Banned Prohibited Leaking Features:**
  - `road_distance_km` (0.0 for controls, >0.0 for point-matched events)
  - `fatalities` (post-event consequence)
  - Identifiers (`event_id`, `source`, `sample_type`, `provenance`)
  - Timestamps (`event_date`, `event_timestamp`)
  - Coordinates (`latitude`, `longitude`, `matched_road_id`)

All models passed automated leakage auditing with **zero prohibited features entering the predictor matrix**.

---

## 4. Empirical Evaluation Results

### Validation Set (2014–2016)

| Model Strategy | Accuracy | Precision | Recall | Macro-F1 | PR-AUC |
|---|:---:|:---:|:---:|:---:|:---:|
| **Logistic Regression (Unweighted)** | 99.31% | 1.0000 | 0.9848 | 0.9930 | 1.0000 |
| **Logistic Regression (Class-Weighted)** | **99.65%** | **1.0000** | **0.9924** | **0.9965** | **1.0000** |
| **Logistic Regression (Oversampled)** | 99.31% | 1.0000 | 0.9848 | 0.9930 | 1.0000 |
| **Deterministic Rules Baseline** | 87.54% | 0.7857 | 1.0000 | 0.8753 | 1.0000 |

### Prospective Holdout Test Set (2022–2026)

| Model Strategy | Accuracy | Precision | Recall | Macro-F1 | PR-AUC |
|---|:---:|:---:|:---:|:---:|:---:|
| **Logistic Regression (Unweighted)** | 97.09% | 0.0000 | 0.0000 | 0.4926 | 0.1398 |
| **Logistic Regression (Class-Weighted)** | 97.09% | 0.0000 | 0.0000 | 0.4926 | 0.1422 |
| **Logistic Regression (Oversampled)** | 97.09% | 0.0000 | 0.0000 | 0.4926 | 0.1192 |
| **Deterministic Rules Baseline** | **84.85%** | **0.1013** | **0.5333** | **0.5434** | **0.6006** |

---

## 5. Critical Research Insights & Limitations

1. **The Class Imbalance & Generalization Paradox:**
   - On the in-distribution validation split (2014–2016 ERA5 weather + NASA events), all ML models scored $>99\%$ Macro-F1 and $1.00$ PR-AUC.
   - However, on the **prospective holdout set (2022–2026)**, the uncalibrated ML models collapsed (Recall = 0.0), whereas the **deterministic rules baseline captured 53.33% of field disruptions with 0.6006 PR-AUC**.
   - This empirically demonstrates domain shift between satellite ERA5 reanalysis and ground-level weather stations, as well as spatial density differences between regional NASA events and corridor-specific road disruptions.

2. **IEEE Paper Contribution:**
   - These experiments provide clear empirical justification for why NER-ResQ maintains the **deterministic mathematical formulation** ($R_{\text{route}} = 0.7 R_{\text{weighted}} + 0.3 R_{\text{max}}$) for production safety-critical logistics routing, positioning the ML model honestly as an offline empirical research benchmark.
