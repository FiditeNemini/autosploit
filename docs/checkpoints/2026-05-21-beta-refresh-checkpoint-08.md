# Beta Refresh Checkpoint 08 — 2026-05-21

## Scope

Eighth checkpoint toward the beta-refresh objective:

- Add SSM companion configuration to `/health.effective_config`.
- Return richer SSM companion stats from `/v1/cache/stats`.
- Display SSM companion status in the Settings live runtime summary.

## Changed Surface

- Updated `vmlx_engine/runtime_status.py`
  - Adds `cache.ssm_companion` with enabled state, max entries, max MB, and
    disk L2 enabled state.
- Updated `vmlx_engine/server.py`
  - Uses scheduler `_get_ssm_cache_stats()` when available for `/v1/cache/stats`.
  - Falls back to the older entry-count shape for older batch generators.
- Updated Swift runtime parsing and Settings summary
  - Parses SSM companion fields from `effective_config`.
  - Shows an `SSM` runtime tile with entry budget and L2 status.

## Verification

Passed:

```sh
python3 -m compileall -q ExploitBotEngine
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
swift build
git diff --check
```

`swift build` still reports the existing Swift 6 sendability warnings in
agent logging paths. No real-model cache proof is claimed here; this checkpoint
only improves visibility needed for that proof.
