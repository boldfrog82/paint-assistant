"""Utilities for accessing paint pricing information."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PRICES_FILE = _REPO_ROOT / "pricelistnationalpaints.json"


def _load_raw_prices() -> Dict[str, Any]:
    with _PRICES_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _prices_payload() -> Dict[str, Any]:
    return _load_raw_prices()


def _flatten_price_products(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    products: List[Dict[str, Any]] = []
    for category in payload.get("product_categories", []):
        for subcategory in category.get("subcategories", []):
            products.extend(subcategory.get("products", []))
    return products


@lru_cache(maxsize=1)
def _products_by_code() -> Dict[str, Dict[str, Any]]:
    return {
        product["product_code"].upper(): product
        for product in _flatten_price_products(_prices_payload())
        if product.get("product_code")
    }


def get_currency() -> str:
    return _prices_payload().get("currency", "")


def get_product_by_code(code: str) -> Optional[Dict[str, Any]]:
    if not code:
        return None
    return _products_by_code().get(code.strip().upper())


def list_available_sizes(code: str) -> List[str]:
    product = get_product_by_code(code)
    if not product:
        return []
    return [price.get("size", "") for price in product.get("prices", []) if price.get("size")]


def _normalize_size(value: str) -> str:
    return " ".join(value.strip().lower().split())


def lookup_price(code: str, size: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], str]:
    product = get_product_by_code(code)
    currency = get_currency()
    if not product:
        return None, None, currency

    normalized_size = _normalize_size(size) if size else ""
    for price_entry in product.get("prices", []):
        size_label = price_entry.get("size")
        if size_label and _normalize_size(size_label) == normalized_size:
            return product, price_entry, currency

    return product, None, currency


__all__ = [
    "get_currency",
    "get_product_by_code",
    "list_available_sizes",
    "lookup_price",
]
