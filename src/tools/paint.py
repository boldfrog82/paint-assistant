"""Tools that expose product and pricing data as structured payloads."""

from __future__ import annotations

from typing import Any, Dict, List

from ..data.products import find_product_by_name, summarize_product
from ..data.prices import (
    get_currency,
    get_product_by_code,
    list_available_sizes,
    lookup_price,
)


def price_lookup_tool(code: str, size: str) -> Dict[str, Any]:
    """Return a structured payload describing the price lookup result."""

    cleaned_code = code.strip()
    cleaned_size = size.strip()

    missing_fields: List[str] = []
    if not cleaned_code:
        missing_fields.append("code")
    if not cleaned_size:
        missing_fields.append("size")

    payload: Dict[str, Any] = {
        "tool": "price_lookup",
        "requested_code": cleaned_code,
        "requested_size": cleaned_size,
        "found": False,
    }

    if "code" in missing_fields:
        payload["currency"] = get_currency()
        payload["missing_fields"] = missing_fields
        return payload

    product, price_entry, currency = lookup_price(cleaned_code, cleaned_size)
    payload["currency"] = currency
    if missing_fields:
        payload["missing_fields"] = missing_fields

    if product:
        payload["product_name"] = product.get("product_name")
        payload["product_code"] = product.get("product_code")

    if price_entry:
        payload["found"] = True
        payload["price"] = price_entry.get("price")
        payload["size"] = price_entry.get("size", cleaned_size)
    elif product:
        code_to_query = product.get("product_code") or cleaned_code
        payload["available_sizes"] = list_available_sizes(code_to_query)

    return payload


def product_card_tool(identifier: str) -> Dict[str, Any]:
    """Return metadata useful for rendering a product card."""

    query = identifier.strip()
    payload: Dict[str, Any] = {
        "tool": "product_card",
        "identifier": query,
        "found": False,
    }

    if not query:
        return payload

    product = find_product_by_name(query)
    price_product = None
    if not product:
        price_product = get_product_by_code(query)
        if price_product:
            product = price_product
    else:
        price_product = get_product_by_code(product.get("product_code", ""))

    if not product:
        return payload

    payload["found"] = True
    payload["product_name"] = product.get("product_name") or product.get("productName")
    product_code = product.get("product_code") or query
    payload["product_code"] = product_code

    summary = summarize_product(product) if product else ""
    if not summary and price_product:
        summary = price_product.get("product_description", "")
    if summary:
        payload["summary"] = summary

    if product_code:
        payload["available_sizes"] = list_available_sizes(product_code)

    return payload


__all__ = ["price_lookup_tool", "product_card_tool"]
