# Checkpoint 88 - Cache Stats State Proof

## Scope

- Make parsed engine cache runtime counters script-verifiable from the app, not
  only visible in Settings screenshots.

## Changes

- `/state.engineCacheStats` now exposes parsed `EngineCacheStats` values:
  TurboQuant enabled/encode-decode marker, hybrid layer counts, prompt L2
  counters, block L2 counters, SSM companion disk counters, and memory cache
  counters.
- Added `scripts/cache-stats-state-proof.py`.

## Proof

- `python3 scripts/cache-stats-state-proof.py`
- `swift build --package-path ExploitBot`
- `python3 scripts/visual-settings-proof.py`
- `python3 scripts/live-turn-harness.py`
- `python3 scripts/settings-apply-proof.py`
- `python3 scripts/request-audit-proof.py`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`

## Remaining

- Real-engine UI screenshot proof after loading an actual model remains a
  separate visual gate.
