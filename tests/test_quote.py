"""Tests covering discount calculations and VAT totals."""

from decimal import Decimal
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
