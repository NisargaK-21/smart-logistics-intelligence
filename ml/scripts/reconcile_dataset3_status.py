from pathlib import Path
import shutil
import pandas as pd

path = Path("ml/data/final/historical/dataset3_landslide_events.csv")
backup = path.with_name("dataset3_landslide_events_before_status_fix.csv")
slide_id = "MZ/AIZ/84A14/2015/70"

df = pd.read_csv(path)
matches = df.index[df["slide_id"].astype(str) == slide_id].tolist()

if len(matches) != 1:
    raise ValueError(f"Expected one matching record; found {len(matches)}")

i = matches[0]
row = df.loc[i]

if abs(float(row["latitude"]) - 23.736217) > 0.000001:
    raise ValueError("Latitude does not match the verified source value")
if abs(float(row["longitude"]) - 92.796936) > 0.000001:
    raise ValueError("Longitude does not match the verified source value")
if not bool(row["coordinate_in_geographic_bounds"]):
    raise ValueError("Geographic-bounds flag is not True; stopping")

if not backup.exists():
    shutil.copy2(path, backup)

df.at[i, "coordinate_in_ner_bounds"] = True
df.at[i, "spatial_use_status"] = "eligible_for_reviewed_spatial_analysis"

df.to_csv(path, index=False)

print("Updated verified Mizoram record.")
print(f"Backup: {backup}")
print(df.loc[i, [
    "slide_id", "latitude", "longitude",
    "coordinate_in_geographic_bounds",
    "coordinate_in_ner_bounds", "spatial_use_status"
]].to_string())
