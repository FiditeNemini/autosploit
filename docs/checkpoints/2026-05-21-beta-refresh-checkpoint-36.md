# Beta Refresh Checkpoint 36

Date: 2026-05-21

## Scope

- Added explicit cache topology metadata to the engine effective runtime config.
- Marked Qwen3-next as `hybrid_ssm_attention` with SSM companion cache requirements.
- Marked MiniMax as `full_kv_attention` without SSM companion requirements.
- Exposed active topology components and cache warnings through `/health` and `/v1/models`.
- Parsed and displayed the effective topology in Swift Settings.

## Files

- `ExploitBotEngine/vmlx_engine/model_configs.py`
- `ExploitBotEngine/vmlx_engine/runtime_status.py`
- `ExploitBotEngine/testsuite/test_runtime_status.py`
- `ExploitBotEngine/testsuite/test_reasoning_registry.py`
- `ExploitBot/Sources/ExploitBot/Services/EngineManager.swift`
- `ExploitBot/Sources/ExploitBot/Views/Settings/SettingsView.swift`

## Verification

- `PYTHONPATH=. uv run --extra dev pytest -q`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Result

- Engine: `22 passed, 3 warnings`
- Swift app: build passed

## Notes

- This is metadata/proof-surface work, not a live MiniMax or Qwen generation proof.
- The topology object gives the app and future tests a stable place to distinguish full-KV MiniMax paths from hybrid SSM/Qwen paths and to surface unsafe cache combinations.
