from ortools.sat.python import cp_model

from .catalog import assignment_matches_choice, is_half_assignment
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
            for vacation in ctx.assignable_vacations
            if assignment_matches_choice(ctx, vacation, agent["preferences"]["preferred"])
        )
    )

    objective_other_vacations = cp_model.LinearExpr.Sum(
        list(
            ctx.planning[(agent["name"], day, vacation)] * weight_other
            for agent in ctx.agents
            for day in ctx.week_schedule
            for vacation in ctx.assignable_vacations
            if not assignment_matches_choice(ctx, vacation, agent["preferences"]["preferred"])
        )
    )

    penalized_vacations = cp_model.LinearExpr.Sum(
        list(
            ctx.planning[(agent["name"], day, vacation)] * weight_avoid
            for agent in ctx.agents
            for day in ctx.week_schedule
            for vacation in ctx.assignable_vacations
            if assignment_matches_choice(ctx, vacation, agent["preferences"]["avoid"])
        )
    )

    half_vacation_penalties = cp_model.LinearExpr.Sum(
        list(
            ctx.planning[(agent["name"], day, vacation)]
            * ctx.assignment_metadata[vacation].penalty
            for agent in ctx.agents
            for day in ctx.week_schedule
            for vacation in ctx.assignable_vacations
            if is_half_assignment(ctx, vacation)
        )
    )

    agent_usage_bonus_weight = 5
    agent_usage_bonus_terms = []
    for agent in ctx.agents:
        agent_name = agent["name"]
        is_used = ctx.model.NewBoolVar(f"{agent_name}_used_at_least_once")
        worked_assignments = [
            ctx.planning[(agent_name, day, vacation)]
            for day in ctx.week_schedule
            for vacation in ctx.assignable_vacations
        ]
        ctx.model.Add(sum(worked_assignments) >= 1).OnlyEnforceIf(is_used)
        ctx.model.Add(sum(worked_assignments) == 0).OnlyEnforceIf(is_used.Not())
        agent_usage_bonus_terms.append(is_used * agent_usage_bonus_weight)

    preserve_existing_weight = 10000
    change_existing_full_penalty = 1000
    change_existing_half_penalty = 2000
    preserve_existing_assignments = []
    change_existing_assignments = []
    known_agents = {agent["name"] for agent in ctx.agents}
    for (agent_name, day), existing_vacation in (ctx.existing_assignments or {}).items():
        if (
            agent_name not in known_agents
            or day not in ctx.week_schedule
            or existing_vacation not in ctx.assignable_vacations
        ):
            continue
        for vacation in ctx.assignable_vacations:
            variable = ctx.planning[(agent_name, day, vacation)]
            if vacation == existing_vacation:
                preserve_existing_assignments.append(variable * preserve_existing_weight)
            else:
                penalty = (
                    change_existing_half_penalty
                    if is_half_assignment(ctx, vacation)
                    else change_existing_full_penalty
                )
                change_existing_assignments.append(variable * penalty)

    objective = (
        objective_preferred_vacations
        + objective_other_vacations
        + penalized_vacations
        + cp_model.LinearExpr.Sum(agent_usage_bonus_terms)
        + cp_model.LinearExpr.Sum(preserve_existing_assignments)
        - half_vacation_penalties
        - cp_model.LinearExpr.Sum(change_existing_assignments)
        - ctx.weekend_balancing_objective
    )
    if ctx.optimize_period_balance:
        objective -= ctx.period_balance_weight * ctx.period_balancing_objective

    ctx.model.Maximize(objective)
