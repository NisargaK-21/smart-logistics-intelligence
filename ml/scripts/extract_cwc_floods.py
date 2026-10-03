import re
from pathlib import Path

import pandas as pd
import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PDF_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "raw"
    / "historical"
    / "cwc_flood_assessment.pdf"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "historical"
    / "cwc_floods_extracted.csv"
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


EXPECTED_COUNTS = {
    "Arunachal Pradesh": 25,
    "Assam": 33,
    "Manipur": 16,
    "Meghalaya": 11,
    "Mizoram": 8,
    "Nagaland": 11,
    "Sikkim": 4,
    "Tripura": 8,
}


# Exact PDF pages containing the NER district tables.
STATE_TABLE_PAGES = {
    "Arunachal Pradesh": 40,
    "Assam": 42,
    "Manipur": 68,
    "Meghalaya": 70,
    "Mizoram": 72,
    "Nagaland": 74,
    "Sikkim": 82,
    "Tripura": 88,
}


def clean_text(text):
    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip()


def parse_area(value):
    return float(value.replace(",", ""))


records = []

print(f"Reading: {PDF_PATH}")

with pdfplumber.open(PDF_PATH) as pdf:

    print(f"Total PDF pages: {len(pdf.pages)}")

    for state, page_number in STATE_TABLE_PAGES.items():

        page = pdf.pages[page_number - 1]

        text = page.extract_text()

        if not text:
            print(f"WARNING: no text found for {state}")
            continue

        print(f"Extracting {state} from page {page_number}")

        table_started = False

        for raw_line in text.splitlines():

            line = clean_text(raw_line)

            if not line:
                continue

            # Start after the district-table header
            if "Name of the District" in line:
                table_started = True
                continue

            if not table_started:
                continue

            # Stop at Total
            if re.match(
                r"^Total\s+[\d,]+\.\d+$",
                line,
                re.IGNORECASE,
            ):
                break

            # District format:
            # 1 ANJAW 4,403.83
            match = re.match(
                r"^(\d+)\s+(.+?)\s+([\d,]+\.\d+)$",
                line,
            )

            if not match:
                continue

            serial_no = int(match.group(1))
            district = clean_text(match.group(2))
            affected_area = parse_area(match.group(3))

            if serial_no > EXPECTED_COUNTS[state]:
                continue

            records.append(
                {
                    "disaster_type": "Flood",
                    "state": state,
                    "district": district,
                    "flood_affected_area_ha": affected_area,
                    "study_period": "1986-2022",
                    "source": "Central Water Commission",
                    "source_file": "cwc_flood_assessment.pdf",
                    "source_page": page_number,
                }
            )


df = pd.DataFrame(records)

if df.empty:
    raise RuntimeError(
        "No flood records were extracted."
    )


# Check duplicates
duplicates = df[
    df.duplicated(
        subset=["state", "district"],
        keep=False,
    )
]

if not duplicates.empty:
    print("\nWARNING: duplicate state/district records found:")
    print(
        duplicates[
            ["state", "district"]
        ].to_string(index=False)
    )


df = df.drop_duplicates(
    subset=["state", "district"]
).reset_index(drop=True)


df = df.sort_values(
    ["state", "district"]
).reset_index(drop=True)


print("\nExpected vs extracted:")

state_counts = df["state"].value_counts()

for state in NER_STATES:

    expected = EXPECTED_COUNTS[state]
    actual = int(state_counts.get(state, 0))

    status = "OK" if expected == actual else "CHECK"

    print(
        f"{state}: "
        f"expected={expected}, "
        f"extracted={actual} -> {status}"
    )


print("\nTotal records:", len(df))

if len(df) != sum(EXPECTED_COUNTS.values()):
    raise RuntimeError(
        "Record count is incorrect. "
        "Do not use the extracted CSV."
    )


OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_csv(
    OUTPUT_PATH,
    index=False,
)


print(f"\nExtraction complete.")
print(f"Output: {OUTPUT_PATH}")

print("\nPreview:")
print(df.head(15).to_string(index=False))