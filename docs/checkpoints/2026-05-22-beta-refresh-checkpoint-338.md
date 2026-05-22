# Checkpoint 338 - Runtime Aggregate Detail

## Goal

Make `/qa/coverage-index.groups.runtimeAndCache` preserve the detailed runtime
contract, route, proof, live-proof, and cache metadata already exposed by
`/qa/runtime-coverage`.

## Changes

- Added runtime contract map/count to the runtime/cache aggregate.
- Added runtime route list/count and runtime proof list/count.
- Added the live proof family matrix and live proof artifact map/count.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because the top-level runtime/cache aggregate exposed only
the live-proof count and cache component proof details. The green path keeps the
runtime contracts, route/proof coverage, live Qwen/MiniMax proof matrix, and
checked-in live artifact paths visible from the same top-level QA index used by
the broad app matrix.
