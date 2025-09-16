#!/usr/bin/env python3
"""Utility to ensure product codes are unique within the price list."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Iterable, List


def iter_product_codes(data: dict) -> Iterable[str]:
    """Yield each product code from the nested price list structure."""
    for category in data.get("product_categories", []):
        for subcategory in category.get("subcategories", []):
            for product in subcategory.get("products", []):
                code = product.get("product_code")
                if code is not None:
                    yield code


def load_codes(file_path: Path) -> List[str]:
    """Load all product codes from the provided JSON file."""
    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return list(iter_product_codes(payload))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate product codes in a National Paints price list.")
    parser.add_argument(
        "price_list",
        nargs="?",
        default="pricelistnationalpaints.json",
        help="Path to the price list JSON file (defaults to pricelistnationalpaints.json).",
    )
    args = parser.parse_args()

    price_list_path = Path(args.price_list)
    if not price_list_path.exists():
        parser.error(f"Price list file not found: {price_list_path}")

    codes = load_codes(price_list_path)
    counts = Counter(codes)
    duplicates = {code: count for code, count in counts.items() if count > 1}

    print(f"Total products: {len(codes)}")
    if duplicates:
        print("Duplicate product codes detected:")
        for code, count in sorted(duplicates.items()):
            print(f"  {code}: {count}")
        return 1

    print("No duplicate product codes found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
