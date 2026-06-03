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

## Local low-RAM model lane addendum

`scripts/runtime-local-model-lane-proof.py` now drives
`/qa/runtime-local-model-lane`. The route pins the active small local Qwen beta
target to `/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP` and reads the
release-app live artifact
`docs/live-proofs/2026-06-03-release-app-qwen-mxfp4-live.json`.

The route proves:

- Qwen release-app live chat returned `RELEASE-QWEN-OK`
- repeat prompt cache reuse surfaced cached tokens / scheduler hits
- active Qwen smoke memory stayed under the 20 GB low-RAM ceiling
- Qwen topology is `hybrid_ssm_attention` with TurboQuant q4 KV, prefix cache,
  paged cache, block L2, and SSM companion enabled
- Qwen continuous batching uses the same local model path and also stays under
  the 20 GB active-memory ceiling
- MiniMax small release lane remains tracked at
  `/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ`
- active beta families are Qwen/MiniMax only, with ZAYA excluded from active
  runtime artifacts

The route is mirrored into `/qa/runtime-coverage`,
`/qa/deep-runtime-flow-coverage`, and `/qa/coverage-index`.

## Streaming, parser, and Responses reuse addendum

`scripts/streaming-parser-reuse-proof.py` now verifies
`/qa/streaming-parser-reuse`. The route source-checks the Chat Completions SSE
path, ChatService handling for content, reasoning, tool-call, usage, and
cached-token deltas, the `/v1/responses` endpoint, Responses streaming events,
`previous_response_id` session reuse, per-request reasoning parser state, and
Qwen/MiniMax streaming tool parser files.

This gate is source/API-contract-backed. It does not replace the separate live
Qwen and MiniMax load/chat/cache artifacts, and it does not claim MiniMax live
multi-request batching.

## CVE import, include filter, and embedding addendum

`scripts/cve-import-embedding-coverage-proof.py` now drives
`/qa/cve-import-embedding-coverage`. The proof imports a mixed CVE list,
applies an `includeOnly` allowlist, verifies selected and excluded CVE IDs,
seeds semantic CVE embeddings through the fake test embedder, requests a
semantic CVE context packet, and checks that the route reports the
`search-on-demand-not-force-injected` context policy.

This makes the CVE import/filter/embedding flow visible in `/qa/coverage-index`
instead of leaving it split across the CVE settings and semantic CVE proofs.

## Prompt-injection boundary addendum

`scripts/context-prompt-injection-boundary-proof.py` now drives
`/qa/context-prompt-injection-boundary`. The route proves the app is using
bounded automatic context plus on-demand tools instead of force-injecting broad
CVE/stash/tool state into every prompt.

The proof checks:

- automatic context cap `4` and the active configured injected-context limit
- on-demand callback tools: `search_context`, `search_cve`, and `lookup_cve`
- stash/CVE retrieval via context delivery modes, not broad prompt stuffing
- per-turn tool schema cap `12` with the full agent registry kept separate
- `run_shell` visibility plus destructive-pattern blocklist samples
- streaming delta surfaces for content, reasoning, tool calls, and Responses
  `previous_response_id` reuse
- `/qa/deep-runtime-flow-coverage` and `/qa/coverage-index` mirrors

This is app-state/source-backed. It does not replace live Qwen/MiniMax model
chat or cache artifacts; it proves the prompt/context/tool boundary around
those runtime paths.

## Session, context, and cache lifecycle addendum

`scripts/session-context-cache-flow-proof.py` now drives
`/qa/session-context-cache-flow`. The route rolls up the app-visible lifecycle
for new-context behavior, context carrying, Responses session reuse, streaming
delta parsing, stash/CVE on-demand retrieval, parallel agent sessions,
continuous batching, and cache components.

The proof checks:

- flow rows for new-context cache preservation, `previous_response_id` reuse,
  bounded context compaction, stash/CVE retrieval, parallel sessions,
  continuous batching, streaming deltas, runtime cache components, and Qwen
  hybrid SSM async rederive
- `contextCarryMode = bounded-automatic-plus-on-demand-retrieval`
- `newContextCacheMode = clear-visible-chat-preserve-engine-cache-session`
- streaming delta surfaces for content, reasoning, tool calls, and cached-token
  usage telemetry
- cache components for prefix cache, prompt L2 disk, block L2 disk,
  TurboQuant KV, and SSM companion L2
- `/qa/deep-runtime-flow-coverage` and `/qa/coverage-index` mirrors

This is an app-state plus existing-live-artifact gate. It does not replace the
dedicated Qwen live batching proof, the dedicated CVE import/embedding proof, or
the still-pending MiniMax live batching stress proof.

## Cache artifact matrix addendum

`scripts/cache-artifact-matrix-proof.py` now drives
`/qa/cache-artifact-matrix`. The route reads existing live proof JSON artifacts
and exposes cache facts as row-level counters instead of only broad component
labels.

The matrix currently covers:

- Qwen release-app cross-restart cache hit evidence:
  `schedulerDiskHits >= 1`, `schedulerTokensSaved >= 1`,
  `blockL2DiskHits >= 1`, and `ssmDiskHits >= 1`
- block-L2 unit proof storage/read evidence:
  `disk_writes >= 2` and `disk_hits >= 2`
- Qwen hybrid SSM rederive evidence:
  requested, completed, no failures, and a positive `last_num_tokens`
- Qwen continuous-batching cache evidence:
  TurboQuant q4 KV, block-L2 disk writes, and SSM rederive completion
- MiniMax cache evidence:
  TurboQuant q4 KV and block-L2 disk writes

This route is mirrored through `/qa/runtime-coverage`,
`/qa/deep-runtime-flow-coverage`, and `/qa/coverage-index`. It distinguishes
storage/write proof from hit proof so a future agent does not overclaim cache
hits where the artifact only proves cache population.

## Objective runtime coverage addendum

`scripts/objective-runtime-coverage-proof.py` now drives
`/qa/objective-runtime-coverage`. The route aggregates the user's requested beta
readiness surface into one app-backed map: tool flow usage, runtime engines,
local Qwen/MiniMax lanes, context carry and compaction, prompt-injection
boundary, CVE import/embedding flow, stash retrieval, parallel sessions,
continuous batching, Responses reuse, streaming content/reasoning/tool-call
deltas, L2 disk cache, TurboQuant KV, hybrid SSM async rederive, proof ledgers,
and release package readiness.

This is an objective coverage map, not a completion claim. It currently reports
`objectiveComplete = false`, `objectiveStatus = covered-with-known-gaps`, 14
ready requirements, zero blocked requirements, and one tracked known-gap
requirement. At this checkpoint `cveDatabaseEmbeddings` is ready through the
proof-backed CVE import/embedding flow parity plus the dedicated seeded semantic
CVE proof, `l2DiskCacheStorageHit` is ready through the cache artifact matrix
contracts, and `qwenMultimodalRuntime` remains the tracked known gap in
`/qa/gap-ledger`.

The route is mirrored through the `releaseReadiness` group in
`/qa/coverage-index`, including ready count, blocked count, blocked IDs, known
gap IDs, contract parity, and proof-file parity.

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

## Context budget and compaction addendum

`/qa/context-budget-compaction` now records the context-management policy in one
app-backed surface:

- automatic injected context cap: `4`
- policy steps: `selectBoundedContext`, `compactCatalogSnippets`,
  `applyMaxTokenBudget`, `preserveCacheOnNewContext`,
  `reuseStashAndCVEOnDemand`
- compaction format: `single-line-snippet`
- cache response method: `prefix-cache-l2-turboquant`
- new context behavior: `clear-visible-chat-preserve-engine-cache-session`
- prompt-injection policy: `search-on-demand-not-force-injected`

The route mirrors retrieval sources and delivery modes from
`/qa/context-coverage`, cache session fields from `/qa/chat-coverage`, and is
rolled up through `/qa/deep-runtime-flow-coverage` plus `/qa/coverage-index`.

Verification after the contract update:

- `swift build --package-path ExploitBot -c debug`
- `python3 scripts/model-folder-warning-proof.py`
- `python3 scripts/unsupported-model-start-proof.py`
- `python3 scripts/runtime-coverage-proof.py`
- `python3 scripts/runtime-concurrency-stats-proof.py`
- `python3 scripts/runtime-continuous-batching-cli-proof.py`
- `EXPLOITBOT_LIVE_BATCH_QWEN_MODEL=/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP python3 scripts/prove-live-continuous-batching.py`
- `python3 scripts/continuous-batching-coverage-proof.py`
- `python3 scripts/context-budget-compaction-proof.py`
- `python3 scripts/context-coverage-proof.py`
- `python3 scripts/deep-runtime-flow-coverage-proof.py`
- `python3 scripts/settings-coverage-proof.py`
- `python3 scripts/gap-ledger-proof.py`
- `python3 scripts/objective-runtime-coverage-proof.py`
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
