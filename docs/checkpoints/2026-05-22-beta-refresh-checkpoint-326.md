# Checkpoint 326 - Checkpoint Path List Aggregate

## Goal

Make the top-level coverage index preserve checkpoint path lists from
`/qa/checkpoint-ledger`.

## Changes

- Added `checkpoints`, `completeCheckpoints`, and `incompleteCheckpoints` to
  `/qa/coverage-index.groups.appState`.
- Extended `scripts/coverage-index-proof.py` to compare those aggregate lists
  against `/qa/checkpoint-ledger`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` with the same broad smoke
  checks.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the app-state aggregate exposed
checkpoint count, complete/incomplete counts, completion ratio, and latest
checkpoint metadata, but not the underlying checkpoint path lists. The green
path keeps the full checkpoint ledger, completed checkpoint list, and incomplete
checkpoint list traceable from the top-level QA index.
