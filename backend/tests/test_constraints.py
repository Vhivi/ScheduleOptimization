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
    """
    Test the vacation preferences of agents in the generated planning.
    This test checks if the generated planning respects the 'avoid' preferences of each agent.
    It prints a note if an agent is assigned to a vacation that they prefer to avoid.
    Args:
        setup_correct_data (tuple): A tuple containing the setup data for the test, which includes:
            - agents (list): A list of agents with their details and preferences.
            - vacations (list): A list of available vacations.
            - week_schedule (dict): The weekly schedule.
            - dayOff (list): A list of days off.
    Returns:
        None
    """
    agents, vacations, week_schedule, dayOff = setup_correct_data
    result = generate_planning(agents, vacations, week_schedule, dayOff)
    
    for agent in agents:
        name = agent['name']
        avoid_preferences = agent['preferences'].get('avoid', [])
        for _, vacation in result[name]:
            if vacation in avoid_preferences:
                print(f"Note: {name} has been assigned to {vacation} which is in their avoid preferences.")
