import validate_codes


def _build_price_payload(product_codes):
    return {
        "product_categories": [
            {
                "subcategories": [
                    {
                        "products": [
                            {"product_code": code, "prices": []}
                            for code in product_codes
                        ]
                    }
                ]
            }
        ]
    }


def test_find_duplicate_codes_detects_a050_duplicate(monkeypatch):
    price_payload = _build_price_payload(["A050", "A050", "B123"])

    monkeypatch.setattr(validate_codes, "load_pricelist", lambda path=None: price_payload)

    duplicates = validate_codes.find_duplicate_codes()

    assert "A050" in duplicates
    assert duplicates["A050"] == 2
