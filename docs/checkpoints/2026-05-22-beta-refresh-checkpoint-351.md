# Checkpoint 351 - Qwen Gap Contract Counts

## Goal

Make the Qwen multimodal open-gap contract expose machine-readable counts for
blocked model kinds, required runtime work, and enforcement proofs.

## Changes

- Added Qwen multimodal blocked-kind, required-work, and proof counts to
  `/qa/gap-ledger`.
- Mirrored those counts through `/qa/audit-ledger`.
- Added source and audit Qwen gap detail counts to
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

The red source proof failed because `/qa/gap-ledger` preserved the Qwen
multimodal contract lists but did not expose count fields for blocked model
kinds, required runtime work, or enforcement proofs. The green path makes the
remaining Qwen multimodal runtime gap more directly auditable from the source,
audit, and top-level QA layers.
