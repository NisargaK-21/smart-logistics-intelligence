from pathlib import Path
from pyrosm import OSM

# Project root
ROOT = Path(__file__).resolve().parents[2]

# Input and output paths
PBF_FILE = ROOT / "ml" / "data" / "raw" / "roads" / "north-eastern-zone.osm.pbf"
OUTPUT_DIR = ROOT / "ml" / "data" / "processed" / "roads"
OUTPUT_FILE = OUTPUT_DIR / "roads_ner.gpkg"


def main():
    print("Loading OSM data...")
    print(f"Input: {PBF_FILE}")

    if not PBF_FILE.exists():
        raise FileNotFoundError(f"OSM file not found: {PBF_FILE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    osm = OSM(str(PBF_FILE))

    print("Extracting road network...")
    roads = osm.get_network(network_type="driving")

    if roads is None or roads.empty:
        raise RuntimeError("No road data was extracted.")

    print(f"Extracted {len(roads):,} road segments.")

    print(f"Saving to: {OUTPUT_FILE}")
    roads.to_file(OUTPUT_FILE, driver="GPKG")

    print("Road extraction complete!")


if __name__ == "__main__":
    main()