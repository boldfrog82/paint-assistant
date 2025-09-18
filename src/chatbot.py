"""Command line chatbot for paint product information."""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

try:  # pragma: no cover - optional dependency during tests.
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover - fallback matcher used in CI.
    from difflib import SequenceMatcher

    class _FallbackFuzz:
        """Lightweight stand-in for :mod:`rapidfuzz.fuzz`."""

        @staticmethod
        def _ratio(a: str, b: str) -> int:
            return int(SequenceMatcher(None, str(a), str(b)).ratio() * 100)

        WRatio = _ratio
        partial_ratio = _ratio
        token_set_ratio = _ratio

    class _FallbackProcess:
        """Simplified :mod:`rapidfuzz.process` replacement."""

        @staticmethod
        def extract(
            query: str,
            choices: Sequence[str],
            processor=None,
            scorer=None,
            score_cutoff: int = 0,
            limit: int = 5,
        ) -> List[Tuple[str, int, int]]:
            if processor is not None:
                processed_query = processor(query)
                processed_choices = [(choice, processor(choice)) for choice in choices]
            else:
                processed_query = query
                processed_choices = [(choice, choice) for choice in choices]

            scorer_fn = scorer or _FallbackFuzz._ratio
            results: List[Tuple[str, int, int]] = []
            for original, processed in processed_choices:
                score = int(scorer_fn(processed_query, processed))
                if score >= score_cutoff:
                    results.append((original, score, 0))

            results.sort(key=lambda item: item[1], reverse=True)
            return results[:limit]

    fuzz = _FallbackFuzz  # type: ignore
    process = _FallbackProcess  # type: ignore

try:  # pragma: no cover - allow running both as a module and as a script.
    from .chatbot_config import ChatbotConfig, DEFAULT_CONFIG
    from .data.products import (
        find_product_by_name,
        get_all_products,
        list_product_names,
        summarize_product,
    )
    from .data.prices import list_available_sizes, list_product_codes, lookup_price
except ImportError:  # pragma: no cover - fallback for direct script execution.
    from chatbot_config import ChatbotConfig, DEFAULT_CONFIG  # type: ignore
    from data.products import (  # type: ignore
        find_product_by_name,
        get_all_products,
        list_product_names,
        summarize_product,
    )
    from data.prices import list_available_sizes, list_product_codes, lookup_price  # type: ignore


_ABOUT_RE = re.compile(r"^\s*tell me about\s+(.+?)[\.!?]*\s*$", re.IGNORECASE)
_PRICE_RE = re.compile(
    r"^\s*how much is\s+([A-Za-z0-9-]+)\s+(?:in|for)\s+(.+?)[\.!?]*\s*$",
    re.IGNORECASE,
)
_PRICE_PATTERNS: Sequence[re.Pattern[str]] = (
    re.compile(r"(?P<code>[A-Za-z0-9-]+)\s+(?:in|for|at)\s+(?P<size>.+)", re.IGNORECASE),
    re.compile(r"(?P<size>.+?)\s+(?:for|in|at)\s+(?P<code>[A-Za-z0-9-]+)", re.IGNORECASE),
    re.compile(r"code\s+(?P<code>[A-Za-z0-9-]+)\s+(?:in|for|at)\s+(?P<size>.+)", re.IGNORECASE),
)
_SIZE_TOKEN_SPLIT = re.compile(r"[^a-z0-9.]+")


def _strip_trailing_punctuation(value: str) -> str:
    return value.strip().strip("\"'.,!?;:")


def _strip_leading_words(text: str, filler_words: Sequence[str]) -> str:
    filler = {word.lower() for word in filler_words}
    tokens = text.split()
    while tokens and tokens[0].lower() in filler:
        tokens.pop(0)
    return " ".join(tokens)


def _normalize_simple(value: str) -> str:
    return " ".join(value.lower().split())


def _normalize_code_query(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()


def _normalize_size_phrase(value: str, config: ChatbotConfig) -> str:
    if not value:
        return ""
    spaced = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", str(value))
    tokens = [token for token in _SIZE_TOKEN_SPLIT.split(spaced.lower()) if token]
    normalized: List[str] = []
    for token in tokens:
        normalized.append(config.size_aliases.get(token, token))
    return " ".join(normalized)


def _parse_about_query(message: str, config: ChatbotConfig) -> Optional[str]:
    lower = message.lower()
    for trigger in config.about_triggers:
        index = lower.find(trigger)
        if index == -1:
            continue
        candidate = message[index + len(trigger) :]
        candidate = _strip_trailing_punctuation(candidate)
        candidate = _strip_leading_words(candidate, config.filler_words)
        if candidate:
            return candidate
    return None


def _extract_code_and_size(text: str) -> Optional[Tuple[str, str]]:
    for pattern in _PRICE_PATTERNS:
        match = pattern.search(text)
        if match:
            code = _strip_trailing_punctuation(match.group("code"))
            size = _strip_trailing_punctuation(match.group("size"))
            if code:
                return code, size
    tokens = text.split()
    if not tokens:
        return None
    code = _strip_trailing_punctuation(tokens[0])
    size = _strip_trailing_punctuation(" ".join(tokens[1:]))
    return code, size


def _parse_price_query(message: str, config: ChatbotConfig) -> Optional[Tuple[str, str]]:
    lower = message.lower()
    for trigger in config.price_triggers:
        index = lower.find(trigger)
        if index == -1:
            continue
        candidate = message[index + len(trigger) :]
        candidate = _strip_trailing_punctuation(candidate)
        candidate = _strip_leading_words(candidate, config.filler_words)
        parsed = _extract_code_and_size(candidate)
        if parsed:
            return parsed
    # Fall back to scanning the full message when no explicit trigger is found.
    if any(keyword in lower for keyword in ("price", "cost")):
        parsed = _extract_code_and_size(message)
        if parsed and parsed[0]:
            return parsed
    return None


def _format_suggestions(items: Sequence[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return " or ".join(items)
    return ", ".join(items[:-1]) + f", or {items[-1]}"


def _suggest_product_names(query: str, config: ChatbotConfig) -> List[str]:
    if not query:
        return []
    names = list_product_names()
    results = process.extract(
        query,
        names,
        processor=_normalize_simple,
        scorer=fuzz.WRatio,
        score_cutoff=config.product_similarity_threshold,
        limit=config.suggestion_limit,
    )
    return [match[0] for match in results]


def _suggest_product_codes(query: str, config: ChatbotConfig) -> List[str]:
    if not query:
        return []
    codes = list_product_codes()
    normalized_query = _normalize_code_query(query)
    if not normalized_query:
        return []
    results = process.extract(
        normalized_query,
        codes,
        processor=_normalize_code_query,
        scorer=fuzz.partial_ratio,
        score_cutoff=config.code_similarity_threshold,
        limit=config.suggestion_limit,
    )
    return [match[0] for match in results]


def _match_size_alias(size: str, available_sizes: Sequence[str], config: ChatbotConfig) -> Optional[str]:
    if not size or not available_sizes:
        return None
    normalized_query = _normalize_size_phrase(size, config)
    if not normalized_query:
        return None
    best_match: Optional[str] = None
    best_score = 0.0
    for candidate in available_sizes:
        normalized_candidate = _normalize_size_phrase(candidate, config)
        score = fuzz.token_set_ratio(normalized_query, normalized_candidate)
        if score > best_score and score >= config.size_similarity_threshold:
            best_score = score
            best_match = candidate
    return best_match


def _handle_about(product_name: str, *, config: ChatbotConfig = DEFAULT_CONFIG) -> str:
    product = find_product_by_name(product_name)
    if product:
        summary = summarize_product(product)
        name = product.get("product_name", product_name).strip()
        return f"{name}\n{summary}"

    suggestions = _suggest_product_names(product_name, config)
    if not suggestions:
        return f"I couldn't find a product named \"{product_name.strip()}\"."

    best_name = suggestions[0]
    best_product = find_product_by_name(best_name)
    if not best_product:
        normalized_target = _normalize_simple(best_name)
        for candidate in get_all_products():
            if _normalize_simple(candidate.get("product_name", "")) == normalized_target:
                best_product = candidate
                break

    if best_product:
        summary = summarize_product(best_product)
        resolved_name = best_product.get("product_name", best_name).strip()
        return (
            f"I couldn't find a product named \"{product_name.strip()}\". "
            f"Here's the closest match I found:\n{resolved_name}\n{summary}"
        )

    formatted = _format_suggestions(suggestions)
    return (
        f"I couldn't find a product named \"{product_name.strip()}\". "
        f"Did you mean: {formatted}?"
    )


def _handle_price(product_code: str, size: str, *, config: ChatbotConfig = DEFAULT_CONFIG) -> str:
    original_size = size
    product, price_entry, currency = lookup_price(product_code, size)
    if product is None:
        suggestions = _suggest_product_codes(product_code, config)
        if suggestions:
            formatted = _format_suggestions(suggestions)
            return (
                f"I couldn't find a product with the code \"{product_code.strip()}\". "
                f"Closest match: {formatted}."
            )
        return f"I couldn't find a product with the code \"{product_code.strip()}\"."

    if not original_size.strip():
        available_sizes = list_available_sizes(product["product_code"])
        if available_sizes:
            choices = ", ".join(available_sizes)
            return (
                f"{product['product_name']} (code {product['product_code']}) is available in: {choices}. "
                "Please specify one of these sizes to get a price."
            )
        return f"I couldn't find size details for {product['product_name']} (code {product['product_code']})."

    matched_size = None
    if price_entry is None:
        available_sizes = list_available_sizes(product["product_code"])
        matched_size = _match_size_alias(original_size, available_sizes, config)
        if matched_size:
            product, price_entry, currency = lookup_price(product["product_code"], matched_size)

    if price_entry is None:
        available_sizes = list_available_sizes(product["product_code"])
        if matched_size:
            prefix = (
                f"I couldn't find the size \"{original_size.strip()}\" for {product['product_name']} "
                f"(code {product['product_code']}). The closest size is \"{matched_size}\"."
            )
        else:
            prefix = (
                f"I couldn't find the size \"{original_size.strip()}\" for {product['product_name']} "
                f"(code {product['product_code']})."
            )
        if available_sizes:
            choices = ", ".join(available_sizes)
            return f"{prefix} Available sizes are: {choices}."
        return prefix

    price_value = price_entry.get("price")
    size_label = price_entry.get("size", matched_size or original_size.strip()) or original_size.strip()
    if price_value is None:
        return (
            f"The price for {product['product_name']} (code {product['product_code']}) in {size_label} isn't listed."
        )

    formatted_price = f"{price_value:,.2f}"
    currency_label = currency.strip()
    if currency_label:
        formatted_price = f"{formatted_price} {currency_label}"

    clarification = ""
    if original_size.strip() and _normalize_size_phrase(original_size, config) != _normalize_size_phrase(size_label, config):
        clarification = f" (closest size to \"{original_size.strip()}\")"

    return (
        f"{product['product_name']} (code {product['product_code']}) costs {formatted_price} for {size_label}{clarification}."
    )


def _handle_unknown(message: str, *, config: ChatbotConfig) -> str:
    name_suggestions = _suggest_product_names(message, config)
    if name_suggestions:
        suggestion = name_suggestions[0]
        return (
            "I'm not sure how to help with that directly, but it sounds like you're interested in "
            f"{suggestion}. Try asking 'Tell me about {suggestion}'."
        )

    code_suggestions = _suggest_product_codes(message, config)
    if code_suggestions:
        suggestion = code_suggestions[0]
        return (
            "I'm not sure how to help with that directly, but the closest product code I found is "
            f"{suggestion}. Try asking 'How much is {suggestion} in <size>?'."
        )

    return (
        "I'm not sure how to help with that. Try asking 'Tell me about <product name>' or "
        "'How much is <product code> in <size>?'."
    )


def respond_to(message: str, *, config: ChatbotConfig | None = None) -> str:
    config = config or DEFAULT_CONFIG
    message = message.strip()
    if not message:
        return "Please enter a question about a product or its price."

    price_match = _PRICE_RE.match(message)
    if price_match:
        product_code, size = price_match.groups()
        return _handle_price(product_code, size, config=config)

    parsed_price = _parse_price_query(message, config)
    if parsed_price:
        product_code, size = parsed_price
        return _handle_price(product_code, size, config=config)

    about_match = _ABOUT_RE.match(message)
    if about_match:
        product_name = about_match.group(1)
        return _handle_about(product_name, config=config)

    parsed_about = _parse_about_query(message, config)
    if parsed_about:
        return _handle_about(parsed_about, config=config)

    return _handle_unknown(message, config=config)


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
