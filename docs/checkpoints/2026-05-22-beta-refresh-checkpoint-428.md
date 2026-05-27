# Beta Refresh Checkpoint 428

## Goal

Expose a source-owned Swift function-flow inventory so individual AppState
helpers, QA snapshots, service functions, view callbacks, and agent-loop
functions are parsed, grouped, mirrored into coverage, documented, and tied to
proof-file parity.

## Changes

- Added `scripts/function-flow-inventory-proof.py`.
- Added `/qa/function-flow-inventory`.
- Added `/qa/function-flow-inventory` to `/state.qaCoverage.stateRoutes`.
- Added source parsing for Swift function declarations under
  `ExploitBot/Sources/ExploitBot/App`, `Models`, `Services`, and `Views`.
- Added function-flow grouping for app-state actions, QA/proof helpers, agent
  loop functions, chat/context functions, runtime/model functions,
  settings/visual functions, tab/evidence functions, service/execution
  functions, view callbacks, and support helpers.
- Mirrored `functionFlowInventoryCount`, function-flow group counts, and
  proof-file parity into `/qa/coverage-index.groups.appState`.
- Updated coverage-index and app matrix proofs to require the function-flow
  inventory endpoint and mirror.
- Updated the system review and flow inventory docs with the function-flow
  inventory contract.

## Proof

- `python3 scripts/function-flow-inventory-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/function-flow-inventory` did not exist. The
green path keeps the Swift source tree as the authority and uses the app QA
routes as the mirror, so new functions must remain visible by ownership group,
proof owner, coverage-index count, and proof-file parity.
