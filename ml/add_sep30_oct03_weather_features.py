
from pathlib import Path
import pandas as pd

raw_path = Path("ml/data/raw/weather/weather_sep30_oct03_2026.csv")
output_path = Path(
    "ml/data/processed/weather_recent_sep30_oct03_2026_features.csv"
)

# Find the actual hourly weather header in the downloaded CSV.
lines = raw_path.read_text(encoding="utf-8-sig").splitlines()
header_index = next(
    i for i, line in enumerate(lines)
    if line.strip().startswith("location_id,time,")
)

df = pd.read_csv(raw_path, skiprows=header_index)

# Standardize column names.
df = df.rename(columns={
    "temperature_2m (°C)": "temperature_c",
    "relative_humidity_2m (%)": "relative_humidity_pct",
    "precipitation (mm)": "precipitation_mm",
    "cloud_cover (%)": "cloud_cover_pct",
    "wind_speed_10m (km/h)": "wind_speed_kmh",
})

df["time"] = pd.to_datetime(df["time"])
df = df.sort_values(["location_id", "time"]).reset_index(drop=True)

# Validate hourly records before calculating rolling rainfall.
if df.duplicated(["location_id", "time"]).any():
    raise ValueError("Duplicate location/time records found.")

for location_id, group in df.groupby("location_id"):
    if not group["time"].diff().dropna().eq(pd.Timedelta(hours=1)).all():
        raise ValueError(f"Missing or irregular hourly records at location {location_id}.")

# Rolling totals include the current hour and preceding hours.
for hours in (3, 6, 24):
    df[f"precipitation_sum_{hours}h_mm"] = (
        df.groupby("location_id")["precipitation_mm"]
        .transform(lambda s: s.rolling(hours, min_periods=hours).sum())
    )

output_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(output_path, index=False)

print("Saved:", output_path)
print("Shape:", df.shape)
print("Locations:", df["location_id"].nunique())
print("Date range:", df["time"].min(), "to", df["time"].max())
print("Missing values in rolling features:")
print(df[[
    "precipitation_sum_3h_mm",
    "precipitation_sum_6h_mm",
    "precipitation_sum_24h_mm",
]].isna().sum())
print("All checks passed!")
