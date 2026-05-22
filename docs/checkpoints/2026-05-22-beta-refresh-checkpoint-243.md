# Checkpoint 243 - Complete Checkpoint Lists

## Goal

Expose the complete checkpoint path list alongside the incomplete checkpoint
path list so documentation completeness is inspectable from both sides.

## Changes

- Updated `scripts/checkpoint-ledger-proof.py` to require
  `completeCheckpoints` in numeric checkpoint order.
- Updated `scripts/audit-ledger-proof.py` to require complete checkpoint list
  parity between `/qa/audit-ledger` and `/qa/checkpoint-ledger`.
- Added `completeCheckpoints` to `GET /qa/checkpoint-ledger`.
- Added `completeCheckpoints` to `GET /qa/audit-ledger`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/checkpoint-ledger` only exposed the complete
count, not the complete path list. The green path keeps checkpoint completion
auditable without inferring complete paths from the full minus incomplete set.
