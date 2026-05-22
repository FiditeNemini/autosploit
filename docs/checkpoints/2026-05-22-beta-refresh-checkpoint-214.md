# Checkpoint 214 - Coverage Index Runtime Artifact Count

## Goal

Make `/qa/coverage-index` surface the runtime live proof artifact count from its
`runtimeAndCache` group.

## Changes

- Strengthened `scripts/coverage-index-proof.py` to require
  `groups.runtimeAndCache.liveProofArtifactCount`.
- Moved runtime live proof artifacts into a shared AppState constant so
  `/qa/runtime-coverage` and `/qa/coverage-index` use the same source.
- Updated the coverage index group helper to accept extra metadata.
- Updated review and flow docs with the runtime/cache group count.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/runtime-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because the runtime/cache coverage-index group only exposed
its endpoint and proof counts. The green path adds artifact accounting without
duplicating the live proof artifact list.
