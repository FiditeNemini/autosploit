# Beta Refresh Checkpoint 10 — 2026-05-21

## Scope

Tenth checkpoint toward the beta-refresh objective:

- Add a repeatable no-model API smoke for the embedded Python engine.
- Verify the full FastAPI runtime surface with the bundled vMLX Python
  environment instead of only the lightweight system Python tests.
- Record why real Qwen/MiniMax model cache proof was not launched in this pass.

## Added Tooling

- Added `scripts/smoke-engine-api.sh`
  - Uses the bundled vMLX Python by default.
  - Starts `vmlx_engine.server:app` on `127.0.0.1:${PORT:-8130}`.
  - Verifies:
    - `/health` returns `status=no_model`.
    - `/health.effective_config.cache` includes `prefix_cache`,
      `paged_cache`, `kv_cache_quantization`, `disk_cache`, and
      `ssm_companion`.
    - `/v1/cache/stats` returns memory diagnostics.
    - `/v1/models` returns OpenAI-compatible list shape.
  - Cleans up the smoke server on exit.

## Evidence

Passed:

```sh
PYTHON_BIN=/Applications/vMLX.app/Contents/Resources/bundled-python/python/bin/python3 PORT=8130 scripts/smoke-engine-api.sh
```

Output:

```text
health.status=no_model
effective.cache.keys=disk_cache,kv_cache_quantization,paged_cache,prefix_cache,ssm_companion
cache.keys=memory
models.count=0
```

Also passed:

```sh
swift build
python3 -m compileall -q ExploitBotEngine
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
PYTHONPATH=ExploitBotEngine /Applications/vMLX.app/Contents/Resources/bundled-python/python/bin/python3 -m unittest discover -s ExploitBotEngine/testsuite -v
git diff --check
```

## Real Model Proof Status

Real Qwen/MiniMax generation/cache proof remains open. The machine currently
has an external `/Applications/vMLX.app` process serving
`/Users/eric/models/JANGQ/DeepSeek-V4-Flash-JANG` on port `8005`, and memory
inspection showed very high wired memory. The smallest relevant local targets
found were still large:

- `/Users/eric/models/dealign.ai/Nemotron-Omni-Nano-JANGTQ-CRACK` — 12 GB
- `/Users/eric/models/OsaurusAI/Qwen3.6-35B-A3B-mxfp4` — 18 GB
- `/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ` — 37 GB

Do not claim full MiniMax/Qwen cache correctness until a cold/warm real-model
smoke proves generation, cache hit reporting, TurboQuant encode/decode, and
hybrid SSM companion behavior.
