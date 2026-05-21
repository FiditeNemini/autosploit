# Beta Refresh Checkpoint 12 — 2026-05-21

## Scope

Twelfth checkpoint toward the beta-refresh objective:

- Tighten launch-time parser autodetection from the selected model folder.
- Prove configured tool parsers return OpenAI-compatible `tool_calls`.
- Keep current vMLX tool parser modules importable in lightweight Python
  environments used by the repo test suite.

## Changes

- `load_model_folder_defaults()` now consults the engine model config registry
  after `jang_config.json` capability fields, so `config.json.model_type` and
  nested `text_config.model_type` can supply parser defaults when the app/CLI
  leaves parsers on `auto`.
- `model_config_registry.lookup()` now falls back to direct `config.json` JSON
  loading when `mlx_lm.utils.load_config` is unavailable.
- Added postponed annotation imports to tool parser modules that use modern
  union type annotations, preserving importability under the lightweight system
  Python used by tests.
- Added tests covering:
  - Qwen parser defaults from a temporary `config.json`.
  - Tool parser registry coverage for current vMLX parsers.
  - Configured Qwen tool parser extraction into OpenAI-compatible `ToolCall`
    objects.

## Evidence

Passed:

```sh
python3 -m compileall -q ExploitBotEngine
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
PYTHONPATH=ExploitBotEngine /Applications/vMLX.app/Contents/Resources/bundled-python/python/bin/python3 -m unittest discover -s ExploitBotEngine/testsuite -v
scripts/smoke-engine-api.sh
swift build
git diff --check
```

System Python ran 16 tests with 2 expected skips for missing optional runtime
packages. Bundled Python ran all 16 tests successfully.
