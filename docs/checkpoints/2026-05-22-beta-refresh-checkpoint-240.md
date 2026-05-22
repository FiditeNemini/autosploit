# Checkpoint 240 - Numeric Latest Checkpoint Ledger

## Goal

Fix checkpoint-ledger latest-checkpoint reporting so it uses the numeric
checkpoint suffix instead of lexicographic filename order.

## Changes

- Updated `scripts/checkpoint-ledger-proof.py` to compute the expected latest
  checkpoint by numeric suffix.
- Added a required `latestCheckpointNumber` assertion.
- Updated `GET /qa/checkpoint-ledger` to compute latest checkpoint by numeric
  checkpoint number.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because lexicographic ordering reported checkpoint 90 as
the latest after checkpoint 239 existed. The green path reports the real highest
numeric checkpoint and keeps `/qa/audit-ledger.latestCheckpoint` consistent
through the child checkpoint ledger.
