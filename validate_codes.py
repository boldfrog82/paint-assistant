"""Utility script to validate product codes in the price list dataset."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, Iterable

from paint_assistant import (
    PRICELIST_PATH,
    _iter_price_products,
    _normalize_product_code,
    load_pricelist,
)


def _collect_product_codes(price_data: dict) -> Iterable[str]:
    """Yield all product codes from the price data structure."""

    for product in _iter_price_products(price_data):
        code = product.get("product_code")
        if isinstance(code, str):
            normalized = _normalize_product_code(code)
            if normalized:
                yield normalized


def find_duplicate_codes(path: str | Path = PRICELIST_PATH) -> Dict[str, int]:
    """Return a mapping of duplicate product codes to their counts."""

    price_data = load_pricelist(path)
    counts = Counter(_collect_product_codes(price_data))
    return {code: count for code, count in counts.items() if count > 1}


def main() -> None:
    """Print duplicate product codes, if any."""

    duplicates = find_duplicate_codes()
    if not duplicates:
        print("No duplicate product codes found.")
        return

    print("Duplicate product codes detected:")
    for code, count in sorted(duplicates.items()):
        print(f"- {code}: {count} occurrences")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
