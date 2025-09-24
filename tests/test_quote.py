"""Unit tests for quotation calculations."""

from decimal import Decimal
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.quote import (
    QuoteItem,
    calculate_line_total,
    calculate_subtotal,
    calculate_total,
    calculate_vat,
)


def test_calculate_line_total_applies_discount():
    total = calculate_line_total(100, 2, 10)
    assert total == Decimal("180.00")


def test_calculate_line_total_rounds_half_up():
    total = calculate_line_total("33.335", 1, 0)
    assert total == Decimal("33.34")


def test_calculate_subtotal_accumulates_values():
    subtotal = calculate_subtotal([Decimal("10.00"), Decimal("5.55"), "4.45"])
    assert subtotal == Decimal("20.00")


@pytest.mark.parametrize(
    "subtotal, expected_vat",
    [
        (Decimal("100.10"), Decimal("5.01")),
        (Decimal("100.00"), Decimal("5.00")),
        (Decimal("99.99"), Decimal("5.00")),
    ],
)
def test_calculate_vat_rounding(subtotal: Decimal, expected_vat: Decimal):
    assert calculate_vat(subtotal) == expected_vat


def test_calculate_total_sums_subtotal_and_vat():
    subtotal = Decimal("250.50")
    vat = calculate_vat(subtotal)
    total = calculate_total(subtotal, vat)
    assert total == Decimal("263.03")


def test_quote_item_line_total_matches_function():
    item = QuoteItem(
        product_name="Sample",
        pack_size="18 Ltr",
        quantity=Decimal("3"),
        unit_price=Decimal("45.50"),
        discount_pct=Decimal("5"),
    )
    assert item.line_total == calculate_line_total("45.50", 3, 5)
