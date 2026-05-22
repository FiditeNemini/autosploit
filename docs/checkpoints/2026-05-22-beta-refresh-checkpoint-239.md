# Checkpoint 239 - Audit Ledger Action Lists

## Goal

Make the global audit ledger directly actionable by exposing the specific
missing/failed/incomplete paths it counts.

## Changes

- Updated `scripts/audit-ledger-proof.py` to require list parity between
  `/qa/audit-ledger` and the child ledgers.
- Added `missingVisualCaptures`, `failedLiveProofs`, and
  `incompleteCheckpoints` to `GET /qa/audit-ledger`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/audit-ledger` exposed only counts. The green
path keeps the aggregate audit endpoint useful for immediate triage without
requiring clients to call every child ledger separately.
