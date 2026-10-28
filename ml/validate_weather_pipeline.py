
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"

files = {
    "Historical weather": DATA / "weather_processed.csv",
    "Rainfall features": DATA / "weather_features.csv",
    "Recent weather": DATA / "weather_recent_oct2026.csv",
    "Extended recent weather features": (
        DATA / "weather_recent_sep30_oct03_2026_features.csv"
    ),
    "Weather locations": DATA / "weather_locations.csv",
    "Field reports + weather": (
        DATA / "field_reports" / "field_reports_with_weather.csv"
    ),
    "Field reports + extended weather features": (
        ROOT / "data" / "final" / "field_reports_with_weather_features.csv"
    ),
}

failed = False

for name, path in files.items():
    print(f"\n--- {name} ---")

    if not path.exists():
        print("MISSING:", path)
        failed = True
        continue

    df = pd.read_csv(path)
    print("Rows:", len(df))
    print("Columns:", len(df.columns))

    if name == "Historical weather":
        print("Locations:", df["location_id"].nunique())
        print("Missing values:", int(df.isna().sum().sum()))
        print("Duplicate location/time pairs:",
              int(df.duplicated(["location_id", "time"]).sum()))

    elif name == "Rainfall features":
        cols = [
            "precipitation_sum_3h_mm",
            "precipitation_sum_6h_mm",
            "precipitation_sum_24h_mm",
        ]
        print("Locations:", df["location_id"].nunique())
        print("Feature missing values:", df[cols].isna().sum().to_dict())
        print("Negative rainfall features:",
              int((df[cols].lt(0).fillna(False)).sum().sum()))

    elif name == "Recent weather":
        print("Locations:", df["location_id"].nunique())
        print("Missing values:", int(df.isna().sum().sum()))

    elif name == "Weather locations":
        print("Location IDs:", df["location_id"].nunique())
        print("Missing values:", int(df.isna().sum().sum()))

    elif name == "Field reports + weather":
        print("Reports:", len(df))
        print("Reports with weather:",
              int(df["temperature_c"].notna().sum()))
        print("Missing weather rows:",
              int(df["temperature_c"].isna().sum()))

print("\nValidation inspection complete.")
print("This is a summary check, not proof of scientific accuracy.")
