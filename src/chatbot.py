"""Command line chatbot for paint product information."""

from __future__ import annotations

import re
from typing import Optional, Sequence, Tuple

try:  # pragma: no cover - allow running both as a module and as a script.
    from .chatbot_config import ChatbotConfig, DEFAULT_CONFIG
    from .data.products import find_product_by_name, summarize_product
    from .data.prices import list_available_sizes, lookup_price
except ImportError:  # pragma: no cover - fallback for direct script execution.
    from chatbot_config import ChatbotConfig, DEFAULT_CONFIG  # type: ignore
    from data.products import find_product_by_name, summarize_product  # type: ignore
    from data.prices import list_available_sizes, lookup_price  # type: ignore


_ABOUT_RE = re.compile(r"^\s*tell me about\s+(.+?)[\.!?]*\s*$", re.IGNORECASE)
_IN_SPLIT_RE = re.compile(r"\bin\b", re.IGNORECASE)
_TRAILING_PUNCTUATION = " .,!?;:"


def _normalise_whitespace(text: str) -> str:
    return " ".join(text.strip().split())


def _strip_trailing_punctuation(text: str) -> str:
    return text.rstrip(_TRAILING_PUNCTUATION)


def _remove_filler_tokens(text: str, filler_words: Sequence[str]) -> str:
    cleaned = text
    for filler in sorted({word.strip() for word in filler_words if word}, key=len, reverse=True):
        pattern = re.compile(rf"\b{re.escape(filler)}\b", re.IGNORECASE)
        cleaned = pattern.sub(" ", cleaned)
    return _normalise_whitespace(cleaned)


def _choose_code_token(tokens: Sequence[str]) -> Tuple[str, int]:
    """Return the most likely product code token and its index."""

    best_digit_idx = None
    best_digit_token = ""
    best_any_idx = None
    best_any_token = ""

    for index in range(len(tokens) - 1, -1, -1):
        token = tokens[index]
        cleaned = _strip_trailing_punctuation(token)
        if not cleaned:
            continue

        if best_any_idx is None:
            best_any_idx = index
            best_any_token = cleaned

        if any(char.isdigit() for char in cleaned):
            if any(char.isalpha() for char in cleaned):
                return cleaned, index
            if best_digit_idx is None:
                best_digit_idx = index
                best_digit_token = cleaned

    if best_digit_idx is not None:
        return best_digit_token, best_digit_idx

    if best_any_idx is not None:
        return best_any_token, best_any_idx

    return "", -1


def _extract_code_and_size(text: str) -> Optional[Tuple[str, str, bool]]:
    value = _strip_trailing_punctuation(text.strip())
    if not value:
        return None

    in_match = _IN_SPLIT_RE.search(value)
    if in_match:
        prefix = _strip_trailing_punctuation(value[: in_match.start()].strip())
        suffix = _strip_trailing_punctuation(value[in_match.end() :].strip())
        if prefix:
            tokens = prefix.split()
            code, _ = _choose_code_token(tokens)
            if not code:
                return None
            return code, suffix, False

    tokens = value.split()
    if not tokens:
        return None

    code, index = _choose_code_token(tokens)
    if not code:
        return None

    remainder_tokens = tokens[index + 1 :]
    remainder = " ".join(remainder_tokens).strip()
    remainder = _strip_trailing_punctuation(remainder)
    return code, remainder, True


def _parse_price_query(message: str, config: ChatbotConfig) -> Optional[Tuple[str, str]]:
    normalised = _normalise_whitespace(message)
    lowered = normalised.lower()

    for trigger in config.price_triggers:
        trigger = trigger.strip().lower()
        if not trigger:
            continue
        if not lowered.startswith(trigger):
            continue

        remainder = normalised[len(trigger) :].strip()
        if not remainder:
            continue

        remainder = _strip_trailing_punctuation(remainder)
        if not remainder:
            continue

        remainder = _remove_filler_tokens(remainder, config.filler_words)
        if not remainder:
            continue

        digits_present = any(char.isdigit() for char in remainder)
        extracted = _extract_code_and_size(remainder)
        if not extracted:
            continue

        code, size, used_fallback = extracted
        if not code:
            continue

        if used_fallback and digits_present and not any(char.isdigit() for char in code):
            continue

        return code, size

    return None


def parse_price_prompt(
    message: str,
    *,
    config: Optional[ChatbotConfig] = None,
) -> Optional[Tuple[str, str]]:
    """Return (code, size) when the prompt looks like a price query."""

    if config is None:
        config = DEFAULT_CONFIG
    return _parse_price_query(message, config)


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


def respond_to(message: str, *, config: Optional[ChatbotConfig] = None) -> str:
    message = message.strip()
    if not message:
        return "Please enter a question about a product or its price."

    about_match = _ABOUT_RE.match(message)
    if about_match:
        product_name = about_match.group(1)
        return _handle_about(product_name)

    if config is None:
        config = DEFAULT_CONFIG

    price_query = _parse_price_query(message, config)
    if price_query:
        product_code, size = price_query
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


__all__ = ["respond_to", "run_cli", "parse_price_prompt", "main"]
