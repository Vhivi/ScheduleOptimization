from copy import deepcopy

from app import get_week_schedule, validate_runtime_config
from solver.catalog import assignment_matches_choice, build_vacation_catalog
from solver.engine import generate_planning


def _agent(name, preferred=None, restriction=None, unavailable=None):
    return {
        "name": name,
        "preferences": {"preferred": preferred or ["Jour"], "avoid": []},
        "restriction": restriction or [],
        "unavailable": unavailable or [],
        "training": [],
        "exclusion": [],
        "vacations": [],
    }


def _runtime_config():
    return {
        "agents": [
            _agent("Agent1"),
            _agent("Agent2"),
        ],
        "vacations": ["Jour"],
        "staffing_requirements": {"Jour": 1},
        "vacation_durations": {"Jour": 12, "Conge": 7},
        "half_vacations": {
            "Jour": {
                "enabled": True,
                "penalty": 500,
                "segments": [
                    {"name": "Jour matin", "label": "J matin", "duration": 6},
                    {"name": "Jour après-midi", "label": "J aprem", "duration": 6},
                ],
            }
        },
        "vacation_colors": {
            "Jour": "#75FA79",
            "Jour matin": "#B9F6CA",
            "Jour après-midi": "#00C853",
        },
        "holidays": [],
        "solver": {
            "max_time_seconds": 30,
            "relative_gap_limit": 0.1,
            "num_search_workers": 0,
            "global_max_gap": 240,
            "period_max_gap": 240,
            "max_weekly_hours": 42,
            "optimize_period_balance": False,
            "period_balance_weight": 2,
            "min_free_weekends_per_horizon": 0,
        },
    }


def test_half_vacation_config_validates_and_builds_assignable_catalog():
    config = _runtime_config()

    assert validate_runtime_config(config) == []
    catalog = build_vacation_catalog(config)

    assert catalog["coverage_vacations"] == ["Jour"]
    assert catalog["assignable_vacations"] == ["Jour", "Jour matin", "Jour après-midi"]
    assert catalog["assignment_metadata"]["Jour matin"].parent == "Jour"
    assert catalog["assignment_metadata"]["Jour matin"].duration == 60
    assert catalog["segment_covering_assignments"][("Jour", "Jour matin")] == [
        "Jour",
        "Jour matin",
    ]


def test_half_vacation_config_rejects_duration_mismatch():
    config = _runtime_config()
    config["half_vacations"]["Jour"]["segments"][1]["duration"] = 5

    errors = validate_runtime_config(config)

    assert errors
    assert "segment durations must sum" in errors[0]["message"]


def test_solver_can_cover_parent_with_complementary_half_vacations():
    config = _runtime_config()
    agents = config["agents"]
    week_schedule = get_week_schedule("2026-01-05", "2026-01-05")

    result = generate_planning(
        agents=agents,
        vacations=config["vacations"],
        week_schedule=week_schedule,
        dayOff={agent["name"]: [] for agent in agents},
        previous_week_schedule=[],
        initial_shifts={
            "Agent1": [(week_schedule[0], "Jour matin")],
            "Agent2": [(week_schedule[0], "Jour après-midi")],
        },
        runtime_config=config,
        planning_start_date="2026-01-05",
    )

    assert "info" not in result
    assignments = [vacation for shifts in result.values() for _, vacation in shifts]
    assert sorted(assignments) == ["Jour après-midi", "Jour matin"]


def test_half_vacations_are_forbidden_on_weekends():
    config = _runtime_config()
    agents = config["agents"]
    week_schedule = get_week_schedule("2026-01-10", "2026-01-10")

    result = generate_planning(
        agents=agents,
        vacations=config["vacations"],
        week_schedule=week_schedule,
        dayOff={agent["name"]: [] for agent in agents},
        previous_week_schedule=[],
        initial_shifts={
            "Agent1": [(week_schedule[0], "Jour matin")],
            "Agent2": [(week_schedule[0], "Jour après-midi")],
        },
        runtime_config=config,
        planning_start_date="2026-01-10",
    )

    assert "info" in result


def test_solver_chooses_half_vacations_when_full_shift_exceeds_weekly_hours():
    config = _runtime_config()
    config["solver"]["max_weekly_hours"] = 6
    agents = config["agents"]
    week_schedule = get_week_schedule("2026-01-05", "2026-01-05")

    result = generate_planning(
        agents=agents,
        vacations=config["vacations"],
        week_schedule=week_schedule,
        dayOff={agent["name"]: [] for agent in agents},
        previous_week_schedule=[],
        initial_shifts={},
        runtime_config=config,
        planning_start_date="2026-01-05",
    )

    assert "info" not in result
    assignments = [vacation for shifts in result.values() for _, vacation in shifts]
    assert sorted(assignments) == ["Jour après-midi", "Jour matin"]


def test_half_night_requires_next_day_rest():
    config = _runtime_config()
    config["agents"] = [_agent(f"Agent{i}", preferred=["Jour", "Nuit"]) for i in range(1, 5)]
    config["vacations"] = ["Jour", "Nuit"]
    config["staffing_requirements"] = {"Jour": 1, "Nuit": 1}
    config["vacation_durations"] = {"Jour": 12, "Nuit": 12, "Conge": 7}
    config["half_vacations"] = {
        "Nuit": {
            "enabled": True,
            "penalty": 700,
            "segments": [
                {
                    "name": "Nuit début",
                    "label": "N début",
                    "duration": 6,
                    "is_night": True,
                    "requires_next_day_rest": True,
                },
                {
                    "name": "Nuit fin",
                    "label": "N fin",
                    "duration": 6,
                    "is_night": True,
                    "requires_next_day_rest": True,
                },
            ],
        }
    }
    week_schedule = get_week_schedule("2026-01-05", "2026-01-06")

    feasible_result = generate_planning(
        agents=config["agents"],
        vacations=config["vacations"],
        week_schedule=week_schedule,
        dayOff={agent["name"]: [] for agent in config["agents"]},
        previous_week_schedule=[],
        initial_shifts={"Agent1": [(week_schedule[0], "Nuit début")]},
        runtime_config=config,
        planning_start_date="2026-01-05",
    )
    blocked_result = generate_planning(
        agents=config["agents"],
        vacations=config["vacations"],
        week_schedule=week_schedule,
        dayOff={agent["name"]: [] for agent in config["agents"]},
        previous_week_schedule=[],
        initial_shifts={
            "Agent1": [(week_schedule[0], "Nuit début"), (week_schedule[1], "Jour")]
        },
        runtime_config=config,
        planning_start_date="2026-01-05",
    )

    assert "info" not in feasible_result
    assert "info" in blocked_result


def test_half_vacations_are_forbidden_on_holidays():
    config = _runtime_config()
    config["holidays"] = ["05-01"]
    agents = config["agents"]
    week_schedule = get_week_schedule("2026-01-05", "2026-01-05")

    result = generate_planning(
        agents=agents,
        vacations=config["vacations"],
        week_schedule=week_schedule,
        dayOff={agent["name"]: [] for agent in agents},
        previous_week_schedule=[],
        initial_shifts={
            "Agent1": [(week_schedule[0], "Jour matin")],
            "Agent2": [(week_schedule[0], "Jour après-midi")],
        },
        runtime_config=config,
        planning_start_date="2026-01-05",
    )

    assert "info" in result


def test_parent_restriction_blocks_half_vacation_segments():
    config = _runtime_config()
    config["agents"][0]["restriction"] = ["Jour"]
    agents = config["agents"]
    week_schedule = get_week_schedule("2026-01-05", "2026-01-05")

    result = generate_planning(
        agents=agents,
        vacations=config["vacations"],
        week_schedule=week_schedule,
        dayOff={agent["name"]: [] for agent in agents},
        previous_week_schedule=[],
        initial_shifts={
            "Agent1": [(week_schedule[0], "Jour matin")],
            "Agent2": [(week_schedule[0], "Jour après-midi")],
        },
        runtime_config=config,
        planning_start_date="2026-01-05",
    )

    assert "info" in result


def test_avoid_parent_inherits_and_segment_avoid_is_targeted():
    config = _runtime_config()
    catalog = build_vacation_catalog(config)

    assert assignment_matches_choice(catalog, "Jour matin", {"Jour"})
    assert assignment_matches_choice(catalog, "Jour matin", {"Jour matin"})
    assert not assignment_matches_choice(catalog, "Jour après-midi", {"Jour matin"})


def test_config_rejects_cdp_half_vacations():
    config = deepcopy(_runtime_config())
    config["vacations"] = ["Jour", "CDP"]
    config["vacation_durations"]["CDP"] = 5.5
    config["half_vacations"]["CDP"] = {
        "enabled": True,
        "penalty": 1000,
        "segments": [
            {"name": "CDP matin", "duration": 2.75},
            {"name": "CDP après-midi", "duration": 2.75},
        ],
    }

    errors = validate_runtime_config(config)

    assert any(error["path"] == "half_vacations/CDP" for error in errors)
