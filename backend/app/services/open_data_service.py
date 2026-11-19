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


open_data_service = OpenDataService()
