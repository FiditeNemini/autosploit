# Checkpoint 322 - Runtime Cache Component Proof Map Aggregate

## Goal

Make the top-level coverage index preserve the runtime cache component proof map
from `/qa/runtime-coverage`.

## Changes

- Added `cacheComponentProofs` to `/qa/coverage-index.groups.runtimeAndCache`.
- Extended `scripts/coverage-index-proof.py` to compare the aggregate runtime
  cache component proof map against `/qa/runtime-coverage`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` with the same broad smoke
  check.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the runtime/cache aggregate exposed
cache component list/count/parity and proof count/parity, but not the component
to proof-script map. The green path keeps prefix cache, prompt L2 disk, paged
KV cache, block L2 disk, TurboQuant KV, SSM companion L2, and new-context
engine-session preservation traceable from the top-level QA index to their
proof scripts.
