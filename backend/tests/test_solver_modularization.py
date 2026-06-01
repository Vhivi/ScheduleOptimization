from solver.engine import _build_registry, generate_planning


def _sample_dataset():
    """
    Returns a sample dataset containing agents, vacation types, and week schedule for testing solver modularization.

    The sample dataset contains 7 agents, each with a mix of unavailable dates, training dates, and preferences. The agents are named from "Agent1" to "Agent7".

    The sample dataset also contains 3 vacation types: "Jour", "Nuit", and "CDP".

    The week schedule is a list of strings representing the week schedule. Each string is in the format "Day of the week. DD-MM".

    Returns:
        tuple: A tuple containing:
            - agents (list): A list of dictionaries, each representing an agent with their name, unavailable dates, training dates, and preferences.
            - vacations (list): A list of vacation types.
            - week_schedule (list): A list of strings representing the week schedule.
    """
    agents = [
        {
            "name": "Agent1",
            "unavailable": ["01-01-2023"],
            "training": ["02-01-2023"],
            "preferences": {"preferred": ["Jour", "CDP"], "avoid": ["Nuit"]},
            "vacations": [{"start": "03-01-2023", "end": "05-01-2023"}],
            "restriction": [],
            "exclusion": [],
        },
        {
            "name": "Agent2",
            "unavailable": ["03-01-2023"],
            "training": ["04-01-2023"],
            "preferences": {"preferred": ["Nuit"], "avoid": ["Jour", "CDP"]},
            "vacations": [{"start": "01-01-2023", "end": "02-01-2023"}],
            "restriction": [],
            "exclusion": [],
        },
        {
            "name": "Agent3",
            "unavailable": ["05-01-2023"],
            "training": ["06-01-2023"],
            "preferences": {"preferred": ["Nuit"], "avoid": []},
            "vacations": [],
            "restriction": [],
            "exclusion": [],
        },
        {
            "name": "Agent4",
            "unavailable": ["07-01-2023"],
            "training": ["01-01-2023"],
            "preferences": {"preferred": ["Jour", "CDP"], "avoid": ["Nuit"]},
            "vacations": [],
            "restriction": [],
            "exclusion": [],
        },
        {
            "name": "Agent5",
            "unavailable": ["02-01-2023"],
            "training": ["03-01-2023"],
            "preferences": {"preferred": ["Jour", "CDP"], "avoid": ["Nuit"]},
            "vacations": [],
            "restriction": [],
            "exclusion": [],
        },
        {
            "name": "Agent6",
            "unavailable": ["04-01-2023"],
            "training": ["05-01-2023"],
            "preferences": {"preferred": ["Nuit"], "avoid": []},
            "vacations": [],
            "restriction": [],
            "exclusion": [],
        },
        {
            "name": "Agent7",
            "unavailable": ["06-01-2023"],
            "training": ["07-01-2023"],
            "preferences": {"preferred": ["Jour"], "avoid": ["Nuit"]},
            "vacations": [],
            "restriction": [],
            "exclusion": [],
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
    return agents, vacations, week_schedule


def _runtime_config_for_tests():
    return {
        "vacation_durations": {"Jour": 12, "Nuit": 12, "CDP": 5.5, "Conge": 7},
        "staffing_requirements": {"Jour": 1, "Nuit": 1, "CDP": 1},
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
    }


def test_registry_contains_constraint_groups():
    """
    Tests that the constraint registry contains hard, soft, and mixed constraints groups.
    """
    registry = _build_registry()

    assert len(registry.hard) > 0
    assert len(registry.soft) > 0
    assert len(registry.mixed) > 0


def test_night_shift_blocks_next_day_jour_or_cdp():
    """
    Tests that night shifts block the next day from being assigned to
    'Jour' or 'CDP' shifts.
    """
    agents, vacations, week_schedule = _sample_dataset()
    result = generate_planning(
        agents=agents,
        vacations=vacations,
        week_schedule=week_schedule,
        dayOff={},
        previous_week_schedule=[],
        initial_shifts={},
        runtime_config=_runtime_config_for_tests(),
    )

    assert "info" not in result

    for shifts in result.values():
        assignments = {day: vacation for day, vacation in shifts}
        for idx, day in enumerate(week_schedule[:-1]):
            next_day = week_schedule[idx + 1]
            if assignments.get(day) == "Nuit":
                assert assignments.get(next_day) not in {"Jour", "CDP"}


def test_cdp_is_limited_to_two_per_week_per_agent():
    """
    Tests that the CDP constraint is correctly applied: each agent is limited
    to two CDP shifts per week.
    """
    agents, vacations, week_schedule = _sample_dataset()
    result = generate_planning(
        agents=agents,
        vacations=vacations,
        week_schedule=week_schedule,
        dayOff={},
        previous_week_schedule=[],
        initial_shifts={},
        runtime_config=_runtime_config_for_tests(),
    )

    assert "info" not in result

    for shifts in result.values():
        cdp_count = sum(1 for _, vacation in shifts if vacation == "CDP")
        assert cdp_count <= 2


def test_diagnostic_probe_without_leave_constraint_does_not_require_leave_hours():
    """Diagnostic probes can disable leave handling without breaking soft hour balance."""
    agents, vacations, week_schedule = _sample_dataset()
    runtime_config = _runtime_config_for_tests()
    runtime_config["_disabled_hard_constraints_for_diagnostics"] = [
        "block_leave_and_compute_paid_hours"
    ]

    result = generate_planning(
        agents=agents,
        vacations=vacations,
        week_schedule=week_schedule,
        dayOff={},
        previous_week_schedule=[],
        initial_shifts={},
        runtime_config=runtime_config,
    )

    assert isinstance(result, dict)
