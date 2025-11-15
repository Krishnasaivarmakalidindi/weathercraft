from __future__ import annotations

import json
from pathlib import Path

import pytest
import responses

from app.weather.service import FileCache, WeatherService


@pytest.fixture()
def tmp_cache(tmp_path: Path) -> FileCache:
    return FileCache(root=tmp_path / ".cache")


def _mock_current(city: str = "London", units: str = "metric") -> dict:
    return {
        "name": city,
        "dt": 1700000000,
        "sys": {"country": "GB"},
        "main": {"temp": 10.5, "feels_like": 8.0, "humidity": 75},
        "wind": {"speed": 3.2},
        "weather": [{"main": "Clouds", "description": "broken clouds", "icon": "04d"}],
    }


def _mock_forecast(units: str = "metric") -> dict:
    base = 1700000000
    items = []
    # 3 days, every 6 hours
    for i in range(1, 4 * 4 + 1):
        items.append(
            {
                "dt": base + i * 6 * 3600,
                "main": {"temp": 7.0 + (i % 5)},
                "weather": [{"main": "Clouds", "description": "scattered", "icon": "03d"}],
            }
        )
    return {"list": items}


@responses.activate
def test_get_weather_success(tmp_cache: FileCache) -> None:
    svc = WeatherService(api_key="test", cache=tmp_cache)

    responses.add(
        responses.GET,
        f"{svc.BASE_URL}/weather",
        json=_mock_current(),
        status=200,
    )
    responses.add(
        responses.GET,
        f"{svc.BASE_URL}/forecast",
        json=_mock_forecast(),
        status=200,
    )

    payload, stale = svc.get_weather("London", units="metric")
    assert not stale
    assert payload.current.city == "London"
    assert len(payload.forecast) in (3, 4)  # allow edge around today trimming


@responses.activate
def test_cache_used_on_network_error(tmp_cache: FileCache) -> None:
    svc = WeatherService(api_key="test", cache=tmp_cache)

    # First call succeeds to warm cache
    responses.add(
        responses.GET,
        f"{svc.BASE_URL}/weather",
        json=_mock_current(),
        status=200,
    )
    responses.add(
        responses.GET,
        f"{svc.BASE_URL}/forecast",
        json=_mock_forecast(),
        status=200,
    )
    payload, stale = svc.get_weather("London", units="metric")
    assert not stale

    # Next call errors -> should serve stale from cache
    responses.reset()
    responses.add(responses.GET, f"{svc.BASE_URL}/weather", body=Exception("boom"))
    responses.add(responses.GET, f"{svc.BASE_URL}/forecast", body=Exception("boom"))

    payload2, stale2 = svc.get_weather("London", units="metric")
    assert stale2
    assert payload2.current.city == payload.current.city
