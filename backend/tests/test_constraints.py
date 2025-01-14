import pytest
from app import generate_planning

@pytest.fixture
def setup_data():
    agents = [
        {"name": "Agent1", "unavailable": ["01-01-2023"], "training": ["02-01-2023"], "preferences": {"preferred": ["Jour"], "avoid": ["Nuit"]}},
        {"name": "Agent2", "unavailable": ["03-01-2023"], "training": ["04-01-2023"], "preferences": {"preferred": ["Nuit"], "avoid": ["Jour"]}}
    ]
    vacations = ["Jour", "Nuit", "CDP"]
    week_schedule = ["Lun 01-01", "Mar 02-01", "Mer 03-01", "Jeu 04-01", "Ven 05-01", "Sam 06-01", "Dim 07-01"]
    dayOff = ["01-01-2023", "02-01-2023"]
    config = {
        "vacation_durations": {
            "Jour": 7.0,
            "Nuit": 10.0,
            "CDP": 8.0,
            "Conge": 7.0
        }
    }
    holidays = ["01-01-2023"]
    return agents, vacations, week_schedule, dayOff

def test_generate_planning(setup_data):
    agents, vacations, week_schedule, dayOff = setup_data
    result = generate_planning(agents, vacations, week_schedule, dayOff)
    assert isinstance(result, dict)
    assert "Agent1" in result
    assert "Agent2" in result

def test_agent_unavailability(setup_data):
    agents, vacations, week_schedule, dayOff = setup_data
    result = generate_planning(agents, vacations, week_schedule, dayOff)
    assert ("Lun 01-01", "Jour") not in result["Agent1"]
    assert ("Lun 01-01", "Nuit") not in result["Agent1"]
    assert ("Mer 03-01", "Jour") not in result["Agent2"]
    assert ("Mer 03-01", "Nuit") not in result["Agent2"]

def test_agent_training(setup_data):
    agents, vacations, week_schedule, dayOff = setup_data
    result = generate_planning(agents, vacations, week_schedule, dayOff)
    assert ("Mar 02-01", "Jour") not in result["Agent1"]
    assert ("Mar 02-01", "Nuit") not in result["Agent1"]
    assert ("Jeu 04-01", "Jour") not in result["Agent2"]
    assert ("Jeu 04-01", "Nuit") not in result["Agent2"]

def test_vacation_preferences(setup_data):
    agents, vacations, week_schedule, dayOff = setup_data
    result = generate_planning(agents, vacations, week_schedule, dayOff)
    for day, vacation in result["Agent1"]:
        assert vacation != "Nuit", "Agent1 should not be assigned to Nuit vacation"
    for day, vacation in result["Agent2"]:
        assert vacation != "Jour", "Agent2 should not be assigned to Jour vacation"
