# Beta Refresh Checkpoint 03 — 2026-05-21

## Scope

Third checkpoint toward the beta-refresh objective:

- Add a dependency-light engine metadata builder for effective runtime config.
- Expose selected/default reasoning parser and tool parser through API metadata.
- Expose generation defaults loaded from the model folder/CLI startup path.
- Expose prefix cache, paged cache, KV cache quantization, and L2 disk cache settings.

## Changed Engine Surface

- Added `vmlx_engine/runtime_status.py`
  - Builds API-safe `effective_config` metadata without importing FastAPI.
  - Reports model identity, parser choices, generation defaults, and cache settings.
- Updated `vmlx_engine/server.py`
  - Tracks the selected reasoning parser name after autodetect/explicit selection.
  - Adds `effective_config` to `/health`.
  - Adds matching `metadata` to `/v1/models` entries.
- Updated `vmlx_engine/api/models.py`
  - Adds optional `metadata` to `ModelInfo`.
- Added `ExploitBotEngine/testsuite/test_runtime_status.py`
  - Covers runtime metadata shape and parser-name fallback behavior.

## Verification

Passed:

```sh
python3 -m compileall -q ExploitBotEngine
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
git diff --check
```

The lightweight test environment does not currently have `pydantic`, so the
`ModelInfo` metadata construction test is skipped there. Full server import/API
smoke still requires the runtime dependency environment used by the app engine.

## Remaining

- Wire Swift engine status to display/inspect `effective_config`.
- Bring in the current vMLX cache implementation slices needed for MiniMax
  full KV cache, prefix cache, block/prompt L2 disk cache, and TurboQuant encode/decode.
- Bring in the Qwen hybrid SSM cache/rederive pieces and prove unsafe KV-only
  restores are rejected.
- Run real MiniMax JANGTQ and Qwen hybrid generation/cache smoke tests.
