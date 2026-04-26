from datetime import datetime, timedelta

from ortools.sat.python import cp_model

from .constraints import hard, mixed, soft
from .context import SolverContext
from .objective import apply_objective
from .registry import ConstraintRegistry
from .utils import split_into_weeks


def _build_planning_variables(ctx: SolverContext) -> None:
    """
    Builds the planning variables for each agent, day, and vacation type.

    These variables will be used to represent the planning and will be
    used to compute the objective of the model.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]
        for day in set(ctx.week_schedule + ctx.previous_week_schedule):
            for vacation in ctx.vacations:
                ctx.planning[(agent_name, day, vacation)] = ctx.model.NewBoolVar(
                    f"planning_{agent_name}_{day}_{vacation}"
                )


def _load_solver_settings(ctx: SolverContext) -> None:
    """
    Loads the solver settings from the config into the solver context.

    This function sets the following solver context attributes from the config:
    - max_time_seconds: the maximum time in seconds the solver is allowed to run.
    - global_max_gap: the maximum allowed gap in hours * 10 between two consecutive shifts.
    - period_max_gap: the maximum allowed gap in hours * 10 between two consecutive shifts in the same period.
    - relative_gap_limit: the maximum allowed relative gap between two consecutive shifts.
    - num_search_workers: the number of search workers to use.
    - optimize_period_balance: whether to optimize the period balance.
    - period_balance_weight: the weight of the period balance objective.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    solver_config = ctx.config.get("solver", {})
    ctx.max_time_seconds = int(solver_config.get("max_time_seconds", 600))
    ctx.global_max_gap = int(solver_config.get("global_max_gap", 240))
    ctx.period_max_gap = int(solver_config.get("period_max_gap", 240))
    ctx.relative_gap_limit = float(solver_config.get("relative_gap_limit", 0.10))
    ctx.num_search_workers = int(solver_config.get("num_search_workers", 0))
    ctx.optimize_period_balance = bool(solver_config.get("optimize_period_balance", False))
    ctx.period_balance_weight = int(solver_config.get("period_balance_weight", 2))


def _load_shift_durations(ctx: SolverContext) -> None:
    """
    Loads the shift durations from the config into the solver context.

    This function sets vacation durations for all configured vacations and leave.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    configured_durations = ctx.config["vacation_durations"]
    missing_vacation_durations = [
        vacation for vacation in ctx.vacations if vacation not in configured_durations
    ]
    if missing_vacation_durations:
        missing_joined = ", ".join(sorted(missing_vacation_durations))
        raise ValueError(
            "Missing vacation_durations entries for configured vacations: "
            f"{missing_joined}"
        )

    ctx.shift_durations = {
        vacation: int(configured_durations[vacation] * 10) for vacation in ctx.vacations
    }
    ctx.conge_duration = int(ctx.config["vacation_durations"]["Conge"] * 10)

    staffing_config = ctx.config.get("staffing_requirements", {})
    ctx.staffing_requirements = {}
    for vacation in ctx.vacations:
        configured_value = staffing_config.get(vacation, 1)
        required_count = int(configured_value)
        if required_count < 0:
            raise ValueError(
                f"staffing_requirements[{vacation}] must be greater than or equal to 0"
            )
        ctx.staffing_requirements[vacation] = required_count


def _build_registry() -> ConstraintRegistry:
    """
    Builds a constraint registry containing all the hard, soft, and mixed constraints.

    The registry is used to apply the constraints to the model and to
    extract the solution from the solver.

    :return: A constraint registry containing all the constraints.
    :rtype: ConstraintRegistry
    """
    registry = ConstraintRegistry()
    hard.register(registry)
    soft.register(registry)
    mixed.register(registry)
    return registry


def _parse_iso_date(date_value):
    if date_value is None:
        return None
    if isinstance(date_value, datetime):
        return date_value
    if isinstance(date_value, str):
        return datetime.strptime(date_value, "%Y-%m-%d")
    raise ValueError("planning_start_date must be YYYY-MM-DD or datetime")


def _build_day_dates(ctx: SolverContext) -> None:
    start_date = _parse_iso_date(ctx.planning_start_date)
    if start_date is None:
        return

    for idx, day in enumerate(ctx.week_schedule):
        ctx.day_dates[day] = start_date + timedelta(days=idx)

    previous_start = start_date - timedelta(days=7)
    for idx, day in enumerate(ctx.previous_week_schedule):
        # Keep deterministic mapping for continuity constraints when previous week is provided.
        ctx.day_dates.setdefault(day, previous_start + timedelta(days=idx))


def _extract_solution(ctx: SolverContext, solver: cp_model.CpSolver):
    """
    Extracts the solution from the solver and returns it as a dictionary.

    The returned dictionary has the following structure:
    - Each key is an agent name.
    - Each value is a list of tuples, where each tuple contains a day and a vacation type.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    :param solver: The solver used to solve the problem.
    :type solver: cp_model.CpSolver
    :return: The extracted solution as a dictionary.
    :rtype: Dict[str, List[Tuple[str, str]]]
    """
    result = {}
    for agent in ctx.agents:
        agent_name = agent["name"]
        result[agent_name] = []
        for day in ctx.week_schedule:
            for vacation in ctx.vacations:
                if solver.Value(ctx.planning[(agent_name, day, vacation)]):
                    result[agent_name].append((day, vacation))
    return result


def generate_planning(
    agents,
    vacations,
    week_schedule,
    dayOff,
    previous_week_schedule,
    initial_shifts,
    runtime_config,
    planning_start_date=None,
):
    """
    Generates a planning based on the given parameters.

    :param agents: A list of agent names.
    :type agents: List[str]
    :param vacations: A list of vacation types.
    :type vacations: List[str]
    :param week_schedule: A list of days, where each day is represented as a string in the format "YYYY-MM-DD".
    :type week_schedule: List[str]
    :param dayOff: A list of days off, where each day is represented as a string in the format "YYYY-MM-DD".
    :type dayOff: List[str]
    :param previous_week_schedule: A list of days, where each day is represented as a string in the format "YYYY-MM-DD".
    :type previous_week_schedule: List[str]
    :param initial_shifts: A dictionary of initial shifts, where each key is an agent name and each value is a list of tuples, where each tuple contains a day and a shift type.
    :type initial_shifts: Dict[str, List[Tuple[str, str]]]
    :param runtime_config: A dictionary containing the runtime configuration.
    :type runtime_config: Dict[str, Any]
    :return: A dictionary containing the generated planning, where each key is an agent name and each value is a list of tuples, where each tuple contains a day and a vacation type.
    :rtype: Dict[str, List[Tuple[str, str]]]
    """
    model = cp_model.CpModel()
    ctx = SolverContext(
        model=model,
        config=runtime_config,
        agents=agents,
        vacations=vacations,
        week_schedule=week_schedule,
        day_off=dayOff,
        previous_week_schedule=previous_week_schedule,
        initial_shifts=initial_shifts,
        holidays=runtime_config["holidays"],
        planning_start_date=planning_start_date,
    )

    _load_solver_settings(ctx)
    _load_shift_durations(ctx)
    ctx.weeks_split = split_into_weeks(ctx.week_schedule)
    _build_day_dates(ctx)
    _build_planning_variables(ctx)

    registry = _build_registry()
    registry.apply_hard(ctx)
    registry.apply_soft(ctx)
    registry.apply_mixed(ctx)
    apply_objective(ctx)

    solver = cp_model.CpSolver()
    if ctx.num_search_workers > 0:
        solver.parameters.num_search_workers = ctx.num_search_workers
    if ctx.relative_gap_limit > 0:
        solver.parameters.relative_gap_limit = ctx.relative_gap_limit
    solver.parameters.max_time_in_seconds = ctx.max_time_seconds
    status = solver.Solve(ctx.model)

    print(
        "OR-Tools Status:",
        solver.StatusName(status),
        "     conflicts :",
        solver.NumConflicts(),
        "     branches :",
        solver.NumBranches(),
        "     execution time :",
        f"{solver.WallTime():.4f} seconds",
    )

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return _extract_solution(ctx, solver)
    return {"info": "No solution found."}
