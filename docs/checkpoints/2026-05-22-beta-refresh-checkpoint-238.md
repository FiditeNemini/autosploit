# Checkpoint 238 - Audit Ledger Gap Rollup

## Goal

Make the global audit ledger include the currently documented gap so the
aggregate QA endpoint covers both completed proof evidence and known remaining
work.

## Changes

- Updated `scripts/audit-ledger-proof.py` to cross-check `/qa/audit-ledger`
  against `/qa/gap-ledger`.
- Added `currentGapCount` and `nextGap` to `GET /qa/audit-ledger`.
- Included the gap count in `totalLedgerItemCount`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/audit-ledger` did not include gap state. The
green path keeps the global audit endpoint aligned with the source-derived
current gap ledger.
