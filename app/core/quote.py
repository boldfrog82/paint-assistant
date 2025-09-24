"""Core quotation logic for the paint quotation tool."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

MONEY_QUANT = Decimal("0.01")
DEFAULT_VAT_RATE = Decimal("0.05")


@dataclass
class QuoteItem:
    """A line item included in a quotation."""

    product_name: str
    pack_size: str
    quantity: Decimal
    unit_price: Decimal
    discount_pct: Decimal = Decimal("0")

    @property
    def line_total(self) -> Decimal:
        """Calculate the total amount for the line item."""
        return calculate_line_total(self.unit_price, self.quantity, self.discount_pct)

    def to_dict(self) -> Dict[str, str]:
        """Return a serialisable representation of the quote item."""
        data = asdict(self)
        data["quantity"] = f"{self.quantity}"
        data["unit_price"] = format_aed(self.unit_price)
        data["discount_pct"] = f"{self.discount_pct.normalize()}%" if self.discount_pct else "0%"
        data["line_total"] = format_aed(self.line_total)
        return data


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    """Convert supported numeric inputs to :class:`~decimal.Decimal`."""

    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def format_aed(value: Decimal | float | int | str) -> str:
    """Format a value as an AED currency string."""

    amount = _to_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    return f"AED {amount:,.2f}"


def load_products(path: str | Path) -> List[Dict]:
    """Load and flatten product metadata from ``paint_products.json``."""

    data_path = Path(path)
    with data_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    products: List[Dict] = []
    for group in raw:
        if isinstance(group, Sequence) and not isinstance(group, (str, bytes)):
            for entry in group:
                if isinstance(entry, dict):
                    products.append(entry)
        elif isinstance(group, dict):
            products.append(group)
    return products


def load_price_catalog(path: str | Path) -> Dict[str, List[Dict[str, Decimal]]]:
    """Load product prices indexed by product name."""

    data_path = Path(path)
    with data_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    catalog: Dict[str, List[Dict[str, Decimal]]] = {}
    for category in raw.get("product_categories", []):
        for subcategory in category.get("subcategories", []):
            for product in subcategory.get("products", []):
                name = product.get("product_name")
                prices = [
                    {"size": tier.get("size", ""), "price": _to_decimal(tier.get("price", 0))}
                    for tier in product.get("prices", [])
                    if tier.get("size")
                ]
                if name:
                    catalog[name] = prices
    return catalog


def search_products(products: Sequence[Dict], query: str, limit: int = 10) -> List[Dict]:
    """Return products whose names contain the search query."""

    if not query:
        return list(products)[:limit]

    needle = query.casefold()
    scored: List[tuple[int, Dict]] = []
    for product in products:
        name = product.get("product_name", "")
        haystack = name.casefold()
        if needle in haystack:
            scored.append((haystack.find(needle), product))
    scored.sort(key=lambda item: (item[0], item[1].get("product_name", "")))
    return [product for _, product in scored[:limit]]


def calculate_line_total(
    unit_price: Decimal | float | int | str,
    quantity: Decimal | float | int | str,
    discount_pct: Decimal | float | int | str = Decimal("0"),
) -> Decimal:
    """Calculate the total for a quotation line item."""

    price = _to_decimal(unit_price)
    qty = _to_decimal(quantity)
    discount = _to_decimal(discount_pct)

    if qty < 0:
        raise ValueError("Quantity cannot be negative")
    if discount < 0:
        raise ValueError("Discount cannot be negative")

    line_total = price * qty
    if discount:
        line_total *= (Decimal("100") - discount) / Decimal("100")

    return line_total.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def calculate_subtotal(line_totals: Iterable[Decimal | float | int | str]) -> Decimal:
    """Aggregate a collection of line totals."""

    subtotal = sum((_to_decimal(total) for total in line_totals), start=Decimal("0"))
    return subtotal.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def calculate_vat(subtotal: Decimal | float | int | str, vat_rate: Decimal = DEFAULT_VAT_RATE) -> Decimal:
    """Calculate VAT from a subtotal using half-up rounding."""

    subtotal_value = _to_decimal(subtotal)
    vat_amount = subtotal_value * vat_rate
    return vat_amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def calculate_total(subtotal: Decimal | float | int | str, vat: Decimal | float | int | str) -> Decimal:
    """Calculate the grand total for a quote."""

    total = _to_decimal(subtotal) + _to_decimal(vat)
    return total.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


__all__ = [
    "QuoteItem",
    "calculate_line_total",
    "calculate_subtotal",
    "calculate_total",
    "calculate_vat",
    "format_aed",
    "load_price_catalog",
    "load_products",
    "search_products",
]
