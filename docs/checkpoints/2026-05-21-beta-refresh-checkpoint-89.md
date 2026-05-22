# Checkpoint 89 - Model Folder Warning Proof

## Scope

- Make the Settings model-folder support warning script-verifiable for Qwen,
  MiniMax, and unsupported folders.

## Changes

- `/state.modelFolderInfo` now exposes `ModelFolderInspector` output:
  family, model type, support status, detected config files, support message,
  and config summary.
- Added QA route `/qa/model-folder` to select a model folder in proof scripts.
- Added `scripts/model-folder-warning-proof.py` with temporary Qwen, MiniMax,
  and unsupported fixtures.
- `scripts/live-turn-harness.py` now runs against an isolated temporary app data
  directory and waits for usage metrics before asserting them.
- Tool cancellation now marks `ToolExecutor` idle immediately after terminating
  the running process, so the UI/status proof does not remain stuck while the
  process exit is being collected.

## Proof

- `python3 scripts/model-folder-warning-proof.py`
- `swift build --package-path ExploitBot`
- `python3 scripts/cache-stats-state-proof.py`
- `python3 scripts/settings-apply-proof.py`
- `python3 scripts/live-turn-harness.py`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`

## Remaining

- Live unsupported-folder UI screenshot and start-blocking behavior can be
  tightened further, but the warning state is now directly testable.
