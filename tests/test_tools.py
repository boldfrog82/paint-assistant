"""Tests for utility tools that expose structured payloads."""

from src.data.prices import get_currency, list_available_sizes
from src.tools.paint import price_lookup_tool


def test_price_lookup_requires_product_code():
    """A missing product code should short-circuit the lookup."""

    payload = price_lookup_tool("   ", "18 Ltr (Drum)")

    assert payload["found"] is False
    assert payload["requested_code"] == ""
    assert payload["missing_fields"] == ["code"]
    assert payload["currency"] == get_currency()


def test_price_lookup_returns_sizes_when_size_missing():
    """When only the size is missing, available sizes should be returned."""

    payload = price_lookup_tool("A119", "")

    assert payload["found"] is False
    assert payload["missing_fields"] == ["size"]
    assert payload["available_sizes"] == list_available_sizes("A119")
    assert payload["currency"] == get_currency()
