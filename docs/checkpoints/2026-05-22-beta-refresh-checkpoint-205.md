# Checkpoint 205 - Settings Coverage Proof Count Metadata

## Goal

Make `/qa/settings-coverage` expose proof-count metadata for the split Settings
panel contract.

## Changes

- Strengthened `scripts/settings-coverage-proof.py` to require settings
  `proofCount`.
- Updated `GET /qa/settings-coverage` with the settings proof count.
- Updated docs with Settings aggregate proof-count coverage.

## Proof

- `python3 scripts/settings-coverage-proof.py`
- `python3 scripts/settings-category-coverage-proof.py`
- `python3 scripts/visual-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/settings-coverage` listed the Settings proof
scripts but did not expose a direct proof count. The green path keeps the split
category/page-section contract unchanged while making Settings proof breadth
machine-checkable.
