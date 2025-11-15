# WeatherCraft - Netlify Deployment Guide

## Quick Deploy Steps

### 1. Prepare Your Repository

Make sure you have:
- ✅ `netlify.toml` (configuration file)
- ✅ `netlify/functions/api.py` (serverless function)
- ✅ Updated `requirements.txt` with werkzeug

### 2. Push to GitHub

```bash
git init
git add .
git commit -m "Ready for Netlify deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/weathercraft.git
git push -u origin main
```

### 3. Deploy on Netlify

1. Go to [app.netlify.com](https://app.netlify.com)
2. Click **"Add new site"** → **"Import an existing project"**
3. Choose **GitHub** and authorize Netlify
4. Select your **weathercraft** repository
5. Netlify will auto-detect settings from `netlify.toml`
6. Click **"Show advanced"** and add environment variable:
   - **Key:** `WEATHERAPI_KEY`
   - **Value:** Your WeatherAPI key
7. Click **"Deploy site"**

### 4. Your Site is Live! 🎉

Netlify will give you a URL like: `https://your-site-name.netlify.app`

## Custom Domain (Optional)

1. Go to **Site settings** → **Domain management**
2. Click **"Add custom domain"**
3. Follow DNS configuration steps

## Environment Variables

To update your API key later:
1. Go to **Site settings** → **Environment variables**
2. Update `WEATHERAPI_KEY`
3. Trigger a new deploy

## Redeploy

Any push to your `main` branch will automatically redeploy!

```bash
git add .
git commit -m "Update app"
git push
```

## Troubleshooting

### Build fails?
- Check build logs in Netlify dashboard
- Ensure all dependencies are in `requirements.txt`

### Function timeout?
- Netlify free tier: 10 second timeout
- Upgrade plan if needed for longer requests

### API not working?
- Check function logs: **Functions** tab in Netlify dashboard
- Verify `WEATHERAPI_KEY` is set correctly
