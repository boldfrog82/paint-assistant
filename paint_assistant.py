"""Utilities for working with the National Paints product datasets."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Mapping, MutableMapping

# Paths to the JSON datasets distributed with the repository.
BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_PATH = BASE_DIR / "paint_products.json"
PRICELIST_PATH = BASE_DIR / "pricelistnationalpaints.json"


def load_products(path: str | Path = PRODUCTS_PATH) -> list:
    """Load the structured product data from :mod:`paint_products.json`.

    Parameters
    ----------
    path:
        Optional override for the file location. The default points to the copy
        tracked in the repository.

    Returns
    -------
    list
        A nested list of dictionaries describing the available paint products.
    """

    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _iter_price_products(price_data: Mapping) -> Iterable[MutableMapping[str, object]]:
    """Yield the product dictionaries from a price list payload."""

    for category in price_data.get("product_categories", []):
        for subcategory in category.get("subcategories", []):
            yield from subcategory.get("products", [])


def load_pricelist(path: str | Path = PRICELIST_PATH) -> Mapping[str, object]:
    """Load the price list JSON document into a Python mapping."""

    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def get_price(product_code: str, size: str, *, price_data: Mapping[str, object] | None = None) -> float:
    """Return the price for a product *code* and *size* combination.

    Parameters
    ----------
    product_code:
        The product code as listed in :mod:`pricelistnationalpaints.json`.
    size:
        The size entry to look up (for example, ``"18 Ltr (Drum)"``).
    price_data:
        Optionally provide a pre-loaded price list structure to avoid reloading
        the JSON file for repeated lookups.

    Raises
    ------
    KeyError
        If the product code or size is not present in the dataset.
    """

    if price_data is None:
        price_data = load_pricelist()

    for product in _iter_price_products(price_data):
        if product.get("product_code") != product_code:
            continue
        for entry in product.get("prices", []):
            if entry.get("size") == size:
                return float(entry["price"])
        raise KeyError(f"Size {size!r} not found for product code {product_code!r}")

    raise KeyError(f"Product code {product_code!r} not found in price list")


def list_sizes(product_code: str, *, price_data: Mapping[str, object] | None = None) -> List[str]:
    """Return the available package sizes for *product_code*.

    Parameters
    ----------
    product_code:
        The product code to search for in the price list.
    price_data:
        Optionally provide a pre-loaded price list structure to avoid reloading
        the JSON file.

    Raises
    ------
    KeyError
        If the product code is not present in the dataset.
    """

    if price_data is None:
        price_data = load_pricelist()

    for product in _iter_price_products(price_data):
        if product.get("product_code") == product_code:
            return [entry.get("size", "") for entry in product.get("prices", [])]

    raise KeyError(f"Product code {product_code!r} not found in price list")
