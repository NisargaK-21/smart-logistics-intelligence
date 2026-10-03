from pathlib import Path
import re

import geopandas as gpd
import pandas as pd


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT
    / "ml"
    / "data"
    / "processed"
    / "roads"
    / "roads_ner.gpkg"
)

OUTPUT_DIR = (
    ROOT
    / "ml"
    / "data"
    / "final"
    / "roads"
)

OUTPUT_GPKG = OUTPUT_DIR / "roads_final.gpkg"
OUTPUT_CSV = OUTPUT_DIR / "roads_final.csv"


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    """Convert empty/NaN text values to None."""
    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def parse_number(value):
    """Extract the first numeric value from a field."""
    if pd.isna(value):
        return None

    match = re.search(r"\d+(?:\.\d+)?", str(value))

    if match:
        return float(match.group())

    return None


def parse_bool(value):
    """Convert common OSM yes/no values to boolean."""
    if pd.isna(value):
        return False

    value = str(value).strip().lower()

    return value in {
        "yes",
        "true",
        "1",
    }


def classify_road(road_type):
    """
    Normalize OSM highway types into broader road classes.

    The original road_type is preserved.
    """

    if pd.isna(road_type):
        return "unknown"

    road_type = str(road_type).strip().lower()

    major = {
        "motorway",
        "motorway_link",
        "trunk",
        "trunk_link",
        "primary",
        "primary_link",
        "secondary",
        "secondary_link",
    }

    collector = {
        "tertiary",
        "tertiary_link",
    }

    local = {
        "residential",
        "living_street",
        "unclassified",
        "service",
    }

    special = {
        "escape",
    }

    if road_type in major:
        return "major"

    if road_type in collector:
        return "collector"

    if road_type in local:
        return "local"

    if road_type in special:
        return "special"

    return "unknown"


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("ROAD FINAL DATA PROCESSING")
    print("=" * 60)

    # --------------------------------------------------------
    # Check input
    # --------------------------------------------------------

    print("\nLoading processed road data...")
    print(f"Input: {INPUT_FILE}")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Processed road dataset not found:\n{INPUT_FILE}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    gdf = gpd.read_file(INPUT_FILE)

    print(f"Loaded {len(gdf):,} road records.")

        # --------------------------------------------------------
    # Geometry cleaning
    # --------------------------------------------------------

    print("\nCleaning geometries...")

    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[~gdf.geometry.is_empty].copy()

    invalid_before = (~gdf.geometry.is_valid).sum()

    print(
        f"Invalid geometries before repair: "
        f"{invalid_before}"
    )

    if invalid_before > 0:
        gdf["geometry"] = gdf.geometry.make_valid()

        # make_valid() can return GeometryCollection.
        # For the road network, keep only the line component.
        def extract_line_geometry(geom):
            if geom is None or geom.is_empty:
                return geom

            if geom.geom_type == "GeometryCollection":
                line_parts = [
                    part
                    for part in geom.geoms
                    if part.geom_type in {"LineString", "MultiLineString"}
                ]

                if not line_parts:
                    return None

                if len(line_parts) == 1:
                    return line_parts[0]

                from shapely.ops import linemerge

                return linemerge(line_parts)

            return geom

        gdf["geometry"] = (
            gdf["geometry"]
            .apply(extract_line_geometry)
        )

    invalid_after = (~gdf.geometry.is_valid).sum()

    print(
        f"Invalid geometries after repair: "
        f"{invalid_after}"
    )
    # Remove anything that could not be converted to a road geometry
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[~gdf.geometry.is_empty].copy()

# Final road geometry check
    non_line_geometry = ~gdf.geometry.geom_type.isin(
    ["LineString", "MultiLineString"]
)

    print(
    f"Non-line geometries removed: "
    f"{non_line_geometry.sum()}"
)

    gdf = gdf[~non_line_geometry].copy()

    if invalid_after > 0:
        raise RuntimeError(
            "Some geometries are still invalid after repair."
        )

    print(
        f"After geometry filtering: "
        f"{len(gdf):,} records."
    )
    # --------------------------------------------------------
    # Remove non-road feature
    # --------------------------------------------------------

    print("\nRemoving non-road features...")

    before = len(gdf)

    if "highway" in gdf.columns:

        bus_stop_mask = (
            gdf["highway"]
            .astype(str)
            .str.lower()
            .eq("bus_stop")
        )

        removed_bus_stops = int(bus_stop_mask.sum())

        gdf = gdf[~bus_stop_mask].copy()

    else:
        removed_bus_stops = 0

    print(
        f"Removed bus_stop features: "
        f"{removed_bus_stops}"
    )

    print(
        f"Records remaining: "
        f"{len(gdf):,}"
    )

    # --------------------------------------------------------
    # Rename important fields
    # --------------------------------------------------------

    rename_map = {
        "id": "osm_id",
        "highway": "road_type",
        "name": "road_name",
    }

    gdf = gdf.rename(
        columns=rename_map
    )

    # --------------------------------------------------------
    # Clean text fields
    # --------------------------------------------------------

    print("\nCleaning attributes...")

    text_columns = [
        "road_type",
        "road_name",
        "surface",
        "smoothness",
        "access",
        "motor_vehicle",
    ]

    for column in text_columns:

        if column in gdf.columns:

            gdf[column] = (
                gdf[column]
                .apply(clean_text)
            )

    # --------------------------------------------------------
    # Numeric fields
    # --------------------------------------------------------

    if "lanes" in gdf.columns:

        gdf["lanes"] = (
            gdf["lanes"]
            .apply(parse_number)
        )

    if "maxspeed" in gdf.columns:

        gdf["maxspeed_kmh"] = (
            gdf["maxspeed"]
            .apply(parse_number)
        )

    if "width" in gdf.columns:

        gdf["width_m"] = (
            gdf["width"]
            .apply(parse_number)
        )

    # --------------------------------------------------------
    # Boolean fields
    # --------------------------------------------------------

    for column in [
        "oneway",
        "bridge",
        "tunnel",
    ]:

        if column in gdf.columns:

            gdf[column] = (
                gdf[column]
                .apply(parse_bool)
            )

    # --------------------------------------------------------
    # Road length
    # --------------------------------------------------------

    print("\nCalculating road lengths...")

    if "length" in gdf.columns:

        gdf["length_km"] = (
            pd.to_numeric(
                gdf["length"],
                errors="coerce",
            )
            / 1000.0
        )

    else:

        print(
            "Length field unavailable."
        )

        print(
            "Calculating geometry length..."
        )

        projected = gdf.to_crs(
            gdf.estimate_utm_crs()
        )

        gdf["length_km"] = (
            projected.geometry.length
            / 1000.0
        )

    # Remove invalid lengths

    gdf = gdf[
        gdf["length_km"].notna()
        & (gdf["length_km"] > 0)
    ].copy()

    # --------------------------------------------------------
    # Road classification
    # --------------------------------------------------------

    print("\nCreating normalized road classes...")

    gdf["road_class"] = (
        gdf["road_type"]
        .apply(classify_road)
    )

    # --------------------------------------------------------
    # Derived accessibility features
    # --------------------------------------------------------

    print(
        "\nCreating derived road features..."
    )

    if "surface" in gdf.columns:

        paved_surfaces = {
            "asphalt",
            "concrete",
            "paving_stones",
            "paved",
            "chipseal",
            "cement",
        }

        gdf["is_paved"] = (
            gdf["surface"]
            .astype("string")
            .str.lower()
            .isin(paved_surfaces)
        )

    else:

        gdf["is_paved"] = False

    gdf["is_major_road"] = (
        gdf["road_class"] == "major"
    )

    gdf["is_bridge"] = (
        gdf["bridge"]
        if "bridge" in gdf.columns
        else False
    )

    gdf["is_tunnel"] = (
        gdf["tunnel"]
        if "tunnel" in gdf.columns
        else False
    )

    gdf["is_oneway"] = (
        gdf["oneway"]
        if "oneway" in gdf.columns
        else False
    )

    # --------------------------------------------------------
    # Coordinates
    # --------------------------------------------------------

    print("\nGenerating road coordinates...")

    representative_points = (
        gdf.geometry.representative_point()
    )

    gdf["lon"] = representative_points.x
    gdf["lat"] = representative_points.y

    # --------------------------------------------------------
    # Stable road ID
    # --------------------------------------------------------

    print("\nCreating stable road IDs...")

    gdf["road_id"] = (
        "osm_way_"
        + gdf["osm_id"].astype(str)
    )

    # --------------------------------------------------------
    # Remove duplicate OSM IDs
    # --------------------------------------------------------

    duplicate_osm_ids = (
        gdf["osm_id"]
        .duplicated()
        .sum()
    )

    print(
        f"Duplicate OSM IDs: "
        f"{duplicate_osm_ids}"
    )

    if duplicate_osm_ids > 0:

        print(
            "Keeping first occurrence "
            "of each OSM way."
        )

        gdf = (
            gdf
            .drop_duplicates(
                subset=["osm_id"],
                keep="first",
            )
            .copy()
        )

    # --------------------------------------------------------
    # Final column selection
    # --------------------------------------------------------

    final_columns = [
        "road_id",
        "osm_id",

        "road_type",
        "road_class",
        "road_name",

        "surface",
        "smoothness",
        "lanes",
        "maxspeed_kmh",
        "width_m",

        "oneway",
        "bridge",
        "tunnel",

        "access",
        "motor_vehicle",

        "is_paved",
        "is_major_road",
        "is_bridge",
        "is_tunnel",
        "is_oneway",

        "length_km",

        "lat",
        "lon",

        "geometry",
    ]

    available_columns = [
        column
        for column in final_columns
        if column in gdf.columns
    ]

    gdf = gdf[
        available_columns
    ].copy()

    # --------------------------------------------------------
    # Reset index
    # --------------------------------------------------------

    gdf = gdf.reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("FINAL ROAD DATA VALIDATION")
    print("=" * 60)

    print(
        f"\nRoad segments: "
        f"{len(gdf):,}"
    )

    print(
        f"CRS: "
        f"{gdf.crs}"
    )

    print(
        "\nGeometry types:"
    )

    print(
        gdf.geometry
        .geom_type
        .value_counts()
        .to_string()
    )

    print(
        "\nRoad classes:"
    )

    print(
        gdf["road_class"]
        .value_counts(dropna=False)
        .to_string()
    )

    print(
        "\nRoad types:"
    )

    print(
        gdf["road_type"]
        .value_counts(dropna=False)
        .head(30)
        .to_string()
    )

    print(
        "\nMissing values:"
    )

    print(
        gdf.isna()
        .sum()
        .sort_values(
            ascending=False
        )
        .to_string()
    )

    print(
        "\nLength statistics (km):"
    )

    print(
        gdf["length_km"]
        .describe()
        .to_string()
    )

    print(
        "\nLatitude range:"
    )

    print(
        f"{gdf['lat'].min():.6f} "
        f"to "
        f"{gdf['lat'].max():.6f}"
    )

    print(
        "\nLongitude range:"
    )

    print(
        f"{gdf['lon'].min():.6f} "
        f"to "
        f"{gdf['lon'].max():.6f}"
    )

    # --------------------------------------------------------
    # Save GeoPackage
    # --------------------------------------------------------

    print("\nSaving GeoPackage...")

    gdf.to_file(
        OUTPUT_GPKG,
        driver="GPKG",
        layer="roads_final",
    )

    # --------------------------------------------------------
    # Save CSV
    # --------------------------------------------------------

    print("Saving CSV...")

    csv_gdf = gdf.drop(
        columns=["geometry"]
    )

    csv_gdf.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("ROAD FINAL PROCESSING COMPLETE")
    print("=" * 60)

    print(
        f"\nGeoPackage:"
        f"\n{OUTPUT_GPKG}"
    )

    print(
        f"\nCSV:"
        f"\n{OUTPUT_CSV}"
    )

    print(
        f"\nFinal road count: "
        f"{len(gdf):,}"
    )

    print(
        "\nYour road dataset is ready "
        "for validation/integration."
    )


if __name__ == "__main__":
    main()