# Checkpoint 241 - Audit Latest Checkpoint Number

## Goal

Keep the global audit ledger aligned with the numeric latest-checkpoint signal
exposed by `/qa/checkpoint-ledger`.

## Changes

- Updated `scripts/audit-ledger-proof.py` to require
  `latestCheckpointNumber` parity with `/qa/checkpoint-ledger`.
- Added `latestCheckpointNumber` to `GET /qa/audit-ledger`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/audit-ledger` mirrored the latest checkpoint
path but not the numeric checkpoint value. The green path preserves that
numbered ordering signal at the aggregate audit layer.
