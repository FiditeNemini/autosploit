# Checkpoint 460 - Context Session Efficiency Matrix

## Goal

Make context carry, token budget, compaction, session reuse, parallel sessions,
and cache efficiency auditable from one route instead of requiring agents to
manually join several QA endpoints.

## Changes

- Added `scripts/context-session-efficiency-matrix-proof.py`.
- Added `/qa/context-session-efficiency-matrix`.
- Mirrored the route through `/state` QA route coverage and the
  `chatAndContext` group in `/qa/coverage-index`.
- Wired the matrix into `/qa/objective-runtime-coverage` rows for
  `contextCarryCompaction` and `sessionParallelContinuousBatching`.
- The matrix rows cover automatic context cap, max-token forwarding,
  max-iteration budget, compaction format, new-context cache preservation,
  stash/CVE on-demand retrieval, Responses `previous_response_id` reuse,
  streaming usage telemetry, parallel sessions, Qwen/MiniMax continuous
  batching, live loaded-model agent stress, L2 disk hit/storage counters,
  TurboQuant KV, and hybrid SSM async rederive counters.

## Proof

Red path:

```bash
python3 scripts/context-session-efficiency-matrix-proof.py
```

Initially failed with:

```text
unknown: GET /qa/context-session-efficiency-matrix
```

Green path:

```bash
python3 scripts/context-session-efficiency-matrix-proof.py
```

Passed after the route and coverage-index mirrors were added.

## Remaining

- This route is a context/session/cache efficiency audit. It does not close the
  separate Qwen multimodal runtime promotion gap.
