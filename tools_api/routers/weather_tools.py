"""Weather tool endpoints using Open-Meteo (free, no API key)."""

from fastapi import APIRouter, HTTPException, Query
from tools_api.http_client import async_client

router = APIRouter(prefix="/weather", tags=["weather"])

OPEN_METEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


async def _geocode(city: str) -> dict:
    async with async_client() as client:
        response = await client.get(
            OPEN_METEO_GEOCODE,
            params={"name": city, "count": 1, "language": "en", "format": "json"},
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            raise HTTPException(status_code=404, detail=f"City not found: {city}")
        return results[0]


@router.get("/current")
async def current_weather(
    city: str = Query(..., description="City name, e.g. London, Tokyo"),
) -> dict:
    """Get current weather for a city via Open-Meteo."""
    location = await _geocode(city)
    lat, lon = location["latitude"], location["longitude"]

    async with async_client() as client:
        response = await client.get(
            OPEN_METEO_FORECAST,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "timezone": "auto",
            },
        )
        response.raise_for_status()
        data = response.json()

    current = data.get("current", {})
    code = current.get("weather_code", 0)

    return {
        "city": location.get("name"),
        "country": location.get("country"),
        "latitude": lat,
        "longitude": lon,
        "temperature_c": current.get("temperature_2m"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "conditions": WEATHER_CODES.get(code, f"Code {code}"),
        "source": "open_meteo",
    }


@router.get("/forecast")
async def weather_forecast(
    city: str = Query(..., description="City name"),
    days: int = Query(5, ge=1, le=7, description="Forecast days (1-7)"),
) -> dict:
    """Get multi-day weather forecast for a city."""
    location = await _geocode(city)
    lat, lon = location["latitude"], location["longitude"]

    async with async_client() as client:
        response = await client.get(
            OPEN_METEO_FORECAST,
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
                "timezone": "auto",
                "forecast_days": days,
            },
        )
        response.raise_for_status()
        data = response.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    forecast = []
    for i, date in enumerate(dates):
        code = daily["weather_code"][i] if i < len(daily.get("weather_code", [])) else 0
        forecast.append(
            {
                "date": date,
                "temp_max_c": daily["temperature_2m_max"][i],
                "temp_min_c": daily["temperature_2m_min"][i],
                "precipitation_mm": daily["precipitation_sum"][i],
                "conditions": WEATHER_CODES.get(code, f"Code {code}"),
            }
        )

    return {
        "city": location.get("name"),
        "country": location.get("country"),
        "forecast_days": days,
        "forecast": forecast,
        "source": "open_meteo",
    }
