# Checkpoint 203 - Visual Coverage Proof Count Metadata

## Goal

Make `/qa/visual-coverage` expose proof-count metadata in addition to manifests
and capture-count gates.

## Changes

- Strengthened `scripts/visual-coverage-proof.py` to require visual
  `proofCount`.
- Updated `GET /qa/visual-coverage` with the visual proof count.
- Updated docs with the visual aggregate proof-count coverage.

## Proof

- `python3 scripts/visual-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/settings-coverage-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/visual-coverage` listed proof scripts and
visual manifests but did not expose a direct proof count. The green path keeps
the existing manifest and image-size checks while making visual proof breadth
auditable from the aggregate endpoint.
