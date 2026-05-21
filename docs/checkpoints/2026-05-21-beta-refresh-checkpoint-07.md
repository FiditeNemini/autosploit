# Beta Refresh Checkpoint 07 — 2026-05-21

## Scope

Seventh checkpoint toward the beta-refresh objective:

- Bring the current vMLX standalone hybrid SSM companion cache modules into
  ExploitBot.
- Add the current Qwen hybrid TurboQuant policy helper.
- Wire the LLM scheduler to the standalone SSM companion cache.
- Attach SSM companion L2 disk storage beside block L2 disk cache.
- Surface SSM companion cache stats through scheduler cache stats.
- Keep utility imports compatible with the Python 3.9 test environment.

## Changed Engine Surface

- Added `vmlx_engine/utils/ssm_companion_cache.py`
  - Model-scoped SSM companion keys.
  - Deep-copy fetch/store behavior.
  - Optional max-bytes cap.
  - Optional disk-store attachment.
- Added `vmlx_engine/utils/ssm_companion_disk_store.py`
  - Filesystem-backed L2 for SSM companion state.
- Added `vmlx_engine/utils/hybrid_tq_cache.py`
  - Qwen hybrid TurboQuant policy helpers.
- Updated `vmlx_engine/scheduler.py`
  - Uses standalone `HybridSSMStateCache`.
  - Handles new `(states, is_complete)` fetch return shape.
  - Treats incomplete/missing SSM companion state as a safe full-prefill miss.
  - Attaches SSM companion disk store when block L2 is enabled.
  - Reports `ssm_companion_cache` stats.
- Updated `vmlx_engine/utils/tokenizer.py`
  - Adds future annotations for Python 3.9 import compatibility.
- Added `ExploitBotEngine/testsuite/test_hybrid_ssm_helpers.py`.

## Verification

Passed:

```sh
python3 -m compileall -q ExploitBotEngine
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
swift build
git diff --check
```

This checkpoint improves the LLM scheduler path and exposes SSM companion
telemetry. It does not yet claim full Qwen hybrid correctness: real model
smoke still needs to prove cold prefill, warm hit, missing-companion rejection,
and deferred rederive behavior against an actual hybrid model.
