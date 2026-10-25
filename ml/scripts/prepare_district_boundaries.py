from pathlib import Path

import geopandas as gpd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "raw"
    / "boundaries"
    / "district_nwic.GeoJSON"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "boundaries"
)

OUTPUT_FILE = OUTPUT_DIR / "ner_district_boundaries.geojson"


# ============================================================
# NORTHEAST REGION STATES
# ============================================================

NER_STATES = [
    "Arunachal Pradesh",
    "Assam",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Sikkim",
    "Tripura",
]

# The source file spells this state "Arunanchal Pradesh".
STATE_NAME_ALIASES = {
    "Arunanchal Pradesh": "Arunachal Pradesh",
}

# Expected feature counts based on the source inspection.
EXPECTED_STATE_COUNTS = {
    "Arunachal Pradesh": 25,
    "Assam": 33,
    "Manipur": 16,
    "Meghalaya": 11,
    "Mizoram": 8,
    "Nagaland": 11,
    "Sikkim": 4,
    "Tripura": 8,
}


# ============================================================
# MAIN PROCESSING FUNCTION
# ============================================================

def main():
    print("=" * 65)
    print("NORTHEAST INDIA DISTRICT BOUNDARY PREPARATION")
    print("=" * 65)

    # --------------------------------------------------------
    # 1. Check input file
    # --------------------------------------------------------

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"\nInput boundary file not found:\n{INPUT_FILE}"
        )

    print(f"\nInput file:\n{INPUT_FILE}")

    # --------------------------------------------------------
    # 2. Read source dataset
    # --------------------------------------------------------

    print("\nReading district boundary dataset...")

    gdf = gpd.read_file(INPUT_FILE)

    print(f"Total source features: {len(gdf)}")
    print(f"Source CRS: {gdf.crs}")

    print("\nSource columns:")
    print(list(gdf.columns))

    # --------------------------------------------------------
    # 3. Validate required columns
    # --------------------------------------------------------

    required_columns = {
        "state_name",
        "district",
        "geometry",
    }

    missing_columns = required_columns - set(gdf.columns)

    if missing_columns:
        raise ValueError(
            "Required columns are missing: "
            f"{sorted(missing_columns)}"
        )

    if gdf.crs is None:
        raise ValueError(
            "The source dataset has no CRS. "
            "Verify its coordinate reference system before proceeding."
        )

    # --------------------------------------------------------
    # 4. Inspect source state names
    # --------------------------------------------------------

    print("\nState counts in source dataset:")

    print(
        gdf["state_name"]
        .value_counts(dropna=False)
        .to_string()
    )

    # --------------------------------------------------------
    # 5. Normalize known state-name variation
    # --------------------------------------------------------

    print("\nNormalizing known state-name variations...")

    gdf["state_name"] = (
        gdf["state_name"]
        .astype("string")
        .str.strip()
        .replace(STATE_NAME_ALIASES)
    )

    print("Applied state-name aliases:")
    print(STATE_NAME_ALIASES)

    # --------------------------------------------------------
    # 6. Filter Northeast Region
    # --------------------------------------------------------

    ner = gdf[
        gdf["state_name"].isin(NER_STATES)
    ].copy()

    print(f"\nNER features selected: {len(ner)}")

    # --------------------------------------------------------
    # 7. Verify all eight states are present
    # --------------------------------------------------------

    found_states = set(
        ner["state_name"].dropna().unique()
    )

    missing_states = set(NER_STATES) - found_states

    if missing_states:
        raise ValueError(
            "The following NER states were not found: "
            f"{sorted(missing_states)}"
        )

    print("\nAll eight Northeast states are present.")

    # --------------------------------------------------------
    # 8. Validate expected feature counts
    # --------------------------------------------------------

    actual_state_counts = (
        ner.groupby("state_name")
        .size()
        .to_dict()
    )

    print("\nDistrict feature counts by state:")
    print(
        ner.groupby("state_name")
        .size()
        .to_string()
    )

    count_errors = []

    for state, expected_count in EXPECTED_STATE_COUNTS.items():
        actual_count = actual_state_counts.get(state, 0)

        if actual_count != expected_count:
            count_errors.append(
                f"{state}: expected {expected_count}, "
                f"found {actual_count}"
            )

    if count_errors:
        print("\nWARNING: Feature counts differ from expectations.")

        for error in count_errors:
            print(f"  - {error}")

        raise ValueError(
            "Feature-count validation failed. "
            "Investigate the source before saving."
        )

    expected_total = sum(EXPECTED_STATE_COUNTS.values())

    if len(ner) != expected_total:
        raise ValueError(
            f"Expected {expected_total} features, "
            f"but found {len(ner)}."
        )

    print(f"\nFeature-count validation passed: {expected_total}")

    # --------------------------------------------------------
    # 9. Check geometry types
    # --------------------------------------------------------

    print("\nGeometry types:")
    print(
        ner.geom_type
        .value_counts(dropna=False)
        .to_string()
    )

    # --------------------------------------------------------
    # 10. Check missing and empty attributes/geometries
    # --------------------------------------------------------

    missing_districts = int(
        ner["district"].isna().sum()
    )

    missing_geometries = int(
        ner.geometry.isna().sum()
    )

    empty_geometries = int(
        ner.geometry.is_empty.sum()
    )

    print("\nBasic data-quality checks:")
    print(f"Missing district names: {missing_districts}")
    print(f"Missing geometries: {missing_geometries}")
    print(f"Empty geometries: {empty_geometries}")

    if missing_districts > 0:
        print("\nDistrict records with missing names:")
        print(
            ner.loc[
                ner["district"].isna(),
                ["state_name", "district"],
            ].to_string(index=False)
        )

    # --------------------------------------------------------
    # 11. Check duplicate state-district pairs
    # --------------------------------------------------------

    duplicate_mask = ner.duplicated(
        subset=["state_name", "district"],
        keep=False,
    )

    duplicate_count = int(duplicate_mask.sum())

    print(
        "Rows involved in duplicate state-district pairs: "
        f"{duplicate_count}"
    )

    if duplicate_count > 0:
        print("\nDuplicate district records:")
        print(
            ner.loc[
                duplicate_mask,
                ["state_name", "district", "dtcode"],
            ].sort_values(
                ["state_name", "district"]
            ).to_string(index=False)
        )

   # --------------------------------------------------------
    # --------------------------------------------------------
    # 12. Repair and validate invalid geometries
    # --------------------------------------------------------

    from shapely import make_valid
    from shapely.validation import explain_validity

    invalid_mask = ~ner.geometry.is_valid
    invalid_count = int(invalid_mask.sum())

    print(f"\nInvalid geometries before repair: {invalid_count}")

    if invalid_count > 0:
        print("\nRepairing invalid geometries...")

        for idx in ner.index[invalid_mask]:
            row = ner.loc[idx]
            original_geometry = row.geometry

            print(
                f"\nDistrict: {row['district']}, "
                f"State: {row['state_name']}"
            )
            print(
                "Original issue:",
                explain_validity(original_geometry),
            )

            # Repair the geometry in memory.
            repaired_geometry = make_valid(original_geometry)

            # Validate the repair before applying it.
            if repaired_geometry.is_empty:
                raise ValueError(
                    f"Repair produced an empty geometry for "
                    f"{row['state_name']} / {row['district']}."
                )

            if not repaired_geometry.is_valid:
                raise ValueError(
                    f"Geometry repair failed for "
                    f"{row['state_name']} / {row['district']}."
                )

            if repaired_geometry.geom_type not in (
                "Polygon",
                "MultiPolygon",
            ):
                raise ValueError(
                    f"Unexpected geometry type "
                    f"{repaired_geometry.geom_type} for "
                    f"{row['state_name']} / {row['district']}."
                )

            original_area = original_geometry.area
            repaired_area = repaired_geometry.area

            if original_area > 0:
                area_difference_pct = (
                    abs(repaired_area - original_area)
                    / original_area
                    * 100
                )
            else:
                area_difference_pct = float("inf")

            print("Original geometry:", original_geometry.geom_type)
            print("Repaired geometry:", repaired_geometry.geom_type)
            print(f"Original area: {original_area:.6f}")
            print(f"Repaired area: {repaired_area:.6f}")
            print(
                f"Area difference: {area_difference_pct:.12g}%"
            )

            # Replace only the invalid geometry.
            ner.at[idx, "geometry"] = repaired_geometry

    # Recheck the complete dataset after repair.
    remaining_invalid = int(
        (~ner.geometry.is_valid).sum()
    )

    remaining_empty = int(
        ner.geometry.is_empty.sum()
    )

    print(
        f"\nInvalid geometries after repair: {remaining_invalid}"
    )
    print(f"Empty geometries after repair: {remaining_empty}")

    if remaining_invalid > 0:
        raise ValueError(
            "Invalid geometries remain after repair. "
            "The output will not be saved."
        )

    if remaining_empty > 0:
        raise ValueError(
            "Empty geometries remain after repair. "
            "The output will not be saved."
        )
    # --------------------------------------------------------
    # 13. Stop if critical quality checks fail
    # --------------------------------------------------------

    critical_errors = []

    if missing_districts:
        critical_errors.append("Missing district names")

    if missing_geometries:
        critical_errors.append("Missing geometries")

    if empty_geometries:
        critical_errors.append("Empty geometries")

    if duplicate_count:
        critical_errors.append("Duplicate state-district pairs")

    if remaining_invalid:
         critical_errors.append("Invalid geometries remain after repair")

    if critical_errors:
        print("\n" + "=" * 65)
        print("VALIDATION FAILED")
        print("=" * 65)

        for error in critical_errors:
            print(f"- {error}")

        print(
            "\nNo output was written by this run. "
            "Investigate the reported issues before proceeding."
        )

        raise ValueError(
            "District boundary quality checks failed."
        )

    # --------------------------------------------------------
    # 14. Save filtered dataset
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\nSaving validated boundaries...")

    ner.to_file(
        OUTPUT_FILE,
        driver="GeoJSON",
    )

    # --------------------------------------------------------
    # 15. Final summary
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print("BOUNDARY PREPARATION COMPLETED")
    print("=" * 65)

    print(f"Source features: {len(gdf)}")
    print(f"NER features saved: {len(ner)}")
    print(f"States included: {len(found_states)}")
    print(f"Output CRS: {ner.crs}")
    print(f"Output file:\n{OUTPUT_FILE}")

    print("\nFinal feature counts:")
    print(
        ner.groupby("state_name")
        .size()
        .to_string()
    )

    print("\nAll configured quality checks passed.")


if __name__ == "__main__":
    main()