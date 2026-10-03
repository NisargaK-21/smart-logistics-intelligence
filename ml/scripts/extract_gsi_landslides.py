from pathlib import Path
import pdfplumber
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PDF_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "raw"
    / "historical"
    / "landslide_report.pdf"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "historical"
    / "gsi_landslides_extracted.csv"
)

EXPECTED_COLUMNS = [
    "sl_no",
    "slide_id",
    "state",
    "district",
    "slide_name",
    "road_location",
    "latitude",
    "longitude",
    "material",
    "movement_type",
    "history",
]


def clean_cell(value):
    """Normalize whitespace while preserving missing values."""
    if value is None:
        return None

    value = str(value).replace("\n", " ")
    value = " ".join(value.split())

    return value if value else None


def is_header_row(row):
    """Detect repeated table-header rows."""
    if not row:
        return True

    first = clean_cell(row[0])
    second = clean_cell(row[1]) if len(row) > 1 else None

    return (
        first == "Sl.No."
        or second == "Slide_No"
    )


def is_title_row(row):
    """Detect the PDF title row."""
    if not row:
        return True

    first = clean_cell(row[0])

    return first and first.upper().startswith("LANDSLIDE INVENTORY")


def extract_all_pages():
    records = []

    print(f"PDF: {PDF_PATH}")

    with pdfplumber.open(PDF_PATH) as pdf:
        total_pages = len(pdf.pages)

        print(f"Total pages: {total_pages}")

        for page_number, page in enumerate(pdf.pages, start=1):

            print(f"Processing page {page_number}/{total_pages}...")

            tables = page.extract_tables()

            for table in tables:

                for row in table:

                    if not row:
                        continue

                    if is_title_row(row):
                        continue

                    if is_header_row(row):
                        continue

                    # Make sure we have exactly 11 columns.
                    row = list(row)

                    if len(row) < 11:
                        row.extend([None] * (11 - len(row)))

                    if len(row) > 11:
                        row = row[:11]

                    row = [clean_cell(value) for value in row]

                    # Ignore completely empty rows.
                    if not any(row):
                        continue

                    records.append(row)

    df = pd.DataFrame(records, columns=EXPECTED_COLUMNS)

    # Convert coordinates to numeric values.
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Convert serial number to numeric where possible.
    df["sl_no"] = pd.to_numeric(df["sl_no"], errors="coerce")

    # Remove rows that clearly aren't actual records.
    df = df[df["slide_id"].notna()].copy()

    # Remove duplicate records caused by repeated PDF content.
    df = df.drop_duplicates(
        subset=["slide_id"],
        keep="first",
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nExtraction complete.")
    print(f"Rows extracted: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"Output: {OUTPUT_PATH}")

    print("\nColumns:")
    print(list(df.columns))

    print("\nRecords by state:")
    print(df["state"].value_counts(dropna=False))

    print("\nMissing values:")
    print(df.isna().sum())


if __name__ == "__main__":
    extract_all_pages()