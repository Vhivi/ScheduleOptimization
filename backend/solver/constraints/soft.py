from ortools.sat.python import cp_model

from ..context import SolverContext
from ..registry import ConstraintRegistry
from ..utils import split_by_month_or_period


def register(registry: ConstraintRegistry) -> None:
    """
    Registers the soft constraints for the solver.

    The registered constraints are:
    - balance_paid_hours: Balances paid hours across all agents in the week's schedule.
    - balance_paid_hours_by_period: Balances paid hours across all agents in each period of the week's schedule.
    - balance_full_weekends: Balances full weekends across all agents in the week's schedule.

    :param registry: The constraint registry to which the constraints are registered.
    :type registry: ConstraintRegistry
    """
    registry.register_soft(balance_paid_hours)
    registry.register_soft(balance_paid_hours_by_period)
    registry.register_soft(balance_full_weekends)


def balance_paid_hours(ctx: SolverContext) -> None:
    """
    Balances paid hours across all agents in the week's schedule.

    This constraint ensures that the difference between the maximum and minimum paid hours
    across all agents is less than or equal to the global maximum gap.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    paid_hours = {}
    for agent in ctx.agents:
        agent_name = agent["name"]
        paid_hours[agent_name] = cp_model.LinearExpr.Sum(
            list(
                ctx.planning[(agent_name, day, "Jour")] * ctx.jour_duration
                + ctx.planning[(agent_name, day, "Nuit")] * ctx.nuit_duration
                + ctx.planning[(agent_name, day, "CDP")] * ctx.cdp_duration
                + ctx.leave_paid_hours_by_day[(agent_name, day)]
                for day in ctx.week_schedule
            )
        )

    min_hours = ctx.model.NewIntVar(0, 10000, "min_hours")
    max_hours = ctx.model.NewIntVar(0, 10000, "max_hours")

    for agent_name in paid_hours:
        ctx.model.Add(min_hours <= paid_hours[agent_name])
        ctx.model.Add(paid_hours[agent_name] <= max_hours)

    ctx.model.Add(max_hours - min_hours <= ctx.global_max_gap)


def balance_paid_hours_by_period(ctx: SolverContext) -> None:
    """
    Balances paid hours across different periods of the week's schedule.

    This constraint is applied by splitting the week's schedule into periods (either months or periods).
    For each period, it ensures that the difference between the maximum and minimum paid hours
    across all agents is less than or equal to the period's maximum gap.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    periods = split_by_month_or_period(ctx.week_schedule)

    period_balancing_terms = []
    for period_idx, period in enumerate(periods):
        period_total_hours = {}
        for agent in ctx.agents:
            agent_name = agent["name"]
            period_total_hours[agent_name] = cp_model.LinearExpr.Sum(
                list(
                    ctx.planning[(agent_name, day, "Jour")] * ctx.jour_duration
                    + ctx.planning[(agent_name, day, "Nuit")] * ctx.nuit_duration
                    + ctx.planning[(agent_name, day, "CDP")] * ctx.cdp_duration
                    + ctx.leave_paid_hours_by_day[(agent_name, day)]
                    for day in period
                )
            )

        min_period_hours = ctx.model.NewIntVar(0, 100000, f"min_hours_period_{period_idx}")
        max_period_hours = ctx.model.NewIntVar(0, 100000, f"max_hours_period_{period_idx}")
        for agent in ctx.agents:
            agent_name = agent["name"]
            ctx.model.Add(min_period_hours <= period_total_hours[agent_name])
            ctx.model.Add(period_total_hours[agent_name] <= max_period_hours)

        period_gap = ctx.model.NewIntVar(0, 100000, f"period_gap_{period_idx}")
        ctx.model.Add(period_gap == max_period_hours - min_period_hours)
        ctx.model.Add(period_gap <= ctx.period_max_gap)
        period_balancing_terms.append(period_gap)

    ctx.period_balancing_objective = cp_model.LinearExpr.Sum(period_balancing_terms)


def balance_full_weekends(ctx: SolverContext) -> None:
    """
    Balances full weekends (Saturday and Sunday) among agents.

    For each pair of Saturday and Sunday, adds a boolean variable to indicate if the
    agent works on that weekend. Adds constraints to ensure that the variable is
    only true if the agent works on both Saturday and Sunday.

    For each agent, adds a integer variable to count the number of weekends the agent
    works. Adds constraints to ensure that the variable is equal to the sum of the
    boolean variables representing the agent's work on each weekend.

    Adds a minimization objective to minimize the difference between the maximum and
    minimum number of weekends worked by all agents. Adds a quadratic objective to
    minimize the squared difference between the number of weekends worked by each agent
    and the target number of weekends per agent.

    :param ctx: The solver context containing the problem data and the model.
    :type ctx: SolverContext
    """
    total_weekends = sum(1 for day in ctx.week_schedule if "Sam" in day)
    target_weekends_per_agent = (total_weekends * 2) // len(ctx.agents)

    weekends_worked = {}
    for agent in ctx.agents:
        agent_name = agent["name"]
        weekends_worked[agent_name] = ctx.model.NewIntVar(
            0, total_weekends, f"weekends_worked_{agent_name}"
        )

        weekend_count = []
        for day_idx, day in enumerate(ctx.week_schedule):
            if (
                "Sam" in day
                and day_idx + 1 < len(ctx.week_schedule)
                and "Dim" in ctx.week_schedule[day_idx + 1]
            ):
                saturday = day
                sunday = ctx.week_schedule[day_idx + 1]

                saturday_work = ctx.model.NewBoolVar(f"{agent_name}_works_saturday_{saturday}")
                sunday_work = ctx.model.NewBoolVar(f"{agent_name}_works_sunday_{sunday}")

                ctx.model.Add(
                    ctx.planning[(agent_name, saturday, "Jour")]
                    + ctx.planning[(agent_name, saturday, "Nuit")]
                    > 0
                ).OnlyEnforceIf(saturday_work)
                ctx.model.Add(
                    ctx.planning[(agent_name, saturday, "Jour")]
                    + ctx.planning[(agent_name, saturday, "Nuit")]
                    == 0
                ).OnlyEnforceIf(saturday_work.Not())

                ctx.model.Add(
                    ctx.planning[(agent_name, sunday, "Jour")]
                    + ctx.planning[(agent_name, sunday, "Nuit")]
                    > 0
                ).OnlyEnforceIf(sunday_work)
                ctx.model.Add(
                    ctx.planning[(agent_name, sunday, "Jour")]
                    + ctx.planning[(agent_name, sunday, "Nuit")]
                    == 0
                ).OnlyEnforceIf(sunday_work.Not())

                works_weekend = ctx.model.NewBoolVar(
                    f"{agent_name}_works_weekend_{saturday}_{sunday}"
                )
                ctx.model.AddBoolAnd([saturday_work, sunday_work]).OnlyEnforceIf(works_weekend)
                ctx.model.AddBoolOr([saturday_work.Not(), sunday_work.Not()]).OnlyEnforceIf(
                    works_weekend.Not()
                )
                weekend_count.append(works_weekend)

        ctx.model.Add(weekends_worked[agent_name] == sum(weekend_count))

    min_weekends = ctx.model.NewIntVar(0, total_weekends, "min_weekends")
    max_weekends = ctx.model.NewIntVar(0, total_weekends, "max_weekends")
    for agent_name in weekends_worked:
        ctx.model.Add(min_weekends <= weekends_worked[agent_name])
        ctx.model.Add(weekends_worked[agent_name] <= max_weekends)

    ctx.model.Minimize(max_weekends - min_weekends)

    weekend_balancing_terms = []
    for agent in ctx.agents:
        agent_name = agent["name"]
        difference = ctx.model.NewIntVar(
            -2 * total_weekends, 2 * total_weekends, f"difference_weekends_{agent_name}"
        )
        squared_difference = ctx.model.NewIntVar(
            0, (total_weekends * 2) ** 2, f"squared_difference_weekends_{agent_name}"
        )

        ctx.model.Add(difference == weekends_worked[agent_name] - target_weekends_per_agent)
        ctx.model.AddMultiplicationEquality(squared_difference, [difference, difference])
        weekend_balancing_terms.append(squared_difference)

    ctx.weekend_balancing_objective = cp_model.LinearExpr.Sum(weekend_balancing_terms)
