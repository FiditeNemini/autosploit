# Checkpoint 342 - Tool Registry Aggregate Detail

## Goal

Make `/qa/coverage-index.groups.toolsAndParsers` preserve the detailed model
tool registry exposed by `/qa/tool-coverage`.

## Changes

- Added always-visible tool count and bounded catalogue limit.
- Added registry tab list and full registry tool list.
- Added registry failure list/count.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because the aggregate carried registry counts but not the
actual tool rows, tab ownership, bounded catalogue limit, or registry failure
details. The green path keeps model-visible tool inventory and routing ownership
auditable from the top-level QA index.
