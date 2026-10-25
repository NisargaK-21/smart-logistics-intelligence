from pathlib import Path

import geopandas as gpd
from shapely import make_valid
from shapely.validation import explain_validity


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "raw"
    / "boundaries"
    / "district_nwic.GeoJSON"
)

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

STATE_NAME_ALIASES = {
    "Arunanchal Pradesh": "Arunachal Pradesh",
}


def main():
    print("Reading source boundary dataset...")
    gdf = gpd.read_file(INPUT_FILE)

    # Normalize the known spelling variation.
    gdf["state_name"] = (
        gdf["state_name"]
        .astype("string")
        .str.strip()
        .replace(STATE_NAME_ALIASES)
    )

    ner = gdf[gdf["state_name"].isin(NER_STATES)].copy()

    # Locate Gomati in Tripura.
    target = ner[
        (ner["state_name"] == "Tripura")
        & (ner["district"].str.strip() == "Gomati")
    ]

    if len(target) != 1:
        raise ValueError(
            f"Expected exactly one Tripura/Gomati feature; "
            f"found {len(target)}."
        )

    original = target.geometry.iloc[0]
    repaired = make_valid(original)

    print("\n--- Original geometry ---")
    print("Type:", original.geom_type)
    print("Valid:", original.is_valid)
    print("Reason:", explain_validity(original))
    print("Area:", original.area)

    print("\n--- Repaired geometry (test only) ---")
    print("Type:", repaired.geom_type)
    print("Valid:", repaired.is_valid)
    print("Area:", repaired.area)
    print("Area difference:", abs(repaired.area - original.area))
    print("Area difference percentage:",
          abs(repaired.area - original.area)
          / original.area * 100 if original.area else float("nan"))

    print("\nOriginal geometry components:",
          len(original.geoms) if hasattr(original, "geoms") else 1)

    print("Repaired geometry components:",
          len(repaired.geoms) if hasattr(repaired, "geoms") else 1)

    print("\nNo files were modified or saved.")


if __name__ == "__main__":
    main()