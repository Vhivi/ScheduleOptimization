from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple

from ortools.sat.python import cp_model


@dataclass
class SolverContext:
    """
    SolverContext

    A comprehensive data container for managing the state and configuration of constraint programming models
    used in schedule optimization.

    This class encapsulates all necessary information required by the solver, including model configuration,
    agent information, scheduling constraints, temporal parameters, and optimization objectives.

    Attributes:
        model (cp_model.CpModel): The constraint programming model instance used for solving.
        config (dict): Configuration dictionary containing solver settings and parameters.
        agents (List[dict]): List of agent dictionaries with agent-specific information.
        vacations (List[str]): List of vacation periods or dates.
        week_schedule (List[str]): List of days/shifts defining the current week's schedule.
        day_off (dict): Dictionary mapping agents or days to their off-day information.
        previous_week_schedule (List[str]): Historical schedule from the previous week for continuity.
        initial_shifts (dict): Dictionary containing initial shift assignments before optimization.
        holidays (List[str]): List of public holidays or special non-working dates.
        
        weeks_split (List[List[str]]): Weekly breakdown of the schedule, partitioned into sublists.
        planning (Dict[Tuple[str, str, str], cp_model.IntVar]): Mapping of (agent, day, shift) to CP integer variables.
        leave_paid_hours_by_day (Dict[Tuple[str, str], int]): Paid leave hours indexed by (agent, day).
        
        jour_duration (int): Duration in minutes for day shifts. Default: 0.
        nuit_duration (int): Duration in minutes for night shifts. Default: 0.
        cdp_duration (int): Duration in minutes for CDP shifts. Default: 0.
        conge_duration (int): Duration in minutes for leave/vacation shifts. Default: 0.
        
        max_time_seconds (int): Maximum solver runtime in seconds. Default: 600.
        global_max_gap (int): Global maximum optimality gap in hours * 10. Default: 240.
        period_max_gap (int): Period-specific maximum optimality gap in hours * 10. Default: 240.
        relative_gap_limit (float): Relative optimality gap limit as a fraction. Default: 0.10.
        num_search_workers (int): Number of parallel search workers for the solver. Default: 0.
        optimize_period_balance (bool): Flag to enable period balancing optimization. Default: False.
        period_balance_weight (int): Weight factor for period balancing objectives. Default: 2.
        
        period_balancing_objective (cp_model.LinearExpr | int): Objective expression for balancing workload across periods.
        weekend_balancing_objective (cp_model.LinearExpr | int): Objective expression for balancing weekend assignments.
    """
    model: cp_model.CpModel
    config: dict
    agents: List[dict]
    vacations: List[str]
    week_schedule: List[str]
    day_off: dict
    previous_week_schedule: List[str]
    initial_shifts: dict
    holidays: List[str]
    planning_start_date: datetime | None = None

    weeks_split: List[List[str]] = field(default_factory=list)
    planning: Dict[Tuple[str, str, str], cp_model.IntVar] = field(default_factory=dict)
    leave_paid_hours_by_day: Dict[Tuple[str, str], int] = field(default_factory=dict)
    day_dates: Dict[str, datetime] = field(default_factory=dict)

    jour_duration: int = 0
    nuit_duration: int = 0
    cdp_duration: int = 0
    conge_duration: int = 0

    max_time_seconds: int = 600
    global_max_gap: int = 240
    period_max_gap: int = 240
    relative_gap_limit: float = 0.10
    num_search_workers: int = 0
    optimize_period_balance: bool = False
    period_balance_weight: int = 2

    period_balancing_objective: cp_model.LinearExpr | int = 0
    weekend_balancing_objective: cp_model.LinearExpr | int = 0
