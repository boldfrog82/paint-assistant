codex/create-product-quotation-tool-db0tm4
"""Tests covering discount calculations and VAT totals."""


codex/create-product-quotation-tool-nq6b3b
"""Tests covering discount calculations and VAT totals."""

"""Unit tests for quotation calculations."""
Codex

Codex
from decimal import Decimal
from pathlib import Path
import sys

codex/create-product-quotation-tool-db0tm4

codex/create-product-quotation-tool-nq6b3b

import pytest

Codex
Codex
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

codex/create-product-quotation-tool-db0tm4

codex/create-product-quotation-tool-nq6b3b
Codex
from app.core import quote


def test_quote_row_applies_discount() -> None:
    item = quote.quote_row("National Acrylic Primer (W.B.)", "18 Ltr (Drum)", 2, 10)
    assert item["unit_price"] == Decimal("80.00")
    assert item["line_net"] == Decimal("144.00")


def test_vat_rounds_half_up() -> None:
    subtotal, vat, total = quote.compute_totals([{"line_net": Decimal("100.10")}])
    assert subtotal == Decimal("100.10")
    assert vat == Decimal("5.01")
    assert total == Decimal("105.11")


def test_totals_for_multiple_rows() -> None:
    drum = quote.quote_row("National Acrylic Primer (W.B.)", "18 Ltr (Drum)", 2, 10)
    gallon = quote.quote_row("National Acrylic Primer (W.B.)", "3.6 Ltr (Gallon)", 3, 0)
    subtotal, vat, total = quote.compute_totals([drum, gallon])
    assert subtotal == Decimal("210.00")
    assert vat == Decimal("10.50")
    assert total == Decimal("220.50")
codex/create-product-quotation-tool-db0tm4


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
Codex
Codex
