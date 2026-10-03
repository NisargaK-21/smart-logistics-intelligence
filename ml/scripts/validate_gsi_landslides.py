from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "final"
    / "historical"
    / "gsi_landslides_ner_normalized.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "final"
    / "historical"
    / "gsi_landslides_ner_validated.csv"
)


# Broad geographic range for Northeast India.
# This is a quality-control check, not an official boundary.
LAT_MIN = 20.0
LAT_MAX = 30.0
LON_MIN = 88.0
LON_MAX = 98.0


def main():
    print("Loading normalized dataset...")

    df = pd.read_csv(INPUT_PATH)

    # Basic coordinate validity.
    df["coordinate_valid"] = (
        df["latitude"].notna()
        & df["longitude"].notna()
        & df["latitude"].between(-90, 90)
        & df["longitude"].between(-180, 180)
    )

    # Check whether coordinates fall inside the broad NER range.
    df["coordinate_in_ner_range"] = (
        df["latitude"].notna()
        & df["longitude"].notna()
        & df["latitude"].between(LAT_MIN, LAT_MAX)
        & df["longitude"].between(LON_MIN, LON_MAX)
    )

    review = df[~df["coordinate_in_ner_range"]]

    print("\nTotal records:", len(df))
    print(
        "Valid latitude/longitude pairs:",
        int(df["coordinate_valid"].sum())
    )
    print(
        "Records outside broad NER range:",
        len(review)
    )

    print("\nRecords requiring coordinate review:")

    if review.empty:
        print("None")
    else:
        print(
            review[
                [
                    "slide_id",
                    "state",
                    "district",
                    "latitude",
                    "longitude",
                    "coordinate_valid",
                    "coordinate_in_ner_range",
                ]
            ].to_string(index=False)
        )

    # Save validated dataset.
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nValidated dataset saved to:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()