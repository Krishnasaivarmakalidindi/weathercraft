# Run WeatherCraft in development mode
$env:FLASK_ENV = "development"
# Let Flask know the app factory
flask --app app:create_app --debug run --port 5000