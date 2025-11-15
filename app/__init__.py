"""WeatherCraft Flask application factory.

This module exposes `create_app` for WSGI/ASGI servers.
It wires configuration, blueprints, Jinja globals, and error handlers.
"""
from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template


def _wants_json() -> bool:
    """Return True if the request prefers JSON over HTML.

    This is used for unified error handling.
    """
    from flask import request

    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return best == "application/json" and (
        request.accept_mimetypes[best] > request.accept_mimetypes["text/html"]
    )


def create_app(config_name: str | None = None) -> Flask:
    """Application factory for WeatherCraft.

    Args:
        config_name: Optional configuration name (e.g., "development", "production").
                     Falls back to `FLASK_ENV` or "development".

    Returns:
        A configured Flask application instance.
    """
    # Load environment variables from .env if present
    load_dotenv()

    app = Flask(__name__, static_folder=None)

    # Lazy import config to avoid circulars during test discovery
    from .config import get_config

    cfg = get_config(config_name or os.getenv("FLASK_ENV", "development"))
    app.config.from_object(cfg)

    # Register blueprints
    from .weather.routes import weather_bp

    app.register_blueprint(weather_bp)

    # Jinja globals or filters
    @app.context_processor
    def inject_globals() -> dict[str, Any]:
        return {
            "APP_NAME": "WeatherCraft",
            "APP_VERSION": os.getenv("APP_VERSION", "0.1.0"),
        }

    # Error handlers: return JSON if requested, else render a friendly page
    @app.errorhandler(404)
    def not_found(err):  # type: ignore[no-redef]
        if _wants_json():
            return jsonify({"error": "Not Found"}), 404
        return render_template("base.html", page_title="Not Found"), 404

    @app.errorhandler(500)
    def server_error(err):  # type: ignore[no-redef]
        if _wants_json():
            return jsonify({"error": "Internal Server Error"}), 500
        return render_template("base.html", page_title="Server Error"), 500

    return app
