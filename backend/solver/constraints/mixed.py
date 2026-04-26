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
    registry.register_mixed(limit_weekly_nights_and_hours)


def limit_weekly_nights_and_hours(ctx: SolverContext) -> None:
    """
    Limits the number of weekly night shifts to 3 and the total weekly hours to 360.

    This constraint is applied per agent and per week in the week's schedule.
    For each agent, it ensures that the agent is not assigned more than 3 night shifts
    per week, and that the total number of hours worked by the agent per week is
    less than or equal to 360.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    for agent in ctx.agents:
        agent_name = agent["name"]

        for week in ctx.weeks_split:
            if NIGHT_SHIFT in ctx.vacations:
                ctx.model.Add(
                    sum(ctx.planning[(agent_name, day, NIGHT_SHIFT)] for day in week) <= 3
                )

            total_heures = sum(
                sum(
                    ctx.planning[(agent_name, day, vacation)] * ctx.shift_durations[vacation]
                    for vacation in (DAY_SHIFT, CDP_SHIFT)
                    if vacation in ctx.vacations
                )
                for day in week
            )
            ctx.model.Add(total_heures <= 360)
