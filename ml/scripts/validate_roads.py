from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

ROAD_FILE = (
    ROOT
    / "ml"
    / "data"
    / "final"
    / "roads"
    / "roads_final.gpkg"
)


def main():

    print("=" * 60)
    print("ROAD DATASET VALIDATION")
    print("=" * 60)

    if not ROAD_FILE.exists():
        raise FileNotFoundError(
            f"Road dataset not found:\n{ROAD_FILE}"
        )

    gdf = gpd.read_file(ROAD_FILE)

    errors = []

    # --------------------------------------------------------
    # Basic checks
    # --------------------------------------------------------

    print(f"\nRows: {len(gdf):,}")
    print(f"CRS: {gdf.crs}")

    if len(gdf) == 0:
        errors.append("Dataset is empty.")

    if gdf.crs is None:
        errors.append("CRS is missing.")

    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    required_columns = [
        "road_id",
        "osm_id",
        "road_type",
        "road_class",
        "length_km",
        "lat",
        "lon",
        "geometry",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in gdf.columns
    ]

    if missing_columns:
        errors.append(
            f"Missing required columns: {missing_columns}"
        )

    # --------------------------------------------------------
    # Geometry checks
    # --------------------------------------------------------

    null_geometry = gdf.geometry.isna().sum()
    empty_geometry = gdf.geometry.is_empty.sum()
    invalid_geometry = (~gdf.geometry.is_valid).sum()

    print("\nGeometry:")
    print(f"  Null: {null_geometry}")
    print(f"  Empty: {empty_geometry}")
    print(f"  Invalid: {invalid_geometry}")

    if null_geometry > 0:
        errors.append("Null geometries found.")

    if empty_geometry > 0:
        errors.append("Empty geometries found.")

    if invalid_geometry > 0:
        errors.append("Invalid geometries found.")

    # --------------------------------------------------------
    # ID checks
    # --------------------------------------------------------

    duplicate_road_ids = (
        gdf["road_id"].duplicated().sum()
    )

    duplicate_osm_ids = (
        gdf["osm_id"].duplicated().sum()
    )

    print("\nIDs:")
    print(f"  Duplicate road_id: {duplicate_road_ids}")
    print(f"  Duplicate osm_id: {duplicate_osm_ids}")

    if duplicate_road_ids > 0:
        errors.append("Duplicate road_id values found.")

    if duplicate_osm_ids > 0:
        errors.append("Duplicate osm_id values found.")

    # --------------------------------------------------------
    # Length checks
    # --------------------------------------------------------

    invalid_length = (
        gdf["length_km"].isna()
        | (gdf["length_km"] <= 0)
    ).sum()

    print("\nLength:")
    print(f"  Invalid length values: {invalid_length}")

    if invalid_length > 0:
        errors.append(
            "Roads with invalid length found."
        )

    # --------------------------------------------------------
    # Coordinate checks
    # --------------------------------------------------------

    invalid_lat = (
        gdf["lat"].isna()
        | (gdf["lat"] < -90)
        | (gdf["lat"] > 90)
    ).sum()

    invalid_lon = (
        gdf["lon"].isna()
        | (gdf["lon"] < -180)
        | (gdf["lon"] > 180)
    ).sum()

    print("\nCoordinates:")
    print(f"  Invalid latitude: {invalid_lat}")
    print(f"  Invalid longitude: {invalid_lon}")

    if invalid_lat > 0:
        errors.append("Invalid latitude values found.")

    if invalid_lon > 0:
        errors.append("Invalid longitude values found.")

    # --------------------------------------------------------
    # Bus-stop check
    # --------------------------------------------------------

    bus_stop_count = (
        gdf["road_type"]
        .astype(str)
        .str.lower()
        .eq("bus_stop")
        .sum()
    )

    print("\nNon-road feature check:")
    print(f"  bus_stop records: {bus_stop_count}")

    if bus_stop_count > 0:
        errors.append(
            "bus_stop records are present in final road data."
        )

    # --------------------------------------------------------
    # Road classes
    # --------------------------------------------------------

    print("\nRoad classes:")
    print(
        gdf["road_class"]
        .value_counts(dropna=False)
        .to_string()
    )

    # --------------------------------------------------------
    # Road types
    # --------------------------------------------------------

    print("\nTop road types:")
    print(
        gdf["road_type"]
        .value_counts(dropna=False)
        .head(20)
        .to_string()
    )

    # --------------------------------------------------------
    # Missing data
    # --------------------------------------------------------

    print("\nMissing values:")
    print(
        gdf.isna()
        .sum()
        .sort_values(ascending=False)
        .to_string()
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    if errors:

        print("VALIDATION FAILED")
        print("=" * 60)

        for error in errors:
            print(f"- {error}")

        raise SystemExit(1)

    else:

        print("VALIDATION PASSED")
        print("=" * 60)

        print(
            "\nRoad dataset is structurally valid "
            "and ready for team integration."
        )


if __name__ == "__main__":
    main()