import json
from copy import deepcopy
from unittest.mock import mock_open, patch

import pytest
from app import (
    RELAXED_CONSTRAINT_DIAGNOSTICS,
    _diagnose_manual_entry_conflicts,
    _probe_relaxed_hard_constraints,
    _inject_manual_status_entries,
    app,
    get_active_config,
    load_config,
    load_default_config,
    set_active_config,
)


@pytest.fixture
def client():
    """
    Fixture to create a test client for the Flask application.

    This fixture sets the Flask application in testing mode and provides a test client
    that can be used to simulate requests to the application in tests.

    Yields:
        FlaskClient: A test client for the Flask application.
    """

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def reset_active_config():
    """
    Fixture to reset the active configuration before each test.

    This fixture is used to reset the active configuration before each test
    to ensure that each test starts with a clean configuration. It attempts
    to load the configuration from the file system, and if the file is not
    found, it loads the default configuration instead.

    Yields:
        None
    """
    config = load_default_config()
    config.setdefault("solver", {})["min_free_weekends_per_horizon"] = 0
    set_active_config(config)
    yield


def test_home(client):
    """
    Test the home route of the Flask application.

    This test sends a GET request to the root URL ('/') and checks that the
    response status code is 200 (OK) and that the response data contains the
    expected message 'Flask is up and running!'.

    Args:
        client (FlaskClient): The test client used to make requests to the Flask application.

    Asserts:
        - The response status code should be 200 (OK).
        - The response data should contain the expected message.
    """

    response = client.get("/")
    assert response.status_code == 200
    assert b"Flask is up and running!" in response.data


@patch(
    "builtins.open", new_callable=mock_open, read_data='{"holidays": ["01-01-2023"]}'
)
@patch("os.path.exists", return_value=True)
@patch("app.CONFIG_PATH", "config.json")
def test_load_config(mock_path_exists, mock_open_file):
    """
    Test function for load_config.

    This test uses the patch decorator from the unittest.mock module to mock the open function and the os.path.join function.
    It verifies that the load_config function correctly loads the configuration from a JSON file.

    Args:
        mock_path_join (MagicMock): Mocked os.path.join function.
        mock_open_file (MagicMock): Mocked open function with predefined read data.

    Assertions:
        - The loaded configuration matches the expected configuration.
        - The open function is called once with the correct file path and mode.
    """

    expected_config = {"holidays": ["01-01-2023"]}
    config = load_config()
    assert config == expected_config
    mock_open_file.assert_called_once_with("config.json", "r", encoding="utf-8")


@patch("os.path.exists", return_value=False)
@patch("app.CONFIG_PATH", "config.json")
def test_load_config_missing_file_raises_clear_error(mock_path_exists):
    with pytest.raises(FileNotFoundError, match="backend/config\\.json"):
        load_config()


def test_config_route(client):
    set_active_config({"holidays": ["01-01-2023"]})
    response = client.get("/config")
    assert response.status_code == 200
    assert response.json == {"holidays": ["01-01-2023"]}


def test_config_default_route(client):
    """
    Test the /config/default route to ensure it returns the default configuration.

    This test sends a GET request to the /config/default endpoint and checks
    that the response status code is 200 (OK). It also verifies that the response JSON
    contains the expected keys "agents" and "vacations", which are essential components
    of the default configuration.

    Args:
        client: The test client used to make requests to the application.

    Assertions:
        - The response status code should be 200 (OK).
        - The response JSON should contain the expected keys "agents" and "vacations".
    """
    response = client.get("/config/default")
    assert response.status_code == 200
    payload = response.get_json()
    assert "agents" in payload
    assert "vacations" in payload


def test_put_config_route_updates_active_config(client):
    """
    Test that the /config PUT route updates the active configuration.

    This test sends a PUT request to the /config endpoint with a valid configuration payload.
    It checks that the response status code is 200 (OK) and that the response
    JSON contains the updated configuration. It also verifies that the active
    configuration in the application has been updated to match the new configuration.

    Args:
        client: The test client used to make requests to the application.

    Assertions:
        - The response status code should be 200 (OK).
        - The response JSON should contain the updated configuration.
        - The active configuration in the application should match the new configuration.
    """

    new_config = deepcopy(load_default_config())
    new_config["solver"]["max_time_seconds"] = 321

    with patch("app.save_config") as mock_save_config:
        response = client.put(
            "/config", data=json.dumps(new_config), content_type="application/json"
        )

    assert response.status_code == 200
    assert response.get_json()["solver"]["max_time_seconds"] == 321
    assert get_active_config()["solver"]["max_time_seconds"] == 321
    mock_save_config.assert_called_once_with(new_config)


def test_put_config_route_rejects_invalid_config(client):
    """
    Test that the /config PUT route rejects invalid configuration payloads.

    This test sends a PUT request to the /config endpoint with an invalid
    configuration payload (an empty JSON object) and checks that the response
    status code is 400 (Bad Request). It also verifies that the response JSON
    contains an error message indicating the invalid configuration payload and
    that the details field contains a list of validation errors.

    Args:
        client: The test client used to make requests to the application.

    Assertions:
        - The response status code should be 400 (Bad Request).
        - The response JSON should contain an error message indicating the invalid configuration payload.
        - The details field should contain a list of validation errors.
    """

    response = client.put("/config", data=json.dumps({}), content_type="application/json")
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "Invalid configuration payload"
    assert isinstance(payload["details"], list)
    assert payload["details"] != []


def test_generate_planning_uses_runtime_config_after_put(client):
    """
    Test that the /generate-planning route uses the updated configuration
    after a PUT request to /config.

    This test first updates the configuration using a PUT request to the /config endpoint,
    changing the "max_time_seconds" parameter. Then, it sends a POST request
    to the /generate-planning endpoint and checks that the planning generation
    function is called with the updated configuration.

    Args:
        client: The test client used to make requests to the application.

    Assertions:
        - The PUT request to /config should return a 200 status code.
        - The POST request to /generate-planning should return a 200 status code.
        - The planning generation function should be called with the updated configuration.
    """

    new_config = deepcopy(load_default_config())
    new_config["solver"]["max_time_seconds"] = 654

    with patch("app.save_config"):
        update_response = client.put(
            "/config", data=json.dumps(new_config), content_type="application/json"
        )
    assert update_response.status_code == 200

    fake_planning = {agent["name"]: [] for agent in new_config["agents"]}
    with patch("app.generate_planning", return_value=fake_planning) as mocked_generate_planning:
        planning_response = client.post(
            "/generate-planning",
            data=json.dumps({"start_date": "2026-01-05", "end_date": "2026-01-06"}),
            content_type="application/json",
        )

    assert planning_response.status_code == 200
    called_runtime_config = mocked_generate_planning.call_args.kwargs["runtime_config"]
    assert called_runtime_config["solver"]["max_time_seconds"] == 654


def test_generate_planning_route_valid_data(client):
    """
    Test the /generate-planning route with valid data.

    This test sends a POST request to the /generate-planning endpoint with a valid
    date range and checks if the response status code is 200 (OK). It also verifies
    that the response contains a "planning" key and that the "week_schedule" key
    contains 2 days.

    Args:
        client: The test client used to make requests to the application.

    Assertions:
        - The response status code is 200.
        - The response JSON contains a "planning" key.
        - The "week_schedule" key in the response JSON contains 2 days.
    """

    # Keep a short weekday-only range to stay feasible with config.example.json used in CI.
    data = {"start_date": "2026-01-05", "end_date": "2026-01-06"}
    response = client.post(
        "/generate-planning", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
    result = response.get_json()
    assert "planning" in result
    assert result["assignment_labels"]["Jour"] == "Jour"
    assert len(result["week_schedule"]) == 2



def test_optimize_existing_planning_requires_valid_manual_entries(client):
    data = {
        "start_date": "2026-01-05",
        "end_date": "2026-01-06",
        "manual_entries": [{"agent": "Unknown", "date": "2026-01-05", "slot": "day", "type": "shift", "value": "M"}],
    }
    response = client.post(
        "/optimize-existing-planning", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid agent: Unknown"


def test_optimize_existing_planning_accepts_manual_shift_and_returns_ok_status(client):
    agent_name = load_default_config()["agents"][0]["name"]
    forced_day = "2026-01-05"
    forced_vacation = load_default_config()["vacations"][0]
    data = {
        "start_date": forced_day,
        "end_date": "2026-01-06",
        "manual_entries": [
            {
                "agent": agent_name,
                "date": forced_day,
                "slot": "day",
                "type": "shift",
                "value": forced_vacation,
            }
        ],
    }
    response = client.post(
        "/optimize-existing-planning", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["meta"]["manual_cell_count"] == 1
    assert payload["warnings"] == []
    forced_day_label = "Lun. 05-01"
    assert [forced_day_label, forced_vacation] in payload["planning"][agent_name]


def test_optimize_existing_planning_locks_manual_shifts_by_default(client):
    agent_name = load_default_config()["agents"][0]["name"]
    data = {
        "start_date": "2026-01-05",
        "end_date": "2026-01-05",
        "manual_entries": [
            {
                "agent": agent_name,
                "date": "2026-01-05",
                "slot": "day",
                "type": "shift",
                "value": "Jour",
            }
        ],
    }
    fake_result = {
        "planning": {agent_name: [["Lun. 05-01", "Jour"]]},
        "vacation_durations": {"Jour": 12, "Conge": 7},
        "vacation_colors": {},
        "assignable_vacations": ["Jour"],
        "assignment_labels": {"Jour": "Jour"},
        "week_schedule": ["Lun. 05-01"],
        "holidays": [],
        "unavailable": {},
        "dayOff": {},
        "training": {},
        "restrictions": {},
        "restriction_types_durations": {},
    }

    with patch("app._build_planning_payload", return_value=(fake_result, 200)) as build_payload:
        response = client.post(
            "/optimize-existing-planning", data=json.dumps(data), content_type="application/json"
        )

    assert response.status_code == 200
    planning_payload = build_payload.call_args.kwargs["payload"]
    assert planning_payload["initial_shifts"] == {agent_name: [("Lun. 05-01", "Jour")]}
    assert response.get_json()["meta"]["existing_assignments_strict"] is True


def test_optimize_existing_planning_can_keep_manual_shifts_soft(client):
    agent_name = load_default_config()["agents"][0]["name"]
    data = {
        "start_date": "2026-01-05",
        "end_date": "2026-01-05",
        "existing_assignments_strict": False,
        "manual_entries": [
            {
                "agent": agent_name,
                "date": "2026-01-05",
                "slot": "day",
                "type": "shift",
                "value": "Jour",
            }
        ],
    }
    fake_result = {
        "planning": {agent_name: [["Lun. 05-01", "Jour"]]},
        "vacation_durations": {"Jour": 12, "Conge": 7},
        "vacation_colors": {},
        "assignable_vacations": ["Jour"],
        "assignment_labels": {"Jour": "Jour"},
        "week_schedule": ["Lun. 05-01"],
        "holidays": [],
        "unavailable": {},
        "dayOff": {},
        "training": {},
        "restrictions": {},
        "restriction_types_durations": {},
    }

    with patch("app._build_planning_payload", return_value=(fake_result, 200)) as build_payload:
        response = client.post(
            "/optimize-existing-planning", data=json.dumps(data), content_type="application/json"
        )

    assert response.status_code == 200
    planning_payload = build_payload.call_args.kwargs["payload"]
    assert planning_payload["initial_shifts"] == {}
    assert planning_payload["existing_assignments"] == {agent_name: [("Lun. 05-01", "Jour")]}
    assert response.get_json()["meta"]["existing_assignments_strict"] is False


def test_optimize_existing_planning_returns_warning_for_status_entries(client):
    data = {
        "start_date": "2026-01-05",
        "end_date": "2026-01-06",
        "manual_entries": [
            {
                "agent": load_default_config()["agents"][0]["name"],
                "date": "2026-01-05",
                "slot": "day",
                "type": "status",
                "value": "restriction",
            }
        ],
    }
    response = client.post(
        "/optimize-existing-planning", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "warning"
    assert payload["warnings"][0]["code"] == "STATUS_RESTRICTION_REQUIRES_SHIFT"
    assert payload["suggestions"] != []
    assert "planning" in payload
    assert len(payload["week_schedule"]) == 2


def test_optimize_existing_planning_unsat_returns_blocking_reasons_and_suggestions(client):
    agent_name = load_default_config()["agents"][0]["name"]
    data = {
        "start_date": "2026-01-05",
        "end_date": "2026-01-06",
        "manual_entries": [
            {
                "agent": agent_name,
                "date": "2026-01-05",
                "slot": "day",
                "type": "shift",
                "value": load_default_config()["vacations"][0],
            }
        ],
    }
    with patch("app._build_planning_payload", return_value=({"info": "No solution found."}, 400)):
        response = client.post(
            "/optimize-existing-planning", data=json.dumps(data), content_type="application/json"
        )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["status"] == "unsat"
    assert payload["blocking_reasons"] != []
    assert payload["suggestions"] != []


def test_diagnose_manual_entry_conflicts_detects_unavailable_day():
    config = deepcopy(load_default_config())
    agent = config["agents"][0]
    day_str = "15-01-2026"
    agent["unavailable"] = [day_str]

    reasons = _diagnose_manual_entry_conflicts(
        [
            {
                "agent": agent["name"],
                "date": "2026-01-15",
                "slot": "day",
                "type": "shift",
                "value": config["vacations"][0],
            }
        ],
        config,
    )

    reason_codes = [reason["code"] for reason in reasons]
    assert "MANUAL_SHIFT_ON_UNAVAILABLE_DAY" in reason_codes


def test_diagnose_manual_entry_conflicts_detects_understaffed_shift_capacity():
    config = deepcopy(load_default_config())
    config["vacations"] = ["Jour"]
    config["staffing_requirements"] = {"Jour": 2}
    config["agents"] = config["agents"][:2]
    config["agents"][0]["unavailable"] = ["15-01-2026"]
    config["agents"][1]["unavailable"] = ["15-01-2026"]

    reasons = _diagnose_manual_entry_conflicts(
        [
            {
                "agent": config["agents"][0]["name"],
                "date": "2026-01-15",
                "slot": "day",
                "type": "shift",
                "value": "Jour",
            }
        ],
        config,
    )

    staffing_reason = next(
        reason for reason in reasons if reason["code"] == "STAFFING_REQUIREMENT_UNMET"
    )
    assert staffing_reason["count"] == 2
    assert "2026-01-15 / Jour" in staffing_reason["details"][0]
    assert staffing_reason["segments"][0]["date"] == "2026-01-15"
    assert staffing_reason["segments"][0]["vacation"] == "Jour"
    assert staffing_reason["segments"][0]["required_agents"] == 2
    assert staffing_reason["segments"][0]["eligible_agents"] == 0
    assert "status" in staffing_reason["segments"][0]["blockers"]
    assert "free_agent" in staffing_reason["segments"][0]["actions"]


def test_diagnose_manual_entry_conflicts_detects_manual_overstaffing():
    config = deepcopy(load_default_config())
    config["vacations"] = ["Jour"]
    config["staffing_requirements"] = {"Jour": 1}
    config["agents"] = config["agents"][:2]
    for agent in config["agents"]:
        agent["unavailable"] = []
        agent["training"] = []
        agent["vacations"] = []
        agent["restriction"] = []

    reasons = _diagnose_manual_entry_conflicts(
        [
            {
                "agent": config["agents"][0]["name"],
                "date": "2026-01-15",
                "slot": "day",
                "type": "shift",
                "value": "Jour",
            },
            {
                "agent": config["agents"][1]["name"],
                "date": "2026-01-15",
                "slot": "day",
                "type": "shift",
                "value": "Jour",
            },
        ],
        config,
    )

    reason_codes = [reason["code"] for reason in reasons]
    assert "MANUAL_SHIFT_EXCEEDS_STAFFING_REQUIREMENT" in reason_codes


def test_diagnose_manual_entry_conflicts_does_not_emit_day_shift_weekly_quota():
    config = deepcopy(load_default_config())
    agent_name = config["agents"][0]["name"]
    config["solver"]["max_weekly_hours"] = 48
    entries = [
        {
            "agent": agent_name,
            "date": f"2026-01-{day:02d}",
            "slot": "day",
            "type": "shift",
            "value": "Jour",
        }
        for day in range(12, 16)
    ]

    reasons = _diagnose_manual_entry_conflicts(entries, config)

    reason_codes = [reason["code"] for reason in reasons]
    assert "MANUAL_DAY_SHIFT_WEEKLY_LIMIT_EXCEEDED" not in reason_codes

def test_diagnose_manual_entry_conflicts_detects_shift_after_night():
    config = deepcopy(load_default_config())
    agent_name = config["agents"][0]["name"]

    reasons = _diagnose_manual_entry_conflicts(
        [
            {
                "agent": agent_name,
                "date": "2026-01-12",
                "slot": "night",
                "type": "shift",
                "value": "Nuit",
            },
            {
                "agent": agent_name,
                "date": "2026-01-13",
                "slot": "day",
                "type": "shift",
                "value": "Jour",
            },
        ],
        config,
    )

    reason_codes = [reason["code"] for reason in reasons]
    assert "MANUAL_SHIFT_AFTER_NIGHT" in reason_codes


def test_probe_relaxed_hard_constraints_reports_feasible_relaxed_constraint():
    config = deepcopy(load_default_config())

    def fake_build(payload, runtime_config):
        disabled = runtime_config.get("_disabled_hard_constraints_for_diagnostics", [])
        if disabled == ["cover_daily_shifts"]:
            return {"planning": {}}, 200
        return {"info": "No solution found."}, 400

    with patch("app._build_planning_payload", side_effect=fake_build):
        reasons = _probe_relaxed_hard_constraints(
            {
                "start_date": "2026-01-15",
                "end_date": "2026-01-15",
                "initial_shifts": {},
            },
            config,
        )

    assert reasons[0]["code"] == "RELAXED_CONSTRAINT_MAKES_FEASIBLE"
    assert "couverture quotidienne" in reasons[0]["message"]


def test_relaxed_constraints_do_not_include_agent_minimum_assignment():
    constraints = [diagnostic["constraint"] for diagnostic in RELAXED_CONSTRAINT_DIAGNOSTICS]

    assert "require_at_least_one_shift_per_agent" not in constraints


def test_probe_relaxed_hard_constraints_uses_generic_rest_wording():
    config = deepcopy(load_default_config())

    def fake_build(payload, runtime_config):
        disabled = runtime_config.get("_disabled_hard_constraints_for_diagnostics", [])
        if disabled == ["avoid_day_after_night"]:
            return {"planning": {}}, 200
        return {"info": "No solution found."}, 400

    with patch("app._build_planning_payload", side_effect=fake_build):
        reasons = _probe_relaxed_hard_constraints(
            {
                "start_date": "2026-01-15",
                "end_date": "2026-01-15",
                "initial_shifts": {},
            },
            config,
        )

    assert reasons[0]["code"] == "RELAXED_CONSTRAINT_MAKES_FEASIBLE"
    assert "repos après affectation de nuit" in reasons[0]["message"]
    assert "Nuit" not in reasons[0]["message"]


def test_optimize_existing_planning_unsat_uses_relaxed_constraint_diagnostics(client):
    config = deepcopy(load_default_config())
    agent = config["agents"][0]
    agent_name = agent["name"]
    agent["unavailable"] = []
    agent["training"] = []
    agent["vacations"] = []
    agent["restriction"] = []
    set_active_config(config)
    data = {
        "start_date": "2026-01-15",
        "end_date": "2026-01-15",
        "manual_entries": [
            {
                "agent": agent_name,
                "date": "2026-01-15",
                "slot": "day",
                "type": "shift",
                "value": config["vacations"][0],
            }
        ],
    }
    relaxed_reason = {
        "code": "RELAXED_CONSTRAINT_MAKES_FEASIBLE",
        "message": "Une solution devient possible si la contrainte « couverture quotidienne des besoins » est relâchée.",
        "count": 1,
        "details": ["Le besoin configuré semble trop fort."],
    }
    with (
        patch("app._build_planning_payload", return_value=({"info": "No solution found."}, 400)),
        patch("app._probe_relaxed_hard_constraints", return_value=[relaxed_reason]),
    ):
        response = client.post(
            "/optimize-existing-planning", data=json.dumps(data), content_type="application/json"
        )

    payload = response.get_json()
    reason_codes = [reason["code"] for reason in payload["blocking_reasons"]]
    assert "RELAXED_CONSTRAINT_MAKES_FEASIBLE" in reason_codes
    assert "MANUAL_ASSIGNMENTS_IMPACT_UNKNOWN" not in reason_codes


def test_optimize_existing_planning_unsat_returns_unknown_manual_impact_without_specific_diagnostic(client):
    config = deepcopy(load_default_config())
    agent = config["agents"][0]
    agent_name = agent["name"]
    agent["unavailable"] = []
    agent["training"] = []
    agent["vacations"] = []
    agent["restriction"] = []
    set_active_config(config)
    data = {
        "start_date": "2026-01-15",
        "end_date": "2026-01-15",
        "manual_entries": [
            {
                "agent": agent_name,
                "date": "2026-01-15",
                "slot": "day",
                "type": "shift",
                "value": config["vacations"][0],
            }
        ],
    }
    with patch("app._build_planning_payload", return_value=({"info": "No solution found."}, 400)):
        response = client.post(
            "/optimize-existing-planning", data=json.dumps(data), content_type="application/json"
        )
    assert response.status_code == 400
    payload = response.get_json()
    reason_codes = [reason["code"] for reason in payload["blocking_reasons"]]
    assert "GLOBAL_UNSAT" in reason_codes
    assert "MANUAL_ASSIGNMENTS_IMPACT_UNKNOWN" in reason_codes
    assert "MANUAL_ASSIGNMENTS_CONFLICT_POSSIBLE" not in reason_codes
    assert payload["suggestions"] != []


def test_optimize_existing_planning_unsat_returns_generic_blocking_reasons(client):
    config = deepcopy(load_default_config())
    agent_name = config["agents"][0]["name"]
    set_active_config(config)
    data = {
        "start_date": "2026-01-16",
        "end_date": "2026-01-16",
        "manual_entries": [
            {
                "agent": agent_name,
                "date": "2026-01-16",
                "slot": "day",
                "type": "shift",
                "value": config["vacations"][0],
            }
        ],
    }
    with patch("app._build_planning_payload", return_value=({"info": "No solution found."}, 400)):
        response = client.post(
            "/optimize-existing-planning", data=json.dumps(data), content_type="application/json"
        )
    assert response.status_code == 400
    payload = response.get_json()
    reason_codes = [reason["code"] for reason in payload["blocking_reasons"]]
    assert "GLOBAL_UNSAT" in reason_codes
    assert "MANUAL_ASSIGNMENTS_IMPACT_UNKNOWN" in reason_codes
    assert "MANUAL_ASSIGNMENTS_CONFLICT_POSSIBLE" not in reason_codes
    assert payload["suggestions"] != []


def test_optimize_existing_planning_unsat_omits_manual_reason_when_specific_diagnostic_exists(client):
    config = deepcopy(load_default_config())
    config["vacations"] = ["Jour"]
    config["staffing_requirements"] = {"Jour": 1}
    config["agents"] = config["agents"][:2]
    for agent in config["agents"]:
        agent["unavailable"] = []
        agent["training"] = []
        agent["vacations"] = []
        agent["restriction"] = []
    set_active_config(config)
    data = {
        "start_date": "2026-01-15",
        "end_date": "2026-01-15",
        "manual_entries": [
            {
                "agent": config["agents"][0]["name"],
                "date": "2026-01-15",
                "slot": "day",
                "type": "shift",
                "value": "Jour",
            },
            {
                "agent": config["agents"][1]["name"],
                "date": "2026-01-15",
                "slot": "day",
                "type": "shift",
                "value": "Jour",
            },
        ],
    }
    with patch("app._build_planning_payload", return_value=({"info": "No solution found."}, 400)):
        response = client.post(
            "/optimize-existing-planning", data=json.dumps(data), content_type="application/json"
        )

    payload = response.get_json()
    reason_codes = [reason["code"] for reason in payload["blocking_reasons"]]
    assert "MANUAL_SHIFT_EXCEEDS_STAFFING_REQUIREMENT" in reason_codes
    assert "MANUAL_ASSIGNMENTS_IMPACT_UNKNOWN" not in reason_codes
    assert payload["suggestions"][0]["reason_code"] == "MANUAL_SHIFT_EXCEEDS_STAFFING_REQUIREMENT"


def test_optimize_existing_planning_rejects_unknown_status_value(client):
    agent_name = load_default_config()["agents"][0]["name"]
    data = {
        "start_date": "2026-01-05",
        "end_date": "2026-01-06",
        "manual_entries": [
            {
                "agent": agent_name,
                "date": "2026-01-05",
                "slot": "day",
                "type": "status",
                "value": "other_status",
            }
        ],
    }
    response = client.post(
        "/optimize-existing-planning", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid status value: other_status"


def test_optimize_existing_planning_keeps_multiple_manual_shifts(client):
    config = load_default_config()
    agent_a = config["agents"][0]["name"]
    agent_b = config["agents"][1]["name"]
    vacations = config["vacations"]
    data = {
        "start_date": "2026-01-05",
        "end_date": "2026-01-05",
        "manual_entries": [
            {
                "agent": agent_a,
                "date": "2026-01-05",
                "slot": "day",
                "type": "shift",
                "value": vacations[0],
            },
            {
                "agent": agent_b,
                "date": "2026-01-05",
                "slot": "day",
                "type": "shift",
                "value": vacations[1],
            },
        ],
    }
    response = client.post(
        "/optimize-existing-planning", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert ["Lun. 05-01", vacations[0]] in payload["planning"][agent_a]
    assert ["Lun. 05-01", vacations[1]] in payload["planning"][agent_b]
    assert payload["meta"]["manual_cell_count"] == 2


def test_optimize_existing_planning_reports_modified_existing_assignment(client):
    config = deepcopy(load_default_config())
    config["vacations"] = ["Jour", "Nuit"]
    config["staffing_requirements"] = {"Jour": 1, "Nuit": 1}
    config["vacation_durations"] = {"Jour": 12, "Nuit": 12, "Conge": 7}
    config["half_vacations"] = {}
    agent_name = config["agents"][0]["name"]
    set_active_config(config)
    data = {
        "start_date": "2026-01-05",
        "end_date": "2026-01-05",
        "manual_entries": [
            {
                "agent": agent_name,
                "date": "2026-01-05",
                "slot": "day",
                "type": "shift",
                "value": "Jour",
            }
        ],
    }
    fake_result = {
        "planning": {agent_name: [["Lun. 05-01", "Nuit"]]},
        "vacation_durations": {"Jour": 12, "Nuit": 12, "Conge": 7},
        "vacation_colors": {},
        "assignable_vacations": ["Jour", "Nuit"],
        "assignment_labels": {"Jour": "Jour", "Nuit": "Nuit"},
        "week_schedule": ["Lun. 05-01"],
        "holidays": [],
        "unavailable": {},
        "dayOff": {},
        "training": {},
        "restrictions": {},
        "restriction_types_durations": {},
    }
    with patch("app._build_planning_payload", return_value=(fake_result, 200)):
        response = client.post(
            "/optimize-existing-planning", data=json.dumps(data), content_type="application/json"
        )

    payload = response.get_json()
    assert payload["modified_existing_assignments"] == [
        {
            "agent": agent_name,
            "date": "2026-01-05",
            "day": "Lun. 05-01",
            "initial_value": "Jour",
            "final_value": "Nuit",
            "change_type": "changed_to_full",
        }
    ]


def test_inject_manual_status_entries_adds_unavailable_day():
    runtime_config = load_default_config()
    agent_name = runtime_config["agents"][0]["name"]
    updated_config, warnings = _inject_manual_status_entries(
        runtime_config,
        [
            {
                "agent": agent_name,
                "date": "2026-01-06",
                "slot": "day",
                "value": "unavailable",
            }
        ],
    )
    assert warnings == []
    target_agent = next(agent for agent in updated_config["agents"] if agent["name"] == agent_name)
    assert "06-01-2026" in target_agent["unavailable"]


def test_generate_planning_route_invalid_date(client):
    """
    Test the /generate-planning route with an invalid date.

    This test sends a POST request to the /generate-planning endpoint with an invalid start date
    ("2024-11-31") and a valid end date ("2024-11-07"). It verifies that the server responds with
    a 400 status code, indicating that the request failed due to the invalid date.

    Args:
        client: The test client used to make requests to the application.

    Asserts:
        The response status code is 400, indicating a bad request due to the invalid date.
    """

    data = {
        "start_date": "2024-11-31",  # Invalid Date
        "end_date": "2024-11-07",
    }
    response = client.post(
        "/generate-planning", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 400  # Checks if the request fails


def test_generate_planning_route_missing_data(client):
    """
    Test the /generate-planning route with missing data.

    This test sends a POST request to the /generate-planning endpoint with an empty JSON payload.
    It verifies that the server responds with a 400 status code, indicating that the missing data is handled correctly.

    Args:
        client (FlaskClient): The test client used to make requests to the Flask application.

    Asserts:
        The response status code is 400, indicating that the server correctly identifies and handles the missing data.
    """
    response = client.post(
        "/generate-planning", data=json.dumps({}), content_type="application/json"
    )
    assert response.status_code == 400  # Checks that missing data is managed


def test_generate_planning_route_missing_json_payload(client):
    response = client.post("/generate-planning")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Missing or invalid JSON payload"}


def test_generate_planning_route_non_object_json_payload(client):
    response = client.post(
        "/generate-planning",
        data=json.dumps(["2026-01-05", "2026-01-06"]),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "JSON payload must be an object"}


def test_generate_planning_route_end_date_before_start_date(client):
    data = {"start_date": "2026-01-07", "end_date": "2026-01-06"}
    response = client.post(
        "/generate-planning", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 400
    assert response.get_json() == {
        "error": "end_date must be greater than or equal to start_date"
    }


def test_generate_planning_route_initial_shifts_must_be_object(client):
    data = {
        "start_date": "2026-01-05",
        "end_date": "2026-01-06",
        "initial_shifts": [],
    }
    response = client.post(
        "/generate-planning", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "initial_shifts must be an object"}


def test_generate_planning_route_initial_shift_shape_validation(client):
    data = {
        "start_date": "2026-01-05",
        "end_date": "2026-01-06",
        "initial_shifts": {"Agent1": [["Lun. 29-12"]]},
    }
    response = client.post(
        "/generate-planning", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Each initial shift must be [day, vacation] with string values"
    }


def test_generate_planning_route_invalid_agent(client):
    """
    Test the /generate-planning route with an invalid agent.

    This test sends a POST request to the /generate-planning endpoint with a payload
    containing an invalid agent name. It verifies that the response status code is 400
    and that the response JSON contains an error message indicating the invalid agent.

    Args:
        client (FlaskClient): The test client used to make requests to the Flask application.

    Asserts:
        - The response status code is 400.
        - The response JSON contains the error message "Invalid agent: InvalidAgent".
    """
    data = {
        "start_date": "2023-01-01",
        "end_date": "2023-01-07",
        "initial_shifts": {"InvalidAgent": [("Sam. 31-12", "Jour")]},
    }
    response = client.post(
        "/generate-planning", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 400
    assert response.json == {"error": "Invalid agent: InvalidAgent"}


def test_generate_planning_route_invalid_vacation(client):
    """
    Test the /generate-planning route with an invalid vacation entry.

    This test sends a POST request to the /generate-planning endpoint with
    a payload containing an invalid vacation entry for an agent. It verifies
    that the response status code is 400 (Bad Request) and that the response
    JSON contains the appropriate error message indicating the invalid vacation.

    Args:
        client (FlaskClient): The test client used to make requests to the Flask application.

    Asserts:
        - The response status code is 400.
        - The response JSON contains the error message "Invalid vacation: InvalidVacation".
    """
    data = {
        "start_date": "2023-01-01",
        "end_date": "2023-01-07",
        "initial_shifts": {"Agent1": [("Sam. 31-12", "InvalidVacation")]},
    }
    response = client.post(
        "/generate-planning", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 400
    assert response.json == {"error": "Invalid vacation: InvalidVacation"}


def test_previous_week_schedule_missing_json_payload(client):
    response = client.post("/previous-week-schedule")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Missing or invalid JSON payload"}


def test_previous_week_schedule_non_object_json_payload(client):
    response = client.post(
        "/previous-week-schedule", data=json.dumps([]), content_type="application/json"
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "JSON payload must be an object"}


def test_previous_week_schedule_missing_start_date(client):
    response = client.post(
        "/previous-week-schedule", data=json.dumps({}), content_type="application/json"
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "Missing start_date"}


def test_previous_week_schedule_invalid_start_date_format(client):
    response = client.post(
        "/previous-week-schedule",
        data=json.dumps({"start_date": "31-01-2026"}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid date format. Use YYYY-MM-DD."}
