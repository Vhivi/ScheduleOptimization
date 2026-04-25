from ortools.sat.python import cp_model

from .context import SolverContext


def apply_objective(ctx: SolverContext) -> None:
    """
    Applies the objective function to the model.

    The objective function is composed of three parts: the preferred vacations, the other vacations, and the penalized vacations.
    The preferred vacations are given a positive weight, the other vacations are given a unit weight, and the penalized vacations are given a negative weight.
    The objective is to maximize the sum of the preferred vacations and the other vacations, and to minimize the sum of the penalized vacations.
    If the period balance is optimized, the period balancing objective is subtracted from the main objective.
    """
    weight_preferred = 100
    weight_other = 1
    weight_avoid = -250

    objective_preferred_vacations = cp_model.LinearExpr.Sum(
        list(
            ctx.planning[(agent["name"], day, vacation)] * weight_preferred
            for agent in ctx.agents
            for day in ctx.week_schedule
            for vacation in ctx.vacations
            if vacation in agent["preferences"]["preferred"]
        )
    )

    objective_other_vacations = cp_model.LinearExpr.Sum(
        list(
            ctx.planning[(agent["name"], day, vacation)] * weight_other
            for agent in ctx.agents
            for day in ctx.week_schedule
            for vacation in ctx.vacations
            if vacation not in agent["preferences"]["preferred"]
        )
    )

    penalized_vacations = cp_model.LinearExpr.Sum(
        list(
            ctx.planning[(agent["name"], day, vacation)] * weight_avoid
            for agent in ctx.agents
            for day in ctx.week_schedule
            for vacation in ctx.vacations
            if vacation in agent["preferences"]["avoid"]
        )
    )

    objective = (
        objective_preferred_vacations
        + objective_other_vacations
        + penalized_vacations
        - ctx.weekend_balancing_objective
    )
    if ctx.optimize_period_balance:
        objective -= ctx.period_balance_weight * ctx.period_balancing_objective

    ctx.model.Maximize(objective)
