"""Quotation helpers for the Streamlit paint quotation app."""

from __future__ import annotations

import json
from dataclasses import dataclass
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

    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def format_aed(value: Decimal | float | int | str) -> str:
    """Return a value formatted as an AED currency string."""

    amount = _to_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    return f"AED {amount:,.2f}"


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
    for category in raw.get("product_categories", []):
        for subcategory in category.get("subcategories", []):
            for product in subcategory.get("products", []):
                name = product.get("product_name")
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

for name, product in _PRODUCT_LOOKUP.items():
    packs = list(_PRICE_CATALOG.get(name, {}).keys())
    if packs:
        product["packs"] = packs


@dataclass(frozen=True)
class QuoteItem:
    """Immutable container describing a single line on the quotation."""

    product_id: str
    product_name: str
    pack: str
    quantity: Decimal
    unit_price: Decimal
    discount_pct: Decimal
    line_net: Decimal

    def as_dict(self) -> dict:
        """Return a plain ``dict`` for serialization/UI rendering."""

        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "pack": self.pack,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "discount_pct": self.discount_pct,
            "line_net": self.line_net,
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
    if not Decimal("0") <= discount <= Decimal("100"):
        raise ValueError("Discount must be between 0 and 100 percent")

    unit_price = pack_prices[pack]
    line_gross = unit_price * quantity
    discount_multiplier = (Decimal("100") - discount) / Decimal("100")
    line_net = (line_gross * discount_multiplier).quantize(
        MONEY_QUANT, rounding=ROUND_HALF_UP
    )

    product = _PRODUCT_LOOKUP.get(product_id)
    product_name = product.get("product_name") if product else product_id

    item = QuoteItem(
        product_id=product_id,
        product_name=product_name,
        pack=pack,
        quantity=quantity,
        unit_price=unit_price,
        discount_pct=discount,
        line_net=line_net,
    )
    return item.as_dict()


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
]
