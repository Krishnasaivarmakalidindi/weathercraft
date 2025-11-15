from __future__ import annotations

from typing import Tuple

import pytest
from flask import Flask

from app import create_app


@pytest.fixture()
def app() -> Flask:
    app = create_app("development")
    app.config.update(OPENWEATHER_API_KEY="test")
    yield app


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def test_index_page(client) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert b"WeatherCraft" in r.data


def test_api_weather_monkeypatch(client, monkeypatch) -> None:
    from app.weather import service as service_mod

    def fake_get_weather(self, city: str, units: str = "metric") -> Tuple[object, bool]:
        class _Obj:
            def model_dump(self):
                return {
                    "units": units,
                    "current": {
                        "city": city,
                        "country": "GB",
                        "temp": 20.0,
                        "feelsLike": 20.0,
                        "humidity": 50,
                        "wind": 2.0,
                        "condition": {"main": "Clear", "description": "clear", "icon": "01d"},
                        "dt": 1700000000,
                    },
                    "forecast": [],
                    "source": "fake",
                }

        return _Obj(), False

    monkeypatch.setattr(service_mod.WeatherService, "get_weather", fake_get_weather)

    r = client.get("/api/weather?city=London&units=metric", headers={"Accept": "application/json"})
    assert r.status_code == 200
    js = r.get_json()
    assert js["ok"] is True
    assert js["data"]["current"]["city"] == "London"
