"""Weather blueprint routes: UI pages and JSON API."""
from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, render_template, request

from . import weather_bp
from .service import (
    WeatherService,
    build_cache_backend_from_env,
    ApiRateLimited,
    CityNotFound,
    MissingApiKey,
    NetworkError,
)


@weather_bp.get("/")
def index():
    """Homepage with search UI and animated hero."""
    return render_template("index.html", page_title="WeatherCraft")


@weather_bp.get("/about")
def about():
    """Simple about/feature page."""
    return render_template("about.html", page_title="About · WeatherCraft")


@weather_bp.get("/api/weather")
def api_weather():
    """Return compact JSON payload for a city and units.

    Query params:
      - city: required
      - units: optional (metric|imperial), default metric
    """
    city = (request.args.get("city") or "").strip()
    units = (request.args.get("units") or "metric").strip()

    try:
        api_key = current_app.config.get("WEATHER_API_KEY")
        cache = build_cache_backend_from_env()
        svc = WeatherService(api_key=api_key, cache=cache, ttl_seconds=int(current_app.config.get("CACHE_TTL", 600)))
        payload, stale = svc.get_weather(city, units=units)
        return jsonify({"ok": True, "stale": stale, "data": payload.model_dump()}), 200
    except MissingApiKey:
        return jsonify({"ok": False, "error": "Missing API key"}), 500
    except CityNotFound:
        return jsonify({"ok": False, "error": "City not found"}), 404
    except ApiRateLimited:
        return jsonify({"ok": False, "error": "Rate limited"}), 429
    except NetworkError:
        return jsonify({"ok": False, "error": "Network error"}), 503
    except Exception:
        return jsonify({"ok": False, "error": "Unexpected server error"}), 500


@weather_bp.get("/api/suggest")
def api_suggest():
    """Return location suggestions for autocomplete.

    Query params:
      - q: required partial search string
    """
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"ok": True, "data": []})
    try:
        api_key = current_app.config.get("WEATHER_API_KEY")
        cache = build_cache_backend_from_env()
        svc = WeatherService(api_key=api_key, cache=cache, ttl_seconds=int(current_app.config.get("CACHE_TTL", 600)))
        items = svc.search_locations(q)
        return jsonify({"ok": True, "data": items}), 200
    except Exception:
        return jsonify({"ok": True, "data": []}), 200
