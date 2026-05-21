# Beta Refresh Checkpoint 26 — 2026-05-21

## Scope

Twenty-sixth checkpoint toward the beta-refresh objective:

- Surface live cache diagnostics from the Python engine in the Swift app.
- Make TurboQuant, L2 disk cache, SSM companion, and memory stats visible in
  Settings during real engine runs.

## Changes

- Added `EngineCacheStats` parsing for `/v1/cache/stats`, including:
  - TurboQuant enabled state, make-cache wrapper, and hybrid policy;
  - hybrid TurboQuant attention/companion layer counts;
  - prompt L2 entries/hits/misses;
  - block L2 blocks/hits/misses;
  - SSM companion entries, max entries, and disk L2 state;
  - active/cache memory MB.
- `EngineManager` now fetches cache stats immediately after the engine reports
  ready, and refreshes them during the existing health monitor loop.
- Settings now shows a selectable `Cache Runtime` diagnostics panel below the
  existing effective runtime summary.

## Evidence

Passed:

```sh
swift build --package-path ExploitBot
git diff --check
```

## Remaining Proof Gap

This checkpoint proves Swift build integration and UI plumbing. It does not
prove real TurboQuant encode/decode or live cache hit behavior; that still
requires starting a model-backed engine and observing `/v1/cache/stats` during
generation once a safe memory slot is available.
