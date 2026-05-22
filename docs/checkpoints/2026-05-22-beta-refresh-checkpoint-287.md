# Checkpoint 287 - Runtime Cache Component Contract

## Goal
Make runtime/cache coverage enumerate the cache components behind the `prefix-cache-l2-turboquant` response path.

## Changes
- Added `/qa/runtime-coverage.cacheComponents`.
- Added `cacheComponentCount` and `cacheComponentParity`.
- Mirrored the runtime cache component list/count/parity into `/qa/coverage-index.groups.runtimeAndCache`.
- Strengthened `scripts/runtime-coverage-proof.py`, `scripts/coverage-index-proof.py`, and `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/runtime-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red runtime coverage proof failed because `/qa/runtime-coverage` exposed cache contracts as booleans but not an ordered component list/count/parity for prefix cache, prompt L2 disk, paged KV cache, block L2 disk, TurboQuant KV, SSM companion L2, and new-context engine-session preservation.
