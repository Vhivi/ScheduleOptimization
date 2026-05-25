from app import get_week_schedule
import pytest
from solver.engine import generate_planning


def _build_runtime_config(vacations, vacation_durations, staffing_requirements=None):
    return {
        "agents": [
            {
                "name": "Agent1",
                "preferences": {"preferred": [vacations[0]], "avoid": []},
                "restriction": [],
                "unavailable": [],
                "training": [],
                "exclusion": [],
                "vacations": [],
            },
            {
                "name": "Agent2",
                "preferences": {"preferred": [vacations[0]], "avoid": []},
                "restriction": [],
                "unavailable": [],
                "training": [],
                "exclusion": [],
                "vacations": [],
            },
            {
                "name": "Agent3",
                "preferences": {"preferred": [vacations[0]], "avoid": []},
                "restriction": [],
                "unavailable": [],
                "training": [],
                "exclusion": [],
                "vacations": [],
            },
        ],
        "vacations": vacations,
        "vacation_durations": vacation_durations,
        "staffing_requirements": staffing_requirements or {},
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


def test_solver_supports_multiple_agents_per_shift():
    vacations = ["Jour"]
    runtime_config = _build_runtime_config(
        vacations=vacations,
        vacation_durations={"Jour": 12, "Conge": 7},
        staffing_requirements={"Jour": 2},
    )
    agents = runtime_config["agents"]
    week_schedule = get_week_schedule("2026-01-05", "2026-01-06")

    result = generate_planning(
        agents=agents,
        vacations=vacations,
        week_schedule=week_schedule,
        dayOff={agent["name"]: [] for agent in agents},
        previous_week_schedule=get_week_schedule("2025-12-29", "2026-01-04"),
        initial_shifts={},
        runtime_config=runtime_config,
        planning_start_date="2026-01-05",
    )

    assert "info" not in result
    for day in week_schedule:
        assigned = sum(
            1 for shifts in result.values() for shift_day, vacation in shifts if shift_day == day and vacation == "Jour"
        )
        assert assigned == 2


def test_solver_accepts_custom_vacations_without_nuit_or_cdp():
    vacations = ["Jour", "Soutien"]
    runtime_config = _build_runtime_config(
        vacations=vacations,
        vacation_durations={"Jour": 12, "Soutien": 10, "Conge": 7},
        staffing_requirements={"Jour": 1, "Soutien": 1},
    )
    agents = runtime_config["agents"][:2]
    week_schedule = get_week_schedule("2026-01-05", "2026-01-05")

    result = generate_planning(
        agents=agents,
        vacations=vacations,
        week_schedule=week_schedule,
        dayOff={agent["name"]: [] for agent in agents},
        previous_week_schedule=get_week_schedule("2025-12-29", "2026-01-04"),
        initial_shifts={},
        runtime_config=runtime_config,
        planning_start_date="2026-01-05",
    )

    assert "info" not in result
    assigned_vacations = {vacation for shifts in result.values() for _, vacation in shifts}
    assert assigned_vacations.issubset(set(vacations))
    assert assigned_vacations == set(vacations)


def test_solver_enforces_min_free_weekends_per_horizon_when_feasible():
    vacations = ["Jour"]
    runtime_config = _build_runtime_config(
        vacations=vacations,
        vacation_durations={"Jour": 12, "Conge": 7},
        staffing_requirements={"Jour": 1},
    )
    runtime_config["solver"]["min_free_weekends_per_horizon"] = 1
    agents = runtime_config["agents"]
    week_schedule = get_week_schedule("2026-01-05", "2026-01-18")

    result = generate_planning(
        agents=agents,
        vacations=vacations,
        week_schedule=week_schedule,
        dayOff={agent["name"]: [] for agent in agents},
        previous_week_schedule=get_week_schedule("2025-12-29", "2026-01-04"),
        initial_shifts={},
        runtime_config=runtime_config,
        planning_start_date="2026-01-05",
    )

    assert "info" not in result

    weekend_pairs = []
    for idx, day in enumerate(week_schedule[:-1]):
        next_day = week_schedule[idx + 1]
        if day.startswith("Sam") and next_day.startswith("Dim"):
            weekend_pairs.append((day, next_day))

    for agent in agents:
        assignments_by_day = {day for day, _ in result[agent["name"]]}
        free_weekends = sum(
            1
            for saturday, sunday in weekend_pairs
            if saturday not in assignments_by_day and sunday not in assignments_by_day
        )
        assert free_weekends >= 1


def test_solver_rejects_infeasible_min_free_weekends_per_horizon():
    vacations = ["Jour"]
    runtime_config = _build_runtime_config(
        vacations=vacations,
        vacation_durations={"Jour": 12, "Conge": 7},
        staffing_requirements={"Jour": 2},
    )
    runtime_config["solver"]["min_free_weekends_per_horizon"] = 2
    agents = runtime_config["agents"]
    week_schedule = get_week_schedule("2026-01-05", "2026-01-11")

    with pytest.raises(
        ValueError, match="min_free_weekends_per_horizon is infeasible"
    ):
        generate_planning(
            agents=agents,
            vacations=vacations,
            week_schedule=week_schedule,
            dayOff={agent["name"]: [] for agent in agents},
            previous_week_schedule=get_week_schedule("2025-12-29", "2026-01-04"),
            initial_shifts={},
            runtime_config=runtime_config,
            planning_start_date="2026-01-05",
        )
