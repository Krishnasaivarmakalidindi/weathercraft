from __future__ import annotations

from flask import Blueprint

# Expose a blueprint for the weather module
weather_bp = Blueprint(
    "weather",
    __name__,
    template_folder="../templates",
    static_folder="static",
)
