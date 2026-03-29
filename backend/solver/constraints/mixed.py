from ..context import SolverContext
from ..registry import ConstraintRegistry


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
            ctx.model.Add(sum(ctx.planning[(agent_name, day, "Nuit")] for day in week) <= 3)

            total_heures = sum(
                ctx.planning[(agent_name, day, "Jour")] * ctx.jour_duration
                + ctx.planning[(agent_name, day, "CDP")] * ctx.cdp_duration
                for day in week
            )
            ctx.model.Add(total_heures <= 360)
