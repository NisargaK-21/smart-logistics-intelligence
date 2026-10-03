
import pandas as pd
from pathlib import Path

raw_path = Path("ml/data/raw/weather/weather.csv")
output_path = Path("ml/data/processed/weather_locations.csv")

locations = pd.read_csv(raw_path, nrows=16)

output_path.parent.mkdir(parents=True, exist_ok=True)
locations.to_csv(output_path, index=False)

print("Location metadata saved to:", output_path)
print("Number of locations:", len(locations))
print(locations.head())
