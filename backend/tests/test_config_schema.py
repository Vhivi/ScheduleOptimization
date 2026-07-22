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
    if not CONFIG_PATH.exists():
        pytest.skip("backend/config.json not found in test environment")
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


def test_schema_accepts_custom_shift_name():
    schema = _load_json(SCHEMA_PATH)
    example = _load_json(EXAMPLE_PATH)

    example["vacations"] = ["Jour", "Late"]
    example["vacation_durations"]["Late"] = 8
    example["staffing_requirements"]["Late"] = 2
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))

    assert errors == []


def test_schema_rejects_negative_staffing_requirement():
    schema = _load_json(SCHEMA_PATH)
    example = _load_json(EXAMPLE_PATH)

    example["staffing_requirements"]["Jour"] = -1
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))

    assert errors != []


def test_schema_accepts_max_weekly_hours():
    schema = _load_json(SCHEMA_PATH)
    example = _load_json(EXAMPLE_PATH)

    example["solver"]["max_weekly_hours"] = 42
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))

    assert errors == []


@pytest.mark.parametrize("penalty", [0, 500])
def test_schema_accepts_weekend_monday_night_penalty(penalty):
    schema = _load_json(SCHEMA_PATH)
    example = _load_json(EXAMPLE_PATH)
    example["solver"]["weekend_monday_night_penalty"] = penalty

    validator = Draft202012Validator(schema)

    assert list(validator.iter_errors(example)) == []


def test_schema_rejects_negative_weekend_monday_night_penalty():
    schema = _load_json(SCHEMA_PATH)
    example = _load_json(EXAMPLE_PATH)
    example["solver"]["weekend_monday_night_penalty"] = -1

    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))

    assert errors != []
    assert any(
        "weekend_monday_night_penalty" in "/".join(str(part) for part in error.path)
        for error in errors
    )


def test_schema_accepts_agent_balance_opt_out():
    schema = _load_json(SCHEMA_PATH)
    example = _load_json(EXAMPLE_PATH)

    example["agents"][0]["include_in_balance"] = False
    validator = Draft202012Validator(schema)

    assert list(validator.iter_errors(example)) == []


def test_schema_rejects_non_boolean_agent_balance_opt_out():
    schema = _load_json(SCHEMA_PATH)
    example = _load_json(EXAMPLE_PATH)

    example["agents"][0]["include_in_balance"] = "false"
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))

    assert errors != []
    assert any(
        "include_in_balance" in "/".join(str(part) for part in error.path)
        for error in errors
    )


def test_schema_accepts_temporal_vacation_metadata():
    schema = _load_json(SCHEMA_PATH)
    example = _load_json(EXAMPLE_PATH)

    example.setdefault("vacation_metadata", {})["Nuit"] = {
        "is_night": True,
        "requires_next_day_rest": True,
        "start_time": "19:00",
        "end_time": "07:00",
    }
    example["half_vacations"]["Nuit"]["segments"][0]["start_time"] = "19:00"
    example["half_vacations"]["Nuit"]["segments"][0]["end_time"] = "01:00"
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))

    assert errors == []


def test_schema_rejects_invalid_temporal_vacation_metadata_time():
    schema = _load_json(SCHEMA_PATH)
    example = _load_json(EXAMPLE_PATH)

    example.setdefault("vacation_metadata", {})["Nuit"] = {
        "start_time": "24:00",
        "end_time": "07:00",
    }
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))

    assert errors != []
    assert any(
        "start_time" in "/".join(str(part) for part in error.path)
        for error in errors
    )


@pytest.mark.parametrize("max_weekly_hours", [0, -1])
def test_schema_rejects_non_positive_max_weekly_hours(max_weekly_hours):
    schema = _load_json(SCHEMA_PATH)
    example = _load_json(EXAMPLE_PATH)

    example["solver"]["max_weekly_hours"] = max_weekly_hours
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))

    assert errors != []
    assert any(
        "max_weekly_hours" in "/".join(str(part) for part in error.path)
        for error in errors
    )
