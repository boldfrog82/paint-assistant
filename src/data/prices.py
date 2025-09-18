"""Utilities for working with National Paints price list data."""
from __future__ import annotations

from collections import OrderedDict
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

_PRICE_DATA: Dict[str, Dict[str, object]] | None = None

_DASH_TRANSLATION = str.maketrans(
    {
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
    }
)


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
        cleaned = re.sub(r"/-\s*$", "", cleaned)
        cleaned = cleaned.strip()
        cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
        cleaned = cleaned.rstrip("-")

        if cleaned in {"", ".", "-", "-.", ".-"}:
            raise ValueError(f"Could not parse price value: {value!r}")

        try:
            return float(cleaned)
        except ValueError as exc:
            raise ValueError(f"Could not parse price value: {value!r}") from exc

    raise TypeError(f"Unsupported price value type: {type(value)!r}")


def _normalize_size_key(size: object) -> str:
    """Create a canonical key for a size label."""

    text = str(size or "")
    text = text.translate(_DASH_TRANSLATION)
    text = text.strip().lower()
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

                prices_field = product.get("prices")
                price_sources: List[tuple[Optional[str], List[dict]]] = []

                if isinstance(prices_field, list) and prices_field:
                    price_sources.append((None, prices_field))
                else:
                    variants = product.get("variants", [])
                    if isinstance(variants, list):
                        for variant in variants:
                            if not isinstance(variant, dict):
                                continue

                            variant_name = variant.get("variant_name")
                            variant_prices = variant.get("prices", [])
                            if not isinstance(variant_prices, list) or not variant_prices:
                                continue

                            price_sources.append((variant_name, variant_prices))

                if not price_sources:
                    continue

                for variant_name, prices in price_sources:
                    variant_label = ""
                    if variant_name is not None:
                        variant_label = str(variant_name).strip()

                    for price_entry in prices:
                        if not isinstance(price_entry, dict):
                            continue

                        size_label_value = price_entry.get("size")
                        if not size_label_value:
                            continue

                        size_label = str(size_label_value).strip()
                        combined_label = size_label
                        if variant_label:
                            combined_label = f"{variant_label} – {size_label}"

                        normalized_price = _normalize_price(price_entry.get("price"))
                        size_key = _normalize_size_key(combined_label)

                        entry["prices"][size_key] = {
                            "size": combined_label,
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
