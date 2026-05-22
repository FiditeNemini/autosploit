# Checkpoint 211 - Visual Coverage Route Metadata

## Goal

Make `/qa/visual-coverage` expose the QA routes used to seed or switch visual
proof states, not only the screenshot manifests and proof names.

## Changes

- Strengthened `scripts/visual-coverage-proof.py` to require visual QA route
  coverage.
- Updated `GET /qa/visual-coverage` with chat, Settings, tab, OSINT, report,
  stash, tool-panel, cache, and unsupported-model visual proof routes.
- Updated docs with visual aggregate route coverage.

## Proof

- `python3 scripts/visual-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/visual-coverage` exposed manifest and proof
metadata but omitted the seed/switch routes those visual proofs use. The green
path makes screenshot-backed UI proof setup visible from the aggregate endpoint.
