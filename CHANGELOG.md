# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.0] - 2026-05-01

### Added

- Added runtime configuration API endpoints in the backend: `GET /config`, `GET /config/default`, and `PUT /config`.
- Added schema-backed config persistence flow with atomic writes and immediate in-memory reload.
- Added frontend interactive configuration mode in `App.vue` with load/save/default actions and inline editing for agents, vacations, durations, and staffing quotas.
- Added backend dynamic solver tests in `backend/tests/test_dynamic_solver_config.py` for custom vacations and multi-agent-per-shift scenarios.

### Changed

- Updated solver internals to support dynamic vacation names instead of hard-coded `Jour/Nuit/CDP` assumptions.
- Added `staffing_requirements` support to drive simultaneous staffing counts per vacation and per day.
- Updated config schema to allow dynamic vacation names and dynamic vacation duration keys while keeping `Conge` mandatory.
- Updated generation flow so frontend auto-saves dirty config before planning generation.

### Fixed

- Fixed frontend generation flow regression where auto-save could stop generation before calling `/generate-planning`.

## [0.8.0] - 2026-04-25

### Added

- Added a modular backend solver package under `backend/solver/` with dedicated context, registry, grouped constraints, and objective builder.
- Added a solver modularization guide at `docs/solver-modularization.md`.
- Added backend tests in `backend/tests/test_solver_modularization.py` to validate registry wiring and key hard-constraint behavior.

### Changed

- Refactored `backend/app.py` so API routes keep a stable `generate_planning(...)` facade while solver logic is delegated to `backend/solver/engine.py`.
- Preserved API and configuration compatibility while splitting hard/soft/mixed constraints into dedicated modules.

### Fixed

- Fixed leave-year handling in the solver so leave periods are matched against full planning dates, preventing `dd-mm` collisions across years (for example 2025 leave affecting 2026 planning).
- Fixed backend leave helper behavior to support year-safe date resolution with a planning start-date reference.
- Fixed frontend leave rendering in `PlanningTable` to use full-date matching and correctly display `Con.` on weekend days included in leave periods.
- Fixed frontend unavailable/training day matching in `PlanningTable` to use full dates consistently with backend config (`dd-mm-YYYY`).

## [0.7.9] - 2026-03-22

### Added

- Added frontend API client utility with centralized base URL support through `VUE_APP_API_BASE_URL`.
- Added frontend tests for API error normalization and year-boundary leave rendering in `PlanningTable`.
- Added backend route tests for invalid/missing JSON payloads and invalid date ranges.

### Changed

- Hardened backend route payload validation (`/generate-planning`, `/previous-week-schedule`) with defensive JSON/object checks.
- Reworked backend day label formatting to be locale-independent across platforms.
- Improved frontend generation UX with explicit loading state and safer error handling for transport/API failures.

### Removed

- Removed `frontend/src/components/ConfigComponent.vue` debug component from the main application flow.

## [0.7.8] - 2026-03-15

### Changed

- Made `backend/config.json` a local-only file by ignoring it in Git and removing it from version control tracking.
- Added explicit backend startup/config loading guidance: copy `backend/config.example.json` to `backend/config.json`.
- Updated backend CI to create `backend/config.json` from the example before running tests.

### Fixed

- Updated `test_generate_planning_route_valid_data` to use a date range that is feasible with `backend/config.example.json`, preventing CI failures caused by solver infeasibility.

## [0.7.7] - 2026-03-15

### Added

- Added a dedicated English configuration reference (`docs/config-reference.md`).
- Added `backend/config.schema.json` and `backend/config.example.json` for user-friendly configuration and machine validation.
- Added backend schema validation tests to ensure `config.json` and the example file remain valid.

### Changed

- Updated the README configuration section to point to the new reference, schema, and example files.
- Added `jsonschema` to backend dependencies for automated config validation tests.

## [0.7.6] - 2026-03-15

### Fixed

- Resolved a planning infeasibility regression where global hour balancing was accidentally constrained against leave-only constants instead of total paid hours.
- Updated balancing logic to use paid hours consistently (worked shifts plus paid leave) and enforce per-period balance with a configurable capped gap.
- Improved generation performance for continuity-heavy monthly chunks by adding configurable solver stop criteria (`relative_gap_limit`) while keeping the existing time limit.
- Added a backend regression test to ensure planning generation remains feasible with asymmetric paid-leave distributions.

## [0.7.5] - 2026-03-13

### Changed

- Reclassified frontend test tooling packages (`jest`, `jest-environment-jsdom`, `babel-jest`, `@vue/test-utils`, `@vue/vue3-jest`, `jest-serializer-vue`) from runtime dependencies to `devDependencies`.

### Security

- Resolved the remaining frontend runtime audit findings; `npm audit --omit=dev` now reports no vulnerabilities.

## [0.7.4] - 2026-03-13

### Changed

- Documented backend virtual environment setup and a reproducible pytest baseline run using Python 3.10.
- Updated backend dependencies to current compatible releases for Flask, Flask-Cors, and pytest.
- Updated frontend dependencies with non-breaking releases for Vue, core-js, and Babel tooling.
- Extended CI to run frontend tests and upgraded GitHub Action `setup-python` to v5.
- Expanded project documentation with dedicated testing instructions and a maintenance policy.

### Security

- Applied npm audit non-breaking fixes; 4 low-severity frontend vulnerabilities remain and require breaking upgrades (Jest/jsdom stack) for full remediation.

## [0.7.3] - 2026-03-12

### Fixed

- Refreshed frontend npm dependencies and lockfile to address known vulnerable packages.
- Updated frontend tests so the `PlanningTable` suite matches the current component props and linting setup.

## [0.7.2] - 2025-05-27

### Changed

- Expanded the project documentation with a dedicated architecture guide and clearer installation guidance.
- Updated key runtime dependencies for the frontend and backend environment, including Vue, Axios, and Flask-Cors.

### Fixed

- Corrected planning generation across long date ranges by splitting requests into monthly periods and chaining continuity data between periods.

## [0.7.0] - 2025-03-19

### Added

- Support for multiple leave periods per agent in the configuration and scheduling pipeline.
- Improved leave handling around unavailable days before time off.

### Changed

- Updated the leave data model used by the backend, frontend display, and tests.
- Improved solver feedback during planning generation with additional status logging.

### Fixed

- Corrected planning behavior for leave-heavy scenarios and adjusted related test data.

## [0.6.0] - 2025-02-08

### Added

- Continuity mode in the UI to seed a new planning run with shifts from the previous week.
- Backend support for validating and applying `initial_shifts` in `/generate-planning`.
- `/previous-week-schedule` API route to compute and return the transition week used by the frontend.

### Changed

- Improved the planning interface with a dedicated transition table and clearer visual feedback for selected shifts and weekends.
- Strengthened automated test coverage for route validation and previous-week scheduling behavior.

### Fixed

- Improved date validation and error reporting when schedule generation receives invalid or incomplete input.
- Added clearer handling for cases where the solver cannot produce a valid planning.

## [0.5.0] - 2025-01-16

### Added

- Hard restriction support for agent-specific shift exclusions and scheduling rules.
- Backend test setup, frontend test setup, and CI workflow for automated backend validation.

### Changed

- Reworked constraint organization to better separate hard, soft, and mixed scheduling rules.
- Clarified project setup, prerequisites, and usage documentation.

### Fixed

- Corrected holiday handling errors and invalid calendar date handling during schedule generation.
- Improved configuration path handling and general request validation in the backend.

## [0.4.0] - 2024-11-18

### Added

- Training-day management in the backend and frontend, including visual display in the planning table.
- Monthly schedule splitting and per-period totals for generated plannings.
- Additional fairness constraints for complete weekends, hour balancing by period, and restrictions around training days.
- Agent-specific exclusion rules for shifts and support for the `Conge` leave type.

### Changed

- Extended the optimization model to better balance weekends and worked hours across agents.

### Fixed

- Prevented Monday night shifts after weekend work and tightened night-shift rules before unavailable days.

## [0.3.0] - 2024-10-29

### Added

- Vacation and day-off management in the backend response and frontend display.
- Constraints for agent unavailability, leave periods, weekly day-shift caps, minimum night grouping, and weekly CDP limits.
- Holiday-aware scheduling rules, including holiday exclusion for CDP assignments.

### Changed

- Updated the configuration model to carry holiday lists, unavailable dates, and leave periods.
- Improved the planning table to highlight weekends, holidays, and leave cells more clearly.

### Fixed

- Standardized day and holiday date formats so backend generation and frontend display use the same schedule keys.

## [0.2.0] - 2024-10-23

### Added

- Optimization constraints for minimum rest, weekly hour limits, workload balancing, and preferred shift maximization.
- Dynamic planning generation from start and end dates instead of a fixed precomputed week.
- Frontend schedule rendering with per-shift colors and generated planning display.

### Changed

- Moved schedule inputs into `config.json`, including agents, preferences, shift definitions, and scheduling parameters.
- Refined the optimization objective to reward preferred shifts and penalize undesired ones.

### Fixed

- Corrected agent preference handling and shift assignment rules so each shift is assigned consistently.

## [0.1.0] - 2024-10-11

### Added

- Initial Flask backend and Vue frontend setup for the Schedule Optimization project.
- First REST API flow between frontend and backend for requesting generated plannings.
- Initial OR-Tools integration and schedule generation endpoint.
- Base project documentation and repository setup.
