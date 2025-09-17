"""Tests for price normalization utilities."""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from data.prices import _normalize_price


def test_normalize_price_handles_trailing_slash_hyphen():
    """Ensure price strings ending with '/-' normalize correctly."""

    assert _normalize_price("78/-") == 78.0
    assert _normalize_price("AED 78/-") == 78.0
