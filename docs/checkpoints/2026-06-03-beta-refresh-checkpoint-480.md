# Beta refresh checkpoint 480

## Goal

- Added `scripts/live-qwen-multimodal-loader-proof.py` as the guarded live
  Qwen/MiniMax multimodal loader harness.

## Changes

- The harness requires `EXPLOITBOT_LIVE_QWEN_MULTIMODAL_MODEL` or `--model`,
  rejects ZAYA and non-Qwen/MiniMax folders, rejects Qwen3.5/3.6 text-lane
  folders without explicit VL markers, and only writes
  `docs/live-proofs/live-qwen-multimodal-loader-proof.json` after a real engine
  load plus non-empty multimodal chat response.
- Updated `/qa/qwen-multimodal-promotion-readiness`, `/qa/gap-ledger`, and
  `/qa/coverage-index` proof expectations so the loader script can exist while
  promotion remains blocked by the missing live result artifact.

## Status

- The loader harness script exists.
- No live Qwen/MiniMax multimodal artifact was produced at this checkpoint
  because no explicit Qwen/MiniMax VL model path was provided for this run.
- Promotion remains false until the loader, prefix-cache, and context-routing
  live result artifacts all exist and pass.

## Proof

- `python3 scripts/qwen-multimodal-loader-harness-gate-proof.py`
- `python3 scripts/qwen-multimodal-live-result-gate-proof.py`
- `python3 scripts/qwen-multimodal-promotion-readiness-proof.py`
- `python3 scripts/gap-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/docs-inventory-parity-proof.py`
- `python3 scripts/coverage-false-flag-classification-proof.py`
- `python3 scripts/active-objective-audit-proof.py`
- `swift build --package-path ExploitBot -c debug`
