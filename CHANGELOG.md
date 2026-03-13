# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Documented backend virtual environment setup and a reproducible pytest baseline run using Python 3.10.

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
