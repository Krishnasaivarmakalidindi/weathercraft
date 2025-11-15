"""Lightweight input validation helpers for weather search."""
from __future__ import annotations

import re
from dataclasses import dataclass


CITY_RE = re.compile(r"^[\w\-\s\.,]{1,80}$", re.IGNORECASE)


@dataclass
class CityQuery:
    city: str
    units: str = "metric"

    def validate(self) -> None:
        if not self.city or not CITY_RE.match(self.city.strip()):
            raise ValueError("Invalid city name")
        if self.units not in {"metric", "imperial"}:
            raise ValueError("Invalid units")
