from src.chatbot import respond_to


def test_about_query_with_synonym():
    response = respond_to("Can you describe NATIONAL N.C AUTOLACQUER TOPCOAT?")

    assert "NATIONAL N.C AUTOLACQUER TOPCOAT" in response


def test_price_query_with_size_alias():
    response = respond_to("What's the price of A119 for 18 liter drum?")

    assert "A119" in response
    assert "80.00" in response


def test_about_query_best_effort_suggestion():
    response = respond_to("Tell me about national nc autolacer topcat")

    assert "closest match" in response.lower()
    assert "NATIONAL N.C AUTOLACQUER TOPCOAT" in response
