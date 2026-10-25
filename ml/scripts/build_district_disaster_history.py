
from pathlib import Path

import geopandas as gpd
import pandas as pd


# --------------------------------------------------
# Paths
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

LANDSLIDES_PATH = (
    ROOT / "ml" / "data" / "processed" / "landslides"
    / "ner_gsi_landslide_points.geojson"
)

FLOODS_PATH = (
    ROOT / "ml" / "data" / "processed" / "floods"
    / "ner_district_floods.geojson"
)

OUTPUT_DIR = ROOT / "ml" / "data" / "processed" / "disaster"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_GEOJSON = OUTPUT_DIR / "ner_district_disaster_history.geojson"
OUTPUT_CSV = OUTPUT_DIR / "ner_district_disaster_history.csv"
UNMATCHED_CSV = OUTPUT_DIR / "unmatched_landslide_points.csv"
SUMMARY_TXT = OUTPUT_DIR / "disaster_history_summary.txt"


def normalize_name(value):
    """Normalize district/state names for diagnostic comparisons."""
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().upper().split())


def main():
    print("Loading datasets...")

    landslides = gpd.read_file(LANDSLIDES_PATH)
    districts = gpd.read_file(FLOODS_PATH)

    if landslides.crs is None:
        raise ValueError("Landslide dataset has no CRS.")

    if districts.crs is None:
        raise ValueError("District flood dataset has no CRS.")

    required_landslide_fields = {"slide_id", "state", "district"}
    missing = required_landslide_fields - set(landslides.columns)

    if missing:
        raise ValueError(
            f"Landslide dataset is missing fields: {sorted(missing)}"
        )

    required_district_fields = {
        "state_name",
        "district",
        "flood_affected_area_ha",
    }
    missing = required_district_fields - set(districts.columns)

    if missing:
        raise ValueError(
            f"District flood dataset is missing fields: {sorted(missing)}"
        )

    if landslides["slide_id"].duplicated().any():
        raise ValueError("Duplicate slide IDs detected.")

    if districts.duplicated(subset=["state_name", "district"]).any():
        raise ValueError("Duplicate state-district pairs in district layer.")

    # Use the district polygons as the base layer.
    # Project points into the polygon layer's CRS for the spatial join.
    landslides_projected = landslides.to_crs(districts.crs)

    # Count points that intersect each district polygon.
    joined = gpd.sjoin(
        landslides_projected[["slide_id", "state", "district", "geometry"]],
        districts[["state_name", "district", "geometry"]],
        how="left",
        predicate="within",
    )

    matched = joined.loc[joined["index_right"].notna()].copy()
    unmatched = joined.loc[joined["index_right"].isna()].copy()

    # Keep unmatched source records for review.
    if not unmatched.empty:
        unmatched_source = landslides.loc[unmatched.index].copy()
        unmatched_source.to_csv(UNMATCHED_CSV, index=False)
    else:
        pd.DataFrame(
            columns=list(landslides.columns)
        ).to_csv(UNMATCHED_CSV, index=False)

    # Count only points assigned to a district.
    counts = (
        matched.groupby("index_right")["slide_id"]
        .nunique()
        .rename("landslide_count")
    )

    # Add counts to the original district layer without changing its geometry.
    result = districts.copy()
    result["landslide_count"] = (
        result.index.to_series().map(counts).fillna(0).astype(int).values
    )

    result["landslide_data_source"] = (
        "GSI validated NER landslide records"
    )
    result["flood_data_source"] = (
        "CWC district-level flood-affected area, 1986-2022"
    )

    # Sanity checks
    if len(result) != len(districts):
        raise ValueError("Output district count changed unexpectedly.")

    if result["flood_affected_area_ha"].isna().any():
        raise ValueError("Missing flood values found in output.")

    if (result["landslide_count"] < 0).any():
        raise ValueError("Negative landslide counts detected.")

    # Export the district layer and a non-spatial table.
    result.to_file(OUTPUT_GEOJSON, driver="GeoJSON")

    result.drop(columns="geometry").to_csv(OUTPUT_CSV, index=False)

    total_landslides = int(result["landslide_count"].sum())
    assigned_points = len(matched)
    unmatched_points = len(unmatched)

    summary = [
        "DISTRICT-LEVEL HISTORICAL DISASTER SUMMARY",
        "=" * 46,
        f"Input landslide points: {len(landslides)}",
        f"Points assigned to districts: {assigned_points}",
        f"Points unmatched to district polygons: {unmatched_points}",
        f"District polygons: {len(districts)}",
        f"Districts with at least one landslide: "
        f"{int((result['landslide_count'] > 0).sum())}",
        f"Total assigned landslide records: {total_landslides}",
        f"Total CWC flood-affected area (ha): "
        f"{result['flood_affected_area_ha'].sum():.2f}",
        f"Output CRS: {result.crs}",
        "",
        "Top 10 districts by landslide count:",
    ]

    top_districts = result.sort_values(
        "landslide_count", ascending=False
    ).head(10)

    for _, row in top_districts.iterrows():
        summary.append(
            f"  {row['state_name']} - {row['district']}: "
            f"{row['landslide_count']} landslides; "
            f"{row['flood_affected_area_ha']:.2f} ha flood-affected area"
        )

    summary.extend(
        [
            "",
            f"GeoJSON output: {OUTPUT_GEOJSON}",
            f"CSV output: {OUTPUT_CSV}",
            f"Unmatched points: {UNMATCHED_CSV}",
        ]
    )

    SUMMARY_TXT.write_text("\n".join(summary), encoding="utf-8")

    print("\n".join(summary))


if __name__ == "__main__":
    main()
