from pathlib import Path

import rasterio
from rasterio.merge import merge


# Input DEM tiles
input_dir = Path("ml/data/raw/terrain/copernicus")

# Output location
output_dir = Path("ml/data/processed/terrain")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "elevation_mosaic.tif"


# Find all DEM files
dem_files = list(input_dir.glob("*.tif"))

if not dem_files:
    raise FileNotFoundError("No DEM .tif files found!")

print(f"Found {len(dem_files)} DEM tiles.")

# Open all tiles
src_files = [rasterio.open(file) for file in dem_files]

try:
    # Merge tiles
    mosaic, transform = merge(src_files)

    # Copy metadata from first tile
    metadata = src_files[0].meta.copy()

    metadata.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": transform,
        "compress": "deflate"
    })

    # Save mosaic
    with rasterio.open(output_file, "w", **metadata) as dest:
        dest.write(mosaic)

finally:
    for src in src_files:
        src.close()

print(f"Mosaic created successfully:")
print(output_file)