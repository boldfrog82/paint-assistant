"""ASGI application for the Paint Assistant chatbot."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from src.chatbot import respond_to


class ChatRequest(BaseModel):
    """Request payload for the chat endpoint."""

    prompt: str


class ChatResponse(BaseModel):
    """Response payload returned by the chat endpoint."""

    response: str


app = FastAPI(title="Paint Assistant API", version="1.0.0")


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Simple health check endpoint."""

    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Generate a chatbot response for the provided prompt."""

    response_text = respond_to(request.prompt)
    return ChatResponse(response=response_text)
