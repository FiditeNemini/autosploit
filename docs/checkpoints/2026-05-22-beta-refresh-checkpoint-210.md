# Checkpoint 210 - Subtab Coverage Route And Proof Metadata

## Goal

Make `/qa/subtab-coverage` expose the route and proof-count metadata behind
state and visual subtab switching.

## Changes

- Strengthened `scripts/subtab-coverage-proof.py` to require `proofCount`.
- Strengthened the same proof to require `/qa/tool-subtab` and
  `/qa/visual-subtab`.
- Updated `GET /qa/subtab-coverage` with those routes and proof-count metadata.
- Refreshed checkpoint-70 visual subtab lifecycle screenshots through
  `scripts/visual-tab-proof.py`.
- Updated docs with subtab aggregate route coverage.

## Proof

- `python3 scripts/subtab-coverage-proof.py`
- `python3 scripts/visual-tab-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/subtab-coverage` listed each tab's focused
proof script but did not expose a direct proof count or the routes used for
state and visual subtab switching. The green path makes those routes visible
from the aggregate endpoint and keeps the screenshot-backed lifecycle proof
fresh.
