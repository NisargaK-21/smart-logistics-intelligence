from pathlib import Path
import pandas as pd


input_file = Path("ml/data/raw/gps/vehicle_gps.csv")
output_file = Path("ml/data/processed/gps/vehicle_gps_processed.csv")

df = pd.read_csv(input_file)

# Standardize column names
df = df.rename(columns={
    "bus_id": "vehicle_id",
    "speed": "speed_kmh"
})

# Convert timestamp
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Keep project schema
df = df[
    [
        "vehicle_id",
        "timestamp",
        "latitude",
        "longitude",
        "speed_kmh"
    ]
]

# Remove duplicates
df = df.drop_duplicates()

# Sort by vehicle and time
df = df.sort_values(
    ["vehicle_id", "timestamp"]
).reset_index(drop=True)

# Save
output_file.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(output_file, index=False)

print("GPS dataset processed successfully!")
print(f"Output: {output_file}")
print(f"Rows: {len(df):,}")
print()
print(df.head())
print()
print("Missing values:")
print(df.isnull().sum())