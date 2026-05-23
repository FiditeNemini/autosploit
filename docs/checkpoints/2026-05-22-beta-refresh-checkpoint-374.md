# Checkpoint 374 - Checkpoint Ledger File Parity

## Goal

Make `/qa/checkpoint-ledger` expose file parity for checkpoint documentation
paths and mirror that flag through audit and coverage-index surfaces.

## Changes

- Added `checkpointFileParity` to `/qa/checkpoint-ledger`.
- Mirrored `checkpointFileParity` through `/qa/audit-ledger`.
- Mirrored source and audit checkpoint parity through
  `/qa/coverage-index.groups.appState`.
- Extended `scripts/checkpoint-ledger-proof.py`,
  `scripts/audit-ledger-proof.py`, `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/checkpoint-ledger` listed checkpoint
documentation paths without an explicit route-owned file-parity flag.
