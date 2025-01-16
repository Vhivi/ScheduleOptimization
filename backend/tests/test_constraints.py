import pytest
from app import generate_planning


@pytest.fixture
def setup_correct_data():
    agents = [
        {
            "name": "Agent1",
            "unavailable": ["01-01-2023"],
            "training": ["02-01-2023"],
            "preferences": {"preferred": ["Jour", "CDP"], "avoid": ["Nuit"]},
        },
        {
            "name": "Agent2",
            "unavailable": ["03-01-2023"],
            "training": ["04-01-2023"],
            "preferences": {"preferred": ["Nuit"], "avoid": ["Jour", "CDP"]},
        },
        {
            "name": "Agent3",
            "unavailable": ["05-01-2023"],
            "training": ["06-01-2023"],
            "preferences": {"preferred": ["Nuit"], "avoid": []},
        },
        {
            "name": "Agent4",
            "unavailable": ["07-01-2023"],
            "training": ["01-01-2023"],
            "preferences": {"preferred": ["Jour", "CDP"], "avoid": ["Nuit"]},
        },
        {
            "name": "Agent5",
            "unavailable": ["02-01-2023"],
            "training": ["03-01-2023"],
            "preferences": {"preferred": ["JourCDP"], "avoid": ["Nuit"]},
        },
        {
            "name": "Agent6",
            "unavailable": ["04-01-2023"],
            "training": ["05-01-2023"],
            "preferences": {"preferred": ["Nuit"], "avoid": []},
        },
    ]
    vacations = ["Jour", "Nuit", "CDP"]
    week_schedule = [
        "Lun. 01-01",
        "Mar. 02-01",
        "Mer. 03-01",
        "Jeu. 04-01",
        "Ven. 05-01",
        "Sam. 06-01",
        "Dim. 07-01",
    ]
    dayOff = ["01-01-2023", "02-01-2023"]
    return agents, vacations, week_schedule, dayOff


@pytest.fixture
def setup_incorrect_data():
    agents = [
        {
            "name": "Agent1",
            "unavailable": ["01-01-2023"],
            "training": ["02-01-2023"],
            "preferences": {"preferred": ["Jour"], "avoid": ["Nuit"]},
        },
        {
            "name": "Agent2",
            "unavailable": ["03-01-2023"],
            "training": ["04-01-2023"],
            "preferences": {"preferred": ["Nuit"], "avoid": ["Jour"]},
        },
    ]
    vacations = ["Jour", "Nuit", "CDP"]
    week_schedule = [
        "Lun. 01-01",
        "Mer. 03-01",
        "Jeu. 04-01",
        "Ven. 05-01",
        "Sam. 06-01",
        "Dim. 07-01",
    ]
    dayOff = ["01-01-2023", "02-01-2023"]
    return agents, vacations, week_schedule, dayOff


@pytest.fixture
def setup_correct_dataless():
    agents = [
        {
            "name": "Agent1",
            "unavailable": ["01-01-2023"],
            "training": ["02-01-2023"],
            "preferences": {"preferred": ["Jour"], "avoid": ["Nuit"]},
        },
        {
            "name": "Agent2",
            "unavailable": ["03-01-2023"],
            "training": ["04-01-2023"],
            "preferences": {"preferred": ["Nuit"], "avoid": ["Jour"]},
        },
    ]
    vacations = ["Jour", "Nuit", "CDP"]
    week_schedule = [
        "Lun. 01-01",
        "Mar. 02-01",
        "Mer. 03-01",
        "Jeu. 04-01",
        "Ven. 05-01",
        "Sam. 06-01",
        "Dim. 07-01",
    ]
    dayOff = ["01-01-2023", "02-01-2023"]
    return agents, vacations, week_schedule, dayOff


def test_generate_planning_valid_data(setup_correct_data):
    agents, vacations, week_schedule, dayOff = setup_correct_data
    result = generate_planning(agents, vacations, week_schedule, dayOff)
    assert isinstance(result, dict)
    assert "Agent1" in result
    assert "Agent2" in result
    assert "Agent3" in result
    assert "Agent4" in result
    assert "Agent5" in result
    assert "Agent6" in result


def test_generate_planning_invalid_data(setup_incorrect_data):
    agents, vacations, week_schedule, dayOff = setup_incorrect_data
    result = generate_planning(agents, vacations, week_schedule, dayOff)
    assert isinstance(result, dict)
    assert "info" in result


def test_generate_planning_valid_dataless(setup_correct_dataless):
    agents, vacations, week_schedule, dayOff = setup_correct_dataless
    result = generate_planning(agents, vacations, week_schedule, dayOff)
    assert isinstance(result, dict)
    assert "info" in result


def test_agent_unavailability(setup_correct_data):
    agents, vacations, week_schedule, dayOff = setup_correct_data
    result = generate_planning(agents, vacations, week_schedule, dayOff)
    assert ("Lun. 01-01", "Jour") not in result["Agent1"]
    assert ("Lun. 01-01", "Nuit") not in result["Agent1"]
    assert ("Mer. 03-01", "Jour") not in result["Agent2"]
    assert ("Mer. 03-01", "Nuit") not in result["Agent2"]
    assert ("Ven. 05-01", "Jour") not in result["Agent3"]
    assert ("Ven. 05-01", "Nuit") not in result["Agent3"]
    assert ("Dim. 07-01", "Jour") not in result["Agent4"]
    assert ("Dim. 07-01", "Nuit") not in result["Agent4"]
    assert ("Mar. 02-01", "Jour") not in result["Agent5"]
    assert ("Mar. 02-01", "Nuit") not in result["Agent5"]
    assert ("Jeu. 04-01", "Jour") not in result["Agent6"]
    assert ("Jeu. 04-01", "Nuit") not in result["Agent6"]


def test_agent_training(setup_correct_data):
    agents, vacations, week_schedule, dayOff = setup_correct_data
    result = generate_planning(agents, vacations, week_schedule, dayOff)
    assert ("Mar. 02-01", "Jour") not in result["Agent1"]
    assert ("Mar. 02-01", "Nuit") not in result["Agent1"]
    assert ("Jeu. 04-01", "Jour") not in result["Agent2"]
    assert ("Jeu. 04-01", "Nuit") not in result["Agent2"]
    assert ("Sam. 06-01", "Jour") not in result["Agent3"]
    assert ("Sam. 06-01", "Nuit") not in result["Agent3"]
    assert ("Lun. 01-01", "Jour") not in result["Agent4"]
    assert ("Lun. 01-01", "Nuit") not in result["Agent4"]
    assert ("Mer. 03-01", "Jour") not in result["Agent5"]
    assert ("Mer. 03-01", "Nuit") not in result["Agent5"]
    assert ("Ven. 05-01", "Jour") not in result["Agent6"]
    assert ("Ven. 05-01", "Nuit") not in result["Agent6"]


def test_vacation_preferences(setup_correct_data):
    agents, vacations, week_schedule, dayOff = setup_correct_data
    result = generate_planning(agents, vacations, week_schedule, dayOff)
    for _, vacation in result["Agent1"]:
        assert vacation != "Nuit", "Agent1 should not be assigned to Nuit vacation"
    for _, vacation in result["Agent2"]:
        assert vacation not in ["Jour", "CDP"], (
            "Agent2 should not be assigned to Jour or CDP vacation"
        )
    for _, vacation in result["Agent3"]:
        assert vacation not in ["Jour", "CDP"], (
            "Agent3 should not be assigned to Jour or CDP vacation"
        )
    for _, vacation in result["Agent4"]:
        assert vacation != "Nuit", "Agent4 should not be assigned to Nuit vacation"
    for _, vacation in result["Agent5"]:
        assert vacation != "Nuit", "Agent5 should not be assigned to Nuit vacation"
    for _, vacation in result["Agent6"]:
        assert vacation not in ["Jour", "CDP"], (
            "Agent6 should not be assigned to Jour or CDP vacation"
        )
