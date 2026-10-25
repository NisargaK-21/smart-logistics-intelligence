
from pathlib import Path

import geopandas as gpd
import pandas as pd


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_CSV = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "final"
    / "historical"
    / "gsi_landslides_ner_validated.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "landslides"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_GEOJSON = OUTPUT_DIR / "ner_gsi_landslide_points.geojson"
OUTPUT_REVIEW_CSV = OUTPUT_DIR / "gsi_landslides_coordinate_review.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "gsi_landslide_preparation_summary.txt"


def main():
    df = pd.read_csv(INPUT_CSV)

    required_columns = {
        "slide_id",
        "state",
        "district",
        "latitude",
        "longitude",
        "coordinate_valid",
        "coordinate_in_ner_range",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    # Preserve the original coordinate values and validation flags.
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    coordinate_valid = (
        df["coordinate_valid"].astype("boolean").fillna(False)
    )
    in_ner_range = (
        df["coordinate_in_ner_range"].astype("boolean").fillna(False)
    )

    # Coordinate eligibility is determined by existing validation flags
    # and the presence of both coordinate values.
    has_coordinates = (
        df["latitude"].notna()
        & df["longitude"].notna()
    )

    eligible = coordinate_valid & in_ner_range & has_coordinates

    # Retain all non-eligible records for investigation.
    review = df.loc[~eligible].copy()

    def review_reason(row):
        reasons = []

        if pd.isna(row["latitude"]) or pd.isna(row["longitude"]):
            reasons.append("missing_coordinate")

        if not bool(row["coordinate_valid"]):
            reasons.append("coordinate_invalid")

        if not bool(row["coordinate_in_ner_range"]):
            reasons.append("outside_ner_range")

        return ";".join(reasons) if reasons else "review_required"

    review["review_reason"] = review.apply(review_reason, axis=1)
    review.to_csv(OUTPUT_REVIEW_CSV, index=False)

    # Build point geometries only for eligible records.
    valid_df = df.loc[eligible].copy()

    points = gpd.GeoDataFrame(
        valid_df,
        geometry=gpd.points_from_xy(
            valid_df["longitude"],
            valid_df["latitude"],
        ),
        crs="EPSG:4326",
    )

    # Basic geometry checks.
    invalid_geometry_count = int((~points.geometry.is_valid).sum())
    empty_geometry_count = int(points.geometry.is_empty.sum())

    if invalid_geometry_count or empty_geometry_count:
        raise ValueError(
            "Generated point geometries failed validation: "
            f"{invalid_geometry_count} invalid, "
            f"{empty_geometry_count} empty."
        )

    points.to_file(OUTPUT_GEOJSON, driver="GeoJSON")

    state_counts = (
        points.groupby("state")
        .size()
        .sort_values(ascending=False)
    )

    summary_lines = [
        "GSI LANDSLIDE POINT PREPARATION SUMMARY",
        "=" * 42,
        f"Input records: {len(df)}",
        f"Eligible spatial records: {len(points)}",
        f"Records requiring coordinate review: {len(review)}",
        f"Missing latitude: {int(df['latitude'].isna().sum())}",
        f"Missing longitude: {int(df['longitude'].isna().sum())}",
        f"Missing district: {int(df['district'].isna().sum())}",
        f"Invalid output geometries: {invalid_geometry_count}",
        f"Empty output geometries: {empty_geometry_count}",
        "Output CRS: EPSG:4326",
        "",
        "Eligible records by state:",
    ]

    summary_lines.extend(
        f"  {state}: {count}"
        for state, count in state_counts.items()
    )

    summary_lines.extend(
        [
            "",
            f"GeoJSON: {OUTPUT_GEOJSON}",
            f"Review CSV: {OUTPUT_REVIEW_CSV}",
        ]
    )

    OUTPUT_SUMMARY.write_text(
        "\n".join(summary_lines),
        encoding="utf-8",
    )

    print("\n".join(summary_lines))


if __name__ == "__main__":
    main()
