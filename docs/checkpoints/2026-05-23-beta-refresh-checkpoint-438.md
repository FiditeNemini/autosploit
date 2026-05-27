# Beta Refresh Checkpoint 438

## Goal

Add a tab action surface matrix so every per-tab action surface has row-level
tab, route, action-state, function-matrix, and proof ownership.

## Changes

- Added `scripts/tab-action-surface-matrix-proof.py`.
- Added `/qa/tab-action-surface-matrix`.
- Added `/qa/tab-action-surface-matrix` to `/state.qaCoverage.stateRoutes`.
- Added one row per `/qa/tab-action-coverage.tabActionSurfaces` item with tab
  owners, route owners, action-state key owners, proof owners,
  `/qa/action-state-inventory`, and `/qa/function-proof-matrix` linkage.
- Mirrored `tabActionSurfaceMatrixCount`,
  `tabActionSurfaceMatrixProofOwnerFileParity`,
  `tabActionSurfaceMatrixProofFileParity`, and
  `tabActionSurfaceMatrixActionStateCount` into
  `/qa/coverage-index.groups.tabsAndSessions`.
- Updated coverage-index and app matrix proofs to require the new tab action
  surface matrix route and mirrors.
- Updated the system review and flow inventory docs with the tab action
  surface matrix contract.

## Proof

- `python3 scripts/tab-action-surface-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/tab-action-surface-matrix` did not exist. The
green path keeps every tab action surface tied to tabs, routes, action-state
keys, proof-owner files, function proof ownership, docs, and coverage-index
mirrors.
