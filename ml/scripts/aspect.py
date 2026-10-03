from pathlib import Path

import numpy as np
import rasterio


input_file = Path("ml/data/processed/terrain/elevation_mosaic.tif")
output_file = Path("ml/data/processed/terrain/aspect.tif")

with rasterio.open(input_file) as src:
    elevation = src.read(1).astype("float32")
    profile = src.profile
    transform = src.transform

    height, width = elevation.shape

    center_lat = transform.f + transform.e * height / 2

    meters_per_degree_lat = 111_320
    meters_per_degree_lon = 111_320 * np.cos(np.radians(center_lat))

    x_res = abs(transform.a) * meters_per_degree_lon
    y_res = abs(transform.e) * meters_per_degree_lat

    dz_dy, dz_dx = np.gradient(elevation, y_res, x_res)

    # Calculate aspect
    aspect = np.degrees(np.arctan2(-dz_dx, dz_dy))

    # Convert to 0–360 degrees
    aspect = (aspect + 360) % 360

    aspect = aspect.astype("float32")

    profile.update(
        dtype="float32",
        count=1,
        compress="deflate",
        nodata=-9999
    )

    with rasterio.open(output_file, "w", **profile) as dst:
        dst.write(aspect, 1)

print(f"Aspect created: {output_file}")