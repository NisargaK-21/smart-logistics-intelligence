from pathlib import Path
import zipfile

ROOT = Path.cwd()
OUT = ROOT / "Dataset3_Historical_Disasters.zip"

files = {
    "data/landslides/dataset3_landslide_events.csv":
        "ml/data/final/historical/dataset3_landslide_events.csv",
    "data/landslides/ner_gsi_landslide_points.geojson":
        "ml/data/processed/landslides/ner_gsi_landslide_points.geojson",
    "data/floods/dataset3_flood_district_impacts.csv":
        "ml/data/final/historical/dataset3_flood_district_impacts.csv",
    "data/floods/ner_district_floods.geojson":
        "ml/data/processed/floods/ner_district_floods.geojson",
    "data/district_disaster_history/ner_district_disaster_history.csv":
        "ml/data/processed/disaster/ner_district_disaster_history.csv",
    "data/district_disaster_history/ner_district_disaster_history.geojson":
        "ml/data/processed/disaster/ner_district_disaster_history.geojson",
    "validation/gsi_landslides_coordinate_review.csv":
        "ml/data/processed/landslides/gsi_landslides_coordinate_review.csv",
    "validation/gsi_landslide_preparation_summary.txt":
        "ml/data/processed/landslides/gsi_landslide_preparation_summary.txt",
    "validation/cwc_flood_boundary_join_audit.csv":
        "ml/data/processed/floods/cwc_flood_boundary_join_audit.csv",
    "validation/disaster_history_summary.txt":
        "ml/data/processed/disaster/disaster_history_summary.txt",
    "validation/unmatched_landslide_points.csv":
        "ml/data/processed/disaster/unmatched_landslide_points.csv",
}

missing = [
    source for source in files.values()
    if not (ROOT / source).is_file()
]

if missing:
    print("ERROR: These required files are missing:")
    for source in missing:
        print(f" - {source}")
    raise SystemExit(1)

readme = """# Dataset 3 — Historical Disasters

Project: NER-ResQ — AI-Based Smart Logistics and Accessibility
Intelligence Platform for Northeast India.

## Contents

- Landslide event records derived from GSI data.
- Landslide GeoJSON containing spatially eligible records.
- District-level flood-impact records derived from CWC data.
- Flood and combined district disaster-history GeoJSON files.
- Validation summaries, coordinate-review records, and boundary-join audit.

## Important interpretation notes

The landslide CSV contains source records, including one record whose
longitude is missing and which remains under coordinate review. The
spatial landslide GeoJSON excludes records that cannot be mapped due
to missing coordinates.

The Mizoram record MZ/AIZ/84A14/2015/70 has the source-verified
coordinates latitude 23.736217 and longitude 92.796936.

The flood dataset represents district-level aggregated flood impacts
for the study period 1986–2022. It is not a catalogue of individually
dated flood events. Event dates and severity should not be inferred
where source data does not provide them.

Geometric validity and consistency checks do not independently prove
the accuracy of every source measurement or geographic boundary join.
Consult the validation files before using the data for analysis.

## Coordinate reference systems

The processed GeoJSON files use EPSG:7755, as checked during validation.

## Provenance

Consult the source, source_file, source_page, study_period, and
record-level fields in the CSVs where available. The original source
PDFs are not included in this package.
"""

with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("README.md", readme)

    for archive_name, source in files.items():
        zf.write(ROOT / source, f"Dataset3_Historical_Disasters/{archive_name}")

    # Include a machine-readable list of packaged files.
    manifest = "\n".join(
        ["Archive path | Project source path"] +
        [
            f"Dataset3_Historical_Disasters/{archive_name} | {source}"
            for archive_name, source in files.items()
        ]
    )
    zf.writestr("Dataset3_Historical_Disasters/manifest.txt", manifest + "\n")

print(f"Created: {OUT}")
print(f"Size: {OUT.stat().st_size:,} bytes")

with zipfile.ZipFile(OUT, "r") as zf:
    bad = zf.testzip()
    print("ZIP integrity:", "PASS" if bad is None else f"FAIL: {bad}")
    print("Files included:", len(zf.namelist()))
    for name in zf.namelist():
        print(" -", name)
