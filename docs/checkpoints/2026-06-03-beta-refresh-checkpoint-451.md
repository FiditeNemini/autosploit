# Parallel Agent and Continuous Batching Coverage

## Goal

Tighten the beta runtime-flow gate around parallel sessions and continuous
batching without overstating loaded-model proof.

## Changes

- Added `GET /qa/continuous-batching-coverage`.
- Added `scripts/continuous-batching-coverage-proof.py`.
- Added `scripts/parallel-agent-session-proof.py`.
- Expanded `/qa/deep-runtime-flow-coverage` with:
  - `parallelAgentSessionProof`
  - `continuousBatchingSourceCoverage`
  - `continuousBatching` domain coverage
- Mirrored continuous batching through `/qa/runtime-coverage` and
  `/qa/coverage-index.groups.runtimeAndCache`.
- Updated README beta status to separate:
  - proven mock-engine parallel app sessions
  - proven source-backed continuous batching contracts
  - still-open live loaded-model continuous batching stress

## Proof

Verified:

```bash
swift build --package-path ExploitBot -c debug
python3 scripts/continuous-batching-coverage-proof.py
python3 scripts/parallel-agent-session-proof.py
python3 scripts/deep-runtime-flow-coverage-proof.py
python3 scripts/runtime-coverage-proof.py
python3 scripts/coverage-index-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
python3 scripts/proof-suite-inventory-proof.py
```

The parallel proof observed two overlapping app-to-engine requests against a
delayed mock Qwen engine: `max_in_flight=2`.

Proven by this checkpoint:

- Two deployed autonomous agents can run concurrently from the app against the
  mock engine.
- The app exposes live parallel-agent progress through `/state.agents`:
  `workingCount`, per-agent `isWorking`, and per-agent `statusLine`.
- Agents still inherit full tool schema access, runtime defaults, reasoning
  state, and max-iteration settings.
- Continuous batching source coverage is present for:
  - server `--continuous-batching` / `BatchedEngine` selection
  - LLM waiting/running queues and `mlx_lm.BatchGenerator`
  - MLLM scheduler queues and `MLLMBatchGenerator`
  - BatchKVCache and BatchMambaCache cache merge/extract support
  - TurboQuant KV cache storage contracts
  - prompt/block L2 disk cache contracts
  - hybrid SSM companion cache and async eval paths

Still not proven:

- Live loaded-model continuous batching under realistic concurrent Qwen/MiniMax
  traffic.
- A full release-app visual pass across every tab/status/hover/detail state.
