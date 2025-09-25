codex/create-product-quotation-tool-nnzhnd
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

"""Interactive quotation builder for National Paints products.

The tool loads the price list contained in ``pricelistnationalpaints.json`` and
allows the user to create a quotation interactively from the terminal. It
supports product name suggestions, selection of available pack sizes, optional
per-line discounts, and applies the mandatory 5% tax to the final amount.

Usage::

    python quotation_tool.py

The program is intentionally lightweight so it can run in environments without
additional dependencies.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

PRICE_LIST_FILE = Path(__file__).with_name("pricelistnationalpaints.json")
SUGGESTION_LIMIT = 7
TAX_RATE = 0.05  # 5%


@dataclass
class PriceOption:
    size: str
    price: float


@dataclass
class Product:
    name: str
    code: str | None
    category: str
    subcategory: str
    prices: List[PriceOption]


@dataclass
class SelectedItem:
    product: Product
    price_option: PriceOption
    quantity: float
    discount_percent: float

    @property
    def line_total(self) -> float:
        return self.quantity * self.price_option.price

    @property
    def discount_amount(self) -> float:
        return self.line_total * self.discount_percent / 100

    @property
    def net_total(self) -> float:
        return self.line_total - self.discount_amount


class QuotationBuilder:
    def __init__(self, products: Sequence[Product]):
        self.products = list(products)

    def run(self) -> None:
        if not self.products:
            print("No products available in the price list. Aborting.")
            return

        selected_items: List[SelectedItem] = []
        print("\nQuotation Builder (type 'exit' at any prompt to finish)\n")

        while True:
            product = self.prompt_for_product()
            if product is None:
                break

            price_option = self.prompt_for_price_option(product)
            if price_option is None:
                # User chose to go back and search again.
                continue
            if price_option is False:  # type: ignore[truthy-bool]
                break

            quantity = self.prompt_for_number(
                prompt="Enter quantity (default 1): ",
                default=1.0,
                allow_zero=False,
            )
            if quantity is None:
                break

            discount = self.prompt_for_number(
                prompt="Enter discount percentage (default 0): ",
                default=0.0,
                allow_zero=True,
                min_value=0.0,
                max_value=100.0,
            )
            if discount is None:
                break

            selected_items.append(
                SelectedItem(
                    product=product,
                    price_option=price_option,
                    quantity=quantity,
                    discount_percent=discount,
                )
            )

            add_more = input("Add another product? [Y/n]: ").strip().lower()
            if add_more in {"n", "no", "exit"}:
                break

        if selected_items:
            self.print_summary(selected_items)
        else:
            print("No items selected. Nothing to do.")

    # ------------------------------------------------------------------
    def prompt_for_product(self) -> Product | None:
        while True:
            query = input("Search product name (leave blank to finish): ").strip()
            if not query:
                return None
            if query.lower() == "exit":
                return None

            suggestions = suggest_products(self.products, query, SUGGESTION_LIMIT)
            if not suggestions:
                print("No matching products found. Try another search term.\n")
                continue

            print("\nSuggestions:")
            for idx, product in enumerate(suggestions, start=1):
                code = f" [{product.code}]" if product.code else ""
                print(
                    f"  {idx}. {product.name}{code} — {product.category} / {product.subcategory}"
                )

            selection = self.prompt_for_choice(
                "Select a product by number (or press Enter to search again): ",
                len(suggestions),
            )
            if selection is None:
                print()
                continue
            if selection is False:  # type: ignore[truthy-bool]
                return None

            return suggestions[selection]

    def prompt_for_price_option(self, product: Product) -> PriceOption | bool | None:
        if not product.prices:
            print("Selected product has no price options. Please choose another product.\n")
            return None

        while True:
            print(f"\nAvailable pack sizes for {product.name}:")
            for idx, option in enumerate(product.prices, start=1):
                print(f"  {idx}. {option.size} — {option.price:.2f} AED")

            selection = self.prompt_for_choice(
                "Select a pack size by number (Enter to reselect product, 'exit' to finish): ",
                len(product.prices),
            )
            if selection is None:
                print()
                return None
            if selection is False:  # type: ignore[truthy-bool]
                return False

            return product.prices[selection]

    def prompt_for_choice(self, prompt: str, max_index: int) -> int | bool | None:
        value = input(prompt).strip()
        if not value or value.lower() == "exit":
            return None if not value else False

        if not value.isdigit():
            print("Please enter a valid number.")
            return self.prompt_for_choice(prompt, max_index)

        index = int(value)
        if not 1 <= index <= max_index:
            print(f"Enter a number between 1 and {max_index}.")
            return self.prompt_for_choice(prompt, max_index)

        return index - 1

    def prompt_for_number(
        self,
        prompt: str,
        default: float,
        allow_zero: bool,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> float | None:
        value = input(prompt).strip()
        if not value:
            return default
        if value.lower() == "exit":
            return None

        try:
            number = float(value)
        except ValueError:
            print("Please enter a numeric value.")
            return self.prompt_for_number(prompt, default, allow_zero, min_value, max_value)

        if not allow_zero and number == 0:
            print("Zero is not allowed for this field.")
            return self.prompt_for_number(prompt, default, allow_zero, min_value, max_value)
        if min_value is not None and number < min_value:
            print(f"Value must be at least {min_value}.")
            return self.prompt_for_number(prompt, default, allow_zero, min_value, max_value)
        if max_value is not None and number > max_value:
            print(f"Value must not exceed {max_value}.")
            return self.prompt_for_number(prompt, default, allow_zero, min_value, max_value)

        return number

    def print_summary(self, items: Iterable[SelectedItem]) -> None:
        print("\nQuotation Summary")
        print("=" * 80)

        header = (
            f"{'Product':35}  {'Pack Size':15}  {'Qty':>6}  {'Unit Price':>12}  "
            f"{'Line Total':>12}  {'Discount':>10}  {'Net':>12}"
        )
        print(header)
        print("-" * len(header))

        subtotal = 0.0
        total_discount = 0.0
        for item in items:
            subtotal += item.line_total
            total_discount += item.discount_amount
            name = truncate(item.product.name, 35)
            size = truncate(item.price_option.size, 15)
            print(
                f"{name:35}  {size:15}  {item.quantity:>6.2f}  {item.price_option.price:>12.2f}  "
                f"{item.line_total:>12.2f}  {item.discount_amount:>10.2f}  {item.net_total:>12.2f}"
            )

        taxable_amount = subtotal - total_discount
        tax = taxable_amount * TAX_RATE
        total_due = taxable_amount + tax

        print("-" * len(header))
        print(f"{'Subtotal':>74}: {subtotal:>12.2f} AED")
        print(f"{'Total Discount':>74}: {total_discount:>12.2f} AED")
        print(f"{'Taxable Amount':>74}: {taxable_amount:>12.2f} AED")
        print(f"{'VAT (5%)':>74}: {tax:>12.2f} AED")
        print(f"{'Grand Total':>74}: {total_due:>12.2f} AED")
        print("=" * 80)
        print("\nThank you!\n")


# ---------------------------------------------------------------------------
def suggest_products(
    products: Sequence[Product], query: str, limit: int = SUGGESTION_LIMIT
) -> List[Product]:
    """Return a list of suggested products for *query*.

    Suggestions prioritise products where the query appears earlier in the name
    and shorter names, producing a behaviour similar to a search engine's
    auto-complete suggestions. Results are limited to ``limit`` items.
    """

    query_lower = query.lower()
    matches: List[tuple[int, int, Product]] = []
    for product in products:
        name_lower = product.name.lower()
        idx = name_lower.find(query_lower)
        if idx != -1:
            matches.append((idx, len(product.name), product))

    matches.sort(key=lambda item: (item[0], item[1], item[2].name))
    return [product for *_rest, product in matches[:limit]]


def load_products(path: Path = PRICE_LIST_FILE) -> List[Product]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except OSError as exc:
        print(f"Failed to read price list: {exc}")
        sys.exit(1)

    products: List[Product] = []
    for category in data.get("product_categories", []):
        category_name = category.get("category_name", "Unknown Category")
        for subcategory in category.get("subcategories", []):
            subcategory_name = subcategory.get("subcategory_name", "General")
            for product_data in subcategory.get("products", []):
                prices = [
                    PriceOption(size=price.get("size", ""), price=float(price.get("price", 0)))
                    for price in product_data.get("prices", [])
                    if price.get("size") and price.get("price") is not None
                ]
                products.append(
                    Product(
                        name=product_data.get("product_name", "Unnamed Product"),
                        code=product_data.get("product_code"),
                        category=category_name,
                        subcategory=subcategory_name,
                        prices=prices,
                    )
                )
    return products


def truncate(value: str, width: int) -> str:
    return value if len(value) <= width else value[: width - 1] + "…"


def main() -> None:
    products = load_products()
    builder = QuotationBuilder(products)
    try:
        builder.run()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting without saving.")
Codex


if __name__ == "__main__":
    main()
