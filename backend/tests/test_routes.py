import json
import pytest
from unittest.mock import patch, mock_open
from app import app
from app import load_config

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Flask is up and running!' in response.data
    
@patch("builtins.open", new_callable=mock_open, read_data='{"holidays": ["01-01-2023"]}')
@patch("os.path.join", return_value="config.json")
def test_load_config(mock_path_join, mock_open_file):
    expected_config = {"holidays": ["01-01-2023"]}
    config = load_config()
    assert config == expected_config
    mock_open_file.assert_called_once_with("config.json", "r")

@patch("builtins.open", new_callable=mock_open, read_data='{"holidays": ["01-01-2023"]}')
@patch("os.path.join", return_value="config.json")
def test_config_route(mock_path_join, mock_open_file, client):
    response = client.get("/config")
    assert response.status_code == 200
    assert response.json == {"holidays": ["01-01-2023"]}

def test_generate_planning_route_valid_data(client):
    data = {
        "start_date": "2024-11-01",
        "end_date": "2024-11-07"
    }
    response = client.post('/generate-planning', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    result = response.get_json()
    assert "planning" in result
    assert len(result["week_schedule"]) == 7  # Vérifie que 7 jours sont bien générés

def test_generate_planning_route_invalid_date(client):
    data = {
        "start_date": "2024-11-31",  # Date invalide
        "end_date": "2024-11-07"
    }
    response = client.post('/generate-planning', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 400  # Vérifie que la requête échoue

def test_generate_planning_route_missing_data(client):
    response = client.post('/generate-planning', data=json.dumps({}), content_type='application/json')
    assert response.status_code == 400  # Vérifie que les données manquantes sont gérées
