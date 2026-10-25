
from pathlib import Path
import re
import sys

import geopandas as gpd
import pandas as pd


# ------------------------------------------------------------
# 1. File paths
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

BOUNDARY_FILE = (
    ROOT
    / "ml/data/processed/boundaries/ner_district_boundaries.geojson"
)

FLOOD_FILE = (
    ROOT
    / "ml/data/final/historical/cwc_floods_ner_clean.csv"
)

OUTPUT_DIR = ROOT / "ml/data/processed/floods"

OUTPUT_GEOJSON = OUTPUT_DIR / "ner_district_floods.geojson"
OUTPUT_CSV = OUTPUT_DIR / "cwc_flood_boundary_join_audit.csv"


# ------------------------------------------------------------
# 2. District-name normalization and explicit aliases
# ------------------------------------------------------------

def normalize_name(value):
    """Normalize a name for matching without changing source values."""
    value = str(value).strip().upper()
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


# Historical CWC district name -> current boundary district name.
# Original source names remain unchanged in the output.
DISTRICT_ALIASES = {
    ("ARUNACHAL PRADESH", "LEPA RADA"): "LEPARADA",
    ("ASSAM", "KAMRUP METROPOLITAN"): "KAMRUP METRO",
    ("ASSAM", "KAMRUP RURAL"): "KAMRUP",
    ("ASSAM", "MORIGAON"): "MARIGAON",
    ("ASSAM", "SOUTH SALMARA MANKACHAR"): "SOUTH SALMARA MANCACHAR",
    ("SIKKIM", "EAST SIKKIM"): "GANGTOK",
    ("SIKKIM", "NORTH SIKKIM"): "MANGAN",
    ("SIKKIM", "SOUTH SIKKIM"): "NAMCHI",
    ("SIKKIM", "WEST SIKKIM"): "GYALSHING",
}


def boundary_district_key(state, district):
    """Map historical CWC district names to boundary matching keys."""
    state_key = normalize_name(state)
    district_key = normalize_name(district)

    return DISTRICT_ALIASES.get(
        (state_key, district_key),
        district_key,
    )


# ------------------------------------------------------------
# 3. Main workflow
# ------------------------------------------------------------

def main():
    print("=" * 65)
    print("CWC FLOOD DATA — DISTRICT BOUNDARY JOIN")
    print("=" * 65)

    # Check input files.
    if not BOUNDARY_FILE.exists():
        raise FileNotFoundError(
            f"Boundary file not found:\n{BOUNDARY_FILE}"
        )

    if not FLOOD_FILE.exists():
        raise FileNotFoundError(
            f"Flood CSV not found:\n{FLOOD_FILE}"
        )

    # Load data.
    boundaries = gpd.read_file(BOUNDARY_FILE)
    floods = pd.read_csv(FLOOD_FILE)

    required_boundary_columns = {
        "state_name",
        "district",
        "geometry",
    }

    required_flood_columns = {
        "state",
        "district",
        "flood_affected_area_ha",
        "study_period",
        "source",
    }

    missing_boundary_columns = (
        required_boundary_columns - set(boundaries.columns)
    )
    missing_flood_columns = (
        required_flood_columns - set(floods.columns)
    )

    if missing_boundary_columns:
        raise ValueError(
            "Boundary dataset is missing columns: "
            f"{sorted(missing_boundary_columns)}"
        )

    if missing_flood_columns:
        raise ValueError(
            "Flood dataset is missing columns: "
            f"{sorted(missing_flood_columns)}"
        )

    print(f"Boundary features: {len(boundaries)}")
    print(f"Flood records: {len(floods)}")

    # Validate input geometry before processing.
    if boundaries.geometry.isna().any():
        raise ValueError("Boundary dataset contains missing geometries.")

    if boundaries.geometry.is_empty.any():
        raise ValueError("Boundary dataset contains empty geometries.")

    if (~boundaries.geometry.is_valid).any():
        raise ValueError("Boundary dataset contains invalid geometries.")

    if boundaries.crs is None:
        raise ValueError("Boundary dataset has no CRS defined.")

    # Validate flood measurements.
    floods["flood_affected_area_ha"] = pd.to_numeric(
        floods["flood_affected_area_ha"],
        errors="raise",
    )

    if floods["flood_affected_area_ha"].isna().any():
        raise ValueError("Flood dataset contains missing area values.")

    if (floods["flood_affected_area_ha"] < 0).any():
        raise ValueError("Flood dataset contains negative area values.")

    # --------------------------------------------------------
    # 4. Create normalized matching keys
    # --------------------------------------------------------

    boundaries["state_key"] = boundaries["state_name"].map(
        normalize_name
    )

    boundaries["district_key"] = boundaries["district"].map(
        normalize_name
    )

    floods["state_key"] = floods["state"].map(
        normalize_name
    )

    floods["district_key"] = floods.apply(
        lambda row: boundary_district_key(
            row["state"],
            row["district"],
        ),
        axis=1,
    )

    # --------------------------------------------------------
    # 5. Check duplicate matching keys
    # --------------------------------------------------------

    boundary_duplicates = boundaries.duplicated(
        subset=["state_key", "district_key"],
        keep=False,
    )

    flood_duplicates = floods.duplicated(
        subset=["state_key", "district_key"],
        keep=False,
    )

    if boundary_duplicates.any():
        print("\nDuplicate boundary join keys:")
        print(
            boundaries.loc[
                boundary_duplicates,
                ["state_name", "district"],
            ].to_string(index=False)
        )
        raise ValueError(
            "Boundary dataset contains duplicate state-district keys."
        )

    if flood_duplicates.any():
        print("\nDuplicate flood join keys after alias normalization:")
        print(
            floods.loc[
                flood_duplicates,
                ["state", "district"],
            ].to_string(index=False)
        )
        raise ValueError(
            "Flood dataset contains duplicate state-district keys."
        )

    # --------------------------------------------------------
    # 6. Outer join for a complete audit
    # --------------------------------------------------------

    boundary_audit = boundaries[
        [
            "state_name",
            "district",
            "state_key",
            "district_key",
        ]
    ].rename(
        columns={
            "state_name": "state_boundary",
            "district": "district_boundary",
        }
    )

    flood_audit = floods[
        [
            "state",
            "district",
            "state_key",
            "district_key",
        ]
    ].rename(
        columns={
            "state": "state_flood",
            "district": "district_flood",
        }
    )

    audit = flood_audit.merge(
        boundary_audit,
        on=["state_key", "district_key"],
        how="outer",
        indicator=True,
        validate="one_to_one",
    )

    matched = audit["_merge"].eq("both")
    flood_only = audit["_merge"].eq("left_only")
    boundary_only = audit["_merge"].eq("right_only")

    matched_count = int(matched.sum())
    flood_only_count = int(flood_only.sum())
    boundary_only_count = int(boundary_only.sum())

    print("\nJoin results:")
    print(f"Matched district pairs: {matched_count}")
    print(f"Flood records without boundaries: {flood_only_count}")
    print(f"Boundaries without flood records: {boundary_only_count}")

    # Save the audit even if some records do not match.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    audit.to_csv(OUTPUT_CSV, index=False)

    print(f"\nJoin audit saved to:\n{OUTPUT_CSV}")

    if flood_only.any():
        print("\nFlood records without matching boundaries:")
        print(
            audit.loc[
                flood_only,
                ["state_flood", "district_flood"],
            ].to_string(index=False)
        )

    if boundary_only.any():
        print("\nBoundaries without matching flood records:")
        print(
            audit.loc[
                boundary_only,
                ["state_boundary", "district_boundary"],
            ].to_string(index=False)
        )

    if flood_only_count or boundary_only_count:
        print(
            "\nJOIN INCOMPLETE. Review the audit CSV. "
            "No final flood GeoJSON was written."
        )
        sys.exit(1)


    # --------------------------------------------------------
    # 7. Join flood attributes to district geometries
    # --------------------------------------------------------

    # Preserve the original CWC district name before joining.
    flood_attributes = floods.drop(
        columns=["state_key", "district_key"]
    ).rename(
        columns={
            "state": "cwc_state",
            "district": "cwc_district",
        }
    )

    # Join using the normalized keys validated in Section 6.
    result = boundaries.merge(
        flood_attributes.drop(
            columns=["cwc_state", "cwc_district"]
        ).assign(
            state_key=floods["state_key"].values,
            district_key=floods["district_key"].values,
            cwc_state=floods["state"].values,
            cwc_district=floods["district"].values,
        ),
        on=["state_key", "district_key"],
        how="left",
        validate="one_to_one",
        suffixes=("_boundary", "_flood"),
    )

    # Verify the join succeeded for every district.
    if len(result) != len(boundaries):
        raise ValueError(
            "Output feature count does not match boundary feature count."
        )

    if result["flood_affected_area_ha"].isna().any():
        raise ValueError(
            "Some districts have no flood-area value. "
            "Final GeoJSON was not written."
        )

    if result.geometry.isna().any() or result.geometry.is_empty.any():
        raise ValueError(
            "Final output contains missing or empty geometries."
        )

    if (~result.geometry.is_valid).any():
        raise ValueError(
            "Final output contains invalid geometries."
        )

    # Remove temporary matching keys.
    result = result.drop(
        columns=["state_key", "district_key"]
    )

    # --------------------------------------------------------
    # 8. Save final spatial dataset
    # --------------------------------------------------------

    result.to_file(
        OUTPUT_GEOJSON,
        driver="GeoJSON",
    )

    print("\n" + "=" * 65)
    print("FLOOD-BOUNDARY JOIN COMPLETED")
    print("=" * 65)
    print(f"Output features: {len(result)}")
    print(f"States included: {result['state_name'].nunique()}")
    print(f"Output CRS: {result.crs}")
    print(f"GeoJSON saved to:\n{OUTPUT_GEOJSON}")
    print(f"Audit CSV saved to:\n{OUTPUT_CSV}")

    print(
        "\nData interpretation: flood_affected_area_ha is a "
        "district-level aggregate for the study period, not an "
        "individual flood-event location."
    )

    print(
        "Historical district names are retained in cwc_district; "
        "boundary names are retained in district."
    )


if __name__ == "__main__":
    main()
