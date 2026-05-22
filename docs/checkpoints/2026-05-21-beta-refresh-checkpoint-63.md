# Checkpoint 63 - Exploit Lifecycle State

## Changes

- Added `ExploitLifecycleItem` and `AppState.exploitLifecycle`.
- Exposed `exploitLifecycle` through the QA `/state` endpoint.
- Classified Exploit-tab `run_shell` actions into listener, custom script, and
  implant lifecycle lanes.
- Added Exploit lifecycle strips to Reverse Shells, Custom, and C2 subviews.
- Extended `scripts/live-turn-harness.py` with a long-running exploit listener
  proof that must move from running to canceled through `/stop`.

## Verified

- `python3 scripts/live-turn-harness.py`
- `swift build --package-path ExploitBot`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`

## Notes

- The live proof covers state and cancellation semantics. Visual screenshot
  proof for the Exploit lifecycle strips is still outstanding.
