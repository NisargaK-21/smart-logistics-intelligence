from pathlib import Path
import shutil
import pandas as pd

csv_path = Path("ml/data/final/historical/gsi_landslides_ner_validated.csv")
backup_path = csv_path.with_name("gsi_landslides_ner_validated_before_coordinate_fix.csv")

slide_id = "MZ/AIZ/84A14/2015/70"

df = pd.read_csv(csv_path)

matches = df.index[df["slide_id"].astype(str) == slide_id].tolist()

if len(matches) != 1:
    raise ValueError(f"Expected exactly one record for {slide_id}; found {len(matches)}")

idx = matches[0]
old_lat = df.at[idx, "latitude"]
longitude = df.at[idx, "longitude"]

if pd.isna(old_lat) or abs(float(old_lat)) != 23.736217:
    raise ValueError(f"Unexpected latitude {old_lat}; refusing to change it")

if pd.isna(longitude) or abs(float(longitude) - 92.796936) > 0.000001:
    raise ValueError(f"Unexpected longitude {longitude}; refusing to change it")

if not backup_path.exists():
    shutil.copy2(csv_path, backup_path)

df.at[idx, "latitude"] = 23.736217

# Recalculate the existing validation flags for this record.
df.at[idx, "coordinate_valid"] = True
df.at[idx, "coordinate_in_ner_range"] = True

df.to_csv(csv_path, index=False)

print("Correction saved.")
print(f"Backup: {backup_path}")
print(df.loc[idx, [
    "slide_id", "state", "district", "latitude", "longitude",
    "coordinate_valid", "coordinate_in_ner_range"
]].to_string())
