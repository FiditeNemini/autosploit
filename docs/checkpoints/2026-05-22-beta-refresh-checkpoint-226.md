# Checkpoint 226 - Runtime Cache Index Metadata

## Goal

Make `/qa/coverage-index.groups.runtimeAndCache` expose the supported model
families and cache response method that are critical to long-context
prefix-cache operation.

## Changes

- Strengthened `scripts/coverage-index-proof.py` to require `supportedFamilies`
  and `cacheResponseMethod` on the runtime/cache group.
- Updated `GET /qa/coverage-index` so `runtimeAndCache` rolls up Qwen/MiniMax
  support, the `prefix-cache-l2-turboquant` response method, and live proof
  artifact count.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/runtime-coverage-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because the runtime/cache group only exposed the live proof
artifact count. The green path keeps `/qa/runtime-coverage` as the detailed
runtime contract while making the supported families and cache response method
visible from the top-level QA index.
