"""Utilities for working with National Paints price list data."""
from __future__ import annotations

from collections import OrderedDict
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

_PRICE_DATA: Dict[str, Dict[str, object]] | None = None


def _price_list_path() -> Path:
    """Return the path to the bundled National Paints price list JSON."""
    return Path(__file__).resolve().parents[2] / "pricelistnationalpaints.json"


def _normalize_price(value: object) -> float:
    """Normalize a price value to a float in AED.

    The price list occasionally mixes formatting (strings with currency symbols,
    comma separated thousands, etc.).  This helper converts any supported value
    into a float so callers always receive a consistent representation.
    """

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Price string is empty")

        cleaned = cleaned.lower().replace("aed", "")
        cleaned = cleaned.replace(",", "")
        cleaned = re.sub(r"[^0-9.\-]", "", cleaned)

        if cleaned in {"", ".", "-", "-.", ".-"}:
            raise ValueError(f"Could not parse price value: {value!r}")

        try:
            return float(cleaned)
        except ValueError as exc:
            raise ValueError(f"Could not parse price value: {value!r}") from exc

    raise TypeError(f"Unsupported price value type: {type(value)!r}")


def _normalize_size_key(size: object) -> str:
    """Create a canonical key for a size label."""
    text = str(size or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def _load_price_data() -> Dict[str, Dict[str, object]]:
    """Load and cache the price list keyed by product code."""
    global _PRICE_DATA

    if _PRICE_DATA is not None:
        return _PRICE_DATA

    with _price_list_path().open("r", encoding="utf-8") as price_file:
        raw_data = json.load(price_file)

    default_currency = str(raw_data.get("currency", "AED")).upper()
    price_data: Dict[str, Dict[str, object]] = {}

    for category in raw_data.get("product_categories", []):
        for subcategory in category.get("subcategories", []):
            for product in subcategory.get("products", []):
                code = str(product.get("product_code", "")).strip()
                if not code:
                    continue

                entry = price_data.setdefault(
                    code.upper(),
                    {
                        "product_names": [],
                        "currency": default_currency,
                        "prices": OrderedDict(),
                    },
                )

                product_name = product.get("product_name")
                if isinstance(product_name, str) and product_name and product_name not in entry["product_names"]:
                    entry["product_names"].append(product_name)

                prices = product.get("prices", [])
                if not isinstance(prices, list):
                    continue

                for price_entry in prices:
                    if not isinstance(price_entry, dict):
                        continue

                    size_label = price_entry.get("size")
                    if not size_label:
                        continue

                    normalized_price = _normalize_price(price_entry.get("price"))
                    size_key = _normalize_size_key(size_label)

                    entry["prices"][size_key] = {
                        "size": str(size_label).strip(),
                        "price": normalized_price,
                        "currency": default_currency,
                    }

    _PRICE_DATA = price_data
    return _PRICE_DATA


def list_sizes(code: str) -> List[str]:
    """Return the list of size labels available for a given product code."""
    entry = _load_price_data().get(str(code).strip().upper())
    if not entry:
        return []

    return [info["size"] for info in entry["prices"].values()]


def get_price(code: str, size: str) -> Optional[float]:
    """Fetch the AED price for a given product code and size.

    Parameters
    ----------
    code:
        Product code from the National Paints price list.
    size:
        Size label as listed in the price list.  The lookup is
        case-insensitive and ignores extra whitespace for convenience.

    Returns
    -------
    Optional[float]
        The price in AED if the product and size are known, otherwise ``None``.
    """

    entry = _load_price_data().get(str(code).strip().upper())
    if not entry:
        return None

    size_key = _normalize_size_key(size)
    size_info = entry["prices"].get(size_key)
    if not size_info:
        return None

    return float(size_info["price"])


__all__ = ["get_price", "list_sizes"]
