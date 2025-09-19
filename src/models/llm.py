"""Interface with large language models for the AI chat endpoint."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Sequence

from ..rag import RetrievedChunk

try:  # pragma: no cover - optional dependency
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - support environments without OpenAI SDK
    OpenAI = None  # type: ignore[misc,assignment]

try:  # pragma: no cover - optional dependency
    import openai  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    openai = None  # type: ignore[misc,assignment]

_DEFAULT_MODEL = "gpt-3.5-turbo"


def _format_tools(tools: Sequence[Dict[str, Any]]) -> str:
    formatted = []
    for tool in tools:
        name = tool.get("tool", "unknown")
        formatted.append(f"- {name}: {json.dumps(tool, ensure_ascii=False, sort_keys=True)}")
    return "\n".join(formatted)


def _format_contexts(contexts: Sequence[RetrievedChunk]) -> str:
    formatted = []
    for chunk in contexts[:10]:
        snippet = chunk.text.strip().replace("\n", " ")
        metadata = json.dumps(chunk.metadata, ensure_ascii=False, sort_keys=True)
        formatted.append(f"- score={chunk.score:.3f} {snippet} | metadata={metadata}")
    return "\n".join(formatted)


def _build_messages(prompt: str, contexts: Sequence[RetrievedChunk], tools: Sequence[Dict[str, Any]]):
    instructions = (
        "You are Paint Assistant, a helpful expert on National Paints products. "
        "Use the provided tool results and reference documents to answer the user question."
    )

    details: List[str] = []
    if tools:
        details.append("Tool outputs:\n" + _format_tools(tools))
    if contexts:
        details.append("Retrieved documents:\n" + _format_contexts(contexts))
    details.append(f"User question: {prompt}")

    return [
        {"role": "system", "content": instructions},
        {"role": "user", "content": "\n\n".join(details)},
    ]


def _compose_prompt(prompt: str, contexts: Sequence[RetrievedChunk], tools: Sequence[Dict[str, Any]]) -> str:
    payload = {
        "prompt": prompt,
        "tools": tools,
        "contexts": [
            {
                "text": chunk.text,
                "score": chunk.score,
                "metadata": chunk.metadata,
            }
            for chunk in contexts
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def _format_price(tool: Dict[str, Any]) -> str:
    price = tool.get("price")
    if isinstance(price, (int, float)):
        price_value = f"{price:,.2f}"
    else:
        price_value = str(price)
    currency = tool.get("currency") or ""
    size = tool.get("size") or tool.get("requested_size")
    product_name = tool.get("product_name") or tool.get("requested_code") or "the product"
    if currency:
        return f"{product_name} costs {price_value} {currency} for {size}."
    return f"{product_name} costs {price_value} for {size}."


def _fallback_answer(prompt: str, contexts: Sequence[RetrievedChunk], tools: Sequence[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for tool in tools:
        if tool.get("tool") == "price_lookup" and tool.get("found"):
            parts.append(_format_price(tool))
        elif tool.get("tool") == "product_card" and tool.get("found") and tool.get("summary"):
            parts.append(str(tool.get("summary")))

    if not parts and contexts:
        parts.append(contexts[0].text)

    if not parts:
        parts.append(
            "I'm unable to reach the language model right now, but I'm still here to help. "
            "Please try again in a moment."
        )

    if prompt:
        parts.append(f"(Original question: {prompt})")

    return "\n\n".join(parts)


def generate_answer(
    prompt: str,
    *,
    contexts: Sequence[RetrievedChunk],
    tools: Sequence[Dict[str, Any]],
) -> str:
    """Generate a response using the available LLM backend or fall back gracefully."""

    api_key = os.getenv("OPENAI_API_KEY")
    messages = _build_messages(prompt, contexts, tools)

    if OpenAI is not None and api_key:
        client = OpenAI(api_key=api_key)
        try:  # pragma: no cover - requires networked OpenAI access
            completion = client.chat.completions.create(
                model=_DEFAULT_MODEL,
                messages=messages,
            )
        except AttributeError:  # pragma: no cover - support newer SDK variants
            try:
                response = client.responses.create(  # type: ignore[attr-defined]
                    model=_DEFAULT_MODEL,
                    input=_compose_prompt(prompt, contexts, tools),
                )
            except Exception as exc:  # pragma: no cover - network errors
                raise RuntimeError("Failed to generate response from OpenAI API") from exc
            else:
                for item in getattr(response, "output", []):
                    if getattr(item, "type", "") == "message":
                        text_parts = [
                            getattr(content, "text", "")
                            for content in getattr(item, "content", [])
                            if getattr(content, "type", "") == "text"
                        ]
                        text = "".join(text_parts).strip()
                        if text:
                            return text
        except Exception as exc:  # pragma: no cover - network errors
            raise RuntimeError("Failed to generate response from OpenAI API") from exc
        else:
            try:
                text = completion.choices[0].message.content
            except (IndexError, AttributeError, KeyError):  # pragma: no cover - SDK variations
                text = None
            if text:
                return text.strip()

    if openai is not None and api_key:
        openai.api_key = api_key
        try:  # pragma: no cover - requires OpenAI SDK v0 compatibility
            completion = openai.ChatCompletion.create(model=_DEFAULT_MODEL, messages=messages)
        except Exception as exc:  # pragma: no cover - propagate as runtime error
            raise RuntimeError("Failed to generate response from OpenAI API") from exc
        else:
            message = completion["choices"][0]["message"].get("content")
            if message:
                return str(message).strip()

    return _fallback_answer(prompt, contexts, tools)


__all__ = ["generate_answer"]
