"""Command line chatbot for paint product information."""

from __future__ import annotations

import re

try:  # pragma: no cover - allow running both as a module and as a script.
    from .data.products import find_product_by_name, summarize_product
    from .data.prices import list_available_sizes, lookup_price
except ImportError:  # pragma: no cover - fallback for direct script execution.
    from data.products import find_product_by_name, summarize_product  # type: ignore
    from data.prices import list_available_sizes, lookup_price  # type: ignore


_ABOUT_RE = re.compile(r"^\s*tell me about\s+(.+?)[\.!?]*\s*$", re.IGNORECASE)
_PRICE_RE = re.compile(r"^\s*how much is\s+([A-Za-z0-9]+)\s+in\s+(.+?)[\.!?]*\s*$", re.IGNORECASE)


def _handle_about(product_name: str) -> str:
    product = find_product_by_name(product_name)
    if not product:
        return f"I couldn't find a product named \"{product_name.strip()}\"."

    summary = summarize_product(product)
    name = product.get("product_name", product_name).strip()
    return f"{name}\n{summary}"


def _handle_price(product_code: str, size: str) -> str:
    product, price_entry, currency = lookup_price(product_code, size)
    if product is None:
        return f"I couldn't find a product with the code \"{product_code.strip()}\"."

    if price_entry is None:
        available_sizes = list_available_sizes(product_code)
        if available_sizes:
            choices = ", ".join(available_sizes)
            return (
                f"I couldn't find the size \"{size.strip()}\" for {product['product_name']} (code {product['product_code']}). "
                f"Available sizes are: {choices}."
            )
        return f"I couldn't find size details for {product['product_name']} (code {product['product_code']})."

    price_value = price_entry.get("price")
    size_label = price_entry.get("size", size.strip())
    if price_value is None:
        return (
            f"The price for {product['product_name']} (code {product['product_code']}) in {size_label} isn't listed."
        )

    formatted_price = f"{price_value:,.2f}"
    currency_label = currency.strip()
    if currency_label:
        formatted_price = f"{formatted_price} {currency_label}"

    return (
        f"{product['product_name']} (code {product['product_code']}) costs {formatted_price} for {size_label}."
    )


def respond_to(message: str) -> str:
    message = message.strip()
    if not message:
        return "Please enter a question about a product or its price."

    about_match = _ABOUT_RE.match(message)
    if about_match:
        product_name = about_match.group(1)
        return _handle_about(product_name)

    price_match = _PRICE_RE.match(message)
    if price_match:
        product_code, size = price_match.groups()
        return _handle_price(product_code, size)

    return (
        "I'm not sure how to help with that. Try asking 'Tell me about <product name>' or "
        "'How much is <product code> in <size>?'."
    )


def run_cli() -> None:
    print("Paint Assistant Chatbot")
    print("Ask me about a product or a price. Type 'exit' or 'quit' to leave.\n")

    while True:
        try:
            user_input = input("You: ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\nAssistant: Goodbye!")
            return

        if user_input.strip().lower() in {"exit", "quit"}:
            print("Assistant: Goodbye!")
            break

        response = respond_to(user_input)
        print(f"Assistant: {response}")


def main() -> None:
    run_cli()


if __name__ == "__main__":
    main()
