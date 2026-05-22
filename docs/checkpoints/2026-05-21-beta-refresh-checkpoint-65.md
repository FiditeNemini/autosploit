# Checkpoint 65 - OSINT Lifecycle State

## Changes

- Added `OSINTLifecycleItem` and `AppState.osintLifecycle`.
- Exposed `osintLifecycle` through the QA `/state` endpoint.
- Classified OSINT actions into username, email, metadata, and screenshot
  lifecycle lanes.
- Added an OSINT lifecycle strip for the active search mode.
- Extended `scripts/live-turn-harness.py` with a long-running Sherlock-style
  proof that must move from running to canceled through `/stop`.

## Verified

- `python3 scripts/live-turn-harness.py`
- `swift build --package-path ExploitBot`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`

## Notes

- The live proof covers state and cancellation semantics. Screenshot artifact
  preview validation and visual screenshot proof are still outstanding.
