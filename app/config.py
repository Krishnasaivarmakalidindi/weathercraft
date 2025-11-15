"""Application configuration for WeatherCraft.

Provides Development and Production settings loaded from environment.
"""
from __future__ import annotations

import os


class Config:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret")
    WEATHER_API_KEY: str | None = os.getenv("WEATHER_API_KEY")

    # Caching
    CACHE_BACKEND: str = os.getenv("CACHE_BACKEND", "file")  # file|redis
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "600"))
    WEATHER_CACHE_DIR: str = os.getenv("WEATHER_CACHE_DIR", ".cache/weather")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Flask tweaks
    JSONIFY_PRETTYPRINT_REGULAR: bool = False
    TEMPLATES_AUTO_RELOAD: bool = True


class DevelopmentConfig(Config):
    DEBUG: bool = True


class ProductionConfig(Config):
    DEBUG: bool = False


def get_config(name: str) -> type[Config]:
    """Map a name to a config class."""
    key = (name or "development").lower()
    if key.startswith("prod"):
        return ProductionConfig
    return DevelopmentConfig
