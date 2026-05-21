# Beta Refresh Checkpoint 45

Date: 2026-05-21

## Scope

- Extended model-folder generation defaults beyond sampling fields to cover thinking/template behavior.
- `jang_config.json` generation defaults can now supply `enable_thinking` and `chat_template_kwargs`.
- The launcher now passes model-derived `--default-enable-thinking` instead of hardcoding thinking on for every model.
- The launcher now forwards model-derived `--chat-template-kwargs` to the server with provenance in `effective_config.sources.generation`.
- The direct server entrypoint now accepts `--chat-template-kwargs` and applies it to server-wide chat template defaults.
- Extracted server default application into `apply_server_defaults_from_args` so template kwargs and thinking defaults are testable.

## Files

- `ExploitBotEngine/launch.py`
- `ExploitBotEngine/vmlx_engine/server.py`
- `ExploitBotEngine/testsuite/test_launch_model_defaults.py`
- `ExploitBotEngine/testsuite/test_server_cache_defaults.py`
- `docs/engine-migration-prep-2026-05-21.md`

## Verification

- `PYTHONPATH=. uv run --extra dev pytest -q`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Result

- Engine: `31 passed, 3 warnings`.
- Swift app: build passed.
- Whitespace gate passed.

## Notes

- This closes a model-default gap for Qwen/JANG-style reasoning controls where a selected model folder needs to disable or parameterize thinking through template kwargs.
