"""Validate data files used by the paint quotation tool."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable, Tuple

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SCHEMA_DIR = ROOT / "schemas"

DATASETS: Tuple[Tuple[str, str], ...] = (
    ("paint_products.json", "products.schema.json"),
    ("pricelistnationalpaints.json", "pricelist.schema.json"),
)


def _format_path(path: Iterable[Any]) -> str:
    return " -> ".join(str(part) for part in path) or "<root>"


def _validate_type(value: Any, expected_type: str) -> bool:
    type_map = {
        "object": dict,
        "array": list,
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
    }
    python_type = type_map.get(expected_type)
    if python_type is None:
        return True
    return isinstance(value, python_type)


def _validate(value: Any, schema: dict, path: Tuple[Any, ...]) -> list[str]:
    errors: list[str] = []

    schema_type = schema.get("type")
    if schema_type and not _validate_type(value, schema_type):
        errors.append(f"{_format_path(path)}: expected {schema_type}")
        return errors

    if schema_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{_format_path(path)}: expected object")
            return errors

        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{_format_path(path)}: missing required property '{key}'")

        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                errors.extend(_validate(item, properties[key], path + (key,)))
            else:
                if additional is False:
                    errors.append(f"{_format_path(path + (key,))}: additional property not allowed")
                elif isinstance(additional, dict):
                    errors.extend(_validate(item, additional, path + (key,)))

    if schema_type == "array":
        if not isinstance(value, list):
            errors.append(f"{_format_path(path)}: expected array")
            return errors

        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(_validate(item, item_schema, path + (index,)))
        elif isinstance(item_schema, list):
            for index, sub_schema in enumerate(item_schema):
                if index < len(value):
                    errors.extend(_validate(value[index], sub_schema, path + (index,)))

    if schema_type == "string" and isinstance(value, str):
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{_format_path(path)}: string shorter than {min_length}")

    if schema_type in {"number", "integer"} and isinstance(value, (int, float)):
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            errors.append(f"{_format_path(path)}: value less than minimum {minimum}")

    return errors


def validate_dataset(data_path: Path, schema_path: Path) -> bool:
    """Validate a single dataset and report errors."""

    with schema_path.open("r", encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    with data_path.open("r", encoding="utf-8") as data_file:
        data = json.load(data_file)

    errors = _validate(data, schema, ())

    if errors:
        print(f"✗ {data_path.name} is invalid:")
        for error in errors:
            print(f"  • {error}")
        return False

    print(f"✓ {data_path.name} is valid.")
    return True


def main() -> int:
    results = []
    for data_name, schema_name in DATASETS:
        data_path = DATA_DIR / data_name
        schema_path = SCHEMA_DIR / schema_name
        if not data_path.exists():
            print(f"✗ Missing data file: {data_path}")
            results.append(False)
            continue
        if not schema_path.exists():
            print(f"✗ Missing schema file: {schema_path}")
            results.append(False)
            continue
        results.append(validate_dataset(data_path, schema_path))

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
