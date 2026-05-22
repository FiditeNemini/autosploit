# Checkpoint 204 - Coverage Index Group Counts

## Goal

Make `/qa/coverage-index` expose per-group endpoint and proof counts, not only
top-level totals.

## Changes

- Strengthened `scripts/coverage-index-proof.py` to require every coverage
  group to expose matching `endpointCount` and `proofCount`.
- Updated `GET /qa/coverage-index` groups with those counts.
- Updated docs with coverage-index group-count accounting.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/tool-flow-coverage-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/coverage-index` groups exposed endpoint and
proof arrays but not direct counts. The green path keeps existing group
membership while making each group independently auditable.
