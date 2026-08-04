"""
Very lightweight sentiment/urgency detector.

Like the intent classifier, this is a cheap rule-based pass rather than an
LLM call, so every conversation gets an instant frustration/urgency signal
before any specialist agent (or LLM) is invoked. It's deliberately biased
toward over-detecting frustration - in a real support system, escalating a
mildly annoyed customer to a human early is a much cheaper mistake than
missing a genuinely angry one.
"""
from __future__ import annotations

from typing import Literal

Sentiment = Literal["neutral", "frustrated", "angry"]

_ANGRY_WORDS = [
    "furious", "ridiculous", "unacceptable", "scam", "lawsuit", "sue",
    "worst", "terrible", "awful", "disgusted", "never again", "cancel my account",
    "speak to a manager", "speak to your manager", "human", "real person",
]

_FRUSTRATED_WORDS = [
    "frustrated", "annoyed", "still not", "again", "third time", "keeps happening",
    "not happy", "disappointed", "come on", "seriously",
]


def detect_sentiment(text: str) -> Sentiment:
    lowered = text.lower()

    shouting = _is_shouting(text)
    exclamations = text.count("!")

    angry_hits = sum(1 for w in _ANGRY_WORDS if w in lowered)
    frustrated_hits = sum(1 for w in _FRUSTRATED_WORDS if w in lowered)

    if angry_hits > 0 or (shouting and exclamations >= 2):
        return "angry"
    if frustrated_hits > 0 or exclamations >= 2 or shouting:
        return "frustrated"
    return "neutral"


def _is_shouting(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 6:
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    return upper_ratio > 0.6


def wants_human(text: str) -> bool:
    """Detect an explicit request to speak to a human agent."""
    lowered = text.lower()
    triggers = ["speak to a human", "real person", "human agent", "speak to your manager",
                "speak to a manager", "talk to a person", "escalate"]
    return any(t in lowered for t in triggers)
