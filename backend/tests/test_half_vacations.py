from app import get_week_schedule, validate_runtime_config
from solver.catalog import build_vacation_catalog
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
