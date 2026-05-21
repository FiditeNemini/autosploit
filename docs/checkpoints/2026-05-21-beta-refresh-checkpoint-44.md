# Beta Refresh Checkpoint 44

Date: 2026-05-21

## Scope

- Aligned the direct `python -m vmlx_engine.server` cache defaults with the app launcher.
- Defaulted the server module to prompt L2, paged cache, and Block L2 enabled.
- Extracted server cache flag translation into `build_scheduler_config_from_args` so the direct-server scheduler topology is testable.
- Added a server cache default regression covering paged cache, prompt L2, and Block L2 scheduler config.

## Files

- `ExploitBotEngine/vmlx_engine/server.py`
- `ExploitBotEngine/testsuite/test_server_cache_defaults.py`
- `docs/engine-migration-prep-2026-05-21.md`

## Verification

- `PYTHONPATH=. uv run --extra dev pytest -q`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Result

- Engine: `29 passed, 3 warnings`.
- Swift app: build passed.
- Whitespace gate passed.

## Notes

- This keeps the app launcher and direct server entrypoint on the same default cache topology. The console `vmlx-engine serve` parser still has its own boolean flags and can be handled separately if we decide to change that public CLI contract.
