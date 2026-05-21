# Beta Refresh Checkpoint 06 — 2026-05-21

## Scope

Sixth checkpoint toward the beta-refresh objective:

- Wire prompt L2 disk cache and block L2 disk cache flags through the full app
  launch path.
- Make the restored prompt L2 disk cache reachable from the Swift settings.
- Pass expected layer count into prompt L2 cache validation.

## Changed Surface

- Updated `ExploitBotEngine/launch.py`
  - Forwards `--enable-disk-cache`, `--disk-cache-dir`,
    `--disk-cache-max-gb`.
  - Forwards `--enable-block-disk-cache`, `--block-disk-cache-dir`,
    `--block-disk-cache-max-gb`.
- Updated `vmlx_engine/server.py`
  - Adds matching CLI flags.
  - Applies them to `SchedulerConfig`.
  - Scopes scheduler cache config with `model_path`.
- Updated `vmlx_engine/scheduler.py`
  - Passes `expected_num_layers` into `DiskCacheManager`.
- Updated Swift app config/settings persistence
  - Adds Prompt L2 Disk and Block L2 Disk toggles plus GB budgets.
  - Persists those settings in the local DB.

## Verification

Passed:

```sh
python3 -m compileall -q ExploitBotEngine
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
swift build
git diff --check
```

`swift build` still emits existing Swift 6 sendability warnings in agent
timeout/completion logging; this checkpoint did not introduce those paths.

## Remaining

- Compare and import the current vMLX scheduler/hybrid SSM changes needed for
  deferred SSM rederive and visible SSM companion stats.
- Run real MiniMax JANGTQ and Qwen hybrid smoke tests with cache hits before
  claiming the cache stack is production-ready.
