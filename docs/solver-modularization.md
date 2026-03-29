# Solver Modularization Guide

## Overview

The solver is now split from Flask routes to improve maintainability and reduce regression risk.

Runtime entry points:

- API facade: `backend/app.py::generate_planning`
- Solver engine: `backend/solver/engine.py::generate_planning`

## Internal Architecture

Main components:

- `context.py`: shared `SolverContext` containing OR-Tools model, input data, durations, and objective terms.
- `registry.py`: ordered constraint registration and execution (`hard`, `soft`, `mixed`).
- `constraints/hard.py`: mandatory rules.
- `constraints/soft.py`: balancing rules that also produce objective terms.
- `constraints/mixed.py`: mixed rules combining hard/soft intent.
- `objective.py`: objective aggregation and `model.Maximize(...)`.

Execution flow:

1. Build `SolverContext` from API/runtime config.
2. Build planning variables.
3. Register and apply hard constraints.
4. Register and apply soft constraints.
5. Register and apply mixed constraints.
6. Apply objective.
7. Solve and extract result.

## How To Add A Constraint

1. Choose the right group (`hard`, `soft`, `mixed`).
2. Add a function with signature `fn(ctx: SolverContext) -> None` in the corresponding module.
3. Register the function in the module-level `register(...)` function.
4. Add/adjust tests in `backend/tests/`.

Notes:

- Keep function order explicit in `register(...)` to preserve behavior.
- If a new soft constraint contributes to optimization, store its term in `ctx` and integrate it in `objective.py`.
- Keep API and config contracts unchanged unless a dedicated versioned change is planned.

## Test Conventions

Run backend tests with the backend virtual environment:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Recommended coverage for solver changes:

- route compatibility tests (`test_routes.py`)
- behavior constraints (`test_constraints.py`)
- modular structure and critical hard constraints (`test_solver_modularization.py`)
