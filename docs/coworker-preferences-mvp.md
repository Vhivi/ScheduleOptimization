# Coworker Preferences — MVP Technical Spec

## 1) Goal

Allow each agent to express how much they want to work with another agent.
The solver uses these ratings as a soft preference: hard constraints, staffing,
availability, rest rules, and working-hour limits always remain authoritative.

This document describes the MVP implemented on `feat/coworker-preferences`.
For the complete configuration reference, see `docs/config-reference.md`.

## 2) MVP scope

### Included

- Per-agent coworker ratings configured in JSON.
- Integer ratings from `-2` (strongly avoid) to `2` (strongly prefer).
- A configurable global objective weight, defaulting to `50`.
- Positive rewards requiring mutual positive ratings.
- Negative ratings applying even when they are unilateral.
- Pairing counted only when both agents have the exact same assignment on the
  same day.
- Validation of scores, agent references, self-references, and duplicate agent
  names.
- Backward compatibility with configurations that omit the new fields.

### Out of scope

- Frontend entry or visualization.
- Per-pair weights or different rating scales.
- Pairing based on overlapping hours or compatible assignments.
- Explanations of coworker preference effects in API responses.
- Making coworker preferences hard constraints.

## 3) Configuration contract

Coworker ratings are optional and live under the existing agent preferences:

```json
{
  "agents": [
    {
      "name": "Agent1",
      "preferences": {
        "preferred": ["Jour"],
        "avoid": ["Nuit"],
        "coworkers": {
          "Agent2": 2,
          "Agent3": -1
        }
      }
    },
    {
      "name": "Agent2",
      "preferences": {
        "preferred": ["Jour"],
        "avoid": [],
        "coworkers": {
          "Agent1": 1
        }
      }
    }
  ],
  "solver": {
    "coworker_preference_weight": 50
  }
}
```

- `agents[].preferences.coworkers` is optional and defaults to `{}`.
- Keys must be the exact name of another configured agent.
- Values must be integers from `-2` to `2`; storing `0` is equivalent to
  omitting the entry.
- `solver.coworker_preference_weight` is an optional integer greater than or
  equal to `0`; `0` disables the feature without removing ratings.

## 4) Scoring behavior

Each unordered pair is evaluated once. For ratings `A → B` and `B → A`:

1. If both ratings are positive, their sum is rewarded.
2. Positive unilateral ratings contribute `0`.
3. Every negative rating contributes to the penalty.
4. The resulting pair score is multiplied by the global weight for each exact
   assignment shared on the same day.

With the default weight of `50`:

| A → B | B → A | Pair score | Objective effect per shared assignment |
| ---: | ---: | ---: | ---: |
| 2 | 2 | 4 | +200 |
| 2 | 1 | 3 | +150 |
| 2 | 0 | 0 | 0 |
| 2 | -1 | -1 | -50 |
| 0 | -2 | -2 | -100 |
| -2 | -1 | -3 | -150 |

`Jour` and `Nuit` on the same date do not count as working together. Likewise,
two different half-vacation segments do not match. A negative score never makes
a schedule infeasible when the agents must work together.

## 5) Solver integration

- The soft-constraint registry builds one Boolean conjunction per active pair,
  planning day, and assignable vacation.
- Pairs with a neutral effective score create no additional solver variables.
- A global weight of `0` skips the feature entirely.
- The resulting linear expression is added to the existing maximization
  objective alongside shift preferences and other soft terms.

## 6) Validation and acceptance criteria

Configuration is rejected when:

- a rating is not an integer in `[-2, 2]`;
- a coworker name does not exist;
- an agent references itself;
- two agents have the same name;
- the global weight is negative or not an integer.

The MVP is accepted when automated tests confirm that:

1. legacy configurations without coworker settings remain valid;
2. mutual positive ratings favor a shared assignment when an alternative exists;
3. unilateral positive ratings produce no reward;
4. unilateral negative ratings avoid a shared assignment when possible;
5. negative ratings remain soft when pairing is required;
6. different assignments on the same day do not count;
7. schema and cross-agent validation reject invalid inputs.

Run the backend regression suite from `backend` after activating the virtual
environment:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

## 7) Possible follow-up

Add a frontend editor only after JSON configuration proves insufficient in real
use. The smallest useful UI would reuse native numeric inputs and the existing
agent configuration screen; richer matrices, privacy rules, and preference
explanations should remain separate requirements.
