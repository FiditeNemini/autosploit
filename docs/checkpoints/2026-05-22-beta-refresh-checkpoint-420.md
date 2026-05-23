# Beta Refresh Checkpoint 420

## Goal

Expose a source-owned action-state inventory so every visible app action state
is grouped, documented, mirrored into coverage, and tied to a proof owner.

## Changes

- Added `scripts/action-state-inventory-proof.py`.
- Added `/qa/action-state-inventory`.
- Added `/qa/action-state-inventory` to `/state.qaCoverage.stateRoutes`.
- Added source parsing for `*ActionState` structs, AppState action fields,
  action snapshot helpers, `record*Action` functions, and action QA routes.
- Mirrored action-state counts, groups, and proof-file parity into
  `/qa/coverage-index.groups.appState`.
- Updated coverage-index and app matrix proofs to require the action-state
  inventory endpoint and mirror.
- Updated the system review and flow inventory docs with the action-state
  inventory contract.

## Proof

- `python3 scripts/action-state-inventory-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/action-state-inventory` did not exist. The
green path keeps `AppState.swift` as the authority and uses coverage-index only
as the mirror, so future tab/tool/control action additions must appear in the
source-derived inventory.
