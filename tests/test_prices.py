"""Tests for price normalization utilities."""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from data.prices import _normalize_price, get_price, list_sizes


def test_normalize_price_handles_trailing_slash_hyphen():
    """Ensure price strings ending with '/-' normalize correctly."""

    assert _normalize_price("78/-") == 78.0
    assert _normalize_price("AED 78/-") == 78.0


def test_list_sizes_includes_variant_labels():
    """Variant-only products expose combined variant and size labels."""

    sizes = list_sizes("A015")

    assert sizes == [
        "White – 18 Ltr (Drum)",
        "White – 3.6 Ltr (Gallon)",
        "APS – 18 Ltr (Drum)",
        "APS – 3.6 Ltr (Gallon)",
    ]


def test_get_price_handles_variant_only_product():
    """Variant-specific price lookups are available when no top-level prices exist."""

    assert get_price("A015", "White – 18 Ltr (Drum)") == 60.0
    assert get_price("a015", "APS – 3.6 Ltr (Gallon)") == 23.0
