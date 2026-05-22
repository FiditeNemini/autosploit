# Checkpoint 113: Qwen Hybrid Full Prefix Skip Proof

## Scope

- Fix text scheduler prefix-cache lookup keys so they match the store path when
  chat templates append assistant-generation prompt tokens.
- Prove a full Qwen hybrid prefix skip with prompt L2 disabled, block L2 replay,
  and a matching SSM companion L2 hit.

## Changes

- Added `_prefix_cache_lookup_tokens()` in `vmlx_engine.scheduler`.
- The text scheduler now strips `_gen_prompt_len` before block-aware prefix
  cache, memory-aware cache, legacy prefix cache, and prompt disk L2 lookup.
- Added verifier support for `--require-ssm-companion-hit`.
- Added focused tests for:
  - scheduler prefix-cache key normalization;
  - SSM companion L2 hit proof;
  - rejecting rederive fallback when a full companion hit is required.

## Proof

Commands:

```bash
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q testsuite/test_live_model_verifier.py testsuite/test_hybrid_ssm_helpers.py
python3 scripts/verify-live-models.py --qwen /Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP --block-l2-only-replay --require-ssm-companion-hit --timeout 1200 --prompt 'ExploitBot Qwen hybrid full prefix skip proof. This prompt is intentionally long enough to create a full paged prefix cache block and a matching hybrid SSM companion checkpoint before generation. Repeatable context segment alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega. The replay process must disable prompt disk cache and recover cached prefix state from block disk cache plus the matching SSM companion without rederive fallback. Reply with cache-proof and one short sentence.' --output docs/live-proofs/checkpoint-113-qwen-hybrid-full-prefix-skip-live.json
```

Result:

- Focused verifier/helper tests passed: `26 passed`.
- Live proof loaded
  `/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP` twice.
- Replay process had `prompt_l2_active=false`.
- Replay request reported:
  - `block_l2_hits_delta=2`;
  - `scheduler_disk_hits_delta=2`;
  - `scheduler_tokens_saved_delta=112`;
  - `prompt_l2_hits_delta=0`;
  - `ssm_l2_hits_delta=1`;
  - `prompt_tokens_details.cached_tokens=112`.
- SSM companion proof reported:
  - `disk_hit=true`;
  - `disk_hits=1`;
  - `no_rederive=true`;
  - `no_failures=true`.
- Engine log shows `hybrid paged HIT - 112 tokens (KV + 48 SSM layers)`.

Artifact:

- `docs/live-proofs/checkpoint-113-qwen-hybrid-full-prefix-skip-live.json`

## Boundary

This proves the full Qwen hybrid prefix skip path for the local
`Qwen3.6-27B-MXFP4-MTP` model under a repeated prompt where the replayed KV
prefix and SSM companion checkpoint match. It does not prove every possible
hybrid prompt shape or multimodal path.
