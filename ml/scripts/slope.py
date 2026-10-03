from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import xy


input_file = Path("ml/data/processed/terrain/elevation_mosaic.tif")
output_file = Path("ml/data/processed/terrain/slope.tif")

with rasterio.open(input_file) as src:
    elevation = src.read(1).astype("float32")
    profile = src.profile
    transform = src.transform

    # Approximate metres-per-pixel using latitude.
    # DEM is in geographic coordinates (EPSG:4326).
    height, width = elevation.shape

    center_lat = (transform.f + transform.e * height / 2)

    meters_per_degree_lat = 111_320
    meters_per_degree_lon = 111_320 * np.cos(np.radians(center_lat))

    x_res = abs(transform.a) * meters_per_degree_lon
    y_res = abs(transform.e) * meters_per_degree_lat

    # Calculate elevation gradients
    dz_dy, dz_dx = np.gradient(elevation, y_res, x_res)

    # Slope in degrees
    slope = np.degrees(
        np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    ).astype("float32")

    profile.update(
        dtype="float32",
        count=1,
        compress="deflate",
        nodata=-9999
    )

    with rasterio.open(output_file, "w", **profile) as dst:
        dst.write(slope, 1)

print(f"Slope created: {output_file}")