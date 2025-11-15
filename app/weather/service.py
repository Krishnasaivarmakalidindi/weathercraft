"""Weather service with caching and typed payloads.

This module wraps OpenWeatherMap current + forecast endpoints, validates
responses using Pydantic, and caches results using a pluggable backend
(file-based by default, optional Redis if configured).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Tuple

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError


DEFAULT_TTL_SECONDS = 600  # 10 minutes


class ServiceError(Exception):
    """Base service error for weather operations."""


class MissingApiKey(ServiceError):
    """Raised when an API key is not configured."""


class CityNotFound(ServiceError):
    """Raised when a city query returns no data."""


class ApiRateLimited(ServiceError):
    """Raised when OpenWeatherMap rate limits our client."""


class NetworkError(ServiceError):
    """Raised when a network error occurs accessing the API."""


# -----------------------------
# Models
# -----------------------------


class WeatherCondition(BaseModel):
    main: str
    description: str
    icon: str  # full URL


class CurrentWeather(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    city: str
    country: str
    temp: float
    feels_like: float = Field(alias="feelsLike")
    humidity: int
    wind: float
    uv: float | None = None
    pressure: float | None = None
    visibility: float | None = None
    condition: WeatherCondition
    dt: int


class ForecastDay(BaseModel):
    date: str  # ISO date (YYYY-MM-DD)
    min: float
    max: float
    precip_chance: int | None = None
    sunrise: str | None = None
    sunset: str | None = None
    condition: WeatherCondition


class WeatherPayload(BaseModel):
    units: str
    current: CurrentWeather
    forecast: list[ForecastDay]
    source: str


# -----------------------------
# Cache backends
# -----------------------------


class CacheBackend:
    """Minimal cache interface."""

    def get(self, key: str) -> Optional[dict[str, Any]]:  # pragma: no cover - interface
        raise NotImplementedError

    def set(self, key: str, value: dict[str, Any]) -> None:  # pragma: no cover - interface
        raise NotImplementedError


@dataclass
class FileCache(CacheBackend):
    root: Path
    ttl_seconds: int = DEFAULT_TTL_SECONDS

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def get(self, key: str) -> Optional[dict[str, Any]]:
        path = self._path_for(key)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            # Expired? Our caller can still use as stale if needed.
            payload["__expired__"] = (time.time() - payload.get("__ts__", 0)) > self.ttl_seconds
            return payload
        except Exception:
            return None

    def set(self, key: str, value: dict[str, Any]) -> None:
        path = self._path_for(key)
        value = {**value, "__ts__": time.time()}
        with path.open("w", encoding="utf-8") as f:
            json.dump(value, f)


@dataclass
class RedisCache(CacheBackend):
    url: str
    ttl_seconds: int = DEFAULT_TTL_SECONDS

    def __post_init__(self) -> None:
        try:
            import redis  # type: ignore
        except Exception as e:  # pragma: no cover - import guard
            raise RuntimeError("redis package is required for RedisCache") from e
        self._redis = redis.from_url(self.url, decode_responses=True)

    def get(self, key: str) -> Optional[dict[str, Any]]:
        raw = self._redis.get(key)
        if not raw:
            return None
        payload = json.loads(raw)
        payload["__expired__"] = (time.time() - payload.get("__ts__", 0)) > self.ttl_seconds
        return payload

    def set(self, key: str, value: dict[str, Any]) -> None:
        value = {**value, "__ts__": time.time()}
        self._redis.setex(key, self.ttl_seconds, json.dumps(value))


# -----------------------------
# Service logic
# -----------------------------


class WeatherService:
    """Fetch and cache weather data from WeatherAPI.com.

    This service uses the current weather and forecast endpoints.
    It aggregates the forecast into the next 3 distinct days.
    """

    BASE_URL = "http://api.weatherapi.com/v1"

    def __init__(
        self,
        api_key: Optional[str],
        cache: Optional[CacheBackend] = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        if not api_key:
            raise MissingApiKey("OPENWEATHER_API_KEY is not configured")
        self.api_key = api_key
        self.cache = cache or FileCache(Path(os.getenv("WEATHER_CACHE_DIR", ".cache/weather")))
        self.ttl = ttl_seconds

    @staticmethod
    def _cache_key(city: str, units: str) -> str:
        return f"weather:{city.strip().lower()}:{units}"

    def get_weather(self, city: str, units: str = "metric") -> Tuple[WeatherPayload, bool]:
        """Return weather payload and a stale flag.

        If the API is unavailable but cached data exists, returns the cached
        data and marks it stale.
        """
        city = city.strip()
        if not city:
            raise CityNotFound("City is required")

        key = self._cache_key(city, units)
        cached = self.cache.get(key)
        if cached and not cached.get("__expired__", False):
            try:
                model = WeatherPayload.model_validate(cached["data"])
                return model, False
            except ValidationError:
                # Ignore corrupt cache entries
                pass

        # Perform fresh fetch
        try:
            current = self._get_current(city, units)
            forecast = self._get_forecast(city, units)
            payload = WeatherPayload(
                units=units,
                current=current,
                forecast=forecast,
                source="live",
            )
            self.cache.set(key, {"data": payload.model_dump(by_alias=True)})
            return payload, False
        except CityNotFound:
            raise
        except ApiRateLimited:
            # Use cache if available
            if cached:
                try:
                    model = WeatherPayload.model_validate(cached["data"])
                    model.source = "cache"
                    return model, True
                except ValidationError:
                    pass
            raise
        except (requests.RequestException, NetworkError):
            # Use stale cache if available
            if cached:
                try:
                    model = WeatherPayload.model_validate(cached["data"])
                    model.source = "cache"
                    return model, True
                except ValidationError:
                    pass
            raise NetworkError("Network error querying weather API")

    # -------------------------
    # Endpoint helpers
    # -------------------------

    def _get_current(self, city: str, units: str) -> CurrentWeather:
        url = f"{self.BASE_URL}/current.json"
        params = {"key": self.api_key, "q": city, "aqi": "yes"}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 400:
            data = r.json()
            if "error" in data and "No matching location" in data["error"].get("message", ""):
                raise CityNotFound(f"City not found: {city}")
        if r.status_code == 429:
            raise ApiRateLimited("Rate limited by WeatherAPI")
        r.raise_for_status()
        data = r.json()
        
        # Convert to our format
        loc = data["location"]
        curr = data["current"]
        temp = curr["temp_c"] if units == "metric" else curr["temp_f"]
        feels = curr["feelslike_c"] if units == "metric" else curr["feelslike_f"]
        wind = curr["wind_kph"] / 3.6 if units == "metric" else curr["wind_mph"]
        icon_url = str(curr["condition"]["icon"]) or ""
        if icon_url.startswith("//"):
            icon_url = "https:" + icon_url
        
        # Optional units-aware fields
        pressure: float | None
        visibility: float | None
        try:
            if units == "metric":
                pressure = float(curr.get("pressure_mb")) if curr.get("pressure_mb") is not None else None
                visibility = float(curr.get("vis_km")) if curr.get("vis_km") is not None else None
            else:
                pressure = float(curr.get("pressure_in")) if curr.get("pressure_in") is not None else None
                visibility = float(curr.get("vis_miles")) if curr.get("vis_miles") is not None else None
        except Exception:
            pressure = None
            visibility = None

        cw = CurrentWeather(
            city=loc["name"],
            country=loc["country"],
            temp=float(temp),
            feelsLike=float(feels),
            humidity=int(curr["humidity"]),
            wind=float(wind),
            uv=float(curr.get("uv")) if curr.get("uv") is not None else None,
            pressure=pressure,
            visibility=visibility,
            condition=WeatherCondition(
                main=curr["condition"]["text"],
                description=curr["condition"]["text"],
                icon=icon_url,
            ),
            dt=int(curr["last_updated_epoch"]),
        )
        return cw

    def _get_forecast(self, city: str, units: str) -> list[ForecastDay]:
        url = f"{self.BASE_URL}/forecast.json"
        params = {"key": self.api_key, "q": city, "days": 3, "aqi": "no", "alerts": "no"}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 400:
            data = r.json()
            if "error" in data and "No matching location" in data["error"].get("message", ""):
                raise CityNotFound(f"City not found: {city}")
        if r.status_code == 429:
            raise ApiRateLimited("Rate limited by WeatherAPI")
        r.raise_for_status()
        data = r.json()
        
        results: list[ForecastDay] = []
        for day_data in data["forecast"]["forecastday"]:
            day = day_data["day"]
            min_temp = day["mintemp_c"] if units == "metric" else day["mintemp_f"]
            max_temp = day["maxtemp_c"] if units == "metric" else day["maxtemp_f"]
            icon_url = str(day["condition"]["icon"]) or ""
            if icon_url.startswith("//"):
                icon_url = "https:" + icon_url
            
            results.append(
                ForecastDay(
                    date=day_data["date"],
                    min=float(min_temp),
                    max=float(max_temp),
                    precip_chance=int(day.get("daily_chance_of_rain") or day.get("daily_chance_of_snow") or 0),
                    sunrise=day_data.get("astro", {}).get("sunrise"),
                    sunset=day_data.get("astro", {}).get("sunset"),
                    condition=WeatherCondition(
                        main=day["condition"]["text"],
                        description=day["condition"]["text"],
                        icon=icon_url,
                    ),
                )
            )
        return results

    # Suggestions API
    def search_locations(self, q: str, limit: int = 7) -> list[dict[str, str]]:
        q = q.strip()
        if not q:
            return []
        url = f"{self.BASE_URL}/search.json"
        params = {"key": self.api_key, "q": q}
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        items = r.json() or []
        results: list[dict[str, str]] = []
        for it in items[:limit]:
            name = it.get("name", "")
            region = it.get("region") or ""
            country = it.get("country") or ""
            label = ", ".join([part for part in [name, region or None, country or None] if part])
            results.append({
                "name": name,
                "region": region,
                "country": country,
                "label": label,
                "lat": str(it.get("lat")),
                "lon": str(it.get("lon")),
            })
        return results


def build_cache_backend_from_env() -> CacheBackend:
    """Factory to build a cache backend based on environment variables."""
    backend = os.getenv("CACHE_BACKEND", "file").lower()
    ttl = int(os.getenv("CACHE_TTL", str(DEFAULT_TTL_SECONDS)))
    if backend == "redis":
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return RedisCache(url=url, ttl_seconds=ttl)
    # Default: file
    cache_dir = Path(os.getenv("WEATHER_CACHE_DIR", ".cache/weather"))
    return FileCache(root=cache_dir, ttl_seconds=ttl)
