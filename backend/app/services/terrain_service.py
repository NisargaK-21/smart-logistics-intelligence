"""Terrain raster querying service for elevation, slope, and ruggedness from DEM tiles.

Provides on-demand spatial querying of Digital Elevation Model (DEM) tiles (e.g., Copernicus
GLO-30) at native pixel resolution (~30m / 1 arc-second).
"""

from __future__ import annotations

import logging
import math
import threading
from pathlib import Path
from typing import Any

import numpy as np

try:
    import rasterio
    from rasterio.transform import rowcol
except ImportError:  # pragma: no cover
    rasterio = None
    rowcol = None

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

EARTH_METERS_PER_DEGREE = 111_320.0


class TileMetadata:
    """Metadata and open handle cache for a single DEM tile."""

    def __init__(self, path: Path):
        self.path = path
        self.filename = path.name
        self.min_lon: float = 0.0
        self.min_lat: float = 0.0
        self.max_lon: float = 0.0
        self.max_lat: float = 0.0
        self.width: int = 0
        self.height: int = 0
        self.res_x_deg: float = 0.0
        self.res_y_deg: float = 0.0
        self.nodata: float | None = None
        self.transform = None
        self.valid: bool = False
        self._load_metadata()

    def _load_metadata(self) -> None:
        if rasterio is None:
            logger.warning("rasterio is not installed; DEM raster querying disabled.")
            return
        try:
            with rasterio.open(self.path) as src:
                self.bounds = src.bounds
                self.min_lon = float(src.bounds.left)
                self.min_lat = float(src.bounds.bottom)
                self.max_lon = float(src.bounds.right)
                self.max_lat = float(src.bounds.top)
                self.width = int(src.width)
                self.height = int(src.height)
                self.transform = src.transform
                self.res_x_deg = abs(float(src.transform.a))
                self.res_y_deg = abs(float(src.transform.e))
                self.nodata = src.nodata
                self.valid = True
        except Exception as exc:
            logger.warning("Failed to read DEM tile metadata for %s: %s", self.path, exc)
            self.valid = False

    def contains(self, lon: float, lat: float) -> bool:
        if not self.valid:
            return False
        return self.min_lon <= lon <= self.max_lon and self.min_lat <= lat <= self.max_lat


class TerrainService:
    """Lightweight spatial index and on-demand raster querying for DEM tiles."""

    def __init__(self, terrain_dir: str | Path | None = None):
        configured_dir = terrain_dir or getattr(settings, "TERRAIN_DATA_DIR", None)
        if configured_dir:
            self.terrain_dir = Path(configured_dir)
        else:
            self.terrain_dir = (
                Path(__file__).resolve().parents[3] / "ml" / "data" / "processed" / "terrain"
            )

        self._tiles: list[TileMetadata] = []
        self._tile_grid: dict[tuple[int, int], TileMetadata] = {}
        self._open_datasets: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._indexed: bool = False

    def _ensure_indexed(self) -> None:
        if self._indexed:
            return
        with self._lock:
            if self._indexed:
                return
            self._index_tiles()
            self._indexed = True

    def _index_tiles(self) -> None:
        self._tiles.clear()
        self._tile_grid.clear()
        if not self.terrain_dir.exists() or not self.terrain_dir.is_dir():
            logger.info("Terrain directory does not exist: %s", self.terrain_dir)
            return

        for ext in ("*.tif", "*.tiff"):
            for tile_path in sorted(self.terrain_dir.glob(ext)):
                tile = TileMetadata(tile_path)
                if tile.valid:
                    self._tiles.append(tile)
                    lat_key = int(math.floor(tile.min_lat))
                    lon_key = int(math.floor(tile.min_lon))
                    self._tile_grid[(lat_key, lon_key)] = tile

        logger.info(
            "TerrainService indexed %d DEM tiles from %s", len(self._tiles), self.terrain_dir
        )

    def refresh_index(self) -> None:
        """Force re-scanning the terrain directory."""
        with self._lock:
            self._close_all()
            self._index_tiles()
            self._indexed = True

    def _get_dataset(self, tile: TileMetadata):
        key = str(tile.path)
        ds = self._open_datasets.get(key)
        if ds is None or ds.closed:
            ds = rasterio.open(tile.path)
            self._open_datasets[key] = ds
        return ds

    def _close_all(self) -> None:
        for ds in self._open_datasets.values():
            try:
                if not ds.closed:
                    ds.close()
            except Exception:
                pass
        self._open_datasets.clear()

    def get_tile_for_point(self, lon: float, lat: float) -> TileMetadata | None:
        """Find the tile covering (lon, lat) using grid lookup or bounds scan."""
        self._ensure_indexed()
        if not self._tiles:
            return None

        # 1. Fast grid check (1-degree floor lookup)
        lat_key = int(math.floor(lat))
        lon_key = int(math.floor(lon))
        tile = self._tile_grid.get((lat_key, lon_key))
        if tile and tile.contains(lon, lat):
            return tile

        # 2. General bounds scan
        for t in self._tiles:
            if t.contains(lon, lat):
                return t

        return None

    def sample_point(self, lon: float, lat: float) -> dict[str, float | None]:
        """Sample elevation (m), slope (deg), and ruggedness for a single point.

        Returns:
            dict with keys 'elevation_m', 'slope_deg', 'ruggedness'.
            Values are None if out of coverage, missing tile, or invalid nodata.
        """
        if rasterio is None or not getattr(settings, "TERRAIN_ENABLED", True):
            return {"elevation_m": None, "slope_deg": None, "ruggedness": None}

        tile = self.get_tile_for_point(lon, lat)
        if tile is None or not tile.valid:
            return {"elevation_m": None, "slope_deg": None, "ruggedness": None}

        try:
            with self._lock:
                ds = self._get_dataset(tile)
                r, c = rowcol(tile.transform, lon, lat)

                # Ensure pixel is inside raster with margin for 3x3 window
                if r < 1 or r >= tile.height - 1 or c < 1 or c >= tile.width - 1:
                    # Point at edge: sample single pixel without slope/ruggedness window
                    if 0 <= r < tile.height and 0 <= c < tile.width:
                        w_single = ds.read(1, window=((r, r + 1), (c, c + 1)))
                        elev = float(w_single[0, 0])
                        if self._is_valid_elevation(elev, tile.nodata):
                            return {
                                "elevation_m": round(elev, 1),
                                "slope_deg": 0.0,
                                "ruggedness": 0.0,
                            }
                    return {"elevation_m": None, "slope_deg": None, "ruggedness": None}

                # Read 3x3 window around (r, c)
                window = ds.read(1, window=((r - 1, r + 2), (c - 1, c + 2))).astype(np.float32)

            center_elev = float(window[1, 1])
            if not self._is_valid_elevation(center_elev, tile.nodata):
                return {"elevation_m": None, "slope_deg": None, "ruggedness": None}

            # Check for invalid / nodata in 3x3 window; replace with center if partial
            nodata_mask = (window == tile.nodata) if tile.nodata is not None else np.isnan(window)
            nodata_mask = nodata_mask | (window < -500.0) | (window > 9000.0)
            if np.all(nodata_mask):
                return {"elevation_m": None, "slope_deg": None, "ruggedness": None}
            if np.any(nodata_mask):
                window[nodata_mask] = center_elev

            # Ground distances per pixel in meters
            dx = tile.res_x_deg * EARTH_METERS_PER_DEGREE * math.cos(math.radians(lat))
            dy = tile.res_y_deg * EARTH_METERS_PER_DEGREE

            if dx <= 0 or dy <= 0:
                return {
                    "elevation_m": round(center_elev, 1),
                    "slope_deg": 0.0,
                    "ruggedness": 0.0,
                }

            # Horn's method for surface slope (3x3 kernel)
            dz_dx = (
                (window[0, 2] + 2.0 * window[1, 2] + window[2, 2])
                - (window[0, 0] + 2.0 * window[1, 0] + window[2, 0])
            ) / (8.0 * dx)

            dz_dy = (
                (window[2, 0] + 2.0 * window[2, 1] + window[2, 2])
                - (window[0, 0] + 2.0 * window[0, 1] + window[0, 2])
            ) / (8.0 * dy)

            slope_deg = math.degrees(math.atan(math.sqrt(dz_dx**2 + dz_dy**2)))

            # Ruggedness: root-mean-square elevation difference in 3x3 neighborhood
            ruggedness = float(np.sqrt(np.mean((window - center_elev) ** 2)))

            return {
                "elevation_m": round(center_elev, 1),
                "slope_deg": round(slope_deg, 2),
                "ruggedness": round(ruggedness, 2),
            }
        except Exception as exc:
            logger.warning("Error sampling terrain at (%f, %f): %s", lon, lat, exc)
            return {"elevation_m": None, "slope_deg": None, "ruggedness": None}

    @staticmethod
    def _is_valid_elevation(value: float, nodata: float | None) -> bool:
        if math.isnan(value) or math.isinf(value):
            return False
        if nodata is not None and value == nodata:
            return False
        # Physically plausible terrestrial elevation range (-500m to 8900m)
        return -500.0 <= value <= 8900.0

    def query_linestring(
        self, coordinates: list[list[float]], max_step_m: float = 100.0
    ) -> dict[str, Any]:
        """Query terrain attributes for a route segment linestring.

        Samples points along the linestring.
        If ANY point is missing or out of coverage, terrain_available is False
        and values are None to avoid silently masking missing data.
        """
        if not coordinates or len(coordinates) < 2:
            return {
                "terrain_available": False,
                "elevation_m": None,
                "slope_deg": None,
                "ruggedness": None,
            }

        # Subdivide segment linestring into evenly spaced sample coordinates
        sampled_points = self._interpolate_linestring(coordinates, max_step_m=max_step_m)
        if not sampled_points:
            return {
                "terrain_available": False,
                "elevation_m": None,
                "slope_deg": None,
                "ruggedness": None,
            }

        elevations: list[float] = []
        slopes: list[float] = []
        ruggednesses: list[float] = []

        for lon, lat in sampled_points:
            sample = self.sample_point(lon, lat)
            elev = sample.get("elevation_m")
            slope = sample.get("slope_deg")
            rugg = sample.get("ruggedness")

            # Strict coverage requirement: if any point lacks valid terrain, fail safe
            if elev is None or slope is None or rugg is None:
                return {
                    "terrain_available": False,
                    "elevation_m": None,
                    "slope_deg": None,
                    "ruggedness": None,
                }

            elevations.append(elev)
            slopes.append(slope)
            ruggednesses.append(rugg)

        return {
            "terrain_available": True,
            "elevation_m": round(float(np.mean(elevations)), 1),
            "slope_deg": round(float(np.mean(slopes)), 2),
            "ruggedness": round(float(np.mean(ruggednesses)), 2),
            "max_slope_deg": round(float(np.max(slopes)), 2),
            "min_elevation_m": round(float(np.min(elevations)), 1),
            "max_elevation_m": round(float(np.max(elevations)), 1),
        }

    @staticmethod
    def _interpolate_linestring(
        coordinates: list[list[float]], max_step_m: float = 100.0
    ) -> list[tuple[float, float]]:
        """Evenly sample points along a polyline at native spacing."""
        points: list[tuple[float, float]] = []
        for i in range(len(coordinates) - 1):
            p1 = coordinates[i]
            p2 = coordinates[i + 1]
            lon1, lat1 = float(p1[0]), float(p1[1])
            lon2, lat2 = float(p2[0]), float(p2[1])

            # Approximate segment distance in meters
            mean_lat = (lat1 + lat2) / 2.0
            dx = (lon2 - lon1) * EARTH_METERS_PER_DEGREE * math.cos(math.radians(mean_lat))
            dy = (lat2 - lat1) * EARTH_METERS_PER_DEGREE
            dist_m = math.sqrt(dx**2 + dy**2)

            steps = max(1, int(math.ceil(dist_m / max_step_m)))
            for s in range(steps):
                frac = s / float(steps)
                points.append((lon1 + frac * (lon2 - lon1), lat1 + frac * (lat2 - lat1)))

        # Add the final endpoint
        points.append((float(coordinates[-1][0]), float(coordinates[-1][1])))
        return points


terrain_service = TerrainService()
