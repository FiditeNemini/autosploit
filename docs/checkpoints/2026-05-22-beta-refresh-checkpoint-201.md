# Checkpoint 201 - Runtime Coverage Route And Proof Metadata

## Goal

Make `/qa/runtime-coverage` expose the route and proof-count metadata behind
the runtime/cache contract, especially the prefix-cache new-context path.

## Changes

- Strengthened `scripts/runtime-coverage-proof.py` to require runtime
  `proofCount`.
- Strengthened the same proof to require model-folder, engine-start,
  new-context, settings cache seed, and live cache seed routes.
- Updated `GET /qa/runtime-coverage` with the required routes and proof count.
- Updated docs with runtime aggregate route coverage.

## Proof

- `python3 scripts/runtime-coverage-proof.py`
- `python3 scripts/context-window-cache-proof.py`
- `python3 scripts/cache-stats-state-proof.py`
- `python3 scripts/model-folder-warning-proof.py`
- `python3 scripts/unsupported-model-start-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/runtime-coverage` named the runtime proofs but
did not expose `proofCount` or the routes that exercise model-folder
autodetect, unsupported-start blocking, cache stats, live cache stats, and
cache-preserving new context.
