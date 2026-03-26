"""News headline fetching from NewsAPI or Google News RSS fallback."""
from __future__ import annotations

import logging
import os
import textwrap
from typing import Any

import feedparser
import requests

logger = logging.getLogger(__name__)

MAX_ITEMS = 5
LINE_WIDTH = 46
_RSS_URL = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
_NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"


def _format_headline(index: int, headline: str) -> str:
    """Format a numbered headline, word-wrapped and truncated to 2 lines."""
    lines = textwrap.wrap(f"[{index}] {headline}", LINE_WIDTH)
    if len(lines) > 2:
        lines = lines[:2]
        lines[-1] = lines[-1][: LINE_WIDTH - 3] + "..."
    return "\n".join(lines)


def _fetch_newsapi(api_key: str) -> list[str]:
    """Fetch top English headlines from NewsAPI."""
    resp = requests.get(
        _NEWSAPI_URL,
        params={"apiKey": api_key, "language": "en", "pageSize": MAX_ITEMS},
        timeout=10,
    )
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    return [a["title"] for a in data.get("articles", [])[:MAX_ITEMS]]


def _fetch_rss() -> list[str]:
    """Fetch top headlines from Google News RSS (no API key required)."""
    feed = feedparser.parse(_RSS_URL)
    return [entry.title for entry in feed.entries[:MAX_ITEMS]]


def fetch_news() -> str:
    """Fetch news headlines and return formatted receipt text."""
    try:
        api_key = os.environ.get("NEWS_API_KEY")
        raw_headlines = _fetch_newsapi(api_key) if api_key else _fetch_rss()
    except Exception as exc:
        logger.warning("News fetch failed: %s", exc)
        return "News unavailable"

    if not raw_headlines:
        return "No headlines available"

    return "\n".join(
        _format_headline(i, h) for i, h in enumerate(raw_headlines, start=1)
    )
