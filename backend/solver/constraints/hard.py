from collections import defaultdict
from datetime import datetime, timedelta

from ..context import SolverContext
from ..registry import ConstraintRegistry
from ..utils import day_token


def register(registry: ConstraintRegistry) -> None:
    """
    Registers all the hard constraints to the given registry.

    The hard constraints are:
    - Apply initial shifts
    - Limit one shift per day
    - Require at least one shift per agent
    - Cover daily shifts
    - Avoid day after night
    - Limit CDP per week
    - Block unavailable days
    - Block training days
    - Block leave and compute paid hours
    - Limit day shifts per week
    - Block night before unavailable
    - Block night before training
    - Limit pre/post training
    - Block exclusion days
    - Block Monday night after weekend nights
    - Apply agent restrictions
    """
    registry.register_hard(apply_initial_shifts)
    registry.register_hard(limit_one_shift_per_day)
    registry.register_hard(require_at_least_one_shift_per_agent)
    registry.register_hard(cover_daily_shifts)
    registry.register_hard(avoid_day_after_night)
    registry.register_hard(limit_cdp_per_week)
    registry.register_hard(block_unavailable_days)
    registry.register_hard(block_training_days)
    registry.register_hard(block_leave_and_compute_paid_hours)
    registry.register_hard(limit_day_shifts_per_week)
    registry.register_hard(block_night_before_unavailable)
    registry.register_hard(block_night_before_training)
    registry.register_hard(limit_pre_post_training)
    registry.register_hard(block_exclusion_days)
    registry.register_hard(block_monday_night_after_weekend_nights)
    registry.register_hard(apply_agent_restrictions)


def apply_initial_shifts(ctx: SolverContext) -> None:
    """
    Applies the initial shifts given in the context to the model.

    The initial shifts are represented as a dictionary of agent names
    to lists of tuples, where each tuple contains a day and a vacation type.
    The function will only apply the shifts if the agent name is valid,
    the vacation type is valid, and the day is in the previous week's schedule.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    valid_agents = {agent["name"] for agent in ctx.agents}
    for agent_name, shifts in ctx.initial_shifts.items():
        for day, vacation in shifts:
            if (
                agent_name in valid_agents
                and vacation in ctx.vacations
                and day in ctx.previous_week_schedule
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
                sum(ctx.planning[(agent_name, day, vacation)] for vacation in ctx.vacations)
                <= 1
            )


def require_at_least_one_shift_per_agent(ctx: SolverContext) -> None:
    """
    Requires each agent to have at least one shift per week.

    This constraint is applied per agent and ensures that the sum of all shift variables
    for that agent on all days in the week's schedule is greater than or equal to one.
    This prevents the agent from being assigned no shifts at all.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]
        ctx.model.Add(
            sum(
                ctx.planning[(agent_name, day, vacation)]
                for day in ctx.week_schedule
                for vacation in ctx.vacations
            )
            >= 1
        )


def cover_daily_shifts(ctx: SolverContext) -> None:
    """
    Covers all daily shifts with one agent shift per day.

    This constraint is applied per day in the week's schedule.
    For each day, it ensures that the sum of all shift variables for all agents
    on that day is equal to one. This prevents the day from being left uncovered.

    For days that are part of a weekend or fall on a holiday, and for CDP shifts,
    it ensures that the sum of all shift variables for all agents on that day is zero.
    This prevents CDP shifts from being assigned on weekends or holidays.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for day in ctx.week_schedule:
        day_date = day.split(" ")[1]
        day_is_weekend = day.startswith(("Sam", "Dim"))
        for vacation in ctx.vacations:
            if vacation == "CDP" and (day_is_weekend or day_date in ctx.holidays):
                ctx.model.Add(
                    sum(ctx.planning[(agent["name"], day, "CDP")] for agent in ctx.agents)
                    == 0
                )
            else:
                ctx.model.Add(
                    sum(
                        ctx.planning[(agent["name"], day, vacation)]
                        for agent in ctx.agents
                    )
                    == 1
                )


def avoid_day_after_night(ctx: SolverContext) -> None:
    """
    Avoids assigning a day shift after a night shift.

    This constraint is applied per agent and per day in the week's schedule.
    For each agent, it ensures that if the agent is assigned a night shift on a given day,
    the agent is not assigned a day shift on the next day.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]
        for day_idx, day in enumerate(ctx.week_schedule[:-1]):
            next_day = ctx.week_schedule[day_idx + 1]
            nuit_var = ctx.planning[(agent_name, day, "Nuit")]
            jour_var = ctx.planning[(agent_name, next_day, "Jour")]
            cdp_var = ctx.planning[(agent_name, next_day, "CDP")]
            ctx.model.Add(jour_var == 0).OnlyEnforceIf(nuit_var)
            ctx.model.Add(cdp_var == 0).OnlyEnforceIf(nuit_var)


def limit_cdp_per_week(ctx: SolverContext) -> None:
    """
    Limits the number of CDP shifts per week to two.

    This constraint is applied per agent and per week in the week's schedule.
    For each agent, it ensures that the sum of all CDP shift variables for that agent
    on that week is less than or equal to two. This prevents the agent from being
    assigned more than two CDP shifts per week.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]
        for week in ctx.weeks_split:
            ctx.model.Add(sum(ctx.planning[(agent_name, day, "CDP")] for day in week) <= 2)


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
                    for vacation in ctx.vacations:
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
                    for vacation in ctx.vacations:
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
                    for vacation in ctx.vacations:
                        ctx.model.Add(ctx.planning[(agent_name, day_str, vacation)] == 0)
                    if day_date.weekday() < 6:
                        leave_paid_hours_by_day[(agent_name, day_str)] = ctx.conge_duration

            if vacation_start.weekday() == 0:
                previous_saturday = vacation_start - timedelta(days=2)
                previous_sunday = vacation_start - timedelta(days=1)
                for weekend_day in [previous_saturday, previous_sunday]:
                    weekend_str = weekend_day.strftime("%a %d-%m").capitalize()
                    if (
                        weekend_str in ctx.week_schedule
                        or weekend_str in ctx.previous_week_schedule
                    ):
                        for vacation in ctx.vacations:
                            ctx.model.Add(ctx.planning[(agent_name, weekend_str, vacation)] == 0)

    ctx.leave_paid_hours_by_day = leave_paid_hours_by_day


def limit_day_shifts_per_week(ctx: SolverContext) -> None:
    """
    Limits the number of day shifts per week to three.

    This constraint is applied per agent and per week in the week's schedule.
    For each agent, it ensures that the sum of all day shift variables for that agent
    on that week is less than or equal to three. This prevents the agent from being
    assigned more than three day shifts per week.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    week_days = [
        (day, datetime.strptime(day.split(" ")[1], "%d-%m")) for day in ctx.week_schedule
    ]
    weeks_dict = defaultdict(list)
    for day_str, day_date in week_days:
        week_number = day_date.isocalendar()[:2]
        weeks_dict[week_number].append(day_str)

    for agent in ctx.agents:
        agent_name = agent["name"]
        for days in weeks_dict.values():
            ctx.model.Add(sum(ctx.planning[(agent_name, day, "Jour")] for day in days) <= 3)


def block_night_before_unavailable(ctx: SolverContext) -> None:
    """
    Blocks night shifts before unavailable days.

    This constraint is applied per agent and per day in the week's schedule.
    For each agent, it ensures that if the agent is unavailable on the next day,
    the agent is not assigned a night shift on the current day.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]
        unavailable_days = [day_token(date) for date in agent.get("unavailable", [])]
        for day_idx, day in enumerate(ctx.week_schedule[:-1]):
            next_day = ctx.week_schedule[day_idx + 1]
            if any(unavailable_day in next_day for unavailable_day in unavailable_days):
                ctx.model.Add(ctx.planning[(agent_name, day, "Nuit")] == 0)


def block_night_before_training(ctx: SolverContext) -> None:
    """
    Blocks night shifts before training days.

    This constraint is applied per agent and per day in the week's schedule.
    For each agent, it ensures that if the agent has a training day on the next day,
    the agent is not assigned a night shift on the current day.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]
        training_days = [day_token(date) for date in agent.get("training", [])]
        for day_idx, day in enumerate(ctx.week_schedule[:-1]):
            next_day = ctx.week_schedule[day_idx + 1]
            if any(training_day in next_day for training_day in training_days):
                ctx.model.Add(ctx.planning[(agent_name, day, "Nuit")] == 0)


def limit_pre_post_training(ctx: SolverContext) -> None:
    """
    Limits vacation types before and after training days.

    This constraint is applied per agent and per day in the week's schedule.
    For each agent, it ensures that the agent is not assigned any vacation type
    except for CDP and night shifts on the day after a training day, and that the agent
    is not assigned any vacation type except for CDP on the day before a training day.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]
        training_days = [day_token(date) for date in agent.get("training", [])]

        for day_idx, day in enumerate(ctx.week_schedule):
            if not any(training_day in day for training_day in training_days):
                continue

            if day_idx > 0:
                previous_day = ctx.week_schedule[day_idx - 1]
                for vacation in ctx.vacations:
                    if vacation != "CDP":
                        ctx.model.Add(ctx.planning[(agent_name, previous_day, vacation)] == 0)

            if day_idx < len(ctx.week_schedule) - 1:
                next_day = ctx.week_schedule[day_idx + 1]
                allowed_vacations = ["CDP", "Nuit"]
                for vacation in ctx.vacations:
                    if vacation not in allowed_vacations:
                        ctx.model.Add(ctx.planning[(agent_name, next_day, vacation)] == 0)


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
                    for vacation in ctx.vacations:
                        ctx.model.Add(ctx.planning[(agent_name, day_str, vacation)] == 0)


def block_monday_night_after_weekend_nights(ctx: SolverContext) -> None:
    """
    Blocks Monday night shifts after weekend night shifts.

    This constraint is applied per agent and per day in the week's schedule.
    For each agent, it ensures that if the agent is assigned a night shift on a Saturday,
    the agent is not assigned a night shift on the following Monday.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]
        for day_idx, day in enumerate(ctx.week_schedule[:-2]):
            if "Sam" in day:
                sunday_idx = day_idx + 1
                monday_idx = day_idx + 2
                if sunday_idx < len(ctx.week_schedule) and monday_idx < len(ctx.week_schedule):
                    sunday = ctx.week_schedule[sunday_idx]
                    monday = ctx.week_schedule[monday_idx]
                    saturday_night = ctx.planning[(agent_name, day, "Nuit")]
                    sunday_night = ctx.planning[(agent_name, sunday, "Nuit")]
                    ctx.model.Add(ctx.planning[(agent_name, monday, "Nuit")] == 0).OnlyEnforceIf(
                        [saturday_night, sunday_night]
                    )


def apply_agent_restrictions(ctx: SolverContext) -> None:
    """
    Applies agent-specific vacation restrictions.

    This constraint is applied per agent and per day in the week's schedule.
    For each agent, it ensures that the agent is not assigned any restricted vacation type
    on any day of the week.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]
        restricted_vacations = agent.get("restriction", [])
        for day in ctx.week_schedule:
            for restricted_vacation in restricted_vacations:
                ctx.model.Add(ctx.planning[(agent_name, day, restricted_vacation)] == 0)
