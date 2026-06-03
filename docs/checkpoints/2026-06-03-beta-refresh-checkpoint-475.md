# Beta Refresh Checkpoint 475

Date: 2026-06-03

## Goal

Expose the active broad objective as explicit app-visible audit rows instead of relying on scattered objective, runtime, cache, and lifecycle routes.

## Changes

- Added `GET /qa/active-objective-audit`.
- Wired the route into `/state.qaCoverage.stateRoutes`.
- Mirrored audit requirement IDs, covered count, blocked IDs, known-gap boundary, completion-claim boundary, and proof parity into the `releaseReadiness` group of `/qa/coverage-index`.
- Added `scripts/active-objective-audit-proof.py`.
- Updated `scripts/coverage-index-proof.py` to require the new route/proof and verify coverage-index mirrors.
- Added missing `/qa/cve-taxonomy-coverage` route inventory parity because the route existed but was absent from `/state.qaCoverage.stateRoutes`.
- Updated `README.md` with the active objective audit route and proof command.

## Proof

Red:

- `python3 scripts/active-objective-audit-proof.py`
- Initial failure: `/qa/active-objective-audit failed: {'error': 'unknown: GET /qa/active-objective-audit'}`

Green:

- `python3 scripts/active-objective-audit-proof.py`

## Requirement Rows

- `toolFlowUsageBuilt`
- `engineRuntimeBuilt`
- `cacheAndMemoryBuilt`
- `promptInjectionBoundaryBuilt`
- `cveEmbedsDatabaseBuilt`
- `contextCarryMaxTokensCompactionBuilt`
- `stashMemoryBuilt`
- `sessionLifecycleBuilt`
- `parallelSessionsContinuousBatchingBuilt`
- `responsesCacheReuseEndpointBuilt`
- `contentDeltaStreamingBuilt`
- `reasoningAndToolParserBuilt`
- `l2DiskCacheStorageHitBuilt`
- `turboQuantKVCacheComponentBuilt`
- `hybridSSMAsyncReDeriveBuilt`
- `toolLiveStatusLogsBuilt`
- `knownGapBoundaryBuilt`

## Remaining

- The broad active objective is still intentionally open; `/qa/active-objective-audit` reports `completionClaimAllowed=false`.
- Qwen multimodal promotion remains a known open gap.
- Longer realistic chat/tool-call quality runs and final native visual review still need more proof before calling the beta fully ready.
