# Checkpoint 350 - Audit Proof Category Map

## Goal

Make `/qa/audit-ledger` and `/qa/coverage-index.groups.appState` preserve the
full source proof-ledger category map.

## Changes

- Added `proofLedgerCategories` to `/qa/audit-ledger`.
- Added `auditProofLedgerCategories` to the coverage-index app-state aggregate.
- Extended `scripts/audit-ledger-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red audit proof failed because `/qa/audit-ledger` mirrored source
proof-ledger category counts/surfaces/other/total/parity but not the detailed
category map. The green path keeps source proof ownership visible through both
the audit ledger and the top-level QA index.
