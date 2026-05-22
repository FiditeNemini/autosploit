# ExploitBot App Flow Inventory - 2026-05-21

## Current Runtime Contract

ExploitBot is now intended to run from a selected model folder, not a guessed
small/medium/large profile. The user selects a local Qwen or MiniMax
JANG/JANGTQ model folder. The app inspects `config.json`, `jang_config.json`,
`jangtq_config.json`, `generation_config.json`, and tokenizer metadata, then the
Python engine autodetects the effective runtime config.

Supported model warning: only Qwen and MiniMax families are supported in this
beta path. Unknown folders can still be selected for inspection, but the app
warns that runtime behavior is unsupported.

Required engine defaults for this lane:

- Reasoning parser: `auto`
- Tool parser: `auto`
- Generation defaults: model folder source of truth
- KV cache: TurboQuant Q4 encode/decode at cache storage boundaries
- Prefix cache: enabled
- Prompt L2 disk cache: enabled
- Paged KV cache: enabled
- Block L2 disk cache: enabled
- Qwen hybrid SSM: requires companion SSM state and async rederive support
- MiniMax: full KV attention path with prefix/L2/TurboQuant cache support

## Shell And Session Wiring

`ContentView` owns the main surface. It switches between onboarding and the
workspace, then renders:

- `SidebarView` for ops, mode, and agent selection.
- `TabBarView` for Recon/Web/Network/Creds/Exploit/Post/OSINT/Report/Stash.
- `PhaseIndicatorView` for pentest phase and findings count.
- Active tab content on the left.
- Activity feed or terminal at the bottom.
- `ChatPanelView` on the right.
- `SettingsView` and `FindingWizardView` as overlays.

Every actionable tool-tab button currently flows through
`ContentView.sendToChat(_:)`, which calls `state.displayChatService.send(...)`.
In multi-agent mode, `displayChatService`, `displayResultsStore`, and
`displayActivityFeed` point at the selected agent; otherwise they point at the
main session.

`AppState` owns persistence and runtime setup:

- Loads/saves engine settings in `DatabaseManager` settings.
- Starts/stops `EngineManager`.
- Wires `ChatService` to `ToolExecutor`, `ResultsStore`, `ActivityFeed`,
  `CVEService`, and `AgentManager`.
- Saves current messages and active op state.
- Deploys agents with the same model-folder-driven generation defaults.

## Chat Stream And Tool Execution

`ChatService` owns the OpenAI-compatible chat loop:

- Builds the system prompt with phase guidance, tool catalog, and context.
- Injects a prompt-ranked context catalogue through `onContextUpdate`.
- Sends streaming and non-streaming requests to the local engine.
- Keeps reasoning content separate when the engine parser exposes it.
- Reasoning can be toggled on/off from the chat header. Reasoning blocks expand
  while streaming and collapse after completion unless the user manually toggles
  the block.
- Metrics show token/s, TTFT, prompt tokens, cached prompt tokens, and
  completion tokens when the engine returns usage.
- The same strip shows the last request's selected context count and exposed
  tool-schema count, with hover details for context preview and tool names.
- Chat scroll lock is explicit: locked mode follows the latest output, dragging
  pauses auto-scroll, and the "Latest/New output" control relocks to the newest
  message.
- Parses `tool_calls` from the API response.
- In manual mode, tools require explicit user approval.
- In copilot/autopilot modes, the loop can execute approved tool calls up to
  `maxIterations`.
- Built-in CVE calls use callbacks instead of shell subprocesses.
- Shell-backed tools run through `ToolExecutor`.
- Tool output is appended to chat, activity feed, and `ResultsStore.ingest`.

The full tool catalog is no longer force-sent to the engine. `ChatService`
passes the latest user prompt plus active tab into `ToolDefinitions.forModel`,
which always keeps the built-in retrieval/CVE/shell callbacks visible and then
adds only the highest-ranked installed tools for the current lane, capped at 12
schemas by default. The old profile-dependent tool reduction is removed; tool
visibility is now prompt/tab based rather than small/medium/large model based.

## Context And Catalog State

Current context sources:

- `ContextCatalogService.contextPacket(...)` via `ChatService.onContextUpdate`.
- CVE full-text/CPE/severity lookup through `CVEService`.
- CVE semantic search support exists inside `CVEService`, backed by stored
  embeddings when available.
- Stash items can be sent to chat, truncated to about 5 KB in `ContentView`.
- Active phase guidance comes from `PentestPhase`.
- Active op, scope, findings, and stash are persisted through `DatabaseManager`.

Implemented dynamic catalogue lane:

- `ContextCatalogService` indexes parsed assets, findings, recent raw tool
  output, stash items, and CVE results for the active chat turn.
- The catalogue ranks items against the latest user prompt, active tab, current
  phase, severity, and source type.
- Only the configured top snippets are injected into the chat API request as a
  system note. The full stash/results/raw output set is not force-fed.
- The injected packet includes source labels such as `asset.port`, `finding`,
  `tool.output`, `stash.raw`, and `cve` so the model can see provenance.
- CVE assist is controlled by Settings: off, current visible CVE results, or
  semantic embedding search. Semantic mode calls the local CVE embedder path
  when available and falls back through `CVEService` when embeddings are absent.
- Semantic mode is covered by `scripts/semantic-cve-proof.py`: the proof injects
  a deterministic fake embedder, seeds stored vectors, and verifies the context
  packet uses the vector-ranked CVE rather than silent text fallback.

Required next catalog lane:

- Add durable embeddings for tools, techniques, findings, assets, commands,
  prior outputs, and stash items, not only CVEs.
- Store retrieval decisions with the chat turn for later audit.
- Add a full expandable "context used" inspection panel; compact context/tool
  counters are visible now.

## Tab Functions

Recon:

- Subtabs cover subdomains, ports, web hosts, crawl, and OSINT-oriented recon.
- Main buttons create recon prompts and send them to chat.
- Displays parsed `subfinder`, `dnsx`, `nmap`, `httpx`, and crawl outputs from
  `ResultsStore`.
- Needs button-level running/error/complete states tied to tool calls.

Web:

- Shows web hosts, vulnerabilities, CVE data, and finding creation entrypoints.
- Can stash selected content and prefill the finding wizard.
- Uses `CVEService` directly for visible CVE search/lookup.
- Needs CVE/tool progress indicators on the related buttons and rows.

Network:

- Covers protocol enumeration, SMB/WinRM/SSH-style netexec prompts, SNMP,
  capture, MITM, and tunnels.
- Buttons send structured prompts to chat.
- Displays parsed network host and raw tool output.
- Capture, MITM, and Tunnels lifecycle strip screenshots are captured under
  `docs/visual-proofs/checkpoint-70`.
- Still needs per-action visual state for protocol scan buttons.

Creds:

- Covers hash cracking, brute force, secret scanning, and credential-derived
  findings.
- Buttons route prompts through chat.
- Displays parsed vulnerabilities and credential-oriented results.
- Needs progress and result badges on cracking/bruteforce actions.

Exploit:

- Covers exploit search, listeners, custom script execution, and Sliver helper
  prompts.
- Buttons route prompts through chat and display raw execution output.
- Listener, custom script, and implant actions expose lifecycle strips for
  idle/running/done/failed/canceled status and are covered by the live-turn
  listener cancellation proof plus checkpoint-70 visual screenshots.
- Still needs safer visual differentiation between search, prepare, and execute
  actions.

Post:

- Covers privilege escalation, impacket/netexec-style post-exploitation, and
  pivot prompts.
- Buttons route prompts through chat and display raw results.
- Privilege escalation, AD/impacket, and lateral movement actions expose
  lifecycle strips for idle/running/done/failed/canceled status and are covered
  by the live-turn LinPEAS-style cancellation proof plus checkpoint-70 visual
  screenshots.
- Still needs progress tied to host/session context and visible output status.

OSINT:

- Covers username, email, metadata, screenshot, and general OSINT prompts.
- Displays parsed `sherlock` results and raw output.
- Username, email, metadata, and screenshot actions expose lifecycle state for
  idle/running/done/failed/canceled status on the active search mode and are
  covered by the live-turn Sherlock-style cancellation proof plus checkpoint-70
  visual screenshots.
- Still needs screenshot artifact preview validation and richer result-row
  status.

Report:

- Generates markdown/HTML/PDF from stored findings.
- Opens finding creation and deletes findings.
- Does not currently route report generation through chat.
- Needs proof-oriented export status and screenshot/render validation.

Stash:

- Stores reusable raw/context items by type.
- Filters and searches stash.
- Can send a bounded item into chat context.
- Needs retrieval scoring and catalogue integration before it becomes the
  dynamic context memory layer.

## Settings Functions

Model:

- User selects a model folder by path or browse panel.
- `ModelFolderInspector` detects family, model type, and config files.
- UI warns when the folder is not Qwen or MiniMax.
- Curated S/M/L profile selection is removed.

Runtime Autodetect:

- Generation defaults are marked as model-folder driven.
- Reasoning parser and tool parser are fixed to `auto`.
- Parser override controls are removed from the primary settings surface.

Cache:

- KV cache is fixed to TurboQuant Q4 auto.
- Prefix cache, prompt L2 disk cache, paged cache, and block L2 disk cache stay
  enabled.
- User can tune disk budgets, block size, and memory percentage.

Agents:

- Multi-agent mode remains available.
- Active agents inherit the same model-folder defaults and parser/cache policy.
- App-only Settings apply updates agent and loop controls without restarting the
  engine.

Context Catalog:

- Dynamic context can be enabled or disabled.
- User can choose max injected snippets.
- User can include/exclude assets, findings, recent tool output, and stash.
- CVE assist can be off, current-result only, or semantic embedding ranked.
- These settings are stored in the local settings database and applied to main
  chat plus newly deployed agents.
- App-only Settings apply updates context controls without restarting the
  engine; model/cache/runtime engine changes use the explicit restart action.

CVE Database and Tools:

- Existing settings panels remain in place.
- They should later feed the dynamic catalogue index and visible tool-status
  indicators.

## Test And Proof Requirements

Current repeatable gates:

- `swift build --package-path ExploitBot`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `python3 scripts/live-turn-harness.py`
- `cd ExploitBotEngine && uv run --extra dev ../scripts/prove-parser-api.py --output ../docs/live-proofs/checkpoint-79-parser-api-proof.json`
- `python3 scripts/context-catalog-proof.py`
- `python3 scripts/tool-catalog-proof.py`
- `python3 scripts/semantic-cve-proof.py`
- `python3 scripts/settings-apply-proof.py`
- `python3 scripts/verify-live-models.py --metadata-only --qwen /Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP --minimax /Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ --unsupported /Users/eric/models/mlx-community/gemma-3n-E2B-it-4bit`
- `python3 scripts/visual-tab-proof.py`
- `python3 scripts/visual-chat-proof.py`
- `python3 scripts/visual-chat-interaction-proof.py`
- `python3 scripts/visual-settings-proof.py`
- `python3 scripts/verify-live-models.py --qwen /Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP --unsupported /Users/eric/models/mlx-community/gemma-3n-E2B-it-4bit --output docs/live-proofs/checkpoint-76-qwen-repeat-cache-live.json`
- `cd ExploitBotEngine && uv run --extra dev ../scripts/prove-block-l2-cache.py --output ../docs/live-proofs/checkpoint-77-block-l2-quantized-proof.json`
- `git diff --check`
- Static scans proving no S/M/L profile selectors or `ModelProfile` code remain.
- Visual QA through the local app run script plus screenshots.

Required future proof gates:

- Model-folder fixture test: Qwen folder, MiniMax folder, and unsupported folder
  detection. Covered by `testsuite/test_live_model_verifier.py`.
- Engine no-model smoke proving `/health` and `/v1/models` report parser,
  generation, topology, and cache metadata.
- MiniMax real generation smoke proving full KV attention with prefix hits,
  prompt/block L2 cache metadata, and TurboQuant encode/decode cache stats.
  Current strict live proof at
  `docs/live-proofs/checkpoint-80-minimax-strict-live.json` reaches model load,
  warmup, health, runtime metadata, isolated prompt/block L2 cache roots,
  thinking-enabled MiniMax template kwargs, non-empty first/repeat assistant
  content, and repeat cached-token reuse.
- Qwen hybrid SSM smoke proving KV prefix hits only when companion SSM state is
  present, plus async rederive status. Current Qwen live proof verifies load,
  generation, cache metadata, SSM companion L2 storage, and a repeat paged-cache
  hit with 20 cached tokens. Async rederive status remains open.
- Quantized block L2 proof: covered by
  `docs/live-proofs/checkpoint-77-block-l2-quantized-proof.json`, which proves
  real MLX safetensors write/read plus full-block disk promotion for
  `quantized_kv` cache data.
- Reasoning parser smoke proving thinking text is separated from visible output:
  covered by `docs/live-proofs/checkpoint-79-parser-api-proof.json`.
- Tool parser smoke proving parsed API `tool_calls`, not raw text only:
  covered by `docs/live-proofs/checkpoint-79-parser-api-proof.json`.
- Settings model warning, engine live cache status, and cache topology
  screenshots are captured under `docs/visual-proofs/checkpoint-73`.
- Chat token metrics, active tool header, approval card, running tool card,
  failed tool card, and streaming reasoning state are captured under
  `docs/visual-proofs/checkpoint-71`.
- Chat scroll locked/paused and reasoning expanded/collapsed states are captured
  under `docs/visual-proofs/checkpoint-72`.
- Tab-bar activity screenshots are captured under
  `docs/visual-proofs/checkpoint-69`.
- Nested lifecycle strip screenshots are captured under
  `docs/visual-proofs/checkpoint-70`.
