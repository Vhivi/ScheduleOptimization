from dataclasses import dataclass, field
from typing import Callable, List

from .context import SolverContext

ConstraintFn = Callable[[SolverContext], None]


@dataclass
class ConstraintRegistry:
    """
    Registry for managing and applying different types of constraints in the solver.

    This class provides a centralized mechanism to register and apply constraints
    categorized by their type: hard constraints, soft constraints, and mixed constraints.

    Hard constraints are mandatory requirements that must be satisfied.
    Soft constraints are optional preferences that should be satisfied when possible.
    Mixed constraints are constraints that combine aspects of both hard and soft constraints.

    Attributes:
        hard (List[ConstraintFn]): List of hard constraint functions.
        soft (List[ConstraintFn]): List of soft constraint functions.
        mixed (List[ConstraintFn]): List of mixed constraint functions.

    Methods:
        register_hard: Register a new hard constraint function.
        register_soft: Register a new soft constraint function.
        register_mixed: Register a new mixed constraint function.
        apply_hard: Apply all registered hard constraints to a solver context.
        apply_soft: Apply all registered soft constraints to a solver context.
        apply_mixed: Apply all registered mixed constraints to a solver context.
    """
    hard: List[ConstraintFn] = field(default_factory=list)
    soft: List[ConstraintFn] = field(default_factory=list)
    mixed: List[ConstraintFn] = field(default_factory=list)

    def register_hard(self, fn: ConstraintFn) -> None:
        self.hard.append(fn)

    def register_soft(self, fn: ConstraintFn) -> None:
        self.soft.append(fn)

    def register_mixed(self, fn: ConstraintFn) -> None:
        self.mixed.append(fn)

    def apply_hard(self, ctx: SolverContext) -> None:
        for constraint in self.hard:
            constraint(ctx)

    def apply_soft(self, ctx: SolverContext) -> None:
        for constraint in self.soft:
            constraint(ctx)

    def apply_mixed(self, ctx: SolverContext) -> None:
        for constraint in self.mixed:
            constraint(ctx)
