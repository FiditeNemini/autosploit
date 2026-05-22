# Checkpoint 244 - Checkpoint Completion Ratio

## Goal

Expose a compact checkpoint documentation completion ratio through the
checkpoint and audit ledgers.

## Changes

- Updated `scripts/checkpoint-ledger-proof.py` to require
  `checkpointCompletionRatio`.
- Updated `scripts/audit-ledger-proof.py` to require ratio parity with
  `/qa/checkpoint-ledger`.
- Added `checkpointCompletionRatio` to `GET /qa/checkpoint-ledger`.
- Added `checkpointCompletionRatio` to `GET /qa/audit-ledger`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because the ledgers exposed complete/incomplete counts and
lists but no direct completion ratio. The green path reports a six-decimal
ratio derived from complete checkpoint docs divided by all checkpoint docs.
