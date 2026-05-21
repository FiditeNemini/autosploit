# Beta Refresh Checkpoint 13 — 2026-05-21

## Scope

Thirteenth checkpoint toward the beta-refresh objective:

- Broaden model-folder generation defaults beyond temperature/top-p/max tokens.
- Apply defaults consistently across chat, text completions, Anthropic adapter,
  Ollama adapter, and Responses API paths.
- Preserve per-request override behavior.

## Changes

- `generation_config.json` / JANG generation fields now feed:
  - `temperature`
  - `top_p`
  - `top_k`
  - `min_p`
  - `repetition_penalty`
  - `stop` / `stop_sequences` / `stop_strings`
  - `max_new_tokens` / `max_tokens` / `max_output_tokens`
- `launch.py` forwards those defaults to the embedded server through explicit
  `--default-*` flags.
- `server.py` now stores server-wide defaults for `top_k`, `min_p`,
  `repetition_penalty`, and stop sequences, then applies them only when a
  request omits that field.
- `/health.effective_config` and `/v1/models` metadata now include the broader
  effective generation summary.
- Added tests proving folder defaults are forwarded, request values override
  folder defaults, effective runtime metadata includes the values, and server
  request-merge behavior preserves override priority.

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

System Python ran 17 tests with 3 expected skips for optional runtime packages.
Bundled Python ran all 17 tests successfully.
