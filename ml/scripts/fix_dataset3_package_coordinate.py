from pathlib import Path
import shutil
import pandas as pd

path = Path("ml/data/final/historical/dataset3_landslide_events.csv")
backup = path.with_name("dataset3_landslide_events_before_coordinate_fix.csv")
slide_id = "MZ/AIZ/84A14/2015/70"

df = pd.read_csv(path)

matches = df.index[df["slide_id"].astype(str) == slide_id].tolist()

if len(matches) != 1:
    raise ValueError(f"Expected one matching record, found {len(matches)}")

idx = matches[0]
lat = float(df.at[idx, "latitude"])
lon = float(df.at[idx, "longitude"])

if abs(lat) != 23.736217 or abs(lon - 92.796936) > 0.000001:
    raise ValueError(f"Unexpected coordinates: latitude={lat}, longitude={lon}")

if not backup.exists():
    shutil.copy2(path, backup)

df.at[idx, "latitude"] = 23.736217

if "coordinate_valid" in df.columns:
    df.at[idx, "coordinate_valid"] = True

if "coordinate_in_ner_range" in df.columns:
    df.at[idx, "coordinate_in_ner_range"] = True

df.to_csv(path, index=False)

print("Dataset 3 package CSV corrected.")
print(f"Backup created at: {backup}")
print(df.loc[idx].to_string())
