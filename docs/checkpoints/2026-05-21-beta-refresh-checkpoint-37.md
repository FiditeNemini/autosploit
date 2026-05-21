# Beta Refresh Checkpoint 37

Date: 2026-05-21

## Scope

- Added explicit regression coverage for Qwen hybrid SSM topology warnings when prefix/L2 cache options require paged cache.
- Added explicit regression coverage that MiniMax full-KV topology stays warning-free when paged block L2 is active.
- Surfaced cache topology warnings as their own selectable row in the Settings effective runtime panel.
- Enabled text selection on runtime config cells so parser, generation, topology, and cache metadata can be copied directly from Settings.

## Files

- `ExploitBotEngine/testsuite/test_runtime_status.py`
- `ExploitBot/Sources/ExploitBot/Views/Settings/SettingsView.swift`

## Verification

- `swift build --package-path ExploitBot`
- `PYTHONPATH=. uv run --extra dev pytest -q`

## Result

- Engine: `24 passed, 3 warnings`
- Swift app: build passed

## Notes

- This checkpoint makes the existing topology policy more auditable from the app and locks the warning behavior down with tests.
- This is not a live MiniMax or Qwen generation/cache proof.
