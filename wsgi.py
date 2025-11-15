"""WSGI entrypoint for WeatherCraft."""
from app import create_app

app = create_app()
