
import pandas as pd

file_path = "ml/data/raw/weather/weather.csv"

# Skip the location metadata section and read the hourly weather table
df = pd.read_csv(file_path, skiprows=18)

print("Dataset shape:", df.shape)
print("\nColumn names:")
print(df.columns.tolist())
print("\nFirst 5 rows:")
print(df.head())
print("\nMissing values:")
print(df.isnull().sum())
print("\nUnique locations:", df["location_id"].nunique())
df["time"] = pd.to_datetime(df["time"])
print("\nDate range:")
print("Start:", df["time"].min())
print("End:", df["time"].max())


print("\nRecords per location:")
print(df.groupby("location_id").size())

print("\nDuplicate rows:", df.duplicated().sum())

print("\nDuplicate location-time pairs:",
      df.duplicated(subset=["location_id", "time"]).sum())

print("\nTime gaps by location:")
for location_id, group in df.groupby("location_id"):
    times = group["time"].sort_values()
    gaps = times.diff().dropna()
    missing_hours = int((gaps / pd.Timedelta(hours=1) - 1).clip(lower=0).sum())
    print(f"Location {location_id}: {missing_hours} missing hours")



# Prepare a processed copy for the ML pipeline
processed = df.copy()

processed = processed.rename(columns={
    "temperature_2m (°C)": "temperature_c",
    "relative_humidity_2m (%)": "relative_humidity_pct",
    "precipitation (mm)": "precipitation_mm",
    "cloud_cover (%)": "cloud_cover_pct",
    "wind_speed_10m (km/h)": "wind_speed_kmh",
})

processed["time"] = pd.to_datetime(processed["time"])

output_path = "ml/data/processed/weather_processed.csv"
processed.to_csv(output_path, index=False)

print("\nProcessed dataset saved to:", output_path)
print("Processed shape:", processed.shape)
print("Processed columns:", processed.columns.tolist())



# Summary statistics for weather features
weather_columns = [
    "temperature_c",
    "relative_humidity_pct",
    "precipitation_mm",
    "cloud_cover_pct",
    "wind_speed_kmh",
]

print("\nWeather Summary Statistics:")
print(processed[weather_columns].describe())

print("\nNegative precipitation values:")
print((processed["precipitation_mm"] < 0).sum())

print("\nNegative wind speed values:")
print((processed["wind_speed_kmh"] < 0).sum())

print("\nRelative humidity outside 0–100%:")
print(
    (
        (processed["relative_humidity_pct"] < 0)
        | (processed["relative_humidity_pct"] > 100)
    ).sum()
)

print("\nCloud cover outside 0–100%:")
print(
    (
        (processed["cloud_cover_pct"] < 0)
        | (processed["cloud_cover_pct"] > 100)
    ).sum()
)
