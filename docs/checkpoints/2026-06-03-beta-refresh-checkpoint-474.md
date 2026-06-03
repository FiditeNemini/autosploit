# Beta Refresh Checkpoint 474

Date: 2026-06-03

## Goal

Make the runtime/context/cache objective visible as one ordered per-turn lifecycle instead of scattered route rows.

## Changes

- Added `GET /qa/turn-lifecycle-evidence`.
- Wired the route into `/state.qaCoverage.stateRoutes`.
- Mirrored lifecycle phase IDs, ready counts, known-gap boundary, contract parity, and proof parity into the `runtimeAndCache` group of `/qa/coverage-index`.
- Added `scripts/turn-lifecycle-evidence-proof.py`.
- Updated `scripts/coverage-index-proof.py` to require the new route/proof and compare the coverage-index mirror.
- Updated `README.md` with the lifecycle route and proof command.

## Proof

Red:

- `python3 scripts/turn-lifecycle-evidence-proof.py`
- Initial failure: `/qa/turn-lifecycle-evidence failed: {'error': 'unknown: GET /qa/turn-lifecycle-evidence'}`

Green:

- `python3 scripts/turn-lifecycle-evidence-proof.py`
- `python3 scripts/coverage-index-proof.py`

## Lifecycle Phases

- `turnInput`
- `contextBudgetAndCompaction`
- `cveIncludeAndSemanticRetrieval`
- `stashMemoryRetrieval`
- `promptInjectionBoundary`
- `toolSchemaAndLiveStatus`
- `responsesReuseAndStreaming`
- `reasoningAndToolParser`
- `parallelSessionBatching`
- `l2DiskCache`
- `turboQuantKV`
- `hybridSSMAsyncReDerive`
- `resultLogAndKnownGapBoundary`

## Remaining

- Longer realistic chat/tool-call quality runs are still required.
- Native app final visual review remains open.
- Manual adversarial security review remains open.
- Qwen multimodal promotion proofs remain open; the lifecycle route intentionally keeps `objectiveComplete=false`.
