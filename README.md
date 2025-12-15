# WeatherCraft

Modern Flask + Tailwind weather app with smooth animations, dark mode, and a compact JSON API.

## Features
- Flask app factory + blueprint structure
- Current weather + 3-day forecast (WeatherAPI.com)
- File cache (10 min TTL)
- Tailwind CSS via CDN (optional local build), Alpine.js for interactivity
- Lottie animations for loading/empty/error
- Dark mode toggle persisted to `localStorage`
- Accessible, mobile‑first UI with skeletons and transitions
- JSON endpoint: `/api/weather?city=...&units=metric`

## Quickstart (Windows)

1. Create and activate a virtual env:
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Install dependencies:
```powershell
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set your key:
```powershell
Copy-Item .env.example .env
# Edit .env to set WEATHER_API_KEY=<your-key>
```

4. Start the dev server:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```
Open http://127.0.0.1:5000

Tip: You can also run `flask --app app:create_app --debug run`.

## Tailwind (optional local build)
By default Tailwind CDN is used for instant start. For a local build:
```powershell
npm install
npm run tailwind:build
```
Adjust `tailwind.config.js` as needed.

## Configuration
- `WEATHER_API_KEY` (required)
- `CACHE_TTL` (seconds, default 600)
- `WEATHER_CACHE_DIR` (for file cache)

## API
- Endpoint: `/api/weather?city=<name>&units=metric|imperial`
- Returns: current + forecast in a compact JSON schema

## Testing
```powershell
pytest -q
```

## Pre-commit
```powershell
pre-commit install; pre-commit run --all-files
```

## Notes on animations
- Loading/empty/error Lottie files live in `app/weather/static/lottie/`. Placeholders are provided; replace with actual JSON files from lottiefiles.com or similar.

## Project Structure
- App code under `app/` with blueprints and templates
- Static assets under `app/weather/static/`
- Scripts for development in `scripts/`

## License
This project uses third-party APIs and libraries; review their licenses. No paid assets required.
