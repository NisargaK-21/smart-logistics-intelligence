"""Bootstrap and download Copernicus DEM GLO-30 raster tiles for terrain querying.

Dataset Provenance:
- Source: Copernicus Digital Elevation Model (GLO-30 Public), European Space Agency (ESA)
- License: Copernicus WorldDEM-30 Open Access Licence (free and open data)
- Native Resolution: 1 arc-second (~30 meters per pixel, 3600 x 3600 per 1° tile)
- CRS: EPSG:4326 (WGS84 geographic coordinates)
- Public AWS S3 Storage: https://copernicus-dem-30m.s3.amazonaws.com/
- URL Convention:
    https://copernicus-dem-30m.s3.amazonaws.com/{tile}/{tile}.tif
    where {tile} = Copernicus_DSM_COG_10_{northing}_00_{easting}_00_DEM
    e.g., Copernicus_DSM_COG_10_N26_00_E091_00_DEM
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import rasterio
except ImportError:  # pragma: no cover
    rasterio = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

S3_BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed" / "terrain"

# Default demonstration / test tile covering the Guwahati corridor
DEFAULT_TEST_TILES = [
    "Copernicus_DSM_COG_10_N26_00_E091_00_DEM",
]


def format_tile_name(lat: int, lon: int) -> str:
    """Format the 1-degree Copernicus DEM GLO-30 tile name from integer coordinates."""
    northing = f"N{abs(lat):02d}" if lat >= 0 else f"S{abs(lat):02d}"
    easting = f"E{abs(lon):03d}" if lon >= 0 else f"W{abs(lon):03d}"
    return f"Copernicus_DSM_COG_10_{northing}_00_{easting}_00_DEM"


def get_tile_url(tile_name: str) -> str:
    return f"{S3_BASE_URL}/{tile_name}/{tile_name}.tif"


def verify_tile(file_path: Path) -> bool:
    """Verify that a tile file exists, is non-empty, and can be opened by rasterio."""
    if not file_path.exists() or file_path.stat().st_size < 1024:
        return False
    if rasterio is None:
        return True
    try:
        with rasterio.open(file_path) as src:
            return src.width > 0 and src.height > 0
    except Exception as exc:
        logger.warning("Corrupt or invalid tile %s: %s", file_path, exc)
        return False


def download_tile(
    tile_name: str,
    output_dir: Path,
    max_retries: int = 3,
    timeout: float = 60.0,
) -> Path | None:
    """Download a single Copernicus DEM tile if missing or invalid."""
    output_dir.mkdir(parents=True, exist_ok=True)
    target_file = output_dir / f"{tile_name}.tif"

    if verify_tile(target_file):
        logger.info("Tile already exists and verified: %s", target_file.name)
        return target_file

    url = get_tile_url(tile_name)
    logger.info("Downloading DEM tile from: %s", url)

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SmartLogistics-TerrainBootstrap/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read()
                temp_file = target_file.with_suffix(".tmp")
                with open(temp_file, "wb") as f:
                    f.write(content)
                temp_file.replace(target_file)

            if verify_tile(target_file):
                logger.info(
                    "Successfully downloaded and verified %s (%d bytes)",
                    target_file.name,
                    target_file.stat().st_size,
                )
                return target_file
            else:
                logger.error("Downloaded file %s failed validation", target_file.name)
                target_file.unlink(missing_ok=True)
        except urllib.error.HTTPError as http_err:
            if http_err.code == 404:
                logger.warning("Tile %s does not exist on server (HTTP 404).", tile_name)
                return None
            logger.warning("HTTP error on attempt %d: %s", attempt, http_err)
        except Exception as exc:
            logger.warning("Download error on attempt %d: %s", attempt, exc)

        if attempt < max_retries:
            time.sleep(2.0 * attempt)

    logger.error("Failed to download tile %s after %d attempts.", tile_name, max_retries)
    return None


def tiles_for_bbox(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> list[str]:
    """Generate the list of tile names covering a bounding box."""
    lat_start = int(math.floor(min_lat))
    lat_end = int(math.floor(max_lat))
    lon_start = int(math.floor(min_lon))
    lon_end = int(math.floor(max_lon))

    tiles: list[str] = []
    for lat in range(lat_start, lat_end + 1):
        for lon in range(lon_start, lon_end + 1):
            tiles.append(format_tile_name(lat, lon))
    return tiles


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap Copernicus DEM GLO-30 tiles for Smart Logistics terrain index."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Target directory for downloaded DEM GeoTIFF files",
    )
    parser.add_argument(
        "--tile",
        type=str,
        default=None,
        help="Specific tile name to download (e.g. Copernicus_DSM_COG_10_N26_00_E091_00_DEM)",
    )
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        help="Bounding box to download tiles for (e.g. 91.0 26.0 92.0 27.0)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing tiles without downloading missing ones",
    )

    args = parser.parse_args()

    target_tiles: list[str] = []
    if args.tile:
        target_tiles = [args.tile]
    elif args.bbox:
        target_tiles = tiles_for_bbox(*args.bbox)
    else:
        target_tiles = DEFAULT_TEST_TILES

    logger.info("Target tiles to bootstrap: %s", target_tiles)
    success = True

    for tile in target_tiles:
        file_path = args.output_dir / f"{tile}.tif"
        if args.verify_only:
            valid = verify_tile(file_path)
            status = "VALID" if valid else "MISSING/INVALID"
            logger.info("Verification of %s: %s", tile, status)
            if not valid:
                success = False
        else:
            result = download_tile(tile, args.output_dir)
            if result is None:
                success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
