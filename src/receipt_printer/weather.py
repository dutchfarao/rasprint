"""Open-Meteo weather fetching and receipt formatting."""
from __future__ import annotations

import logging
from typing import Any

import requests

from receipt_printer import config

logger = logging.getLogger(__name__)

URL = "https://api.open-meteo.com/v1/forecast"

_WMO_DESCRIPTIONS: dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Slight showers", 81: "Moderate showers", 82: "Heavy showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Thunderstorm + heavy hail",
}

_ASCII_ICONS: dict[str, list[str]] = {
    "sun": [
        r"     \  |  /    ",
        r"    --( o )--   ",
        r"     /  |  \    ",
    ],
    "cloud": [
        r"      .---.     ",
        r"    _(     ).   ",
        r"   (___.--__)   ",
    ],
    "rain": [
        r"      .---.     ",
        r"    _(     ).   ",
        r"    ' ' ' '     ",
    ],
    "snow": [
        r"      .---.     ",
        r"    _(     ).   ",
        r"    * * * *     ",
    ],
    "storm": [
        r"      .---.     ",
        r"    _(     ).   ",
        r"     //_//      ",
    ],
}


def _icon_key(code: int) -> str:
    """Map a WMO weather code to an ASCII icon key."""
    if code <= 1:
        return "sun"
    if code in (2, 3, 45, 48):
        return "cloud"
    if 51 <= code <= 67 or code in (80, 81, 82):
        return "rain"
    if 71 <= code <= 77 or code in (85, 86):
        return "snow"
    if code >= 95:
        return "storm"
    return "cloud"


def _description(code: int) -> str:
    """Return a human-readable string for a WMO weather code."""
    return _WMO_DESCRIPTIONS.get(code, f"Code {code}")


def fetch_weather() -> str:
    """Fetch current weather from Open-Meteo and return formatted receipt text."""
    try:
        resp = requests.get(
            URL,
            params={
                "latitude": config.LATITUDE,
                "longitude": config.LONGITUDE,
                "current_weather": "true",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "timezone": config.TIMEZONE,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()

        cw = data["current_weather"]
        daily = data["daily"]
        code = int(cw["weathercode"])
        temp = cw["temperature"]
        t_max = daily["temperature_2m_max"][0]
        t_min = daily["temperature_2m_min"][0]
        precip = daily["precipitation_sum"][0]

        icon_lines = _ASCII_ICONS[_icon_key(code)]
        lines = [
            *icon_lines,
            "",
            f"  {_description(code)}",
            f"  Now:  {temp} C",
            f"  High: {t_max} C    Low: {t_min} C",
            f"  Precip: {precip} mm",
        ]
        return "\n".join(lines)

    except Exception as exc:
        logger.warning("Weather fetch failed: %s", exc)
        return "Weather unavailable"
