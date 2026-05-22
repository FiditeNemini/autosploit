# Checkpoint 73 - Settings Visual Proof

## Changes

- Added `scripts/visual-settings-proof.py`.
- Added QA routes:
  - `/qa/seed-settings-visual-state`
  - `/qa/settings-category`
- Added QA-only Settings category forcing.
- Seeded Settings with:
  - unsupported Gemma model folder warning;
  - running engine status;
  - effective Qwen hybrid runtime metadata;
  - Qwen parser/tool parser sources;
  - prefix cache, paged cache, Prompt L2, Block L2, SSM companion state, and
    TurboQuant Q4 cache details.

## Artifacts

- `docs/visual-proofs/checkpoint-73/settings-model-warning.png`
- `docs/visual-proofs/checkpoint-73/settings-engine-cache-status.png`
- `docs/visual-proofs/checkpoint-73/settings-cache-topology.png`
- `docs/visual-proofs/checkpoint-73/manifest.json`

## Verified

- Red first: `python3 scripts/visual-settings-proof.py` failed on missing
  `/qa/seed-settings-visual-state`.
- Green: `python3 scripts/visual-settings-proof.py`
- Visual inspection of all three checkpoint-73 screenshots.

## Notes

- This checkpoint proves seeded Settings warning/cache visual states. Real
  Qwen/MiniMax load and live cache metrics remain separate proof gates.
