from pathlib import Path
import pandas as pd


INPUT_FILE = Path("ml/data/raw/field_reports/field_reports.csv")
OUTPUT_FILE = Path(
    "ml/data/processed/field_reports/field_reports_processed.csv"
)

REQUIRED_COLUMNS = [
    "report_id",
    "timestamp",
    "latitude",
    "longitude",
    "incident_type",
    "severity",
    "description",
    "image_path",
    "reported_by",
]

VALID_INCIDENT_TYPES = {
    "landslide",
    "flood",
    "road_blockage",
    "heavy_rainfall",
    "road_damage",
    "bridge_damage",
    "other",
}

VALID_SEVERITIES = {
    "low",
    "medium",
    "high",
    "critical",
}


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    # Check required columns
    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # Keep required columns in fixed order
    df = df[REQUIRED_COLUMNS].copy()

    # Convert timestamp
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    # Convert numeric fields
    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce"
    )

    # Remove duplicate reports
    df = df.drop_duplicates(subset=["report_id"])

    # Validate incident types
    invalid_incidents = set(df["incident_type"].dropna()) - VALID_INCIDENT_TYPES

    if invalid_incidents:
        raise ValueError(
            f"Invalid incident types: {invalid_incidents}"
        )

    # Validate severity
    invalid_severity = set(df["severity"].dropna()) - VALID_SEVERITIES

    if invalid_severity:
        raise ValueError(
            f"Invalid severity values: {invalid_severity}"
        )

    # Remove invalid records
    df = df.dropna(
        subset=[
            "report_id",
            "timestamp",
            "latitude",
            "longitude",
            "incident_type",
            "severity",
        ]
    )

    # Sort by time
    df = df.sort_values("timestamp")

    # Create output folder
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Save
    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("Field report processing completed.")
    print(f"Input rows: {len(pd.read_csv(INPUT_FILE))}")
    print(f"Output rows: {len(df)}")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()