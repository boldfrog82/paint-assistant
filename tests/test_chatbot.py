"""Tests for the chatbot response logic and API."""

from __future__ import annotations

import pytest

from src.chatbot import respond_to

client = None

try:  # pragma: no cover - optional dependency for API tests
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover - allow skipping API tests when FastAPI isn't installed
    TestClient = None  # type: ignore
else:
    from app.main import app

    client = TestClient(app)


# ---------------------------------------------------------------------------
# respond_to direct tests
# ---------------------------------------------------------------------------

def test_respond_to_about_exact_match() -> None:
    response = respond_to("Tell me about National Acrylic Primer (W.B.)")

    assert response.startswith("NATIONAL ACRYLIC PRIMER (W.B.)\n")
    assert "National Acrylic Primer (W.B.) is an acrylic emulsion based" in response
    assert "Uses: Summary: National Acrylic Primer (W.B.)" in response


def test_respond_to_about_fuzzy_match() -> None:
    response = respond_to("  tell me about    national aqua acrylic primer   ")

    lines = response.splitlines()
    assert lines[0] == "NATIONAL AQUA ACRYLIC PRIMER"
    assert "National Aqua Acrylic Primer is a pure acrylic" in response


def test_respond_to_price_lookup_success() -> None:
    response = respond_to("How much is A119 in 18 Ltr (Drum)?")

    expected = "National Acrylic Primer (W.B.) (code A119) costs 80.00 AED for 18 Ltr (Drum)."
    assert response == expected


def test_respond_to_price_unknown_size() -> None:
    response = respond_to("How much is A119 in 1 Ltr?")

    expected = (
        'I couldn\'t find the size "1 Ltr" for National Acrylic Primer (W.B.) (code A119). '
        "Available sizes are: 18 Ltr (Drum), 3.6 Ltr (Gallon)."
    )
    assert response == expected


def test_respond_to_price_without_size_lists_available_sizes() -> None:
    response = respond_to("How much does A119 cost?")

    assert "Available sizes are:" in response
    assert "(code A119)" in response


def test_respond_to_price_of_phrase_detects_code() -> None:
    response = respond_to("How much is the price of A119?")

    assert "Available sizes are:" in response
    assert "(code A119)" in response
    assert "code price" not in response.lower()


def test_respond_to_unknown_product_name() -> None:
    response = respond_to("Tell me about unknown product")

    expected = 'I couldn\'t find a product named "unknown product".'
    assert response == expected


def test_respond_to_unknown_product_code() -> None:
    response = respond_to("How much is ZZZZ in 18 Ltr (Drum)")

    expected = 'I couldn\'t find a product with the code "ZZZZ".'
    assert response == expected


def test_respond_to_empty_prompt() -> None:
    response = respond_to("   ")

    expected = "Please enter a question about a product or its price."
    assert response == expected


def test_respond_to_fallback_message() -> None:
    response = respond_to("What's the weather like today?")

    expected = (
        "I'm not sure how to help with that. Try asking 'Tell me about <product name>' or "
        "'How much is <product code> in <size>?'."
    )
    assert response == expected


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(TestClient is None, reason="FastAPI is not installed")
def test_chat_endpoint_returns_price_response() -> None:
    payload = {"prompt": "How much is A119 in 18 Ltr (Drum)?"}

    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "response": "National Acrylic Primer (W.B.) (code A119) costs 80.00 AED for 18 Ltr (Drum)."
    }


@pytest.mark.skipif(TestClient is None, reason="FastAPI is not installed")
def test_chat_endpoint_handles_empty_prompt() -> None:
    payload = {"prompt": ""}

    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "response": "Please enter a question about a product or its price."
    }
