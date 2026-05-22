# Checkpoint 353 - Gap Contract Count Ledger Source

## Goal

Make the gap-contract count originate in `/qa/gap-ledger`, mirror through
`/qa/audit-ledger`, and surface unchanged through `/qa/coverage-index`.

## Changes

- Added `gapContractCount` to `/qa/gap-ledger`.
- Mirrored `gapContractCount` through `/qa/audit-ledger`.
- Updated `/qa/coverage-index.groups.appState.gapContractCount` and
  `auditGapContractCount` to consume the ledger-owned counts.
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

The red proof failed because `/qa/gap-ledger` exposed the structured
`gapContracts` map without a machine-readable contract count. The green path
makes the source gap ledger own the count, keeps the audit ledger as a mirror,
and prevents the coverage index from recomputing audit contract accounting.
