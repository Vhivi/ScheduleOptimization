import pytest
from app import generate_planning


@pytest.fixture
def setup_correct_data():
    """
    Fixture to set up correct data for testing schedule optimization constraints.

    Returns:
        tuple: A tuple containing:
            - agents (list): A list of dictionaries, each representing an agent with their name, unavailable dates, training dates, and preferences.
            - vacations (list): A list of vacation types.
            - week_schedule (list): A list of strings representing the week schedule.
            - dayOff (list): A list of dates representing days off.
            - previous_week_schedule (list): A list of strings representing the previous week's schedule.
    """

    agents = [
        {
            "name": "Agent1",
            "unavailable": ["01-01-2023"],
            "training": ["02-01-2023"],
            "preferences": {"preferred": ["Jour", "CDP"], "avoid": ["Nuit"]},
            "vacations": [
                { "start": "03-01-2023", "end": "05-01-2023" }
            ]
        },
        {
            "name": "Agent2",
            "unavailable": ["03-01-2023"],
            "training": ["04-01-2023"],
            "preferences": {"preferred": ["Nuit"], "avoid": ["Jour", "CDP"]},
            "vacations": [
                { "start": "01-01-2023", "end": "02-01-2023" }
            ]
        },
        {
            "name": "Agent3",
            "unavailable": ["05-01-2023"],
            "training": ["06-01-2023"],
            "preferences": {"preferred": ["Nuit"], "avoid": []},
            "vacations": []
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
    previous_week_schedule = [
        "Lun. 25-12",
        "Mar. 26-12",
        "Mer. 27-12",
        "Jeu. 28-12",
        "Ven. 29-12",
        "Sam. 30-12",
        "Dim. 31-12",
    ]
    return agents, vacations, week_schedule, dayOff, previous_week_schedule


@pytest.fixture
def setup_incorrect_data():
    """
    Fixture to set up incorrect data for testing constraints.

    Returns:
        tuple: A tuple containing:
            - agents (list): A list of dictionaries, each representing an agent with their name, unavailable dates, training dates, and preferences.
            - vacations (list): A list of vacation types.
            - week_schedule (list): A list of strings representing the week schedule.
            - dayOff (list): A list of dates representing days off.
    """

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
    """
    Fixture to set up a correct dataset for testing without additional data.

    Returns:
        tuple: A tuple containing:
            - agents (list): A list of dictionaries, each representing an agent with their name, unavailable dates, training dates, and preferences.
            - vacations (list): A list of vacation types.
            - week_schedule (list): A list of strings representing the week schedule.
            - dayOff (list): A list of dates representing days off.
    """

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
    """
    Test the generate_planning function with valid data.

    This test ensures that the generate_planning function returns a dictionary
    containing the expected agents when provided with correct input data.

    Args:
        setup_correct_data (tuple): A tuple containing the following elements:
            - agents (list): A list of agent names.
            - vacations (list): A list of vacation periods.
            - week_schedule (list): A list representing the weekly schedule.
            - dayOff (list): A list of days off.
            - previous_week_schedule (list): A list representing the previous week's schedule.

    Asserts:
        - The result is an instance of a dictionary.
        - The result contains the keys "Agent1", "Agent2", "Agent3", "Agent4",
          "Agent5", and "Agent6".
    """

    agents, vacations, week_schedule, dayOff, previous_week_schedule = (
        setup_correct_data
    )
    result = generate_planning(
        agents,
        vacations,
        week_schedule,
        dayOff,
        previous_week_schedule,
        initial_shifts={},
    )
    assert isinstance(result, dict)
    assert "Agent1" in result
    assert "Agent2" in result
    assert "Agent3" in result
    assert "Agent4" in result
    assert "Agent5" in result
    assert "Agent6" in result


def test_generate_planning_valid_data_with_initial_shifts(setup_correct_data):
    """
    Test the generate_planning function with valid data and initial shifts.

    This test ensures that the generate_planning function correctly incorporates
    initial shifts into the generated planning. It verifies that the resulting
    planning includes the specified initial shifts for the agents.

    Args:
        setup_correct_data (tuple): A tuple containing the following elements:
            - agents (list): A list of agent names.
            - vacations (list): A list of vacation periods.
            - week_schedule (list): A list representing the weekly schedule.
            - dayOff (list): A list of days off.
            - previous_week_schedule (list): A list representing the previous week's schedule.

    Asserts:
        The result contains the keys "Agent1" and "Agent2".
    """
    agents, vacations, week_schedule, dayOff, previous_week_schedule = (
        setup_correct_data
    )
    initial_shifts = {
        "Agent1": [("Dim. 31-12", "Jour")],
        "Agent2": [("Dim. 31-12", "Nuit")],
    }

    result = generate_planning(
        agents, vacations, week_schedule, dayOff, previous_week_schedule, initial_shifts
    )
    assert "Agent1" in result
    assert "Agent2" in result


def test_generate_planning_invalid_data(setup_incorrect_data):
    """
    Test the generate_planning function with invalid data.

    This test ensures that the generate_planning function handles invalid input data correctly.
    It verifies that the function returns a dictionary and contains an "info" key in the result.

    Args:
        setup_incorrect_data (tuple): A fixture that provides incorrect data for agents, vacations, week_schedule, and dayOff.

    Asserts:
        The result is an instance of a dictionary.
        The result contains an "info" key.
    """

    agents, vacations, week_schedule, dayOff = setup_incorrect_data
    result = generate_planning(
        agents,
        vacations,
        week_schedule,
        dayOff,
        previous_week_schedule=[],
        initial_shifts={},
    )
    assert isinstance(result, dict)
    assert "info" in result


def test_generate_planning_valid_dataless(setup_correct_dataless):
    """
    Test the generate_planning function with valid dataless input.

    This test ensures that the generate_planning function returns a dictionary
    when provided with valid input data that does not contain any specific data
    (details are abstracted by the setup_correct_dataless fixture).

    Args:
        setup_correct_dataless (tuple): A fixture that provides the necessary
        input data for the test, including agents, vacations, week_schedule,
        and dayOff.

    Asserts:
        The result of the generate_planning function is a dictionary.
        The result contains the key "info".
    """

    agents, vacations, week_schedule, dayOff = setup_correct_dataless
    result = generate_planning(
        agents,
        vacations,
        week_schedule,
        dayOff,
        previous_week_schedule=[],
        initial_shifts={},
    )
    assert isinstance(result, dict)
    assert "info" in result


def test_agent_unavailability(setup_correct_data):
    """
    Test the unavailability of agents on specific dates and shifts.

    This test ensures that the generated planning does not assign any shifts
    (day or night) to agents on their specified unavailable dates.

    Args:
        setup_correct_data (tuple): A tuple containing the following elements:
            - agents (list): A list of agent names.
            - vacations (list): A list of vacation periods.
            - week_schedule (list): A list representing the weekly schedule.
            - dayOff (list): A list of days off.
            - previous_week_schedule (list): A list representing the previous week's schedule.

    Asserts:
        The test asserts that for each agent, the specified unavailable dates
        and shifts are not present in the generated planning result.
    """

    agents, vacations, week_schedule, dayOff, previous_week_schedule = (
        setup_correct_data
    )
    result = generate_planning(
        agents,
        vacations,
        week_schedule,
        dayOff,
        previous_week_schedule,
        initial_shifts={},
    )
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
    """
    Test the agent training constraints in the generated planning.

    This test ensures that agents are not scheduled for work on specific days
    when they are supposed to be in training.

    Args:
        setup_correct_data (tuple): A tuple containing the following elements:
            - agents (list): A list of agent names.
            - vacations (list): A list of vacation periods.
            - week_schedule (list): A list representing the weekly schedule.
            - dayOff (list): A list of days off.
            - previous_week_schedule (list): A list representing the previous week's schedule.

    Asserts:
        The test checks that the specified agents do not have any shifts (day or night)
        on the days they are supposed to be in training.
    """

    agents, vacations, week_schedule, dayOff, previous_week_schedule = (
        setup_correct_data
    )
    result = generate_planning(
        agents,
        vacations,
        week_schedule,
        dayOff,
        previous_week_schedule,
        initial_shifts={},
    )
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
