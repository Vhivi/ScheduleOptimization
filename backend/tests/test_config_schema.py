import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "config.schema.json"
CONFIG_PATH = ROOT / "config.json"
EXAMPLE_PATH = ROOT / "config.example.json"


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_config_json_matches_schema():
    schema = _load_json(SCHEMA_PATH)
    config = _load_json(CONFIG_PATH)

    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(config))

    assert errors == []


def test_config_example_matches_schema():
    schema = _load_json(SCHEMA_PATH)
    example = _load_json(EXAMPLE_PATH)

    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))

    assert errors == []


def test_schema_rejects_invalid_date_format():
    schema = _load_json(SCHEMA_PATH)
    example = _load_json(EXAMPLE_PATH)

    example["agents"][0]["unavailable"] = ["2026-03-05"]
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))

    assert errors != []
    assert any(
        "unavailable" in "/".join(str(part) for part in error.path) for error in errors
    )


def test_schema_rejects_unknown_shift():
    schema = _load_json(SCHEMA_PATH)
    example = _load_json(EXAMPLE_PATH)

    example["vacations"] = ["Jour", "Late"]
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))

    assert errors != []
