import json
import pytest
from unittest.mock import patch, mock_open
from app import app
from app import load_config

@pytest.fixture
def client():
    """
    Fixture to create a test client for the Flask application.

    This fixture sets the Flask application in testing mode and provides a test client
    that can be used to simulate requests to the application in tests.

    Yields:
        FlaskClient: A test client for the Flask application.
    """

    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

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
    
    response = client.get('/')
    assert response.status_code == 200
    assert b'Flask is up and running!' in response.data
    
@patch("builtins.open", new_callable=mock_open, read_data='{"holidays": ["01-01-2023"]}')
@patch("os.path.join", return_value="config.json")
def test_load_config(mock_path_join, mock_open_file):
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
    mock_open_file.assert_called_once_with("config.json", "r")

@patch("builtins.open", new_callable=mock_open, read_data='{"holidays": ["01-01-2023"]}')
@patch("os.path.join", return_value="config.json")
def test_config_route(mock_path_join, mock_open_file, client):
    """
    Test the /config route to ensure it returns the correct configuration data.

    This test uses the patch decorator to mock the open function and the os.path.join function.
    The open function is mocked to return a file-like object with the specified read_data.
    The os.path.join function is mocked to return a fixed file path ("config.json").

    Args:
        mock_path_join (MagicMock): Mocked os.path.join function.
        mock_open_file (MagicMock): Mocked open function.
        client (FlaskClient): Test client for making requests to the Flask application.

    Asserts:
        - The response status code should be 200.
        - The response JSON should match the expected configuration data.
    """

    response = client.get("/config")
    assert response.status_code == 200
    assert response.json == {"holidays": ["01-01-2023"]}

def test_generate_planning_route_valid_data(client):
    """
    Test the /generate-planning route with valid data.

    This test sends a POST request to the /generate-planning endpoint with a valid
    date range and checks if the response status code is 200 (OK). It also verifies
    that the response contains a "planning" key and that the "week_schedule" key
    contains 7 days.

    Args:
        client: The test client used to make requests to the application.

    Assertions:
        - The response status code is 200.
        - The response JSON contains a "planning" key.
        - The "week_schedule" key in the response JSON contains 7 days.
    """
    
    data = {
        "start_date": "2024-11-01",
        "end_date": "2024-11-07"
    }
    response = client.post('/generate-planning', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    result = response.get_json()
    assert "planning" in result
    assert len(result["week_schedule"]) == 7  # Checks that 7 days have been generated

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
        "end_date": "2024-11-07"
    }
    response = client.post('/generate-planning', data=json.dumps(data), content_type='application/json')
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
    response = client.post('/generate-planning', data=json.dumps({}), content_type='application/json')
    assert response.status_code == 400  # Checks that missing data is managed
