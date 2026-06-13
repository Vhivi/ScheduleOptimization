from collections import defaultdict
from datetime import datetime, timedelta

from ..catalog import (
    assignment_matches_choice,
    assignment_parent,
    is_half_assignment,
    is_night_assignment,
    requires_next_day_rest,
)
from ..context import SolverContext
from ..registry import ConstraintRegistry
from ..utils import day_token

DAY_SHIFT = "Jour"
NIGHT_SHIFT = "Nuit"
CDP_SHIFT = "CDP"
FRENCH_WEEKDAY_ABBREVIATIONS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


def _has_shift(ctx: SolverContext, shift_name: str) -> bool:
    """
    Checks if the given shift name is in the list of vacations.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    :param shift_name: The name of the shift to check.
    :type shift_name: str
    :return: True if the shift name is in the list of vacations, False otherwise.
    :rtype: bool
    """
    return shift_name in ctx.vacations


def _format_day_label(day_date: datetime) -> str:
    day_name = FRENCH_WEEKDAY_ABBREVIATIONS[day_date.weekday()]
    return f"{day_name}. {day_date.strftime('%d-%m')}"


def register(registry: ConstraintRegistry) -> None:
    """
    Registers all the hard constraints to the given registry.

    The hard constraints are:
    - Apply initial shifts
    - Limit one shift per day
    - Cover daily shifts
    - Avoid day after night
    - Limit CDP per week (historical hard business exception)
    - Block unavailable days
    - Block training days
    - Block leave and compute paid hours
    - Block night before unavailable
    - Block night before training
    - Limit pre/post training
    - Block exclusion days
    - Apply agent restrictions
    """
    registry.register_hard(apply_initial_shifts)
    registry.register_hard(limit_one_shift_per_day)
    registry.register_hard(cover_daily_shifts)
    registry.register_hard(enforce_full_weekend_composition)
    registry.register_hard(enforce_min_free_weekends_per_horizon)
    registry.register_hard(avoid_day_after_night)
    registry.register_hard(limit_cdp_per_week)
    registry.register_hard(block_unavailable_days)
    registry.register_hard(block_training_days)
    registry.register_hard(block_leave_and_compute_paid_hours)
    registry.register_hard(block_night_before_unavailable)
    registry.register_hard(block_night_before_training)
    registry.register_hard(limit_pre_post_training)
    registry.register_hard(block_exclusion_days)
    registry.register_hard(apply_agent_restrictions)


def apply_initial_shifts(ctx: SolverContext) -> None:
    """
    Applies the initial shifts given in the context to the model.

    The initial shifts are represented as a dictionary of agent names
    to lists of tuples, where each tuple contains a day and a vacation type.
    The function will only apply the shifts if the agent name is valid,
    the vacation type is valid, and the day is either in the previous week's
    schedule (continuity seed) or in the current optimization horizon
    (manual existing-schedule optimization).

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    valid_agents = {agent["name"] for agent in ctx.agents}
    for agent_name, shifts in ctx.initial_shifts.items():
        for day, vacation in shifts:
            if (
                agent_name in valid_agents
                and vacation in ctx.assignable_vacations
                and (day in ctx.previous_week_schedule or day in ctx.week_schedule)
            ):
                ctx.model.Add(ctx.planning[(agent_name, day, vacation)] == 1)


def limit_one_shift_per_day(ctx: SolverContext) -> None:
    """
    Limits the number of shifts per day to one.

    This constraint is applied per agent and per day in the week's schedule.
    For each agent, it ensures that the sum of all shift variables for that agent
    on that day is less than or equal to one. This prevents the agent from being
    assigned more than one shift per day.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]
        for day in ctx.week_schedule:
            ctx.model.Add(
                sum(ctx.planning[(agent_name, day, vacation)] for vacation in ctx.assignable_vacations)
                <= 1
            )


def cover_daily_shifts(ctx: SolverContext) -> None:
    """Covers all parent vacation segments with assignable full/half vacations."""
    for day in ctx.week_schedule:
        day_date = day.split(" ")[1]
        day_is_weekend = day.startswith(("Sam", "Dim"))
        day_is_holiday = day_date in ctx.holidays

        for assignment in ctx.assignable_vacations:
            parent = assignment_parent(ctx, assignment)
            if is_half_assignment(ctx, assignment) and (day_is_weekend or day_is_holiday):
                ctx.model.Add(
                    sum(ctx.planning[(agent["name"], day, assignment)] for agent in ctx.agents)
                    == 0
                )
            if parent == CDP_SHIFT and (day_is_weekend or day_is_holiday):
                ctx.model.Add(
                    sum(ctx.planning[(agent["name"], day, assignment)] for agent in ctx.agents)
                    == 0
                )

        for vacation in ctx.vacations:
            required_agents = ctx.staffing_requirements.get(vacation, 1)
            if vacation == CDP_SHIFT and (day_is_weekend or day_is_holiday):
                required_agents = 0
            for segment in ctx.coverage_segments.get(vacation, [vacation]):
                covering_assignments = ctx.segment_covering_assignments.get(
                    (vacation, segment), [vacation]
                )
                ctx.model.Add(
                    sum(
                        ctx.planning[(agent["name"], day, assignment)]
                        for agent in ctx.agents
                        for assignment in covering_assignments
                        if assignment in ctx.assignable_vacations
                    )
                    == required_agents
                )

def enforce_full_weekend_composition(ctx: SolverContext) -> None:
    """
    Ensures weekend assignments are made as full weekends (Saturday + Sunday) per agent.

    For each Saturday/Sunday pair in the planning horizon and for each agent, this
    constraint enforces that the agent either works both days or none of them.
    
    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for day_idx, day in enumerate(ctx.week_schedule[:-1]):
        next_day = ctx.week_schedule[day_idx + 1]
        if not (day.startswith("Sam") and next_day.startswith("Dim")):
            continue

        for agent in ctx.agents:
            agent_name = agent["name"]
            saturday_work = sum(
                ctx.planning[(agent_name, day, vacation)] for vacation in ctx.assignable_vacations
            )
            sunday_work = sum(
                ctx.planning[(agent_name, next_day, vacation)] for vacation in ctx.assignable_vacations
            )
            ctx.model.Add(saturday_work == sunday_work)


def enforce_min_free_weekends_per_horizon(ctx: SolverContext) -> None:
    """
    Enforces a minimum number of fully free weekends per agent on the planning horizon.

    A weekend is considered free for an agent if the agent works neither Saturday nor Sunday
    on the corresponding Saturday/Sunday pair.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    min_free_weekends = max(0, int(ctx.min_free_weekends_per_horizon))
    if min_free_weekends == 0:
        return

    weekend_pairs = []
    for day_idx, day in enumerate(ctx.week_schedule[:-1]):
        next_day = ctx.week_schedule[day_idx + 1]
        if day.startswith("Sam") and next_day.startswith("Dim"):
            weekend_pairs.append((day, next_day))

    total_weekends = len(weekend_pairs)
    if total_weekends == 0:
        return

    max_worked_weekends = total_weekends - min_free_weekends
    if max_worked_weekends < 0:
        raise ValueError(
            "solver.min_free_weekends_per_horizon is infeasible for this planning horizon: "
            f"requested={min_free_weekends}, available_weekends={total_weekends}"
        )

    for agent in ctx.agents:
        agent_name = agent["name"]
        worked_weekend_vars = []

        for saturday, sunday in weekend_pairs:
            works_weekend = ctx.model.NewBoolVar(
                f"{agent_name}_works_weekend_hard_{saturday}_{sunday}"
            )
            saturday_work = sum(
                ctx.planning[(agent_name, saturday, vacation)] for vacation in ctx.assignable_vacations
            )
            sunday_work = sum(
                ctx.planning[(agent_name, sunday, vacation)] for vacation in ctx.assignable_vacations
            )
            ctx.model.Add(saturday_work == 1).OnlyEnforceIf(works_weekend)
            ctx.model.Add(sunday_work == 1).OnlyEnforceIf(works_weekend)
            ctx.model.Add(saturday_work == 0).OnlyEnforceIf(works_weekend.Not())
            ctx.model.Add(sunday_work == 0).OnlyEnforceIf(works_weekend.Not())
            worked_weekend_vars.append(works_weekend)

        ctx.model.Add(sum(worked_weekend_vars) <= max_worked_weekends)

def avoid_day_after_night(ctx: SolverContext) -> None:
    """Blocks assignments that require rest on the next day."""
    rest_trigger_assignments = [
        assignment for assignment in ctx.assignable_vacations if requires_next_day_rest(ctx, assignment)
    ]
    if not rest_trigger_assignments:
        return

    for agent in ctx.agents:
        agent_name = agent["name"]
        for day_idx, day in enumerate(ctx.week_schedule[:-1]):
            next_day = ctx.week_schedule[day_idx + 1]
            for rest_assignment in rest_trigger_assignments:
                rest_var = ctx.planning[(agent_name, day, rest_assignment)]
                for assignment in ctx.assignable_vacations:
                    if is_night_assignment(ctx, assignment):
                        continue
                    ctx.model.Add(ctx.planning[(agent_name, next_day, assignment)] == 0).OnlyEnforceIf(
                        rest_var
                    )

def limit_cdp_per_week(ctx: SolverContext) -> None:
    """
    Limits the number of CDP shifts per week to two.

    CDP keeps this hard historical business exception even though the general
    workload rule is hour-based through solver.max_weekly_hours.

    This constraint is applied per agent and per week in the week's schedule.
    For each agent, it ensures that the sum of all CDP shift variables for that agent
    on that week is less than or equal to two. This prevents the agent from being
    assigned more than two CDP shifts per week.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    if not _has_shift(ctx, CDP_SHIFT):
        return

    for agent in ctx.agents:
        agent_name = agent["name"]
        for week in ctx.weeks_split:
            ctx.model.Add(sum(ctx.planning[(agent_name, day, CDP_SHIFT)] for day in week) <= 2)


def block_unavailable_days(ctx: SolverContext) -> None:
    """
    Blocks unavailable days for all agents.

    This constraint is applied per agent and per day in the week's schedule.
    For each agent, it ensures that the agent is not assigned any shift on unavailable days.
    For each unavailable day, it ensures that the sum of all shift variables for that agent
    on that day is equal to zero. This prevents the agent from being assigned any shift on unavailable days.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]
        unavailable_days = [day_token(date) for date in agent.get("unavailable", [])]
        for unavailable_day in unavailable_days:
            for day in ctx.week_schedule:
                if unavailable_day in day:
                    for vacation in ctx.assignable_vacations:
                        ctx.model.Add(ctx.planning[(agent_name, day, vacation)] == 0)


def block_training_days(ctx: SolverContext) -> None:
    """
    Blocks training days for all agents.

    This constraint is applied per agent and per day in the week's schedule.
    For each agent, it ensures that the agent is not assigned any shift on training days.
    For each training day, it ensures that the sum of all shift variables for that agent
    on that day is equal to zero. This prevents the agent from being assigned any shift on training days.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]
        training_days = [day_token(date) for date in agent.get("training", [])]
        for training_day in training_days:
            for day in ctx.week_schedule:
                if training_day in day:
                    for vacation in ctx.assignable_vacations:
                        ctx.model.Add(ctx.planning[(agent_name, day, vacation)] == 0)


def block_leave_and_compute_paid_hours(ctx: SolverContext) -> None:
    """
    Blocks leave days for all agents and computes the paid hours for each leave day.

    This constraint is applied per agent and per day in the week's schedule.
    For each agent, it ensures that the agent is not assigned any shift on leave days.
    For each leave day, it ensures that the sum of all shift variables for that agent
    on that day is equal to zero. This prevents the agent from being assigned any shift on leave days.

    The paid hours for each leave day are computed by checking if the leave day is a weekday.
    If it is, the paid hours for that day are set to the conge duration.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext

    :return: None
    """
    date_format_full = "%d-%m-%Y"
    leave_paid_hours_by_day = defaultdict(int)

    for agent in ctx.agents:
        agent_name = agent["name"]
        vacations_periods = agent.get("vacations", [])
        if not isinstance(vacations_periods, list):
            continue

        for vac in vacations_periods:
            if not (isinstance(vac, dict) and "start" in vac and "end" in vac):
                continue

            vacation_start = datetime.strptime(vac["start"], date_format_full)
            vacation_end = datetime.strptime(vac["end"], date_format_full)

            for day_str in ctx.week_schedule:
                day_date = ctx.day_dates.get(day_str)
                if day_date is None:
                    day_part = day_str.split(" ")[1]
                    try:
                        day_date = datetime.strptime(
                            f"{day_part}-{vacation_start.year}", date_format_full
                        )
                    except ValueError:
                        continue

                if vacation_start <= day_date <= vacation_end:
                    for vacation in ctx.assignable_vacations:
                        ctx.model.Add(ctx.planning[(agent_name, day_str, vacation)] == 0)
                    if day_date.weekday() < 6:
                        leave_paid_hours_by_day[(agent_name, day_str)] = ctx.conge_duration

            if vacation_start.weekday() == 0:
                previous_saturday = vacation_start - timedelta(days=2)
                previous_sunday = vacation_start - timedelta(days=1)
                for weekend_day in [previous_saturday, previous_sunday]:
                    weekend_str = _format_day_label(weekend_day)
                    if (
                        weekend_str in ctx.week_schedule
                        or weekend_str in ctx.previous_week_schedule
                    ):
                        for vacation in ctx.assignable_vacations:
                            ctx.model.Add(ctx.planning[(agent_name, weekend_str, vacation)] == 0)

    ctx.leave_paid_hours_by_day = leave_paid_hours_by_day

def block_night_before_unavailable(ctx: SolverContext) -> None:
    """
    Blocks night shifts before unavailable days.

    This constraint is applied per agent and per day in the week's schedule.
    For each agent, it ensures that if the agent is unavailable on the next day,
    the agent is not assigned a night shift on the current day.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    rest_trigger_assignments = [
        assignment for assignment in ctx.assignable_vacations if requires_next_day_rest(ctx, assignment)
    ]
    if not rest_trigger_assignments:
        return

    for agent in ctx.agents:
        agent_name = agent["name"]
        unavailable_days = [day_token(date) for date in agent.get("unavailable", [])]
        for day_idx, day in enumerate(ctx.week_schedule[:-1]):
            next_day = ctx.week_schedule[day_idx + 1]
            if any(unavailable_day in next_day for unavailable_day in unavailable_days):
                for assignment in rest_trigger_assignments:
                    ctx.model.Add(ctx.planning[(agent_name, day, assignment)] == 0)


def block_night_before_training(ctx: SolverContext) -> None:
    """
    Blocks night shifts before training days.

    This constraint is applied per agent and per day in the week's schedule.
    For each agent, it ensures that if the agent has a training day on the next day,
    the agent is not assigned a night shift on the current day.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    rest_trigger_assignments = [
        assignment for assignment in ctx.assignable_vacations if requires_next_day_rest(ctx, assignment)
    ]
    if not rest_trigger_assignments:
        return

    for agent in ctx.agents:
        agent_name = agent["name"]
        training_days = [day_token(date) for date in agent.get("training", [])]
        for day_idx, day in enumerate(ctx.week_schedule[:-1]):
            next_day = ctx.week_schedule[day_idx + 1]
            if any(training_day in next_day for training_day in training_days):
                for assignment in rest_trigger_assignments:
                    ctx.model.Add(ctx.planning[(agent_name, day, assignment)] == 0)


def limit_pre_post_training(ctx: SolverContext) -> None:
    """Limits assignment types before and after training days."""
    if not _has_shift(ctx, CDP_SHIFT):
        return

    for agent in ctx.agents:
        agent_name = agent["name"]
        training_days = [day_token(date) for date in agent.get("training", [])]

        for day_idx, day in enumerate(ctx.week_schedule):
            if not any(training_day in day for training_day in training_days):
                continue

            if day_idx > 0:
                previous_day = ctx.week_schedule[day_idx - 1]
                for assignment in ctx.assignable_vacations:
                    if assignment_parent(ctx, assignment) != CDP_SHIFT:
                        ctx.model.Add(ctx.planning[(agent_name, previous_day, assignment)] == 0)

            if day_idx < len(ctx.week_schedule) - 1:
                next_day = ctx.week_schedule[day_idx + 1]
                for assignment in ctx.assignable_vacations:
                    if assignment_parent(ctx, assignment) == CDP_SHIFT or is_night_assignment(ctx, assignment):
                        continue
                    ctx.model.Add(ctx.planning[(agent_name, next_day, assignment)] == 0)

def block_exclusion_days(ctx: SolverContext) -> None:
    """
    Blocks exclusion days for all agents.

    This constraint is applied per agent and per day in the week's schedule.
    For each agent, it ensures that the agent is not assigned any shift on exclusion days.
    For each exclusion day, it ensures that the sum of all shift variables for that agent
    on that day is equal to zero. This prevents the agent from being assigned any shift on exclusion days.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]
        exclusion_days = [day_token(date) for date in agent.get("exclusion", [])]
        for exclusion_day in exclusion_days:
            for day_str in ctx.week_schedule:
                day_date = day_str.split(" ")[1]
                if exclusion_day == day_date:
                    for vacation in ctx.assignable_vacations:
                        ctx.model.Add(ctx.planning[(agent_name, day_str, vacation)] == 0)


def apply_agent_restrictions(ctx: SolverContext) -> None:
    """Applies agent-specific vacation/assignment restrictions."""
    for agent in ctx.agents:
        agent_name = agent["name"]
        restricted_vacations = set(agent.get("restriction", []))
        for day in ctx.week_schedule:
            for assignment in ctx.assignable_vacations:
                if assignment_matches_choice(ctx, assignment, restricted_vacations):
                    ctx.model.Add(ctx.planning[(agent_name, day, assignment)] == 0)
