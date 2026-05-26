# Optimization of Existing Schedule — MVP Technical Spec

## 1) Goal

Add a third planning mode that lets users:

1. Define a date range.
2. Manually fill specific schedule cells (unit-cell granularity).
3. Run optimization to fill only empty cells while preserving manual inputs whenever possible.
4. Receive actionable warnings when manual inputs conflict with constraints.

This mode is intended to complement current generation flows (new generation and continuity generation), not replace them.

---

## 2) Scope (MVP)

### Included

- New UI mode on the home page: **Optimization de l'existant**.
- Manual editing at **single-cell level**.
- Manual entries treated as pre-assignments for solver.
- Empty cells remain solver decision variables.
- Special statuses usable in manual grid:
  - `restriction`
  - `unavailable`
  - `training`
  - `vacations`
- Optimization continues even with manual-input conflicts and returns warnings.
- Minimal correction suggestions returned by backend.
- Optional draft save/load for **manual input only** (no optimization result persistence).

### Explicitly Out of Scope (MVP)

- Advanced versioning/history workflows.
- Agent preference-weight tuning UI.
- Rich bulk editing (copy week, fill range templates).

---

## 3) Functional behavior

## 3.1 Input semantics

For each cell in the planning grid:

- `null` => optimizable by solver.
- Manual shift assignment (e.g. day/night/cdp) => fixed assignment target.
- Manual special status => fixed non-working status handled as existing config constraints.

## 3.2 Priority rules

Priority order for conflict interpretation:

1. **Manual grid input (current session)**
2. Base config constraints from file
3. Soft preferences/objective terms

When manual input contradicts config or hard rules, optimization should not fail immediately; instead:

- attempt solve with controlled conflict handling,
- return warnings with conflict locations and reasons,
- include minimal correction suggestions.

## 3.3 Conflict handling policy

- **Non-blocking conflict:** continue optimization and return warnings.
- **Blocking/unsat conflict:** return explicit unsat result with list of conflicting cells and proposed minimal actions:
  - remove manual assignment,
  - switch to alternative compatible shift,
  - convert to empty for optimization.

---

## 4) Backend API contract (proposed)

## 4.1 Endpoint

`POST /optimize-existing-planning`

## 4.2 Request body

```json
{
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "manual_entries": [
    {
      "agent": "AgentName",
      "date": "YYYY-MM-DD",
      "slot": "day|night|cdp",
      "type": "shift|status",
      "value": "SHIFT_CODE_OR_STATUS"
    }
  ],
  "scope": {
    "agents": ["AgentA", "AgentB"],
    "slots": ["day", "night", "cdp"]
  }
}
```

Notes:

- `scope` is optional in MVP phase 1 (global empty-cell optimization).
- In phase 2, `scope` can restrict optimization to subset (agents and/or slots).

## 4.3 Response body

```json
{
  "status": "ok|warning|unsat",
  "planning": {
    "AgentA": {
      "2026-05-01": {"day": "M", "night": null, "cdp": null}
    }
  },
  "fixed_cells_respected": true,
  "warnings": [
    {
      "code": "MANUAL_CONFLICT",
      "agent": "AgentA",
      "date": "2026-05-02",
      "slot": "night",
      "message": "Manual entry conflicts with minimum rest rule.",
      "source": "hard_constraint"
    }
  ],
  "suggestions": [
    {
      "agent": "AgentA",
      "date": "2026-05-02",
      "slot": "night",
      "action": "clear_cell",
      "reason": "Rest constraint violation"
    }
  ],
  "meta": {
    "optimized_cell_count": 42,
    "manual_cell_count": 18,
    "conflict_count": 1
  }
}
```

---

## 5) Internal backend design adjustments

- Add request parser/validator for manual entries and date range.
- Build pre-assignment map keyed by `(agent, date, slot)`.
- Extend solver context to include fixed cell directives.
- During variable creation:
  - fixed shift cell => restrict variable domain to that assignment,
  - fixed status cell => enforce non-working status per existing constraint logic,
  - empty cell => standard domain.
- Add diagnostics collector to capture rule conflicts and attach warnings/suggestions.

---

## 6) Frontend behavior and components

- Add mode radio option in `App.vue`.
- Reuse `PlanningTable.vue` with editable cell mode enabled.
- Provide per-cell quick actions:
  - set shift,
  - set unavailable/training/vacations/restriction,
  - clear value.
- Add primary action button: `Optimiser le reste`.
- Render warning panel grouped by agent/date.

---

## 7) Validation rules

- Date range required and valid (`start_date <= end_date`).
- Manual entry dates must be inside range.
- Agent names must exist in config.
- Slot values must exist in project slot model.
- Status values limited to supported set.

---

## 8) Test strategy (targeted then global)

## 8.1 Backend targeted tests

1. request validation (bad dates, unknown agent, invalid slot/status),
2. fixed cell respected in feasible case,
3. empty cells optimized while fixed cells preserved,
4. manual conflict returns warning structure,
5. unsat scenario returns `status=unsat` with suggestions.

## 8.2 Frontend targeted tests

1. mode switch renders existing-optimization controls,
2. editable cell writes manual entries payload correctly,
3. optimize call hits new endpoint,
4. warning panel displays grouped conflicts.

## 8.3 Global regression

- Run existing backend + frontend suites unchanged.
- Verify no regression on current generation modes.

---

## 9) Delivery slices

1. **Slice A (mandatory)**
   - Endpoint + fixed-cell semantics + warnings + UI mode + optimize action.
2. **Slice B (if low effort)**
   - Optional optimization scope filters (`agents`, `slots`).
3. **Slice C**
   - Manual draft save/load (local JSON workflow).

