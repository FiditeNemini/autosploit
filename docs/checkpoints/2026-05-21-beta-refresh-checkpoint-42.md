# Beta Refresh Checkpoint 42

Date: 2026-05-21

## Scope

- Added centralized KV cache quantization mode normalization.
- Accepted `turboquant-q4`, `turboquant-q8`, `tq-q4`, and `tq-q8` through launcher/server/CLI paths.
- Fixed scheduler bit mapping so `turboquant-q4` maps to 4-bit instead of falling through to 8-bit.
- Added TurboQuant Q4/Q8 options to Settings so the app can launch the intended TurboQuant KV cache path.
- Kept legacy `q4`/`q8` options available as mlx-lm KV quantization modes.

## Files

- `ExploitBotEngine/vmlx_engine/kv_quantization.py`
- `ExploitBotEngine/vmlx_engine/scheduler.py`
- `ExploitBotEngine/vmlx_engine/mllm_scheduler.py`
- `ExploitBotEngine/vmlx_engine/server.py`
- `ExploitBotEngine/vmlx_engine/cli.py`
- `ExploitBotEngine/launch.py`
- `ExploitBotEngine/testsuite/test_kv_quantization_modes.py`
- `ExploitBotEngine/testsuite/test_launch_model_defaults.py`
- `ExploitBot/Sources/ExploitBot/Views/Settings/SettingsView.swift`

## Verification

- `PYTHONPATH=. uv run --extra dev pytest -q`
- `swift build --package-path ExploitBot`
- `python3 -m compileall -q ExploitBotEngine/vmlx_engine/kv_quantization.py ExploitBotEngine/launch.py`

## Result

- Engine: `27 passed, 3 warnings`.
- Swift app: build passed.
- Python compile check passed.

## Notes

- This does not claim a live MiniMax/Qwen TurboQuant generation proof.
- It removes a real launch-path blocker where TurboQuant modes could be shown in metadata/tests but were not accepted consistently by executable CLI paths.
