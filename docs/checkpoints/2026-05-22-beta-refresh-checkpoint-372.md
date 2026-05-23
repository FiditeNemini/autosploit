# Checkpoint 372 - Proof Ledger File Parity

## Goal

Make `/qa/proof-ledger` expose machine-readable proof-file parity and mirror
that parity through the audit ledger and coverage index.

## Changes

- Added `proofFileParity` to `/qa/proof-ledger`.
- Added `proofLedgerProofFileParity` to `/qa/audit-ledger`.
- Added `proofLedgerProofFileParity` and `auditProofLedgerProofFileParity` to
  `/qa/coverage-index.groups.appState`.
- Extended `scripts/proof-ledger-proof.py`, `scripts/audit-ledger-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/proof-ledger` listed all proof scripts without
an explicit route-owned parity flag proving those script paths exist.
