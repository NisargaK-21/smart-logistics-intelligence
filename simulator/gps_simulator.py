import json
import time
from pathlib import Path

import pandas as pd


INPUT_FILE = Path("ml/data/processed/gps/vehicle_gps_processed.csv")
OUTPUT_DIR = Path("simulator/output")
OUTPUT_FILE = OUTPUT_DIR / "gps_live.jsonl"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT_FILE)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(["timestamp", "vehicle_id"])

print("🚚 GPS Simulator Started")
print(f"Vehicles: {df['vehicle_id'].nunique()}")
print("Press Ctrl+C to stop.\n")

try:
    with open(OUTPUT_FILE, "a", encoding="utf-8") as file:

        for timestamp, frame in df.groupby("timestamp"):

            for _, vehicle in frame.iterrows():

                gps_data = {
                    "vehicle_id": int(vehicle["vehicle_id"]),
                    "timestamp": timestamp.isoformat(),
                    "latitude": float(vehicle["latitude"]),
                    "longitude": float(vehicle["longitude"]),
                    "speed_kmh": float(vehicle["speed_kmh"]),
                }

                # Write live GPS record
                file.write(json.dumps(gps_data) + "\n")
                file.flush()

                print(
                    f"🚚 V{gps_data['vehicle_id']} | "
                    f"Lat: {gps_data['latitude']:.6f} | "
                    f"Lon: {gps_data['longitude']:.6f} | "
                    f"Speed: {gps_data['speed_kmh']} km/h"
                )

            print("-" * 80)

            # 1 simulated minute = 1 real second
            time.sleep(1)

except KeyboardInterrupt:
    print("\nGPS simulator stopped.")