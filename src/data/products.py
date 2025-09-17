"""Utilities for accessing paint product metadata."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

# Paths ---------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PRODUCTS_FILE = _REPO_ROOT / "paint_products.json"


# Data loading ---------------------------------------------------------------

def _load_raw_products() -> Any:
    """Load the raw nested JSON payload for products."""
    with _PRODUCTS_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


def _flatten_products(payload: Any) -> List[Dict[str, Any]]:
    """Flatten the nested payload into individual product dictionaries."""
    products: List[Dict[str, Any]] = []
    stack: List[Any] = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if "product_name" in current:
                products.append(current)
            for value in current.values():
                stack.append(value)
        elif isinstance(current, list):
            stack.extend(current)
    return products


@lru_cache(maxsize=1)
def get_all_products() -> List[Dict[str, Any]]:
    """Return a list of all products defined in the dataset."""
    return _flatten_products(_load_raw_products())


# Helpers -------------------------------------------------------------------

def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, list):
        parts = [_stringify(item) for item in value if item]
        return "; ".join(part for part in parts if part)
    if isinstance(value, dict):
        parts = []
        for key, inner_value in value.items():
            text = _stringify(inner_value)
            if text:
                nice_key = key.replace("_", " ").replace("-", " ").strip().capitalize()
                parts.append(f"{nice_key}: {text}")
        return "; ".join(parts)
    return str(value)


# Public API ----------------------------------------------------------------


def find_product_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Return the product dictionary for *name* if available."""
    if not name:
        return None

    normalized_query = _normalize_text(name)
    products = get_all_products()

    # First try exact match ignoring case and spacing differences.
    for product in products:
        if _normalize_text(product.get("product_name", "")) == normalized_query:
            return product

    # Fallback to partial match.
    for product in products:
        if normalized_query in _normalize_text(product.get("product_name", "")):
            return product

    return None


def list_product_names() -> List[str]:
    """Return all product names available in the dataset."""
    return [product.get("product_name", "") for product in get_all_products() if product.get("product_name")]


def summarize_product(product: Dict[str, Any]) -> str:
    """Create a readable summary for a product dictionary."""
    description = product.get("description") or product.get("product_description")
    uses = product.get("uses") or product.get("usage") or product.get("usage_data")
    advantages = product.get("advantages") or product.get("advantages_and_intended_use")

    parts: List[str] = []
    if description:
        parts.append(_stringify(description))
    if uses:
        parts.append(f"Uses: {_stringify(uses)}")
    if advantages:
        parts.append(f"Advantages: {_stringify(advantages)}")

    if not parts:
        return "No summary is available for this product."

    return "\n".join(parts)


__all__ = [
    "find_product_by_name",
    "get_all_products",
    "list_product_names",
    "summarize_product",
]
