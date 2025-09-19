from __future__ import annotations

import pytest

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover - FastAPI optional in CI
    TestClient = None  # type: ignore[misc]
else:
    from app.main import app

    client = TestClient(app)


@pytest.mark.skipif(TestClient is None, reason="FastAPI is not installed")
def test_ai_chat_price_lookup(monkeypatch):
    from app import ai_routes

    class DummyPipeline:
        def get_contexts(self, query: str, *, top_k: int = 18, rerank_k: int = 5):
            assert query
            return []

    monkeypatch.setattr(ai_routes, "_PIPELINE", DummyPipeline())

    def fake_generate_answer(query: str, *, contexts, tools):
        assert contexts == []
        assert any(tool.get("tool") == "price_lookup" for tool in tools)
        return "Stubbed AI response."

    monkeypatch.setattr(ai_routes, "generate_answer", fake_generate_answer)

    response = client.post(
        "/ai/chat",
        json={"prompt": "How much is A119 in 18 Ltr (Drum)?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reply"] == "Stubbed AI response."
    price_tool = next(tool for tool in payload["used_tools"] if tool["tool"] == "price_lookup")
    assert price_tool["found"] is True
    assert price_tool["price"] == 80.0
    assert price_tool["currency"] == "AED"


@pytest.mark.skipif(TestClient is None, reason="FastAPI is not installed")
def test_ai_chat_rejects_empty_prompt(monkeypatch):
    from app import ai_routes

    class DummyPipeline:
        def get_contexts(self, query: str, *, top_k: int = 18, rerank_k: int = 5):
            return []

    monkeypatch.setattr(ai_routes, "_PIPELINE", DummyPipeline())
    monkeypatch.setattr(ai_routes, "generate_answer", lambda *args, **kwargs: "unused")

    response = client.post("/ai/chat", json={"prompt": "   "})
    assert response.status_code == 400
    assert response.json()["detail"] == "Prompt must not be empty."


@pytest.mark.skipif(TestClient is None, reason="FastAPI is not installed")
def test_ai_chat_returns_service_unavailable_when_openai_fails(monkeypatch):
    from app import ai_routes
    from src.models import llm

    class DummyPipeline:
        def get_contexts(self, query: str, *, top_k: int = 18, rerank_k: int = 5):
            return []

    monkeypatch.setattr(ai_routes, "_PIPELINE", DummyPipeline())
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FailingCompletions:
        def create(self, *args, **kwargs):
            raise Exception("boom")

    class FailingChat:
        def __init__(self):
            self.completions = FailingCompletions()

    class FailingClient:
        def __init__(self, *args, **kwargs):
            self.chat = FailingChat()

    monkeypatch.setattr(llm, "OpenAI", FailingClient)
    monkeypatch.setattr(llm, "openai", None)

    response = client.post("/ai/chat", json={"prompt": "Hello there"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Failed to generate response from OpenAI API"
