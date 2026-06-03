# Beta Refresh Checkpoint 478

Date: 2026-06-03

## Goal

Tighten the remaining Qwen multimodal known gap so promotion cannot be faked by broad source evidence or by accidentally including non-Qwen/MiniMax VL folders.

## Changes

- Added `GET /qa/qwen-multimodal-promotion-readiness`.
- Wired the route into `/state.qaCoverage.stateRoutes`.
- Added `scripts/qwen-multimodal-promotion-readiness-proof.py`.
- Mirrored promotion readiness, missing live proofs, criteria count, and proof-existence parity into the `appState` group of `/qa/coverage-index`.
- Classified Qwen multimodal proof scripts under the runtime proof ledger category instead of the generic `other` bucket.
- Updated `README.md` and `docs/app-system-review-2026-05-21.md` with the readiness route.

## Proof

Red:

- `python3 scripts/qwen-multimodal-promotion-readiness-proof.py`
- Initial failure: `/qa/qwen-multimodal-promotion-readiness failed: {'error': 'unknown: GET /qa/qwen-multimodal-promotion-readiness'}`

Green:

- `python3 scripts/qwen-multimodal-promotion-readiness-proof.py`

## Boundary

- Active beta families remain `qwen` and `minimax`.
- ZAYA and non-Qwen/MiniMax multimodal folders remain outside the active beta lane.
- Promotion remains false until these exact live proofs exist and pass:
  - `live-qwen-multimodal-loader-proof.py`
  - `live-qwen-multimodal-prefix-cache-proof.py`
  - `live-qwen-multimodal-context-routing-proof.py`

## Remaining

- This checkpoint does not load a Qwen VL model. It prevents the known gap from being misreported and keeps the live proof requirements explicit.
- The broad active objective remains open until the live Qwen multimodal loader, multimodal prefix-cache discipline, and multimodal context-routing proofs exist and pass.
