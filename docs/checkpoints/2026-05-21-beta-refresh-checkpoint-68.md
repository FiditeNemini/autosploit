# Checkpoint 68 - Qwen/MiniMax Model Verification Script

## Changes

- Added `scripts/verify-live-models.py`.
- Added `ExploitBotEngine/testsuite/test_live_model_verifier.py`.
- The verifier checks Qwen, MiniMax, and unsupported model folders.
- Metadata/dry-run mode proves model-family detection and launcher arguments for:
  - model-folder generation defaults;
  - auto reasoning and tool parsers;
  - prefix cache;
  - prompt L2 disk cache;
  - paged cache;
  - block L2 disk cache;
  - TurboQuant Q4 KV cache.
- Live mode can launch the embedded engine and verify `/health`, `/v1/models`,
  `/v1/chat/completions`, and `/v1/cache/stats`.

## Verified

- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q testsuite/test_live_model_verifier.py`
- `python3 scripts/verify-live-models.py --metadata-only --qwen /Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP --minimax /Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ --unsupported /Users/eric/models/mlx-community/gemma-3n-E2B-it-4bit --output /tmp/exploitbot-model-verifier-metadata.json`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `swift build --package-path ExploitBot`
- `python3 scripts/live-turn-harness.py`
- `python3 scripts/context-catalog-proof.py`
- `python3 scripts/settings-apply-proof.py`
- `git diff --check`

## Notes

- The metadata run did not load the real large models. To run the expensive live
  proof, remove `--metadata-only` from the verifier command and keep the output
  report as evidence.
