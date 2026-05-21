# Beta Refresh Checkpoint 05 — 2026-05-21

## Scope

Fifth checkpoint toward the beta-refresh objective:

- Replace the ExploitBot prompt disk cache stub with the current vMLX prompt
  L2 disk cache implementation.
- Bring the current vMLX TurboQuant-native disk serializer/deserializer.
- Bring the current vMLX cache-record validator used to reject malformed or
  stale safetensors cache records before tensor allocation.
- Add lightweight tests for prompt L2 initialization and TurboQuant cache
  detection.

## Changed Engine Surface

- Replaced `vmlx_engine/disk_cache.py`
  - SQLite index and background writer.
  - Prompt L2 fetch/store/stats/shutdown.
  - TQ-native store/hit counters.
  - Runtime fingerprint checks.
- Added `vmlx_engine/tq_disk_store.py`
  - Serializes compressed `TurboQuantKVCache` layers directly when available.
  - Deserializes TQ-native safetensors records for later recompression by the
    scheduler path.
- Added `vmlx_engine/cache_record_validator.py`
  - Rejects unsafe cache tensor shapes, oversized records, and bad TQ metadata.
- Added `ExploitBotEngine/testsuite/test_disk_cache_manager.py`.

## Verification

Passed:

```sh
python3 -m compileall -q ExploitBotEngine
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
git diff --check
```

This checkpoint restores the prompt L2 cache implementation, but does not yet
claim a real MiniMax/Qwen cache hit. The next cache slice still needs scheduler
integration review against current vMLX for TQ recompress/decompress behavior,
block L2 stats, and hybrid SSM companion/rederive handling.
