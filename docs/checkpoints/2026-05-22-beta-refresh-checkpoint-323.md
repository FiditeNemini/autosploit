# Checkpoint 323 - Gap Contract Map Aggregate

## Goal

Make the top-level coverage index preserve the current gap contract map from
`/qa/gap-ledger`.

## Changes

- Added `gapContracts` to `/qa/coverage-index.groups.appState`.
- Extended `scripts/coverage-index-proof.py` to compare the aggregate gap
  contract map against `/qa/gap-ledger`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` with the same broad smoke
  check.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the app-state aggregate exposed the
open gap IDs and gap contract count, but not the structured gap contract map
itself. The green path keeps the Qwen multimodal runtime gap, blocked model
kinds, and enforcement proofs visible from the top-level QA index.
