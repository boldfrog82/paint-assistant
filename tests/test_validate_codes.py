import validate_codes


def test_find_duplicate_codes_detects_a050_duplicate():
    duplicates = validate_codes.find_duplicate_codes()

    assert "A050" in duplicates
    assert duplicates["A050"] == 2
