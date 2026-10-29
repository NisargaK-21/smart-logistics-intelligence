
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

files = {
    "Floods": ROOT / "ml/data/final/historical/cwc_floods_ner_clean.csv",
    "Landslides": ROOT / "ml/data/final/historical/gsi_landslides_ner_validated.csv",
    "Weather locations": ROOT / "ml/data/processed/weather_locations.csv",
}

for name, path in files.items():
    print(f"\n--- {name} ---")

    if not path.exists():
        print("File not found:", path)
        continue

    df = pd.read_csv(path)
    print("Total records:", len(df))

    state_col = next(
        (c for c in df.columns if c.lower() in
         ["state", "state_name", "state/ut"]),
        None,
    )

    if state_col:
        print("States found:")
        for state in sorted(df[state_col].dropna().astype(str).str.strip().unique()):
            print(" -", state)
    else:
        print("No state column; coordinate-based checking is needed.")
        print("Columns:", ", ".join(df.columns))
