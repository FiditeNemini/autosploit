# Beta Refresh Checkpoint 424

## Goal

Expose a source-owned Swift model/state inventory so AppState helpers, operation
models, tab and phase enums, chat roles, and parsed tool-result models are
grouped, documented, mirrored into coverage, and tied to proof owners.

## Changes

- Added `scripts/model-state-inventory-proof.py`.
- Added `/qa/model-state-inventory`.
- Added `/qa/model-state-inventory` to `/state.qaCoverage.stateRoutes`.
- Added source parsing for Swift files under
  `ExploitBot/Sources/ExploitBot/Models`.
- Added grouping and proof-owner mapping for AppState core, operation models,
  navigation models, chat models, and parsed-result models.
- Added enum-case inventory for operation status, interaction mode, pentest
  phase, chat role, and tool-tab contracts.
- Mirrored model-state file counts, type counts, function counts, group counts,
  and proof-file parity into `/qa/coverage-index.groups.appState`.
- Updated coverage-index and app matrix proofs to require the model-state
  inventory endpoint and mirror.
- Updated the system review and flow inventory docs with the model-state
  inventory contract.

## Proof

- `python3 scripts/model-state-inventory-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/model-state-inventory` did not exist. The
green path keeps `ExploitBot/Sources/ExploitBot/Models` as the authority, so
future AppState/model/type/function/enum changes must appear in the
source-derived inventory and coverage-index mirror.
