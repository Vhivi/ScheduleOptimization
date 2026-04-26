import json
from copy import deepcopy
from unittest.mock import mock_open, patch

import pytest
from app import (
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
    try:
        set_active_config(load_config())
    except FileNotFoundError:
        set_active_config(load_default_config())
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
    assert len(result["week_schedule"]) == 2  # Checks that 2 days have been generated


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
