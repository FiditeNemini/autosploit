# ExploitBot System Review Matrix - 2026-05-21

## Purpose

This is the current whole-app review ledger for the beta refresh. It tracks how
each page/tool/function is wired, what context reaches the model, what UI state
must be visible, and what test evidence is required before the app can be called
fully agentic.

## Runtime And Chat Backbone

Engine startup:

- `SettingsView` writes `EngineConfig` and calls `AppState.startEngine()`.
- `EngineManager.start(config:)` launches the Python vMLX engine and polls
  `/health`.
- `AppState.startEngine()` copies the engine URL/model name into main chat and
  active agents.
- Required proof: real Qwen and MiniMax model-folder load, `/health` effective
  parser/generation/cache metadata, one streamed response, and one stopped
  response.

Chat streaming:

- `ChatPanelView.sendMessage()` calls `ChatService.send(...)`.
- `ChatService.runConversationLoop()` streams, parses reasoning/tool calls,
  executes tool loops, and repeats until no tool calls or `maxIterations`.
- Metrics are populated from streaming usage: token/s, TTFT, prompt tokens,
  completion tokens, cached prompt tokens.
- Reasoning is toggled by `ChatPanelView` and sent as `enable_thinking` plus
  `chat_template_kwargs.enable_thinking`.
- Reasoning UI is `ReasoningBlock`; it expands while streaming and collapses
  after completion unless the user toggled it.
- Scroll lock is now explicit: locked mode follows the latest message, dragging
  pauses auto-scroll, and the "Latest/New output" control relocks to bottom.
- Required proof: stream with reasoning on/off, metrics visible after usage,
  manual scroll pause while output streams, relock jump, stop button cancels the
  stream session.

Interaction modes:

- `SidebarView` and onboarding choose `autopilot`, `copilot`, or `manual`.
- Autopilot executes model tool calls directly.
- Copilot shows an approval card before tool execution.
- Manual converts model tool calls into suggested commands and stops.
- Agents always run as autopilot after deployment.
- Required proof: same mock tool call under all three modes with expected
  execute/approve/suggest behavior.

## Context Flow

Static prompt:

- `ChatService.systemPrompt` provides identity, compact tool categories, phase
  guidance, reasoning mode, and scope rules.
- OpenAI-compatible `tools` now sends a prompt/tab-ranked function schema capped
  at 12 entries by default. Built-in retrieval/CVE/shell callbacks remain
  visible; installed external tool schemas are selected by active lane and
  query terms instead of model-size profiles.

Dynamic context:

- `ChatService.streamCompletion()` asks `onContextUpdate(latestUserPrompt)`.
- `AppState.wireContextCatalog(...)` routes that to `ContextCatalogService`.
- The catalogue ranks active assets, findings, recent raw tool output, stash
  items, and CVE results against the prompt, active tab, current phase, source,
  and severity.
- Settings control max snippets and source inclusion.
- CVE assist mode can be off, current visible results, or semantic embedding
  ranked. Semantic mode uses `CVEService.semanticSearch(...)` and falls back
  through local CVE search behavior when embeddings are unavailable.
- `search_context` is exposed as a model-callable built-in tool. It queries the
  same ranked catalogue on demand with a bounded `max_snippets` limit so the
  model can pull targeted notes/assets/findings/CVEs without forcing all context
  into every prompt.
- Stash retrieval is now query-scored before it enters the dynamic catalogue:
  active-operation and global stash can be considered, inactive-operation stash
  is excluded, labels/tags/content/source tab influence score, and the latest
  retrieval audit is exposed through `/state.stashRetrieval`.
- Automatic context injection is capped to 4 snippets. Settings stores a bounded
  maximum, but routine model turns stay lean and rely on `search_context` for
  deeper retrieval.
- Source controls and operation scoping are covered by
  `scripts/context-catalog-proof.py`: disabled asset/finding/recent-output/stash
  sources stay out of selected snippets, active-op stash and global stash remain
  visible, and inactive-op stash is excluded.
- Targeted stash retrieval is covered by `scripts/stash-retrieval-proof.py`: a
  kerberos/golden-ticket query selects the matching active-op note first, keeps
  unrelated noise out of the bounded context packet, excludes inactive-op stash,
  and exposes candidate/returned/top-score audit state.
- Semantic CVE mode invocation is covered by `scripts/semantic-cve-proof.py`,
  which launches the app with a deterministic fake embedder, seeds tiny stored
  vectors, verifies the embedder subprocess was called, and asserts
  `/state.cveSemantic.usedEmbedding=true` with no fallback.

Storage:

- Ops, messages, settings, stash, findings, and CVEs persist through
  `DatabaseManager`.
- ResultsStore state is rebuilt from restored tool-call messages when operation
  messages load.
- Settings, per-op messages, and result-store rebuild after relaunch are
  covered by `scripts/persistence-proof.py`: it uses an isolated temporary home
  directory, seeds context/chat settings plus a persisted `nmap` tool message,
  relaunches the app, and verifies the restored message reparses into the
  visible `443/https` port result.
- Per-assistant-turn request context/tool-schema audit metadata is persisted in
  the `messages` table and covered by `scripts/request-audit-proof.py`.

## Tool Loop And Result Routing

Tool API:

- `ToolDefinitions.forModel()` exposes 34 tools plus `run_shell`.
- `ToolDefinitions.buildCliArgs(...)` maps parsed model tool calls to CLI
  binaries/arguments.
- Built-ins `search_context`, `search_cve`, and `lookup_cve` route to app
  callbacks instead of subprocesses.
- External tools route through `ToolExecutor.execute(...)`.

Result fanout:

- `ChatService` appends tool cards.
- `onToolStart` logs activity, increments phase tool count, and auto-switches
  tabs through `AppState.tabForTool(...)`.
- `onToolComplete` logs success/failure and duration.
- `onToolResult` feeds `ResultsStore.ingest(...)`.
- `ResultsStore` parses known tool output into tab state and fires auto-CVE
  callbacks for service versions and CVE IDs.
- Required proof: each tool family can produce a visible chat card, activity
  entry, tab result, and context-catalog item from representative output.

## Page And Button Coverage

Recon:

- Buttons: Full Recon, Crawl, OSINT/theHarvester, copy controls.
- Chat path: run buttons record a Recon action state, then send the generated
  prompt to chat.
- State: subdomains, ports, web hosts, crawl URLs from `ResultsStore`, plus
  `/state.reconAction` for the latest Full Recon/Crawl/Harvest action.
- Recon action status is covered by `scripts/recon-action-status-proof.py`: a
  seeded Full Recon records target, generated command, running status, and Recon
  tab activity with `lastTool=full_recon`.
- Visible Full Recon running state is captured under
  `docs/visual-proofs/checkpoint-97`.

Web:

- Buttons: scan target, create finding, stash vuln, verify placeholder, CVE
  details, related CVE search.
- Chat path: scan/related CVE routes through chat; finding/stash are direct app
  state actions.
- Verify now routes through chat with a focused prompt containing target,
  finding title, source, CVE, and description for minimal safe evidence
  collection.
- State: web hosts, vulns, CVE lookup details, and queued Verify action state.
- Verify action state is covered by `scripts/web-verify-action-proof.py`: a
  seeded finding records `/state.webAction`, preserves the exact verification
  prompt, and marks the Web tab activity state as running/verify.
- Visible Verify button progress state is captured under
  `docs/visual-proofs/checkpoint-96`.

Network:

- Buttons: Scan, SMB shares/users/sessions/SAM/LSA/whoami, SNMP Walk, Start
  Capture, Start MITM, Create Tunnel.
- Chat path: Protocol Scan records a Network action state, then sends the
  generated prompt to chat. Other actions send prompts to chat.
- State: network hosts, raw output, `/state.networkAction` for the latest
  protocol scan, and long-running lifecycle state for Capture/MITM/Tunnel.
- Protocol Scan action state is covered by
  `scripts/network-protocol-action-proof.py`: a seeded SMB netexec scan records
  target, protocol, credential context, generated command, running status, and
  Network tab activity with `lastTool=netexec`.
- Visible Protocol Scan running state is captured under
  `docs/visual-proofs/checkpoint-98`.
- Long-running lifecycle state now tracks capture/MITM/tunnel status as idle,
  running, done, failed, or canceled and is visible inside the relevant Network
  subtab.
- Live UI screenshot coverage for Capture, MITM, and Tunnels lifecycle strips
  is captured by `scripts/visual-tab-proof.py`.

Creds:

- Buttons: Start Crack, Brute Force, Scan Secrets.
- Chat path: Start Crack records a Creds action state, then sends the generated
  haiti/hashcat prompt to chat. Brute Force and Scan Secrets send prompts to
  chat.
- State: parsed credential/hash/secret findings, `/state.credsAction` for the
  latest hash-cracking action, and `/results.creds` rows with
  CRACKED/BRUTE/SECRET/CRED badges.
- Hash-cracking action/result state is covered by
  `scripts/creds-action-results-proof.py`: a seeded hashcat result set records
  target, generated haiti/hashcat command, done status, result count, Creds tab
  activity with `lastTool=hashcat`, and CRACKED result badges.
- Visible Start Crack done state and credential result badges are captured under
  `docs/visual-proofs/checkpoint-99`.
- Cracking, brute force, and secret scan lifecycle state now tracks idle,
  running, done, failed, and canceled and is visible in the relevant Creds
  subtab.
- Live UI screenshot coverage for Cracking, Online Brute, and Secrets lifecycle
  strips is captured by `scripts/visual-tab-proof.py`.

Exploit:

- Buttons: Search, Start Listener, Run Script, Generate Implant, Sliver listener.
- Chat path: Search records an Exploit action state, then sends the generated
  prompt to chat. Prepare/execute status is represented as separate action
  stages; listener/script/implant buttons send prompts to chat.
- State: raw metasploit/sliver/session output, `/state.exploitAction` for the
  latest Exploit action, and `/state.exploitActionHistory` for bounded
  search/prepare/execute stage history.
- Search/prepare/execute differentiation is covered by
  `scripts/exploit-action-differentiation-proof.py`: seeded state records
  SEARCH done with `metasploit`, PREPARE done with `manual_plan`, EXECUTE
  running with `run_shell`, and Exploit tab activity with `lastTool=execute`.
- Visible SEARCH/PREPARE/EXECUTE stage badges are captured under
  `docs/visual-proofs/checkpoint-100`.
- Listener, custom script, and implant lifecycle state now tracks idle, running,
  done, failed, and canceled and is visible in the relevant Exploit subtab.
- Live UI screenshot coverage for Reverse Shells, Custom, and C2 lifecycle
  strips is captured by `scripts/visual-tab-proof.py`.

Post:

- Buttons: Run LinPEAS, impacket Run, Pivot.
- Chat path: sends prompts to chat.
- State: raw post-exploitation output, network hosts, and structured
  per-host/session output attribution.
- Privilege escalation, AD/impacket, and lateral movement lifecycle state now
  tracks idle, running, done, failed, and canceled and is visible in the
  relevant Post subtab.
- Live UI screenshot coverage for PrivEsc, AD Attacks, and Lateral lifecycle
  strips is captured by `scripts/visual-tab-proof.py`.
- Per-host/session attribution is covered by `scripts/post-attribution-proof.py`:
  seeded linpeas, impacket secretsdump, and metasploit session output produce
  structured host/user/session rows through `/state.postAttribution` and
  `/results.postAttribution`.
- Visible attribution rows are captured under
  `docs/visual-proofs/checkpoint-94`.

OSINT:

- Buttons: Search for username/email/metadata/screenshot.
- Chat path: sends prompts to chat.
- State: parsed OSINT rows and screenshots.
- Username, email, metadata, and screenshot lifecycle state now tracks idle,
  running, done, failed, and canceled and is visible in the active OSINT subtab.
- Live UI screenshot coverage for Username, Email, Metadata, and Screenshots
  lifecycle strips is captured by `scripts/visual-tab-proof.py`.
- Screenshot artifact path validation and preview metadata are covered by
  `scripts/osint-screenshot-artifact-proof.py`; visible preview state is
  captured under `docs/visual-proofs/checkpoint-90`.
- Screenshot artifact row actions are covered by
  `scripts/osint-artifact-actions-proof.py`: artifact rows expose open, reveal,
  and copy-path actions when the file exists, and `/state.osintArtifactAction`
  tracks last action, validated path, byte count, and action history.
- Visible artifact action controls are captured under
  `docs/visual-proofs/checkpoint-95`.

Report:

- Buttons: Generate, PDF, Markdown, Create Finding, delete finding.
- Chat path: report generation is direct app code, not model-driven.
- State: findings, generated report output, and last export status/artifacts.
- Render/export artifact validation is covered by
  `scripts/report-export-proof.py`: it seeds a deterministic critical finding,
  exports HTML, Markdown, JSON, and PDF into a QA directory, validates paths,
  bytes, expected content markers, and `%PDF`, and exposes the metadata through
  `/state.reportExport`.
- Visible report export state is captured under
  `docs/visual-proofs/checkpoint-91`.

Stash:

- Buttons: filters, search, add, copy, send to chat, delete.
- Chat path: send-to-chat injects bounded stash content into the active chat.
- State: persisted stash rows plus query-scored context catalogue source.
- Source/op scoping and catalogue inclusion/exclusion are covered by
  `scripts/context-catalog-proof.py`; scored targeted retrieval is covered by
  `scripts/stash-retrieval-proof.py`.
- Visible retrieval audit state is captured under
  `docs/visual-proofs/checkpoint-92`.

Settings:

- Model folder only; Qwen/MiniMax warning.
- Unsupported folders are blocked before engine launch. `AppState.startEngine()`
  inspects the selected folder, refuses non-Qwen/non-MiniMax families, sets
  `healthStatus=blocked`, exposes `/state.engineError`, and the Settings engine
  control shows a disabled `Blocked` state.
- Runtime autodetect for generation/parser/cache.
- Context catalogue settings.
- Cache budgets/topology.
- Agent count/mode settings.
- CVE database and tool installer panels.
- App-only settings can now be applied without restarting the engine; model,
  cache, and engine runtime changes still use Apply & Restart Engine.
- App-only apply is covered by `scripts/settings-apply-proof.py`.

## QA Matrix Required For Completion

Automated no-model gates:

- Swift build.
- Engine pytest.
- Static scans for removed zombie profile code and required context hooks.
- TestServer `/state`, `/messages`, `/results` smoke.
- Context catalogue seeded-state smoke.
- Context catalogue source inclusion/exclusion and active-op stash scoping via
  `scripts/context-catalog-proof.py`.
- App-only settings apply without engine restart via
  `scripts/settings-apply-proof.py`.
- Chat scroll lock visual smoke.
- `scripts/live-turn-harness.py` mock-engine proof:
  - attaches a mock OpenAI-compatible stream endpoint;
  - seeds session context through the QA server;
  - proves outbound requests include the dynamic context packet and tools schema;
  - proves streamed reasoning/content/usage metrics are consumed;
  - proves reasoning-off requests disable both `enable_thinking` and
    `chat_template_kwargs.enable_thinking`, with no thinking messages emitted;
  - proves `/stop` interrupts a deliberately slow stream before the final
    marker reaches chat;
  - proves `/stop` interrupts a long-running `run_shell` subprocess, marks the
    tool card canceled, and prevents post-sleep output from landing;
  - proves Network capture lifecycle moves to running and then canceled when a
    long-running capture-style tool is stopped;
  - proves Creds cracking lifecycle moves to running and then canceled when a
    long-running hashcat-style tool is stopped;
  - proves Exploit listener lifecycle moves to running and then canceled when a
    long-running listener-style tool is stopped;
  - proves Post privilege-escalation lifecycle moves to running and then
    canceled when a long-running LinPEAS-style tool is stopped;
  - proves OSINT username lifecycle moves to running and then canceled when a
    long-running Sherlock-style tool is stopped;
  - proves tool callbacks update per-tab activity state that the tab bar can
    render as running/done/failed/canceled indicators;
  - proves model-issued `search_context` returns targeted catalogue facts;
  - proves automatic context injection stays at 4 snippets or fewer and tells
    the model to use `search_context` for more targeted retrieval;
  - proves web-tab tool schemas are query bounded and do not include unrelated
    OSINT/exploit schemas in the request body;
  - proves `/state.requestContext` exposes whether context was injected, how
    many snippets were selected, and which tool schemas were exposed;
  - proves the expandable chat request-context inspector can show the bounded
    context packet preview and exposed tool schema names;
  - proves semantic CVE mode invokes the embedder path when stored embeddings
    are available and exposes semantic state through `/state.cveSemantic`;
  - proves prefix cache, prompt L2, paged cache, block L2, TurboQuant Q4, and
    model-folder generation defaults remain enabled in runtime config;
  - proves the new-context route clears chat state and token/cached counters
    without changing model or cache defaults;
  - proves `search_cve` tool calls execute under autopilot;
  - proves manual mode converts tool calls into suggestions;
  - proves copilot mode pauses for approval and executes after approval.

Mock-model gates:

- Streaming text with usage metrics. Covered by `scripts/live-turn-harness.py`.
- Streaming reasoning with reasoning on. Covered by `scripts/live-turn-harness.py`.
- No-reasoning request path. Covered by `scripts/live-turn-harness.py`.
- Tool-call loop under manual/copilot/autopilot. Covered by
  `scripts/live-turn-harness.py`.
- Stop/cancel during stream. Covered by `scripts/live-turn-harness.py`.
- Stop/cancel during tool execution. Covered by `scripts/live-turn-harness.py`.
  The harness now uses an isolated app data directory, and `ToolExecutor.cancel()`
  marks executor state idle immediately after terminating the process so the
  visible status does not remain stuck while exit collection finishes.
- Context packet observed in the outbound request body. Covered by
  `scripts/live-turn-harness.py`.
- Per-tab tool activity state. Covered by `scripts/live-turn-harness.py` for
  the Web/CVE path; tab-bar visual screenshot coverage is now captured by
  `scripts/visual-tab-proof.py`.
- Nested lifecycle strip visual state. Covered by
  `scripts/visual-tab-proof.py` with cropped captures under
  `docs/visual-proofs/checkpoint-70`.

Real-model gates:

- Qwen, MiniMax, and unsupported-folder metadata/dry-run verification is now
  covered by `scripts/verify-live-models.py` and
  `testsuite/test_live_model_verifier.py`. The script proves supported-family
  detection and launcher args for model-folder generation defaults, parser
  defaults, prefix cache, prompt L2, paged cache, block L2, and TurboQuant Q4.
- App-level model-folder warning state is covered by
  `scripts/model-folder-warning-proof.py`: temporary Qwen and MiniMax fixtures
  are accepted, and an unsupported fixture exposes the required Qwen/MiniMax
  parser/cache warning through `/state.modelFolderInfo`.
- Unsupported folder start-blocking is covered by
  `scripts/unsupported-model-start-proof.py`: an unsupported fixture cannot
  start the engine, `engineRunning` remains false, `/state.engineError` carries
  the Qwen/MiniMax blocking message, and `healthStatus` becomes `blocked`.
- Qwen live proof is captured at
  `docs/live-proofs/checkpoint-76-qwen-repeat-cache-live.json`. It proves
  actual engine startup, JANG folder load, non-empty chat completion,
  `/health`, `/v1/models`, `/v1/cache/stats`, parser autodetect, generation
  defaults from the model folder, prefix cache, prompt L2, paged cache, block
  L2, TurboQuant Q4 metadata, Qwen hybrid SSM companion L2 storage, and a
  repeated prompt hit with 20 cached tokens and 20 tokens saved.
- Quantized block L2 proof is captured at
  `docs/live-proofs/checkpoint-77-block-l2-quantized-proof.json`. It uses real
  MLX safetensors I/O to write a quantized KV block through `BlockDiskStore`,
  reopen the disk store, and promote the full block through
  `BlockAwarePrefixCache.fetch_cache()` with `disk_writes=1`, `disk_hits=1`,
  and `promoted_block.type=quantized_kv`.
- Parser API proof is captured at
  `docs/live-proofs/checkpoint-79-parser-api-proof.json`. It proves configured
  Qwen reasoning/tool parsers convert one mixed output into cleaned assistant
  content, `reasoning_content`, structured OpenAI `tool_calls`, and
  `finish_reason=tool_calls` without leaking raw parser tags into content.
- MiniMax live proof is captured at
  `docs/live-proofs/checkpoint-80-minimax-strict-live.json`. It routes through
  `jang_tools.load_jangtq_model`, warms up, reaches `/health`, `/v1/models`,
  and `/v1/cache/stats`, reports the intended full-KV cache topology, uses
  temporary prompt/block L2 cache roots for proof isolation, sends the MiniMax
  request with thinking-enabled template kwargs, returns non-empty assistant
  content on first and repeat turns, and proves repeat prefix-cache reuse with
  `cached_tokens=40` and `scheduler_cache.tokens_saved_delta=40`.
- Full prompt -> context catalogue -> stream -> tool call -> tab result loop is
  covered with the mock engine; real-model repetition remains open.
- Prefix/L2/cache metrics visibility is script-checkable after real engine load
  and still needs real-engine UI screenshot proof. Seeded token metric UI is
  captured by `scripts/visual-chat-proof.py`.
- Full-block block L2 quantized write/read/promotion is covered by
  `scripts/prove-block-l2-cache.py`; a full real-model cross-run block L2 hit
  remains open.
- New-context reset semantics are covered by `scripts/live-turn-harness.py`:
  the mock-engine app clears chat plus prompt/completion/cached counters while
  preserving prefix, prompt L2, paged, block L2, TurboQuant Q4, and
  model-folder generation-default flags.
- Parsed engine cache runtime counters are exposed through
  `/state.engineCacheStats` and covered by `scripts/cache-stats-state-proof.py`
  for TurboQuant, prompt L2, block L2, SSM companion disk, and memory counters.
- Reasoning/tool parser API shaping is covered by
  `scripts/prove-parser-api.py` and `testsuite/test_tool_parser_api.py`.
- Settings/message/result-store persistence is covered by
  `scripts/persistence-proof.py`.
- Per-turn request context/tool-schema audit persistence is covered by
  `scripts/request-audit-proof.py`.

Visual gates:

- Settings model warning, engine live cache status, and cache topology sections
  are captured under `docs/visual-proofs/checkpoint-73`.
- Chat scroll locked, paused/new-output, and relock-ready states are captured
  under `docs/visual-proofs/checkpoint-72`.
- Reasoning expanded/streaming and collapsed states are captured under
  `docs/visual-proofs/checkpoint-72`; manually reopened is represented by the
  expanded forced state.
- Token metrics plus context/tool-schema count seeded state is captured under
  `docs/visual-proofs/checkpoint-71`.
- Expanded request-context inspector state is captured under
  `docs/visual-proofs/checkpoint-84`.
- Per-assistant-turn request audit badges are captured under
  `docs/visual-proofs/checkpoint-87`.
- Tool approval card, running tool card, and failed tool card states are
  captured under `docs/visual-proofs/checkpoint-71`.
- Tab-bar action running/done/failed/canceled states are captured under
  `docs/visual-proofs/checkpoint-69`.
- Nested lifecycle strip states are captured under
  `docs/visual-proofs/checkpoint-70`.
- Network Protocol Scan running state is captured under
  `docs/visual-proofs/checkpoint-98`.
- Creds Start Crack done state and CRACKED result badges are captured under
  `docs/visual-proofs/checkpoint-99`.
- Exploit search/prepare/execute stage badges are captured under
  `docs/visual-proofs/checkpoint-100`.
- OSINT screenshot artifact preview is captured under
  `docs/visual-proofs/checkpoint-90`.
- Report export status and generated finding state are captured under
  `docs/visual-proofs/checkpoint-91`.
- Stash retrieval audit state is captured under
  `docs/visual-proofs/checkpoint-92`.
- Unsupported model-folder warning and engine blocked states are captured under
  `docs/visual-proofs/checkpoint-93`.
- Post-exploitation output attribution is captured under
  `docs/visual-proofs/checkpoint-94`.
- OSINT screenshot artifact actions are captured under
  `docs/visual-proofs/checkpoint-95`.
- Web Verify queued/progress state is captured under
  `docs/visual-proofs/checkpoint-96`.
- Recon Full Recon running state is captured under
  `docs/visual-proofs/checkpoint-97`.
- Remaining visual gap: real-engine cache metrics state.

## Current Gaps To Close Next

1. Debug MiniMax forced no-thinking decode/API output separately from the
   supported thinking-enabled smoke path; the strict live proof now passes with
   non-empty assistant content and cache reuse.
