import json
from typing import Any, Dict, Tuple

import requests

REQUEST_TIMEOUT = 10
SEARCH_BODY_LIMIT = 200


WEATHER_CODE_MAP = {
    0: "Sunny",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Cloudy",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _get_json(url: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Small helper so every HTTP request has timeout and status checking."""
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _shorten(text: str, limit: int = SEARCH_BODY_LIMIT) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def get_weather(city: str) -> str:
    """Get real current weather for a city using Open-Meteo."""
    try:
        geo = _get_json(
            "https://geocoding-api.open-meteo.com/v1/search",
            {"name": city, "count": 1},
        )
        if not geo.get("results"):
            return f"City not found: {city}"

        place = geo["results"][0]
        lat = place["latitude"]
        lon = place["longitude"]
        display_name = place.get("name", city)

        weather = _get_json(
            "https://api.open-meteo.com/v1/forecast",
            {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weathercode",
            },
        )

        current = weather.get("current", {})
        temp = current.get("temperature_2m")
        code = current.get("weathercode")
        desc = WEATHER_CODE_MAP.get(code, f"Unknown weather code {code}")

        if temp is None:
            return f"Weather data found for {display_name}, but current temperature is unavailable."

        return f"{display_name} is currently {desc}, {temp}°C."
    except requests.RequestException as exc:
        return f"Weather API error: {exc}"
    except (KeyError, TypeError, ValueError) as exc:
        return f"Weather data parse error: {exc}"


def get_exchange_rate(from_currency: str, to_currency: str) -> str:
    """Get a real exchange rate using the free Frankfurter API, no API key needed."""
    from_code = from_currency.upper().strip()
    to_code = to_currency.upper().strip()

    if from_code == to_code:
        return f"1 {from_code} = 1 {to_code}"

    try:
        data = _get_json(
            "https://api.frankfurter.app/latest",
            {"from": from_code, "to": to_code},
        )
        rate = data.get("rates", {}).get(to_code)
        date = data.get("date")

        if rate is None:
            return f"Exchange rate not found for {from_code} to {to_code}."

        suffix = f" Based on Frankfurter latest data date: {date}." if date else ""
        return f"1 {from_code} = {rate} {to_code}.{suffix}"
    except requests.RequestException as exc:
        return f"Exchange rate API error: {exc}"
    except (KeyError, TypeError, ValueError) as exc:
        return f"Exchange rate data parse error: {exc}"


def search_web(query: str) -> str:
    """Search the web and return short results to avoid wasting tokens."""
    try:
        from ddgs import DDGS

        results = list(DDGS().text(query, max_results=3))
        if not results:
            return "No results found."

        lines = []
        for index, result in enumerate(results, start=1):
            title = _shorten(result.get("title", "No title"), 120)
            body = _shorten(result.get("body", ""), SEARCH_BODY_LIMIT)
            href = result.get("href", "")
            lines.append(f"{index}. Title: {title}\nContent: {body}\nURL: {href}")

        return "\n\n".join(lines)
    except Exception as exc:
        # DDGS can be rate-limited or blocked, so return the error as a tool result
        # instead of crashing the whole app.
        return f"Search tool error: {exc}"


tool_map = {
    "get_weather": get_weather,
    "get_exchange_rate": get_exchange_rate,
    "search_web": search_web,
}


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the real current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, for example Kuala Lumpur",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_exchange_rate",
            "description": "Get the real exchange rate between two currencies using a free API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_currency": {
                        "type": "string",
                        "description": "Currency code, for example USD",
                    },
                    "to_currency": {
                        "type": "string",
                        "description": "Currency code, for example MYR",
                    },
                },
                "required": ["from_currency", "to_currency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for current or latest information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        },
    },
]


def describe_tool_call(name: str, args: Dict[str, Any]) -> str:
    """Human-friendly message for the frontend tool timeline."""
    if name == "get_weather":
        return f"🔧 Checking real weather for {args.get('city', 'the city')}..."
    if name == "get_exchange_rate":
        return (
            "🔧 Checking real exchange rate "
            f"{args.get('from_currency', '').upper()} → {args.get('to_currency', '').upper()}..."
        )
    if name == "search_web":
        return f"🔧 Searching the web for: {args.get('query', '')}"
    return f"🔧 Running tool: {name}"


def execute_tool_call(tool_call: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Execute one model tool call safely.
    Returns:
        result: string sent back to the model
        event: small dict for frontend display
    """
    function = tool_call.get("function", {})
    name = function.get("name", "")
    raw_args = function.get("arguments") or "{}"

    try:
        args = json.loads(raw_args)
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be a JSON object.")
    except Exception as exc:
        result = f"Tool argument JSON parse error for {name}: {exc}"
        return result, {
            "name": name or "unknown_tool",
            "args": {},
            "message": f"⚠️ Failed to parse tool arguments for {name or 'unknown_tool'}.",
            "result": result,
        }

    event = {
        "name": name,
        "args": args,
        "message": describe_tool_call(name, args),
    }

    func = tool_map.get(name)
    if func is None:
        result = f"Unknown tool requested by model: {name}"
        event["result"] = result
        return result, event

    try:
        result = func(**args)
    except TypeError as exc:
        result = f"Tool argument mismatch for {name}: {exc}"
    except Exception as exc:
        result = f"Tool execution error in {name}: {exc}"

    event["result"] = result
    return result, event
