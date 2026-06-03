# Beta Refresh Checkpoint 469 - Per-Turn Runtime Contract

Date: 2026-06-03

## Goal

Convert the objective execution graph into per-turn runtime contracts so each
turn phase exposes its input contract, visible status surface, route/proof
evidence, and runtime/cache counters.

## Changes

- Added `/qa/per-turn-runtime-contract`.
- Added `scripts/per-turn-runtime-contract-proof.py`.
- Wired the contract route through `/state.qaCoverage.stateRoutes`.
- Mirrored row count, readiness, parity, status surfaces, and proof parity
  through `/qa/coverage-index.groups.releaseReadiness`.
- Updated the README beta lane with the per-turn runtime contract.

## Proof

Red path:

- `python3 scripts/per-turn-runtime-contract-proof.py`
- Expected failure before route wiring:
  `unknown: GET /qa/per-turn-runtime-contract`.

Green path:

- `python3 scripts/per-turn-runtime-contract-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

The contract exposes 18 ready rows for turn input, context budget, compaction,
CVE include filters, semantic CVE retrieval, stash retrieval, prompt-injection
boundary, tool schema selection, live tool progress, engine request budget,
Responses reuse, streaming deltas, reasoning/tool parser, parallel
session/batching, L2 disk cache, TurboQuant KV, hybrid SSM async rederive, and
the result/gap boundary.

## Remaining

This checkpoint proves per-turn wiring and status/evidence surfaces. It does
not close the tracked Qwen multimodal runtime promotion, multimodal prefix-cache,
or multimodal context-routing live-proof gaps.
