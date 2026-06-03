# Beta Refresh Checkpoint 462 - Engine API/Cache Proof Matrix

Date: 2026-06-03

## Goal

Expose the engine pytest-backed API/cache coverage through the app QA surface so beta readiness has one auditable route for Responses session reuse, parser API shape, reasoning/content delta fields, cache defaults, TurboQuant KV mode, prompt/block L2 disk cache, and hybrid SSM rederive status.

## Changes

- Added `/qa/engine-api-cache-proof-matrix`.
- Added `scripts/engine-api-cache-proof-matrix-proof.py`.
- Mirrored the new route and proof into the runtime/cache coverage index group.
- Documented the new beta verification gate in `README.md`.

## Proof

Red path:

- `python3 scripts/engine-api-cache-proof-matrix-proof.py`
- Expected failure before route wiring: `unknown: GET /qa/engine-api-cache-proof-matrix`.

Green path:

- `python3 scripts/engine-api-cache-proof-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/endpoint-inventory-proof.py`
- `python3 scripts/endpoint-route-matrix-proof.py`
- `python3 scripts/beta-readiness-coverage-proof.py`
- `swift build --package-path ExploitBot -c debug`

## Remaining

This checkpoint improves app-visible engine/API/cache proof coverage. It does not close the broader Qwen multimodal runtime promotion gap or replace live model load/chat verification.
