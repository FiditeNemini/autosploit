# Checkpoint 188 - Runtime Coverage Endpoint

## Goal

Expose the runtime/model/cache contract through a machine-readable QA route so
Qwen/MiniMax support, parser autodetect, model-folder defaults, cache topology,
and live-proof gates can be audited together.

## Changes

- Added `scripts/runtime-coverage-proof.py`.
- Added `GET /qa/runtime-coverage`, returning:
  - supported runtime families (`qwen`, `minimax`)
  - `prefix-cache-l2-turboquant` cache-response method
  - parser/model-folder/cache/new-context/unsupported-start contract flags
  - Qwen and MiniMax live-proof gate summaries
  - proof scripts covering metadata, model-folder warnings, unsupported starts,
    cache stats, new context windows, live model verifier, block L2, and SSM
    rederive status
- Extended `scripts/app-qa-matrix-smoke-proof.py` to require the new route and
  validate the cache-response method.
- Updated app flow and system review docs with the runtime audit route.

## Proof

```bash
python3 scripts/runtime-coverage-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
python3 scripts/cache-stats-state-proof.py
```

## Notes

The red proof failed because `GET /qa/runtime-coverage` did not exist. The green
proof verifies the route exposes Qwen/MiniMax runtime support plus the
prefix-cache/L2/TurboQuant cache-response contract and associated proof gates.
