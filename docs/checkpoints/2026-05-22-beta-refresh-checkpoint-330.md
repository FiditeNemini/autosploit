# Checkpoint 330 - Gap Source Detail Aggregate

## Goal

Make the top-level coverage index preserve the source-derived gap warning
details from `/qa/gap-ledger`.

## Changes

- Added `gapSource`, `gapSourceDerived`, and `gapSourcePathExists` to
  `/qa/coverage-index.groups.appState`.
- Added `currentGaps`, `nextGap`, `gapSupportedFamilies`, and
  `unsupportedMultimodalBlocked`.
- Extended `scripts/coverage-index-proof.py` to compare those aggregate fields
  against `/qa/gap-ledger`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` with the same broad smoke
  checks.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red coverage-index proof failed because the app-state aggregate exposed the
gap count, open IDs, and structured contracts, but not the source-derived text
or support-boundary fields. The green path keeps the Qwen/MiniMax-only warning
and Qwen multimodal block state visible from the top-level QA index.
