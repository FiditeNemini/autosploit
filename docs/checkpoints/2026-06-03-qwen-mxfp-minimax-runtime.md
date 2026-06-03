# 2026-06-03 Qwen MXFP MTP and MiniMax Runtime Checkpoint

This checkpoint records the current runtime proof lane after narrowing the beta
focus back to Qwen MXFP MTP and MiniMax text. ZAYA and visual-model work are not
part of this checkpoint.

## Scope

- Qwen target: `/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP`.
- MiniMax low-RAM live target: `/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ`.
- MiniMax full JANG artifact inspected without live load:
  `/Users/eric/models/dealign.ai/MiniMax-M2.7-JANG_K-CRACK`.

## Proof artifacts

- `docs/live-proofs/2026-06-03-qwen-mxfp4-current-metadata.json`
- `docs/live-proofs/2026-06-03-release-app-qwen-mxfp4-live.json`
- `docs/live-proofs/2026-06-03-qwen-mxfp4-mtp-block-l2-ssm-live.json`
- `docs/live-proofs/checkpoint-452-qwen-continuous-batching-live.json`
- `docs/live-proofs/2026-06-03-minimax-current-metadata.json`
- `docs/live-proofs/2026-06-03-release-app-minimax-live.json`
- `docs/live-proofs/2026-06-03-minimax-jang-k-current-metadata.json`

## Qwen MXFP4-MTP status

The release app proof loaded `Qwen3.6-27B-MXFP4-MTP` through
`release/ExploitBot.app`, selected the bundled vMLX Python runtime, and returned
`RELEASE-QWEN-OK` for both first and repeated chat requests.

The stronger direct-engine restart proof used a long agent-context prompt with
prompt L2 disabled on replay. It recorded:

- `block_l2_hits_delta: 3`
- `cached_tokens: 156`
- `scheduler_disk_hits_delta: 3`
- `scheduler_tokens_saved_delta: 156`
- `ssm_l2_hits_delta: 1`
- `ssm_companion_hit_checks.disk_hit: true`
- `ssm_companion_hit_checks.no_rederive: true`

This proves the Qwen MXFP4-MTP hybrid SSM attention lane can load, chat, use the
Qwen parser defaults, and restore block L2 plus SSM companion L2 state for the
bounded prompt shape exercised here.

## Qwen live continuous batching addendum

`scripts/prove-live-continuous-batching.py` live-loaded
`/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP` through
`ExploitBotEngine/launch.py` with `--max-num-seqs 2`, TurboQuant q4 KV, prefix
cache, paged cache, block L2 disk cache, and hybrid SSM companion enabled. It
sent two concurrent non-streaming chat completions and recorded:

- `clientOverlap: true`
- `max_running_observed: 2`
- `max_waiting_observed: 2`
- `num_requests_processed: 2`
- `kv_cache_quantization.bits: 4`
- `block_disk_cache.disk_writes: 2`
- `ssm_companion.rederive.completed: 2`
- `ssm_companion.rederive.failed: 0`
- `memory.active_mb: 14221.2`

The QA surface now exposes this as
`/qa/continuous-batching-coverage.proofLevel =
source-and-live-qwen-stress-backed` and mirrors the live artifact through
`/qa/runtime-coverage`, `/qa/deep-runtime-flow-coverage`, and
`/qa/coverage-index`. This is a Qwen live batching proof only; MiniMax
multi-request live batching remains a separate not-yet-run stress proof.

## MiniMax status

The release app proof loaded `/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ`
through the bundled vMLX Python runtime. Runtime health reported full-KV
attention, MiniMax parser defaults, TurboQuant q4 KV cache, prefix cache, paged
cache, and block L2 enabled. The repeated no-thinking request recorded:

- `schedulerCacheHitsDelta: 1`
- `schedulerHitsDelta: 1`
- `schedulerTokensSavedDelta: 46`
- `secondCachedTokens: 46`

This is a valid MiniMax load/cache/parser proof for the smaller local target. It
is not a broad chat-quality pass: the saved previews show the model repeating or
analyzing the prompt instead of cleanly following the brief-answer instruction.

`/Users/eric/models/dealign.ai/MiniMax-M2.7-JANG_K-CRACK` was inspected with
`--metadata-only`. The artifact is present, supported as `minimax_m2`, has
`jang_config`, uses full KV cache, and selects the MiniMax tool parser. It was
not live-loaded in this pass because the folder is about 80 GB and the user asked
to avoid unnecessary RAM pressure.

## Current beta interpretation

- Qwen MXFP4-MTP is the strongest current model lane: live release-app chat plus
  direct restart replay proof covers hybrid SSM cache reuse.
- MiniMax is partially proven: the smaller MiniMax text target loads and caches
  correctly in the release app, but instruction-following quality needs a real
  prompt-suite pass before calling it polished.
- Qwen continuous batching is now live-model proven for the two-request low-RAM
  gate above. MiniMax continuous batching is not live-model proven yet.
- Full MiniMax JANG_K is artifact/metadata proven only at this checkpoint; it
  still needs a live load/chat/cache pass on a quiet machine.
- The live `exploit.bot` website copy was updated after this scope correction:
  stale visual-lane public copy was replaced with Qwen MXFP4-MTP and MiniMax
  JANG_K scope language.

## App supported-family contract

The app and QA routes now expose only `qwen` and `minimax` as active beta
families. `ModelFolderInspector` treats ZAYA-shaped folders as unsupported, and
`unsupported-model-start-proof.py` verifies that both generic unsupported and
ZAYA-shaped folders are blocked before engine launch.

Verification after the contract update:

- `swift build --package-path ExploitBot -c debug`
- `python3 scripts/model-folder-warning-proof.py`
- `python3 scripts/unsupported-model-start-proof.py`
- `python3 scripts/runtime-coverage-proof.py`
- `python3 scripts/runtime-concurrency-stats-proof.py`
- `python3 scripts/runtime-continuous-batching-cli-proof.py`
- `EXPLOITBOT_LIVE_BATCH_QWEN_MODEL=/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP python3 scripts/prove-live-continuous-batching.py`
- `python3 scripts/continuous-batching-coverage-proof.py`
- `python3 scripts/deep-runtime-flow-coverage-proof.py`
- `python3 scripts/settings-coverage-proof.py`
- `python3 scripts/gap-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

Post-push release-readiness rerun:

- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/release-readiness-proof.py`
- `python3 scripts/beta-readiness-coverage-proof.py`

`release-readiness-proof.py` rebuilt and re-signed the ignored local
`release/ExploitBot.app` and `release/ExploitBot-beta.dmg`; both passed
`codesign --verify` after the rebuild. The first beta-readiness rerun failed
against the stale unsigned local release app, and the rerun passed after the
release-readiness rebuild refreshed those ignored artifacts.
