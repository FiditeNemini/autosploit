# Beta Refresh Checkpoint 463 - State-Dependent Contract Matrix

Date: 2026-06-03

## Goal

Make state-dependent QA false flags auditable instead of ambiguous. The app now separates fixture-required CVE semantic embedding, semantic context-packet, parser fixture, tool/engine/context, and deep runtime rows from implementation failures.

## Changes

- Added `/qa/state-dependent-contract-matrix`.
- Added `scripts/state-dependent-contract-matrix-proof.py`.
- Mirrored the new route and proof through the chat/context, runtime/cache, and tools/parsers coverage-index groups.
- Extended the broad app QA smoke proof to exercise the new route.
- Documented the new state-dependent contract matrix in `README.md`.

## Proof

Red path:

- `python3 scripts/state-dependent-contract-matrix-proof.py`
- Expected failure before route wiring: `unknown: GET /qa/state-dependent-contract-matrix`.

Green path:

- `python3 scripts/state-dependent-contract-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Remaining

This checkpoint clarifies and proves fixture-dependent CVE/parser state. It does not close the Qwen multimodal runtime promotion gap, and it does not replace live Qwen/MiniMax model load/chat proof.
