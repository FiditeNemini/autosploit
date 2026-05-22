# Checkpoint 346 - Open Gap Count Aggregate

## Goal

Make the source gap ledger, audit ledger, and top-level coverage index expose a
machine-readable count of open gap ids.

## Changes

- Added `openGapCount` to `/qa/gap-ledger`.
- Mirrored `openGapCount` through `/qa/audit-ledger`.
- Added `openGapCount` and `auditOpenGapCount` to
  `/qa/coverage-index.groups.appState`.
- Extended `scripts/gap-ledger-proof.py`, `scripts/audit-ledger-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/gap-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red source proof failed because `/qa/gap-ledger` exposed `openGapIds`
without a matching count. The green path keeps remaining runtime gap accounting
machine-readable at the source, audit, and aggregate QA layers.
