from __future__ import annotations

import json
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any

from backend.app.core.errors import DependencyUnavailableException

NORTHEAST_VIEWBOX = "87.5,29.9,97.8,21.5"


class OpenDataService:
    def __init__(self) -> None:
        self._place_cache: OrderedDict[str, tuple[float, list[dict[str, Any]]]] = OrderedDict()
        self._weather_cache: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
        self._place_lock = threading.Lock()
        self._weather_lock = threading.Lock()
        self._last_place_request = 0.0

    @staticmethod
    def _get_json(url: str, user_agent: str) -> Any:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": user_agent,
            },
        )
        try:
            with urlopen(request, timeout=12) as response:
                return json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise DependencyUnavailableException(
                module="open_data",
                message="An OpenStreetMap or weather data provider could not be reached.",
            ) from error

    def search_places(self, query: str) -> list[dict[str, Any]]:
        normalized_query = " ".join(query.split())
        if len(normalized_query) < 3:
            return []

        now = time.monotonic()
        with self._place_lock:
            cached = self._place_cache.get(normalized_query.casefold())
            if cached and cached[0] > now:
                self._place_cache.move_to_end(normalized_query.casefold())
                return cached[1]

            wait_seconds = 1.0 - (now - self._last_place_request)
            if wait_seconds > 0:
                time.sleep(wait_seconds)

            self._last_place_request = time.monotonic()
            query_string = urlencode({
                "q": normalized_query,
                "format": "jsonv2",
                "limit": 5,
                "addressdetails": 1,
                "countrycodes": "in",
                "viewbox": NORTHEAST_VIEWBOX,
                "bounded": 1,
            })
            results = self._get_json(
                f"https://nominatim.openstreetmap.org/search?{query_string}",
                "NER-ResQ/1.0 (Northeast India route planner)",
            )

            places = [
                {
                    "display_name": item["display_name"],
                    "lat": float(item["lat"]),
                    "lng": float(item["lon"]),
                }
                for item in results
                if item.get("display_name") and item.get("lat") and item.get("lon")
            ]
            cache_key = normalized_query.casefold()
            self._place_cache[cache_key] = (time.monotonic() + 3600, places)
            self._place_cache.move_to_end(cache_key)
            while len(self._place_cache) > 256:
                self._place_cache.popitem(last=False)
            return places

    def get_current_weather(self, lat: float, lng: float) -> dict[str, Any]:
        cache_key = (round(lat, 2), round(lng, 2))
        now = time.monotonic()
        with self._weather_lock:
            cached = self._weather_cache.get(cache_key)
            if cached and cached[0] > now:
                return cached[1]

        query_string = urlencode({
            "latitude": lat,
            "longitude": lng,
            "current": (
                "temperature_2m,precipitation,rain,weather_code,"
                "wind_speed_10m,wind_gusts_10m"
            ),
            "wind_speed_unit": "kmh",
            "timezone": "auto",
        })
        payload = self._get_json(
            f"https://api.open-meteo.com/v1/forecast?{query_string}",
            "NER-ResQ/1.0 (Northeast India weather)",
        )
        current = payload.get("current")
        if not isinstance(current, dict):
            raise DependencyUnavailableException(
                module="weather",
                message="The weather provider returned no current conditions.",
            )

        weather = {
            "latitude": float(payload.get("latitude", lat)),
            "longitude": float(payload.get("longitude", lng)),
            "elevation_m": payload.get("elevation"),
            "time": str(current.get("time", "")),
            "temperature_c": float(current.get("temperature_2m", 0.0)),
            "precipitation_mm": float(current.get("precipitation", 0.0)),
            "rain_mm": float(current.get("rain", 0.0)),
            "weather_code": int(current.get("weather_code", 0)),
            "wind_speed_kmh": float(current.get("wind_speed_10m", 0.0)),
            "wind_gusts_kmh": float(current.get("wind_gusts_10m", 0.0)),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "Open-Meteo",
        }
        with self._weather_lock:
            self._weather_cache[cache_key] = (time.monotonic() + 600, weather)
        return weather

    def get_hourly_forecast(self, lat: float, lng: float) -> dict[str, Any]:
        """Fetch hourly weather forecast for a location, cached for 15 minutes."""
        cache_key = ("hourly", round(lat, 2), round(lng, 2))
        now = time.monotonic()
        with self._weather_lock:
            cached = self._weather_cache.get(cache_key)  # type: ignore[arg-type]
            if cached and cached[0] > now:
                return cached[1]

        query_string = urlencode({
            "latitude": lat,
            "longitude": lng,
            "hourly": (
                "temperature_2m,precipitation,rain,weather_code,"
                "wind_speed_10m,wind_gusts_10m"
            ),
            "wind_speed_unit": "kmh",
            "timezone": "auto",
            "forecast_days": 2,
        })
        payload = self._get_json(
            f"https://api.open-meteo.com/v1/forecast?{query_string}",
            "NER-ResQ/1.0 (Northeast India weather forecast)",
        )
        hourly = payload.get("hourly")
        if not isinstance(hourly, dict) or "time" not in hourly:
            raise DependencyUnavailableException(
                module="weather",
                message="The weather provider returned no hourly forecast.",
            )

        with self._weather_lock:
            self._weather_cache[cache_key] = (time.monotonic() + 900, hourly)  # type: ignore[index]
        return hourly

    def get_weather_for_arrival_time(
        self, lat: float, lng: float, arrival_time: datetime
    ) -> dict[str, Any]:
        """
        Retrieves weather condition matched to the target time-of-arrival (ToA).
        Finds the closest forecast hour from Open-Meteo's hourly array.
        """
        try:
            hourly = self.get_hourly_forecast(lat, lng)
            times = hourly.get("time", [])
            if not times:
                return self.get_current_weather(lat, lng)

            # Match arrival_time with hourly times (ISO strings like "2026-11-21T05:00")
            target_str = arrival_time.strftime("%Y-%m-%dT%H:00")
            best_idx = 0
            if target_str in times:
                best_idx = times.index(target_str)
            else:
                # Find closest timestamp
                best_diff = float("inf")
                target_ts = arrival_time.timestamp()
                for idx, t_str in enumerate(times):
                    try:
                        # parse ISO time
                        t_dt = datetime.fromisoformat(t_str)
                        if t_dt.tzinfo is None and arrival_time.tzinfo is not None:
                            t_dt = t_dt.replace(tzinfo=arrival_time.tzinfo)
                        diff = abs(t_dt.timestamp() - target_ts)
                        if diff < best_diff:
                            best_diff = diff
                            best_idx = idx
                    except Exception:
                        continue

            temps = hourly.get("temperature_2m", [])
            precips = hourly.get("precipitation", [])
            rains = hourly.get("rain", [])
            codes = hourly.get("weather_code", [])
            wind_speeds = hourly.get("wind_speed_10m", [])
            wind_gusts = hourly.get("wind_gusts_10m", [])

            return {
                "latitude": lat,
                "longitude": lng,
                "time": str(times[best_idx]) if best_idx < len(times) else "",
                "temperature_c": float(temps[best_idx]) if best_idx < len(temps) else 0.0,
                "precipitation_mm": float(precips[best_idx]) if best_idx < len(precips) else 0.0,
                "rain_mm": float(rains[best_idx]) if best_idx < len(rains) else 0.0,
                "weather_code": int(codes[best_idx]) if best_idx < len(codes) else 0,
                "wind_speed_kmh": float(wind_speeds[best_idx]) if best_idx < len(wind_speeds) else 0.0,
                "wind_gusts_kmh": float(wind_gusts[best_idx]) if best_idx < len(wind_gusts) else 0.0,
                "source": "Open-Meteo Hourly Forecast (ToA)",
            }
        except Exception:
            return self.get_current_weather(lat, lng)


open_data_service = OpenDataService()
