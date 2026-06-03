# Beta Refresh Checkpoint 473

Date: 2026-06-03

## Goal

Add an app-visible chat-quality evidence gate for the beta release lane so the repo can distinguish functional Qwen/MiniMax runtime evidence from broader answer-quality work that still needs longer runs.

## Changes

- Added `GET /qa/chat-quality-evidence-matrix`.
- Wired the route into `/state.qaCoverage.stateRoutes`, `/qa/runtime-coverage`, and the `runtimeAndCache` section of `/qa/coverage-index`.
- Added `scripts/chat-quality-evidence-matrix-proof.py`.
- Updated `scripts/coverage-index-proof.py` and `scripts/app-qa-matrix-smoke-proof.py` so broad QA checks request and mirror the new route.
- Updated `README.md` with the new matrix and kept the general chat-quality item in the remaining-work section.

## Evidence Matrix

The route reads these live artifacts:

- `docs/live-proofs/2026-06-03-release-app-qwen-mxfp4-live.json`
- `docs/live-proofs/2026-06-03-qwen-mxfp4-mtp-block-l2-ssm-live.json`
- `docs/live-proofs/2026-06-03-release-app-minimax-live.json`
- `docs/live-proofs/checkpoint-464-minimax-continuous-batching-live.json`

Rows:

- `qwenReleaseChat`: ready when the release app has non-empty first/repeat Qwen responses, repeat/cache reuse, TurboQuant q4 KV, and hybrid SSM topology.
- `qwenBlockL2SSMReplay`: ready when the current Qwen MXFP4-MTP block-L2/SSM replay artifact has TurboQuant q4 KV, block-L2 writes, SSM async rederive, and SSM L2 hit evidence.
- `minimaxReleaseChat`: partial by design because the release-app MiniMax artifact proves non-empty chat/cache/TurboQuant evidence but still shows first-turn instruction-following caveats.
- `minimaxBatchingChat`: ready when the live MiniMax batching artifact proves overlapping requests, TurboQuant q4 KV, and block-L2 writes.
- `qualityGapBoundary`: partial by design and keeps `broadQualityComplete=false`.

## Proof

Red:

- `python3 scripts/chat-quality-evidence-matrix-proof.py`
- Initial failure: `/qa/chat-quality-evidence-matrix failed: {'error': 'unknown: GET /qa/chat-quality-evidence-matrix'}`

Green:

- `python3 scripts/chat-quality-evidence-matrix-proof.py`

## Remaining

- Run the broader serial QA/build gate for this checkpoint.
- Longer realistic chat/tool-call quality runs are still required before calling broad model behavior polished.
- Native app final visual review across tabs, status indicators, hover/detail states, and the release-build window remains open.
- Manual adversarial security review of logging, command safety, and misuse cases remains open.
