from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "final"
    / "historical"
    / "gsi_landslides_ner_validated.csv"
)

REPORT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "historical"
    / "gsi_final_quality_report.txt"
)


def main():
    df = pd.read_csv(INPUT_PATH)

    report = []

    report.append("GSI NORTHEAST INDIA LANDSLIDE DATASET")
    report.append("Final Data Quality Report")
    report.append("=" * 60)
    report.append("")

    report.append(f"Total records: {len(df)}")
    report.append(f"Total columns: {len(df.columns)}")
    report.append(
        f"Unique slide IDs: {df['slide_id'].nunique()}"
    )
    report.append("")

    report.append("RECORDS BY STATE")
    report.append("-" * 30)
    report.append(
        df["state"].value_counts().to_string()
    )
    report.append("")

    report.append("MISSING VALUES")
    report.append("-" * 30)
    report.append(
        df.isna().sum().to_string()
    )
    report.append("")

    report.append("DUPLICATE SLIDE IDs")
    report.append("-" * 30)
    report.append(
        str(df["slide_id"].duplicated().sum())
    )
    report.append("")

    report.append("COORDINATE QUALITY")
    report.append("-" * 30)
    report.append(
        f"Valid coordinate pairs: "
        f"{int(df['coordinate_valid'].sum())}"
    )
    report.append(
        f"Outside broad NER range: "
        f"{int((~df['coordinate_in_ner_range']).sum())}"
    )
    report.append("")

    report.append("MOVEMENT CATEGORIES")
    report.append("-" * 30)
    report.append(
        df["movement_category"]
        .value_counts(dropna=False)
        .to_string()
    )
    report.append("")

    report.append("MATERIAL CATEGORIES")
    report.append("-" * 30)
    report.append(
        df["material_category"]
        .value_counts(dropna=False)
        .to_string()
    )
    report.append("")

    report.append("COORDINATE RECORDS REQUIRING REVIEW")
    report.append("-" * 30)

    review = df[~df["coordinate_in_ner_range"]]

    if review.empty:
        report.append("None")
    else:
        report.append(
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

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    REPORT_PATH.write_text(
        "\n".join(report),
        encoding="utf-8"
    )

    print("Report generated:")
    print(REPORT_PATH)


if __name__ == "__main__":
    main()