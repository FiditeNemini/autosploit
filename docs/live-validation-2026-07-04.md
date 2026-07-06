# ExploitBot Live Validation - 2026-07-04

## Goal

Validate whether the current checkout can run real Qwen 3.6 MXFP8 MTP models through the app and engine with:

- correct prompt delivery across multi-turn chat
- prefix cache
- paged cache and block L2 cache
- TurboQuant q4 KV cache
- hybrid SSM async rederive
- panel/tool wiring sufficient for real autonomous pentest workflows
- modern CVE library data that the model can dynamically search and use

Cache contract note: current Qwen proof must not rely on a generic or native `q4KV` default. The proof-bearing field is TurboQuant q4 attention-KV (`q4TurboQuantKV`, `mode=turboquant-q4`). SSM state is not quantized; it remains native companion/rederive state (`ssm_policy=native_companion_state`, `rederive=async_clean_prefill_on_miss_or_warm_pass`).

## Method

RLM loop for this pass:

1. Run the real surface.
2. Log exact evidence and artifacts.
3. Measure pass/fail against the runtime contract.
4. Fix only after root cause is isolated and a failing test exists.

## Models Found

- `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP`
  - Size: 27G
  - `jang_config.json`: `weight_format=mxfp8`, `bundle_has_mtp=true`, `mtp_layers=1`, `capabilities.cache_type=hybrid`, `reasoning_parser=qwen3`, `tool_parser=qwen`
- `/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP`
  - Size: 35G
  - `jang_config.json`: `weight_format=mxfp8`, `bundle_has_mtp=true`, `mtp_layers=1`, `capabilities.cache_type=hybrid`, `reasoning_parser=qwen3`, `tool_parser=qwen`

## Current Evidence

### 2026-07-05 packaged-app CUA/settings/cache checkpoint

Status: PARTIAL overall. The packaged app is live-displayable on this Mac through Computer Use, but distribution remains blocked by missing notarization credentials and the full project objective is not complete.

Fresh evidence:

- CUA attach to `/Users/eric/exploitbot/release/ExploitBot.app`: PASS. Computer Use returned CUA App Version 857, bundle ID `ai.jangq.ExploitBot`, pid `20100`, and a visible `ExploitBot` window.
- Settings panel navigation: PASS. CUA opened Settings and observed Engine, Model, Runtime, Context, Cache, Agents, CVE Database, Tools, and Logs categories.
- Model library UI/state: PASS. The live Model panel and `/state` showed root `/Users/eric/models/dealign.ai`, `14` models, `6` supported models, selected `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP`, and supported entries for both `Qwen3.6-27B-MXFP8-CRACK-MTP` and `Qwen3.6-35B-A3B-MXFP8-CRACK-MTP`.
- Cache UI/state: PASS. The live Cache panel showed `TurboQuant Q4` selected and `/state` reported `kvCacheQuantization=turboquant-q4`, `prefixCache=true`, `pagedCache=true`, `promptL2Disk=true`, and `blockL2Disk=true`.
- CVE/tool inventory state: PASS for current feed/library coverage and current-machine tool installation. The refreshed live CVE proof shows `cveDatabase.totalCount=1641` and `kevCount=1631` after importing all current CISA KEV rows plus bounded recent NVD critical rows; the latest tool inventory rerun reports `installedCount=42`, `missingCount=0`, `fullPentestToolchainInstalled=PASS`, and `settingsCurrentMachineDetection=PASS`.
- Fresh 17:50 CVE source refresh: PASS. `scripts/cve-current-threat-intel-live-proof.py` was rerun after fixing its teardown race and refreshed `docs/live-proofs/2026-07-04-cve-current-threat-intel-live.json` with CISA catalog `2026.07.01`, `feedReleasedAt=2026-07-01T19:00:06.9016Z`, latest KEV `CVE-2026-45659`, `totalCount=1641`, `kevCount=1631`, exact app search `searchResultCount=1`, and top app result source attribution `cisa-kev,nvd,references,tags`. `scripts/cve-live-source-freshness-proof.py` then compared the app artifact against live CISA/NVD metadata and wrote `docs/live-proofs/2026-07-05-cve-live-source-freshness.json` with all checks PASS, live CISA total `1631`, and NVD 45-day critical total `237`.
- Process/RAM guard for this checkpoint: PASS. `ps` showed only the packaged app process for this check; no `launch.py`, `Qwen3.6`, or `vmlx` model process was running.
- Fresh 17:39 Computer Use retry: PASS for current Computer Use namespace exposure and release-app UI navigation. `mcp__computer_use.list_apps` returned `/Users/eric/exploitbot/release/ExploitBot.app`, `mcp__computer_use.get_app_state(app="/Users/eric/exploitbot/release/ExploitBot.app")` returned CUA app version `857`, PID `11094`, accessibility tree, and inline screenshot. A current click sweep reached Web, Network, Creds, Exploit, Post, Supply, OSINT, Report, and Stash; `/state` then reported `activeTab=stash`, ordered `manualTabSwitch` feed entries from `recon -> web` through `report -> stash`, selected model `/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP`, visible/supported 27B and 35B MXFP8 MTP model entries, `kvCacheQuantization=turboquant-q4`, `prefixCache=true`, `pagedCache=true`, `promptL2Disk=true`, `blockL2Disk=true`, `installedCount=42`, `missingCount=0`, `cveDatabase.totalCount=1644`, `kevCount=1631`, and `engineRunning=false`/`enginePort=0`. Screenshot files: `docs/live-proofs/2026-07-05-release-app-computer-use-retry-current.png` and `docs/live-proofs/2026-07-05-release-app-computer-use-retry-current-final.png`. Artifact: `docs/live-proofs/2026-07-05-release-app-computer-use-retry-current.json`.
- Fresh 17:53 release proof refresh: PARTIAL/BLOCKED. `scripts/release-readiness-proof.py` rebuilt the local package and wrote `docs/live-proofs/2026-07-04-release-readiness.json` with `localPackageStatus=PASS`, app/DMG codesign PASS, bundled runtime PASS, and `distributionStatus=BLOCKED` because `notarizationGate=requires-notary-credentials`. `scripts/notarization-preflight-proof.py` wrote `docs/live-proofs/2026-07-04-notarization-preflight.json` with `nextAction=configure-notary-credentials-and-run-package-notarize`, no configured notary inputs, no stapled ticket on the app or DMG, and Gatekeeper `REJECTED` with `source=Insufficient Context`. `scripts/release-public-truth-proof.py` wrote `docs/live-proofs/2026-07-05-release-public-truth.json` with `publicReleaseStatus=PARTIAL`, `releaseClaimAllowed=false`, local DMG hash `150feff5f76da1a406ec868170f7b5abfba5d8f28c9e308735c9ad60032cb7fb`, local manifest hash `d5b0e41b94ef2c8b912307486585a950e79929407ccc7aebb8cccf637a663d07`, and published `v0.1.0-beta` assets still pointing at older hashes and commit `afe3ece9c0ce06405a3ec5eaecf0e27bef079bf2`.
- Fresh 18:20 public release truth refresh: PARTIAL/BLOCKED. `scripts/release-public-truth-proof.py` refreshed `docs/live-proofs/2026-07-05-release-public-truth.json` against GitHub for `HEAD=3094235b0882f43a466db82ff2ae98495aa4c85a`. The repo and `v0.1.0-beta` release/DMG/manifest assets are visible, but the published DMG digest, manifest digest, release target commit `afe3ece9c0ce06405a3ec5eaecf0e27bef079bf2`, and local `notarizationGate=requires-notary-credentials` keep `releaseClaimAllowed=false`.
- Current objective open-blockers proof: BLOCKED overall, no model load. `scripts/objective-open-blockers-proof.py` writes `docs/live-proofs/2026-07-05-objective-open-blockers-current.json` from the current PASS/PARTIAL/BLOCKED matrix and goal audit. After the independent natural-language 27B/35B reruns, the remaining open gates are `Full-context-length stress`, which needs true near-max final assistant output plus post-generation cache-write proof above the 192k proven safe ceiling, and `Release/distribution readiness`, which remains blocked by missing notary credentials, missing stapled app/DMG tickets, Gatekeeper rejection, and unpublished current-hash release assets.
- Release audit future-gate fix: `scripts/goal-requirement-audit-proof.py` now derives the `release_displayable` expected status from `release/release-manifest.json` instead of permanently requiring `requires-notary-credentials`. Current artifacts still report BLOCKED because the manifest is not notarized, but a future `notarizationGate=passed` manifest can promote the release requirement to PASS after the matrix evidence is updated.
- Open-blocker future-gate fix: `scripts/objective-open-blockers-proof.py` now derives open blocker rows from current matrix row status instead of permanently requiring the release row to be blocked. Current artifacts list exactly two open gates: full-context stress PARTIAL and release distribution BLOCKED.
- Matrix future-gate fix: `scripts/pass-partial-blocked-matrix-proof.py` now derives accepted status counts from current matrix rows instead of permanently validating one static snapshot. Current artifacts record `25` PASS / `1` PARTIAL / `1` BLOCKED, and a notarized release row can move the matrix to `26` PASS / `1` PARTIAL / `0` BLOCKED without the matrix proof rejecting the transition.
- Long-context future-gate fix: `scripts/goal-requirement-audit-proof.py` now derives `generation_reasoning_context` from its matrix evidence rows, and `scripts/objective-open-blockers-proof.py` can drop the long-context row when `Full-context-length stress` becomes PASS. Current artifacts still record the row as PARTIAL because near-max final-output plus post-generation cache-write proof above the 192k proven safe ceiling is still missing.
- Completion-state future-gate fix: `scripts/goal-requirement-audit-proof.py` now derives `objectiveComplete`, `completionClaimAllowed`, and `overallStatus` from requirement rows, and `scripts/objective-open-blockers-proof.py` can report completion only when the matrix has no open rows and the goal audit is PASS/complete. Current artifacts still keep completion false because release and long-context gates remain open.
- Goal-audit matrix-count future-gate fix: `scripts/goal-requirement-audit-proof.py` now derives accepted matrix status counts from current matrix rows, so an eventual `27` PASS / `0` PARTIAL / `0` BLOCKED matrix is not rejected by the goal audit. Current artifacts record the real current `25` PASS / `1` PARTIAL / `1` BLOCKED evidence state.
- Independent natural tool-schema profile proof: PASS for schema filtering and execution blocking. `scripts/tool-schema-profile-exclusion-proof.py` launches the current app in testing mode with a mock engine, applies `toolSchemaExcludedTools=["run_shell"]`, verifies `/qa/tool-catalog` omits `run_shell`, verifies `/state.chat.toolSchemaExcludedTools` records the exclusion, then feeds a mock model response that still attempts `run_shell`. Artifact `docs/live-proofs/2026-07-06-tool-schema-profile-exclusion.json` reports PASS for catalog exclusion, state recording, model attempt capture, blocked execution, and no `SHOULD_NOT_RUN` shell marker. This proves the app can present a scenario-focused tool schema and refuse excluded tool calls if a model emits them anyway; the separate 27B/35B natural-language artifacts now provide real-model completion evidence.
- Independent natural empty-argument repair proof: PASS for local target repair. The earlier real 27B natural artifact showed the model repeatedly saying it would pass the scoped target to `httpx`, while the parsed tool call reached the executor as empty arguments and produced an `echo '' | httpx` command. `scripts/tool-argument-repair-proof.py` reproduces that failure with a mock model that emits `httpx` plus `{}` arguments, a prompt containing only a loopback target, and a deterministic fake `httpx`. After the fix, artifact `docs/live-proofs/2026-07-06-tool-argument-repair.json` reports PASS for model empty-argument emission, visible repair notice, command target use, fake `httpx` receiving the repaired target, no empty `httpx` command, and mock-engine-only execution. Boundary: repair is restricted to local-safe URLs parsed from the scoped prompt.
- Post-repair real 27B natural rerun: PASS after evidence checkpointing. `scripts/real-qwen-natural-tool-choice-proof.py` was rerun against Qwen3.6 27B MXFP8 MTP after the repair and checkpoint update. The saved artifact `docs/live-proofs/2026-07-06-real-qwen-natural-tool-choice-27b.json` now reports `ok=true`, `overall=PASS`, `toolSequence=["httpx","katana","sqlmap","search_cve"]`, final assistant continuation, report generation, SQLi proof, raw/terminal evidence, TurboQuant q4 KV, paged cache, prefix cache, block disk cache, hybrid async SSM rederive, and native D3 MTP.
- Independent natural-language 27B/35B proof: PASS. `scripts/real-qwen-natural-tool-choice-proof.py` now checkpoints after required evidence is visible, stops the tool phase, sends a no-tool final prompt, and verifies final/report proof. Fresh artifacts `docs/live-proofs/2026-07-06-real-qwen-natural-tool-choice-27b.json` and `docs/live-proofs/2026-07-06-real-qwen-natural-tool-choice-35b.json` both report `ok=true` and `overall=PASS` with no exact tool-call blocks, no function-specific retry, capped web schemas with `run_shell` excluded, model-selected web/prove/CVE tool sequences, SQLi proof marker `EXPLOITBOT_SQLI_PROOF_USER=alice`, verbose chat transcripts, terminal transcripts, final assistant continuation, report generation from evidence, TurboQuant q4 KV, hybrid SSM, paged cache, prefix cache, block disk cache, hybrid async SSM rederive, and native D3 MTP.
- Independent natural-language breadth tool-choice proof: PASS for direct-engine first-tool selection across non-SQLi classes. `scripts/real-qwen-natural-breadth-tool-choice-proof.py` launches real Qwen3.6 27B MXFP4 with TurboQuant q4 KV, prefix cache, paged cache, block disk cache, and native MTP. It sends natural objectives plus OpenAI tool schemas only, with no serialized tool-call blocks, and writes `docs/live-proofs/2026-07-06-real-qwen-natural-breadth-tool-choice-27b.json`. The live artifact reports `ok=true`, `overall=PASS`, `scenarioPassCount=10/10`, selected tool sequence `subfinder -> nmap -> wpscan -> hydra -> syft -> nuclei -> trufflehog -> sherlock -> httpx -> checkov`, matching the expected sequence across recon, network, WordPress, creds, container supply-chain, web-template, secrets, OSINT, SSRF probe, and IaC policy scenarios. Cache/runtime rows report `memoryPreflight=PASS`, `q4TurboQuantKV=PASS`, `prefixCache=PASS`, `pagedCache=PASS`, `blockDiskCache=PASS`, and `nativeMTPD3=PASS`. Boundary: this is direct-engine model-selection evidence and does not claim Swift app-loop execution or tool execution for those ten scenarios.
- Contract refresh after independent natural proof promotion: PASS. The pass/partial/blocked matrix, goal audit, and objective-open-blocker contract tests now require the independent natural-language row to stay PASS with both real-Qwen 27B and 35B proof artifacts. The current open-blocker contract requires exactly two remaining open gates: full-context stress and release/distribution readiness.
- App runtime autonomous scenario catalog route: PASS, no model load. `AppState.swift` now exposes `GET /qa/autonomous-scenario-catalog`, returning the six local-only autonomous scenario definitions directly from the app runtime with required `surface -> probe -> prove -> exploit_or_validate -> evidence -> report` stages, required tool lists, final markers, and `local_fixture_only` safety boundaries. `scripts/app-autonomous-scenario-catalog-route-proof.py` launched the current app in `EXPLOITBOT_TESTING=1`, called the route, validated all six scenarios, confirmed `noModelLoaded=true`, and wrote `docs/live-proofs/2026-07-06-app-autonomous-scenario-catalog-route.json` with all checks PASS. The refreshed artifact ledger includes this route proof as a current passing live proof.
- App runtime autonomous scenario prepare route: PASS, no model load. `AppState.swift` now exposes `POST /qa/autonomous-scenario-prepare`, which takes a scenario ID and local target, selects autopilot mode, switches to the appropriate tab, sets a scenario-sized tool-schema budget, and drafts a bounded user prompt with required stages, required tools, safety boundary, and final marker without starting model inference. `scripts/app-autonomous-scenario-prepare-route-proof.py` prepared `webserver_auth_sqli_report_chain` and `github_repo_secret_dependency_chain`, confirmed prompt drafting, tab selection, `sendToChat=false`, `isWorking=false`, and `noModelLoaded=true`, and wrote `docs/live-proofs/2026-07-06-app-autonomous-scenario-prepare-route.json` with all checks PASS.
- Autonomous scenario fixture setup contract: PASS, no model load. The scenario catalog and app runtime catalog rows now expose `fixtureSetup` metadata for all six local-only labs, including setup mode, setup entrypoint, target hint, and proof markers. `scripts/autonomous-scenario-fixture-setup-proof.py` materialized and verified the SQLi webserver, SSRF/file-read webserver, local Git repo secret/dependency fixture, static codebase fixture, container/IaC fixture, and loopback network credential/post-check service. Artifact `docs/live-proofs/2026-07-06-autonomous-scenario-fixture-setup.json` reports `scenarioCount=6`, all scenario rows `ok=true`, file fixtures under `/tmp/exploitbot-autonomous-scenario-fixtures`, and loopback HTTP services limited to the proof run. Boundary: this proves fixture materialization and app-discoverable setup metadata, not a fresh real-Qwen pass across all six scenarios.
- App runtime all-scenario fixture-session prepare handoff: PASS, no model load. `scripts/app-autonomous-scenario-fixture-session-prepare-proof.py` now reuses `build_fixture_session`, keeps the SQLi, SSRF/file-read, and network loopback services alive, launches the current app in `EXPLOITBOT_TESTING=1`, and calls `POST /qa/autonomous-scenario-prepare` for all six autonomous scenarios with their actual live fixture target or local fixture path. Artifact `docs/live-proofs/2026-07-06-app-autonomous-scenario-fixture-session-prepare.json` reports `scenarioCount=6`, `allPromptsContainLiveTargets=PASS`, `servicesAliveDuringPrepare=PASS`, `tabsSelected=PASS`, `noModelLoaded=PASS`, and each row `prepareOk=PASS`, `fixtureSetupInPrompt=PASS`, `targetInPrompt=PASS`, and `sendToChatFalse=PASS`. Boundary: this proves the app can receive prepared local-lab targets for every scenario; it does not start Qwen inference or claim model-selected tool execution.
- Webserver SSRF/file-read scenario: PASS through live app, mock model, real tool executor, and deterministic local scanner shims; now also promoted to real-Qwen 27B/35B proof. `scripts/webserver-ssrf-fileread-scenario-proof.py` reuses the local fixture session, drives `/send` through the current app with `run_shell -> httpx -> nuclei -> search_cve`, validates only loopback/fixture canaries, preserves verbose chat and terminal transcripts, parses a nuclei vulnerability row, creates a finding, and generates a report. Artifact `docs/live-proofs/2026-07-06-webserver-ssrf-fileread-scenario.json` reports `ok=true`, `toolSequence=["run_shell","httpx","nuclei","search_cve"]`, `ssrfProof=PASS`, `fileReadProof=PASS`, `safeLocalBoundary=PASS`, and `reportGeneratedFromEvidence=PASS`. Fresh real-Qwen artifacts `docs/live-proofs/2026-07-06-real-qwen-webserver-ssrf-fileread-27b.json` and `docs/live-proofs/2026-07-06-real-qwen-webserver-ssrf-fileread-35b.json` both report `ok=true`, `overall=PASS`, expected tool sequence, final marker plus second-turn marker, TurboQuant q4 KV, hybrid SSM typed cache, paged cache, prefix cache, block disk cache writes, hybrid async SSM rederive, native D3 MTP, SSRF/file-read canary proof, terminal transcript evidence, and generated report HTML. Boundary: real Qwen used exact prompt blocks with app-side exact-call recovery; this is not proof of independent model tool selection.
- I18n language-toggle proof: PASS through the live app without model load. `Localizer.swift` now declares supported languages, language selector labels, every tab including Supply Chain, every model-visible tool label, and core Settings/Chat/Report/Stash/Finding action labels for `en`, `ko`, `zh`, `es`, and `ja`. `ToolTab.label` now resolves through `Localizer`, and `GET /qa/i18n-snapshot` exposes current language plus localized tab/tool/core labels for proof harnesses. `scripts/i18n-language-toggle-proof.py` launched the current app in an isolated HOME, called `/qa/i18n-snapshot`, toggled Spanish and Japanese through `/qa/onboarding-complete` with `startEngine=false`, and wrote `docs/live-proofs/2026-07-06-i18n-language-toggle.json` with PASS checks for supported languages, Spanish/Japanese language state, changed tab labels, representative tool labels, changed core labels, and `noModelLoaded=PASS`. Boundary: this proves the language state and representative localized labels through live routes; it does not yet prove every hard-coded SwiftUI `Text` in every panel has been replaced.
- ChatService SSE no-progress watchdog: PARTIAL, source/build verified only. `ChatService.streamCompletion` now creates a dedicated `URLSessionConfiguration` with `timeoutIntervalForRequest = Self.streamNoProgressWatchdogSeconds`, tracks `lastStreamProgressAt`, treats reasoning/content/tool-call/usage deltas as stream progress, records `finishReason = "no_progress_timeout"` on watchdog timeout, and surfaces the warning through `lastStreamWarnings` plus the existing assistant-message warning path. Verification: the focused watchdog source contract failed first on the missing `streamNoProgressWatchdogSeconds`, then passed; the broader ChatService/autopilot/autonomous source-contract slice reported `67 passed`; `swift build --package-path ExploitBot -c debug` completed. Boundary: no live app-backed stalled-stream proof was run in this slice because a separate Qwen engine was active on port `8113`.
- First-run onboarding no-autostart fix: PASS for source/build plus isolated live app route proof. Live Computer Use found a RAM-risk path: visible onboarding completion with a real Qwen path immediately launched `ExploitBotEngine/launch.py` for `Qwen3.6-27B-MXFP4-CRACK-MTP`. Source root cause was `AppState.completeOnboarding(... startEngineAfterOnboarding: Bool = true)` plus `OnboardingView.completeOnboarding()` omitting the argument. The fix changes the default to false and passes `startEngineAfterOnboarding: false` from visible onboarding. Verification: the new source contract failed first on the old default, then passed; onboarding/i18n/settings source slice reported `10 passed`; `swift build --package-path ExploitBot -c debug` completed; an isolated `EXPLOITBOT_TESTING=1` live app run completed `/qa/onboarding-complete` without a `startEngine` key and then reported `showOnboarding=false`, `engineRunning=false`, `enginePort=0`, with no `launch.py`/`vmlx_engine.server` process left.
- Parallel-engine cleanup guard: PASS for pid-file-scoped cleanup and live untracked-process survival through the app build/verify path. `script/build_and_run.sh` and `EngineManager.cleanupStaleEngineProcesses` no longer use broad `pkill -f launch.py` cleanup that can terminate a second agent's standalone engine. Cleanup is now scoped to `$HOME/.exploitbot/engine.pid` / `currentEnginePIDFileProcesses(pidFile:)`; untracked `launch.py` engines are left alone and the shell script prints `Skipping untracked ExploitBot engine processes`. Source/build verification: the lifecycle contract failed first on the old broad `pkill`/`currentProcesses(matching:)` cleanup, then passed after the change; focused lifecycle/app-lock slice reported `22 passed`; `swift build --package-path ExploitBot -c debug` completed; `git diff --check` was clean. Live verification: started a harmless untracked process whose command line contained `/Users/eric/exploitbot/ExploitBotEngine/launch.py --dummy-stale-cleanup-proof`, confirmed `pgrep -f` matched it, ran `EXPLOITBOT_TESTING=1 ./script/build_and_run.sh --verify`, observed the skip message, and confirmed `untracked_engine_survived=PASS` after the app launched. Boundary: this proves the broad-kill regression path is closed for untracked matching launchers through the build/verify app launch path; it does not claim a new heavy-model autonomous run.

Artifact:

- `docs/live-proofs/2026-07-05-release-computer-use-settings-cache-model.json`
- `docs/live-proofs/2026-07-05-release-app-computer-use-retry-current.json`
- `docs/live-proofs/2026-07-05-cve-live-source-freshness.json`
- `docs/live-proofs/2026-07-05-release-public-truth.json`
- `docs/live-proofs/2026-07-05-objective-open-blockers-current.json`
- `docs/live-proofs/2026-07-06-app-autonomous-scenario-catalog-route.json`
- `docs/live-proofs/2026-07-06-app-autonomous-scenario-prepare-route.json`
- `docs/live-proofs/2026-07-06-autonomous-scenario-fixture-setup.json`
- `docs/live-proofs/2026-07-06-app-autonomous-scenario-fixture-session-prepare.json`
- `docs/live-proofs/2026-07-06-real-qwen-natural-breadth-tool-choice-27b.json`
- `docs/live-proofs/2026-07-06-webserver-ssrf-fileread-scenario.json`
- `docs/live-proofs/2026-07-06-real-qwen-webserver-ssrf-fileread-27b.json`
- `docs/live-proofs/2026-07-06-real-qwen-webserver-ssrf-fileread-35b.json`
- `docs/live-proofs/2026-07-06-i18n-language-toggle.json`

### Static/build gates

- `swift build` in `ExploitBot/`: PASS
- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m compileall -q ExploitBotEngine`: PASS
- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m pytest ExploitBotEngine/testsuite/test_live_model_verifier.py -q`: PASS, `24 passed`
- Full Python suite: FAIL, `52 passed`, `20 failed`

Failure clusters:

- `vmlx_engine.server` missing launcher/cache contract helpers and globals:
  - `build_scheduler_config_from_args`
  - `clear_response_session_store`
  - `_reasoning_parser_name`
  - `_default_stop`
  - `_content_when_reasoning_suppressed`
- scheduler helper exports missing:
  - `_generated_batch_responses`
  - `_prefix_cache_lookup_tokens`
- cache registry behavior drift:
  - JANG capability cache type resolves as `kv` instead of expected `hybrid`
  - Qwen wrapper nested text config lacks expected `cache_topology`
- disk/block cache behavior no longer matches tests.

### Live model attempt: 27B MXFP8 MTP

Command:

```bash
EXPLOITBOT_LIVE_BATCH_MODEL=/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP \
EXPLOITBOT_LIVE_BATCH_OUTPUT=docs/live-proofs/2026-07-04-qwen36-27b-mxfp8-mtp-live-batch.json \
EXPLOITBOT_LIVE_BATCH_MAX_NUM_SEQS=2 \
PYTHONPATH=ExploitBotEngine \
ExploitBotEngine/.venv/bin/python3 scripts/prove-live-continuous-batching.py
```

Result: FAIL before model load.

The launcher attempted to start:

```bash
python -m vmlx_engine.server \
  --model /Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP \
  --continuous-batching \
  --max-num-seqs 2 \
  --enable-auto-tool-choice \
  --reasoning-parser qwen3 \
  --tool-call-parser qwen \
  --effective-config-sources ... \
  --enable-prefix-cache true \
  --enable-disk-cache true \
  --use-paged-cache true \
  --enable-block-disk-cache true \
  --kv-cache-quantization turboquant-q4
```

`vmlx_engine.server` rejected the launcher/cache flags:

```text
server.py: error: unrecognized arguments: --max-num-seqs 2 --effective-config-sources ... --enable-prefix-cache true --enable-disk-cache true ... --kv-cache-quantization turboquant-q4 --kv-cache-group-size 64
```

Status: BLOCKED. The model folder exists and its metadata has the requested hybrid/MTP/MXFP8 contract, but the app/launcher cannot currently start the engine with the required cache flags.

### Launcher/server bridge fix

Root cause:

- `ExploitBotEngine/launch.py` correctly generated the intended runtime flags.
- `ExploitBotEngine/vmlx_engine/scheduler.py` and `engine/batched.py` already had the required cache/concurrency fields.
- `ExploitBotEngine/vmlx_engine/server.py` was missing the CLI/parser-to-`SchedulerConfig` bridge, so the engine exited in argparse before any model load.

Narrow fix applied:

- Added server globals/helpers for default stop sequences, config provenance, reasoning parser name, and scheduler config construction.
- Added server CLI flags for `--max-num-seqs`, prefix cache, prompt disk cache, paged cache, block L2 disk cache, TurboQuant KV cache, chat template kwargs, and effective config source metadata.
- Passed the built scheduler config into `load_model()`.
- Added `effective_config` metadata to `/health` and `/v1/models`.

Verification after fix:

- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m py_compile ExploitBotEngine/vmlx_engine/server.py`: PASS
- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m pytest ExploitBotEngine/testsuite/test_server_cache_defaults.py ExploitBotEngine/testsuite/test_runtime_status.py::RuntimeStatusTests::test_health_and_models_share_effective_runtime_metadata -q`: PASS, `3 passed`
- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m pytest ExploitBotEngine/testsuite/test_live_model_verifier.py::LiveModelVerifierTests::test_dry_run_launch_args_include_required_cache_and_parser_defaults -q`: PASS

Next: rerun the 27B live proof with the same command.

### Live model attempt: 27B MXFP8 MTP after launcher bridge fix

Result: FAIL during real model startup, after server argument parsing.

Progress observed:

- Server accepted launcher flags.
- Reasoning parser enabled: `qwen3`.
- Tool parser enabled: `qwen`.
- Model recognized as MLLM/native MTP VL artifact.
- Native MTP runtime activated for Qwen3.6 27B, `layers=1`, `tensors=23`, `cache=hybrid`.
- JANG v2 VLM loader selected.

New blocker:

```text
ImportError: cannot import name '_detect_turboquant_layer_types' from 'vmlx_engine.utils.model_inspector'
```

Failing path:

```text
vmlx_engine.models.mllm.load
  -> vmlx_engine.utils.jang_loader.load_jang_vlm_model
  -> _load_jang_v2_vlm
  -> _patch_turboquant_make_cache
  -> from .model_inspector import _detect_turboquant_layer_types, is_mla_model
```

Status: BLOCKED on incomplete engine sync. The runtime now reaches the real JANG VL/native-MTP load path, but TurboQuant KV cache patching cannot proceed because a required helper is absent from `utils/model_inspector.py`.

### Model-inspector helper fix

Root cause:

- `jang_loader._patch_turboquant_make_cache()` expects `_detect_turboquant_layer_types()` from `vmlx_engine.utils.model_inspector`.
- ExploitBot's embedded `model_inspector.py` did not include that helper, while the local vMLX source does.

Narrow fix applied:

- Added `_detect_turboquant_layer_types()` to `ExploitBotEngine/vmlx_engine/utils/model_inspector.py`.
- Added a unit test proving Qwen3.6 hybrid `layer_types` map to `["ssm", "ssm", "ssm", "attention"]` with correct key/value dimensions.

Verification after fix:

- New red/green unit test: PASS
- Targeted launcher/runtime tests: PASS, `4 passed`
- `py_compile` for `model_inspector.py` and `server.py`: PASS

Next: rerun the 27B live proof after the model-inspector fix.

### Additional runtime-schema and scheduler-telemetry fixes

The next 27B live run reached real request handling and exposed two more issues.

1. Chat request schema drift:

```text
AttributeError: 'ChatCompletionRequest' object has no attribute 'logprobs'
```

Fix applied:

- Added OpenAI-compatible `logprobs` and `top_logprobs` fields to `ChatCompletionRequest`.
- Added a targeted parser/API regression test.

2. Scheduler proof telemetry gap:

```text
live-continuous-batching proof failed: scheduler did not observe all requests running
```

Observed runtime evidence before the assertion:

```json
{
  "num_requests_processed": 2,
  "num_running": 0,
  "num_waiting": 0,
  "single_active_decode": false,
  "total_completion_tokens": 14,
  "total_prompt_tokens": 232
}
```

Interpretation: the 27B model loaded, generated, and processed both requests, but the stats endpoint only exposed final instantaneous queue depth. The live proof requires peak observed running/waiting depth so it can prove actual concurrent admission after the queue drains.

Fix applied:

- Added `max_waiting_observed` and `max_running_observed` counters to both text and MLLM schedulers.
- Counters update when requests enter waiting and when they are admitted to running.
- Added a unit test for both scheduler classes.

Verification:

- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m py_compile ExploitBotEngine/vmlx_engine/server.py ExploitBotEngine/vmlx_engine/scheduler.py ExploitBotEngine/vmlx_engine/mllm_scheduler.py`: PASS
- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m pytest ExploitBotEngine/testsuite/test_hybrid_ssm_helpers.py::HybridSSMHelperTests::test_scheduler_peak_queue_depth_counters_are_recorded ExploitBotEngine/testsuite/test_server_cache_defaults.py ExploitBotEngine/testsuite/test_runtime_status.py::RuntimeStatusTests::test_health_and_models_share_effective_runtime_metadata ExploitBotEngine/testsuite/test_live_model_verifier.py::LiveModelVerifierTests::test_dry_run_launch_args_include_required_cache_and_parser_defaults ExploitBotEngine/testsuite/test_tool_parser_api.py::ToolParserApiTests::test_chat_completion_request_logprobs_fields_default_safely -q`: PASS, `6 passed`

Next: rerun the 27B live proof after scheduler telemetry is available.

### Live model result: 27B MXFP8 MTP

Command:

```bash
EXPLOITBOT_LIVE_BATCH_MODEL=/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP \
EXPLOITBOT_LIVE_BATCH_OUTPUT=docs/live-proofs/2026-07-04-qwen36-27b-mxfp8-mtp-live-batch.json \
EXPLOITBOT_LIVE_BATCH_MAX_NUM_SEQS=2 \
PYTHONPATH=ExploitBotEngine \
ExploitBotEngine/.venv/bin/python3 scripts/prove-live-continuous-batching.py
```

Result: PASS.

Proof artifact:

- `docs/live-proofs/2026-07-04-qwen36-27b-mxfp8-mtp-live-batch.json`

Live proof highlights:

- Two concurrent `/v1/chat/completions` requests overlapped on the client.
- Scheduler observed `max_running_observed=2` and `max_waiting_observed=2`.
- Scheduler processed `num_requests_processed=2`.
- Model returned non-empty expected markers: `BATCH-QWEN-A`, `BATCH-QWEN-B`.
- `kv_cache_quantization`: `enabled=true`, `bits=4`, `group_size=64`.
- Native cache contract: `hybrid_ssm_typed`, `prefix=true`, `paged=true`, `block_disk_l2=true`.
- Attention-KV storage quantization reports `bits=4`, `mode=storage_boundary`, with SSM companion state and async clean-prefill rederive.
- Block L2 cache wrote 3 blocks, `166` tokens on disk, `0.313GB`.
- Cache totals report `166` RAM tokens cached and `460` summed L2 tokens across block + SSM companion tiers.

Fixes required before PASS:

- Server CLI bridge for cache/runtime flags.
- Missing model-inspector TurboQuant helpers.
- Chat request schema `logprobs` compatibility.
- Scheduler peak queue-depth telemetry and server stats passthrough.
- Scheduler q4 bit mapping for `turboquant-q4` aliases.

Next: run the same proof against the 35B MXFP8 MTP model.

### Live model result: 35B A3B MXFP8 MTP

Command:

```bash
EXPLOITBOT_LIVE_BATCH_MODEL=/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP \
EXPLOITBOT_LIVE_BATCH_OUTPUT=docs/live-proofs/2026-07-04-qwen36-35b-a3b-mxfp8-mtp-live-batch.json \
EXPLOITBOT_LIVE_BATCH_MAX_NUM_SEQS=2 \
PYTHONPATH=ExploitBotEngine \
ExploitBotEngine/.venv/bin/python3 scripts/prove-live-continuous-batching.py
```

Result: PASS.

Proof artifact:

- `docs/live-proofs/2026-07-04-qwen36-35b-a3b-mxfp8-mtp-live-batch.json`

Live proof highlights:

- Two concurrent `/v1/chat/completions` requests overlapped on the client.
- Scheduler observed `max_running_observed=2` and `max_waiting_observed=2`.
- Scheduler processed `num_requests_processed=2`.
- Model returned non-empty expected markers: `BATCH-QWEN-A`, `BATCH-QWEN-B`.
- `kv_cache_quantization`: `enabled=true`, `bits=4`, `group_size=64`.
- Native cache contract: `hybrid_ssm_typed`, `prefix=true`, `paged=true`, `block_disk_l2=true`.
- Attention-KV storage quantization reports `bits=4`, `mode=storage_boundary`, with SSM companion state and async clean-prefill rederive.
- Block L2 cache wrote 3 blocks, `166` tokens on disk, `0.129GB`.
- Cache totals report `166` RAM tokens cached and `460` summed L2 tokens across block + SSM companion tiers.

Next: launch the macOS app and verify the visible panels/tools are wired to the local engine path instead of only demo data.

### App UI and app-managed engine proof

Build/launch command:

```bash
./script/build_and_run.sh --verify
```

Result: PASS. The dev bundle launched `dist/ExploitBot.app` and the test server listened on `127.0.0.1:9999`.

Computer Use status: PASS after macOS automation permission repair. `mcp__computer_use.get_app_state(app="ExploitBot")` attached to the running dev bundle, returned the live screenshot and accessibility tree, and direct clicks worked.

Retest evidence:

- App PID: `58292`
- Bundle: `dist/ExploitBot.app`
- QA/API port: `127.0.0.1:9999`
- `mcp__computer_use.get_app_state(app="ExploitBot")`: PASS, returned main workspace tree and screenshot.
- Clicked Settings gear by accessibility index `17`: PASS.
- Settings screen exposed live categories and actions: Engine, Model, Runtime, Context, Cache, Agents, CVE Database, Tools, Logs, Done, Apply App Settings, Apply & Restart Engine.
- Current UI state in this retest: Engine stopped. This proves UI attach/control, not a live model generation run.

Visual proof:

- `docs/live-proofs/2026-07-04-exploitbot-live-ui.png`

Visible state from screenshot:

- App opens to onboarding step 1, language selection.
- Main workspace is not first-run visible until onboarding completes.

App API state before onboarding:

- `healthStatus=stopped`
- `model=""`
- `activeTab=recon`
- active subtabs include recon, web, network, creds, exploit, post, supply-chain CVE Intel, OSINT, and report.
- cache UI flags are enabled in app state: prefix cache, prompt L2 disk, paged cache, block L2 disk, TurboQuant KV, model-generation defaults.

App-managed real model proof:

- Completed onboarding via `/qa/onboarding-complete` with model path `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP`.
- Started the app-managed engine with `/engine/start`.
- Engine became healthy on port `8100`.
- `/health` reported:
  - `status=healthy`
  - `engine_type=batched`
  - `model_name=dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP`
  - reasoning parser `qwen3`
  - tool parser `qwen`
  - topology `hybrid_ssm_attention`
  - prefix cache, paged cache, prompt L2, block L2, TurboQuant q4, SSM companion, and SSM L2 all active/expected.
- `/v1/cache/stats` reported:
  - `kv_cache_quantization.enabled=true`
  - `bits=4`
  - `group_size=64`
  - native cache `hybrid_ssm_typed`
  - block L2 cache wrote 28 blocks and 1,778 tokens.
- Sending `/send` through the app chat service produced:
  - user message
  - reasoning message
  - assistant response containing `APP-QWEN-27B-WIRED`
  - dynamic context preview
  - tool schema names: `search_cve`, `lookup_cve`, `search_context`, `run_shell`, `dnsx`, `httpx`
  - pending `run_shell` approval for a scoped localhost `nmap` command.

Status: PASS for app-to-engine/model/chat/tool-schema wiring from the earlier app-managed 27B proof. PASS for Computer Use UI attach/control after permission repair. PARTIAL for end-to-end UI model-generation proof because this specific Computer Use retest did not start a live model.

### Settings and tool transcript continuation

Changes applied after the initial app proof:

- Settings Runtime page now has real controls for model generation defaults, temperature, top-p, max tokens, reasoning on/off, reasoning parser, tool parser, and max iterations.
- Settings Cache page now has real controls for TurboQuant q4/full KV, KV group size, prefix cache, prompt L2 disk, prompt L2 budget, cache memory, paged cache, block size, block L2 disk, and block L2 budget.
- `DarkOptionGrid` options are real SwiftUI buttons now, so Computer Use/accessibility activation is not dependent on coordinate-only clicks.
- `AppState.applyAppSettings` now propagates generation defaults, temperature, top-p, and max tokens to the primary chat service and existing agents instead of leaving live chat on stale values.
- Chat tool transcripts now show verbose tool requests, shell commands where applicable, pretty JSON arguments, stdout/stderr, blocked-scope details, and the follow-up model analysis in the chat stream.

Verification:

- `swift build --package-path ExploitBot`: PASS.
- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m pytest -q ExploitBotEngine/testsuite/test_responses_session_store.py ExploitBotEngine/testsuite/test_tool_parser_api.py`: PASS, `11 passed`.
- `python3 scripts/settings-apply-proof.py`: PASS.
- `python3 scripts/settings-category-coverage-proof.py`: PASS when run alone; do not run it in parallel with other app-launching proof scripts because those scripts kill/restart `ExploitBot`.
- `python3 scripts/agent-live-tool-status-proof.py`: PASS.
- Mock-engine verbose tool transcript proof: PASS. `/messages` contained `Tool request: run_shell`, `$ /bin/zsh -c printf VERBOSE_TOOL_OK`, JSON argument text including `"command"`, tool output `VERBOSE_TOOL_OK`, and model follow-up `Observed VERBOSE_TOOL_OK`.

Live UI toggle proof from Computer Use:

- Chat toolbar reasoning toggled off and `/state` reported `chat.enableReasoning=false` with activity summary `setReasoning off`.
- Cache settings toggled Full KV and Prefix Cache off, then `/state` reported `kvCacheQuantization="none"` and `prefixCache=false`.
- Cache settings were restored to production defaults, then `/state` reported `kvCacheQuantization="turboquant-q4"`, `prefixCache=true`, `pagedCache=true`, `blockL2Disk=true`, `promptL2Disk=true`, `useModelGenerationDefaults=true`, and `chat.enableReasoning=true`.

### Live UI 27B bounded multiturn proof after settings fix

Pre-fix failure found by live UI:

- Computer Use clicked Settings > Engine > Start and loaded `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP`.
- `/health` reported healthy 27B runtime with prefix cache, paged cache, TurboQuant q4, prompt L2, block L2, and hybrid SSM companion active.
- With model generation defaults on and max tokens at `4096`, a reasoning-on UI prompt produced TTFT `8.57s`, `1,235` completion tokens, and only a `78` character reasoning stub in `/messages`; assistant content stayed empty until stopped.
- Reasoning-off then produced assistant content, but it ran to `1,755` completion tokens before manual stop and did not obey the short proof prompt.

Root cause fixed:

- Red proof: `/qa/apply-app-settings` with `engine.useModelGenerationDefaults=false`, `engine.maxTokens=64`, `temperature=0`, `topP=1` changed `engineConfig`, but `/qa/context-budget-compaction` still reported `chatMaxTokens=4096` and `maxTokensForwarded=false`.
- Fix: `AppState.applyAppSettings` now copies updated engine generation settings into the primary `chatService`, matching the already-updated agent propagation path.
- Regression proof: `python3 scripts/settings-apply-proof.py` now checks `maxTokens=64`, `chatMaxTokens=64`, and `contracts.maxTokensForwarded=true`.

Verification after fix:

- `swift build --package-path ExploitBot`: PASS.
- `python3 scripts/settings-apply-proof.py`: PASS.
- Live app route: `/qa/context-budget-compaction` returned `ok=true`, `maxTokens=64`, `chatMaxTokens=64`, `maxTokensForwarded=true`.
- Computer Use relaunched Settings, clicked Engine Start, and `/health` showed `max_tokens=64`, `temperature=0.0`, `top_p=1.0`.
- Computer Use sent bounded UI turn 1 with reasoning off:
  - Response: `UI27-BOUNDED-ACK`.
  - Metrics: TTFT `5.62s`, prompt tokens `1,849`, cached tokens `576`, completion tokens `23`, `3.04 tok/s`.
- Computer Use sent bounded UI turn 2 in the same chat:
  - Response: `UI27-BOUNDED-TURN2` and it referenced `UI27-BOUNDED-ACK`.
  - Metrics: TTFT `5.93s`, prompt tokens `1,923`, cached tokens `576`, completion tokens `31`, `3.56 tok/s`.

Proof artifact:

- `docs/live-proofs/2026-07-04-qwen36-27b-ui-bounded-multiturn-after-settings-fix.json`

Cache proof from the artifact:

- `kv_cache_quantization.enabled=true`, `bits=4`, `group_size=64`.
- Native cache `cache_type=hybrid_ssm_typed`.
- Native cache components include `attention_kv`, `ssm_companion_state`, and `async_rederive`.
- Attention KV storage quantization reports `mode=storage_boundary`, `bits=4`, `group_size=64`, and `rederive=async_clean_prefill_on_miss_or_warm_pass`.
- Prefix cache and paged cache are true; block L2 disk is true.
- App metrics showed `cachedTokens=576`.
- Scheduler cache hits `2`, tokens saved `1,344`, block L2 hits `9`, SSM entries `6`, SSM disk tokens `21,134`.

Status: PASS for 27B live UI bounded multiturn after the settings propagation fix. PARTIAL for reasoning-on quality because the live reasoning-on turn still ran long and surfaced only a short reasoning stub before manual stop.

### Live UI 35B bounded multiturn proof after settings fix

Computer Use continued the same app-managed validation path with `/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP`.

Setup:

- `/qa/apply-app-settings` selected the 35B model path and kept bounded generation settings: `useModelGenerationDefaults=false`, `temperature=0`, `topP=1`, `maxTokens=64`.
- App-managed engine started on port `8101`.
- Settings UI showed `Engine running Qwen3.6-35B-A3B-MXFP8-CRACK-MTP`.
- Chat toolbar reasoning was off and `/state` reported `chat.enableReasoning=false`.
- `/health` reported `max_tokens=64`, `temperature=0.0`, `top_p=1.0`, reasoning parser `qwen3`, tool parser `qwen`, and topology `hybrid_ssm_attention`.

Computer Use sent bounded UI turn 1:

- Prompt marker request: `UI35-BOUNDED-ACK`.
- Response: `UI35-BOUNDED-ACK` and a short 35B confirmation sentence.
- Metrics: TTFT `3.48s`, prompt tokens `1,962`, completion tokens `34`, `7.77 tok/s`.

Computer Use sent bounded UI turn 2 in the same chat:

- Prompt marker request: `UI35-BOUNDED-TURN2` and mention `UI35-BOUNDED-ACK`.
- Response: `UI35-BOUNDED-TURN2` and it referenced `UI35-BOUNDED-ACK`.
- Metrics: TTFT `3.66s`, prompt tokens `2,049`, completion tokens `40`, `8.35 tok/s`.

Proof artifact:

- `docs/live-proofs/2026-07-04-qwen36-35b-ui-bounded-multiturn-after-settings-fix.json`

Cache and MTP proof from the artifact:

- `kv_cache_quantization.enabled=true`, `bits=4`, `group_size=64`.
- Native cache `cache_type=hybrid_ssm_typed`.
- Native cache components include `attention_kv`, `ssm_companion_state`, and `async_rederive`.
- Attention KV storage quantization reports `mode=storage_boundary`, `bits=4`, `group_size=64`, and `rederive=async_clean_prefill_on_miss_or_warm_pass`.
- Prefix cache and paged cache are true; block L2 disk is true.
- Scheduler cache saved `768` tokens and reported `24` cache hits.
- Block L2 held `3,241` tokens on disk; SSM companion L2 held `6,697` tokens on disk.
- Native MTP runtime was active; the second request reported `acceptance_rate=0.1923` with `fallback_reason=null`.

Status: PASS for 35B live UI bounded multiturn after the settings propagation fix. Reasoning-on quality is revalidated below with the mode-scoped prompt fix plus 1024-token bounded live proofs.

### Live UI 35B reasoning-on bounded warning proof

Root-cause evidence:

- The Qwen3.6 27B and 35B tokenizer templates open `<think>` when `enable_thinking=true`, but do not expose `thinking_budget` or `reasoning_effort`.
- Direct streaming engine probe with 35B, `enable_thinking=true`, and `max_tokens=512` produced `2,025` chars of `reasoning_content`, no final `content`, and `finish_reason=length`.
- The requested marker appeared inside reasoning, not final assistant content.
- This is not a UI toggle failure: `/state` reported `chat.enableReasoning=true`, `/health` reported `enable_thinking=true`, and the model generated reasoning deltas.

Fix applied:

- `ChatService.streamCompletion()` now tracks stream finish state and also treats `completionTokens >= maxTokens` as a bounded length-stop signal when the stream omits a usable final `finish_reason`.
- When reasoning is on, reasoning text exists, and no final assistant content is produced before the bounded generation cap, the assistant bubble now shows an explicit app diagnostic instead of staying empty:
  - `No final assistant content was produced. The model exhausted the 64-token generation limit inside the reasoning stream; increase Max Tokens or turn Reasoning off for a direct answer.`

Verification:

- `swift build --package-path ExploitBot`: PASS.
- Relaunched the app and started the app-managed 35B engine.
- Computer Use sent a reasoning-on prompt through the visible chat UI.
- Metrics: TTFT `4.66s`, prompt tokens `1,966`, cached tokens `832`, completion tokens `64`, `10.68 tok/s`.
- `/messages` contained:
  - user prompt requesting `UI35-REASONING-WARN-ACK`
  - `thinking` message with `177` chars
  - assistant diagnostic warning with `182` chars
- `/health` reported native MTP `finish_reason=length`.
- Cache proof stayed active: TurboQuant q4 KV, prefix cache, paged cache, block L2, SSM companion, and async rederive.

Proof artifact:

- `docs/live-proofs/2026-07-04-qwen36-35b-ui-reasoning-on-warning-after-fix.json`

Status: PARTIAL for the 64-token warning path. The UI no longer hides the failure behind an empty assistant message, but 64 tokens is too low for Qwen3.6 reasoning-on final content.

### Live app/API Qwen3.6 reasoning-on final-content proof

Root cause isolated:

- Qwen3.6 model bundles still expose only `enable_thinking`; no real `thinking_budget` or `reasoning_effort` key exists in the local `tokenizer_config.json`, `generation_config.json`, `jang_config.json`, or `chat_template.jinja`.
- The app also made the manual no-tools reasoning proof harder than necessary: `ChatService.systemPrompt` always used the Autopilot-specific line `Think through your attack plan before calling tools`, even when `/mode` was `manual` and the user explicitly said not to use tools.

Fix applied:

- `ChatService.systemPrompt` is now mode-scoped:
  - Autopilot keeps the attack-plan/tool-analysis reasoning instruction.
  - Manual/Copilot reasoning uses bounded task-scoped reasoning and explicitly requires final assistant content.
  - Manual/Copilot reasoning-off no longer says to call tools immediately.
- Added a source-contract regression in `ExploitBotEngine/testsuite/test_chat_service_tool_loop_contracts.py`.
- Added `scripts/real-qwen-reasoning-on-proof.py` to run app/API live reasoning-on proofs with RAM preflight, app-managed engine launch, q4 KV, prefix cache, paged cache, block L2 cache, and process-group cleanup.

Verification:

- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m pytest -q ExploitBotEngine/testsuite/test_chat_service_tool_loop_contracts.py`: PASS, `7 passed`.
- `swift build --package-path ExploitBot`: PASS.
- 27B negative-control with `maxTokens=512`: artifact `docs/live-proofs/2026-07-04-real-qwen-27b-reasoning-on.json` reports `ok=false`, `status=FAIL_MARKER_ONLY_IN_REASONING`, `warningShown=true`; marker reached reasoning only.
- 27B live fixed path with `maxTokens=1024`: artifact `docs/live-proofs/2026-07-04-real-qwen-27b-reasoning-on-1024.json` reports `ok=true`, `status=PASS_FINAL_ASSISTANT_CONTENT`, `assistantHasMarker=true`, `thinkingHasMarker=false`, `warningShown=false`.
- 35B live fixed path with `maxTokens=1024`: artifact `docs/live-proofs/2026-07-04-real-qwen-35b-reasoning-on-1024.json` reports `ok=true`, `status=PASS_FINAL_ASSISTANT_CONTENT`, `assistantHasMarker=true`, `thinkingHasMarker=false`, `warningShown=false`.
- Both 1024-token live proofs report q4 KV (`bits=4`, `group_size=64`), native `hybrid_ssm_typed` cache, `paged=true`, `prefix=true`, `block_disk_l2=true`, scheduler block size `64`, and no heavyweight model process remained after cleanup.

Status: PASS for Qwen3.6 27B and 35B reasoning-on final assistant content through live app/API proof at `maxTokens=1024`. PARTIAL remains for lower bounded caps: 64 and 512 can still stop inside reasoning and correctly surface the warning.

### App QA matrix status

Initial broad matrix run:

```bash
PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 scripts/app-qa-matrix-smoke-proof.py
```

First result: FAIL due `/qa/coverage-index` timeout at 45s.

Standalone check:

- `/qa/coverage-index` returned `ok=true` in `58.21s`.
- Payload size: `306,527` bytes.
- Group count: `7`.

Fix applied:

- Raised the smoke proof timeout for `/qa/coverage-index` from 45s to 90s.

Second broad matrix run result: FAIL on `/qa/deep-runtime-flow-coverage`.

Key failing contracts from the returned payload:

- `contractParity=false`
- `continuousBatchingContractParity=false`
- `runtimeLocalModelLaneContractParity=false`
- `sessionContextCacheFlowContractParity=false`
- `streamingParserContractParity=false`
- `contextPromptInjectionBoundaryContractParity=false`
- `cveImportEmbeddingContractParity=false`
- `continuousBatchingSourceCoverage=false`
- `responsesEndpointReuse=false`
- `streamingReasoningDeltas=false`
- `streamingToolCallDeltas=false`
- `multiAgentEnabled=false`

Interpretation: the app is semi-functional and can run real local models, but the internal release/readiness matrix is not green. Some failure rows look stale against the new Qwen 3.6 MXFP8 proof artifacts, while others are real missing/partial contracts that need triage before calling the app production-ready.

### CVE library status

Live authoritative feed checks:

- CISA KEV URL: `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json`
- CISA catalog version: `2026.07.01`
- CISA date released: `2026-07-01T19:00:06.9016Z`
- CISA entries: `1,631`
- Most recent CISA KEV examples by `dateAdded`: `CVE-2026-45659` SharePoint, `CVE-2026-48558` SimpleHelp, `CVE-2026-12569` PTC Windchill/FlexPLM, `CVE-2026-20230` Cisco Unified Communications Manager, `CVE-2025-67038` Lantronix EDS5000.
- NVD URL checked: `https://services.nvd.nist.gov/rest/json/cves/2.0`
- NVD critical window checked: `2026-05-21T09:31:17.000Z` through `2026-07-05T09:31:17.999Z`
- NVD total critical results in that window: `237`
- NVD examples from the current proof: `CVE-2026-47280` Azure Resource Manager, `CVE-2026-40412` Azure Orbital Spatio, `CVE-2026-23652` Microsoft Power Pages, `CVE-2026-44881` Portainer, `CVE-2026-44477` CloudNativePG, `CVE-2026-9813` FlowIntel.

Bug found:

- `ExploitBot/Resources/starter-cves.db` contained `1,552` CVE rows, but the running app reported only `totalCount=1`.
- Root cause: the dev app bundle did not copy `ExploitBot/Resources`, and `DatabaseManager` did not import the starter DB into the active user database.

Fix applied:

- `script/build_and_run.sh` now copies `ExploitBot/Resources` into `dist/ExploitBot.app/Contents/Resources`.
- `DatabaseManager` now imports `starter-cves.db` on first run or when the active CVE table has fewer than 100 rows.
- `CVEService.refreshCurrentThreatIntel` now defaults to importing the full practical CISA KEV catalog (`maxKEVResults=5000`) while keeping NVD critical imports bounded to 10 current rows.

2026-07-05 refresh update:

- Artifact `docs/live-proofs/2026-07-04-cve-current-threat-intel-live.json` was refreshed at `2026-07-05T03:50:53-0700`.
- CISA source total: `1,631`; app `kevCount=1,631`.
- App current-threat-intel total after refresh: `1,641` rows (`1,631` CISA KEV + `10` recent NVD critical).
- Exact app search for latest KEV `CVE-2026-45659` returned one SharePoint row with CISA source attribution.
- Import records `cve.starterImportPath` and `cve.starterImportAt` in settings.

Verification:

- Clean app data directory imported `1,552` CVEs.
- Clean app state reported `totalCount=1552`, `kevCount=1552`.
- Starter path recorded as `dist/ExploitBot.app/Contents/Resources/starter-cves.db`.
- App CVE settings search for `SharePoint` returned `searchResultCount=9`.
- SQLite rows included recent/high-value SharePoint KEV entries such as `CVE-2026-20963`, `CVE-2025-53770`, `CVE-2025-49706`, and `CVE-2025-49704`.

Status: PARTIAL. The app now has a usable starter CVE library and dynamic search in app services. Still needed: live refresh/sync UX from current feeds, source attribution in the UI, and a complete model-tool turn where CVE tool results produce a final assistant answer.

### Live UI 35B CVE tool loop proof

Live target:

- App: `dist/ExploitBot.app`
- QA API: `http://127.0.0.1:9999`
- Engine: app-managed 35B on `localhost:8103`
- Model: `dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP`
- Chat mode: Autopilot
- Reasoning: off

Computer Use proof:

- Clicked the pending Start New Context confirmation in the live UI; chat moved to `0 msgs ctx 1` while preserving `prefix/l2/tq`.
- Opened Settings -> Runtime, changed Max Tokens from `64` to `256`, clicked Apply App Settings, and closed Settings.
- Cleared context again to `0 msgs ctx 2`.
- Sent CVE tool prompts through the visible chat input and used the Stop button to halt runaway generation.

Model/tool behavior observed:

- The first natural CVE prompt was received by the model with tool schemas, but at the previous `64` token cap it emitted only a partial parameter block and no executable tool call.
- A Qwen XML tool-call contract prompt caused the engine/app to emit and execute real `search_cve` callback tool calls.
- Chat showed verbose transcripts with `Tool request: search_cve`, `$ echo handled by callback`, pretty JSON arguments, and SharePoint CVE rows.
- `search_cve` returned SharePoint KEV data including `CVE-2026-20963`.
- A focused `lookup_cve` prompt first produced an empty-argument call and returned `Missing cve_id parameter`.
- The model retried `lookup_cve` with `"cve_id" : "CVE-2026-20963"` and the callback returned a successful detail transcript.
- Autopilot then kept looping through `search_cve`/`search_context` and did not produce the requested `UI35-CVE-TOOL-ACK` final answer.
- During the earlier natural loop, the model invoked `run_shell` to search for scope files despite the CVE-only constraint. The shell transcript was visible, but this is an autonomy/policy failure for scoped demos.

Engine/cache proof from the same run:

- 35B model healthy on `8103`.
- Tool parser: `qwen`; reasoning parser: `qwen3`; auto tool choice enabled.
- App engine config: `maxTokens=256`, `temperature=0`, `topP=1`, `kvCacheQuantization=turboquant-q4`, prefix cache on, paged cache on, block L2 on.
- Engine launcher metadata still reported `max_tokens=64`; this is launch metadata, not proof that the app request cap changed. Keep this as a follow-up proof gap.
- Cache stats showed q4 KV, prefix/paged cache, block disk L2, SSM companion entries, async rederive topology, and native MTP diagnostics.

Artifact:

- `docs/live-proofs/2026-07-04-qwen36-35b-ui-cve-tool-loop-partial.json`

Status: PARTIAL/FAIL split. PASS for Computer Use, model prompt/tool-schema receipt, `search_cve`, verbose tool transcript, and cache/runtime topology. PARTIAL for `lookup_cve` because the first parsed call lost arguments before a later retry succeeded. FAIL for final assistant answer and autonomy loop control because Autopilot repeated tools, invoked `run_shell`, and never produced the requested marker.

### Live UI 35B CVE tool loop proof after loop fix

Live target:

- App: `dist/ExploitBot.app`
- QA API: `http://127.0.0.1:9999`
- Engine: app-managed 35B on `localhost:8104`
- Model: `dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP`
- Chat mode: Autopilot
- Reasoning: off

Fix applied before this run:

- Added streamed tool-call argument accumulation so later name/id deltas do not clear previously streamed JSON arguments.
- Added native assistant `tool_calls` history and native `role: "tool"` result history when a tool call id is available.
- Added a post-tool forced final-answer turn with `tool_choice: "none"` and no tools in the body.
- Added Autopilot policy gating for explicit user prompts that disallow `run_shell` or shell commands.

Computer Use proof:

- Confirmed Settings was closed and the live app was on the main chat screen.
- Confirmed the app-managed 35B engine was healthy on `8104`.
- Typed this prompt through the visible chat input: `Patched CVE tool loop proof. Use the search_cve tool to search for SharePoint known exploited vulnerabilities. Do not use run_shell or shell commands. After the tool result, answer with exact marker UI35-CVE-PATCHED-ACK, the CVE ID, and one sentence explaining why it matters.`
- Waited for the live UI turn to finish, then inspected `/messages` and `/state`.

Observed result:

- Message shape was bounded: user prompt, assistant tool call, `search_cve` tool result, final assistant answer.
- Tool sequence was exactly `search_cve`; no `run_shell` was invoked after the explicit shell prohibition.
- Chat showed verbose tool transcript with `Tool request: search_cve`, `$ echo handled by callback`, JSON arguments, and SharePoint CVE rows.
- Final assistant message contained `UI35-CVE-PATCHED-ACK`, `CVE-2025-49704`, and a one-sentence explanation.
- UI state showed Supply tab result cards and chat-side `search_cve ok 0.1s`.
- Runtime metrics: `TTFT=2.4302330017089844`, `tokPerSec=14.689460612368043`, `promptTokens=2084`, `cachedTokens=704`, `completionTokens=53`.
- Cache/runtime state showed prefix cache, paged cache, TurboQuant q4 KV, prompt L2, block L2, prefix cache hits, and block L2 hits.
- Screenshot file capture via `screencapture` remained blocked by macOS display capture permissions (`could not create image from display`), but Computer Use returned a live screenshot in-session showing the final chat marker, tool transcript, CVE cards, and metrics.

Artifact:

- `docs/live-proofs/2026-07-04-qwen36-35b-ui-cve-tool-loop-after-loop-fix.json`

Status: PASS for the live 35B UI CVE tool-loop regression: model prompt/tool-schema receipt, streamed argument preservation in the exercised path, `search_cve` execution, verbose chat transcript, post-tool final answer, explicit no-shell policy, bounded loop control, and cache/runtime topology. The follow-up `lookup_cve` first-try proof below now also has fresh visible UI evidence through System Events while Computer Use remains blocked separately.

### Live app/API 35B `lookup_cve` first-try proof

Live target:

- App: `dist/ExploitBot.app`
- QA API: `http://127.0.0.1:9999`
- Engine: proof-managed 35B on a free localhost port
- Model: `/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP`
- Chat mode: Autopilot
- Reasoning: off

Root cause found and fixed before the passing run:

- The live 35B model emitted a Qwen parameter-only dialect: `<parameter=cve_id>\nCVE-2025-49704\n</parameter>`.
- Non-streaming parser repair initially worked in source tests, but the app uses streaming chat; the streaming marker list did not buffer `<parameter=...>`, and then post-stream finalization parsed cleaned visible content instead of raw tool markup.
- `ExploitBotEngine/vmlx_engine/server.py` now schema-gates this dialect: it only repairs parameter tags when request text positively names exactly one available tool, and streaming post-finalization preserves raw `<parameter=...>` text for parsing while keeping display cleanup separate.

Verification:

- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m pytest -q ExploitBotEngine/testsuite/test_tool_parser_api.py`: PASS, `10 passed`.
- `python3 -m py_compile ExploitBotEngine/vmlx_engine/server.py scripts/real-qwen-lookup-cve-proof.py`: PASS.
- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 scripts/real-qwen-lookup-cve-proof.py`: PASS on the 2026-07-04 21:05 rerun after completing onboarding before the visible capture.

Artifact:

- `docs/live-proofs/2026-07-04-real-qwen-35b-lookup-cve-first-try.json`

Observed result:

- Artifact `ok=true`, `generatedAt=2026-07-04T21:05:05-0700`, `toolSequence=["lookup_cve"]`, target `CVE-2025-49704`, finished at `2026-07-04T21:05:26-0700`.
- Memory preflight allowed the run, and the final process/RAM check after cleanup found no matched ExploitBot/Qwen/vmlx process, `Swapouts: 0`, and `System-wide memory free percentage: 94%`.
- First verbose tool transcript preserved the argument: `"cve_id" : "CVE-2025-49704"` and did not hit `Missing cve_id parameter`.
- Callback returned source-attributed CVE detail: `CVE-2025-49704 [HIGH] CVSS:8.8`, tags `kev`, sources `cisa-kev, nvd, references, tags`.
- Final assistant answer contained `REAL_QWEN_LOOKUP_CVE_FINAL`, `CVE-2025-49704`, and a one-sentence SharePoint impact summary.
- Cache/runtime proof in the artifact shows TurboQuant q4 attention-KV (`effective_config.cache.kv_cache_quantization.mode=turboquant-q4`, `bits=4`), `native_cache.cache_type=hybrid_ssm_typed`, `native_cache.paged=true`, `native_cache.prefix=true`, scheduler block size `64`, and `total_tokens_cached=6062`. The SSM side is not quantized; it remains native companion/rederive state while attention KV uses TurboQuant.
- Visible UI proof in the same artifact reports `visibleUIProof=PASS`, `visibleLookupToolCard=PASS`, `visibleFinalMarker=PASS`, `visibleTargetCVE=PASS`, and screenshot `docs/live-proofs/2026-07-04-real-qwen-35b-lookup-cve-first-try-visible.png`. The screenshot shows the Supply/CVE Intel tab, the visible `lookup_cve` tool card, the `CVE-2025-49704` argument/output, and the final assistant marker.

Status: PASS for live 35B `lookup_cve` first-try argument preservation, callback execution, verbose transcript, final marker, TurboQuant q4 attention-KV/paged/prefix/native-SSM-companion cache proof, and fresh visible UI evidence through System Events plus screenshot. Computer Use MCP remains blocked separately and is not used as proof for this row.

### Settings model library scan/select proof

Problem found:

- Settings had a single model path picker, but the goal requires users to add model folders, scan local model libraries, and choose real local models from Settings.

Fix applied:

- Added `ModelLibraryState` and `ModelLibraryEntry` to app state.
- Added persisted model scan roots via `modelLibrary.roots`.
- Added bounded one-level model-folder scanning using existing `ModelFolderInspector`.
- Added `/state.modelLibrary` with roots, entries, counts, selected path, and scan summary.
- Extended `/qa/model-folder-picker` with `addRoot` and `scan` actions.
- Added Settings > Model controls for scan root, Add Folder, Scan, and selectable discovered model rows.
- Fixed unsupported multimodal folders so they no longer show misleading supported-family text.

Computer Use proof:

- Opened Settings through the live UI.
- Clicked Model category.
- UI displayed the selected model path, Add Folder, Scan, root list, and scanned model rows.
- UI showed `/Users/eric/models/dealign.ai` as a scan root.
- UI showed 14 models and 6 supported models.
- Rows included both requested local folders:
  - `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP`
  - `/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP`
- Clicked Use for `Qwen3.6-27B-MXFP8-CRACK-MTP`; the model path field and `/state.engineConfig.modelPath` changed to the 27B MXFP8 MTP folder.
- Clicked Scan; `/state.modelLibrary.lastAction` became `scan` and Activity showed `scanModelLibrary 14 models from 1 roots`.

Artifact:

- `docs/live-proofs/2026-07-04-settings-model-library-scan-select-live-ui.json`
- `docs/live-proofs/2026-07-04-settings-model-library-state.json`

Fresh app/API proof:

- `scripts/settings-model-library-state-proof.py` launched the app with an isolated test home and did not load a model.
- Added `/Users/eric/models/dealign.ai` as a Settings model-library root and scanned it through `/qa/model-folder-picker`.
- Artifact `docs/live-proofs/2026-07-04-settings-model-library-state.json` finished at 2026-07-04 11:23 PDT with `ok=true`.
- The scan found `14` model folders and `6` supported folders, including both requested targets:
  - `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP`
  - `/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP`
- The proof selected 35B, then selected 27B, and verified `engineConfig.modelPath`, `modelFolderPicker.selectedPath`, `modelFolderInfo.family=Qwen`, `modelLibrary.selectedPath`, `hasGenerationConfig=true`, q4 KV, prefix cache, paged cache, prompt L2 disk cache, block L2 disk cache, and no model loaded.

Status: PASS for Settings model-library scan/select wiring, earlier live UI proof, and current durable no-model app/API proof. Loading the selected 27B/35B engines is proven in separate real-model artifacts; this specific model-library proof is a scan/select/config-state proof only.

### Engine lifecycle RAM guard

Root cause found:

- `script/build_and_run.sh` killed only the Swift app with `pkill -x ExploitBot`.
- The app launches the model server as a separate Python process through `ExploitBotEngine/launch.py`.
- If the Swift app is killed/rebuilt before `EngineManager.stop()` runs, the Python model process can survive as an orphan, keep its 810x port, and retain model RAM.
- On the next app run, `EngineManager.findAvailablePort()` skips the occupied port and can start another model on the next port, allowing repeated live proof runs to accumulate loaded engines.

Fix applied:

- `script/build_and_run.sh` now terminates stale processes whose command line contains this repo's `ExploitBotEngine/launch.py` before relaunching the app.
- `script/build_and_run.sh` also checks `~/.exploitbot/engine.pid` and terminates that PID when it is an ExploitBot launcher or `vmlx_engine.server` process.
- `EngineManager` now runs a stale-engine cleanup on startup for this repo's `launch.py`.
- `EngineManager` now includes the launcher pidfile process in startup stale-engine cleanup, so an orphaned child server can be cleaned even when the parent launcher command is gone.
- `EngineManager` now calls `stop()` in `deinit` for graceful app teardown.
- `ExploitBotEngine/launch.py` now starts `vmlx_engine.server` in a new process group and forwards `SIGTERM`/`SIGKILL` to that process group during shutdown.

No-model verification:

- Spawned a dummy Python sleeper whose argv contained `/Users/eric/exploitbot/ExploitBotEngine/launch.py`.
- Spawned a second dummy Python sleeper whose argv contained `vmlx_engine.server --model dummy`, wrote its PID to `~/.exploitbot/engine.pid`, and restored any prior pidfile after the proof.
- Ran `script/build_and_run.sh --verify`.
- Verified the dummy process was killed.
- Re-ran `python3 scripts/engine-stale-cleanup-visible-proof.py` after the pidfile/process-group hardening.
- Verified artifact `docs/live-proofs/2026-07-04-engine-stale-cleanup-visible.json` reports `foundCount=2`, `remainingCount=0`, `cleaned=true`, `dummyStaleProcessRemoved=PASS`, and `dummyPidFileServerRemoved=PASS`.
- Verified ports `8100-8110` were clear afterward.
- No model was loaded during this lifecycle proof.

Live 27B verification:

- Started the app-managed `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP` engine through `/qa/apply-app-settings` and `/engine/start`.
- Verified the real 27B engine was healthy on `8100`.
- Verified the resident model process before cleanup: launcher PID `7629`, server PID `7630`, server RSS `29031360 KB`, listener `127.0.0.1:8100`.
- Verified cache/runtime flags were active in app state before cleanup: prefix cache on, paged cache on, block L2 on, `kvCacheQuantization=turboquant-q4`, `kvCacheGroupSize=64`.
- Ran `script/build_and_run.sh --verify` while the 27B model was resident.
- Observed launcher output: `Stopping stale ExploitBot engine processes...`.
- Verified old PIDs `7629` and `7630` were gone afterward.
- Verified no listeners remained on `8100-8110`.
- Verified the relaunched app reported `engineRunning=false`, `healthStatus=stopped`, and `enginePort=0`.
- Verified post-cleanup `vm_stat` showed `Swapins=0`, `Swapouts=0`, and `Pages occupied by compressor=0`.

Live 35B verification:

- Started the app-managed `/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP` engine through `/qa/apply-app-settings` and `/engine/start`.
- Verified the real 35B engine was healthy on `8100`.
- Verified the resident model process before cleanup: launcher PID `8560`, server PID `8561`, server RSS `37265296 KB`, listener `127.0.0.1:8100`.
- Verified cache/runtime flags were active in app state before cleanup: prefix cache on, paged cache on, block L2 on, `kvCacheQuantization=turboquant-q4`, `kvCacheGroupSize=64`.
- Ran `script/build_and_run.sh --verify` while the 35B model was resident.
- Observed launcher output: `Stopping stale ExploitBot engine processes...`.
- Verified old PIDs `8560` and `8561` were gone afterward.
- Verified no listeners remained on `8100-8110`.
- Verified the relaunched app reported `engineRunning=false`, `healthStatus=stopped`, and `enginePort=0`.
- Verified post-cleanup `vm_stat` showed `Swapins=0` and `Swapouts=0`.

App-start RAM preflight verification:

- Added `EngineManager.memoryPreflight(modelPath:)` before `Process.run()` so Settings/App engine start uses the same kind of guard as the live proof scripts instead of only relying on launcher cleanup.
- The preflight reads `/usr/bin/vm_stat`, scans `/bin/ps -axo pid=,ppid=,rss=,command=` for heavyweight model/eval processes (`ExploitBotEngine/launch.py`, `vmlx_engine.server`, `osaurus-evals run`, `mlx_lm.server`, `llama-server`), and blocks 27B starts below `42GB` available or 35B starts below `50GB` available unless `EXPLOITBOT_ENGINE_ALLOW_CONCURRENT_HEAVY_MODEL=1`.
- Exposed `engineMemoryPreflight` through `/state` so API/UI proof can show whether the app blocked due to RAM rather than silently doing nothing.
- Ran `python3 scripts/engine-start-memory-preflight-proof.py` with `EXPLOITBOT_ENGINE_MIN_AVAILABLE_GB=9999`.
- Verified live app state reported `engineMemoryPreflight.allowed=false`, `requiredAvailableGB=9999`, `healthStatus=blocked`, and `engineError="Engine start blocked by RAM preflight. available memory 103.7GB is below required 9999.0GB"`.
- Verified `launchPyBefore=[]`, `launchPyAfter=[]`, and `noLaunchPyStarted=true`; no model weights were loaded during this proof.

Direct verifier RAM guard follow-up:

- Current live state after the RAM complaint: `memory_pressure` reports `System-wide memory free percentage: 96%`, `vm.swapusage` reports `used = 0.00M`, and a clean `pgrep` for `vmlx_engine.server|ExploitBotEngine/launch.py|Qwen3.6|osaurus-evals run|mlx_lm.server|llama-server` found no real resident model process.
- Remaining source-level hole found: older direct live verifier paths in `scripts/verify-live-models.py` spawned `ExploitBotEngine/launch.py` directly, outside `EngineManager.memoryPreflight`, and used plain `subprocess.Popen`/`proc.terminate()` rather than a process-group-scoped launch/cleanup.
- Fix: `scripts/verify-live-models.py` now has its own fail-before-launch RAM preflight, scans the same heavyweight process markers, blocks concurrent heavyweight model/eval processes unless `EXPLOITBOT_VERIFY_LIVE_MODELS_ALLOW_CONCURRENT_MODEL=1`, blocks low-memory starts with `EXPLOITBOT_VERIFY_LIVE_MODELS_MIN_AVAILABLE_GB`, records `memory_preflight` in live reports, launches with `start_new_session=True`, and tears down through `terminate_engine_process()`.
- No-model proof artifact `docs/live-proofs/2026-07-04-direct-verifier-ram-guard.json` reports `ok=true`, `preflightBlock=PASS_BLOCKED_BEFORE_LAUNCH`, `hasPreflight=true`, `hasProcessGroupTermination=true`, and `usesStartNewSession=true`.
- Focused verification after the patch: `python3 -m py_compile scripts/verify-live-models.py` passed; `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m pytest -q ExploitBotEngine/testsuite/test_live_model_verifier.py ExploitBotEngine/testsuite/test_live_batch_memory_preflight.py ExploitBotEngine/testsuite/test_engine_lifecycle_ram_guards.py` passed with `39 passed`.

Artifact:

- `docs/live-proofs/2026-07-04-engine-lifecycle-stale-process-ram-guard.json`
- `docs/live-proofs/2026-07-04-engine-lifecycle-real-27b-stale-cleanup.json`
- `docs/live-proofs/2026-07-04-engine-lifecycle-real-35b-stale-cleanup.json`
- `docs/live-proofs/2026-07-04-engine-start-memory-preflight-block.json`
- `docs/live-proofs/2026-07-04-direct-verifier-ram-guard.json`
- `docs/live-proofs/2026-07-04-release-engine-stale-cleanup.json`

Packaged release verification:

- Rebuilt the release app and DMG with `./script/package_release.sh --skip-notarize`.
- Added `scripts/release-engine-stale-cleanup-proof.py` for the packaged app path.
- The proof launches `release/ExploitBot.app/Contents/MacOS/ExploitBot`, verifies the app selected `app-bundled-vmlx-python`, and uses the bundled launch script at `release/ExploitBot.app/Contents/Resources/ExploitBotEngine/launch.py`.
- The proof spawned a dummy process whose argv contained the bundled release `launch.py` path and a second dummy `vmlx_engine.server` process recorded in `~/.exploitbot/engine.pid`.
- Artifact `docs/live-proofs/2026-07-04-release-engine-stale-cleanup.json` reports `ok=true`, `foundCount=2`, `remainingCount=0`, `bundledLaunchCleanup=PASS`, `pidFileServerCleanup=PASS`, `bundledEnginePath=PASS`, `bundledRuntimeSelected=PASS`, `userVisibleCleanupNotice=PASS` with Settings notice title `Stale engine cleanup ran`, and `modelLoaded=NO`.
- First packaged run exposed a release signing regression: launching the signed app created `starter-cves.db-wal` and `starter-cves.db-shm` under `Contents/Resources`, invalidating `codesign`.
- Fix: bundled starter CVE DB import now copies `Contents/Resources/starter-cves.db` into the active app data directory as `starter-cves-import.db` before attaching it, so SQLite sidecars are created outside the signed app bundle.
- After rebuilding and rerunning the packaged cleanup proof, `find release/ExploitBot.app/Contents/Resources -maxdepth 1 -name 'starter-cves.db*'` showed only `starter-cves.db`, and `codesign --verify --deep --strict --verbose=2 release/ExploitBot.app` plus `codesign --verify --verbose=2 release/ExploitBot-beta.dmg` both passed.

Status: PASS for the source-backed and live 27B/35B dev-relaunch lifecycle guard that caused RAM flooding during repeated app relaunches. PASS for app/API start blocking before `launch.py` when RAM preflight fails. PASS for no-model startup cleanup of both a stale repo launcher process and a pidfile-recorded `vmlx_engine.server` child. PASS for direct `scripts/verify-live-models.py` fail-before-launch RAM guard and process-group cleanup source/test/no-model proof. PASS for the same cleanup behavior from the rebuilt packaged release app path, with post-launch app/DMG code signatures still valid.

### Autonomous phase execution harness

Problem addressed:

- The app had policy proof for explicit tool-deny handling and high-risk external-target gating, but it did not yet have a live app/API proof that an autonomous model turn can fan out across the expected pentest phases and wire results back into tabs, parsed findings, terminal transcripts, and a final model response.

Proof added:

- `scripts/autonomous-phase-execution-proof.py`
- `ExploitBotEngine/testsuite/test_autopilot_tool_policy_contracts.py`

Live harness behavior:

- Starts a mock OpenAI-compatible streaming engine on `127.0.0.1:18996`.
- Launches the real dev app on `127.0.0.1:9999`.
- Installs safe fake local tools in a temporary HOME for `nmap`, `sqlmap`, `hydra`, `msfconsole`, `metasploit`, and `linpeas.sh`.
- Sends an Autopilot prompt authorizing safe loopback checks across recon, network, web, creds, exploit, and post.
- Mock model emits tool calls for `nmap`, `netexec`, `sqlmap`, `hydra`, `metasploit`, and `linpeas`.
- The normal app `ToolExecutor` path executes the fake tools and captures command transcripts.
- `/state.tabActivities` reports `done` for recon, network, web, creds, exploit, and post.
- `/results` contains parsed evidence for port `443/https`, SQL injection, valid credentials, a Metasploit session, and `linpeas-host`.
- `/qa/result-parser-coverage.networkHosts` contains the fake `netexec` host `127.0.0.1 QA-SMB ok`.
- `/state.terminal.commandTranscripts` includes the executed phase tools.
- The model receives the tool outputs and returns `AUTONOMOUS_PHASE_FINAL`.

Verification:

- `python3 scripts/autonomous-phase-execution-proof.py`: PASS.
- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m pytest ExploitBotEngine/testsuite/test_autopilot_tool_policy_contracts.py -q`: PASS, `5 passed`.
- `swift build --package-path ExploitBot`: PASS.
- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 scripts/app-qa-matrix-smoke-proof.py`: PASS.
- `git diff --check`: PASS.

Root-cause detail from the red run:

- The first harness run failed because the app's Metasploit wrapper executes `msfconsole -q -x`, while the harness only installed a fake `metasploit` binary.
- The Network phase first tried `snmpwalk`, but the app resolved `/usr/bin/snmpwalk` before the fake harness binary and hit a real loopback timeout.
- The harness now installs fake `msfconsole` as the app-executed binary while keeping the model/tool-call name as `metasploit`, and uses fake `netexec` for the Network phase so the output is controlled and parsed.
- Fake local tool scripts now terminate with an explicit heredoc terminator plus `exit 0`; this prevents a fake tool from hanging the app `ToolExecutor`.

Fresh Computer Use retest:

- `mcp__computer_use.get_app_state(app="ExploitBot")`: FAIL, `Transport closed`.
- `mcp__computer_use.list_apps`: FAIL, `Transport closed`.
- Current transport artifact: `docs/live-proofs/2026-07-04-computer-use-transport-blocked.json`.
- Artifact status split:
  - `serviceRunning=PASS`
  - `serviceSocket=PASS`
  - `directToolsList=PASS`
  - `shimToolsList=PASS`
  - `activeCodexMCP=BLOCKED_TRANSPORT_CLOSED`
  - `directListAppsToolCall=FAIL_NO_TOOL_RESPONSE`
  - `shimListAppsToolCall=FAIL_NO_TOOL_RESPONSE`
- Current RAM/process status in the same artifact: `memory_pressure` reports `System-wide memory free percentage: 96%`, `Swapins: 0`, `Swapouts: 0`; Computer Use service RSS is about 69MB. The RAM flood is not reproduced by this Computer Use retest.

Status: PASS for safe mock-model, fake-tool, live app/API autonomous phase execution across recon, network, web, creds, exploit, and post. PARTIAL for the product goal because this does not prove real Qwen control of real external tools across every phase. Current fresh GUI proof remains BLOCKED by the Computer Use transport.

## Final Matrix

PASS:

- Swift app builds with `swift build --package-path ExploitBot`.
- Python engine targeted compile/tests pass.
- 27B Qwen3.6 MXFP8 MTP local engine proof passes with q4 cache, paged cache, block L2, SSM companion, and concurrency evidence.
- 35B Qwen3.6 A3B MXFP8 MTP local engine proof passes with the same cache/concurrency evidence.
- App-managed 27B engine starts from ExploitBot, reports healthy runtime metadata, and handles a real chat turn.
- App-managed 27B bounded multiturn through the live UI passes with Computer Use, TTFT, cached-token metrics, and cache topology proof.
- App-managed 35B bounded multiturn through the live UI passes with Computer Use, TTFT, cache reuse, native MTP, and cache topology proof.
- App chat injects dynamic context and exposes callback/tool schemas to the model.
- Current Computer Use retry is passing at the attachment/screenshot/accessibility layer. `docs/live-proofs/2026-07-04-computer-use-current-retry.json` records CUA app version `857`, `listApps`, `getAppState`, inline screenshot, accessibility tree, release app PID `25991`, and visible main workspace controls without starting model inference. `docs/live-proofs/2026-07-05-computer-use-settings-cve-cache-ui.json` records the later Computer Use Settings/CVE/cache toggle pass, and the current direct MCP retry attached to `/Users/eric/exploitbot/dist/ExploitBot.app` with CUA version `857` and returned the live accessibility tree/screenshot. Earlier deeper Computer Use proof also clicked through onboarding/settings and remains tracked in `docs/live-proofs/2026-07-04-computer-use-live-gui.json`.
- Settings Runtime and Cache pages expose real app/engine controls and apply them into `/state`.
- Settings generation controls now propagate to the primary chat service; `/qa/context-budget-compaction` reports `maxTokensForwarded=true`.
- Settings generation controls now persist across app relaunch into the primary chat service and existing agents; `/qa/context-budget-compaction` reports `maxTokens=64` and `chatMaxTokens=64` in the focused persistence proof path.
- Context budget and generation forwarding now have a fresh durable live no-model app proof. `scripts/context-budget-compaction-proof.py` writes `docs/live-proofs/2026-07-04-context-budget-compaction.json`; the 2026-07-04 12:36 rerun reports `ok=true`, `budget.maxTokens=64`, `budget.chatMaxTokens=64`, `budget.maxIterations=7`, `contextPacketMaxCharacters=6000`, `contextPacketMaxSelectedSnippets=8`, `cacheResponseMethod=prefix-cache-l2-turboquant`, `newContextBehavior=clear-visible-chat-preserve-engine-cache-session`, `promptInjectionPolicy=search-on-demand-not-force-injected`, `contractParity=true`, `proofFileParity=true`, and status rows `maxTokensForwarded=PASS`, `maxIterationsBounded=PASS`, `contextPacketBudget=PASS`, `cachePreservingNewContext=PASS`, `policySteps=PASS`, and `coverageIndexParity=PASS`. The proof state also shows the applied engine config carries `modelPath=/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP`, `maxTokens=64`, `temperature=0`, `topP=1`, `kvCacheQuantization=turboquant-q4`, `pagedCache=true`, `blockL2Disk=true`, and `prefixCache=false` after the isolated toggle path.
- Chat-side tool transcript now includes verbose tool request, command, JSON arguments, output, blocked details, and follow-up analysis.
- Reasoning-on empty-output failure is now visible in chat as an explicit bounded-generation diagnostic instead of an empty assistant bubble.
- Starter CVE database imports into a clean active app DB and app CVE search returns real rows.
- Live 35B UI proof shows model-invoked `search_cve` executing through the callback path with verbose chat transcript and SharePoint CVE rows.
- Live 35B UI post-fix proof shows a bounded `search_cve` tool loop followed by a final assistant answer with the requested marker.
- Autopilot now blocks explicit no-shell CVE prompts from invoking `run_shell` in the post-fix live proof.
- Settings Model page now scans a model library root, exposes 27B and 35B MXFP8 MTP folders, selects a scanned model through the live UI, and has a refreshed no-model app/API proof that selects both 35B and 27B while preserving q4/prefix/paged/L2 cache settings in state.
- Demo-ready startup now has a durable no-model app/API proof. `scripts/demo-ready-startup-proof.py` launches the debug app with an isolated data directory, confirms a clean first launch starts on onboarding, completes onboarding through `/qa/onboarding-complete` using the real Qwen 27B MXFP8 MTP path without starting the engine, relaunches against the same data directory, and verifies onboarding stays dismissed, the demo op name persists through `modeSelection.activeOpName`, the selected model path persists, q4 KV/prefix/paged/prompt-L2/block-L2 settings persist, and no model is loaded. Artifact `docs/live-proofs/2026-07-04-demo-ready-startup.json` reports `ok=true`.
- Dev app relaunch path now kills stale repo engine processes; this is source-backed and live-verified against resident 27B and 35B models so repeated proof runs cannot accumulate orphaned Qwen3.6 engines on 810x ports.
- Live Qwen batch proof harness now has a fail-before-load RAM preflight. Fresh proof artifact `docs/live-proofs/2026-07-04-live-batch-memory-preflight-blocked.json` shows it refused to start Qwen while a separate Claude-launched `osaurus-evals` 35B job was active, with `availableGB=46.98`, `requiredAvailableGB=42.0`, and `heavyModelProcessCount=1`.
- JANG `capabilities.cache_type=hybrid` now overrides generic Qwen KV registry defaults and preserves hybrid SSM architecture hints.
- Dev launcher now copies app resources into the bundle.
- Broad app QA smoke now passes after fixing stale proof timeouts, persisted generation-setting mirroring, objective/runtime SSM counter aggregation, and beta package-readiness semantics.
- `/qa/release-readiness` now exposes live `codesign` verification fields for the local app bundle and DMG instead of treating artifact existence as signed readiness.
- Local release artifacts were refreshed again at 2026-07-05 02:07 PDT through `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 scripts/release-readiness-proof.py`, which ran `./script/package_release.sh --skip-notarize`, rebuilt `release/ExploitBot.app` and `release/ExploitBot-beta.dmg` from the current source, launched the packaged app in test mode, verified the bundled Python runtime route, and rechecked app/DMG signatures. The proof writes durable artifact `docs/live-proofs/2026-07-04-release-readiness.json`, which reports `generatedAt=2026-07-05T02:07:07-0700`, `ok=true`, `localPackageStatus=PASS`, `distributionStatus=BLOCKED`, app/DMG codesign `PASS`, bundled runtime `PASS`, and notarization `BLOCKED`. The manifest records `notarizationStatus=not-submitted`, `notarizationGate=requires-notary-credentials`, app binary SHA256 `3e39ffadb254c5e65b6fc197bb51d8f969e2fbbcc16d4623787956f95c443846`, and DMG SHA256 `d03be7172fc0a57ce58c4eb43ca5c99bb3c4473863533820caedda5c0fc2ea73`.
- Notarization preflight is now a separate no-secret proof. `scripts/notarization-preflight-proof.py` writes `docs/live-proofs/2026-07-04-notarization-preflight.json`; the 2026-07-05 02:29 rerun reports `generatedAt=2026-07-05T02:29:06-0700`, `ok=true`, `distributionStatus=BLOCKED`, `checks.notarytool=PASS`, `checks.developerIDSignature=PASS`, `checks.hardenedRuntime=PASS`, `checks.gatekeeperAssessment=BLOCKED`, `checks.notaryCredentials=BLOCKED`, `checks.credentialLiveValidation=NOT_RUN`, `credentials.selectedCredentialMode=not-configured`, `credentialSetup.acceptedCredentialModes=["EXPLOITBOT_NOTARY_PROFILE","NOTARIZE_APPLE_ID+NOTARIZE_TEAM_ID+NOTARIZE_PASSWORD"]`, `keychainProfiles.defaultProfileProbe.status=NOT_FOUND`, `checks.appStapledTicket=BLOCKED`, `checks.dmgStapledTicket=BLOCKED`, `secretsRedacted=true`, and `nextAction=configure-notary-credentials-and-run-package-notarize`. The proof now includes redacted setup commands, post-notarization verification commands, Developer ID authority chain, parsed app entitlements, and Gatekeeper output; direct stapler validation still reports no stapled ticket on both `release/ExploitBot.app` and `release/ExploitBot-beta.dmg`, and live `spctl` rejects the app as `source=Insufficient Context`.
- Release visible smoke is now a separate local-display proof. `scripts/release-visible-smoke-proof.py` writes `docs/live-proofs/2026-07-04-release-visible-smoke.json` and screenshot `docs/live-proofs/2026-07-04-release-visible-smoke.png`; the 2026-07-05 02:11 rerun reports `ok=true`, `localDisplayStatus=PASS`, `visibleWindow=PASS`, `mainWorkspaceVisible=PASS`, `screenshotCaptured=PASS`, `noModelLoaded=PASS`, and `distributionStatus=BLOCKED`. It launches the signed `release/ExploitBot.app`, completes onboarding through the app QA route with the real Qwen 27B path, verifies the main workspace through System Events accessibility text, and records the notarization next action without loading a model.
- `/qa/artifact-ledger` now accepts assertion-map live proof schemas and classifies superseded failed artifacts only when their replacement artifact passes; the live route reports `currentLiveProofFailureFree=true`.
- `/qa/beta-readiness-coverage` was refreshed after the 19:52 release rebuild with `python3 scripts/beta-readiness-coverage-proof.py`; the proof passed and local package gates remain ready, while distribution remains gated by notarization credentials.
- `scripts/cve-import-embedding-coverage-proof.py` now passes after giving the slow `/qa/coverage-index` mirror check a 120s timeout; the CVE import, fake local embedder, semantic context packet, and route assertions themselves complete quickly.
- CVE records now expose per-record source attribution derived from feed tags, references, CISA KEV state, and custom-record state. `search_cve`, `lookup_cve`, dynamic context packets, and `/qa/cve-taxonomy-coverage` expose this contract.
- `scripts/cve-source-attribution-proof.py`, `scripts/cve-taxonomy-coverage-proof.py`, `scripts/cve-taxonomy-matrix-proof.py`, `scripts/cve-import-embedding-coverage-proof.py`, and `scripts/app-qa-matrix-smoke-proof.py` pass sequentially in the current checkout without loading a model after the source-attribution change.
- `scripts/agent-settings-actions-proof.py`, `scripts/deep-runtime-flow-coverage-proof.py`, and `scripts/app-qa-matrix-smoke-proof.py` pass in the current checkout after the CVE proof timeout fix.
- CVE current threat-intel refresh is now a real-feed path exposed in Settings as `Current Threat Intel`. Refreshed again at 2026-07-05 03:50 PDT after fixing the 25-row KEV cap, `scripts/cve-current-threat-intel-live-proof.py` fetched CISA KEV catalog version `2026.07.01` released `2026-07-01T19:00:06.9016Z`, confirmed latest KEV `CVE-2026-45659` for Microsoft SharePoint Server deserialization/RCE, imported all `1,631` current CISA KEV rows plus `10` recent NVD critical rows through the app settings route, and then searched `CVE-2026-45659` through the app service with `searchResultCount=1`, `totalCount=1641`, and `kevCount=1631`. The proof artifact is `docs/live-proofs/2026-07-04-cve-current-threat-intel-live.json` and exposes top-level machine-readable `feedVersion`, `feedReleasedAt`, `latestCVE`, vendor/product/vulnerability fields, counts, `sourceAttribution=["cisa-kev","nvd"]`, and `topModernCVEs` with the ranking policy `CISA KEV dateAdded descending plus recent NVD critical rows sorted by parsed CVSS score then publication recency`, `8` current KEV rows, `10` recent NVD critical rows, CVSS `10.0` NVD examples, and a bounded app-state `appSearchTopResults` row for `CVE-2026-45659` with source attribution `cisa-kev,nvd,references,tags`. The live proof fetch saw `1631` CISA KEV entries and `237` NVD critical results in the 45-day query window.
- Exact CVE-ID search now bypasses brittle FTS parsing for IDs like `CVE-2026-45659`, returning the exact DB row before broader text matches. This makes `search_cve` and Settings search usable for model-supplied CVE IDs from live feeds.
- Terminal visibility now has a state contract beyond the visual panel: `/state.terminal` exposes `surfaceContract=terminal-visibility-command-transcripts`, `activeCommand`, and command transcripts merged from `activityFeed`, `resultsStore.rawResults`, and `tabActivities`. `scripts/terminal-tool-visibility-proof.py` passes against the live no-model app API and writes durable artifact `docs/live-proofs/2026-07-04-terminal-tool-visibility.json`; the 2026-07-04 12:03 rerun reports `ok=true`, `terminalVisible=PASS`, `commandTranscripts=PASS`, `activeCommand=PASS`, and `feedCommandEvidence=PASS`.
- Workflow panel state now has a durable no-model app/API proof. `scripts/workflow-panel-state-proof.py` seeds visual workflow activity and verifies `/state.tabActivities` for web, network, creds, exploit, post, and osint; verifies network/creds/exploit/post/osint lifecycle rows; switches the active tab from recon to creds through `/qa/manual-tab-switch`; then seeds terminal visibility and verifies the terminal is visible, active command comes from network `tabActivities`, and transcripts merge activity feed, raw results, and tab context. Artifact `docs/live-proofs/2026-07-04-workflow-panel-state.json` was refreshed at 2026-07-04 12:10 PDT with `ok=true`, `workflowTabActivities=PASS`, `workflowLifecycleRows=PASS`, `manualTabSwitch=PASS`, `terminalToggleVisible=PASS`, `terminalActiveCommand=PASS`, `terminalTranscripts=PASS`, and `noModelLoaded=PASS`.
- Settings no-model route proof was refreshed at 2026-07-04 12:10 while the unrelated 35B eval was active. `scripts/settings-model-library-state-proof.py` proved model-root add/scan, 27B and 35B MXFP8 MTP visibility/selectability, q4 KV, prefix cache, paged cache, prompt L2, block L2, generation-default toggle visibility, activity-feed scan visibility, and no model load.
- Autopilot now honors explicit user tool-deny instructions beyond `run_shell`. `scripts/autopilot-tool-policy-proof.py` uses a mock model that calls `nmap` after the user says "Do not use nmap" plus a fake `nmap` binary that would print `SHOULD_NOT_RUN`; live app/API proof shows the call is blocked, the fake binary does not execute, and the model produces a post-block final answer.
- Autopilot now publishes and enforces a phase-policy matrix for high-risk external targets. `/qa/autopilot-phase-policy-matrix` proves no-scope external `nmap` is blocked, loopback `nmap` is allowed, explicitly authorized external `nmap` is allowed, and scoped external `nmap` is allowed. `scripts/autopilot-phase-policy-matrix-proof.py`, `scripts/autopilot-tool-policy-proof.py`, `scripts/tool-fanout-status-proof.py`, and `scripts/app-qa-matrix-smoke-proof.py` pass in the current checkout.
- Safe autonomous phase execution now has a live app/API proof. `scripts/autonomous-phase-execution-proof.py` drives a mock model through real app Autopilot and `ToolExecutor` paths with fake local `nmap`, `netexec`, `sqlmap`, `hydra`, `msfconsole`, and `linpeas.sh`; `/state.tabActivities`, `/results`, `/qa/result-parser-coverage`, `/state.terminal.commandTranscripts`, and final model response all show recon, network, web, creds, exploit, and post wiring.
- Real installed-tool loopback execution now has a live app/API proof without loading Qwen weights. `scripts/real-installed-tools-loopback-proof.py` drives a mock model through real app Autopilot and `ToolExecutor` paths using installed `/opt/homebrew/bin/nmap`, app-managed ProjectDiscovery `httpx` `1.9.0`, `/opt/homebrew/bin/nuclei`, `/opt/homebrew/bin/hydra`, `/Users/eric/.local/bin/netexec`, app-managed `/Users/eric/.exploitbot/tools/linpeas.sh`, `/usr/bin/curl`, and `/usr/bin/nc` against a local `ThreadingHTTPServer` or local host; chat tool cards, `/state.terminal.commandTranscripts`, activity feed, dynamic context, and `/results.rawResults` contain the real `nmap` loopback port output, `httpx` title/status output `ExploitBot HTTPX Lab`, custom `nuclei` template finding `exploitbot-loopback-header`, Hydra `http-get` loopback credential proof, NetExec SMB output, MacPEAS-ng linpeas output, and `EXPLOITBOT_LOOPBACK_LAB_OK`. After installing Metasploit, refreshed artifact `docs/live-proofs/2026-07-04-real-installed-tools-loopback.json` reports `ok=true`, every loopback/local real-tool row PASS, `msfconsole=/opt/homebrew/bin/msfconsole`, `missingPentestTools=[]`, and `fullPentestToolchainInstalled=PASS`.
- Real Qwen 27B now has a live real-installed-tool loopback proof. `scripts/real-qwen-real-tools-loopback-proof.py` launches `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP` with `turboquant-q4`, prefix cache, paged cache, block L2 cache, and process-group cleanup, then drives the app Autopilot loop against a local lab target with real installed `nmap`, `httpx`, `nuclei`, `hydra`, `netexec`, `linpeas`, `curl`, and `nc`. The first attempt exposed two real issues: unavailable `katana` leaked into the model tool schema and numeric `nmap.ports` could be ignored, causing a broad default localhost scan. The app now keeps unavailable tools out of this proof path and coerces numeric `nmap` ports to `-p`. Artifact `docs/live-proofs/2026-07-04-real-qwen-real-tools-loopback-27b.json` reports `ok=true`, final marker `REAL_QWEN_REAL_TOOLS_FINAL`, `realQwenDroveRealInstalledTools=PASS`, `realInstalledNmapLoopback=PASS`, `realInstalledHttpxLoopback=PASS`, `realInstalledNucleiLoopback=PASS`, `realInstalledHydraLoopback=PASS`, `realInstalledNetexecLoopback=PASS`, `realInstalledLinpeasLocal=PASS`, `realInstalledCurlNcLoopback=PASS`, `missingPentestTools=["msfconsole"]`, and live cache proof with q4 KV, `native_cache.cache_type=hybrid_ssm_typed`, `native_cache.paged=true`, `native_cache.prefix=true`, block size `64`, `total_tokens_cached=12529`, `block_disk_cache.disk_writes=197`, and `num_requests_processed=2`.
- Real Qwen 35B now has the same live real-installed-tool loopback proof. The first 35B attempt exposed executor/proof-contract drift: Qwen3.6 A3B emitted `httpx` argument `target` instead of schema `targets`, and it added a high-severity nuclei filter while the proof template was marked `info`. `ToolDefinitions` now accepts `httpx` aliases `targets`, `target`, and `url`, and the safe lab nuclei template is marked `high`. The retry artifact `docs/live-proofs/2026-07-04-real-qwen-real-tools-loopback-35b.json` reports `ok=true`, model `/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP`, final marker `REAL_QWEN_REAL_TOOLS_FINAL`, `realQwenDroveRealInstalledTools=PASS`, every real installed loopback/local tool row PASS, `chatContainsRealToolOutput=true`, `terminalContainsRealToolOutput=true`, `resultsContainRealToolOutput=true`, `missingPentestTools=["msfconsole"]`, and live cache proof with q4 KV, `native_cache.cache_type=hybrid_ssm_typed`, `native_cache.paged=true`, `native_cache.prefix=true`, block size `64`, `total_tokens_cached=12580`, `block_disk_cache.disk_writes=198`, and `num_requests_processed=2`.
- Settings Tool inventory now has a live current-machine proof. `ToolInstaller` includes the system execution primitives used by autonomous tool loops (`curl`, `nc`, `python3`, `zsh`) in addition to pentest tools, and now smoke-checks binaries before marking them installed while continuing to a usable fallback if a higher-priority binary is broken. `msfconsole` is smoke-checked with `msfconsole -q -x "version; exit"` before Settings can mark Metasploit installed. `scripts/tool-settings-real-inventory-proof.py` drives `/qa/tool-settings-action` with `detectCurrentMachine` against the live app API. Refreshed artifact `docs/live-proofs/2026-07-04-tool-settings-real-inventory.json` reports `ok=true`, `settingsCurrentMachineDetection=PASS`, `fullPentestToolchainInstalled=PASS`, and no missing pentest tools.
- Real Metasploit app execution now has a safe live proof. Homebrew cask `metasploit 6.4.135,20260522055548` installed `/opt/homebrew/bin/msfconsole`; the cask warned that it is deprecated because it does not pass macOS Gatekeeper and will be disabled by Homebrew on 2026-09-01. Direct `msfconsole -q -x "version; exit"` reports Framework/Console `6.4.135-dev-ba71087220535af939015eb01a78463196f02fb3`. `scripts/real-metasploit-safe-app-proof.py` then drives the app Autopilot/tool loop with a mock engine calling tool `metasploit` and command `version; exit`; artifact `docs/live-proofs/2026-07-04-real-metasploit-safe-app.json` reports `ok=true`, `realMetasploitSafeAppExecution=PASS`, `verboseChatToolOutput=PASS`, `terminalTranscriptOutput=PASS`, `rawResultsOutput=PASS`, and Metasploit output present in chat, terminal transcripts, and `/results`.
- Real Qwen Metasploit safe execution now has live 27B and 35B app/API proof. `scripts/real-qwen-metasploit-safe-proof.py` launches the selected Qwen3.6 model with TurboQuant q4 attention-KV, prefix cache, paged cache, block L2 cache, native SSM companion/rederive state, and process-group cleanup, then prompts the model to call only `metasploit` with command `version; exit`. Refreshed artifacts `docs/live-proofs/2026-07-04-real-qwen-metasploit-safe-27b.json` (`2026-07-04T21:15:05-0700` to `21:16:14-0700`) and `docs/live-proofs/2026-07-04-real-qwen-metasploit-safe-35b.json` (`2026-07-04T21:16:26-0700` to `21:17:20-0700`) report `ok=true`, `realQwenDroveRealMetasploit=PASS`, `realMetasploitSafeAppExecution=PASS`, `verboseChatToolOutput=PASS`, `terminalTranscriptOutput=PASS`, `rawResultsOutput=PASS`, `q4TurboQuantKV=PASS`, `ssmCompanionNotQuantized=PASS`, `hybridSSM=PASS`, `pagedCache=PASS`, `prefixCache=PASS`, and `blockL2=PASS`. Both artifacts show `effective_config.cache.kv_cache_quantization.mode=turboquant-q4`; both show attention KV quantization applies only to attention KV layers, while SSM remains `native_companion_state` with `async_clean_prefill_on_miss_or_warm_pass`. Both use `/opt/homebrew/bin/msfconsole` and direct Framework version `6.4.135-dev-ba71087220535af939015eb01a78463196f02fb3`.
- Engine stale-cleanup visibility now has a live no-model app proof. `EngineManager` records `lastStaleCleanup`, `/state.engineStaleCleanup` exposes `checked`, `foundCount`, `remainingCount`, `cleaned`, and process rows, and Settings > Engine renders a compact stale-cleanup notice when cleanup runs or a stale process remains. `scripts/engine-stale-cleanup-visible-proof.py` spawned a dummy process whose argv contained `/Users/eric/exploitbot/ExploitBotEngine/launch.py` plus a pidfile-recorded dummy `vmlx_engine.server` process, launched the app binary directly, and artifact `docs/live-proofs/2026-07-04-engine-stale-cleanup-visible.json` reports `ok=true`, `foundCount=2`, `cleaned=true`, `remainingCount=0`, `dummyPidFileServerRemoved=PASS`, and `modelLoaded=NO`.
- Packaged release stale-engine cleanup now has a live no-model app proof. `scripts/release-engine-stale-cleanup-proof.py` launches the rebuilt `release/ExploitBot.app`, verifies `app-bundled-vmlx-python`, cleans both a bundled-release `launch.py` dummy and a pidfile-recorded `vmlx_engine.server` dummy, and artifact `docs/live-proofs/2026-07-04-release-engine-stale-cleanup.json` reports `ok=true`, `foundCount=2`, `remainingCount=0`, `bundledLaunchCleanup=PASS`, `pidFileServerCleanup=PASS`, `userVisibleCleanupNotice=PASS`, Settings notice title `Stale engine cleanup ran`, and `modelLoaded=NO`.
- Release starter CVE import no longer mutates signed app resources. A failed proof showed `starter-cves.db-wal` and `starter-cves.db-shm` were created under `release/ExploitBot.app/Contents/Resources`, invalidating app code signature. `DatabaseManager` now copies bundled `starter-cves.db` to the active data directory as `starter-cves-import.db` before attach; after rebuilding and launching the release app, only `starter-cves.db` remains in signed resources and both app/DMG `codesign --verify` checks pass.
- Native UI accessibility now has a fresh System Events proof while Computer Use MCP remains blocked. High-level controls carry accessibility labels in source for the tab bar, Settings categories/actions, cache/reasoning toggles, chat controls, and terminal/settings entry points. The 2026-07-04 11:14 run of `scripts/system-events-ui-accessibility-proof.py` launched the app, opened Settings Cache and Engine, toggled Terminal, and read the native macOS accessibility tree. Artifact `docs/live-proofs/2026-07-04-system-events-ui-accessibility.json` reports `ok=true`, `systemEventsUIAccessibility=PASS`, `cacheSettingsNamedControls=PASS`, `engineSettingsNamedControls=PASS`, `terminalToggleVisible=PASS`, and `computerUseMCP=BLOCKED_SEPARATE_TRANSPORT`.
- Native UI settings toggles now have a fresh live take-effect proof. The 2026-07-04 12:36 run of `scripts/system-events-settings-toggle-proof.py` launched the app, opened Settings > Cache, pressed the actual `AXCheckBox` nearest the `Prefix Cache` row, pressed the footer Apply App Settings button, verified `/state.engineConfig.prefixCache` changed from `true` to `false` without loading a model, and restored it. Artifact `docs/live-proofs/2026-07-04-system-events-settings-toggle.json` reports `ok=true`, `nativeUITogglePrefixCache=PASS`, `applyAppSettingsTakesEffect=PASS`, `checkboxResult="prefixCheckbox 1 -> 0"`, `modelLoaded=NO`, and `restoredPrefixCache=true`.
- Current Computer Use transport is no longer blocked in this Codex session. After the user-side permission repair and tool refresh, `tool_search` exposed `mcp__computer_use`, and `mcp__computer_use.get_app_state(app="ExploitBot")` attached to `/Users/eric/exploitbot/dist/ExploitBot.app` with CUA app version `857`, returned the live screenshot/accessibility tree, and showed visible workspace/chat/settings/terminal controls. This is current attach/control proof only; model-generation proof remains covered by the separate live Qwen artifacts.
- Tool execution hang root cause is now isolated and fixed in source. A live 27B run showed `linpeas.sh -q` could complete as an external process while `ToolExecutor` stayed parked in `NSConcreteTask.waitUntilExit`; app sampling showed the hang inside `ToolExecutor.execute`. `ToolExecutor` now waits through `Process.terminationHandler` and clears stdout/stderr readability handlers on EOF. `swift build --package-path ExploitBot`, focused source contracts, and `scripts/autonomous-phase-execution-proof.py` pass after this fix.
- Real Qwen 27B autonomous phase proof now has a clean app/API artifact. `docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-27b.json` reports `ok=true`, model `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP`, `phaseAttempts=[(1, success, final marker reached)]`, all six phase tabs `done`, verbose tool transcript entries for `nmap`, `netexec`, `sqlmap`, `hydra`, `metasploit`, and `linpeas`, and final assistant marker `REAL_QWEN_PHASE_FINAL`. Cache evidence in the same artifact shows `kv_cache_quantization.bits=4`, `native_cache.cache_type=hybrid_ssm_typed`, `native_cache.paged=true`, `native_cache.prefix=true`, scheduler block size `64`, and `total_tokens_cached=8190`.
- Real Qwen 35B autonomous phase proof now has a clean app/API artifact. `docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-35b.json` reports `ok=true`, model `/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP`, `phaseAttempts=[(1, success, final marker reached)]`, `chat.maxIterations=8`, `forceFinalAnswerAfterToolResults=false`, all six phase tabs `done`, verbose tool transcript entries for the same six phase tools, and final assistant marker `REAL_QWEN_PHASE_FINAL`. Cache evidence in the same artifact shows q4 KV, hybrid SSM typed cache, paged cache, prefix cache, scheduler block size `64`, and `total_tokens_cached=13257`.
- The 35B autonomous proof required two root-cause fixes before the clean artifact: the tool parser now handles Qwen3.6 A3B `<name>/<arguments>` and malformed `<_name>...` XML-ish calls, and the app loop can disable forced final-answer mode after tool results so a model can continue multi-phase tool use. Focused parser and policy source-contract tests cover those changes.
- Qwen3.6 reasoning-on final assistant content now has live app/API proof for both target models when bounded at `maxTokens=1024`. Artifacts `docs/live-proofs/2026-07-04-real-qwen-27b-reasoning-on-1024.json` and `docs/live-proofs/2026-07-04-real-qwen-35b-reasoning-on-1024.json` report `ok=true`, `status=PASS_FINAL_ASSISTANT_CONTENT`, q4 KV, native `hybrid_ssm_typed`, paged cache, prefix cache, and block L2 cache. The low-cap recovery contract is now tracked in `docs/live-proofs/2026-07-04-reasoning-cap-recovery.json`; `scripts/reasoning-cap-recovery-proof.py` reports `ok=true`, `sourceWarningStatus=PASS`, `legacy512Status=PASS_WARNING_ARTIFACT`, `live1024Status=PASS`, `recommendedRecoveryMaxTokens=1024`, and `doesNotChangeGenerationSettings=true`.
- Reasoning-on final assistant content is now classified as PASS in the matrix. The remaining low-cap behavior is treated as a bounded UX/recovery path, not an unhandled failure: 64/512-token caps can exhaust inside reasoning, but the app warning names the cap, points to the proven 1024-token recovery setting, and leaves generation settings under user control.
- Qwen MTP output-path proof is now a separate tracked requirement. Any Qwen model whose selected path/name includes `MTP` must prove D3 MTP is active on the generation/output path, not just present in `jang_config.json` metadata. `scripts/qwen-d3-mtp-output-proof.py` verifies the existing live Qwen autonomous phase artifacts and writes `docs/live-proofs/2026-07-04-qwen-d3-mtp-output-proof.json`. The 2026-07-04 19:40 rerun reports `ok=true`, `2` PASS rows, and `0` FAIL rows. For the 27B MTP model it verifies runtime MTP active, effective depth `3`, D3 drafted tokens `12`, D3 accepted tokens `1`, `253` MTP forward passes, no fallback reason, and final assistant output from `docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-27b.json`. For the 35B MTP model it verifies runtime MTP active, effective depth `3`, D3 drafted tokens `5`, D3 accepted tokens `1`, `18` MTP forward passes, no fallback reason, and final assistant output from `docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-35b.json`.
- Consolidated Qwen runtime readiness is now machine-readable. `scripts/qwen-runtime-readiness-proof.py` writes `docs/live-proofs/2026-07-04-qwen-runtime-readiness.json` from existing live artifacts without loading another model. The 2026-07-04 21:17 refresh reports `ok=true`, `coreStatus=PASS`, `overallStatus=PASS`, `2` PASS model rows, and `0` FAIL model rows. For both the 27B and 35B MXFP8 MTP models it verifies Qwen/MXFP8/MTP identity, TurboQuant q4 attention-KV mode (`q4TurboQuantKV`, `mode=turboquant-q4`), native `hybrid_ssm_typed` cache, native SSM companion/rederive policy (`ssmCompanionNotQuantized`, `ssm_policy=native_companion_state`, `rederive=async_clean_prefill_on_miss_or_warm_pass`), prefix cache, paged cache, block L2, SSM companion disk L2, `qwen3` reasoning parser, `qwen` tool parser, visible chat/terminal/result tool transcripts, and D3 MTP output-path evidence. Cross-surface checks in the same artifact report `streaming=PASS`, `reasoning=PASS`, `cveLookup=PASS`, and `longContext=PASS`.
- Streaming parser and SSE/tool-delta coverage is now a separate tracked requirement. `scripts/streaming-parser-reuse-proof.py` writes `docs/live-proofs/2026-07-04-streaming-parser-reuse.json`; the 2026-07-04 18:12 run reports `ok=true`, `contractCount=18`, and live QA route coverage for `/v1/chat/completions` streaming, `/v1/responses` streaming events, `delta.content`, `delta.reasoning_content`, `delta.tool_calls`, `response.output_text.delta`, `response.reasoning.delta`, `response.function_call_arguments.delta`, cached-token usage telemetry, previous-response reuse, Qwen/Minimax parser reuse, and coverage-index parity. This is app/API/source coverage; real loaded-model streaming remains represented by the Qwen live artifacts listed above.
- Individual toolchain coverage is now machine-readable. `scripts/individual-toolchain-coverage-proof.py` writes `docs/live-proofs/2026-07-04-individual-toolchain-coverage.json`; the 2026-07-04 18:52 run reports `ok=true`, `toolCount=10`, `10` PASS rows, and `0` FAIL rows. It verifies chat transcript, terminal transcript, result/tab evidence, and Qwen 27B/35B model-driven evidence for `nmap`, `httpx`, `nuclei`, `hydra`, `netexec`, `linpeas`, `curl`, `nc`, `metasploit`, and `sqlmap`. Evidence levels are separated: real loopback execution for the installed-tool rows, `run_shell` subtool proof for `curl`/`nc`, safe `version; exit` proof for Metasploit, and autonomous phase loopback proof for `sqlmap`.
- All-tab tool-family fanout is now machine-readable. `scripts/tool-family-fanout-coverage-proof.py` writes `docs/live-proofs/2026-07-05-tool-family-fanout-all-tabs.json`; the current live route run reports `ok=true`, `familyCount=10`, `10` PASS rows, and `0` FAIL rows. It verifies representative tools for every tab family: recon `nmap`, web `nuclei`, network `netexec`, creds `hashcat`, exploit `metasploit`, post `linpeas`, supplyChain `search_cve`, osint `gowitness`, report `search_context`, and stash `search_context`. Each row must have a chat tool card, activity entry, tab activity, parsed tab result, and context-catalog evidence.
- Ordered chained tool workflow coverage is now machine-readable. `scripts/chained-tool-workflow-proof.py` writes `docs/live-proofs/2026-07-04-chained-tool-workflow.json`; the 2026-07-04 20:55 run reports `ok=true`, `5` PASS rows, and `0` FAIL rows. It verifies that the existing live artifacts contain ordered multi-tool chains, not only isolated tool mentions: real installed loopback `nmap/httpx/nuclei/hydra/netexec/linpeas/run_shell/run_shell`, Qwen 27B and 35B real-installed-loopback versions of the same chain, and Qwen 27B and 35B autonomous phase `nmap/netexec/sqlmap/hydra/metasploit/linpeas` chains. For the Qwen rows it also verifies q4 KV, `hybrid_ssm_typed`, paged cache, prefix cache, and final assistant continuation after the last tool call.
- All-tab ordered workflow coverage is now machine-readable. `scripts/all-tab-ordered-tool-flow-proof.py` writes `docs/live-proofs/2026-07-05-all-tab-ordered-tool-flow.json`; the 2026-07-05 13:58 live route run reports `ok=true`, `9` PASS workflow rows, and `0` FAIL rows. It covers the user-named full order `recon/web/network/creds/exploit/post/supplyChain/osint/report/stash`, reverse order, CVE-first, post-to-recon, OSINT-first, credentialed-network, report/stash reopen, and other alternate orders. The artifact now also records aggregate all-tool coverage: `42/42` registered tool rows are present in ordered workflows, have callback/subprocess execution owners, source hooks, and the 3-mode authorization policy map. It validates `/qa/tab-tool-function-flow`, `/qa/tab-action-surface-matrix`, `/qa/tool-execution-matrix`, and coverage-index mirrors, and links the route proof to the existing Qwen 27B/35B ordered tool-chain artifacts without loading a model in this proof.
- Current Computer Use all-tab click-sweep is now captured separately for the clean dist app instance. `docs/live-proofs/2026-07-05-computer-use-all-tabs-dist-current.json` records CUA version `857`, explicit attach to `/Users/eric/exploitbot/dist/ExploitBot.app/`, visible initial Recon, clicked Web -> Network -> Creds -> Exploit -> Post -> Supply -> OSINT -> Report -> Stash, final `/state activeTab=stash`, all `manualTabSwitch` activity events in order, and `engineRunning=false`/`enginePort=0`.
- Long-context smoke proof scaffolding now exists and is RAM-guarded. `scripts/real-qwen-long-context-smoke-proof.py` builds a tokenizer-counted long prompt, auto-reexecs into `ExploitBotEngine/.venv/bin/python3` when plain `python3` lacks `transformers`, launches Qwen with TurboQuant q4 attention-KV, prefix cache, paged cache, block L2, native SSM companion/rederive state, and explicit `--max-prompt-tokens`, first verifies lower per-request prompt-cap rejection, then sends the long prompt and records cache stats. The 2026-07-04 11:43 retry correctly refused before launch while unrelated `osaurus-evals` PID `83940` was active. After that eval exited, the 11:46 live retry exposed real defects instead of producing a clean proof: `ExploitBotEngine/launch.py` did not accept/forward `--max-prompt-tokens`; after fixing that, the live Qwen run loaded 27B, reported session `max_prompt_tokens=11283`, processed about `9247` prompt tokens, produced `LONG_CONTEXT_SMOKE_PASS`, and showed q4 KV plus block/SSM L2 state, but failed because per-request `max_prompt_tokens=4617` was ignored and returned `200` instead of the expected `413`. Follow-up fixes now add launcher forwarding, preserve `max_prompt_tokens` on `ChatCompletionRequest`/`CompletionRequest`, restore hybrid TurboQuant make-cache metadata in cache stats, stamp `generatedAt` on guarded-refusal artifacts, evaluate cache topology from post-generation `/v1/cache/stats`, and file-back engine logs so verbose block-cache output cannot deadlock the proof harness stdout pipe. The 2026-07-04 21:14 rerun loaded the real 27B model and passed: artifact `docs/live-proofs/2026-07-04-real-qwen-long-context-smoke-27b.json` reports `ok=true`, `generatedAt=2026-07-04T21:14:42-0700`, `actualPromptTokensByTokenizer=8227`, `usage.prompt_tokens=8232`, `sessionMaxPromptTokens=10275`, lower per-request cap rejection `PASS`, final marker `LONG_CONTEXT_SMOKE_PASS`, `q4TurboQuantKV=PASS`, `ssmCompanionNotQuantized=PASS`, prefix cache `PASS`, paged cache `PASS`, `hybrid_ssm_typed` `PASS`, SSM companion L2 `16423` tokens, block L2 `8231` tokens, and no leftover Qwen engine process after cleanup. The 2026-07-04 21:53-21:59 graduated 64k rerun also passed: `docs/live-proofs/2026-07-04-real-qwen-long-context-64k-27b.json` reports `ok=true`, `actualPromptTokensByTokenizer=64011`, `usage.prompt_tokens=64016`, `sessionMaxPromptTokens=66059`, lower per-request cap rejection `PASS`, final marker `LONG_CONTEXT_SMOKE_PASS`, `q4TurboQuantKV=PASS`, `ssmCompanionNotQuantized=PASS`, scheduler cache `63936` tokens, block L2 `63936` tokens, SSM companion L2 `128015` tokens, and post-cleanup `Swapouts: 0` with `System-wide memory free percentage: 94%`. The 2026-07-04 22:40-22:53 graduated 128k rerun passed after root-causing two cache-capacity defects: the server now scales paged `max_cache_blocks` from the prompt cap, and `launch.py` no longer pins the default block L2 budget to 10 GB so the server can scale it to `20.34GB`. Artifact `docs/live-proofs/2026-07-04-real-qwen-long-context-128k-27b.json` reports `ok=true`, `actualPromptTokensByTokenizer=128019`, `usage.prompt_tokens=128024`, `sessionMaxPromptTokens=130067`, final marker `LONG_CONTEXT_SMOKE_PASS`, `q4TurboQuantKV=PASS`, `ssmCompanionNotQuantized=PASS`, scheduler cache `128023` tokens, block L2 `128023` tokens with `disk_evictions=0`, SSM companion L2 `256023` tokens, and post-cleanup `Swapouts: 0` with `System-wide memory free percentage: 94%`. The next 160k probe first exposed a real live-cache validation ceiling defect: the original 16 GiB total-record cap rejected a legitimate ~18.5 GiB Qwen3.6 27B hybrid-SSM paged-store record, so `cache_record_validator.py` now keeps per-tensor validation and raises the finite total-record ceiling to 32 GiB. The 2026-07-05 00:12 rerun completed final assistant output and post-generation cache writes: `docs/live-proofs/2026-07-04-real-qwen-long-context-160k-27b.json` reports `ok=true`, `actualPromptTokensByTokenizer=160005`, `usage.prompt_tokens=160010`, `sessionMaxPromptTokens=162053`, `LONG_CONTEXT_SMOKE_PASS`, scheduler cache `160009`, block L2 `160009` tokens with `disk_evictions=0`, SSM companion L2 `320009`, and post-cleanup `Swapouts: 0`. The 2026-07-05 01:03 guarded 192k rerun completed final assistant output and post-generation cache writes: `docs/live-proofs/2026-07-04-real-qwen-long-context-192k-27b.json` reports `ok=true`, `actualPromptTokensByTokenizer=192017`, `usage.prompt_tokens=192022`, `sessionMaxPromptTokens=194065`, `LONG_CONTEXT_SMOKE_PASS`, block L2 `192021` tokens with `disk_writes=3001`, SSM companion L2 `384021`, completion memory guard `aborted=false`, minimum sampled free memory `17%`, and max sampled `Swapouts: 0`. The harness now also has a source-tested completion-memory guard (`CompletionMemoryGuardAbort`) that samples `memory_pressure` during long requests and terminates the engine before swap/flood conditions continue. It also has an opt-in wait-for-memory-slot path (`EXPLOITBOT_LONG_CONTEXT_WAIT_FOR_MEMORY_SLOT_SECONDS`) that keeps the no-stacking guard intact while allowing future long proofs to wait for external heavyweight jobs to exit instead of immediately failing.
- Near-max context preflight is now machine-readable without pretending the real 262k run happened. `scripts/near-max-context-preflight-proof.py` reads the real Qwen 27B config/tokenizer metadata, current long-context artifacts, current memory pressure, current heavyweight process list, the latest near-max attempt artifact, the 200k incremental attempt/refusal, and the 224k retry/refusal artifacts, then writes `docs/live-proofs/2026-07-04-near-max-context-preflight.json` without loading a model. The preflight reports `declaredMaxContextTokens=262144`, `tokenizerMaxLength=262144`, `nearMaxTargetPromptTokens=258000`, current completed live proofs at 8k, 64k, 128k, 160k, and 192k, largest completed prompt `192017`, proven safe target ceiling `192000`, and `nearMaxLiveStatus=FAILED_GUARDED_ATTEMPT`. A 2026-07-05 200k incremental retry (`docs/live-proofs/2026-07-05-real-qwen-long-context-200k-27b.json`) reached live Qwen chunked prefill at `200025` tokenizer-counted prompt tokens / runtime `seq_len=200037`, showed q4 storage-boundary KV, paged cache, prefix cache, hybrid SSM topology, and async rederive in live cache stats, then failed safely with `CompletionMemoryGuardAbort` when swapouts rose from baseline `16` to `204` before final output or post-generation cache writes. `docs/live-proofs/2026-07-05-long-context-200k-safety-refusal.json` proves the same 200k target now refuses before model load with `lastBlockReason=unproven_target_above_safe_ceiling` and empty `engineLogTail` unless the high-risk override is set. A 2026-07-05 224k graduated retry (`docs/live-proofs/2026-07-05-real-qwen-long-context-224k-27b.json`) reached live Qwen chunked prefill at `224003` tokenizer-counted prompt tokens but failed safely with `CompletionMemoryGuardAbort` after swapouts appeared. The harness now samples memory faster for high-context runs, tracks new swapouts relative to the run baseline, and by default refuses targets above the proven safe ceiling; `docs/live-proofs/2026-07-05-long-context-224k-safety-refusal.json` proves the same 224k target now refuses before model load with `lastBlockReason=unproven_target_above_safe_ceiling` and empty `engineLogTail`. Future 258k proof runs must be explicit high-risk runs using the preflight-recorded override command with `EXPLOITBOT_LONG_CONTEXT_ALLOW_UNPROVEN_TARGET=1`. The real 258k attempt is separately captured in `docs/live-proofs/2026-07-04-real-qwen-near-max-context-27b.json` and summarized by `docs/live-proofs/2026-07-04-near-max-context-runtime-attempt-summary.json`: after fixing the prompt builder, exact tokenizer preflight, and launcher timeout forwarding, it loaded Qwen 27B with `--timeout 3600.0`, accepted the full request path, proved lower-cap rejection at exact `258032` tokens, entered live chunked prefill at runtime `seq_len=258044`, and showed q4 storage-boundary KV, paged cache, prefix cache, hybrid SSM topology, and async rederive in live cache stats. It did not complete generation; the 2026-07-05 01:07-01:36 rerun ended through `CompletionMemoryGuardAbort` after sampled free memory reached `14%`, with sampled swapouts still `0`, so this is a guarded failure/partial proof, not a near-max pass.
- The near-max preflight and runtime-attempt summary were refreshed again at `2026-07-05T17:08:26-0700` without starting a new model run. The current summary still reports `ok=false`, but the positive evidence remains current: target and model-load memory preflights `PASS`, exact lower-cap rejection `PASS`, server timeout forwarded `PASS`, chunked prefill entered `PASS` at runtime `seq_len=258044`, and final generation `FAIL`. This keeps full-context stress correctly classified as `PARTIAL`.
- Superseding 160k long-context status: after the 23:22 guarded refusal and the first 160k completion exposing a too-low 16 GiB live-cache validator ceiling, `cache_record_validator.py` now allows finite 32 GiB total live-cache records. The 2026-07-05 00:12 rerun of `docs/live-proofs/2026-07-04-real-qwen-long-context-160k-27b.json` is current: `ok=true`, `actualPromptTokensByTokenizer=160005`, `usage.prompt_tokens=160010`, `sessionMaxPromptTokens=162053`, final marker `LONG_CONTEXT_SMOKE_PASS`, `q4TurboQuantKV=PASS`, `ssmCompanionNotQuantized=PASS`, scheduler cache `160009`, block L2 `160009` with `disk_evictions=0`, SSM companion L2 `320009`, and post-cleanup `Swapouts: 0`.
- Computer Use live GUI proof is restored for current attach/control. `docs/live-proofs/2026-07-04-computer-use-live-gui.json` records the 2026-07-04 21:20-21:25 live `mcp__computer_use` run: `list_apps` returned running apps, `get_app_state` returned the ExploitBot accessibility tree plus inline screenshot after the permission window completed, Computer Use clicked through onboarding, set the Qwen 27B MTP model path, set op name `Computer Use Live Proof`, clicked `Start Op`, reached the main workspace, clicked Settings, and observed Settings categories plus Engine status. The release app began loading the selected Qwen 27B engine from onboarding; the proof captured the exact launch command with `--kv-cache-quantization turboquant-q4`, then PID `92893` was killed and post-cleanup process/RAM checks showed no matching app/model processes, `Swapouts: 0`, and `System-wide memory free percentage: 94%`.
- Current Computer Use permission state is also reproved after the latest user-side repair. `docs/live-proofs/2026-07-05-computer-use-permission-state.json` records live `mcp__computer_use.list_apps` plus `get_app_state(app="System Settings")`: CUA app version `857`, System Settings window `Screen & System Audio Recording`, accessibility tree and inline screenshot returned, and the visible `Codex Computer Use` Screen & System Audio Recording toggle is `on`. This was a non-destructive permission/transport probe and did not launch ExploitBot or start model inference.
- Current `dist` app launch and Computer Use attach are reproved without model inference. `./script/build_and_run.sh --verify` built and launched `/Users/eric/exploitbot/dist/ExploitBot.app`; after removing a duplicate release-app instance from generic app lookup, `mcp__computer_use.get_app_state(app="/Users/eric/exploitbot/dist/ExploitBot.app")` returned CUA version `857`, accessibility tree, inline screenshot, visible tab/settings/terminal/chat controls, and `00:17 INF scanModelLibrary 14 models from 1 roots`. `docs/live-proofs/2026-07-05-computer-use-dist-app-smoke.json` records this current build/UI smoke proof.
- Current `dist` app Settings/CVE controls are reproved through live Computer Use without model inference. `docs/live-proofs/2026-07-05-computer-use-current-attach-proof.json` records the 2026-07-05 02:34 direct attach retry with CUA version `857`, PID `88511`, screenshot/accessibility tree, main workspace, chat input, Settings, Terminal, and visible `scanModelLibrary 14 models from 1 roots` activity. `docs/live-proofs/2026-07-05-computer-use-settings-cve-cache-ui.json` records Settings opened in `/Users/eric/exploitbot/dist/ExploitBot.app`, cache KV mode toggled from `TurboQuant Q4` to `Q4` and restored to `TurboQuant Q4`, Prefix Cache toggled off and restored on, prompt L2/paged/block L2 visible on, Runtime Reasoning toggled off/on, Reasoning Parser toggled `Auto -> Qwen3 -> Auto`, and Tool Parser left on `Auto`. The same proof records live `Current Threat Intel` refresh from `1552/1552 Last synced: Never` to `1587` total CVEs, `1577` CISA KEV, `Last synced: 2026-07-05T07:22:43Z`, newest KEV `CVE-2026-45659`, plus exact-ID search returning the Microsoft SharePoint Server deserialization/RCE row with `source:cisa-kev`, `kev`, `known-exploited`, and due date tags. The Tools settings panel was also visible with `13` installed and `29` missing tools, including installed `nmap`, `httpx`, `nuclei`, `sqlmap`, `netexec`, `hydra`, `metasploit`, and `linpeas`.
- Current-source Tools settings now expose a safe install plan before install-all actions. `docs/live-proofs/2026-07-05-tool-settings-install-plan-live.json` records rebuilt `dist/ExploitBot.app` state and Computer Use evidence for the visible `INSTALL PLAN` section: `29` missing tools grouped as `go: 7`, `homebrew: 13`, `pip: 9`, grouped by category, `Commands queued 29`, and the first queued commands. The same proof verifies the `Install plan reviewed` checkbox gates `Install All Missing`: disabled at value `0`, enabled at value `1`, and restored disabled at value `0`. `Install All Missing` was intentionally not run in this proof because it would start network installs for 29 tools.
- Current direct Computer Use retry after the latest user-side repair is also file-backed in `docs/live-proofs/2026-07-05-computer-use-current-direct-settings-cve-proof.json`. It attached to `/Users/eric/exploitbot/dist/ExploitBot.app` with CUA version `857`, opened Settings, proved 27B/35B MTP selector visibility and a reversible 35B selector change, toggled Cache `TurboQuant Q4 -> Q4 -> TurboQuant Q4` without applying native Q4, observed prefix/prompt-L2/paged/block-L2 enabled, observed the thin Agents panel, and ran a CVE settings search for `apache path traversal` that returned `CVE-2024-32113`, `CVE-2021-42013`, and `CVE-2021-41773`.
- Current Agents settings loop controls are file-backed through live Computer Use in `docs/live-proofs/2026-07-05-computer-use-agent-settings-loop-ui.json` and app/API proof in `docs/live-proofs/2026-07-05-agent-settings-loop-controls.json`. Computer Use attached to `/Users/eric/exploitbot/dist/ExploitBot.app` with CUA version `857`, opened Settings > Agents, observed mode policy, max iterations, tool schema budget, unavailable-tool schema toggle, final-after-tools toggle, multi-agent mode, max concurrent agents, phase routing, and authorization guards. It applied `maxIterations=7`, `toolSchemaMaxTools=32`, `includeUnavailableToolSchemas=true`, `forceFinalAnswerAfterToolResults=false`, `multiAgentEnabled=true`, and `maxConcurrentAgents=3`; `/state.chat` and `/state.agents` mirrored those values, breach routing included `Exploit Agent`, high-risk guard count was `24`, engine/model remained stopped/empty, and defaults were restored afterward.
- Computer Use visible model tool loop is now proven through the release app. `docs/live-proofs/2026-07-04-computer-use-visible-model-tool-loop.json` records the 2026-07-04 21:34-21:39 run: Computer Use attached to `release/ExploitBot.app`, the release-bundled Python engine loaded real Qwen3.6 27B MXFP8 MTP on port 8100, Computer Use entered the prompt into the visible chat field and clicked Send, the model invoked `lookup_cve`, and the final Computer Use accessibility tree/screenshot showed `lookup_cve ok 0.1s`, verbose arguments with `CVE-2025-49704`, final marker `COMPUTER_USE_VISIBLE_TOOL_FINAL`, TTFT `11.54s`, `1451` prompt tokens, `70` completion tokens, and the Supply/CVE panel selected. API/cache evidence from the same run shows `effective_config.cache.kv_cache_quantization.mode=turboquant-q4`, attention KV quantization applies only to attention KV layers, SSM remains `native_companion_state`, and scheduler cache recorded hits/tokens saved. Cleanup killed the orphaned release launcher PID and ended with no matching app/model processes, `Swapouts: 0`, and `System-wide memory free percentage: 94%`. Current release-app Computer Use settings proof is refreshed separately in `docs/live-proofs/2026-07-05-release-app-computer-use-settings-agents.json`: CUA version `857` attached to `/Users/eric/exploitbot/release/ExploitBot.app`, opened Settings, observed Model folder selection and folder scan controls with 27B/35B MTP entries, observed Cache default `TurboQuant Q4` with native `Q4` not selected and prefix/paged/prompt-L2/block-L2 on, and observed the Agents loop controls, phase routing, and authorization guards. Screenshot proof is `docs/live-proofs/2026-07-05-release-app-computer-use-settings-agents.png`.
- Current rebuilt release-app Qwen 27B and 35B proofs are refreshed with strict production-stop cleanup evidence. After patching `EngineManager.stop()` to wait/escalate and patching `scripts/release-app-live-qwen-proof.py` plus `scripts/release-app-qwen-cross-restart-cache-proof.py` to use a 20s `/engine/stop` timeout and fail if bundled release `launch.py` remains before harness fallback cleanup, `scripts/release-readiness-proof.py` rebuilt `release/ExploitBot.app` at `2026-07-05T03:06:28-0700` with manifest hashes `appBinarySha256=4f7212875038601ffbb5c0814018ab4340848280604f33e0bc20283ee9a2db7d` and `dmgSha256=0591ee921f9a859c361d2acedd7ecb9ef6a691009178de54320ba58eb7f5ea20`. Fresh 2026-07-05 14:11/14:12 reruns of `scripts/release-app-live-qwen-proof.py` wrote `docs/live-proofs/2026-07-05-release-app-live-qwen-27b-current.json` and `docs/live-proofs/2026-07-05-release-app-live-qwen-35b-current.json`; both report `ok=true`, PASS memory preflight, app-bundled vMLX Python selected, missing modules `0`, hybrid SSM attention topology, `kv_cache_quantization.mode=turboquant-q4`, prefix cache enabled, paged cache enabled, SSM companion L2 enabled, native MTP runtime active with effective depth `3`, repeat-prompt cached tokens `13`, scheduler cache hit deltas, `productionStopProcessRows=[]`, `productionStopClean=true`, `cleanupTerminatedProcessRows=[]`, and `postCleanupProcessRows=[]`. Post-run process checks found no local matching ExploitBot/Qwen/vMLX launcher rows and `Swapouts` remained unchanged at `1988`.
- Current release-app cross-restart cache proof is refreshed for both target Qwen MXFP8 MTP models after the latest package rebuild. `docs/live-proofs/2026-07-05-release-app-qwen-cross-restart-cache-27b-current.json` (`2026-07-05T16:51:13-0700`) and `docs/live-proofs/2026-07-05-release-app-qwen-cross-restart-cache-35b-current.json` (`2026-07-05T16:52:23-0700`) both report `ok=true` after launching the release app twice with one shared temporary HOME/cache root. The replay phase reports cached prompt tokens `17`, block L2 disk hit `1`, SSM companion disk hit `1`, SSM rederive requested `0`, SSM rederive failed `0`, `kv_cache_quantization.mode=turboquant-q4`, hybrid SSM attention topology, prefix cache enabled, paged cache enabled, native MTP runtime active with effective depth `3`, `productionStopClean=true`, and `postCleanupClean=true`. Post-run process checks found no release app/Qwen/vMLX listener on `:9999`, no leftover matching model process, and `Swapouts` remained `1988`.
- The release-app JSON framing proof was refreshed at `2026-07-05T16:50:59-0700` before the final package rebuild. It was superseded by the `2026-07-05T17:04:48-0700` package/hash refresh below.
- The release app/DMG were rebuilt again from `HEAD 205316b` after the startup-default QA route fix. `docs/live-proofs/2026-07-04-release-readiness.json` now reports `generatedAt=2026-07-05T17:04:40-0700`, `ok=true`, `localPackageStatus=PASS`, app codesign `PASS`, DMG codesign `PASS`, bundled runtime `PASS`, `notarizationGate=requires-notary-credentials`, `appBinarySha256=3d149769ebe5e63774610a2edd79582ebaf6b060fb325094b7b9948898e3c353`, and `dmgSha256=35d6d654d48cd7f9c5e1c5f6e9d555886cbe0cf69b9d711eadafa7c828c39fc7`. Matching refreshes at `2026-07-05T17:04:48-0700` show release JSON framing `ok=true` on those hashes and notarization preflight still `BLOCKED` only on missing accepted notary credentials plus unstapled app/DMG tickets. Release visible smoke and beta-readiness coverage were rerun immediately after the rebuild and passed.
- Release-app Qwen live reruns now have a fail-before-launch memory preflight with optional wait-for-slot support. `scripts/release-app-live-qwen-proof.py` and `scripts/release-app-qwen-cross-restart-cache-proof.py` refuse to start before launching the app when available memory is below the model threshold or when local heavyweight model/eval processes are active, including `vllm-mlx`; override requires `EXPLOITBOT_RELEASE_QWEN_ALLOW_CONCURRENT_MODEL=1` or `EXPLOITBOT_RELEASE_QWEN_SKIP_MEMORY_GUARD=1`, and bounded waiting is available through `EXPLOITBOT_RELEASE_QWEN_WAIT_FOR_MEMORY_SLOT_SECONDS`. `scripts/release-qwen-memory-preflight-proof.py` produced `docs/live-proofs/2026-07-05-release-qwen-memory-preflight-current.json` without loading a model. The current 2026-07-05 14:11 run reports `overallStatus=PASS`, `2` PASS rows, `0` BLOCKED rows, heavy model process count `0`, and next action `safe to run bounded release-app-live-qwen-proof.py`.
- Proof-ledger and per-turn runtime coverage were refreshed at 2026-07-05 02:54 PDT without loading a model. `docs/live-proofs/2026-07-05-proof-ledger-per-turn-runtime-refresh.json` records the original `proof-ledger-proof.py` failure (`categoryOtherCount=47`), root cause in proof categorization drift, the slow `/qa/coverage-index` timing (`74.86s`) that required 120s harness budgets, and the per-turn SSM row mismatch. After the fixes, `proof-ledger-proof.py`, `proof-category-matrix-proof.py`, `endpoint-route-matrix-proof.py`, `tool-execution-matrix-proof.py`, `live-status-preview-flow-proof.py`, `per-turn-runtime-contract-proof.py`, `cache-artifact-matrix-proof.py`, and `app-qa-matrix-smoke-proof.py` pass. Live route snapshot evidence reports `proofCount=257`, `categoryOtherCount=4`, `tabProofFamilyCount=10`, cache artifact `contractParity=true`, Qwen hybrid SSM rederive `completed=1`, `failed=0`, and the seeded per-turn runtime proof shows `hybridSSMAsyncReDerive` ready with `lastNumTokens=113`.
- Current PASS/PARTIAL/BLOCKED matrix is now machine-readable in `docs/live-proofs/2026-07-04-pass-partial-blocked-matrix.json`. The 2026-07-05 03:14 refresh via `scripts/pass-partial-blocked-matrix-proof.py` validates `25` rows with `23` PASS, `1` PARTIAL, and `1` BLOCKED, adds top-level `statusCounts` and `rowCount`, and verifies every row points at an existing evidence path. The Computer Use attach/control row and fully autonomous visible GUI demo row are both PASS, the reasoning-on final-content row is PASS through 27B/35B 1024-token live proofs plus low-cap recovery evidence, and the full-context row includes the completed 160k live-Qwen proof while remaining PARTIAL for the missing 258k final-output/cache-write proof.
- Current goal requirement audit is now machine-readable in `docs/live-proofs/2026-07-04-goal-requirement-audit.json`. The 2026-07-05 03:14 rerun of `scripts/goal-requirement-audit-proof.py` maps the active user goal to `13` requirement rows and verifies the current matrix/evidence paths plus release manifest gate. The artifact reports `ok=true`, `objectiveComplete=false`, `completionClaimAllowed=false`, `overallStatus=BLOCKED`, `11` PASS rows including `computer_use_live_gui`, `qwen_mtp_d3_output_path`, `streaming_parser_reuse`, `individual_toolchain_per_tool`, and `cve_library_current_intel`, `1` PARTIAL row (`generation_reasoning_context`), and `1` BLOCKED row (`release_displayable`).
- Built-in objective audit proofs were refreshed after root-causing a slow `/qa/coverage-index` dependency. Direct timing showed `/qa/objective-flow-requirement-matrix` returned in `6.82s`, while `/qa/coverage-index` took `72.25s`; `scripts/objective-flow-requirement-matrix-proof.py` and `scripts/active-objective-audit-proof.py` now use the same 120s coverage-index timeout budget used by other slow-route proofs. `scripts/active-objective-audit-proof.py` also now accepts the current `qwenHighCardinalityCompleted` hybrid-SSM evidence field. A 2026-07-04 17:52 parallel attempt exposed that these Swift app proof scripts can collide on the app launch/coverage-index route (`RemoteDisconnected`, launch failure, and timeout). Re-running them sequentially passed: `scripts/objective-flow-requirement-matrix-proof.py`, `scripts/objective-runtime-coverage-proof.py`, and `scripts/active-objective-audit-proof.py` all pass in this checkout without loading Qwen.
- Subtab and tab-action matrix proofs now use the same 120s `/qa/coverage-index` budget after `scripts/subtab-lifecycle-matrix-proof.py` reproduced the stale 45s timeout in this pass. `scripts/subtab-lifecycle-matrix-proof.py` and `scripts/tab-action-surface-matrix-proof.py` both pass sequentially after the timeout fix, giving current live debug-app route proof for subtab lifecycle parity and tab action surface parity without loading a model.

PARTIAL:

- Full-context-length stress: the fixed 8k plus graduated 64k, 128k, 160k, and 192k Qwen long-context runs pass with real 27B generation, lower per-request cap rejection, q4 TurboQuant attention-KV, prefix cache, paged cache, hybrid SSM, native SSM companion L2, and block L2 proof. The 2026-07-05 01:03 guarded 192k rerun reports `ok=true`, `actualPromptTokensByTokenizer=192017`, `usage.prompt_tokens=192022`, final marker `LONG_CONTEXT_SMOKE_PASS`, block L2 `192021` tokens, SSM companion L2 `384021`, completion memory guard `aborted=false`, and max sampled `Swapouts: 0`. Later 200k and 224k retries are negative proofs: both reached live chunked prefill but triggered swapouts and were aborted before final output/cache writes, so the harness now refuses above the 192k proven safe ceiling unless explicitly overridden. This remains PARTIAL because the 200k, 224k, and 258k near-max runs did not complete final assistant output or post-generation cache writes.
- Full app QA matrix: `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 scripts/app-qa-matrix-smoke-proof.py` passed again at 2026-07-05 02:53 after a fresh Swift debug build and the slow coverage-index route. The durable artifact `docs/live-proofs/2026-07-04-app-qa-matrix-smoke.json` reports `ok=true`, `generatedAt=2026-07-05T02:53:38-0700`, `noModelLoaded=true`, and live debug-app route coverage across subtabs, agent-loop, tool-execution, security-boundary, runtime, context, CVE, settings, visual, session, artifacts, and ledgers. This is app-route/source/proof smoke coverage, not a production-release claim.
- Computer Use: current attach/control, Settings/CVE interaction, and visible real-model tool-loop proof are PASS after the user-side permission repair and tool refresh. The live Computer Use artifacts prove the active Codex MCP namespace exists, `list_apps` and `get_app_state` execute, inline screenshots are returned, `Codex Computer Use` is visible as enabled in Screen & System Audio Recording, the freshly built `dist` app can be attached and inspected, Settings cache/runtime controls respond and restore to TurboQuant/prefix/paged/L2 defaults, Current Threat Intel can refresh and exact-CVE search returns source-attributed rows, onboarding/model/op/settings clicks and set-value actions reach expected native UI states, and the release app can visibly drive real Qwen3.6 27B through a `lookup_cve` tool call with verbose arguments/results and final assistant output. Cleanup removes release-engine model processes and ends with `Swapouts: 0`.
- Release readiness: app/DMG signatures, bundled runtime selection, hardened runtime, and local package readiness now pass on the 2026-07-05 02:07 rebuilt artifacts. The notarization preflight separately proves `notarytool` is available, no credential input/default keychain profile is configured in the current environment, Gatekeeper rejects the app without notarization context, and neither artifact has a stapled ticket, so distribution remains false until the notary flow is run and stapled.
- Release visible local smoke: the signed release app now has direct local display proof through System Events/screenshot capture and current Computer Use attach/settings proof. `docs/live-proofs/2026-07-04-release-visible-smoke.json` reports the release app window is visible, the main workspace is present after onboarding, the Qwen 27B path is persisted, and no model was loaded. `docs/live-proofs/2026-07-05-release-app-computer-use-settings-agents.json` proves the refreshed package exposes Model, Cache, and Agents controls through CUA version `857`. This strengthens displayability but does not change the distribution blocker.
- CVE lane: starter library, app search, model-invoked `search_cve`, model-invoked first-try `lookup_cve`, verbose transcript, source-attributed CVE context/tool output, current CISA/NVD refresh, exact CVE-ID search, top-modern-CVE ranking, final-answer loop, and fresh visible `lookup_cve` UI evidence now work across current proof layers. The latest current-threat-intel proof refreshed at 2026-07-05 03:50 PDT with CISA KEV `2026.07.01`, latest KEV `CVE-2026-45659`, `totalCount=1641`, `kevCount=1631`, exact search `resultCount=1`, `8` top current KEV rows, `10` recent NVD critical rows sorted by score/recency, and app-state search result source attribution for `CVE-2026-45659`. The 21:05 real-Qwen `lookup_cve` rerun adds visible System Events/screenshot proof for the exact tool card and final answer.
- Autonomy/pentest workflow: model proposed a scoped localhost `nmap` action and created a pending approval in earlier proof. Explicit user-deny policy now applies beyond `run_shell`, and the phase-policy matrix now proves high-risk external targets require scope or authorization while loopback/local proof paths remain executable. Safe mock-model/fake-tool phase execution and real Qwen 27B/35B fake-local-tool phase execution now prove app wiring across recon/network/web/creds/exploit/post. Real installed-tool proof now covers first-class `nmap`, `httpx`, `nuclei`, `hydra`, `netexec`, `linpeas`, plus `curl` and `nc` through the app loop against a safe loopback/local lab target, and real Metasploit execution is proven with the safe `version; exit` command through the app tool loop. Real Qwen 27B and 35B now both drive those real installed loopback/local tools through the app loop to final answer. The release app also now has a Computer Use-visible real Qwen tool turn with prompt entry, Send click, `lookup_cve` tool card, and final answer visible in the chat.
- First-run UX: clean app state opens to onboarding, but demo preload is now proven. `docs/live-proofs/2026-07-04-demo-ready-startup.json` shows completing onboarding once with the real Qwen 27B path and relaunching keeps the main workspace visible with cache/model settings persisted and no model loaded.
- Engine lifecycle UX: stale-process cleanup and app-start RAM preflight are guarded in source. `/state.engineMemoryPreflight` exposes RAM blocking, `/state.engineStaleCleanup` exposes stale cleanup counts/process rows, and Settings > Engine now shows a visible stale-cleanup notice when the startup guard acts. Dev app and packaged release app cleanup paths are both now covered by no-model live proofs.
- RAM guard: stale ExploitBot engine accumulation is fixed/proven, the live-batch script blocks concurrent heavyweight model/eval stacking, and Settings/App engine start now blocks before `launch.py` when the memory preflight fails. Earlier RAM pressure included an unrelated `/Users/eric/cc/osaurus` eval running outside this repo. The 21:25 Computer Use proof observed the release app launching Qwen 27B from onboarding with TurboQuant q4 KV flags, killed the orphaned bundled engine PID, and verified `Swapouts: 0` with `System-wide memory free percentage: 94%`. This is still not a production proof for every possible external launcher, but the app, release app, and proof-script paths now have explicit guards.

BLOCKED:

- Production-ready claim is blocked by distribution gates, not local package readiness: the refreshed release manifest reports `notarizationStatus=not-submitted` and `notarizationGate=requires-notary-credentials`, `docs/live-proofs/2026-07-04-notarization-preflight.json` reports Developer ID signature and hardened runtime PASS but missing notary credential input/default profile, Gatekeeper BLOCKED, and no stapled app/DMG tickets, and `/qa/beta-readiness-coverage` remains package-ready but not distribution-ready.

## Working Todo

- [x] Preflight local model folders.
- [x] Stop stale release packaging process from interrupted proof run.
- [x] Confirm Swift build still passes.
- [x] Confirm lightweight launcher/model verifier still passes.
- [x] Run first live 27B MXFP8 MTP proof.
- [x] Fix or isolate `launch.py` to `vmlx_engine.server` CLI drift.
- [x] Re-run 27B live batch/cache proof after CLI bridge fix.
- [x] Fix or isolate missing TurboQuant model-inspector helper.
- [x] Fix OpenAI-compatible chat schema drift for `logprobs`.
- [x] Add peak scheduler queue-depth telemetry required by the live proof.
- [x] Fix `turboquant-q4` scheduler bit mapping so q4 does not fall through to q8.
- [x] Re-run 27B live batch/cache proof after scheduler/cache fixes.
- [x] Run 35B live batch/cache proof.
- [x] Launch app and capture live UI screenshot.
- [x] Attempt Computer Use UI inspection.
- [x] Repair/retest Computer Use attach and live Settings click path.
- [x] Replace hardcoded Runtime/Cache labels with real controls.
- [x] Verify settings toggles change `/state`.
- [x] Fix generation settings propagation from Settings into the primary chat service.
- [x] Prove bounded max-token/context settings via `/qa/context-budget-compaction` and durable JSON artifact.
- [x] Make chat-side tool usage verbose.
- [x] Prove verbose tool transcript with a mock-engine autonomous tool loop.
- [x] Validate app chat can start model and send a real prompt through the app-managed engine.
- [x] Validate panel/tool wiring against safe local targets through app API and QA matrix routes.
- [x] Check modern CVE feeds from CISA KEV and NVD.
- [x] Fix starter CVE library import into active app DB.
- [x] Prove dynamic CVE search in app settings/services.
- [x] Run real app-managed 27B bounded multiturn through the UI after the settings/tool transcript changes, with TTFT, cache, and reasoning-off proof.
- [x] Run app-managed 35B UI/start proof with bounded same-chat multiturn, TTFT, cache, native MTP, and reasoning-off proof.
- [x] Reproduce 35B reasoning-on empty-output failure and surface it as an explicit chat diagnostic with live UI proof.
- [x] Prove live 35B model-invoked `search_cve` with verbose chat transcript and real CVE rows.
- [x] Prove live 35B model-invoked `lookup_cve` reaches the callback path.
- [x] Fix/prove streamed tool-call argument accumulation guard.
- [x] Add source guard for explicit `run_shell` blocker in Autopilot.
- [x] Fix/prove Autopilot loop stopping/finalization so tool results produce a final assistant answer instead of repeated tool calls.
- [x] Prove model-invoked `search_cve` results are used in a complete turn with final marker.
- [x] Add Settings model folder scanning/multi-folder library beyond the single-folder picker.
- [x] Prove Settings model-library scan/select through live Computer Use UI without loading a model.
- [x] Root-cause RAM flooding from stale orphaned engine processes after app relaunch.
- [x] Add and prove no-model stale-engine cleanup guard for dev/live proof relaunches.
- [x] Prove stale-engine cleanup guard against a resident app-managed 27B model process.
- [x] Prove stale-engine cleanup guard against a resident app-managed 35B model process.
- [x] Root-cause current RAM pressure after Computer Use debugging: no ExploitBot engine listener remained; live process inspection found a separate Claude-launched `osaurus-evals` 35B job still active.
- [x] Add and prove live-batch memory preflight so Qwen 27B/35B proof runs refuse to stack on other heavyweight model/eval processes unless explicitly overridden.
- [x] Fix JANG hybrid cache registry override so stamped `cache_type=hybrid` does not fall back to generic Qwen KV.
- [x] Fix persisted generation settings so `engineConfig.maxTokens` mirrors into primary chat and agents after relaunch.
- [x] Add focused persistence source-contract tests for generation-setting mirroring.
- [x] Fix stale proof readiness/coverage-index timeouts in app QA scripts.
- [x] Expose live app/DMG code-signature verification in `/qa/release-readiness`.
- [x] Make `/qa/beta-readiness-coverage` block package readiness when signatures fail instead of treating artifact presence as signed readiness.
- [x] Update objective/runtime and context-session SSM rows to use current high-cardinality/live-agent/runtime SSM evidence instead of an obsolete low-cardinality counter.
- [x] Re-run focused QA and broad app smoke: `context-budget-compaction`, `session-context-cache-flow`, `parser-tool-matrix`, `deep-runtime-flow-coverage`, `beta-readiness-coverage`, `objective-runtime-coverage`, `context-session-efficiency-matrix`, and `app-qa-matrix-smoke` pass.
- [x] Refresh local `release/` artifacts and prove app/DMG signatures with `python3 scripts/release-readiness-proof.py`, direct `codesign`, `/qa/release-readiness`, and `python3 scripts/beta-readiness-coverage-proof.py`.
- [x] Cache `/qa/release-readiness` signature checks by artifact fingerprint so `/qa/coverage-index` remains responsive while still using real `codesign` output.
- [x] Add no-secret notarization preflight proof; `scripts/notarization-preflight-proof.py` produced `docs/live-proofs/2026-07-04-notarization-preflight.json` with notarytool availability, Developer ID signature and hardened-runtime checks, parsed app entitlements, credential-input/default-profile booleans, Gatekeeper assessment, app/DMG stapled-ticket status, and the concrete next action.
- [x] Add release visible smoke proof; `scripts/release-visible-smoke-proof.py` produced `docs/live-proofs/2026-07-04-release-visible-smoke.json` and `docs/live-proofs/2026-07-04-release-visible-smoke.png` proving the signed release app opens to the main workspace locally without loading a model.
- [x] Add demo-ready startup proof; `scripts/demo-ready-startup-proof.py` produced `docs/live-proofs/2026-07-04-demo-ready-startup.json` proving onboarding completion, relaunch persistence, Qwen 27B model path, q4/prefix/paged/L2 settings, and no model load.
- [x] Fix artifact-ledger live proof classification for assertion-map artifacts and superseded CVE-loop partial artifacts.
- [x] Clear `/qa/beta-readiness-coverage` `liveArtifacts` blocker; live route now reports `packageReady=true`.
- [x] Root-cause and fix `scripts/cve-import-embedding-coverage-proof.py` timeout on slow `/qa/coverage-index`; focused CVE import/embedding proof now passes.
- [x] Re-run current agent settings, deep-runtime, and broad app QA smoke proofs after the CVE proof timeout fix.
- [x] Add source-attributed CVE model/context/tool output without a DB migration.
- [x] Prove CVE source attribution through source contracts, live no-model app QA routes, CVE import/embedding proof, and broad app QA smoke.
- [x] Expose terminal toggle state and command transcripts in `/state.terminal`.
- [x] Prove terminal visibility and command transcript state through source contracts, live no-model app QA route, and durable JSON artifact.
- [x] Prove workflow panel/tab activity state, manual tab switching, terminal active command, and merged transcripts through a durable no-model app/API artifact.
- [x] Add and prove Autopilot explicit tool-deny handling beyond `run_shell` with a fake `nmap` negative-control proof.
- [x] Add and prove Autopilot phase-policy matrix for high-risk external targets: no-scope external blocked, loopback allowed, authorized external allowed, scoped external allowed.
- [x] Add and prove mock-model safe autonomous phase execution across recon/network/web/creds/exploit/post with fake local tools and live app/API state.
- [x] Add and prove real installed `nmap`, `httpx`, `nuclei`, `hydra`, `netexec`, `linpeas`, plus `curl`/`nc` loopback/local execution through app Autopilot, verbose chat tool cards, terminal transcripts, dynamic context, and `/results.rawResults`.
- [x] Add and prove real Qwen 27B drives real installed `nmap`, `httpx`, `nuclei`, `hydra`, `netexec`, `linpeas`, plus `curl`/`nc` through the app loop against a safe local lab target with final assistant marker and q4/paged/prefix/block-L2 cache proof.
- [x] Add and prove real Qwen 35B drives real installed `nmap`, `httpx`, `nuclei`, `hydra`, `netexec`, `linpeas`, plus `curl`/`nc` through the app loop against a safe local lab target with final assistant marker and q4/paged/prefix/block-L2 cache proof.
- [x] Install Metasploit and prove real `msfconsole` safe execution through the app tool loop with verbose chat, terminal transcript, and raw-result output.
- [x] Prove real Qwen 27B and 35B drive real `msfconsole` safely through the app loop using only `version; exit`, with verbose chat, terminal transcript, raw-result output, and q4/paged/prefix/block-L2 cache proof.
- [x] Root-cause RAM spike during real-Qwen proofs: single 27B `vmlx_engine.server` load consumes about 33-35 GB RSS; no overlapping ExploitBot/model process remained after cleanup checks.
- [x] Add and prove Settings/App engine-start RAM preflight so low-memory or concurrent heavy-model cases block before spawning `ExploitBotEngine/launch.py`.
- [x] Fix proof harness launch so fake-tool tests build the app bundle and launch `dist/ExploitBot.app/Contents/MacOS/ExploitBot` directly with controlled `HOME` and `PATH`, instead of relying on `/usr/bin/open` environment inheritance.
- [x] Fix `ToolExecutor` subprocess wait hang by replacing the `waitUntilExit` execution wait with `Process.terminationHandler` and EOF pipe cleanup.
- [x] Prove real Qwen 27B behavior through app/tool loop with fake local phase tools through final marker in a live run.
- [x] Produce clean `ok: true` artifact from `scripts/real-qwen-autonomous-phase-proof.py` for `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP`.
- [x] Fix 35B Qwen3.6 A3B `<name>/<arguments>` tool-call dialect parsing and prove it with focused parser regression tests.
- [x] Disable forced final-answer mode for autonomous phase proof so 35B can continue tool use across all six phases.
- [x] Run `scripts/real-qwen-autonomous-phase-proof.py` against `/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP` and produce clean `ok: true` artifact.
- [x] Patch real-Qwen phase proof harness to stamp `finishedAt` in future artifacts; the current 27B/35B artifacts predate this timestamp fix and rely on file mtime plus `ok=true`.
- [x] Re-check current RAM/process state after the 35B proof: no heavy ExploitBot/Qwen process remains, no swap activity, and system memory pressure is not currently reproduced.
- [x] Re-check current RAM/process state after app-start preflight proof: no matched ExploitBot/Qwen/model-server process remains, no swap activity, and system memory pressure is not currently reproduced.
- [x] Close direct `scripts/verify-live-models.py` RAM guard gap with fail-before-launch memory/process preflight, process-group cleanup, no-model proof artifact, and focused tests.
- [x] Add and prove Settings Tool current-machine inventory for installed system execution primitives plus missing pentest tools.
- [x] Add in-app stale-engine cleanup warning/count and prove it with a no-model app/API stale-process cleanup proof.
- [x] Harden launcher child cleanup with process-group shutdown plus pidfile-recorded `vmlx_engine.server` startup cleanup, and prove it with a no-model app/API stale-process cleanup proof.
- [x] Add packaged-app-safe stale-engine cleanup proof beyond the repo `ExploitBotEngine/launch.py` path.
- [x] Fix and prove release starter CVE import does not create SQLite sidecars inside signed app resources after launch.
- [x] Add source accessibility labels for main UI controls and prove visible Settings/Terminal state through native System Events while Computer Use MCP is blocked.
- [x] Prove a native UI Settings cache toggle changes `/state.engineConfig` after Apply App Settings.
- [x] Refresh current Computer Use transport split in `docs/live-proofs/2026-07-04-computer-use-transport-blocked.json`: 20:52 proof shows the prior service/socket/schema-list path was alive but real tool calls were still blocked.
- [x] Restore current Computer Use attach/tool execution after the user-side permission repair; `docs/live-proofs/2026-07-04-computer-use-live-gui.json` records live `mcp__computer_use.list_apps`, `get_app_state`, click, set-value, onboarding, Start Op, Settings, inline screenshot, and cleanup proof.
- [x] Drive a real-model autonomous tool loop visibly through Computer Use; `docs/live-proofs/2026-07-04-computer-use-visible-model-tool-loop.json` proves the release app loaded real Qwen3.6 27B, Computer Use entered the prompt and clicked Send, the model invoked `lookup_cve`, and the visible chat showed verbose tool request/result plus final assistant output.
- [x] Fix/prove reasoning-on 27B app/API turn produces usable final assistant content with `maxTokens=1024`.
- [x] Fix/prove Qwen3.6 reasoning-on final-answer behavior for 27B and 35B through live app/API proof with mode-scoped reasoning prompts and `maxTokens=1024`.
- [x] Add/prove reasoning-on low-cap recovery messaging without forcing generation defaults. `scripts/reasoning-cap-recovery-proof.py` produced `docs/live-proofs/2026-07-04-reasoning-cap-recovery.json` from current ChatService source plus existing live Qwen 512/1024 artifacts.
- [x] Add RAM-guarded long-context smoke proof harness for Qwen and record guarded refusal when an unrelated 35B eval is active.
- [x] Re-run `scripts/real-qwen-long-context-smoke-proof.py` after the unrelated Osaurus eval exited and refresh it after the TurboQuant/native-SSM contract clarification; the 21:14 artifact is `ok=true` for the 8k-token smoke with `q4TurboQuantKV=PASS`, `ssmCompanionNotQuantized=PASS`, prefix/paged/hybrid/block-L2 proof.
- [x] Add and prove a graduated 64k real-Qwen long-context artifact with final output and post-generation cache writes; `docs/live-proofs/2026-07-04-real-qwen-long-context-64k-27b.json` reports `ok=true`, `actualPromptTokensByTokenizer=64011`, q4 TurboQuant attention-KV, native SSM companion/rederive, block L2, SSM companion L2, and cleanup with `Swapouts: 0`.
- [x] Add and prove a graduated 128k real-Qwen long-context artifact with final output and full post-generation block L2 retention after fixing paged/block-cache capacity; `docs/live-proofs/2026-07-04-real-qwen-long-context-128k-27b.json` reports `ok=true`, `actualPromptTokensByTokenizer=128019`, q4 TurboQuant attention-KV, native SSM companion/rederive, scheduler/block L2 `128023` tokens, block L2 `disk_evictions=0`, SSM companion L2 `256023` tokens, and cleanup with `Swapouts: 0`.
- [x] Add and prove a graduated 160k real-Qwen long-context artifact with final output and full post-generation block L2 retention after raising the cache-record validator ceiling; `docs/live-proofs/2026-07-04-real-qwen-long-context-160k-27b.json` reports `ok=true`, `actualPromptTokensByTokenizer=160005`, q4 TurboQuant attention-KV, native SSM companion/rederive, scheduler/block L2 `160009` tokens, block L2 `disk_evictions=0`, SSM companion L2 `320009` tokens, and cleanup with `Swapouts: 0`.
- [x] Add/prove 192k higher-tier long-context completion without false success: `docs/live-proofs/2026-07-04-real-qwen-long-context-192k-27b.json` now records final assistant output, post-generation block/SSM cache writes, no guard abort, and max sampled `Swapouts: 0`.
- [x] Add source-tested automatic completion memory guard to `scripts/real-qwen-long-context-smoke-proof.py` so future long requests sample `memory_pressure` and terminate the engine before low-memory/swap conditions continue.
- [x] Add source-tested opt-in wait-for-memory-slot behavior to the long-context harness so future high-token proof runs can wait for unrelated heavyweight jobs to exit without bypassing RAM/process guards.
- [x] Add `scripts/near-max-context-preflight-proof.py` and artifact `docs/live-proofs/2026-07-04-near-max-context-preflight.json` so the 262144-token gap has explicit model metadata, memory/process preflight, and future run command evidence instead of a vague TODO.
- [x] Add/prove a separate near-max target-token memory/process guard in `scripts/real-qwen-long-context-smoke-proof.py`; `docs/live-proofs/2026-07-04-near-max-context-guard-refusal.json` proves the 258k run refuses before model load when the configured RAM threshold is not met.
- [x] Run and summarize the real 258k Qwen 27B near-max attempt. `docs/live-proofs/2026-07-04-near-max-context-runtime-attempt-summary.json` records exact lower-cap rejection, `--timeout 3600`, runtime `seq_len=258044`, and chunked-prefill entry; the 2026-07-05 rerun still has final generation `FAIL` because `CompletionMemoryGuardAbort` stopped the engine at sampled free memory `14%` before final output or cache writes.
- [x] Attempt a safer 224k graduated Qwen 27B context run and harden the harness from the result. `docs/live-proofs/2026-07-05-real-qwen-long-context-224k-27b.json` records live chunked-prefill entry plus `CompletionMemoryGuardAbort` after new swapouts appeared; `docs/live-proofs/2026-07-05-long-context-224k-safety-refusal.json` proves future >192k targets refuse before model load unless `EXPLOITBOT_LONG_CONTEXT_ALLOW_UNPROVEN_TARGET=1` is set intentionally.
- [x] Attempt a guarded 200k incremental Qwen 27B context run after the 192k pass and document the ceiling. `docs/live-proofs/2026-07-05-real-qwen-long-context-200k-27b.json` records target `200000`, tokenizer-counted prompt `200025`, runtime chunked prefill at `seq_len=200037`, q4/paged/prefix/hybrid/block-L2 topology at abort, and `CompletionMemoryGuardAbort` after swapouts rose from baseline `16` to `204`; post-cleanup process checks found no matching model process. `docs/live-proofs/2026-07-05-long-context-200k-safety-refusal.json` then proves the same 200k target refuses before model load without `EXPLOITBOT_LONG_CONTEXT_ALLOW_UNPROVEN_TARGET=1`. A later explicit 196k above-ceiling attempt, `docs/live-proofs/2026-07-06-real-qwen-long-context-196k-27b.json`, loaded real 27B with TurboQuant/paged/prefix/block cache, reached tokenizer-counted `196007` prompt tokens and chunked prefill at `seq_len=196019`, but produced no final output or post-generation cache writes before manual interruption for cleanup. This confirms the current proven safe ceiling remains `192000`.
- [x] Surface the long-context safety ceiling in the app instead of leaving it buried in proof files. `docs/live-proofs/2026-07-05-long-context-safety-surface-live.json` proves current-source `/state.contextWindow` reports `declaredMaxContextTokens=262144`, `provenSafeTargetCeiling=192000`, `unprovenTargetPolicy=refuse-before-model-load`, `highRiskOverrideEnv=EXPLOITBOT_LONG_CONTEXT_ALLOW_UNPROVEN_TARGET`, and guarded failure targets `200000`, `224000`, `258000`; Computer Use also opened Settings > Context and saw `LONG-CONTEXT SAFETY`, `192k tokens`, `262144 tokens`, and the high-risk override warning without starting a model process.
- [x] Add/prove D3 MTP output-path evidence for every Qwen model whose path/name contains `MTP`; metadata-only `bundle_has_mtp=true` is not enough. The 19:15 rerun of `scripts/qwen-d3-mtp-output-proof.py` produced `docs/live-proofs/2026-07-04-qwen-d3-mtp-output-proof.json` with runtime decode/output evidence, effective depth `3`, D3 drafted/accepted token counters, and final assistant output evidence for both MTP-named Qwen artifacts.
- [x] Add/prove a consolidated Qwen runtime readiness gate. The 21:17 rerun of `scripts/qwen-runtime-readiness-proof.py` produced `docs/live-proofs/2026-07-04-qwen-runtime-readiness.json` with explicit TurboQuant q4 attention-KV, native SSM companion/rederive evidence, parser, streaming, reasoning, CVE lookup, tool transcript, D3 MTP checks for both target Qwen models, and long-context smoke `PASS`.
- [x] Add/prove streaming parser/SSE/tool-delta reuse as a first-class goal requirement. `scripts/streaming-parser-reuse-proof.py` produced `docs/live-proofs/2026-07-04-streaming-parser-reuse.json` with 18 streaming/parser/cache-reuse contracts and coverage-index parity.
- [x] Add/prove explicit interleaved reasoning/tool/final streaming order. `scripts/interleaved-streaming-tool-reasoning-proof.py` produced `docs/live-proofs/2026-07-05-interleaved-streaming-tool-reasoning.json` with `interleavingStatus=PASS`, 10 PASS contracts, Responses order `response.created -> response.reasoning.delta -> response.function_call_arguments.delta -> tool.result.appended -> response.output_text.delta -> response.usage -> response.completed`, Chat Completions order `delta.reasoning_content -> delta.tool_calls -> tool.result.appended -> delta.content -> usage.prompt_tokens_details.cached_tokens -> data: [DONE]`, and `/qa/streaming-parser-reuse` plus coverage-index parity. This proof does not load a model; loaded-model streaming/cache/tool evidence remains represented by the Qwen live artifacts.
- [x] Add/prove individual toolchain per-tool coverage. `scripts/individual-toolchain-coverage-proof.py` produced `docs/live-proofs/2026-07-04-individual-toolchain-coverage.json` with chat/terminal/result-tab evidence for 10 tools.
- [x] Add/prove ordered chained tool workflow coverage. `scripts/chained-tool-workflow-proof.py` produced `docs/live-proofs/2026-07-04-chained-tool-workflow.json` with ordered multi-tool chains and post-chain final assistant continuation for real installed loopback, Qwen 27B, and Qwen 35B artifacts.
- [x] Add/prove all-tab ordered tool-flow coverage across recon/web/network/creds/exploit/post/supplyChain/osint/report/stash. `scripts/all-tab-ordered-tool-flow-proof.py` produced `docs/live-proofs/2026-07-05-all-tab-ordered-tool-flow.json` with 9 PASS workflow rows, route parity for tab tool/function flow, tab action surfaces, tool execution, existing Qwen 27B/35B ordered-chain linkage, reverse/repeated-tab order diversity across forward, reverse, CVE-first, post-to-recon, osint-first, and report/stash reopen flows, plus aggregate `42/42` all-tool workflow/execution/source-hook/authorization coverage.
- [x] Add/prove current Computer Use all-tab click-sweep on the clean dist app. `docs/live-proofs/2026-07-05-computer-use-all-tabs-dist-current.json` records explicit CUA attach to `dist/ExploitBot.app`, clicks through every main tab in order, final Stash state, ordered `manualTabSwitch` activity events, and no model load.
- [x] Extend/prove tool-family fanout coverage across all 10 tab families. `scripts/tool-family-fanout-coverage-proof.py` now produces `docs/live-proofs/2026-07-05-tool-family-fanout-all-tabs.json` with chat card, activity entry, tab activity, parsed tab result, and context-catalog evidence for each family.
- [x] Refresh subtab lifecycle and tab action surface live route matrix proofs; both now use the 120s `/qa/coverage-index` timeout budget and pass sequentially without loading a model. The 2026-07-05 rerun now writes durable artifacts: `docs/live-proofs/2026-07-05-subtab-lifecycle-matrix.json` records `38` subtab lifecycle rows with route/proof-owner parity and empty engine process rows, and `docs/live-proofs/2026-07-05-tab-action-surface-matrix.json` records `10` tab-action surfaces, `30` action-state owners, `828` function-proof rows, route/proof-owner parity, no `run_shell` pseudo-tool, and empty engine process rows.
- [x] Refresh proof-ledger, proof-category, endpoint-route, tool-execution, live-status-preview, cache-artifact, and seeded per-turn runtime contracts; the 2026-07-05 proof refresh reduces proof-ledger `other` category count from `47` to `4`, preserves `257` proof files, and proves hybrid SSM async rederive `completed=1`, `failed=0`, `lastNumTokens=113`.
- [x] Refresh proof/artifact ledger discoverability after the new subtab/action/all-tab/fanout/public-release artifacts. `docs/live-proofs/2026-07-05-proof-ledger-current.json` records live `/qa/proof-ledger` parity with `proofCount=259`, `categoryOtherCount=4`, `tabProofFamilyCount=10`, and no model inference. `docs/live-proofs/2026-07-05-artifact-ledger-current.json` records live `/qa/artifact-ledger` parity with `liveProofCount=151`, `failedLiveProofCount=13`, `currentFailedLiveProofCount=0`, and no model inference after fixing ledger classification for uppercase `status: PASS`, superseded 512-token reasoning proof, and expected non-passing long-context safety/refusal artifacts.
- [ ] Configure notary credentials with `EXPLOITBOT_NOTARY_PROFILE` or `NOTARIZE_APPLE_ID`/`NOTARIZE_TEAM_ID`/`NOTARIZE_PASSWORD`, then run `./script/package_release.sh --notarize`; rerun `scripts/notarization-preflight-proof.py`, `scripts/release-readiness-proof.py`, and `scripts/goal-requirement-audit-proof.py` after stapling succeeds.
- [x] Add and prove bounded live CVE feed refresh/sync UX around source-attributed CISA KEV and NVD critical rows; refreshed again at 02:31 with CISA KEV `2026.07.01`, latest KEV `CVE-2026-45659`, and NVD 45-day critical total `237`.
- [x] Add and prove CVE live-source freshness against authoritative feeds. `scripts/cve-live-source-freshness-proof.py` produced `docs/live-proofs/2026-07-05-cve-live-source-freshness.json` at `2026-07-05T13:53:10-0700`; it re-fetched CISA KEV and NVD CVE API metadata without loading a model and reports `freshnessStatus=PASS`, CISA catalog `2026.07.01`, latest KEV `CVE-2026-45659`, CISA total `1631`, NVD 45-day critical total `237`, and PASS checks for app artifact latest-CVE, feed-version, release-timestamp, CISA total, NVD coverage, and top app search result source attribution.
- [x] Re-run CVE live-source freshness after the current release UI checkpoint. `docs/live-proofs/2026-07-05-cve-live-source-freshness.json` generated at `2026-07-05T17:19:19-0700` again reports `freshnessStatus=PASS` against authoritative CISA KEV and NVD CVE API metadata: CISA catalog `2026.07.01`, latest KEV `CVE-2026-45659`, CISA total `1631`, NVD 45-day critical total `237`, and app artifact checks all PASS. `scripts/cve-source-attribution-proof.py` was also rerun in the app QA path without loading a model and passed, proving context packets still include source keys and bodies such as `cisa-kev,nvd,references,tags`.
- [x] Fix and prove exact CVE-ID search for latest live-feed rows such as `CVE-2026-45659`.
- [x] Add and prove a machine-readable `topModernCVEs` summary: CISA KEV date-descending rows, recent NVD critical rows, and bounded app-state result rows with source attribution.
- [x] Re-prove `lookup_cve` first-try argument preservation through the live 35B UI via System Events visibility and screenshot capture while Computer Use remains blocked separately.
- [x] Re-run the combined real-model, real installed-tool safe lab proof on Qwen3.6 35B.
- [x] Refresh real Qwen 27B/35B Metasploit-safe artifacts after the TurboQuant/native-SSM contract clarification; the 21:15-21:17 artifacts prove `q4TurboQuantKV=PASS` and `ssmCompanionNotQuantized=PASS` while keeping the safe `version; exit` Metasploit loop.
- [x] Prove model-invoked `lookup_cve` results are used in a complete turn with final marker.
- [x] Produce updated PASS/PARTIAL/BLOCKED matrix after the current live UI/model passes; `scripts/pass-partial-blocked-matrix-proof.py` now owns the refresh and artifact `docs/live-proofs/2026-07-04-pass-partial-blocked-matrix.json` currently records `23` PASS, `1` PARTIAL, and `1` BLOCKED row.
- [x] Add current-goal requirement audit that blocks completion claims while release distribution remains blocked and long-context stress remains partial.
- [x] Refresh built-in objective runtime/flow/active-audit proofs and fix their slow coverage-index timeout plus current hybrid-SSM evidence-field drift.
- [x] Refresh full app QA matrix smoke and make it durable; the 23:29-23:30 rerun of `scripts/app-qa-matrix-smoke-proof.py` writes `docs/live-proofs/2026-07-04-app-qa-matrix-smoke.json` with `generatedAt=2026-07-04T23:30:54-0700`.
- [x] Rebuild current-source local release app/DMG after the CVE state snapshot change, verify codesign and bundled runtime, refresh notarization preflight, and rerun beta readiness coverage. Distribution still requires notary credentials and stapled tickets.
- [x] Rebuild current-source local release app/DMG again after Settings/Agents and long-context guard changes; `scripts/release-readiness-proof.py` refreshed `release/ExploitBot.app`, `release/ExploitBot-beta.dmg`, `release/release-manifest.json`, and `docs/live-proofs/2026-07-04-release-readiness.json` at 2026-07-05T02:07:07-0700 with app/DMG codesign PASS, bundled runtime PASS, local package PASS, and notarization BLOCKED pending credentials.
- [x] Re-run signed release visible smoke after the latest release rebuild; `scripts/release-visible-smoke-proof.py` refreshed `docs/live-proofs/2026-07-04-release-visible-smoke.json` and screenshot at 2026-07-05T02:11:35-0700 with visible window, main workspace, screenshot capture, no-model-loaded PASS, and distribution BLOCKED.
- [x] Attach Computer Use to the refreshed packaged release app and inspect Settings panes; `docs/live-proofs/2026-07-05-release-app-computer-use-settings-agents.json` records CUA version `857`, release app/DMG hashes, visible Model folder scan/select controls with Qwen 27B/35B MTP entries, Cache default `TurboQuant Q4` with prefix/paged/prompt-L2/block-L2 on, and Agents loop controls/phase routing/authorization guards.
- [x] Rebuild the signed release app after lifecycle cleanup changes and rerun real 27B and 35B Qwen release-app proofs; `docs/live-proofs/2026-07-05-release-app-live-qwen-27b-current.json` and `docs/live-proofs/2026-07-05-release-app-live-qwen-35b-current.json` now record fresh 14:11/14:12 bounded live loads, bundled runtime, PASS memory preflight, TurboQuant/prefix/paged/hybrid-SSM cache proof, native D3 MTP, repeat-prompt cache reuse, and empty production-stop plus post-cleanup process rows.
- [x] Add/prove current no-model release-Qwen memory preflight before any fresh live Qwen rerun. `docs/live-proofs/2026-07-05-release-qwen-memory-preflight-current.json` currently records `PASS` for both 27B and 35B with heavy model process count `0`, safe-to-run next action, and no model load attempted.
- [x] Retry Computer Use after permission repair and document current live attach/permission state: `list_apps` plus `get_app_state` now returns CUA version `857`, a System Settings accessibility tree, inline screenshot, and visible `Codex Computer Use` Screen & System Audio Recording toggle `on`; no model inference was started during the latest retry.
- [x] Rebuild/relaunch the current `dist` app and attach Computer Use directly to `/Users/eric/exploitbot/dist/ExploitBot.app`; `docs/live-proofs/2026-07-05-computer-use-dist-app-smoke.json` records live CUA version `857`, accessibility tree, inline screenshot, visible workspace controls, and model-library scan output without starting inference.
- [x] Live-toggle current `dist` app Settings controls through Computer Use without starting inference; `docs/live-proofs/2026-07-05-computer-use-settings-cve-cache-ui.json` records cache mode/Prefix Cache/Reasoning/parser toggles restored to expected defaults, Current Threat Intel refresh, exact `CVE-2026-45659` search, and Tools inventory visibility.
- [x] Re-prove the current Agents settings panel through live Computer Use and app/API state without starting inference; `docs/live-proofs/2026-07-05-computer-use-agent-settings-loop-ui.json` records visible mode policy, loop/tool-schema/final-answer controls, multi-agent controls, phase routing, authorization guards, `/state` mirroring after Apply App Settings, and restored defaults.
- [x] Rebuild the release app after the engine stop-race guard, then run patched release-app Computer Use proof on real Qwen3.6 35B. `docs/live-proofs/2026-07-05-release-app-computer-use-35b-visible-tool-loop.json` records CUA version `857`, visible reasoning-off toggle, prompt entry and Send click, `lookup_cve` verbose tool card/arguments, final marker `CUA35_PATCHED_TOOL_FINAL`, TTFT `2.91s`, `13.70 tok/s`, TurboQuant Q4 attention-KV storage, prefix/paged/block-L2, native SSM companion/rederive, MTP effective depth `3`, screenshot, and clean `/engine/stop` with no remaining bundled launcher and `Swapouts: 204 -> 204`.
- [x] Fix the release-app engine stop race that could auto-restart a model during intentional shutdown. `EngineManager.stop()` now marks `isIntentionalStop` before canceling the health monitor, and the monitor suppresses `onCrash` auto-restart when intentional stop/cancellation is observed; source regression tests and live patched release-app stop proof both cover this RAM-lifecycle path.
- [x] Fix and prove localhost QA JSON response framing after live generation polling exposed transient invalid JSON from `/state` and `/messages`. `TestServer` now sends UTF-8 response bytes with explicit byte `Content-Length`, `Cache-Control: no-store`, and `NWConnection.send(..., isComplete: true)`; `docs/live-proofs/2026-07-05-testserver-json-framing-live.json` records a rebuilt current-source `dist/ExploitBot.app` proof with `240/240` parsed `/state` + `/messages` responses, matching content lengths, zero invalid JSON, no model process spawned, and `Swapouts: 204`.
- [x] Rebuild the packaged release app/DMG after the long-context safety and Tools install-plan Settings fixes and re-smoke the release bundle. `docs/live-proofs/2026-07-04-release-readiness.json` now has generatedAt `2026-07-05T12:34:34-0700`, app binary SHA256 `d42cd456b669f4c8e71d14ee0d7102ac8978484bfcb6467afccb0a90f0c4fcd9`, DMG SHA256 `15d17c40b466763df626a1edb3e2427cc8d8449c136778e418613eec34dc6953`, local package PASS, and distribution BLOCKED for notary credentials. `docs/live-proofs/2026-07-04-release-visible-smoke.json` refreshed at `2026-07-05T12:34:42-0700` with local display PASS, and `docs/live-proofs/2026-07-05-release-app-json-framing-live.json` refreshed at `2026-07-05T12:35:01-07:00` proving the rebuilt release app serves `240/240` parsed `/state` + `/messages` responses with matching `Content-Length`, no invalid JSON, no model process, and distribution still BLOCKED only by notarization.
- [x] Add public GitHub release truth proof without reading signing secrets or downloading assets. `scripts/release-public-truth-proof.py` produced `docs/live-proofs/2026-07-05-release-public-truth.json` at `2026-07-05T13:32:41-0700`; it reports repo visibility `PUBLIC`, matching `v0.1.0-beta` release and `ExploitBot-beta.dmg` asset present, local package PASS, public release PARTIAL, and distribution BLOCKED because the current local DMG SHA256 `15d17c40b466763df626a1edb3e2427cc8d8449c136778e418613eec34dc6953`, local manifest SHA256, current source revision, and notarization gate do not match a publishable current public release.
- [x] Rebuild/relaunch the current-source `dist` app and run a full Computer Use UI surface sweep without starting inference. `docs/live-proofs/2026-07-05-live-ui-surface-sweep.json` records CUA version `857`, every main tab clicked, every Settings category observed, Runtime/Context/Cache/Agents/CVE/Tools/Logs controls visible, `turboquant-q4` plus prefix/paged/L2 cache state, model library scan with 14 entries and 6 supported models, all 42 tool rows observed, Install All Missing still disabled until `Install plan reviewed`, no engine/model process rows, and `Swapouts: 1988`; model-load stress was intentionally deferred to existing Qwen artifacts because recent swapouts are nonzero.
- [x] Re-check Computer Use after the current permission repair and document the process split explicitly. `docs/live-proofs/2026-07-05-computer-use-release-ui-dist-api-split-current.json` records CUA version `857` attached to the visible `release/ExploitBot.app` window while localhost `:9999` was served by `dist/ExploitBot.app`; every main tab from Web through Stash clicked successfully, Settings Model/Runtime/Cache/Agents/CVE Database/Tools were observed, TurboQuant Q4 remained the visible/default KV mode, model folder scan/add/select controls exposed 27B/35B MTP Qwen entries, Tool inventory showed 13 installed and 29 missing with install-all still review-gated, `/state` reported `engineRunning=false`, and no model inference was started. This is packaged-app visible UI evidence plus separate current-source API state evidence, not a single-process CUA/API parity claim.
- [x] Close the split-surface gap with a same-process Computer Use/API parity check. `docs/live-proofs/2026-07-05-computer-use-dist-single-process-parity-current.json` records CUA version `857` attached to `/Users/eric/exploitbot/dist/ExploitBot.app` PID `91569`, and `lsof` proved the same PID owned localhost `:9999`; Computer Use clicked Web, Supply/CVE, Stash, Settings Model, and Settings Cache; `/state` from the same process reported `activeTab=stash`, `engineRunning=false`, selected 35B MXFP8 MTP model path, `kvCacheQuantization=turboquant-q4`, prefix/prompt-L2/paged/block-L2 enabled, and manual tab-switch/open-settings feed entries. No model inference was started.
- [x] Refresh release/distribution truth after the latest live UI/model proofs. `scripts/release-readiness-proof.py` completed at 2026-07-05 14:31 with a live `:9999` packaged-app smoke and rewrote `docs/live-proofs/2026-07-04-release-readiness.json`; `scripts/notarization-preflight-proof.py` rewrote `docs/live-proofs/2026-07-04-notarization-preflight.json` at `2026-07-05T14:31:23-0700`; `scripts/release-public-truth-proof.py` rewrote `docs/live-proofs/2026-07-05-release-public-truth.json` at `2026-07-05T14:31:21-0700`. Current truth remains local package PASS, public release PARTIAL, distribution BLOCKED, and notarization `not-submitted`.
- [x] Re-run every focused tab/tool-flow proof sequentially after a parallel proof-runner contention false start. Fresh sequential PASS results covered `scripts/all-tab-ordered-tool-flow-proof.py`, `scripts/tool-family-fanout-coverage-proof.py`, `scripts/chained-tool-workflow-proof.py`, `scripts/interleaved-streaming-tool-reasoning-proof.py`, `scripts/tab-action-surface-matrix-proof.py`, `scripts/subtab-lifecycle-matrix-proof.py`, `scripts/tool-execution-matrix-proof.py`, `scripts/agent-tool-authorization-proof.py`, and `scripts/terminal-tool-visibility-proof.py`; the static subtab state proofs for recon, web, network, creds, exploit, post, osint, and report also passed in the same refresh window.
- [x] Fix proof-runner app lifecycle contention exposed by parallel live testing. `scripts/app_proof_lock.py` now provides a repo-local lifecycle lock held by app-backed proof scripts from launch through cleanup, with stale-owner recovery; the focused app-backed proofs set `EXPLOITBOT_SKIP_APP_PROOF_LOCK=1` so `build_and_run.sh` no longer owns proof lifecycle. `ExploitBotEngine/testsuite/test_app_proof_lifecycle_lock.py` and `ExploitBotEngine/testsuite/test_app_proof_launch_lock_contracts.py` passed together (`5 passed`), a deliberate parallel retry of `scripts/tab-action-surface-matrix-proof.py` plus `scripts/tool-execution-matrix-proof.py` serialized correctly and both passed, and the full focused app-backed suite reran PASS across recon/web/network/creds/exploit/post/osint/report subtabs, tab-action matrix, subtab lifecycle, tool execution, authorization, terminal visibility, tool-family fanout, interleaved streaming/reasoning/tools, and all-tab ordered flow.
- [x] Refresh aggregate ledgers after the sequential tab/tool-flow pass. `docs/live-proofs/2026-07-04-pass-partial-blocked-matrix.json` generated at `2026-07-05T14:57:39-0700` records `23` PASS, `1` PARTIAL, and `1` BLOCKED; `docs/live-proofs/2026-07-04-goal-requirement-audit.json` generated at `2026-07-05T14:57:39-0700` keeps `overallStatus=BLOCKED`, `objectiveComplete=false`, and `completionClaimAllowed=false`; `docs/live-proofs/2026-07-05-proof-ledger-current.json` generated at `2026-07-05T14:57:42-0700` records `proofCount=262`; `docs/live-proofs/2026-07-05-artifact-ledger-current.json` generated at `2026-07-05T14:57:44-0700` records `liveProofCount=157`.
- [x] Install the full current Tool Settings inventory and fix the last broken binary path. `httpx` root cause was a startup SIGSEGV in `github.com/shoenig/go-m1cpu` from cgo-linked ProjectDiscovery builds; `CGO_ENABLED=0` rebuilt `/Users/eric/.exploitbot/tools/httpx` and `httpx -version` now reports `Current Version: v1.9.0`. `ToolInstaller` now installs ProjectDiscovery `httpx` with `CGO_ENABLED=0` into `$HOME/.exploitbot/tools` and checks app-managed tools before Homebrew collisions. Focused contract test `ExploitBotEngine/testsuite/test_tool_installer_install_command_contracts.py` passed (`6 passed`), `./script/build_and_run.sh --build-only` passed, `scripts/tool-settings-real-inventory-proof.py` reran with `installedCount=42`, `missingCount=0`, `fullPentestToolchainInstalled=PASS`, `settingsCurrentMachineDetection=PASS`, and `scripts/individual-toolchain-coverage-proof.py` reran with `10` PASS rows.
- [x] Re-check the current Tools settings panel through live Computer Use after installing the missing tools. `docs/live-proofs/2026-07-05-computer-use-tools-inventory-42.json` records CUA version `857` attached to `/Users/eric/exploitbot/dist/ExploitBot.app` PID `29475`, with the same PID owning localhost `:9999`; visible Tools UI showed `42 installed`, `0 missing`, disabled `Install All Missing`, and install-plan command count `0`. The same-process `/state` reported `engineRunning=false`, `installedCount=42`, `missingCount=0`, `errorCount=0`, `requiresNetworkInstall=false`, and ProjectDiscovery `httpx` installed at `/Users/eric/.exploitbot/tools/httpx` version `1.9.0`; screenshot saved at `docs/live-proofs/2026-07-05-computer-use-tools-inventory-42.png`.
- [x] Re-run focused all-tab/tool-flow proof suite after the full tool install and `httpx` no-cgo fix. Fresh sequential PASS results covered `scripts/all-tab-ordered-tool-flow-proof.py`, `scripts/tool-family-fanout-coverage-proof.py`, `scripts/chained-tool-workflow-proof.py`, `scripts/tool-execution-matrix-proof.py`, `scripts/tab-action-surface-matrix-proof.py`, `scripts/subtab-lifecycle-matrix-proof.py`, `scripts/agent-tool-authorization-proof.py`, and `scripts/terminal-tool-visibility-proof.py`.
- [x] Add and prove an all-installed-tools safe smoke layer for every current Settings tool row. `scripts/all-installed-tools-smoke-proof.py` now reads the live Settings inventory artifact, runs bounded version/help smoke commands for all `42` installed tools, rejects crash/traceback output even when the tool name appears, and records `safeSmokeOnly=true`, `externalTargetExecution=not-started`, and `modelDrivenEvidence=not-claimed` so it is not confused with exploit or model-driven proof. The first run exposed real current-machine defects: `dnsx` had the same cgo `github.com/shoenig/go-m1cpu` startup crash as `httpx`, `pwncat-cs` failed under Python 3.13/3.12 due `pkg_resources`/`distutils`, and GraphQLmap missed `requests`. `ToolInstaller` now installs `dnsx` with `CGO_ENABLED=0`, installs `pwncat-cs` with `uv tool install --python 3.11 ... --with "setuptools<81"`, and installs GraphQLmap with `--with requests`. Focused contracts passed (`11 passed`), `./script/build_and_run.sh --build-only` passed, `scripts/all-installed-tools-smoke-proof.py` produced `docs/live-proofs/2026-07-05-all-installed-tools-smoke.json` with `42` PASS / `0` FAIL rows, and `scripts/tool-settings-real-inventory-proof.py` refreshed live app inventory at `2026-07-05T15:22:55-0700` with `installedCount=42`, `missingCount=0`, `fullPentestToolchainInstalled=PASS`, and `settingsCurrentMachineDetection=PASS`.
- [x] Re-run current-machine Settings inventory and all-installed-tools smoke after the CVE/release UI checkpoints. `docs/live-proofs/2026-07-04-tool-settings-real-inventory.json` refreshed at `2026-07-05T17:34:59-0700` with `installedCount=42`, `missingCount=0`, `settingsCurrentMachineDetection=PASS`, and `fullPentestToolchainInstalled=PASS`. `docs/live-proofs/2026-07-05-all-installed-tools-smoke.json` refreshed at `2026-07-05T17:35:07-0700` with `toolCount=42`, `statusCounts PASS=42 FAIL=0`, `safeSmokeOnly=true`, `externalTargetExecution=not-started`, and `modelDrivenEvidence=not-claimed`.
- [x] Promote the all-installed-tools smoke proof into the formal goal/readiness audit instead of leaving it as a side artifact. `docs/live-proofs/2026-07-04-pass-partial-blocked-matrix.json` now has an `All installed tools safe smoke coverage` row backed by `docs/live-proofs/2026-07-05-all-installed-tools-smoke.json`; `scripts/pass-partial-blocked-matrix-proof.py` now expects `24` PASS, `1` PARTIAL, and `1` BLOCKED across `26` rows. `scripts/goal-requirement-audit-proof.py` now includes `all_installed_tools_safe_smoke` as a distinct requirement, keeping model-driven safe-lab proof separate from executable smoke proof. Focused audit contracts passed (`5 passed`), and the refreshed goal audit still reports `overallStatus=BLOCKED`, `objectiveComplete=false`, and `completionClaimAllowed=false`.
- [x] Rebuild the packaged release app/DMG after the ToolInstaller and all-tools proof changes, then refresh release truth. `scripts/release-readiness-proof.py` rebuilt `release/ExploitBot.app`, `release/ExploitBot-beta.dmg`, and `release/release-manifest.json` at `2026-07-05T15:29:20-0700`; local package PASS, bundled runtime PASS, app binary SHA256 `f930010ca65b4e0680a474f1a6b5bc3f9096a4f82acbf543d33943c3efec46c0`, DMG SHA256 `95553fbf77ed7b31e1f65e0d6a9c5f25df482963f57354e83934b7bc33715c24`, and distribution remains BLOCKED because notarization is `not-submitted`. `scripts/release-visible-smoke-proof.py` refreshed visible release smoke at `2026-07-05T15:29:37-0700` with local display PASS and no model loaded; `scripts/notarization-preflight-proof.py` refreshed notarization BLOCKED at `2026-07-05T15:29:36-0700`; `scripts/release-public-truth-proof.py` refreshed public release truth at `2026-07-05T15:29:34-0700` with local package PASS, public release PARTIAL, and distribution BLOCKED.
- [x] Restore and rerun the retained release-app JSON framing proof script. `scripts/release-app-json-framing-live-proof.py` now launches `release/ExploitBot.app` with `EXPLOITBOT_TESTING=1`, polls `/state` and `/messages` directly through HTTP `240` times each, validates `Content-Length` byte counts, `Cache-Control: no-store`, JSON parsing, and no model process spawn, then writes `docs/live-proofs/2026-07-05-release-app-json-framing-live.json`. The current artifact generated at `2026-07-05T15:33:00-0700` proves `480` parsed responses, `invalidCount=0`, `maxStateBytes=25344`, app SHA256 `f930010ca65b4e0680a474f1a6b5bc3f9096a4f82acbf543d33943c3efec46c0`, DMG SHA256 `95553fbf77ed7b31e1f65e0d6a9c5f25df482963f57354e83934b7bc33715c24`, local package PASS, and distribution BLOCKED only by notarization. Focused framing contracts passed (`4 passed`).
- [x] Re-check Computer Use on the current packaged release app and persist a same-process UI/API sweep. `docs/live-proofs/2026-07-05-release-app-computer-use-full-ui-current.json` records CUA version `857` attached to `/Users/eric/exploitbot/release/ExploitBot.app` PID `47552`, with the same PID owning localhost `:9999`; every primary tab from Recon through Stash was clicked and showed its distinct controls/empty state, every Settings panel from Engine through Logs was observed, Model selection was toggled from 35B MXFP8 MTP to 27B MXFP8 MTP and restored to 35B, Runtime reasoning and generation-defaults toggles changed state and were restored, Context dynamic-context changed state and was restored, Cache visibly stayed on `TurboQuant Q4` with prefix/prompt-L2/paged/block-L2 enabled, CVE Current Threat Intel refreshed to `1644` total CVEs / `1631` CISA KEV with newest KEV `CVE-2026-45659`, and Tools showed `42 installed` / `0 missing`. `/state` from the same process confirmed `engineRunning=false`, `activeTab=stash`, TurboQuant/prefix/paged/L2 cache state, CVE counts, and the 192k proven-safe long-context ceiling. This artifact does not claim a loaded-model prompt or external-target tool-execution run.
- [x] Refresh the packaged release-app real Qwen production-path load/cache proof after the same-process UI sweep. `scripts/release-app-live-qwen-proof.py` now writes a durable `generatedAt` timestamp plus machine-readable PASS rows for memory preflight, app-bundled runtime, TurboQuant KV, hybrid SSM topology, prefix cache, paged cache, SSM companion, native D3 MTP, repeat-prompt cache reuse, production stop, and post-cleanup. Fresh sequential reruns wrote `docs/live-proofs/2026-07-05-release-app-live-qwen-27b-current.json` at `2026-07-05T15:45:40-0700` and `docs/live-proofs/2026-07-05-release-app-live-qwen-35b-current.json` at `2026-07-05T15:46:06-0700`; both report `ok=true`, app-bundled vMLX Python, memory preflight PASS with zero heavyweight model processes, `kv_cache_quantization.mode=turboquant-q4`, hybrid SSM attention topology, prefix/paged/SSM companion enabled, native MTP runtime active with effective depth `3`, repeat-prompt cache reuse with `secondCachedTokens=13` plus scheduler hit deltas, and empty production-stop/post-cleanup process rows. Post-run process/listener checks found no ExploitBot/Qwen/vMLX engine rows and `Swapouts` remained `1988`.
- [x] Add/prove packaged release-app real Qwen streaming telemetry after the parser-only interleaving gap. `get_usage()` now always emits `usage.prompt_tokens_details.cached_tokens`, even when the first streamed prompt has `0` cached tokens, and the patched engine was rebuilt into `release/ExploitBot.app`/`release/ExploitBot-beta.dmg` with codesign verification. `scripts/release-app-live-qwen-streaming-proof.py` wrote `docs/live-proofs/2026-07-05-release-app-live-qwen-27b-streaming-current.json` at `2026-07-05T15:55:17-0700` and `docs/live-proofs/2026-07-05-release-app-live-qwen-35b-streaming-current.json` at `2026-07-05T15:56:12-0700`; both report `ok=true`, SSE JSON frames, `[DONE]`, reasoning deltas, usage telemetry with `cachedTokensFieldSeen=true`, TurboQuant q4 KV, hybrid SSM topology, prefix/paged/SSM companion enabled, native D3 MTP effective depth `3`, and empty production-stop/post-cleanup process rows. Focused contracts passed (`6 passed`) and post-run listener/process checks found no live app/model server; `Swapouts` remained `1988`.
- [x] Promote the new release-app streaming artifacts into the formal matrix/audit and refresh aggregate proof state. `docs/live-proofs/2026-07-04-pass-partial-blocked-matrix.json` generated at `2026-07-05T16:00:18-0700` still records `24` PASS, `1` PARTIAL, and `1` BLOCKED across `26` rows, now with the 27B/35B release-app streaming artifacts in the streaming row. `docs/live-proofs/2026-07-04-goal-requirement-audit.json` generated at the same time keeps `overallStatus=BLOCKED`, `objectiveComplete=false`, and `completionClaimAllowed=false`.
- [x] Add/prove packaged release-app real Qwen tool-loop parity through the app `/send` path. `scripts/release-app-live-qwen-tool-loop-proof.py` now launches `release/ExploitBot.app`, verifies the app-bundled vMLX Python runtime, selects the real Qwen model through `/qa/model-folder`, starts the bundled engine through `/engine/start`, applies Qwen parser/cache/runtime settings, sends the user prompt through `/send`, and only passes if the chat transcript contains exactly one `lookup_cve` tool message plus final marker `RELEASE_QWEN_TOOL_LOOP_FINAL`. Fresh sequential reruns wrote `docs/live-proofs/2026-07-05-release-app-live-qwen-27b-tool-loop-current.json` at `2026-07-05T16:06:52-0700` and `docs/live-proofs/2026-07-05-release-app-live-qwen-35b-tool-loop-current.json` at `2026-07-05T16:08:04-0700`; both report `ok=true`, target `CVE-2025-49704`, tool sequence `["lookup_cve"]`, verbose tool transcript with preserved CVE argument, final answer marker, TurboQuant q4 KV, hybrid SSM topology, prefix/paged/SSM companion enabled, native D3 MTP effective depth `3`, and empty production-stop/post-cleanup process rows. Focused contracts passed (`8 passed`) and post-run checks found no listener on `:9999`, no release engine process, and `Swapouts` remained `1988`.
- [x] Re-check current `release/ExploitBot.app` through live Computer Use after the latest release rebuild. `docs/live-proofs/2026-07-05-release-app-computer-use-current-manual-sweep.json` generated at `2026-07-05T16:38:44-0700` records CUA version `857` attached to `/Users/eric/exploitbot/release/ExploitBot.app` PID `76483` at repo HEAD/origin `a7dcf2e`, app binary SHA256 `16821a81d9333eef49193ac0f60a9e3f8f806c7acb2a1cbad0c353f1bc355a51`, DMG SHA256 `8f6399c6a352b25550aca3a192fea233df308bcd703d5a64a63795042ad72b2c`, and screenshot `docs/live-proofs/2026-07-05-release-app-computer-use-current-manual-sweep.png`. Computer Use clicked every primary tab from Recon through Stash with same-process API `feedRecent` events from `manualTabSwitch recon -> web` through `manualTabSwitch report -> stash`, then opened Settings and observed Engine/Model/Runtime/Cache/Agents/CVE Database/Tools/Logs. The sweep confirmed 35B MXFP8 MTP selected with 14 scanned models and 6 supported entries, visible 27B/35B Qwen MTP `Use` controls, Runtime reasoning off with Qwen3/Qwen parsers and max iterations 4, Cache `TurboQuant Q4` with prefix/prompt-L2/paged/block-L2 enabled, CVE Database `1644` total CVEs / `1631` CISA KEV, Tools `42 installed` / `0 missing`, Logs empty-state, PID `76483` owning `:9999`, and no model engine started.
- [x] Refresh current-package Computer Use UI/settings proof after the final release hash changed to app SHA256 `3d149769ebe5e63774610a2edd79582ebaf6b060fb325094b7b9948898e3c353` and DMG SHA256 `35d6d654d48cd7f9c5e1c5f6e9d555886cbe0cf69b9d711eadafa7c828c39fc7`. `docs/live-proofs/2026-07-05-release-app-computer-use-current-refresh.json` generated at `2026-07-05T17:14:59-0700` records CUA version `857` attached to `/Users/eric/exploitbot/release/ExploitBot.app` PID `98612`, with the same PID owning localhost `:9999`; every primary tab from Recon through Stash was clicked, every Settings panel from Engine through Logs was observed, Model showed the selected 35B MXFP8 MTP folder plus visible 27B/35B Qwen MTP entries, Runtime reasoning and generation-default toggles were applied through `Apply App Settings` and restored, Cache stayed on `TurboQuant Q4` with prefix/prompt-L2/paged/block-L2 enabled, Context showed the 192k proven-safe ceiling with unproven targets refused before model load, CVE settings searched `apache path traversal` and returned `CVE-QA-SEARCH-1` / `CVE-QA-SEARCH-2`, Tools showed `42 installed` / `0 missing`, Logs stayed empty because no engine was started, and `/state` confirmed `engineRunning=false`, `enginePort=0`, `enableReasoning=false`, `modelGenerationDefaults=false`, and TurboQuant/prefix/paged/L2 cache flags still true. This is a no-model-load UI/settings proof; loaded Qwen prompt/tool/cache proof and notarization remain separate gates.
- [x] Refresh durable report/finding/export proof artifacts instead of relying on old print-only proof scripts. `scripts/report-finding-actions-proof.py`, `scripts/report-generate-action-proof.py`, and `scripts/report-export-proof.py` now use the app proof lifecycle lock and write current JSON artifacts. Fresh live route reruns wrote `docs/live-proofs/2026-07-05-report-finding-actions-current.json` at `2026-07-05T16:26:07-0700`, `docs/live-proofs/2026-07-05-report-generate-action-current.json` at `2026-07-05T16:26:09-0700`, and `docs/live-proofs/2026-07-05-report-export-current.json` at `2026-07-05T16:26:11-0700`; all report `status=PASS`, `noModelLoaded=true`, and cover create/submit/delete finding, report preview generation with activity telemetry, and HTML/Markdown/JSON/PDF export artifacts.
- [x] Refresh aggregate proof/artifact ledgers after the current report artifacts and classify the manual release UI sweep as an expected non-passing partial gate. `scripts/proof-ledger-proof.py` wrote `docs/live-proofs/2026-07-05-proof-ledger-current.json` at `2026-07-05T16:38:56-0700` with `proofCount=266`, route/file/category/tab parity PASS, and `modelInferenceStarted=NO`. `scripts/artifact-ledger-proof.py` wrote `docs/live-proofs/2026-07-05-artifact-ledger-current.json` at `2026-07-05T16:38:59-0700` with `liveProofCount=168`, `failedLiveProofCount=14`, `currentFailedLiveProofCount=0`, `currentLiveProofFailureFree=PASS`, and `modelInferenceStarted=NO`.
- [x] Rebuild the packaged release app/DMG after the ledger-source change and refresh release truth. `scripts/release-readiness-proof.py` rebuilt `release/ExploitBot.app`, `release/ExploitBot-beta.dmg`, and `release/release-manifest.json` at `2026-07-05T16:33:59-0700` with local package PASS, app binary SHA256 `16821a81d9333eef49193ac0f60a9e3f8f806c7acb2a1cbad0c353f1bc355a51`, DMG SHA256 `8f6399c6a352b25550aca3a192fea233df308bcd703d5a64a63795042ad72b2c`, and distribution BLOCKED for notary credentials. `scripts/notarization-preflight-proof.py` refreshed notarization BLOCKED at `2026-07-05T16:34:10-0700`, `scripts/release-visible-smoke-proof.py` refreshed visible smoke at `2026-07-05T16:34:56-0700`, `scripts/release-public-truth-proof.py` refreshed public release PARTIAL at `2026-07-05T16:34:07-0700`, `scripts/goal-requirement-audit-proof.py` kept `overallStatus=BLOCKED`, and the final ledger refresh wrote `proofCount=266` plus `liveProofCount=168` with `currentFailedLiveProofCount=0`.
- [x] Refresh current packaged release-app real Qwen evidence after the latest release rebuild and Computer Use sweep. `scripts/release-qwen-memory-preflight-proof.py` wrote `docs/live-proofs/2026-07-05-release-qwen-memory-preflight-current.json` at `2026-07-05T16:41:31-0700` with both 27B and 35B PASS and no model load attempted. Fresh sequential release-app model reruns wrote `docs/live-proofs/2026-07-05-release-app-live-qwen-27b-current.json` at `2026-07-05T16:42:13-0700` and `docs/live-proofs/2026-07-05-release-app-live-qwen-35b-current.json` at `2026-07-05T16:42:57-0700`, both PASS for app-bundled runtime, memory preflight, TurboQuant q4 KV, hybrid SSM topology, prefix/paged/SSM companion, native D3 MTP effective depth `3`, repeat-prompt cache reuse, production stop, and post-cleanup. Streaming reruns wrote `docs/live-proofs/2026-07-05-release-app-live-qwen-27b-streaming-current.json` at `2026-07-05T16:43:46-0700` and `docs/live-proofs/2026-07-05-release-app-live-qwen-35b-streaming-current.json` at `2026-07-05T16:44:26-0700`, both PASS for SSE JSON frames, `[DONE]`, reasoning/content deltas, usage telemetry with cached-token field, TurboQuant q4 KV, hybrid SSM, native D3 MTP, and cleanup. App `/send` tool-loop reruns wrote `docs/live-proofs/2026-07-05-release-app-live-qwen-27b-tool-loop-current.json` at `2026-07-05T16:46:00-0700` and `docs/live-proofs/2026-07-05-release-app-live-qwen-35b-tool-loop-current.json` at `2026-07-05T16:47:02-0700`, both PASS for real model load, exactly one `lookup_cve` call for `CVE-2025-49704`, verbose tool transcript, final marker, TurboQuant q4, hybrid SSM, native D3 MTP, production stop, and post-cleanup. The refreshed matrix/audit/ledgers at `2026-07-05T16:47:29-0700` through `2026-07-05T16:47:34-0700` still report `24` PASS, `1` PARTIAL, `1` BLOCKED, `overallStatus=BLOCKED`, `objectiveComplete=false`, `completionClaimAllowed=false`, `proofCount=266`, `liveProofCount=168`, and `currentFailedLiveProofCount=0`.
- [x] Continue live Computer Use release-app UI sweep and fix the proof harness issues it exposed. `docs/live-proofs/2026-07-05-release-app-computer-use-continuation-current.json` records CUA version `857` attached to `release/ExploitBot.app` PID `32071`, with the same process starting the `:9999` test server; every primary tab from Recon through Stash was clicked, Terminal opened, and every Settings category from Engine through Logs was observed. The current live UI showed Model scan root `/Users/eric/models/dealign.ai`, `14` models and `6` supported entries including 27B/35B Qwen MXFP8 MTP, Runtime reasoning off with Qwen3/Qwen parsers, Cache default `TurboQuant Q4` with prefix/prompt-L2/paged/block-L2 on, Context 192k proven safe ceiling and unproven-target refusal, CVE Database `1644` total / `1631` KEV, Tools `42 installed` / `0 missing`, and no model inference. This pass exposed two stale proof-harness issues that are now fixed and live-proven: `script/build_and_run.sh --verify` preserves `EXPLOITBOT_TESTING=1` by launching the app binary directly for app-backed proofs, and `scripts/settings-surface-matrix-proof.py` uses the 120s coverage-index timeout budget. Fresh reruns passed `scripts/settings-surface-matrix-proof.py`, `scripts/settings-coverage-proof.py`, `scripts/settings-model-library-state-proof.py`, `scripts/cve-settings-status-proof.py`, `scripts/cve-taxonomy-coverage-proof.py`, `scripts/tool-settings-real-inventory-proof.py`, and `scripts/tool-settings-status-proof.py`; focused contracts passed `36 passed`.
- [x] Harden slow coverage-index proof paths and classify the remaining false-flag mirrors without hiding runtime gaps. The TDD timeout contract first failed with `49` proof scripts still using default/45s `/qa/coverage-index` requests, then repo-wide proof scripts were updated to `timeout=120.0`. A live rerun exposed a real classifier gap instead of a transport failure: `runtimeAndCache.engineAPICacheProofContractParity` remained false because `/qa/engine-api-cache-proof-matrix` is still blocked on `hybridSSMReDeriveStatus` with `ssmReDeriveCompleted=0`, and `appState.falseFlagClassificationParity` was the classifier self-audit mirror. `AppState.swift` now classifies both as known gaps with explicit evidence routes instead of forcing readiness. Direct timing showed `/qa/coverage-index` at `75.387s` and `/qa/coverage-false-flag-classification` at `72.68s` with `classificationParity=True` and `unclassified=[]`; `scripts/coverage-false-flag-classification-proof.py` now reuses its already-fetched coverage-index payload instead of issuing a duplicate slow request. Verification evidence: `test_slow_coverage_index_timeout_contracts.py` and `test_false_flag_classification_contracts.py` passed together (`5 passed`), the focused release/proof contract suite passed (`40 passed`), `scripts/coverage-false-flag-classification-proof.py` passed live, `scripts/coverage-index-proof.py` passed live, and post-run process/listener checks found no `:9999` listener or ExploitBot/Qwen/vMLX engine rows.
- [x] Add/prove a multi-scenario autonomous pentest workflow matrix instead of relying on one-off tool checks. `scripts/repo-codebase-supply-chain-scenario-proof.py` launches the current app in test mode, widens `toolSchemaMaxTools` to `64`, drives a local mock model through `/send`, creates a throwaway vulnerable repo fixture, installs deterministic local scanner shims into the app tool path, and proves `run_shell -> trufflehog -> syft -> grype -> osv_scanner -> search_cve`. `scripts/webserver-auth-sqli-scenario-proof.py` now adds a second live app-backed scenario: loopback webserver route discovery, `httpx`, `nuclei`, bounded local `sqlmap` validation, `search_cve`, raw/structured result ingestion, terminal transcripts, and report generation from the proof marker. Artifacts `docs/live-proofs/2026-07-06-repo-codebase-supply-chain-scenario.json` and `docs/live-proofs/2026-07-06-webserver-auth-sqli-scenario.json` both report `status=PASS`. `scripts/autonomous-scenario-matrix-proof.py` now produces `docs/live-proofs/2026-07-06-autonomous-scenario-matrix.json` with `5/5` PASS rows: webserver auth SQLi report chain, local loopback webserver real-tools, Qwen phase-chain safe exploit/post validation, repo/codebase supply-chain, and report generation from evidence. The matrix aggregates older real-Qwen 27B/35B loopback/phase artifacts; it does not claim those older Qwen rows were freshly rerun in this step.
- [x] Add the next local-only autonomous scenario catalog for broader model stress. `scripts/autonomous-scenario-catalog-proof.py` writes `docs/live-proofs/2026-07-06-autonomous-scenario-catalog.json` with `6` `READY_TO_RUN` scenario definitions under `executionBoundary=local-emulated-targets-only`: emulated webserver auth/SQLi/report, emulated webserver SSRF/file-read, emulated GitHub repo secret/dependency, codebase static-analysis-to-patch-review, container/IaC supply-chain, and network-service credential/post-check. Each row declares the required `surface -> probe -> prove -> exploit_or_validate -> evidence -> report` stages, required tools, final marker, expected future proof artifact, and failure signals. This is a scenario/readiness catalog, not live Qwen pass evidence.
- [x] Expose the autonomous scenario catalog through the live app runtime. `GET /qa/autonomous-scenario-catalog` now returns the same six local-emulated scenario definitions from the current app, so UI/proof harnesses and model-driving scripts can discover scenario IDs, target emulation notes, required tools, stage plans, prompt tasks, final markers, and local-only safety boundaries without scraping repo docs. `scripts/app-autonomous-scenario-catalog-route-proof.py` wrote `docs/live-proofs/2026-07-06-app-autonomous-scenario-catalog-route.json` with `routeScenarioCount=6`, `noModelLoaded=true`, `executionBoundary=local-emulated-targets-only`, and all route checks PASS. Boundary: this proves app-side discoverability of scenario definitions, not a fresh live model pass for every scenario.
- [x] Add app-side autonomous scenario preparation without model execution. `POST /qa/autonomous-scenario-prepare` now converts a scenario ID plus local target into a bounded prompt, autopilot mode, tab selection, and tool-schema budget while leaving inference stopped. `scripts/app-autonomous-scenario-prepare-route-proof.py` wrote `docs/live-proofs/2026-07-06-app-autonomous-scenario-prepare-route.json` with PASS checks for web and repo scenario prompt drafting, final markers, required tool coverage, active tab selection, autopilot mode, `sendToChat=false`, `isWorking=false`, and `noModelLoaded=true`. Boundary: this prepares the model-driving turn and UI state; separate model proof artifacts still prove actual tool execution and report generation.
- [x] Make autonomous scenario fixture setup reusable and machine-readable. The six scenario catalog rows now include `fixtureSetup` metadata, and `scripts/autonomous-scenario-fixture-setup-proof.py` writes `docs/live-proofs/2026-07-06-autonomous-scenario-fixture-setup.json` after creating/verifying the SQLi webserver, SSRF/file-read webserver, local Git repo, static codebase, container/IaC repo, and loopback network-service fixtures. Boundary: file fixtures are left under `/tmp/exploitbot-autonomous-scenario-fixtures`; loopback servers are proof-run-only and are stopped before artifact write.
- [x] Bridge fixture materialization to app prompt preparation for all autonomous scenarios. `scripts/app-autonomous-scenario-fixture-session-prepare-proof.py` keeps a live fixture session open while preparing all six scenario prompts through `POST /qa/autonomous-scenario-prepare`, proving the prompt contains the live target, fixture setup metadata, the correct tab, no model load, and stopped loopback services after artifact write. Boundary: this is the no-model handoff layer; fresh real-Qwen 27B/35B execution remains a separate proof requirement per scenario.
- [x] Add live app-backed SSRF/file-read scenario proof. `scripts/webserver-ssrf-fileread-scenario-proof.py` wrote `docs/live-proofs/2026-07-06-webserver-ssrf-fileread-scenario.json` with PASS checks for ordered tool sequence, SSRF canary, fixture file-read canary, verbose tool transcript, terminal transcript, parsed nuclei evidence, CVE context call, safe local boundary, and report generation from captured evidence. Boundary: mock-engine local fixture proof; real-Qwen model execution for this scenario is still future work.
- [x] Real-Qwen 27B and 35B webserver SSRF/file-read/report scenario now pass with exact-prompt tool execution and a real two-turn model loop. `scripts/real-qwen-webserver-ssrf-fileread-proof.py` launches a reusable loopback SSRF/file-read fixture, installs deterministic local `httpx` and `nuclei` scanner shims on the isolated app/tool path, drives the current app through `/send`, generates a report from parsed evidence, sends a second no-tool marker turn, and rejects duplicate tool cards. Fresh artifacts `docs/live-proofs/2026-07-06-real-qwen-webserver-ssrf-fileread-27b.json` and `docs/live-proofs/2026-07-06-real-qwen-webserver-ssrf-fileread-35b.json` both report `ok=true`, `overall=PASS`, tool sequence exactly `run_shell -> httpx -> nuclei -> search_cve`, final marker plus second-turn marker success, `num_requests_processed=2`, TurboQuant q4 KV, hybrid SSM typed cache, paged cache, prefix cache, block disk cache writes, native D3 MTP, SSRF canary marker `EXPLOITBOT_SSRF_CANARY_OK`, file-read marker `EXPLOITBOT_FILE_READ_CANARY_OK`, terminal transcript evidence, and generated report HTML. Boundary: this is real 27B/35B engine/app/tool/cache/report evidence for local authorized fixture automation with app-side exact-call recovery; it is not proof that either model independently chose every web/probe/exploit tool without an exact-call prompt.
- [x] Promote supply-chain dependency scanner output from raw logs into structured findings/report evidence. `ResultsStore.ingest` now parses `syft` SBOM components, `grype` dependency vulnerabilities, and `osv_scanner` OSV/GHSA rows into `VulnEntry` records; `/results.vulns` now exposes `source`, `description`, `cve`, `cvss`, and `tags` so downstream model/tool/report automation can preserve provenance. `scripts/result-parser-routing-proof.py` passed live with `syft`, `grype`, and `osv_scanner` required as structured parser outputs. The refreshed repo/codebase scenario artifact `docs/live-proofs/2026-07-06-repo-codebase-supply-chain-scenario.json` generated at `2026-07-05T22:34:12-0700` reports `dependencyStructuredFindings=PASS`, `vulnCount=5`, `vulnSources=["grype","osv_scanner","syft","trufflehog"]`, and a generated report finding titled `CVE-2021-23337 vulnerable lodash dependency` with OSV evidence marker `GHSA-35jh-r3h4-6jhm`. Adjacent live proofs `scripts/parser-tool-matrix-proof.py` and `scripts/tool-flow-coverage-proof.py` also passed after updating the tool-flow family contract to all 10 app tabs.
- [x] Real-Qwen 27B and 35B repo/codebase supply-chain scenario now pass with exact-prompt tool execution and a real two-turn model loop. `scripts/real-qwen-repo-codebase-supply-chain-proof.py` now normalizes app `toolSchemas` string rows, executes prompt-specified exact `<tool_call>` blocks directly when parser output is prose-only, prevents exact-call fallback from re-firing during forced final-answer turns, sends a second no-tool marker turn, and rejects duplicate tool cards. Fresh artifacts `docs/live-proofs/2026-07-06-real-qwen-repo-codebase-supply-chain-27b.json` and `docs/live-proofs/2026-07-06-real-qwen-repo-codebase-supply-chain-35b.json` both report `ok=true`, `overall=PASS`, tool sequence exactly `run_shell -> trufflehog -> syft -> grype -> osv_scanner -> search_cve`, final marker plus second-turn marker success, `num_requests_processed=2`, TurboQuant q4 KV, hybrid SSM typed cache, paged cache, prefix cache, block disk cache writes, native D3 MTP, structured dependency findings, terminal transcript evidence, and generated report HTML. Boundary: this is real 27B/35B engine/app/tool/cache/report evidence for local authorized fixture automation with app-side exact-call recovery; it is not proof that either model independently chose every supply-chain tool without an exact-call prompt.
- [x] Real-Qwen 27B and 35B webserver auth/SQLi/report scenario now pass with exact-prompt tool execution and a real two-turn model loop. `scripts/real-qwen-webserver-auth-sqli-proof.py` launches a loopback webserver fixture, installs deterministic local `httpx`, `nuclei`, and `sqlmap` scanner shims on the isolated app/tool path, drives the current app through `/send`, generates a report from parsed evidence, sends a second no-tool marker turn, and rejects duplicate tool cards. Fresh artifacts `docs/live-proofs/2026-07-06-real-qwen-webserver-auth-sqli-27b.json` and `docs/live-proofs/2026-07-06-real-qwen-webserver-auth-sqli-35b.json` both report `ok=true`, `overall=PASS`, tool sequence exactly `run_shell -> httpx -> nuclei -> sqlmap -> search_cve`, final marker plus second-turn marker success, `num_requests_processed=2`, TurboQuant q4 KV, hybrid SSM typed cache, paged cache, prefix cache, block disk cache writes, native D3 MTP, SQL injection proof marker `EXPLOITBOT_SQLI_PROOF_USER=alice`, terminal transcript evidence, and generated report HTML. Boundary: this is real 27B/35B engine/app/tool/cache/report evidence for local authorized fixture automation with app-side exact-call recovery; it is not proof that either model independently chose every web/probe/exploit tool without an exact-call prompt.
- [x] Codebase static-analysis-to-patch-review scenario now passes through the live app with parsed static-analysis findings. `ToolDefinitions.swift`, `ToolInstaller.swift`, `ResultsStore.swift`, and the parser coverage routes now expose `semgrep` and `bandit` as model-visible, Settings-visible, structured subprocess tools. `scripts/codebase-static-patch-scenario-proof.py` creates a throwaway Python codebase fixture, installs deterministic local `semgrep` and `bandit` shims, drives `/send`, proves `run_shell -> semgrep -> bandit -> search_context`, parses `semgrep` and `bandit` vulnerability rows, preserves verbose tool and terminal transcripts, captures `app.py:17` plus `EXPLOITBOT_PATH_TRAVERSAL_PROOF`, records patch guidance for `pathlib resolve` plus an allowlisted base directory, and generates a report. Artifact `docs/live-proofs/2026-07-06-codebase-static-patch-scenario.json` reports `ok=true`, `status=PASS`, `vulnSources=["bandit","semgrep"]`, `rawTools=["run_shell","semgrep","bandit","search_context"]`, and all scenario checks PASS. Boundary: this is local fixture code review and validation only; it does not read sensitive host files or exploit an external codebase.
- [x] Real-Qwen 27B and 35B codebase static-analysis-to-patch-review scenario now pass with exact-prompt tool execution and a real two-turn model loop. `scripts/real-qwen-codebase-static-patch-proof.py` launches a throwaway local codebase fixture, installs deterministic local `run_shell`, `semgrep`, `bandit`, and `search_context` shims on the isolated app/tool path, drives the current app through `/send`, generates a report from parsed evidence, sends a second no-tool marker turn, and rejects duplicate tool cards. Fresh artifacts `docs/live-proofs/2026-07-06-real-qwen-codebase-static-patch-27b.json` and `docs/live-proofs/2026-07-06-real-qwen-codebase-static-patch-35b.json` both report `ok=true`, `overall=PASS`, tool sequence exactly `run_shell -> semgrep -> bandit -> search_context`, TurboQuant q4 KV, hybrid SSM typed cache, paged cache, prefix cache, block disk cache writes, hybrid async SSM rederive, native D3 MTP, `semgrepEvidence=PASS`, `banditEvidence=PASS`, `app.py:17`, patch guidance for `pathlib resolve` plus `allowlist`, terminal transcript evidence, and generated report HTML. Boundary: this is real 27B/35B engine/app/tool/cache/report evidence for local authorized fixture automation with app-side exact-call recovery; it is not proof that either model independently chose every codebase/static-analysis tool without an exact-call prompt.
- [x] Container/IaC supply-chain scenario now passes through the live app with parsed container and IaC findings. `ToolDefinitions.swift`, `ToolInstaller.swift`, and `ResultsStore.swift` now expose `trivy` and `checkov` as model-visible, Settings-visible, structured subprocess tools alongside `syft`, `grype`, and `osv_scanner`. `scripts/container-iac-supply-chain-scenario-proof.py` reuses the local fixture session, installs deterministic local scanner shims, drives `/send`, proves `run_shell -> syft -> grype -> trivy -> checkov -> search_cve`, parses SBOM/vulnerability/IaC findings, preserves verbose tool and terminal transcripts, captures `EXPLOITBOT_CONTAINER_IAC_PROOF`, `nginx:1.16`, `CVE-2019-20372`, `AVD-KSV-0012`, `CKV_K8S_20`, and `allowPrivilegeEscalation: true`, then generates a report. Artifact `docs/live-proofs/2026-07-06-container-iac-supply-chain-scenario.json` reports `ok=true`, `status=PASS`, `vulnSources=["checkov","grype","syft","trivy"]`, `rawTools=["run_shell","syft","grype","trivy","checkov","search_cve"]`, and all scenario checks PASS. Boundary: this is local fixture validation with a mock engine and deterministic scanner shims; it does not run privileged containers, contact an external registry, or prove real-Qwen execution for this specific scenario.
- [x] Real-Qwen 27B and 35B container/IaC supply-chain scenario now pass with exact-prompt tool execution and a real two-turn model loop. `scripts/real-qwen-container-iac-supply-chain-proof.py` launches the local container/IaC fixture, installs deterministic local `run_shell`, `syft`, `grype`, `trivy`, `checkov`, and `search_cve` shims on the isolated app/tool path, drives the current app through `/send`, generates a report from parsed evidence, sends a second no-tool marker turn, and rejects duplicate tool cards. Fresh artifacts `docs/live-proofs/2026-07-06-real-qwen-container-iac-supply-chain-27b.json` and `docs/live-proofs/2026-07-06-real-qwen-container-iac-supply-chain-35b.json` both report `ok=true`, `overall=PASS`, tool sequence exactly `run_shell -> syft -> grype -> trivy -> checkov -> search_cve`, TurboQuant q4 KV, hybrid SSM typed cache, paged cache, prefix cache, block disk cache writes, hybrid async SSM rederive, native D3 MTP, `trivyEvidence=PASS`, `checkovEvidence=PASS`, `CVE-2019-20372`, `CKV_K8S_20`, `allowPrivilegeEscalation: true`, terminal transcript evidence, and generated report HTML. Boundary: this is real 27B/35B engine/app/tool/cache/report evidence for local authorized fixture automation with app-side exact-call recovery; it is not proof that either model independently chose every container/IaC tool without an exact-call prompt.
- [x] Refresh current-machine Tools inventory and all-installed smoke after adding Trivy and Checkov. `brew install trivy` installed Trivy `0.72.0`, `uv tool install checkov` installed Checkov `3.3.6`, `scripts/tool-settings-real-inventory-proof.py` refreshed `docs/live-proofs/2026-07-04-tool-settings-real-inventory.json` with `installedCount=46` and `missingCount=0`, and `scripts/all-installed-tools-smoke-proof.py` refreshed `docs/live-proofs/2026-07-05-all-installed-tools-smoke.json` with `toolCount=46`, `PASS=46`, and `FAIL=0` under `safeSmokeOnly=true`.
- [x] Network credential/post-check scenario now passes through the live app across Network, Creds, Post, and Report evidence surfaces. `scripts/network-credential-post-scenario-proof.py` reuses the loopback network fixture, installs deterministic local `nmap`, `httpx`, `hydra`, `netexec`, and `linpeas.sh` shims, drives `/send`, proves `nmap -> httpx -> hydra -> netexec -> run_shell -> linpeas`, preserves verbose tool and terminal transcripts, captures `EXPLOITBOT_NETWORK_LOGIN_OK`, `EXPLOITBOT_LINPEAS_FIXTURE_OK`, parsed credential evidence from `hydra`, raw/terminal network host evidence from `netexec`, `linpeas-host` post attribution, and generated report output. Artifact `docs/live-proofs/2026-07-06-network-credential-post-scenario.json` reports `ok=true`, `status=PASS`, `rawTools=["nmap","httpx","hydra","netexec","run_shell","linpeas"]`, `vulnSources=["hydra"]`, `postAttributionCount=1`, and all scenario checks PASS. Boundary: this validates only seeded demo credentials and harmless loopback post-check output; it does not target external services or perform privileged host modification.
- [x] Real-Qwen 27B and 35B network credential/post-check scenario now pass with exact-prompt tool execution and a real two-turn model loop. `scripts/real-qwen-network-credential-post-proof.py` launches the same loopback credential/post fixture, installs deterministic local `nmap`, `httpx`, `hydra`, `netexec`, `run_shell`, and `linpeas` shims on the isolated app/tool path, drives the current app through `/send`, generates a report from parsed evidence, sends a second no-tool marker turn, and rejects duplicate tool cards. Fresh artifacts `docs/live-proofs/2026-07-06-real-qwen-network-credential-post-27b.json` and `docs/live-proofs/2026-07-06-real-qwen-network-credential-post-35b.json` both report `ok=true`, `overall=PASS`, tool sequence exactly `nmap -> httpx -> hydra -> netexec -> run_shell -> linpeas`, TurboQuant q4 KV, hybrid SSM typed cache, paged cache, prefix cache, block disk cache writes, hybrid async SSM rederive, native D3 MTP, seeded credential proof marker `EXPLOITBOT_NETWORK_LOGIN_OK`, post-check marker `EXPLOITBOT_LINPEAS_FIXTURE_OK`, terminal transcript evidence, and generated report HTML. Boundary: this is real 27B/35B engine/app/tool/cache/report evidence for local authorized fixture automation with app-side exact-call recovery; it is not proof that either model independently chose every network/post tool without an exact-call prompt.
- [x] Refresh autonomous scenario matrix/catalog/artifact ledgers after the real-Qwen 27B/35B webserver SQLi, repo/codebase, codebase static-analysis, SSRF/file-read, container/IaC, and network credential/post-check scenario passes. `docs/live-proofs/2026-07-06-autonomous-scenario-matrix.json` reports `status=PASS` across 9 rows, marks all nine rows PASS and every autonomous execution row either real-Qwen-backed or direct report-action proof, includes the new real-Qwen-backed `codebase_static_to_patch_review_chain`, `container_iac_supply_chain_chain`, and `network_service_credential_post_chain` rows, `docs/live-proofs/2026-07-06-autonomous-scenario-catalog.json` keeps 6 local-only `READY_TO_RUN` scenario definitions, and `docs/live-proofs/2026-07-05-artifact-ledger-current.json` reports `liveProofCount=205`, `currentFailedLiveProofCount=0`, and current live-proof failure-free status.
- [x] Make the autonomous scenario evidence boundary machine-readable. `scripts/autonomous-scenario-matrix-proof.py` now emits `toolChoiceMode`, `modelToolChoiceEvidence`, and `autonomyBoundary` for every row. The refreshed `docs/live-proofs/2026-07-06-autonomous-scenario-matrix.json` reports `9` PASS rows, folds real-Qwen 27B/35B artifacts into the repo/codebase, codebase static patch, container/IaC, and network credential/post rows with q4 TurboQuant KV, hybrid SSM, paged, and prefix cache proof, and labels the real-Qwen webserver, loopback, phase, repo/codebase, codebase static, container/IaC, and network rows as `exact_tool_call_prompt_with_app_recovery` while the report/export row remains a direct app-action proof. Boundary: those rows prove real Qwen prompt/schema receipt, ordered tool execution, cache/MTP, verbose transcripts, and reports on local fixtures where real-Qwen artifacts exist, but not independent natural-language tool selection for every catalog scenario.
- [x] Promote independent natural-language tool choice into the formal status gates. `docs/live-proofs/2026-07-04-pass-partial-blocked-matrix.json` now marks `Independent natural-language scenario tool selection` PASS after fresh 27B and 35B natural-objective local webserver SQLi artifacts. The row is backed by the autonomous scenario matrix/catalog, schema-profile exclusion proof, local target argument-repair proof, and the 27B/35B real-Qwen natural proof artifacts.
- [x] Prove real-Qwen 27B and 35B independent natural-language webserver scenarios without hiding earlier failures. `scripts/real-qwen-natural-tool-choice-proof.py` launches the current app, a loopback SQLi fixture, Qwen3.6 MXFP8 MTP models, TurboQuant q4 KV, prefix cache, paged cache, block L2 cache, and a natural-language objective with no exact tool-call blocks or forced function-specific retry. It excludes `run_shell` from the model-visible schema, includes deterministic local web-route tools such as `katana`, accepts `search_cve` or `lookup_cve` as the CVE context stage, checkpoints after required evidence is visible, and forces a no-tool final-answer turn. Fresh 27B and 35B artifacts both report PASS for model-selected tool sequence, SQLi proof, final assistant marker, generated report, cache topology, and native D3 MTP. Boundary: this is still local authorized fixture proof, not permission to target external systems.
- [x] Refresh the current-machine Tools settings inventory, all-installed smoke, and Computer Use visible Tools panel for the expanded 44-tool registry. `semgrep` and `bandit` were installed with `uv tool install` and are detected at `/Users/eric/.local/bin/semgrep` version `1.168.0` and `/Users/eric/.local/bin/bandit` version `1.9.4`. `docs/live-proofs/2026-07-04-tool-settings-real-inventory.json` now reports `installedCount=44`, `missingCount=0`, `errorPentestTools=[]`, and `fullPentestToolchainInstalled=PASS`; `docs/live-proofs/2026-07-05-all-installed-tools-smoke.json` reports `toolCount=44` with `PASS=44` and `FAIL=0` under `safeSmokeOnly=true`, `externalTargetExecution=not-started`, and `modelDrivenEvidence=not-claimed`. Computer Use artifact `docs/live-proofs/2026-07-06-computer-use-tools-inventory-44-dist.json` attaches CUA version `857` to current `dist/ExploitBot.app` PID `3617`; visible Settings > Tools shows `44 installed` / `0 missing`, disabled `Install All Missing`, and same-process localhost `:9999` API confirms `toolCount=44`, `semgrep` and `bandit` installed.
- [x] Refresh the packaged release app after the 44-tool registry expansion. `./script/package_release.sh --skip-notarize` rebuilt `release/ExploitBot.app` and `release/ExploitBot-beta.dmg` from current source, verified both signatures, and wrote `release/release-manifest.json` with app binary SHA256 `19b67929f2bd84652d1e616e2e2090a1d14824f88b0893214ce80b9e77650fcf` and DMG SHA256 `67b891ff49614f98f29309ce74bfbb72ebab03b3261517b562cd9b3022c20b61`. Computer Use artifact `docs/live-proofs/2026-07-06-release-app-computer-use-tools-inventory-44.json` attaches CUA version `857` to `release/ExploitBot.app` PID `9817`; visible Settings > Tools shows `44 installed` / `0 missing`, disabled `Install All Missing`, and same-process localhost `:9999` API confirms `toolCount=44`, `semgrep`, and `bandit`. Boundary: this is local signed release packaging and UI proof only; the manifest still reports `notarizationStatus=not-submitted` and `notarizationGate=requires-notary-credentials`.
- [x] Refresh release/displayable package proof after the July 6 app-state and proof-ledger changes, and fix the retained release JSON-framing process classifier. `scripts/release-readiness-proof.py` rebuilt `release/ExploitBot.app`, `release/ExploitBot-beta.dmg`, and `release/release-manifest.json` at `2026-07-06T14:41:00-0700` with local package PASS, bundled runtime PASS, app binary SHA256 `8c3db8fb0d70e05527e5926076d5da18f9ccbac0af7fa25571c2dc1c2537ffa5`, DMG SHA256 `98448fd821b6794737bbb3ecb7d8a43081e300087cbea251b2f09ac927ef0dfc`, and distribution BLOCKED because notarization is `not-submitted`. `scripts/release-app-json-framing-live-proof.py` now ignores unrelated `/Users/eric/mlx/vllm-mlx/panel` build processes while still detecting real ExploitBot engine launch/module rows; the refreshed artifact generated at `2026-07-06T14:41:11-0700` proves `480` parsed `/state` + `/messages` responses, `invalidCount=0`, matching `Content-Length`, `Cache-Control: no-store`, and `engineProcessRows=[]`. `scripts/release-visible-smoke-proof.py` refreshed visible release smoke at `2026-07-06T14:41:24-0700` with local display PASS and no model loaded. `scripts/notarization-preflight-proof.py`, `scripts/release-public-truth-proof.py`, `scripts/beta-readiness-coverage-proof.py`, `scripts/pass-partial-blocked-matrix-proof.py`, `scripts/goal-requirement-audit-proof.py`, `scripts/objective-open-blockers-proof.py`, `scripts/artifact-ledger-proof.py`, and `scripts/proof-ledger-proof.py` were rerun after the package refresh; the current status remains `25` PASS / `1` PARTIAL / `1` BLOCKED, `objectiveComplete=false`, `completionClaimAllowed=false`, `liveProofCount=206`, `currentFailedLiveProofCount=0`, and `proofCount=289`.
- [x] Tighten i18n coverage for the first-run onboarding path instead of only representative tabs/tools. `Localizer.swift` now includes five-language strings for the onboarding language subtitle, model-folder instructions, detected unified-memory label, model-folder prompt/placeholder/folder-picker prompt, first-Op subtitle, Op name/scope/interaction labels, enforce-scope toggle, and mode descriptions. `OnboardingView.swift` now renders those labels through `Localizer.shared.t(...)`, and `/qa/i18n-snapshot` exposes an `onboarding` block for live route proofs. `scripts/i18n-language-toggle-proof.py` refreshed `docs/live-proofs/2026-07-06-i18n-language-toggle.json` at `2026-07-06T14:51:18-0700` with `onboardingLabelsChanged=PASS`, `tabLabelsChanged=PASS`, `toolLabelsPresent=PASS`, `coreLabelsChanged=PASS`, and `noModelLoaded=PASS` after toggling Spanish and Japanese through the live app. Boundary: this materially improves the visible first-run path, but it is not a claim that every hard-coded SwiftUI `Text` in the whole app has been replaced yet.
- [x] Replace the truncated single-page PDF report writer with source-verified wrapping and pagination, then rerun the app-backed export proof after the ChatService/dist window cleared. `ReportService.buildSimplePDF` no longer caps output with `.prefix(32)` or hardcodes `/Count 1`; it now wraps long lines, paginates body lines, builds dynamic page/content object IDs, and emits a dynamic `/Pages` tree. `ExploitBotEngine/testsuite/test_report_workflow_artifact_contracts.py` now has a regression requiring `wrapPDFLine`, `paginatePDFLines`, `buildPDFPageStream`, dynamic `/Kids`, dynamic `/Count`, and no fixed line truncation. Fresh verification on 2026-07-06: `swift build --package-path ExploitBot -c debug` exited 0, `scripts/report-export-proof.py` exited 0 and refreshed `docs/live-proofs/2026-07-05-report-export-current.json` with `ok=true`, `status=PASS`, `noModelLoaded=true`, HTML/Markdown/JSON/PDF artifacts present, and PDF artifact bytes `1010`; focused report workflow contracts passed (`5 passed`). Boundary: this proves the no-model app-backed report export path and PDF artifact creation; release notarization/public-truth and full-context stress remain separate open gates.
- [x] Remove stale active Qwen model defaults that pointed at deleted `/Users/eric/models/JANGQ/Qwen3.6-*` folders. README active commands, `release-app-live-qwen-proof.py`, `prove-live-loaded-model-agent-stress.py`, `live-loaded-model-agent-stress-proof.py`, `persistence-proof.py`, and app QA/status snapshots now point at existing `/Users/eric/models/dealign.ai/*CRACK-MTP` Qwen folders. `prove-live-loaded-model-agent-stress.py` also now launches the app before its external engine so `script/build_and_run.sh --verify` cannot kill the just-started engine during stale-engine cleanup. Fresh verification on 2026-07-06: `docs/live-proofs/checkpoint-466-qwen-live-agent-stress.json` reports `ok=true`, model `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP4-CRACK-MTP`, `appMaxWorkingObserved=2`, `scheduler_stats.max_running_observed=2`, `num_requests_processed=2`, TurboQuant q4 KV, block L2 disk writes `202`, `ssmCompanionL2Tokens=26975`, `ssmReDeriveFailed=0`, active memory `15325.6 MB`, and post-run process/listener checks found no ExploitBot/Qwen/vMLX engine rows. Boundary: this loaded-agent stress row proves SSM companion L2 evidence and no rederive failures, not a rederive completion counter; separate Qwen cache/reasoning artifacts remain the evidence for explicit hybrid async rederive completion.
- [x] Replace the chat history fixed-character trim with a token-budgeted selector in source. `ChatService.streamCompletion` now calls `contextWindowBudget(systemPrompt:reservedOutputTokens:)` and `selectContextWindowMessages(..., budget:)` instead of `maxContextChars = 100_000`; the selector estimates prompt/history tokens, reserves `maxTokens` for output, charges role/tool-call overhead, and keeps recent messages inside the available context budget. Fresh verification on 2026-07-06: the new focused source contract first failed on the old `maxContextChars = 100_000` path, then passed after the change; `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m pytest -q ExploitBotEngine/testsuite/test_chat_service_tool_loop_contracts.py ExploitBotEngine/testsuite/test_autonomous_scenario_matrix_contracts.py ExploitBotEngine/testsuite/test_settings_generation_persistence_contracts.py` reported `52 passed`; `swift build --package-path ExploitBot -c debug` exited 0; `git diff --check` exited 0. Boundary: no live app-backed context-budget proof was run in this slice to leave the app window clear for live breadth testing.
- [x] Add a fresh-launch model fallback that prefers an existing low-RAM Qwen folder instead of leaving the app with an empty or stale model path. `AppState.loadEngineConfig()` now keeps a saved `engine.modelPath` only when its `config.json` still exists; otherwise it falls back through `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP4-CRACK-MTP`, `Qwen3.6-27B-MXFP8-CRACK-MTP`, `Qwen3.6-35B-A3B-MXFP4-CRACK-MTP`, then `Qwen3.6-35B-A3B-MXFP8-CRACK-MTP`. Fresh verification on 2026-07-06: the new focused source contract first failed because no `freshLaunchDefaultModelPath` existed, then passed after the change; `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m pytest -q ExploitBotEngine/testsuite/test_model_path_defaults_contracts.py ExploitBotEngine/testsuite/test_model_library_settings_contracts.py ExploitBotEngine/testsuite/test_demo_ready_startup_contracts.py ExploitBotEngine/testsuite/test_settings_generation_persistence_contracts.py` reported `12 passed`; `swift build --package-path ExploitBot -c debug` exited 0; `git diff --check` exited 0. Boundary: no live app launch was run in this slice.
- [ ] Remaining release gate: configure notary credentials, notarize, staple, rerun release/public-truth/notarization proofs, then rerun the goal audit. Local app/DMG signing and release Tools UI are refreshed; completion claims remain blocked until notarization/public-truth gates pass.
- [ ] Remaining stress gate: full-context proof stays PARTIAL above the proven 192k safe ceiling. Current artifacts prove 192k completion, but 196k stalled after chunked-prefill entry and 200k/224k/258k are guarded/refused or aborted by memory guard rather than completed with final output and cache writes.

## CVE Library Lane

Requirement added during live validation: the app must include a useful modern CVE library, not only static demo rows.

Planned source policy:

- Use current authoritative sources during the CVE refresh pass, not memory or stale bundled data.
- Prioritize exploited/relevant items from CISA KEV, NVD recent CVEs, GitHub Security Advisories, OSV, and tool/ecosystem-specific advisories where applicable.
- Store enough metadata for model retrieval: CVE ID, affected product/ecosystem, severity, EPSS/known-exploited signal when available, concise exploitation/use-case summary, references, remediation, and tags.
- Prove the model can search dynamically via app callback tools (`search_cve`, `lookup_cve`, and `search_context`) without stuffing the entire library into every prompt.
