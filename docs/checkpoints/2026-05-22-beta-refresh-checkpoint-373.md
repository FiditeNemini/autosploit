# Checkpoint 373 - Artifact Ledger File Parity

## Goal

Make `/qa/artifact-ledger` expose file-parity flags for visual manifests and
live proof artifacts, then mirror those flags through audit and coverage-index
surfaces.

## Changes

- Added `visualManifestFileParity` to `/qa/artifact-ledger`.
- Added `liveProofFileParity` to `/qa/artifact-ledger`.
- Mirrored both parity flags through `/qa/audit-ledger`.
- Mirrored source and audit artifact parity through
  `/qa/coverage-index.groups.appState`.
- Extended `scripts/artifact-ledger-proof.py`,
  `scripts/audit-ledger-proof.py`, `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/artifact-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/artifact-ledger` listed visual manifest and
live proof artifact paths without explicit route-owned file-parity flags.
