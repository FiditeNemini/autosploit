# Beta Refresh Checkpoint 02 — 2026-05-21

## Scope

Second checkpoint toward the beta-refresh objective:

- Import missing current vMLX reasoning parser support for MiniMax M2 and Gemma4.
- Register those parsers in the embedded Python engine.
- Make MiniMax model config autodetect use the MiniMax-specific reasoning parser instead of generic Qwen3.
- Keep reasoning parser modules importable on the system Python used by the current local launcher.

## Changed Engine Surface

- Added `vmlx_engine/reasoning/minimax_m2_parser.py`
- Added `vmlx_engine/reasoning/gemma4_parser.py`
- Updated `vmlx_engine/reasoning/__init__.py`
- Updated `vmlx_engine/model_configs.py`
- Added parser registry tests in `ExploitBotEngine/testsuite/test_reasoning_registry.py`

## Verification

Passed:

```sh
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
python3 -m compileall -q ExploitBotEngine
swift build
git diff --check
```

This is still parser-surface work only. Full `/health` exposure, effective parser reporting through `/v1/models`, and real MiniMax/Qwen generation smoke tests remain open.
