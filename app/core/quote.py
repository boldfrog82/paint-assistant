codex/create-product-quotation-tool-nq6b3b
"""Quotation helpers for the Streamlit paint quotation app."""

"""Core quotation logic for the paint quotation tool."""
Codex

from __future__ import annotations

import json
codex/create-product-quotation-tool-nq6b3b
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Iterable, List

MONEY_QUANT = Decimal("0.01")
VAT_RATE = Decimal("0.05")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PRODUCTS_PATH = ROOT_DIR / "data" / "paint_products.json"
PRICES_PATH = ROOT_DIR / "data" / "pricelistnationalpaints.json"


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    """Convert numeric inputs to :class:`Decimal`."""

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
Codex

    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def format_aed(value: Decimal | float | int | str) -> str:
codex/create-product-quotation-tool-nq6b3b
    """Return a value formatted as an AED currency string."""

    """Format a value as an AED currency string."""
Codex

    amount = _to_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    return f"AED {amount:,.2f}"


codex/create-product-quotation-tool-nq6b3b
def load_products(path: str | Path | None = None) -> List[dict]:
    """Load product metadata from ``paint_products.json``.

    The raw catalogue nests product dictionaries within lists and other
    dictionaries. This helper flattens the structure and deduplicates entries
    by product name.
    """

    target = Path(path) if path else PRODUCTS_PATH
    with target.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    collected: List[dict] = []

    def _collect(node: object) -> None:
        if isinstance(node, dict):
            if "product_name" in node:
                collected.append(node)
            for value in node.values():
                _collect(value)
        elif isinstance(node, list):
            for item in node:
                _collect(item)

    _collect(raw)

    deduped: Dict[str, dict] = {}
    for product in collected:
        name = product.get("product_name")
        if name and name not in deduped:
            deduped[name] = product
    return list(deduped.values())


def load_price_catalog(path: str | Path | None = None) -> Dict[str, Dict[str, Decimal]]:
    """Return a mapping of product name -> pack size -> unit price."""

    target = Path(path) if path else PRICES_PATH
    with target.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    catalog: Dict[str, Dict[str, Decimal]] = {}

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
Codex
    for category in raw.get("product_categories", []):
        for subcategory in category.get("subcategories", []):
            for product in subcategory.get("products", []):
                name = product.get("product_name")
codex/create-product-quotation-tool-nq6b3b
                if not name:
                    continue
                packs: Dict[str, Decimal] = {}
                for tier in product.get("prices", []):
                    size = tier.get("size")
                    price = tier.get("price")
                    if size and price is not None:
                        packs[size] = _to_decimal(price).quantize(
                            MONEY_QUANT, rounding=ROUND_HALF_UP
                        )
                if packs:
                    catalog[name] = packs
    return catalog


_PRODUCTS = load_products()
_PRICE_CATALOG = load_price_catalog()
_PRODUCT_LOOKUP = {
    product.get("product_name"): product for product in _PRODUCTS if product.get("product_name")
}


def find_matching_products(query: str) -> List[dict]:
    """Return catalogue entries whose name contains the query string."""

    needle = query.strip().casefold()
    if not needle:
        return _PRODUCTS[:10]

    matches: List[tuple[int, int, str, dict]] = []
    for product in _PRODUCTS:
        name = product.get("product_name", "")
        haystack = name.casefold()
        if needle in haystack:
            prefix_score = 0 if haystack.startswith(needle) else 1
            matches.append((prefix_score, haystack.find(needle), name, product))

    matches.sort(key=lambda item: (item[0], item[1], item[2]))
    return [match[3] for match in matches[:10]]


def quote_row(
    product_id: str,
    pack: str,
    qty: Decimal | float | int | str,
    discount_pct: Decimal | float | int | str,
) -> dict:
    """Build a quote row dict for a given product pack and quantity."""

    if product_id not in _PRICE_CATALOG:
        raise KeyError(f"Unknown product: {product_id}")

    pack_prices = _PRICE_CATALOG[product_id]
    if pack not in pack_prices:
        raise KeyError(f"Unknown pack '{pack}' for product '{product_id}'")

    quantity = _to_decimal(qty)
    discount = _to_decimal(discount_pct)
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")
    if discount < 0:
        raise ValueError("Discount cannot be negative")

    unit_price = pack_prices[pack]
    line_gross = unit_price * quantity
    discount_multiplier = (Decimal("100") - discount) / Decimal("100")
    line_net = (line_gross * discount_multiplier).quantize(
        MONEY_QUANT, rounding=ROUND_HALF_UP
    )

    product = _PRODUCT_LOOKUP.get(product_id)
    product_name = product.get("product_name") if product else product_id

    return {
        "product_id": product_id,
        "product_name": product_name,
        "pack": pack,
        "quantity": quantity,
        "unit_price": unit_price,
        "discount_pct": discount,
        "line_net": line_net,
    }


def compute_totals(items: Iterable[dict]) -> tuple[Decimal, Decimal, Decimal]:
    """Return subtotal, VAT, and grand total for the supplied rows."""

    subtotal = sum((_to_decimal(item["line_net"]) for item in items), start=Decimal("0"))
    subtotal = subtotal.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    vat = (subtotal * VAT_RATE).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    total = (subtotal + vat).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    return subtotal, vat, total


__all__ = [
    "compute_totals",
    "find_matching_products",
    "format_aed",
    "load_price_catalog",
    "load_products",
    "quote_row",

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
Codex
]
