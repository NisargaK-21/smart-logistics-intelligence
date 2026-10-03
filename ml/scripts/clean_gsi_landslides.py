from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "historical"
    / "gsi_landslides_extracted.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "final"
    / "historical"
    / "gsi_landslides_ner_clean.csv"
)

QUALITY_REPORT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "historical"
    / "gsi_landslides_quality_report.txt"
)


NER_STATES = {
    "assam": "Assam",
    "arunachal pradesh": "Arunachal Pradesh",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "sikkim": "Sikkim",
    "tripura": "Tripura",
}


def clean_text(value):
    if pd.isna(value):
        return pd.NA

    value = str(value)
    value = value.replace("\n", " ")
    value = " ".join(value.split())

    return value if value else pd.NA


def normalize_state(value):
    if pd.isna(value):
        return pd.NA

    state = str(value).strip().lower()

    # Fix known formatting variants found in the GSI extraction.
    state = state.lstrip("-").strip()

    return NER_STATES.get(state, value)


def main():
    print("Loading extracted dataset...")
    df = pd.read_csv(INPUT_PATH)

    original_rows = len(df)

    # Clean text fields.
    text_columns = [
        "slide_id",
        "state",
        "district",
        "slide_name",
        "road_location",
        "material",
        "movement_type",
        "history",
    ]

    for column in text_columns:
        df[column] = df[column].apply(clean_text)

    # Normalize state names.
    df["state"] = df["state"].apply(normalize_state)

    # Convert numeric fields.
    df["sl_no"] = pd.to_numeric(df["sl_no"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Check coordinate validity.
    invalid_latitude = (
        df["latitude"].isna()
        | ~df["latitude"].between(-90, 90)
    )

    invalid_longitude = (
        df["longitude"].isna()
        | ~df["longitude"].between(-180, 180)
    )

    invalid_coordinates = invalid_latitude | invalid_longitude

    # Keep only Northeast Region states.
    ner_df = df[df["state"].isin(NER_STATES.values())].copy()

    # Remove duplicate slide IDs within NER.
    duplicate_ids = ner_df["slide_id"].duplicated(keep=False)
    duplicate_count = int(duplicate_ids.sum())

    ner_df = ner_df.drop_duplicates(
        subset=["slide_id"],
        keep="first",
    )

    # Sort for easier inspection.
    ner_df = ner_df.sort_values(
        by=["state", "district", "slide_id"],
        na_position="last",
    ).reset_index(drop=True)

    # Create output directory.
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Save final NER dataset.
    ner_df.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # Build quality report.
    report = []

    report.append("GSI Landslide Historical Dataset - Quality Report")
    report.append("=" * 60)
    report.append("")
    report.append(f"Original extracted rows: {original_rows}")
    report.append(f"NER rows before duplicate removal: {len(ner_df) + duplicate_count}")
    report.append(f"Duplicate slide-ID rows detected: {duplicate_count}")
    report.append(f"Final NER rows: {len(ner_df)}")
    report.append("")

    report.append("NER records by state:")
    report.append(str(ner_df["state"].value_counts()))
    report.append("")

    report.append("Missing values in final NER dataset:")
    report.append(str(ner_df.isna().sum()))
    report.append("")

    report.append(
        f"Rows with invalid/missing coordinates in extracted dataset: "
        f"{int(invalid_coordinates.sum())}"
    )
    report.append("")

    report.append("Unique slide IDs in final NER dataset:")
    report.append(str(ner_df["slide_id"].nunique()))
    report.append("")

    QUALITY_REPORT_PATH.write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    print("\nCleaning complete.")
    print(f"Original rows: {original_rows}")
    print(f"Final NER rows: {len(ner_df)}")
    print(f"Duplicate slide-ID rows detected: {duplicate_count}")
    print(
        f"Invalid/missing coordinates in extracted dataset: "
        f"{int(invalid_coordinates.sum())}"
    )

    print("\nRecords by NER state:")
    print(ner_df["state"].value_counts())

    print("\nFinal dataset:")
    print(OUTPUT_PATH)

    print("\nQuality report:")
    print(QUALITY_REPORT_PATH)


if __name__ == "__main__":
    main()