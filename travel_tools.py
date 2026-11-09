"""Data loading, plain search functions and LangChain tools for the travel agent."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from langchain_core.tools import tool

DATA_DIR = Path(__file__).resolve().parent / "data"

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MAX_FORECAST_DAYS = 15

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 71: "Light snow", 73: "Snow",
    80: "Rain showers", 81: "Rain showers", 82: "Heavy rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}

CITY_COORDINATES = {
    "bangalore": (12.9716, 77.5946), "chennai": (13.0827, 80.2707),
    "delhi": (28.6139, 77.2090), "goa": (15.2993, 74.1240),
    "hyderabad": (17.3850, 78.4867), "jaipur": (26.9124, 75.7873),
    "kolkata": (22.5726, 88.3639), "mumbai": (19.0760, 72.8777),
}


def load_json(filename: str) -> list:
    """Load a JSON file from the data folder."""
    try:
        with open(DATA_DIR / filename, encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not load {filename}: {error}")


FLIGHTS = load_json("flights.json")
HOTELS = load_json("hotels.json")
PLACES = load_json("places.json")

AVAILABLE_CITIES = sorted({h["city"] for h in HOTELS})
PLACE_TYPES = sorted({p["type"] for p in PLACES})


def search_flights(source: str, destination: str, sort_by: str = "price") -> list:
    """Find flights from source to destination, sorted by price or duration."""
    matches = []
    for flight in FLIGHTS:
        if (flight["from"].strip().lower() == source.strip().lower()
                and flight["to"].strip().lower() == destination.strip().lower()):
            departure = datetime.fromisoformat(flight["departure_time"])
            arrival = datetime.fromisoformat(flight["arrival_time"])
            item = dict(flight)
            item["duration_minutes"] = int((arrival - departure).total_seconds() // 60)
            item["departs_at"] = departure.strftime("%H:%M")
            item["arrives_at"] = arrival.strftime("%H:%M")
            matches.append(item)
    key = "duration_minutes" if sort_by == "duration" else "price"
    return sorted(matches, key=lambda f: f[key])[:5]


def search_hotels(city: str, min_stars: int = 0, max_price: float = 1_000_000) -> list:
    """Find hotels in a city by minimum stars and max price per night."""
    matches = [
        h for h in HOTELS
        if h["city"].strip().lower() == city.strip().lower()
        and h["stars"] >= min_stars
        and h["price_per_night"] <= max_price
    ]
    return sorted(matches, key=lambda h: (-h["stars"], h["price_per_night"]))[:5]


def search_places(city: str, place_type: str = "", limit: int = 8) -> list:
    """Find top-rated attractions in a city, optionally filtered by type."""
    matches = [p for p in PLACES if p["city"].strip().lower() == city.strip().lower()]
    if place_type:
        matches = [p for p in matches if place_type.strip().lower() in p["type"].lower()]
    return sorted(matches, key=lambda p: -p["rating"])[:limit]


def get_coordinates(city: str) -> tuple:
    """Return (latitude, longitude): built-in table first, then geocoding in India."""
    known = CITY_COORDINATES.get(city.strip().lower())
    if known:
        return known
    try:
        response = requests.get(
            GEOCODING_URL, params={"name": city, "count": 1, "countryCode": "IN"}, timeout=10
        )
        response.raise_for_status()
        result = response.json()["results"][0]
        return result["latitude"], result["longitude"]
    except (requests.RequestException, KeyError, IndexError) as error:
        raise ValueError(f"Could not find coordinates for '{city}': {error}")


def get_weather(city: str, start_date: str, end_date: str) -> list:
    """Get daily weather forecast for a city. Dates must be YYYY-MM-DD."""
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        return [{"error": "Dates must be in YYYY-MM-DD format."}]
    if end < start:
        return [{"error": "End date is before start date."}]
    if start > date.today() + timedelta(days=MAX_FORECAST_DAYS):
        return [{"error": f"Forecast not available yet (only next {MAX_FORECAST_DAYS} days)."}]
    try:
        latitude, longitude = get_coordinates(city)
        params = {
            "latitude": latitude, "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,weathercode,precipitation_probability_max",
            "start_date": start_date, "end_date": end_date, "timezone": "auto",
        }
        response = requests.get(FORECAST_URL, params=params, timeout=10)
        response.raise_for_status()
        daily = response.json()["daily"]
    except (ValueError, requests.RequestException, KeyError) as error:
        return [{"error": f"Weather unavailable: {error}"}]
    return [
        {
            "date": daily["time"][i],
            "max_temp_c": daily["temperature_2m_max"][i],
            "min_temp_c": daily["temperature_2m_min"][i],
            "condition": WEATHER_CODES.get(daily["weathercode"][i], "Unknown"),
            "rain_chance_percent": daily["precipitation_probability_max"][i],
        }
        for i in range(len(daily["time"]))
    ]


def estimate_budget(outbound_flight_price: float, hotel_price_per_night: float, nights: int,
                    return_flight_price: float = 0, daily_expense: float = 800,
                    travelers: int = 1) -> dict:
    """Calculate total trip cost.

    Flight = (outbound + return) * travelers
    Hotel = price per night * nights (per room)
    Food and local travel = daily_expense * (nights + 1) * travelers
    """
    flight_total = (outbound_flight_price + return_flight_price) * travelers
    hotel_total = hotel_price_per_night * nights
    local_total = daily_expense * (nights + 1) * travelers
    return {
        "flight": flight_total,
        "hotel": hotel_total,
        "food_and_local_travel": local_total,
        "total": flight_total + hotel_total + local_total,
    }


@tool
def flight_search(source: str, destination: str, sort_by: str = "price") -> list:
    """Search one-way flights between two cities. sort_by is 'price' (cheapest) or 'duration' (fastest). Call twice (once each way) for a round trip."""
    results = search_flights(source, destination, sort_by)
    return results or f"No flights found from {source} to {destination} in the dataset."


@tool
def hotel_search(city: str, min_stars: int = 0, max_price: float = 1000000) -> list:
    """Find hotels in a city. Filter by minimum stars and maximum price per night."""
    results = search_hotels(city, min_stars, max_price)
    return results or f"No hotels found in {city} for these filters."


@tool
def places_search(city: str, place_type: str = "") -> list:
    """Find top-rated tourist attractions in a city. Optionally filter by place type (beach, fort, lake, market, monument, museum, park, temple)."""
    results = search_places(city, place_type)
    return results or f"No places found in {city} for type '{place_type}'."


@tool
def weather_lookup(city: str, start_date: str, end_date: str) -> list:
    """Get the daily weather forecast for a city. Dates must be YYYY-MM-DD."""
    return get_weather(city, start_date, end_date)


@tool
def budget_estimator(outbound_flight_price: float, hotel_price_per_night: float, nights: int,
                     return_flight_price: float = 0, daily_expense: float = 800,
                     travelers: int = 1) -> dict:
    """Estimate total trip cost from flight prices, hotel price per night, nights and daily local expenses."""
    return estimate_budget(outbound_flight_price, hotel_price_per_night, nights,
                           return_flight_price, daily_expense, travelers)


ALL_TOOLS = [flight_search, hotel_search, places_search, weather_lookup, budget_estimator]