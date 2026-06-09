from copy import deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from ortools.sat.python import cp_model
from app import generate_planning, get_active_config, load_default_config, set_active_config
from solver.catalog import AssignmentMetadata
from solver.constraints.mixed import limit_weekly_nights_and_hours


def _solve_forced_weekly_shifts(max_weekly_hours):
    model = cp_model.CpModel()
    agent_name = "Agent1"
    vacations = ["Jour", "Nuit"]
    week = ["Lun. 01-06", "Mar. 02-06", "Mer. 03-06", "Jeu. 04-06"]
    planning = {
        (agent_name, day, vacation): model.NewBoolVar(
            f"planning_{agent_name}_{day}_{vacation}"
        )
        for day in week
        for vacation in vacations
    }

    ctx = SimpleNamespace(
        agents=[{"name": agent_name}],
        vacations=vacations,
        weeks_split=[week],
        planning=planning,
        shift_durations={"Jour": 120, "Nuit": 120},
        max_weekly_hours=max_weekly_hours,
        model=model,
    )

    limit_weekly_nights_and_hours(ctx)

    forced_shifts = {
        ("Lun. 01-06", "Jour"),
        ("Mar. 02-06", "Jour"),
        ("Mer. 03-06", "Nuit"),
        ("Jeu. 04-06", "Nuit"),
    }
    for day in week:
        for vacation in vacations:
            model.Add(
                planning[(agent_name, day, vacation)]
                == int((day, vacation) in forced_shifts)
            )

    solver = cp_model.CpSolver()
    return solver.Solve(model)


def _solve_forced_temporal_weekly_shifts(max_weekly_hours):
    model = cp_model.CpModel()
    agent_name = "Agent1"
    vacations = ["Jour", "Nuit"]
    week = [
        "Lun. 05-01",
        "Mar. 06-01",
        "Mer. 07-01",
        "Jeu. 08-01",
        "Ven. 09-01",
        "Sam. 10-01",
        "Dim. 11-01",
    ]
    planning = {
        (agent_name, day, vacation): model.NewBoolVar(
            f"planning_{agent_name}_{day}_{vacation}"
        )
        for day in week
        for vacation in vacations
    }
    start_date = datetime(2026, 1, 5)

    ctx = SimpleNamespace(
        agents=[{"name": agent_name}],
        vacations=vacations,
        assignable_vacations=vacations,
        weeks_split=[week],
        week_schedule=week,
        planning=planning,
        day_dates={day: start_date + timedelta(days=index) for index, day in enumerate(week)},
        assignment_metadata={
            "Jour": AssignmentMetadata(name="Jour", parent="Jour", duration=120),
            "Nuit": AssignmentMetadata(
                name="Nuit",
                parent="Nuit",
                duration=120,
                is_night=True,
                requires_next_day_rest=True,
                start_time="19:00",
                end_time="07:00",
            ),
        },
        shift_durations={"Jour": 120, "Nuit": 120},
        max_weekly_hours=max_weekly_hours,
        model=model,
    )

    limit_weekly_nights_and_hours(ctx)

    forced_shifts = {
        ("Mar. 06-01", "Jour"),
        ("Ven. 09-01", "Nuit"),
        ("Sam. 10-01", "Nuit"),
        ("Dim. 11-01", "Nuit"),
    }
    for day in week:
        for vacation in vacations:
            model.Add(
                planning[(agent_name, day, vacation)]
                == int((day, vacation) in forced_shifts)
            )

    solver = cp_model.CpSolver()
    return solver.Solve(model)


@pytest.fixture(autouse=True)
def _use_legacy_solver_defaults_for_constraints_tests():
    previous_config = deepcopy(get_active_config())
    test_config = deepcopy(load_default_config())
    test_config.setdefault("solver", {})["min_free_weekends_per_horizon"] = 0
    set_active_config(test_config)
    yield
    set_active_config(previous_config)


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
            "preferences": {"preferred": ["Jour", "CDP"], "avoid": ["Nuit"]},
        },
        {
            "name": "Agent6",
            "unavailable": ["04-01-2023"],
            "training": ["05-01-2023"],
            "preferences": {"preferred": ["Nuit"], "avoid": []},
        },
        {
            "name": "Agent7",
            "unavailable": ["06-01-2023"],
            "training": ["07-01-2023"],
            "preferences": {"preferred": ["Jour"], "avoid": ["Nuit"]},
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

@pytest.fixture
def setup_staff_leave_weekend():
    """
    Fixture to set up data for testing staff leave and check if the weekend shifts are not assigned.

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
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour", "CDP"], "avoid": ["Nuit"]},
            "vacations": [
                { "start": "06-01-2025", "end": "12-01-2025" }
            ]
        },
        {
            "name": "Agent2",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Nuit"], "avoid": ["Jour", "CDP"]},
            "vacations": []
        },
        {
            "name": "Agent3",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Nuit"], "avoid": []},
            "vacations": []
        },
        {
            "name": "Agent4",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour", "CDP"], "avoid": ["Nuit"]},
        },
        {
            "name": "Agent5",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour", "CDP"], "avoid": ["Nuit"]},
        },
        {
            "name": "Agent6",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Nuit"], "avoid": []},
        },
        {
            "name": "Agent7",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour"], "avoid": []},
        },
        {
            "name": "Agent8",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour"], "avoid": []},
        },
    ]
    vacations = ["Jour", "Nuit", "CDP"]
    week_schedule = [
        "Sam. 04-01",
        "Dim. 05-01",
        "Lun. 06-01",
        "Mar. 07-01",
        "Mer. 08-01",
        "Jeu. 09-01",
        "Ven. 10-01",
        "Sam. 11-01",
        "Dim. 12-01",
    ]
    dayOff = ["01-01-2025"]
    previous_week_schedule = []
    
    return agents, vacations, week_schedule, dayOff, previous_week_schedule


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


def test_generate_planning_paid_leave_hours_balancing_regression():
    """
    Regression test: paid leave hours must be included in balancing with worked hours.

    With a strong paid-leave asymmetry, the solver should still find a solution when
    worked shifts can compensate the global balance.
    """

    agents = [
        {
            "name": "Agent1",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour"], "avoid": []},
            "vacations": [{"start": "06-01-2025", "end": "06-01-2025"}],
        },
        {
            "name": "Agent2",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour"], "avoid": []},
            "vacations": [],
        },
    ]
    vacations = ["Jour"]
    week_schedule = [
        "Lun. 06-01",
        "Mar. 07-01",
        "Mer. 08-01",
    ]

    result = generate_planning(
        agents,
        vacations,
        week_schedule,
        dayOff={},
        previous_week_schedule=[],
        initial_shifts={},
        runtime_config={
            "vacation_durations": {"Jour": 12, "Conge": 7},
            "staffing_requirements": {"Jour": 1},
            "holidays": [],
            "solver": {
                "max_time_seconds": 30,
                "relative_gap_limit": 0.1,
                "num_search_workers": 0,
                "global_max_gap": 240,
                "period_max_gap": 240,
                "optimize_period_balance": False,
                "period_balance_weight": 2,
                "min_free_weekends_per_horizon": 0,
            },
        },
    )

    assert isinstance(result, dict)
    assert "info" not in result


def test_generate_planning_allows_agent_with_full_period_leave_to_have_no_shift():
    """
    Agents fully blocked by leave should not make the model infeasible merely
    because they receive no worked assignment on the generated period.
    """

    agents = [
        {
            "name": "Agent1",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour"], "avoid": []},
            "vacations": [{"start": "05-01-2026", "end": "09-01-2026"}],
            "restriction": [],
            "exclusion": [],
        },
        {
            "name": "Agent2",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour"], "avoid": []},
            "vacations": [],
            "restriction": [],
            "exclusion": [],
        },
    ]
    vacations = ["Jour"]
    week_schedule = [
        "Lun. 05-01",
        "Mar. 06-01",
        "Mer. 07-01",
        "Jeu. 08-01",
        "Ven. 09-01",
    ]

    result = generate_planning(
        agents,
        vacations,
        week_schedule,
        dayOff={},
        previous_week_schedule=[],
        initial_shifts={},
        planning_start_date="2026-01-05",
        runtime_config={
            "vacation_durations": {"Jour": 12, "Conge": 7},
            "staffing_requirements": {"Jour": 1},
            "holidays": [],
            "solver": {
                "max_time_seconds": 30,
                "relative_gap_limit": 0.1,
                "num_search_workers": 0,
                "global_max_gap": 600,
                "period_max_gap": 600,
                "max_weekly_hours": 60,
                "optimize_period_balance": False,
                "period_balance_weight": 2,
                "min_free_weekends_per_horizon": 0,
            },
        },
    )

    assert "info" not in result
    assert result["Agent1"] == []
    assert len(result["Agent2"]) == len(week_schedule)


def test_generate_planning_ignores_leave_periods_from_other_years():
    """
    Regression test: leave periods from another year must not block a target planning year.

    With exactly three agents and three shifts per day, blocking one agent on a day
    makes the model infeasible. A 2025 leave must not affect a 2026 planning.
    """

    agents = [
        {
            "name": "Agent1",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour", "Nuit", "CDP"], "avoid": []},
            "vacations": [{"start": "01-04-2025", "end": "03-04-2025"}],
            "restriction": [],
            "exclusion": [],
        },
        {
            "name": "Agent2",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour", "Nuit", "CDP"], "avoid": []},
            "vacations": [],
            "restriction": [],
            "exclusion": [],
        },
        {
            "name": "Agent3",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour", "Nuit", "CDP"], "avoid": []},
            "vacations": [],
            "restriction": [],
            "exclusion": [],
        },
    ]
    vacations = ["Jour", "Nuit", "CDP"]
    week_schedule = ["Mar. 01-04", "Mer. 02-04", "Jeu. 03-04"]

    result = generate_planning(
        agents,
        vacations,
        week_schedule,
        dayOff={},
        previous_week_schedule=[],
        initial_shifts={},
        planning_start_date="2026-04-01",
    )

    assert isinstance(result, dict)
    assert "info" not in result


def test_monday_leave_blocks_previous_weekend_with_french_day_labels():
    """
    Regression test: leave starting on Monday must block the preceding Saturday/Sunday.

    The weekend labels must use the same French format as week_schedule; otherwise
    the constraint silently misses the generated days.
    """

    agents = [
        {
            "name": "Agent1",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour"], "avoid": []},
            "vacations": [{"start": "06-01-2025", "end": "10-01-2025"}],
            "restriction": [],
            "exclusion": [],
        },
        {
            "name": "Agent2",
            "unavailable": [],
            "training": [],
            "preferences": {"preferred": ["Jour"], "avoid": []},
            "vacations": [],
            "restriction": [],
            "exclusion": [],
        },
    ]
    vacations = ["Jour"]
    week_schedule = [
        "Sam. 04-01",
        "Dim. 05-01",
        "Lun. 06-01",
    ]

    result = generate_planning(
        agents,
        vacations,
        week_schedule,
        dayOff={},
        previous_week_schedule=[],
        initial_shifts={
            "Agent1": [
                ("Sam. 04-01", "Jour"),
                ("Dim. 05-01", "Jour"),
            ]
        },
        planning_start_date="2025-01-04",
        runtime_config={
            "vacation_durations": {"Jour": 12, "Conge": 7},
            "staffing_requirements": {"Jour": 1},
            "holidays": [],
            "solver": {
                "max_time_seconds": 30,
                "relative_gap_limit": 0.1,
                "num_search_workers": 0,
                "global_max_gap": 600,
                "period_max_gap": 600,
                "max_weekly_hours": 60,
                "optimize_period_balance": False,
                "period_balance_weight": 2,
                "min_free_weekends_per_horizon": 0,
            },
        },
    )

    assert result == {"info": "No solution found."}


def test_weekly_hours_limit_counts_night_shifts_with_default_cap():
    """
    Regression test: weekly hour cap must count night shifts, not only day/CDP.

    Two day shifts and two night shifts at 12h each exceed the default 36h cap,
    even though day-only hours and night-only count are independently valid.
    """

    status = _solve_forced_weekly_shifts(max_weekly_hours=360)

    assert status == cp_model.INFEASIBLE


def test_weekly_hours_limit_uses_configured_cap():
    """
    The same 48h worked week becomes feasible when solver.max_weekly_hours is 48.
    """

    status = _solve_forced_weekly_shifts(max_weekly_hours=480)

    assert status in [cp_model.OPTIMAL, cp_model.FEASIBLE]


def test_weekly_hours_limit_splits_sunday_overnight_shift():
    """
    Tuesday day + Friday/Saturday nights + Sunday night is 41h in the current
    week when Sunday 19:00-07:00 contributes only 5h before Monday.
    """

    status = _solve_forced_temporal_weekly_shifts(max_weekly_hours=450)

    assert status in [cp_model.OPTIMAL, cp_model.FEASIBLE]
    
######
# Test failed, possible bug in the generate_planning function (constraint not respected or too soft)
# Investigate the generate_planning function to find out why
# Perhaps target the weekend constraint
######
# def test_staff_leave_weekend(setup_staff_leave_weekend):
#     """
#     Checks if an agent has a period of leave starting on a Monday,
#     shifts from the previous weekend (Saturday and Sunday) are not allocated.
    
#     Args:
#         setup_staff_leave_weekend (tuple): A tuple containing the following elements:
#             - agents (list): A list of agent names.
#             - vacations_list (list): A list of vacation periods.
#             - week_schedule (list): A list representing the weekly schedule.
#             - dayOff (list): A list of days off.
#             - previous_week_schedule (list): A list representing the previous week's schedule.
            
#     Asserts:
#         The test checks that the specified agents do not have any shifts (day or night)
#         on the days they are supposed to be in training.
#     """
#     agents, vacations_list, week_schedule, dayOff, previous_week_schedule = setup_staff_leave_weekend
    
#     result = generate_planning(agents, vacations_list, week_schedule, dayOff, previous_week_schedule, initial_shifts={})
#     print(result)   # Affiche le planning généré pour test
#     # On s'attend à ce qu'aucun shift ne soit attribué pour "Agent1" les jours "Sam. 04-01" et "Dim. 05-01"
#     assert ("Sam. 04-01", "Jour") not in result["Agent1"]
#     assert ("Sam. 04-01", "Nuit") not in result["Agent1"]
#     assert ("Dim. 05-01", "Jour") not in result["Agent1"]
#     assert ("Dim. 05-01", "Nuit") not in result["Agent1"]

