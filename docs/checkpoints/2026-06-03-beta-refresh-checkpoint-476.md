# Beta Refresh Checkpoint 476

Date: 2026-06-03

## Goal

Expose context, session, cache, batching, and model-efficiency requirements as hard app-visible invariants that can block beta readiness instead of relying only on scattered QA rows.

## Changes

- Added `GET /qa/context-efficiency-invariants`.
- Wired the route into `/state.qaCoverage.stateRoutes`.
- Mirrored invariant IDs, ready counts, blocked IDs, route parity, contract parity, and proof parity into the `chatAndContext` group of `/qa/coverage-index`.
- Mirrored ready count, contract parity, and proof parity into the `runtimeAndCache` group of `/qa/coverage-index`.
- Added `scripts/context-efficiency-invariants-proof.py`.
- Updated `scripts/coverage-index-proof.py` to require the new route/proof and verify both coverage-index mirrors.
- Updated `README.md` with the new context efficiency invariant gate and proof command.

## Proof

Red:

- `python3 scripts/context-efficiency-invariants-proof.py`
- Initial failure: `/qa/context-efficiency-invariants failed: {'error': 'unknown: GET /qa/context-efficiency-invariants'}`

Green:

- `python3 scripts/context-efficiency-invariants-proof.py`

## Invariants

- `automaticContextCap`
- `contextPacketBudget`
- `maxTokenAndIterationForwarding`
- `newContextPreservesCache`
- `stashAndCVEOnDemandRetrieval`
- `promptInjectionBoundedContext`
- `responsesPreviousResponseReuse`
- `streamingDeltaCoverage`
- `parallelSessionBatching`
- `qwenMemoryCeiling`
- `l2DiskCacheHit`
- `turboQuantKVQ4`
- `hybridSSMAsyncReDerive`

## Remaining

- The broad active objective remains open until final app UI review, longer realistic chat/tool-call quality runs, and Qwen multimodal promotion are proven.
- This checkpoint is a hard QA route and proof gate; it does not by itself replace notarized DMG verification.
