# Beta Refresh Checkpoint 33

Date: 2026-05-21

## Scope

- Added explicit model registry metadata to the engine effective runtime config:
  - model family
  - model cache type
  - architecture hints
- Propagated the metadata through `/health` and `/v1/models`.
- Added Swift parsing and Settings display for family/cache topology.
- Fixed a leaking model registry test monkeypatch so parser/cache-family tests use isolated state.

## Files

- `ExploitBotEngine/vmlx_engine/runtime_status.py`
- `ExploitBotEngine/vmlx_engine/server.py`
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

- This makes cache-family claims inspectable without name guessing. MiniMax-style KV and Qwen hybrid/Mamba-family paths can now be surfaced directly from registry metadata in the app.
