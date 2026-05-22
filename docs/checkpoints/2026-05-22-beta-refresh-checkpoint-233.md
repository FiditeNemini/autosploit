# Checkpoint 233 - Checkpoint Documentation Ledger

## Goal

Expose checkpoint documentation coverage through the app QA API so the
implementation history is machine-auditable alongside proof scripts and proof
artifacts.

## Changes

- Added `scripts/checkpoint-ledger-proof.py`.
- Added `GET /qa/checkpoint-ledger`, dynamically discovering checkpoint docs
  under `docs/checkpoints`.
- The ledger reports checkpoint count, complete checkpoint count, incomplete
  checkpoint paths, latest checkpoint, and the full checkpoint path list.
- Added `/qa/checkpoint-ledger` to `/state.qaCoverage.stateRoutes`.
- Added the checkpoint-ledger route and `checkpointLedgerCount` to
  `/qa/coverage-index.groups.appState`.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/checkpoint-ledger` did not exist. The green
path keeps checkpoint docs discoverable and records whether each checkpoint has
the expected Goal, Changes, and Proof sections.
