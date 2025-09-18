"""Configuration utilities for the chatbot parsing logic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ChatbotConfig:
    """Container describing the heuristics used to parse chat prompts."""

    price_triggers: Tuple[str, ...] = (
        "how much is the price of",
        "how much is the price for",
        "how much does it cost to",  # allow slightly more descriptive prompts
        "how much does it cost",
        "how much does",
        "how much is",
        "what is the price of",
        "what's the price of",
        "what is the price for",
        "what's the price for",
    )
    filler_words: Tuple[str, ...] = (
        "the price of",
        "the price for",
        "price of",
        "price for",
        "price",
        "the cost of",
        "the cost for",
        "cost of",
        "cost for",
        "cost",
        "product code",
        "product",
        "code",
        "buy",
        "purchase",
        "the",
        "a",
        "an",
        "please",
        "kindly",
    )


DEFAULT_CONFIG = ChatbotConfig()


__all__ = ["ChatbotConfig", "DEFAULT_CONFIG"]
