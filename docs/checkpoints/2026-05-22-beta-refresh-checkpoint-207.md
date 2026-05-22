# Checkpoint 207 - OSINT Screenshot Seed Route Coverage

## Goal

Make `/qa/tab-action-coverage` expose the OSINT screenshot artifact seed route
used by the OSINT artifact proof.

## Changes

- Strengthened `scripts/tab-action-coverage-proof.py` to require
  `/qa/seed-osint-screenshot-artifact`.
- Updated `GET /qa/tab-action-coverage` with that route.
- Updated docs with OSINT screenshot seed route coverage.

## Proof

- `python3 scripts/tab-action-coverage-proof.py`
- `python3 scripts/osint-screenshot-artifact-proof.py`
- `python3 scripts/osint-artifact-actions-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/tab-action-coverage` listed
`osint-screenshot-artifact-proof.py` but omitted its setup route. The green path
makes the OSINT screenshot artifact setup/action chain visible from the tab
aggregate endpoint.
