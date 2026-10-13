# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import re
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore
from google.cloud import storage
from google.genai import types

from .a2ui_utils import a2ui_callback

MODEL = "gemini-3.8-flash"
IMAGE_MODEL = "gemini-3.1-flash-lite-image"
PROJECT_ID = "qwiklabs-gcp-04-4ff6ed4e49c0"
GCS_BUCKET_NAME = "global-travel-concierge-qwiklabs-gcp-04-4ff6ed4e49c0-98df86"
AGENT_ENGINE_RESOURCE_NAME = "projects/685013156116/locations/us-east1/reasoningEngines/832370984156659712"
SANDBOX_RESOURCE_NAME = "projects/685013156116/locations/us-east1/reasoningEngines/832370984156659712/sandboxEnvironments/215231600160407552"





def _get_firestore_client() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def search_destinations(city: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search for tourist spots and attractions stored in the Firestore database.

    Args:
        city: Optional city name to filter by (e.g. 'Paris', 'Tokyo', 'New York').
        category: Optional category to filter by (e.g. 'Culture & Art', 'Sightseeing').

    Returns:
        A list of destination dictionaries with details such as name, city, duration, cost, and description.
    """
    db = _get_firestore_client()
    query = db.collection("destinations")
    if city:
        query = query.where("city", "==", city)
    
    docs = query.stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        if category and data.get("category", "").lower() != category.lower():
            continue
        results.append(data)
    return results


def add_destination(
    name: str,
    city: str,
    category: str,
    estimated_duration_hours: float,
    estimated_cost_usd: float,
    description: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Dict[str, Any]:
    """Add a new tourist spot or attraction to the catalog in Firestore.

    Args:
        name: Name of the spot or attraction (e.g., 'Louvre Museum').
        city: City where the spot is located (e.g., 'Paris').
        category: Category of the attraction (e.g., 'Culture & Art', 'Sightseeing', 'Food').
        estimated_duration_hours: Estimated time to spend at this spot in hours.
        estimated_cost_usd: Estimated entrance or activity cost in USD.
        description: A brief summary or highlight of the attraction.
        latitude: Optional GPS latitude coordinate.
        longitude: Optional GPS longitude coordinate.

    Returns:
        A dictionary confirming the created destination details and its ID.
    """
    db = _get_firestore_client()
    doc_id = f"{city.lower().replace(' ', '-')}-{name.lower().replace(' ', '-')}"
    item = {
        "id": doc_id,
        "name": name,
        "city": city,
        "category": category,
        "estimated_duration_hours": estimated_duration_hours,
        "estimated_cost_usd": estimated_cost_usd,
        "description": description,
        "latitude": latitude or 0.0,
        "longitude": longitude or 0.0,
    }
    db.collection("destinations").document(doc_id).set(item)
    return {"status": "success", "destination": item}


def get_weather_forecast(city: str, forecast_days: int = 3) -> Dict[str, Any]:
    """Fetch live current weather and multi-day forecast for any city worldwide using Open-Meteo public API (no auth required).

    Args:
        city: City name to look up weather for (e.g. 'San Francisco', 'Paris', 'Tokyo', 'London').
        forecast_days: Number of forecast days to return (1 to 5, default 3).

    Returns:
        A dictionary containing current temperature, conditions, and daily high/low forecast with rain chances.
    """
    days = max(1, min(forecast_days, 5))
    try:
        # 1. Geocode city name to lat/lon
        geo_url = (
            f"https://geocoding-api.open-meteo.com/v1/search?"
            f"name={urllib.parse.quote(city)}&count=1&language=en&format=json"
        )
        req = urllib.request.Request(geo_url, headers={"User-Agent": "GlobalTravelConcierge/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            geo_data = json.loads(resp.read().decode())
        
        results = geo_data.get("results")
        if not results:
            return {"error": f"Could not find coordinates for city '{city}'."}

        target = results[0]
        lat = target["latitude"]
        lon = target["longitude"]
        matched_name = target.get("name", city)
        country = target.get("country", "")

        # 2. Fetch current weather and multi-day forecast
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&"
            f"current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m&"
            f"daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&"
            f"timezone=auto&forecast_days={days}"
        )
        req = urllib.request.Request(weather_url, headers={"User-Agent": "GlobalTravelConcierge/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        current = data.get("current", {})
        daily = data.get("daily", {})

        # Simple weather code mapper
        def _code_to_desc(code: int) -> str:
            if code == 0:
                return "Clear sky"
            elif code in (1, 2, 3):
                return "Mainly clear or partly cloudy"
            elif code in (45, 48):
                return "Foggy"
            elif code in (51, 53, 55, 61, 63, 65):
                return "Rain showers"
            elif code in (71, 73, 75):
                return "Snow showers"
            elif code in (95, 96, 99):
                return "Thunderstorm"
            return "Overcast"

        forecast_list = []
        times = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        rain_probs = daily.get("precipitation_probability_max", [])
        codes = daily.get("weather_code", [])

        for i in range(len(times)):
            forecast_list.append({
                "date": times[i],
                "condition": _code_to_desc(codes[i]) if i < len(codes) else "Unknown",
                "max_temp_c": max_temps[i] if i < len(max_temps) else None,
                "min_temp_c": min_temps[i] if i < len(min_temps) else None,
                "precipitation_probability_pct": rain_probs[i] if i < len(rain_probs) else None,
            })

        return {
            "city": f"{matched_name}, {country}".strip(", "),
            "latitude": lat,
            "longitude": lon,
            "current": {
                "temperature_c": current.get("temperature_2m"),
                "feels_like_c": current.get("apparent_temperature"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "condition": _code_to_desc(current.get("weather_code", 0)),
                "wind_speed_kmh": current.get("wind_speed_10m"),
            },
            "daily_forecast": forecast_list,
        }
    except Exception as e:
        return {"error": f"Failed to fetch live weather forecast: {str(e)}"}



def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    city_lower = query.lower()
    if "sf" in city_lower or "san francisco" in city_lower:
        tz_identifier = "America/Los_Angeles"
    elif "tokyo" in city_lower:
        tz_identifier = "Asia/Tokyo"
    elif "paris" in city_lower:
        tz_identifier = "Europe/Paris"
    elif "new york" in city_lower or "nyc" in city_lower:
        tz_identifier = "America/New_York"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


def convert_currency(
    amount: float,
    from_currency: str = "USD",
    to_currency: str = "EUR",
) -> Dict[str, Any]:
    """Convert an amount from one currency to another using live exchange rates from the open ExchangeRate-API (no auth required).

    Args:
        amount: The monetary amount to convert (e.g. 100.0).
        from_currency: The base 3-letter currency code (e.g. 'USD', 'EUR', 'JPY', 'GBP', 'CAD').
        to_currency: The target 3-letter currency code (e.g. 'JPY', 'EUR', 'GBP', 'USD').

    Returns:
        A dictionary containing the original amount, converted amount, exchange rate, and last update timestamp.
    """
    from_curr = from_currency.strip().upper()
    to_curr = to_currency.strip().upper()
    try:
        url = f"https://open.er-api.com/v6/latest/{urllib.parse.quote(from_curr)}"
        req = urllib.request.Request(url, headers={"User-Agent": "GlobalTravelConcierge/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        if data.get("result") != "success":
            return {"error": f"Failed to fetch exchange rates for currency '{from_curr}'."}

        rates = data.get("rates", {})
        if to_curr not in rates:
            return {"error": f"Target currency '{to_curr}' is not supported or was not found."}

        rate = float(rates[to_curr])
        converted_amount = round(amount * rate, 2)

        return {
            "status": "success",
            "amount": amount,
            "from_currency": from_curr,
            "to_currency": to_curr,
            "exchange_rate": rate,
            "converted_amount": converted_amount,
            "last_updated_utc": data.get("time_last_update_utc", ""),
        }
    except Exception as e:
        return {"error": f"Failed to convert currency: {str(e)}"}


def calculate_trip_budget(
    city: str,
    days: int,
    travelers: int = 1,
    tier: str = "moderate",
    activity_cost_usd: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate an estimated trip budget breakdown for a destination.

    Args:
        city: The destination city (e.g. 'San Francisco', 'Paris', 'Tokyo').
        days: Number of days for the trip.
        travelers: Number of people traveling (default 1).
        tier: Travel style tier - 'budget', 'moderate', or 'luxury' (default 'moderate').
        activity_cost_usd: Optional pre-calculated total attraction tickets/activities cost in USD.

    Returns:
        A dictionary breakdown containing lodging, food & transit, activities, and total estimated cost in USD.
    """
    days = max(1, days)
    travelers = max(1, travelers)
    tier_lower = tier.lower()

    # Base daily rates per person based on tier
    rates = {
        "budget": {"lodging_per_night": 75.0, "daily_food_transit": 40.0},
        "moderate": {"lodging_per_night": 160.0, "daily_food_transit": 85.0},
        "luxury": {"lodging_per_night": 350.0, "daily_food_transit": 200.0},
    }
    tier_info = rates.get(tier_lower, rates["moderate"])

    # Lodging: rooms needed (assuming 2 travelers per room)
    rooms = (travelers + 1) // 2
    nights = max(1, days - 1) if days > 1 else 1
    total_lodging = round(rooms * nights * tier_info["lodging_per_night"], 2)

    total_food_transit = round(travelers * days * tier_info["daily_food_transit"], 2)

    # If activity cost not provided, calculate sum from catalog for the city
    if activity_cost_usd is None:
        spots = search_destinations(city=city)
        activity_cost_usd = round(sum(s.get("estimated_cost_usd", 0.0) for s in spots) * travelers, 2)
    else:
        activity_cost_usd = round(activity_cost_usd, 2)

    total_budget = round(total_lodging + total_food_transit + activity_cost_usd, 2)

    return {
        "city": city,
        "days": days,
        "travelers": travelers,
        "tier": tier_lower,
        "total_lodging_usd": total_lodging,
        "total_food_transit_usd": total_food_transit,
        "total_activities_usd": activity_cost_usd,
        "total_estimated_budget_usd": total_budget,
    }


def generate_destination_image(
    prompt: str,
    item_name: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate a visual postcard or preview image for a travel destination, landmark, or attraction.

    Args:
        prompt: Detailed description of the image to generate (e.g. 'A stunning travel postcard of the Golden Gate Bridge at sunrise').
        item_name: Name of the destination or landmark (e.g. 'Golden Gate Bridge', 'Eiffel Tower').
        tool_context: ADK ToolContext injected by the framework to save artifacts.

    Returns:
        A dictionary containing the destination name, public Cloud Storage image URL, and artifact status.
    """
    try:
        # 1. Generate image using gemini-3.1-flash-lite-image in the global region
        client = genai.Client(project=PROJECT_ID, location="global", vertexai=True)
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return {"error": "Image generation completed but no image bytes were returned by the model."}

        # 2. Save artifact for ADK Playground Artifacts panel
        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", item_name.lower().strip())
        artifact_filename = f"{safe_name}.jpg"
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        tool_context.save_artifact(
            filename=artifact_filename,
            artifact=artifact_part,
            custom_metadata={"item_name": item_name, "prompt": prompt},
        )

        # 3. Upload to public Google Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(f"images/{artifact_filename}")
        blob.upload_from_string(image_bytes, content_type=mime_type)
        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/images/{artifact_filename}"

        return {
            "status": "success",
            "item_name": item_name,
            "artifact_filename": artifact_filename,
            "image_url": public_url,
            "message": f"Generated image for {item_name} and uploaded to public storage.",
        }
    except Exception as e:
        return {"error": f"Failed to generate destination image: {str(e)}"}


async def generate_memories_callback(callback_context: CallbackContext):
    """After each turn, persist durable facts and preferences (home city, currency, budget) to Memory Bank."""
    await callback_context.add_session_to_memory()
    return None


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are a Global Travel Concierge & Itinerary Planner. You help travelers plan "
        "personalized and optimized city itineraries, explore spots to visit, check real live weather forecasts, "
        "calculate trip budgets, and run calculations safely in Python.\n\n"
        "Remember and recall the user's travel preferences across sessions from your memory, "
        "specifically their home city, preferred currency, travel style (budget, moderate, luxury), "
        "and budget limits. Always respect and incorporate these remembered preferences when making recommendations "
        "or calculating trip budgets without asking the user to repeat them.\n\n"
        "Available capabilities:\n"
        "- Use search_destinations and add_destination to manage catalog spots in Firestore.\n"
        "- Use calculate_trip_budget to provide estimated trip expense breakdowns.\n"
        "- Use convert_currency to convert money between world currencies using live exchange rates.\n"
        "- Use get_weather_forecast to fetch real live weather conditions and forecasts.\n"
        "- Use generate_destination_image to generate postcards and preview photos for attractions and destinations.\n"
        "- Execute Python code in the sandbox whenever custom math, route distance matrix, or complex calculations are needed."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        search_destinations,
        add_destination,
        calculate_trip_budget,
        convert_currency,
        get_weather_forecast,
        generate_destination_image,
        get_current_time,
    ],
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE_NAME,
        agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME,
    ),
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)


app = App(
    root_agent=root_agent,
    name="app",
)

