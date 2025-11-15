# Deploy WeatherCraft to Render

This keeps everything Python (Flask + Gunicorn) and is the quickest way to run the server app.

## One-time setup
1. Create a Render account: https://render.com
2. Fork or push this repo to GitHub (already done).
3. In Render, click New → Web Service.
4. Select this repository.

## Service settings
- Runtime: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn wsgi:app --workers 2 --threads 4 --bind 0.0.0.0:$PORT`
- Environment Variables:
  - `PYTHON_VERSION=3.11`
  - `WEATHERAPI_KEY=<your WeatherAPI key>`
- Instance Type: Free

Click Create Web Service. On first deploy, your app will be available at a URL like:
```
https://weathercraft.onrender.com
```

## Verify
- Root: `https://<service>.onrender.com/` should render the UI.
- API: `https://<service>.onrender.com/api/weather?city=London&units=metric`

## Optional: Keep Netlify for static URL
If you want to keep your Netlify domain, add this line to `public/_redirects` to proxy API/app to Render:
```
/*  https://<service>.onrender.com/:splat  200
```
This makes the Netlify site forward all requests to your Render-hosted Flask app.
