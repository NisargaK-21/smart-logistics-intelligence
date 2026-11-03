"""Dataset Audit and Machine Learning Feasibility Evaluation Script.

Inspects all available datasets across `ml/data/`, assesses label availability,
evaluates statistical feasibility for supervised model training, and outputs a
structured provenance and feasibility report.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ML_DATA = ROOT / "ml" / "data"
REPORT_OUTPUT = ML_DATA / "processed" / "dataset_feasibility_report.json"


def audit_datasets() -> dict:
    audit = {
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "datasets": {},
        "feasibility_assessment": {},
    }

    # 1. GSI Landslides
    gsi_path = ML_DATA / "final" / "historical" / "gsi_landslides_ner_validated.csv"
    if gsi_path.exists():
        df_gsi = pd.read_csv(gsi_path)
        valid_coords = int(df_gsi["coordinate_valid"].sum()) if "coordinate_valid" in df_gsi.columns else len(df_gsi)
        has_dates = int(df_gsi["history"].dropna().count()) if "history" in df_gsi.columns else 0
        audit["datasets"]["gsi_landslides"] = {
            "path": str(gsi_path.relative_to(ROOT)),
            "total_records": len(df_gsi),
            "columns": list(df_gsi.columns),
            "valid_coordinates": valid_coords,
            "records_with_date_or_year": has_dates,
            "has_negative_labels": False,
            "provenance": "Geological Survey of India (GSI) validated landslide inventory",
            "spatial_coverage": sorted(df_gsi["state"].dropna().unique().tolist()) if "state" in df_gsi.columns else [],
        }

    # 2. CWC Floods
    cwc_path = ML_DATA / "final" / "historical" / "cwc_floods_ner_clean.csv"
    if cwc_path.exists():
        df_cwc = pd.read_csv(cwc_path)
        audit["datasets"]["cwc_floods"] = {
            "path": str(cwc_path.relative_to(ROOT)),
            "total_records": len(df_cwc),
            "columns": list(df_cwc.columns),
            "granularity": "district_level_aggregate",
            "study_period": "1986-2022",
            "has_negative_labels": False,
            "provenance": "Central Water Commission (CWC) flood assessment report",
        }

    # 3. Weather Stations & Records
    loc_path = ML_DATA / "processed" / "weather_locations.csv"
    if loc_path.exists():
        df_loc = pd.read_csv(loc_path)
        audit["datasets"]["weather_locations"] = {
            "path": str(loc_path.relative_to(ROOT)),
            "station_count": len(df_loc),
            "station_ids": df_loc["location_id"].tolist() if "location_id" in df_loc.columns else [],
            "provenance": "Open-Meteo ERA5 / Historical Archive coordinate grid",
        }

    weather_proc_path = ML_DATA / "processed" / "weather_processed.csv"
    if weather_proc_path.exists():
        # Read header only for efficiency
        df_w_sample = pd.read_csv(weather_proc_path, nrows=5)
        audit["datasets"]["historical_weather"] = {
            "path": str(weather_proc_path.relative_to(ROOT)),
            "period": "2022-01-01 to 2025-12-31 (hourly)",
            "columns": list(df_w_sample.columns),
            "rolling_features_available": True,
            "provenance": "Open-Meteo API (hourly)",
        }

    weather_features_path = ML_DATA / "processed" / "weather_features.csv"
    weather_feature_columns = []
    if weather_features_path.exists():
        weather_feature_columns = list(pd.read_csv(weather_features_path, nrows=0).columns)
        audit["datasets"]["historical_weather_features"] = {
            "path": str(weather_features_path.relative_to(ROOT)),
            "feature_columns": weather_feature_columns,
            "provenance": (
                "Open-Meteo historical weather with rolling rainfall aggregates; "
                "features only, not disruption labels"
            ),
        }

    recent_weather_path = ML_DATA / "processed" / "weather_recent_oct2026_features.csv"
    if recent_weather_path.exists():
        df_rw = pd.read_csv(recent_weather_path)
        audit["datasets"]["recent_weather"] = {
            "path": str(recent_weather_path.relative_to(ROOT)),
            "period": "2026-10-01 to 2026-10-03",
            "total_rows": len(df_rw),
            "provenance": "Open-Meteo recent archive API",
        }

    # 4. Field Reports
    field_reports_path = ML_DATA / "raw" / "field_reports" / "field_reports.csv"
    if field_reports_path.exists():
        df_fr = pd.read_csv(field_reports_path)
        audit["datasets"]["field_reports"] = {
            "path": str(field_reports_path.relative_to(ROOT)),
            "total_records": len(df_fr),
            "columns": list(df_fr.columns),
            "incident_types": df_fr["incident_type"].value_counts().to_dict() if "incident_type" in df_fr.columns else {},
            "severity_counts": df_fr["severity"].value_counts().to_dict() if "severity" in df_fr.columns else {},
            "date_range": [df_fr["timestamp"].min(), df_fr["timestamp"].max()] if "timestamp" in df_fr.columns else [],
            "provenance": "On-ground crowd/operator incident reports (sample test set)",
        }

    # Feasibility evaluation
    n_field_reports = audit["datasets"].get("field_reports", {}).get("total_records", 0)
    has_segment_labels = False
    production_model_path = ML_DATA.parent / "models" / "risk_model.joblib"
    experimental_model_path = ML_DATA.parent / "models" / "weather_risk_logistic_regression.joblib"

    synthetic_features_available = {
        "precipitation_mm",
        "precipitation_sum_3h_mm",
        "precipitation_sum_6h_mm",
        "precipitation_sum_24h_mm",
        "wind_speed_kmh",
    }.issubset(weather_feature_columns)

    audit["feasibility_assessment"] = {
        "supervised_learning_viable": False,
        "real_world_supervised_learning_viable": False,
        "synthetic_pipeline_demonstration_feasible": synthetic_features_available,
        "synthetic_labels_permitted_when_disclosed": True,
        "sample_size_field_reports": n_field_reports,
        "negative_controls_available": False,
        "segment_level_ground_truth_labels_available": has_segment_labels,
        "synthetic_weather_feature_columns_available": weather_feature_columns,
        "data_leakage_risk": (
            "Synthetic evaluation labels are generated from the same weather features "
            "used by the model; this measures rule imitation, not disruption prediction."
        ),
        "justification": (
            f"The {n_field_reports} incident reports are too few and lack verified non-incident traversals "
            "for real-world supervised disruption modeling. Historical landslide points and district-level flood "
            "aggregates are not synchronized segment-time outcomes. The original project plan permits explicitly "
            "disclosed synthetic labels for a reproducible pipeline demonstration. Weather features are available "
            f"for such a demonstration: {synthetic_features_available}. Any classifier trained on labels generated "
            "by the deterministic weather rules demonstrates rule imitation only; it is not evidence of real-world "
            "predictive accuracy. The deterministic baseline remains the production-safe default."
        ),
        "selected_architecture": (
            "Deterministic production baseline with an optional, explicitly synthetic "
            "weather-classification demonstration and inactive model adapter"
        ),
        "model_adapter_configured": False,
        "production_model_configured": False,
        "model_artifact_present": production_model_path.exists(),
        "experimental_weather_model_artifact_present": experimental_model_path.exists(),
        "experimental_weather_model_artifact_path": (
            str(experimental_model_path.relative_to(ROOT))
            if experimental_model_path.exists()
            else None
        ),
        "fallback_status": "Active (all requests safely resolve to baseline)",
    }

    REPORT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)

    return audit


if __name__ == "__main__":
    result = audit_datasets()
    print("Dataset audit complete.")
    print("Supervised ML Viable:", result["feasibility_assessment"]["supervised_learning_viable"])
    print("Reason:", result["feasibility_assessment"]["justification"])
    print("Report written to:", REPORT_OUTPUT)
