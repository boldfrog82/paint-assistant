import validate_codes


def test_find_duplicate_codes_uses_payload_from_monkeypatched_pricelist(monkeypatch):
    """A synthetic payload should produce the expected duplicate mapping."""

    payload = {
        "product_categories": [
            {
                "subcategories": [
                    {
                        "products": [
                            {"product_code": "X001"},
                            {"product_code": "DUP"},
                            {"product_code": "DUP"},
                            {"product_code": "X002"},
                        ]
                    }
                ]
            }
        ]
    }

    def fake_load_pricelist(path=validate_codes.PRICELIST_PATH):  # pragma: no cover - exercised indirectly
        return payload

    monkeypatch.setattr(validate_codes, "load_pricelist", fake_load_pricelist)

    assert validate_codes.find_duplicate_codes() == {"DUP": 2}


def test_find_duplicate_codes_detects_no_duplicates_in_real_dataset():
    """Ensure the bundled dataset still has no duplicate product codes."""

    assert validate_codes.find_duplicate_codes() == {}
