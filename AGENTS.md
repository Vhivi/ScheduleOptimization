# Repository Guidelines

## Project Structure & Module Organization

The Flask API lives in `backend/app.py`. Scheduling logic is split across `backend/solver/`, with constraints grouped in `solver/constraints/{hard,soft,mixed}.py`. Runtime configuration is validated by `backend/config.schema.json`; use `config.example.json` as the committed template. Backend tests are in `backend/tests/`.

The Vue 3 client lives in `frontend/src/`: reusable UI belongs in `components/`, API calls in `apiClient.js`, and static images in `assets/`. Jest tests live in `frontend/tests/`. Architecture and configuration details are documented in `ARCHITECTURE.md` and `docs/`.

## Build, Test, and Development Commands

Backend development uses `backend/.venv`. Before Python commands, check that it exists, create it only if missing (`python -m venv backend/.venv`), then activate it from `backend` with `.\.venv\Scripts\Activate.ps1` (Windows) or `source .venv/bin/activate` (Unix).

- `pip install -r backend/requirements.txt` installs Python dependencies.
- `cd backend; python -m pytest -q` runs the backend suite.
- `cd backend; flask run` serves the API at `http://127.0.0.1:5000`.
- `cd frontend; npm install` installs locked frontend dependencies.
- `cd frontend; npm run serve` starts the development server with hot reload.
- `cd frontend; npm test -- --runInBand` runs Jest tests once, serially.
- `cd frontend; npm run lint` checks JavaScript and Vue files with ESLint.
- `cd frontend; npm run build` creates the production bundle.

## Coding Style & Naming Conventions

Follow existing code: four-space indentation and `snake_case` for Python; two-space indentation, semicolons, and `camelCase` for JavaScript. Name Vue components in `PascalCase` (for example, `PlanningTable.vue`). Keep solver rules in the appropriate constraint module and register new rules through its existing `register(...)` function. Prefer small changes that reuse current helpers.

## Testing Guidelines

Use pytest for backend changes and Jest with Vue Test Utils for frontend changes. Name Python files `test_*.py` and frontend specs `*.spec.js`. Add a focused regression test for bug fixes and cover both valid and rejected configuration inputs when changing validation. No numeric coverage threshold is enforced; all affected suites must pass.

## Commit & Pull Request Guidelines

History follows Conventional Commit-style subjects such as `fix(constraints): ...`, `test(rest): ...`, and `docs(config-reference): ...`. Keep commits scoped and imperative. Pull requests should explain the problem and solution, link relevant issues, list verification commands, and include screenshots for visible UI changes. Update `CHANGELOG.md` under `Unreleased` when behavior or dependencies change.

## Configuration & Security

Copy `backend/config.example.json` to ignored `backend/config.json`; never commit real personnel data or secrets. Keep schema, example configuration, and `docs/config-reference.md` synchronized.
