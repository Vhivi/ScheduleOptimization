from ..context import SolverContext
from ..registry import ConstraintRegistry

DAY_SHIFT = "Jour"
NIGHT_SHIFT = "Nuit"
CDP_SHIFT = "CDP"


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
    for agent in ctx.agents:
        agent_name = agent["name"]

        for week in ctx.weeks_split:
            assignable_vacations = getattr(ctx, "assignable_vacations", None) or ctx.vacations
            total_hours = sum(
                sum(
                    ctx.planning[(agent_name, day, vacation)] * ctx.shift_durations[vacation]
                    for vacation in assignable_vacations
                )
                for day in week
            )
            ctx.model.Add(total_hours <= ctx.max_weekly_hours)


def limit_weekly_nights_and_hours(ctx: SolverContext) -> None:
    """Backward-compatible alias for the weekly worked-hours cap."""
    limit_weekly_worked_hours(ctx)
