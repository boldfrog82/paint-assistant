from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.chatbot import parse_price_prompt
from src.models.llm import generate_answer
from src.rag import RetrievedChunk, RetrievalPipeline
from src.tools.paint import price_lookup_tool, product_card_tool

router = APIRouter(prefix="/ai", tags=["AI Chat"])

_ABOUT_RE = re.compile(r"tell me about\s+(.+?)[.?!]*$", re.IGNORECASE)
_PIPELINE: RetrievalPipeline | None = None


class AIChatRequest(BaseModel):
    prompt: str = Field(min_length=1, description="End-user message")


class AIChatResponse(BaseModel):
    reply: str
    used_tools: list[dict[str, Any]] = Field(default_factory=list)
    retrieved: list[dict[str, Any]] = Field(default_factory=list)


def _get_pipeline() -> RetrievalPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = RetrievalPipeline()
    return _PIPELINE


def _format_retrieved(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for chunk in chunks:
        payloads.append(
            {
                "text": chunk.text,
                "score": chunk.score,
                "metadata": chunk.metadata,
            }
        )
    return payloads


def _gather_tools(prompt: str) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    price_args = parse_price_prompt(prompt)
    card_identifier: str | None = None

    if price_args:
        code, size = price_args
        price_payload = price_lookup_tool(code, size)
        tools.append(price_payload)
        card_identifier = (
            price_payload.get("product_name")
            or price_payload.get("requested_code")
            or code
        )

    about_match = _ABOUT_RE.search(prompt)
    if about_match:
        card_identifier = about_match.group(1).strip()

    if card_identifier:
        card_payload = product_card_tool(card_identifier)
        tools.append(card_payload)

    return tools


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(request: AIChatRequest) -> AIChatResponse:
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    tools = _gather_tools(prompt)

    try:
        pipeline = _get_pipeline()
        contexts = pipeline.get_contexts(prompt)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        reply = generate_answer(prompt, contexts=contexts, tools=tools)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return AIChatResponse(
        reply=reply,
        used_tools=tools,
        retrieved=_format_retrieved(contexts),
    )
