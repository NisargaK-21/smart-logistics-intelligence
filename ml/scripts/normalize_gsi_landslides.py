from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "final"
    / "historical"
    / "gsi_landslides_ner_clean.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "final"
    / "historical"
    / "gsi_landslides_ner_normalized.csv"
)


def normalize_movement(value):
    if pd.isna(value):
        return pd.NA

    text = str(value).strip().lower()

    if text in {"nil", "n/a", "na"}:
        return pd.NA

    # Complex / multiple movement descriptions.
    if (
        "complex" in text
        or "multiple type" in text
        or ("slide" in text and "flow" in text and "subsidence" in text)
    ):
        return "Complex"

    # Combined movement descriptions.
    if "topple" in text and ("fall" in text or "slide" in text):
        return "Complex"

    if "slide" in text and ("flow" in text or "subsidence" in text):
        return "Complex"

    if "fall" in text and "slide" in text:
        return "Complex"

    # Individual categories.
    if "subsidence" in text:
        return "Subsidence"

    if "flow" in text:
        return "Flow"

    if "topple" in text:
        return "Topple"

    if "fall" in text:
        return "Fall"

    if "creep" in text:
        return "Creep"

    if "spread" in text:
        return "Spread"

    if "wedge failure" in text or "planar" in text:
        return "Failure"

    if "translational" in text:
        return "Slide"

    if "slide" in text or "sldies" in text or "silde" in text:
        return "Slide"

    return "Other"


def normalize_material(value):
    if pd.isna(value):
        return pd.NA

    text = str(value).strip().lower()

    if not text:
        return pd.NA

    # Mixed rock/debris descriptions.
    if (
        ("rock" in text and "debris" in text)
        or "boulder" in text
    ):
        return "Rock + Debris"

    # Colluvium / regolith.
    if "colluvium" in text or "regolith" in text:
        return "Colluvium/Regolith"

    # Unconsolidated material.
    if "unconsolidated" in text:
        return "Mixed/Unconsolidated"

    # Earth / soil.
    if "soil" in text or "earth" in text:
        return "Earth/Soil"

    # Debris.
    if "debris" in text:
        return "Debris"

    # Rock.
    if "rock" in text or "shale" in text or "sandstone" in text:
        return "Rock"

    return "Other/Unknown"


def main():
    print("Loading cleaned GSI dataset...")

    df = pd.read_csv(INPUT_PATH)

    df["movement_category"] = df["movement_type"].apply(
        normalize_movement
    )

    df["material_category"] = df["material"].apply(
        normalize_material
    )

    # Put standardized columns next to their source columns.
    columns = list(df.columns)

    movement_index = columns.index("movement_type")
    columns.remove("movement_category")
    columns.insert(movement_index + 1, "movement_category")

    material_index = columns.index("material")
    columns.remove("material_category")
    columns.insert(material_index + 1, "material_category")

    df = df[columns]

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nNormalization complete.")

    print(f"Rows: {len(df)}")

    print("\nMovement categories:")
    print(df["movement_category"].value_counts(dropna=False))

    print("\nMaterial categories:")
    print(df["material_category"].value_counts(dropna=False))

    print("\nOutput:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()