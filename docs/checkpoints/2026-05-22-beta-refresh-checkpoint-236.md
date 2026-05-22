# Checkpoint 236 - Current Gap Ledger

## Goal

Expose the documented current gap through the app QA API so the remaining
runtime boundary is machine-readable and covered by the proof suite.

## Changes

- Added `scripts/gap-ledger-proof.py`.
- Added `GET /qa/gap-ledger`.
- The gap ledger reports the current gap list, next gap, source document,
  Qwen/MiniMax supported-family boundary, and Qwen VL/multimodal blocked state.
- Added `/qa/gap-ledger` to `/state.qaCoverage.stateRoutes`.
- Added gap-ledger route, proof, and `currentGapCount` to
  `/qa/coverage-index.groups.appState`.
- Updated `scripts/app-qa-matrix-smoke-proof.py` to fetch and verify
  `/qa/gap-ledger` directly.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/gap-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/gap-ledger` did not exist. The green path
keeps the known remaining Qwen multimodal promotion boundary visible through
the same QA surface as the proof, artifact, checkpoint, and audit ledgers.
