from datetime import date, timedelta

from ..context import SolverContext
from ..registry import ConstraintRegistry
from ..utils import weekly_hour_contribution_tenths

DAY_SHIFT = "Jour"
NIGHT_SHIFT = "Nuit"
CDP_SHIFT = "CDP"


def _external_assignment_hours(ctx: SolverContext, agent_name: str, day: str) -> int:
    return getattr(ctx, "external_assignment_hours_by_day", {}).get(
        (agent_name, day), 0
    )


def register(registry: ConstraintRegistry) -> None:
    """
    Registers all the mixed constraints to the given registry.

    The mixed constraints are:
    - Limit weekly nights and hours

    :param registry: The registry to which the constraints should be registered.
    :type registry: ConstraintRegistry
    """
    registry.register_mixed(limit_weekly_worked_hours)


def limit_weekly_worked_hours(ctx: SolverContext) -> None:
    """Caps weekly worked hours using solver.max_weekly_hours."""
    assignable_vacations = getattr(ctx, "assignable_vacations", None) or ctx.vacations
    day_dates = getattr(ctx, "day_dates", {}) or {}
    assignment_metadata = getattr(ctx, "assignment_metadata", {}) or {}

    for agent in ctx.agents:
        agent_name = agent["name"]

        for week in ctx.weeks_split:
            if not day_dates:
                days_to_count = week
                week_key = None
            else:
                week_day_dates = [day_dates[day] for day in week if day in day_dates]
                if not week_day_dates:
                    days_to_count = week
                    week_key = None
                else:
                    week_key = week_day_dates[0].isocalendar()[:2]
                    week_start = date.fromisocalendar(week_key[0], week_key[1], 1)
                    scheduled_days = list(
                        dict.fromkeys(
                            getattr(ctx, "previous_week_schedule", [])
                            + getattr(ctx, "week_schedule", week)
                        )
                    )
                    days_to_count = [
                        day
                        for day in scheduled_days
                        if day_dates.get(day)
                        and week_start - timedelta(days=1)
                        <= day_dates[day].date()
                        < week_start + timedelta(days=7)
                    ]

            total_hours = sum(
                sum(
                    ctx.planning[(agent_name, day, vacation)]
                    * (
                        weekly_hour_contribution_tenths(
                            day_dates.get(day),
                            assignment_metadata.get(vacation),
                            ctx.shift_durations[vacation],
                            week_key,
                        )
                        if week_key is not None
                        else ctx.shift_durations[vacation]
                    )
                    for vacation in assignable_vacations
                )
                + (
                    getattr(ctx, "training_hours_by_day", {}).get(
                        (agent_name, day), 0
                    )
                    if week_key is None
                    or day_dates[day].isocalendar()[:2] == week_key
                    else 0
                )
                + (
                    _external_assignment_hours(ctx, agent_name, day)
                    if week_key is None
                    or day_dates[day].isocalendar()[:2] == week_key
                    else 0
                )
                for day in days_to_count
            )
            ctx.model.Add(total_hours <= ctx.max_weekly_hours)


def limit_weekly_nights_and_hours(ctx: SolverContext) -> None:
    """Backward-compatible alias for the weekly worked-hours cap."""
    limit_weekly_worked_hours(ctx)
