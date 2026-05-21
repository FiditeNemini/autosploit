# Beta Refresh Checkpoint 43

Date: 2026-05-21

## Scope

- Aligned the default cache topology so Block L2 starts with paged cache enabled in both the Python launcher and the Swift Settings surface.
- Changed `launch.py` direct-launch defaults to emit `--use-paged-cache true` with the default 64-token page size when Block L2 is enabled.
- Kept explicit `use_paged_cache=False` override behavior available for tests or manual launches.
- Added Settings copy that labels paged cache as required for Block L2 reuse and hybrid SSM cache topology.
- Added a launcher regression test covering the default paged + Block L2 topology.

## Files

- `ExploitBotEngine/launch.py`
- `ExploitBotEngine/testsuite/test_launch_model_defaults.py`
- `ExploitBot/Sources/ExploitBot/Views/Settings/SettingsView.swift`

## Verification

- `PYTHONPATH=. uv run --extra dev pytest -q`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Result

- Engine: `28 passed, 3 warnings`.
- Swift app: build passed.
- Whitespace gate passed.

## Notes

- This checkpoint does not prove live Qwen hybrid SSM or MiniMax generation. It closes the default-launch mismatch that could leave Block L2 configured while paged cache was absent.
