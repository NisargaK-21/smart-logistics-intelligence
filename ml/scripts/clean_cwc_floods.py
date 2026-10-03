from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "historical"
    / "cwc_floods_extracted.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "final"
    / "historical"
    / "cwc_floods_ner_clean.csv"
)


NER_STATES = {
    "Arunachal Pradesh",
    "Assam",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Sikkim",
    "Tripura",
}


print(f"Reading: {INPUT_PATH}")

df = pd.read_csv(INPUT_PATH)

original_count = len(df)


# --------------------------------------------------
# Clean text fields
# --------------------------------------------------

text_columns = [
    "disaster_type",
    "state",
    "district",
    "study_period",
    "source",
    "source_file",
]

for column in text_columns:
    df[column] = (
        df[column]
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )


# --------------------------------------------------
# Numeric conversion
# --------------------------------------------------

df["flood_affected_area_ha"] = pd.to_numeric(
    df["flood_affected_area_ha"],
    errors="coerce",
)

df["source_page"] = pd.to_numeric(
    df["source_page"],
    errors="coerce",
).astype("Int64")


# --------------------------------------------------
# Filter NER states
# --------------------------------------------------

df = df[df["state"].isin(NER_STATES)].copy()


# --------------------------------------------------
# Validate flood area
# --------------------------------------------------

invalid_area = (
    df["flood_affected_area_ha"].isna()
    | (df["flood_affected_area_ha"] < 0)
)

print(
    f"Invalid flood-area records: "
    f"{invalid_area.sum()}"
)

df = df[~invalid_area].copy()


# --------------------------------------------------
# Remove duplicates
# --------------------------------------------------

duplicates = df.duplicated(
    subset=["state", "district"],
    keep="first",
)

print(
    f"Duplicate state+district records removed: "
    f"{duplicates.sum()}"
)

df = df[~duplicates].copy()


# --------------------------------------------------
# Sort
# --------------------------------------------------

df = df.sort_values(
    ["state", "district"]
).reset_index(drop=True)


# --------------------------------------------------
# Final column order
# --------------------------------------------------

df = df[
    [
        "disaster_type",
        "state",
        "district",
        "flood_affected_area_ha",
        "study_period",
        "source",
        "source_file",
        "source_page",
    ]
]


# --------------------------------------------------
# Save
# --------------------------------------------------

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_csv(
    OUTPUT_PATH,
    index=False,
)


# --------------------------------------------------
# Report
# --------------------------------------------------

print("\nCleaning complete.")
print(f"Original records: {original_count}")
print(f"Final records: {len(df)}")

print("\nRecords by state:")
print(
    df["state"]
    .value_counts()
    .sort_index()
    .to_string()
)

print("\nMissing values:")
print(df.isna().sum().to_string())

print("\nDuplicate state+district:")
print(
    df.duplicated(
        ["state", "district"]
    ).sum()
)

print(f"\nOutput:")
print(OUTPUT_PATH)