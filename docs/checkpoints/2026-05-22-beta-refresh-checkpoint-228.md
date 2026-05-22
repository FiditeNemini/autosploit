# Checkpoint 228 - App State Index Counts

## Goal

Make `/qa/coverage-index.groups.appState` expose the `/state.qaCoverage` route
and subtab proof breadth that the matrix smoke proof relies on.

## Changes

- Strengthened `scripts/coverage-index-proof.py` to require state route count,
  subtab state tab count, and subtab state proof count on the app-state group.
- Updated `GET /qa/coverage-index` so `appState` derives those counts from
  `qaCoverageSnapshot()`.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because the app-state group only exposed endpoint and proof
file accounting. The green path derives aggregate counts from the same
`qaCoverageSnapshot()` source used by `/state`, avoiding a second hard-coded
route/proof list.
