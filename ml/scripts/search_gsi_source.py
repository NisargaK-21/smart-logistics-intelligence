from pathlib import Path
import fitz

pdf = Path("ml/data/raw/historical/landslide_report.pdf")
targets = [
    "ASM/WKA/83C09/2016/34",
    "MZ/AIZ/84A14/2015/70",
]

if not pdf.exists():
    raise FileNotFoundError(f"PDF not found: {pdf}")

with fitz.open(pdf) as doc:
    print(f"PDF pages: {len(doc)}")

    for target in targets:
        print(f"\n{'=' * 70}\nSearching for: {target}")
        matches = 0

        for page_number, page in enumerate(doc):
            text = page.get_text()
            if target.casefold() in text.casefold():
                matches += 1
                print(f"\nPage {page_number + 1}:")
                position = text.casefold().find(target.casefold())
                start = max(0, position - 500)
                end = min(len(text), position + len(target) + 1000)
                print(text[start:end])

        if matches == 0:
            print("No exact text match found.")
            print("The report may require OCR or use a different slide-ID format.")
