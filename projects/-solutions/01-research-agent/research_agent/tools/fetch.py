"""Fetch and extract readable text from a web page.

Kept separate from `web_search.py` because search results only give a
short snippet — actually reading the page gives the synthesis step much
more to work with. Every failure mode (timeout, 404, non-HTML content,
blocked robots) degrades gracefully to an empty string rather than
raising, since one bad URL should never crash the whole research run.
"""

from __future__ import annotations

import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ResearchAgent/1.0; "
        "+https://github.com/AdilShamim8/Agentic-AI-Roadmap-with-Notes-and-Projects)"
    )
}

_BLOCKED_TAGS = ("script", "style", "noscript", "nav", "footer", "header", "form", "aside")


def fetch_page_text(url: str, timeout: int = 8, max_chars: int = 8000) -> str:
    """Download `url` and return its main readable text, or "" on any failure."""

    if not url or not url.startswith(("http://", "https://")):
        return ""

    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException:
        return ""

    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type and "text" not in content_type:
        return ""

    try:
        text = extract_main_text(response.text)
    except Exception:
        return ""

    return text[:max_chars]


def extract_main_text(html: str) -> str:
    """Strip an HTML document down to its readable body text."""

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(_BLOCKED_TAGS):
        tag.decompose()

    # Prefer <article> or <main> if present — usually the actual content.
    container = soup.find("article") or soup.find("main") or soup.body or soup

    text = container.get_text(separator="\n")
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()
