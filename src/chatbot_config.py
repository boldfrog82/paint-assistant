"""Configuration helpers for the paint assistant chatbot."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Sequence


@dataclass(frozen=True)
class ChatbotConfig:
    """Runtime configuration for parsing and fuzzy matching."""

    about_triggers: Sequence[str] = (
        "tell me about",
        "information about",
        "information on",
        "what is",
        "what's",
        "describe",
        "details about",
    )
    price_triggers: Sequence[str] = (
        "how much is",
        "how much does",
        "price for",
        "price of",
        "price on",
        "what is the price of",
        "what's the price of",
        "cost of",
    )
    filler_words: Sequence[str] = ("the", "a", "an", "about", "of")
    product_similarity_threshold: float = 75.0
    code_similarity_threshold: float = 80.0
    size_similarity_threshold: float = 70.0
    suggestion_limit: int = 3
    size_aliases: Dict[str, str] = field(
        default_factory=lambda: {
            "l": "ltr",
            "lt": "ltr",
            "ltr": "ltr",
            "liter": "ltr",
            "litre": "ltr",
            "liters": "ltr",
            "litres": "ltr",
            "ml": "ml",
            "milliliter": "ml",
            "millilitre": "ml",
            "milliliters": "ml",
            "millilitres": "ml",
            "g": "g",
            "gram": "g",
            "grams": "g",
            "kg": "kg",
            "kilogram": "kg",
            "kilograms": "kg",
            "gal": "gallon",
            "gallon": "gallon",
            "gallons": "gallon",
            "qt": "quart",
            "quart": "quart",
            "quarts": "quart",
            "tin": "tin",
            "tins": "tin",
            "drum": "drum",
            "drums": "drum",
            "pack": "pack",
            "packs": "pack",
            "pail": "pail",
            "pails": "pail",
            "bucket": "bucket",
            "buckets": "bucket",
        }
    )


DEFAULT_CONFIG = ChatbotConfig()


__all__ = ["ChatbotConfig", "DEFAULT_CONFIG"]
