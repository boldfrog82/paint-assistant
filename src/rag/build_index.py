"""Build a lightweight retrieval index for the AI chat endpoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ..data.products import get_all_products, summarize_product

INDEX_FILENAME = "rag_index.json"
DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[2] / INDEX_FILENAME


def _serialise_product(product: Dict[str, Any]) -> Dict[str, Any]:
    name = str(product.get("product_name", "")).strip()
    code = str(product.get("product_code", "")).strip()
    summary = summarize_product(product)

    text_parts: List[str] = []
    if name:
        text_parts.append(name)
    if code:
        text_parts.append(f"(code {code})")
    if summary:
        text_parts.append(summary)

    metadata: Dict[str, Any] = {
        "product_name": name,
    }
    if code:
        metadata["product_code"] = code
    category = product.get("category") or product.get("product_category")
    if category:
        metadata["category"] = category

    return {
        "text": " ".join(text_parts).strip(),
        "metadata": metadata,
    }


def build_index(output_path: Path | None = None) -> Path:
    """Generate the retrieval index file and return its path."""

    path = output_path or DEFAULT_INDEX_PATH
    products = get_all_products()
    records = [_serialise_product(product) for product in products]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)

    return path


def main() -> None:
    path = build_index()
    print(f"Retrieval index written to {path}")


if __name__ == "__main__":  # pragma: no cover - manual usage script
    main()


__all__ = ["DEFAULT_INDEX_PATH", "build_index", "main"]
