"""Interactive terminal quotation builder using the National Paints catalogue."""
from __future__ import annotations

from decimal import Decimal
from typing import List

from app.core.quote import (
    compute_totals,
    find_matching_products,
    format_aed,
    load_price_catalog,
    quote_row,
)

PRICE_CATALOG = load_price_catalog()


def _prompt(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:  # pragma: no cover - user pressed Ctrl-D
        print()
        return ""


def _choose_from_list(options: List[str], prompt_text: str) -> str | None:
    if not options:
        return None
    for idx, option in enumerate(options, 1):
        print(f"  {idx}. {option}")
    while True:
        choice = _prompt(prompt_text).strip()
        if not choice:
            return None
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(options):
                return options[index - 1]
        print("Please enter a valid number from the list or leave blank to cancel.")


def _prompt_quantity() -> Decimal | None:
    while True:
        raw = _prompt("Quantity (blank to cancel): ").strip()
        if not raw:
            return None
        try:
            value = Decimal(raw)
        except Exception:
            print("Enter a numeric quantity.")
            continue
        if value <= 0:
            print("Quantity must be greater than zero.")
            continue
        return value


def _prompt_discount() -> Decimal:
    while True:
        raw = _prompt("Discount % [0-100] (default 0): ").strip()
        if not raw:
            return Decimal("0")
        try:
            value = Decimal(raw)
        except Exception:
            print("Enter a numeric percentage between 0 and 100.")
            continue
        if not Decimal("0") <= value <= Decimal("100"):
            print("Discount must be between 0 and 100 percent.")
            continue
        return value


def main() -> None:
    print("Paint quotation assistant")
    print("Type part of a product name to see suggestions. Press Enter on an empty line to finish.\n")

    items: List[dict] = []

    while True:
        query = _prompt("Search product (blank to finish): ").strip()
        if not query:
            break

        matches = find_matching_products(query)
        if not matches:
            print("No products matched your search. Try a different term.\n")
            continue

        product_names = [product.get("product_name", "") for product in matches]
        print("Matches:")
        selected_name = _choose_from_list(product_names, "Choose a product number (blank to search again): ")
        if not selected_name:
            print()
            continue

        packs = list(PRICE_CATALOG.get(selected_name, {}).keys())
        if not packs:
            print("No pricing data available for that product.\n")
            continue

        print("Available pack sizes:")
        pack_choice = _choose_from_list(packs, "Select pack size (blank to cancel): ")
        if not pack_choice:
            print()
            continue

        quantity = _prompt_quantity()
        if quantity is None:
            print()
            continue

        discount = _prompt_discount()

        try:
            item = quote_row(selected_name, pack_choice, quantity, discount)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"Could not add line: {exc}\n")
            continue

        unit_price = PRICE_CATALOG[selected_name][pack_choice]
        print(
            f"Added {selected_name} ({pack_choice}) x {quantity} at {format_aed(unit_price)} each, "
            f"discount {discount}%"
        )
        print(f"Line total: {format_aed(item['line_net'])}\n")
        items.append(item)

    if not items:
        print("No items added. Goodbye!")
        return

    subtotal, vat, total = compute_totals(items)

    print("Quotation summary:\n")
    for item in items:
        print(
            f"- {item['product_name']} ({item['pack']}) x {item['quantity']} "
            f"@ {format_aed(item['unit_price'])} less {item['discount_pct']}% -> {format_aed(item['line_net'])}"
        )
    print()
    print(f"Subtotal: {format_aed(subtotal)}")
    print(f"VAT (5%): {format_aed(vat)}")
    print(f"Total: {format_aed(total)}")


if __name__ == "__main__":
    main()
