import pytest

import paint_assistant


@pytest.fixture(scope="module")
def price_data():
    """Load the price list once for reuse across tests."""

    return paint_assistant.load_pricelist()


def test_load_products_parses_product_entries():
    products = paint_assistant.load_products()

    assert isinstance(products, list)
    assert products, "No product data was returned"

    # Extract the first dictionary entry to ensure the nested structure is intact.
    first_entry = None
    for group in products:
        if isinstance(group, list) and group:
            maybe_entry = group[0]
            if isinstance(maybe_entry, dict):
                first_entry = maybe_entry
                break

    assert first_entry is not None, "Expected at least one product entry"
    assert "product_name" in first_entry
    assert first_entry["product_name"], "Product name should not be empty"


def test_get_price_returns_expected_value(price_data):
    price = paint_assistant.get_price("A119", "18 Ltr (Drum)", price_data=price_data)

    assert price == pytest.approx(80.0)


def test_get_price_handles_normalized_inputs(price_data):
    price = paint_assistant.get_price("  a119  ", " 18   LTR   (DRUM)  ", price_data=price_data)

    assert price == pytest.approx(80.0)


def test_list_sizes_returns_known_sizes(price_data):
    sizes = paint_assistant.list_sizes("A119", price_data=price_data)

    assert sizes == ["18 Ltr (Drum)", "3.6 Ltr (Gallon)"]


def test_list_sizes_accepts_case_insensitive_code(price_data):
    sizes = paint_assistant.list_sizes("a119", price_data=price_data)

    assert sizes == ["18 Ltr (Drum)", "3.6 Ltr (Gallon)"]
