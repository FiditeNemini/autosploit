# Beta Refresh Checkpoint 437

## Goal

Add a session workflow matrix so every cross-app workflow surface has row-level
route, state-key, tab-action, and agent-loop phase ownership.

## Changes

- Added `scripts/session-workflow-matrix-proof.py`.
- Added `/qa/session-workflow-matrix`.
- Added `/qa/session-workflow-matrix` to `/state.qaCoverage.stateRoutes`.
- Added one row per `/qa/session-coverage.sessionWorkflowSurfaces` item with
  proof owners, route owners, state-key owners, `/qa/session-coverage`,
  `/qa/tab-action-coverage`, and `/qa/agent-loop-phase-matrix` linkage.
- Mirrored `sessionWorkflowMatrixCount`,
  `sessionWorkflowMatrixProofOwnerFileParity`,
  `sessionWorkflowMatrixProofFileParity`, and
  `sessionWorkflowMatrixTabActionRouteCount` into
  `/qa/coverage-index.groups.tabsAndSessions`.
- Updated coverage-index and app matrix proofs to require the new session
  workflow matrix route and mirrors.
- Updated the system review and flow inventory docs with the session workflow
  matrix contract.

## Proof

- `python3 scripts/session-workflow-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/session-workflow-matrix` did not exist. The
green path keeps every session workflow tied to routes, state keys, proof-owner
files, tab-action coverage, agent-loop phase coverage, docs, and coverage-index
mirrors.
