from pathlib import Path

import numpy as np
import pandas as pd
import rasterio


terrain_dir = Path("ml/data/processed/terrain")
output_file = Path("ml/data/final/terrain_features.csv")

elevation_file = terrain_dir / "elevation_mosaic.tif"
slope_file = terrain_dir / "slope.tif"
aspect_file = terrain_dir / "aspect.tif"
ruggedness_file = terrain_dir / "ruggedness.tif"

# Sample approximately every 10th pixel.
# This keeps the CSV manageable while preserving spatial coverage.
SAMPLE_STEP = 10

with rasterio.open(elevation_file) as elevation_src, \
     rasterio.open(slope_file) as slope_src, \
     rasterio.open(aspect_file) as aspect_src, \
     rasterio.open(ruggedness_file) as ruggedness_src:

    elevation = elevation_src.read(1)
    slope = slope_src.read(1)
    aspect = aspect_src.read(1)
    ruggedness = ruggedness_src.read(1)

    transform = elevation_src.transform

    # Sample pixels
    rows = np.arange(0, elevation.shape[0], SAMPLE_STEP)
    cols = np.arange(0, elevation.shape[1], SAMPLE_STEP)

    row_grid, col_grid = np.meshgrid(rows, cols, indexing="ij")

    elevation_values = elevation[row_grid, col_grid]
    slope_values = slope[row_grid, col_grid]
    aspect_values = aspect[row_grid, col_grid]
    ruggedness_values = ruggedness[row_grid, col_grid]

    # Convert sampled pixels to coordinates
    longitude = transform.c + col_grid * transform.a
    latitude = transform.f + row_grid * transform.e

    df = pd.DataFrame({
        "latitude": latitude.ravel(),
        "longitude": longitude.ravel(),
        "elevation_m": elevation_values.ravel(),
        "slope_deg": slope_values.ravel(),
        "aspect_deg": aspect_values.ravel(),
        "ruggedness": ruggedness_values.ravel(),
    })
        
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()
    
    # Remove background / invalid elevation pixels
    df = df[
        (df["elevation_m"] > 0) &
        (df["slope_deg"] >= 0) &
        (df["ruggedness"] >= 0)
    ].copy()
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    
    print("Terrain CSV created successfully!")
    print(f"Output: {output_file}")
    print(f"Rows: {len(df):,}")
    print(df.head())