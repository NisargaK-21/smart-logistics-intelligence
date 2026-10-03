from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import generic_filter


input_file = Path("ml/data/processed/terrain/elevation_mosaic.tif")
output_file = Path("ml/data/processed/terrain/ruggedness.tif")


def ruggedness(window):
    center = window[len(window) // 2]
    return np.sqrt(np.mean((window - center) ** 2))


with rasterio.open(input_file) as src:
    elevation = src.read(1).astype("float32")
    profile = src.profile

    # 3x3 neighborhood terrain roughness
    roughness = generic_filter(
        elevation,
        ruggedness,
        size=3,
        mode="nearest"
    ).astype("float32")

    profile.update(
        dtype="float32",
        count=1,
        compress="deflate",
        nodata=-9999
    )

    with rasterio.open(output_file, "w", **profile) as dst:
        dst.write(roughness, 1)

print(f"Ruggedness created: {output_file}")