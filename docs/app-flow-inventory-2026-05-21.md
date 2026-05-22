# ExploitBot App Flow Inventory - 2026-05-21

## Current Runtime Contract

ExploitBot is now intended to run from a selected model folder, not a guessed
small/medium/large profile. The user selects a local Qwen or MiniMax
JANG/JANGTQ model folder. The app inspects `config.json`, `jang_config.json`,
`jangtq_config.json`, `generation_config.json`, and tokenizer metadata, then the
Python engine autodetects the effective runtime config.

Supported model warning: only Qwen and MiniMax families are supported in this
beta path. Unknown folders can still be selected for inspection, but the app
warns that runtime behavior is unsupported and blocks engine start before
launching the Python process.

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

Manual tab switching now routes through `AppState.switchToolTab(_:)`, exposes
`/state.tabSwitchActions` with from/to tab, follow-agent pause state, and
activity-feed visibility, and is covered by `scripts/tab-switch-action-proof.py`.
Terminal, settings, and finding-wizard overlay open/close controls route
through AppState and expose `/state.windowOverlayActions`; covered by
`scripts/window-overlay-actions-proof.py`.
Phase dot and Next Phase controls route through AppState and expose
`/state.phaseActions` with from/to phase, reset tool count, phase guidance, and
activity-feed visibility; covered by `scripts/phase-action-proof.py`.
Cross-app session workflows are summarized through `/qa/session-coverage`,
including onboarding and Sidebar mode selection, pending-approval rejection,
sidebar create/rename/switch/delete, create-op stop behavior, overlays,
model-folder pickers, persistence across relaunch, saved messages, restored
results, finding wizard submit, tab switching, phase actions, Activity Feed
actions, proof-count metadata, and the `stateKeys` those proofs validate.
The coverage payload now lists the phase and Activity Feed QA routes (`/phase`,
`/qa/seed-activity-actions`, `/qa/activity-action`) plus `proofCount`, so the
aggregate cannot claim those contracts without exposing the routes.

Every actionable tool-tab button currently flows through
`ContentView.sendToChat(_:)`, which calls `state.sendChatMessage(...)` so the
send is visible in `/state.chatControlActions`.
AppState tool-action helpers that queue prompts also use `sendChatMessage(...)`
instead of calling `ChatService` directly; covered by
`scripts/tool-action-chat-control-proof.py`.
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
- Onboarding completion and Sidebar mode selection now share AppState handlers.
  `/state.modeSelection` exposes the available Autopilot/Copilot/Manual modes,
  current selected mode, active op mode, source, onboarding visibility, and
  pending-approval rejection status.

## Chat Stream And Tool Execution

`ChatService` owns the OpenAI-compatible chat loop:

- Builds the system prompt with phase guidance, tool catalog, and context.
- Injects a prompt-ranked context catalogue through `onContextUpdate`.
- Sends streaming and non-streaming requests to the local engine.
- Keeps reasoning content separate when the engine parser exposes it.
- Reasoning can be toggled on/off from the chat header. Reasoning blocks expand
  while streaming and collapse after completion unless the user manually toggles
  the block. Header reasoning, context-inspector, and new-context controls now
  route through AppState and expose `/state.chatControlActions`; covered by
  `scripts/chat-control-actions-proof.py`.
- Chat send, stop, approve, reject, and clear/new-context controls also route
  through AppState and expose `/state.chatControlActions`; covered by
  `scripts/chat-turn-controls-proof.py`.
- Metrics show token/s, TTFT, prompt tokens, cached prompt tokens, and
  completion tokens when the engine returns usage.
- The same strip shows the last request's selected context count and exposed
  tool-schema count, with hover details for context preview and tool names.
- The request-context inspector expands below the metrics strip and shows the
  bounded context packet preview plus exposed tool schema names for the last
  model request.
- Chat scroll lock is explicit: locked mode follows the latest output, dragging
  pauses auto-scroll, and the "Latest/New output" control relocks to the newest
  message.
- Chat copy and stash controls route through AppState: transcript copy,
  per-message copy, tool-output copy, per-message stash, and latest-assistant
  stash expose `/state.chatActions`; chat stash also updates
  `/state.stashActions` through the same `recordStashAdd` path used by the
  Stash tab. Covered by `scripts/chat-actions-proof.py`; `/qa/chat-coverage`
  exposes `stateKeys` for the chat/control/context/visual/stash/feed surfaces.
- Parses `tool_calls` from the API response.
- In manual mode, tools require explicit user approval.
- In copilot/autopilot modes, the loop can execute approved tool calls up to
  `maxIterations`.
- Mode surface wiring is covered by `scripts/mode-selection-flow-proof.py`,
  which proves onboarding-created Manual mode, Sidebar mode switching,
  active-op persistence, pending approval rejection, and activity logging.
- Multi-agent header/settings controls are covered by
  `scripts/agent-actions-proof.py`, which proves deploy, switch, remove, and
  clear route through AppState, update `/state.agentActions`, preserve the
  active-agent selection, and log visible activity. Deploy task-send telemetry
  exposes `taskSent` and `messageCount`; covered by
  `scripts/agent-deploy-task-send-proof.py`.
- Multi-agent Settings toggles are covered by
  `scripts/agent-settings-actions-proof.py`, which proves enable/disable and
  max-concurrent controls route through AppState, persist config, clear agents
  on disable, and expose visible action telemetry.
- `/qa/agent-loop-coverage` now exposes the mode, route, contract, action
  telemetry fields, proof count, deploy-sheet, task-send, and settings-control
  proof surface for the agentic loop.
- Built-in CVE calls use callbacks instead of shell subprocesses.
- Shell-backed tools run through `ToolExecutor`.
- Tool output is appended to chat, activity feed, and `ResultsStore.ingest`.
  `/state.feedRecent` exposes the latest activity records so model tool actions
  can be audited as visible start/complete status, not just counted.
  Representative outputs across the structured and raw-only tool families are
  now provable through `/qa/result-parser-coverage`, which verifies that parser
  output reaches the tab collections and `/results` rather than staying as raw
  chat text only. The route now returns a standard `ok` aggregate status.
- Parsed result rows also flow back into the dynamic context catalogue. Assets,
  findings, recent raw output, OSINT artifacts, and post-exploitation
  attributions are retrievable through the same bounded context/search path.
- Representative all-family fanout is covered by
  `scripts/tool-family-fanout-coverage-proof.py`: Recon, Web, Network, Creds,
  Exploit, Post, and OSINT fixtures each prove chat-card, activity-feed,
  tab-activity, parsed-result, and context-catalog coverage. The route now
  returns a standard `ok` aggregate status. `/qa/tool-flow-coverage.stateKeys`
  exposes the message, tab activity, feed, result, and context-catalog surfaces
  behind those proofs.

The full tool catalog is no longer force-sent to the engine. `ChatService`
passes the latest user prompt plus active tab into `ToolDefinitions.forModel`,
which always keeps the built-in retrieval/CVE/shell callbacks visible and then
adds only the highest-ranked installed tools for the current lane, capped at 12
schemas by default. The old profile-dependent tool reduction is removed; tool
visibility is now prompt/tab based rather than small/medium/large model based.
The exposed registry is auditable through `/qa/tool-coverage`: each tool reports
callback-vs-subprocess execution, sample CLI routing, tab ownership, global
visibility, and structured-vs-raw result mode so tool-loop coverage can be
checked without relying on a live model to enumerate the catalogue. The route
returns a standard `ok` aggregate status.

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
- Non-CVE catalogue indexing now persists deterministic embedding records in
  `catalogEmbeddings` for assets, findings, raw tool output, and stash items.
  `/state.catalogEmbeddings` exposes record count, source list, per-source
  counts, and vector dimensions for QA and Settings-adjacent diagnostics.
- Each selected context packet includes a compact selected-source audit, and
  assistant turns persist that audit in `messages.contextSelections` alongside
  the context summary and tool-schema list.
- Durable non-CVE catalogue indexing and per-turn selected-source persistence
  are covered by `scripts/catalog-embedding-audit-proof.py`: it seeds
  asset/finding/tool-output/stash records, verifies the persisted embedding
  catalogue, sends a bounded prompt through a mock engine, relaunches the app,
  and verifies both catalogue records and assistant retrieval selections survive.
- `/qa/context-coverage.stateKeys` exposes the AppState/message audit surfaces
  used by these context proofs: context catalogue config, request context,
  context-window reset policy, catalog embeddings, stash retrieval, semantic CVE,
  and assistant-turn selected source/tool-schema audits.

## Tab Functions

Recon:

- Subtabs cover subdomains, ports, web hosts, crawl, and OSINT-oriented recon.
- Main buttons create Recon action state, then send generated prompts to chat.
- Displays parsed `subfinder`, `dnsx`, `nmap`, `httpx`, and crawl outputs from
  `ResultsStore`.
- Full Recon/Crawl/Harvest action status is represented by `/state.reconAction`
  and the active toolbar button. `scripts/recon-action-status-proof.py` verifies
  a seeded Full Recon target, generated command, and running tab activity; the
  visible state is captured under `docs/visual-proofs/checkpoint-97`.
- Copy controls now route through AppState for Subdomains, Ports, Web Hosts,
  Crawl, and OSINT. `/state.reconCopyActions` exposes the last kind, copied
  count, clipboard preview, and summary, with tab activity recorded as
  `lastTool=copy_recon`; `scripts/recon-copy-actions-proof.py` covers the live
  seed/copy/state path.

Web:

- Shows web hosts, vulnerabilities, CVE data, and finding creation entrypoints.
- Can stash selected content and prefill the finding wizard. Create Finding,
  Stash, Copy, Header Copy, and Search Related CVEs now route through AppState
  action handlers, and `/state.webDirectActions` exposes labels, prefill state,
  stash preview/count, clipboard preview, queued related-CVE prompt, and action
  status.
- Uses `CVEService` directly for visible CVE search/lookup.
- Direct action state is covered by `scripts/web-direct-actions-proof.py`,
  which verifies finding prefill, stash creation, copy preview, related-CVE chat
  prompt, and Web tab activity. Header copy is covered by
  `scripts/web-header-copy-proof.py`.
- Row context-menu copy actions for title, target, and details now route
  through AppState and `/state.webDirectActions`; context-menu stash uses the
  same `recordStashAdd` path as Stash tab additions, so `/state.stashActions`
  records the item. Covered by `scripts/web-row-context-actions-proof.py`.
- Verify rows now expose queued progress state tied to `/state.webAction` and
  Web tab activity. `scripts/web-verify-action-proof.py` verifies the target,
  finding title, prompt, and running tab badge; the visible queued button state
  is captured under `docs/visual-proofs/checkpoint-96`.

Per-tab direct action and copy coverage across Recon, Web, Network, Creds,
Exploit, Post, OSINT, Report, and Stash is summarized through
`/qa/tab-action-coverage`. The aggregate ties together action seed routes,
copy routes, row context actions, verify/protocol/hash/exploit/post/OSINT
actions, report generation/finding/export/agent actions, and Stash add/filter/
copy/send/delete controls with the focused proof scripts for each lane. It also
advertises the copy/export/agent and OSINT screenshot seed routes used by those
proof fixtures.
Chat/control coverage is summarized through `/qa/chat-coverage`. The aggregate
ties together Send/Stop, reasoning enable/collapse, approvals, copy/stash
actions, tool-output expansion, request-audit badges, context inspector state,
scroll-lock visual captures, tool-action/Stash chat handoff, token counters,
and visible-new-context behavior while preserving the engine cache session for
the `prefix-cache-l2-turboquant` response path.
- CVE-bearing rows now expose per-row status through `/state.webCVERows` and a
  visible chip on each vulnerability card. The same proof verifies `pending`,
  `enriched`, and active `CVE verifying` row semantics for the seeded Web
  verify path; the visual capture is under `docs/visual-proofs/checkpoint-96`.

Network:

- Covers protocol enumeration, SMB/WinRM/SSH-style netexec prompts, SNMP,
  capture, MITM, and tunnels.
- Protocol Scan creates Network action state, then sends the generated prompt to
  chat. Other buttons send structured prompts to chat.
- Displays parsed network host and raw tool output.
- Protocol Scan action status is represented by `/state.networkAction` and the
  active Scan button. `scripts/network-protocol-action-proof.py` verifies a
  seeded SMB netexec scan target, credential context, generated command, and
  running tab activity; the visible state is captured under
  `docs/visual-proofs/checkpoint-98`.
- Copy controls now route through AppState for Protocols, SNMP, Capture, MITM,
  and Tunnels. `/state.networkCopyActions` exposes the last kind, copied count,
  clipboard preview, and summary, with tab activity recorded as
  `lastTool=copy_network`; `scripts/network-copy-actions-proof.py` covers the
  live seed/copy/state path.
- Capture, MITM, and Tunnels lifecycle strip screenshots are captured under
  `docs/visual-proofs/checkpoint-70`.

Creds:

- Covers hash cracking, brute force, secret scanning, and credential-derived
  findings.
- Start Crack creates Creds action state, then sends the generated prompt to
  chat. Brute Force and Scan Secrets route prompts through chat.
- Displays parsed vulnerabilities and credential-oriented results with visible
  CRACKED/BRUTE/SECRET/CRED badges.
- Hash cracking action status is represented by `/state.credsAction`, the
  active Start Crack button, and parsed credential rows through `/results.creds`.
  `scripts/creds-action-results-proof.py` verifies a seeded hashcat result set,
  generated haiti/hashcat plan, result count, tab activity, and CRACKED badges;
  the visible state is captured under `docs/visual-proofs/checkpoint-99`.
- Copy controls now route through AppState for Cracking, Online Brute, Secrets,
  and Vault. `/state.credsCopyActions` exposes the last kind, copied count,
  clipboard preview, and summary, with tab activity recorded as
  `lastTool=copy_creds`; `scripts/creds-copy-actions-proof.py` covers the live
  seed/copy/state path.

Exploit:

- Covers exploit search, listeners, custom script execution, and Sliver helper
  prompts.
- Search records Exploit action state, then routes the generated prompt through
  chat. Prepare/execute state is represented as distinct Exploit action stages;
  listeners, scripts, and Sliver helpers route prompts through chat and display
  raw execution output.
- `/state.exploitAction` and `/state.exploitActionHistory` expose the latest
  action plus bounded search/prepare/execute history. The Metasploit tab shows
  SEARCH/PREPARE/EXECUTE stage badges instead of flattening all actions into one
  generic run state.
- Listener, custom script, and implant actions expose lifecycle strips for
  idle/running/done/failed/canceled status and are covered by the live-turn
  listener cancellation proof plus checkpoint-70 visual screenshots.
- Search/prepare/execute differentiation is covered by
  `scripts/exploit-action-differentiation-proof.py`, and the visible stage
  badges are captured under `docs/visual-proofs/checkpoint-100`.
- Copy controls now route through AppState for Metasploit, Reverse Shells,
  Custom, and C2 (Sliver). `/state.exploitCopyActions` exposes the last kind,
  copied count, clipboard preview, and summary, with tab activity recorded as
  `lastTool=copy_exploit`; `scripts/exploit-copy-actions-proof.py` covers the
  live seed/copy/state path.

Post:

- Covers privilege escalation, impacket/netexec-style post-exploitation, and
  pivot prompts.
- Buttons route prompts through chat and display raw results.
- Privilege escalation, AD/impacket, and lateral movement actions expose
  lifecycle strips for idle/running/done/failed/canceled status and are covered
  by the live-turn LinPEAS-style cancellation proof plus checkpoint-70 visual
  screenshots.
- LinPEAS, impacket secretsdump, and metasploit session output now parse into
  per-host/session attribution rows exposed through `/state.postAttribution` and
  `/results.postAttribution`; the Post tab shows the same rows above raw output.
- Attribution parsing is covered by `scripts/post-attribution-proof.py`, and the
  visible Post tab state is captured under `docs/visual-proofs/checkpoint-94`.
- Copy controls now route through AppState for PrivEsc, AD Attacks, Lateral, and
  Attribution rows. `/state.postCopyActions` exposes the last kind, copied
  count, clipboard preview, and summary, with tab activity recorded as
  `lastTool=copy_post`; `scripts/post-copy-actions-proof.py` covers the live
  seed/copy/state path.

OSINT:

- Covers username, email, metadata, screenshot, and general OSINT prompts.
- Displays parsed `sherlock` results and raw output.
- Username, email, metadata, and screenshot actions expose lifecycle state for
  idle/running/done/failed/canceled status on the active search mode and are
  covered by the live-turn Sherlock-style cancellation proof plus checkpoint-70
  visual screenshots.
- Toolbar and row copy controls for username, email, metadata, screenshot, and
  all-row OSINT output are routed through AppState. `/state.osintCopyActions`
  exposes copied kind, count, clipboard preview, and summary, while the OSINT
  tab activity reports `copy_osint`. Covered by
  `scripts/osint-copy-actions-proof.py`.
- Screenshot artifact preview validation is covered by
  `scripts/osint-screenshot-artifact-proof.py`, and the visible preview row is
  captured under `docs/visual-proofs/checkpoint-90`.
- Screenshot artifact rows now expose open, reveal, and copy-path actions when
  the backing file exists. Action metadata and state are exposed through
  `/state.osintArtifacts[*].actions`, `/state.osintArtifacts[*].actionLabels`,
  and `/state.osintArtifactAction`. The row now shows the last artifact action
  summary inline after open/reveal/copy-path.
- Artifact action behavior is covered by `scripts/osint-artifact-actions-proof.py`,
  and visible row controls are captured under
  `docs/visual-proofs/checkpoint-95`.

Report:

- Generates markdown/HTML/PDF from stored findings.
- Visible Generate now routes through AppState and exposes
  `/state.reportRenderActions` with template, finding count, generated HTML
  size, and preview; covered by `scripts/report-generate-action-proof.py`.
- Opens finding creation and deletes findings. `/state.reportFindingActions`
  exposes Create Finding/Delete finding labels, wizard visibility, last action,
  current finding rows, and the last created/deleted IDs so Report CRUD actions
  are auditable like tool-tab action states. Visible row delete wiring is
  guarded by `scripts/report-visible-delete-wiring-proof.py`. The modal submit
  button routes through AppState and is covered by
  `scripts/finding-wizard-submit-proof.py`.
- Deterministic Generate and visible PDF/Markdown exports route through
  AppState, while `Agent Draft` routes a bounded report drafting prompt
  through the chat/agent loop.
- `/state.reportAction` exposes the active report-agent draft status, template,
  finding count, and prompt.
- Exposes proof-oriented export status with artifact format/path/byte metadata
  through `/state.reportExport`.
- Export validation is covered by `scripts/report-export-proof.py` for HTML,
  Markdown, JSON, and PDF artifacts. Visible PDF/Markdown export button
  behavior is covered by `scripts/report-visible-export-actions-proof.py`,
  which uses `/qa/report-export-action`, checks `/state.reportExport`, and
  confirms activity-feed visibility. Visible report status is captured under
  `docs/visual-proofs/checkpoint-91`.
- Create/delete finding action state is covered by
  `scripts/report-finding-actions-proof.py`, which opens the Report finding
  wizard, submits a deterministic finding, verifies the row delete action
  label, deletes the row, and checks Report tab activity state.
- Agent-draft routing is covered by `scripts/report-agent-action-proof.py`, and
  the visible queued report-agent strip is captured under
  `docs/visual-proofs/checkpoint-107`.

Stash:

- Stores reusable raw/context items by type.
- Filters and searches stash.
- Filter, Add, Copy All, per-row Copy, Send, and Delete actions now route through
  AppState action handlers. `/state.stashActions` exposes action labels, current
  item rows, active filter, filtered count, clipboard preview, last action, and
  last item/deleted IDs.
- Row context-menu Copy Content and Copy Label now use the same AppState copy
  path instead of direct clipboard calls; covered by
  `scripts/stash-row-context-actions-proof.py`.
- Can send a bounded item into chat context through the same 5 KB truncation
  path used by the Stash tab. Stash send-to-chat routes through AppState chat
  control telemetry; covered by `scripts/stash-send-chat-control-proof.py`.
- Query-scored retrieval now feeds the dynamic context catalogue without forcing
  all stash items into each prompt. Active-op and global stash are eligible,
  inactive-op stash is excluded, and label/tag/content/source-tab matches affect
  rank.
- `/state.stashRetrieval` exposes the latest retrieval query, candidate count,
  returned count, top score, and top labels. The Stash tab shows the same compact
  audit strip after catalogue retrieval.
- Filter/add/copy/send/delete action state is covered by
  `scripts/stash-actions-proof.py`, which verifies item creation, clipboard
  preview, filter state, bounded chat send, deletion, and Stash tab activity
  state.
- Targeted retrieval is covered by `scripts/stash-retrieval-proof.py`, and the
  visible audit strip is captured under `docs/visual-proofs/checkpoint-92`.

## Settings Functions

- Settings are split into Engine, Model, Runtime, Context, Cache, Agents, CVE
  Database, Tools, and Logs pages through the left category sidebar.
- `/state.settingsCategoryCoverage` exposes the same category/page structure for
  proof, including title/subtitle/detail/icon metadata and expected page
  sections; `scripts/settings-category-coverage-proof.py` verifies every
  category can be selected through the QA route.
- `/qa/settings-coverage` aggregates the full Settings proof contract: category
  page order/sections, Qwen/MiniMax-only support warning surface,
  parser/generation autodetect, `prefix-cache-l2-turboquant` cache policy,
  app-only apply without engine restart, engine Start/Stop action state,
  context controls, cache topology, agent controls, CVE/tool/inference-log
  actions, visual Settings proof gates, proof-count metadata, checked-in
  Settings visual manifests, and `visualManifestCount`.

Model:

- User selects a model folder by path or browse panel.
- `ModelFolderInspector` detects family, model type, config files, and
  multimodal/VL shape.
- UI warns when the folder is not Qwen or MiniMax, and the Engine settings page
  shows a disabled `Blocked` control after an unsupported start attempt.
- Qwen VL/multimodal folders are explicitly flagged as not yet supported in the
  beta lane even though their family is Qwen, preventing text-only parser/cache
  assumptions from being applied to image-token models.
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
- Deployed agents force autopilot mode regardless of the main chat interaction
  mode, start their task prompt when the engine is running, and keep their own
  messages, activity feed, result store, context catalogue wiring, and tool-loop
  counters.
- Agent context retrieval uses the agent's own result store plus the main
  session's parsed catalogue as shared operation knowledge, so new agents can
  pull existing parsed assets/findings/attributions through `search_context`
  without forcing the entire catalogue into the prompt.
- Typed agents select the matching active tool lane for prompt-ranked schemas
  and preserve the type-specific prompt override after phase guidance is set.
- App-only Settings apply updates agent and loop controls without restarting the
  engine.
- Settings engine Start/Stop actions expose `/state.settingsEngineActions` with
  previous/current running state, model label, health status, summary, and
  activity-feed visibility. Stop action coverage is handled by
  `scripts/settings-engine-actions-proof.py`.

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
- CVE Database settings status is exposed through `/state.cveDatabase`,
  including import progress, total/KEV counts, last sync, search-result count,
  and active settings category. `scripts/cve-settings-status-proof.py` verifies
  the state contract, and `scripts/visual-cve-settings-status-proof.py` captures
  the visible CVE import/status page under
  `docs/visual-proofs/checkpoint-108`. Quick Import, Full Sync, Search, and
  custom CVE Save controls route through AppState and expose
  `/state.cveSettingsActions`; covered by
  `scripts/cve-settings-actions-proof.py`.
- Tools settings status is exposed through `/state.toolSettings`, including
  installed/missing/installing/error counts, install log, and per-tool status
  rows. `scripts/tool-settings-status-proof.py` verifies the state contract, and
  `scripts/visual-tool-settings-status-proof.py` captures the visible status
  page under `docs/visual-proofs/checkpoint-109`. Refresh, Install, and Install
  All Missing controls route through AppState and expose
  `/state.toolSettingsActions`; covered by
  `scripts/tool-settings-actions-proof.py`.
- Inference Log copy and clear route through AppState and expose
  `/state.inferenceLogActions`; covered by
  `scripts/inference-log-actions-proof.py`.
- `/qa/tab-action-coverage` exposes the per-tab action routes, proof scripts,
  contracts, and `actionStateKeys` for Recon/Web/Network/Creds/Exploit/Post/
  OSINT/Report/Stash action state surfaces.

## Test And Proof Requirements

Current repeatable gates:

- `swift build --package-path ExploitBot`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `python3 scripts/live-turn-harness.py`
- `cd ExploitBotEngine && uv run --extra dev ../scripts/prove-parser-api.py --output ../docs/live-proofs/checkpoint-79-parser-api-proof.json`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/context-catalog-proof.py`
- `python3 scripts/settings-category-coverage-proof.py`
- `python3 scripts/catalog-embedding-audit-proof.py`
- `python3 scripts/tool-catalog-proof.py`
- `python3 scripts/tool-registry-coverage-proof.py`
- `python3 scripts/tool-fanout-status-proof.py`
- `python3 scripts/tool-family-fanout-coverage-proof.py`
- `python3 scripts/result-parser-routing-proof.py`
- `python3 scripts/result-context-catalog-proof.py`
- `python3 scripts/semantic-cve-proof.py`
- `python3 scripts/settings-apply-proof.py`
- `python3 scripts/agent-autopilot-proof.py`
- `python3 scripts/agent-search-context-proof.py`
- `python3 scripts/cache-stats-state-proof.py`
- `python3 scripts/live-cache-stats-ui-proof.py`
- `python3 scripts/model-folder-warning-proof.py`
- `python3 scripts/osint-screenshot-artifact-proof.py`
- `python3 scripts/persistence-proof.py`
- `python3 scripts/request-audit-proof.py`
- `python3 scripts/network-protocol-action-proof.py`
- `python3 scripts/creds-action-results-proof.py`
- `python3 scripts/exploit-action-differentiation-proof.py`
- `python3 scripts/verify-live-models.py --metadata-only --qwen /Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP --minimax /Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ --unsupported /Users/eric/models/mlx-community/gemma-3n-E2B-it-4bit`
- `python3 scripts/visual-tab-proof.py`
- `python3 scripts/visual-network-protocol-proof.py`
- `python3 scripts/visual-creds-action-proof.py`
- `python3 scripts/visual-exploit-action-proof.py`
- `python3 scripts/visual-live-cache-stats-proof.py`
- `python3 scripts/visual-chat-proof.py`
- `python3 scripts/visual-chat-interaction-proof.py`
- `python3 scripts/visual-request-audit-proof.py`
- `python3 scripts/visual-osint-screenshot-proof.py`
- `python3 scripts/visual-settings-proof.py`
- `python3 scripts/verify-live-models.py --qwen /Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP --unsupported /Users/eric/models/mlx-community/gemma-3n-E2B-it-4bit --output docs/live-proofs/checkpoint-76-qwen-repeat-cache-live.json`
- `cd ExploitBotEngine && uv run --extra dev ../scripts/prove-block-l2-cache.py --output ../docs/live-proofs/checkpoint-77-block-l2-quantized-proof.json`
- `cd ExploitBotEngine && uv run --extra dev ../scripts/prove-block-l2-cache.py --output ../docs/live-proofs/checkpoint-102-block-l2-partial-proof.json`
- `cd ExploitBotEngine && uv run --extra dev ../scripts/prove-ssm-rederive-status.py --output ../docs/live-proofs/checkpoint-103-ssm-rederive-status-proof.json`
- `git diff --check`
- Static scans proving no S/M/L profile selectors or `ModelProfile` code remain
  are covered by `scripts/app-qa-matrix-smoke-proof.py`; the same proof verifies
  required context hooks and the TestServer `/state`, `/messages`, and
  `/results` smoke contract through `/state.qaCoverage`. It also now verifies
  that `/state.qaCoverage` advertises the shared AppState subtab proof gates for
  Recon, Web, Network, Creds, Exploit, Post, OSINT, and Report, and checks the
  machine-readable `/qa/subtab-coverage` route against the live subtab registry.
  That aggregate now exposes `proofCount` plus `/qa/tool-subtab` and
  `/qa/visual-subtab` route coverage for state and visual subtab switching.
  The same matrix also checks `/qa/agent-loop-coverage` for manual suggestion,
  copilot approval, autopilot execution, and deployed-agent forced-autopilot
  inheritance coverage. It also checks the agent action telemetry fields needed
  to prove deploy-sheet, task-send, progress, and status behavior. It now also
  checks `/qa/tool-flow-coverage`, which ties
  the tool registry, parser routing, representative family fanout, and
  context-catalog tool-output proofs into one auditable contract. It now lists
  the parser and family-fanout fixture seed routes as part of that contract.
  The aggregate also exposes `proofCount` and `stateKeys` for machine-readable
  proof accounting.
  Runtime and cache invariants are also summarized through
  `/qa/runtime-coverage`, including
  Qwen/MiniMax support, parser autodetect, model-folder generation defaults,
  prefix-cache/L2/TurboQuant response mode, unsupported-start blocking, and
  live-proof cache gates. The aggregate now exposes `proofCount` plus the
  model-folder, engine-start, new-context, settings cache seed, and live cache
  seed routes that back those contracts. It also exposes checked-in live proof
  artifact paths for MiniMax replay/no-thinking and Qwen hybrid replay,
  full-prefix-skip, and catalogue-prefix-shape gates, plus
  `liveProofArtifactCount` for matrix-level artifact accounting. Dynamic context and catalogue
  invariants are now summarized through `/qa/context-coverage`, including the
  `search_context` retrieval tool, the fixed automatic context-injection cap,
  current effective snippet limit, context seed/query QA routes, bounded
  catalogue injection, request-audit persistence, parsed result-to-context
  routing, deployed-agent context search, durable embeddings, stash retrieval,
  and new-context cache preservation proof gates. It now exposes `proofCount`
  and `/context/new` so cache-preserving context resets stay visible in the
  aggregate, plus `stateKeys` for context audit surfaces. Tab action coverage
  also exposes `actionStateKeys`, so the matrix
  can verify the AppState surfaces behind per-tab copy/stash/export/tool
  actions. Visual screenshot coverage is summarized through
  `/qa/visual-coverage`, including chat/tool states, scroll lock, Settings,
  context inspector, request-audit badges, tab activity, subtab lifecycle
  strips, OSINT screenshots, report export, stash retrieval, unsupported model
  states, post attribution, tool action panels, live cache stats, and
  CVE/tool-settings proof manifests. The aggregate exposes `proofCount`,
  `manifestCount`, minimum capture count, and `actualCaptureCount` so visual
  proof breadth is machine-checkable. It also lists the visual QA seed/switch
  routes used by the screenshot proofs.
  Chat/control invariants are summarized through `/qa/chat-coverage`, including
  streaming usage metrics, token counters, reasoning controls, tool-output
  expansion, approval controls, copy/stash actions, request-audit badges,
  context inspector state, scroll-lock visuals, tool-action/Stash chat control,
  and cache-preserving new-context behavior for the
  `prefix-cache-l2-turboquant` response path. It also exposes `stateKeys` for
  `chatActions`, `chatControlActions`, chat/message storage, request context,
  context-window state, QA chat visual state, stash handoff, and the activity
  feed.
  Session workflow invariants are summarized through `/qa/session-coverage`,
  including onboarding, Sidebar operations, overlays, model-folder pickers,
  persistence, finding-wizard submit, tab switching, phase actions, Activity
  Feed actions, proof-count metadata, and `stateKeys`.
  The aggregate QA map is exposed through `/qa/coverage-index`; it groups app
  state, chat/context, runtime/cache, settings/visuals, tools/parsers, and
  tabs/sessions endpoints with their proof scripts, and
  `scripts/coverage-index-proof.py` verifies every named proof file exists.
  Each group also exposes `endpointCount` and `proofCount` for machine-readable
  coverage accounting. The app-state group also exposes `/state.qaCoverage`
  state-route count, subtab state tab count, subtab state proof count, and the
  `/qa/proof-ledger` proof count across all local proof scripts. It also exposes
  proof category counts for agent, chat, context, runtime, settings, tabs,
  tools, and visual proof surfaces, plus a proof-category surface count consumed
  by the broad app QA matrix and a total category count that must match the
  proof ledger count, including the `other` bucket. It also exposes an explicit
  proof-category parity flag consumed by both the coverage-index proof and the
  broad app QA matrix. It also exposes
  `/qa/artifact-ledger`
  visual manifest and live-proof counts so screenshot and live JSON evidence
  stay machine-auditable, including missing visual capture count.
  `/qa/checkpoint-ledger` exposes checkpoint documentation count,
  completeness count, completion ratio, complete checkpoint paths, incomplete
  checkpoint paths, latest checkpoint, and latest checkpoint number using numeric checkpoint ordering; the checkpoint,
  complete, and incomplete path lists also use that numeric order. The
  `/qa/audit-ledger` route combines proof counts, proof category counts/surface
  names/surface count/total/parity, live artifact counts, visual capture
  counts, missing/failed artifact counts, and checkpoint completeness counts/
  ratio plus the current gap count into one machine-readable audit rollup.
  It also exposes the missing visual capture paths, failed live-proof paths,
  complete and incomplete checkpoint paths, latest checkpoint number, open gap
  IDs, and structured gap contracts directly for triage.
  `scripts/app-qa-matrix-smoke-proof.py`
  now fetches all four ledger routes directly and cross-checks their counts
  against the coverage-index app-state group. The coverage-index app-state
  group also carries `/qa/checkpoint-ledger.checkpointCompletionRatio`, so the
  top-level QA summary reports checkpoint documentation completeness, not just
  checkpoint count. It also carries complete and incomplete checkpoint counts
  from `/qa/checkpoint-ledger`, plus `/qa/checkpoint-ledger.latestCheckpoint`
  and `latestCheckpointNumber`, so the same aggregate identifies the current
  documentation frontier and its completion breakdown. It also carries
  `/qa/audit-ledger.proofCategorySurfaces`, proof-category surface count,
  proof-category total count, and proof-category parity, so the top-level index
  proves the audit rollup is exposing named proof-surface breadth and validated
  all-category accounting, not just total ledger size. It also carries
  `/qa/gap-ledger.openGapIds` and a
  `gapContractCount`, so the top-level QA summary names the remaining gap and
  proves a structured contract exists. `/qa/gap-ledger` reads the
  current-gap section from `docs/app-system-review-2026-05-21.md` and exposes
  the currently documented gap, the Qwen/MiniMax support boundary, the Qwen VL
  block state, `openGapIds`, and the `qwenMultimodalRuntime` contract with
  blocked model kinds plus enforcement proofs. The runtime/cache group
  additionally exposes
  `supportedFamilies`, `cacheResponseMethod`, and `liveProofArtifactCount`, so
  Qwen/MiniMax-only support, the `prefix-cache-l2-turboquant` response path, and
  the checked-in live replay artifacts remain visible from the top-level QA
  index. The settings/visuals group exposes settings visual manifest count, full
  visual manifest count, and actual screenshot capture count. The tools/parsers
  group exposes registry tool count, callback count, representative family
  fanout count, and state-key count. The tabs/sessions group exposes
  interaction-mode count, covered tab count, session state-key count, and
  action-state-key count. Chat/context also exposes state-key count.
- Visual QA through the local app run script plus screenshots.

Required future proof gates:

- Model-folder fixture test: Qwen folder, MiniMax folder, and unsupported folder
  detection. Covered by `testsuite/test_live_model_verifier.py`.
- App-level model-folder warning state: covered by
  `scripts/model-folder-warning-proof.py`, which uses temporary fixtures and
  verifies Qwen/MiniMax support, Qwen VL/multimodal blocking, and unsupported
  parser/cache warning text through `/state.modelFolderInfo`.
- Unsupported folder start-blocking: covered by
  `scripts/unsupported-model-start-proof.py`, which verifies the engine remains
  stopped, `healthStatus=blocked`, and `/state.engineError` explains the
  Qwen/MiniMax-only constraint.
- Engine no-model smoke proving `/health` and `/v1/models` report parser,
  generation, topology, and cache metadata: covered by
  `scripts/engine-no-model-metadata-proof.py`, including the
  `prefix-cache-l2-turboquant` cache-response method and new-context cache
  preservation metadata.
- MiniMax real generation smoke proving full KV attention with prefix hits,
  prompt/block L2 cache metadata, and TurboQuant encode/decode cache stats.
  Current strict live proof at
  `docs/live-proofs/checkpoint-80-minimax-strict-live.json` reaches model load,
  warmup, health, runtime metadata, isolated prompt/block L2 cache roots,
  thinking-enabled MiniMax template kwargs, non-empty first/repeat assistant
  content, and repeat cached-token reuse.
- Qwen hybrid SSM smoke proving KV prefix hits only when companion SSM state is
  present, plus rederive status. Current Qwen live proof verifies load,
  generation, cache metadata, SSM companion L2 storage, and a repeat paged-cache
  hit with 20 cached tokens. Re-derive status is now exposed through
  `/v1/cache/stats` and `/state.engineCacheStats`; checkpoint-103 proves queued
  and completed states without loading a model. Real-model async rederive
  execution remains a separate correctness gate.
- Parsed app-level cache stats visibility: covered by
  `scripts/cache-stats-state-proof.py`, which verifies `/state.engineCacheStats`
  exposes TurboQuant, prompt L2, block L2, SSM companion disk, and cache memory
  counters from the app parser. `scripts/live-cache-stats-ui-proof.py` also
  verifies the parser against checked-in real Qwen and MiniMax live
  `/v1/cache/stats` payloads: Qwen covers prefix reuse and SSM companion disk,
  while MiniMax covers prefix reuse plus prompt L2 and block L2 counters.
- New context-window cache preservation: covered by
  `scripts/context-window-cache-proof.py`, which verifies `/context/new`
  increments `/state.contextWindow.generation`, clears visible chat state and
  chat-local token counters, and preserves the engine config plus parsed cache
  stats for the prefix-cache/L2/TurboQuant response path.
- Visible context/cache header status: covered by
  `scripts/visual-chat-proof.py`, which captures the chat header showing the
  active context generation and cache-preserved status next to live tool,
  reasoning, token, context, and tool-schema states.
- Visible new-context control routing is covered by
  `scripts/chat-control-actions-proof.py`, which verifies the same
  cache-preserving context-window behavior from the AppState control path.
- Quantized block L2 proof: covered by
  `docs/live-proofs/checkpoint-77-block-l2-quantized-proof.json`, which proves
  real MLX safetensors write/read plus full-block disk promotion for
  `quantized_kv` cache data.
- Reasoning parser smoke proving thinking text is separated from visible output:
  covered by `docs/live-proofs/checkpoint-79-parser-api-proof.json`.
- Tool parser smoke proving parsed API `tool_calls`, not raw text only:
  covered by `docs/live-proofs/checkpoint-79-parser-api-proof.json`.
- Settings, per-op messages, and result-store rebuild after app relaunch:
  covered by `scripts/persistence-proof.py`, which seeds an isolated app home
  and verifies a persisted `nmap` tool message reparses into the restored
  `443/https` tab result.
- Per-assistant-turn request context/tool-schema audit persistence: covered by
  `scripts/request-audit-proof.py`, which verifies bounded context and selected
  tool schemas are attached to the assistant turn and survive app relaunch.
- Full tool registry execution/result coverage: covered by
  `scripts/tool-registry-coverage-proof.py`, which verifies all 38 exposed
  schemas have declared execution mode, bounded catalogue policy, tab coverage,
  sample CLI routing, and result parser mode.
- End-to-end external tool fanout: covered by
  `scripts/tool-fanout-status-proof.py`, which proves a model-issued `nmap`
  call produces a chat card, activity feed start/complete entries, Recon tab
  status, parsed `/results` port data, and a retrievable context catalogue item.
- Representative all-family tool fanout: covered by
  `scripts/tool-family-fanout-coverage-proof.py`, which proves Recon/Web/
  Network/Creds/Exploit/Post/OSINT fixture tools each produce a chat card,
  activity entry, tab activity, tab result, and context-catalog hit.
- Representative parser-to-tab routing: covered by
  `scripts/result-parser-routing-proof.py`, which seeds representative outputs
  for structured and raw-only tools, checks all expected parser branches emit
  tab state, and verifies parsed `nmap`/screenshot rows are exposed through
  `/results`.
- Parsed result-to-context routing: covered by
  `scripts/result-context-catalog-proof.py`, which reuses the parser fixture and
  proves parsed credential findings, nmap assets, nuclei CVE findings, and
  post-exploitation attribution rows are retrievable as bounded catalogue
  snippets with non-CVE embedding records.
- Deployed-agent on-demand context retrieval: covered by
  `scripts/agent-search-context-proof.py`, which proves an autonomous agent can
  call `search_context`, retrieve shared parsed-result catalogue facts, and feed
  those facts back into the next model request.
- Settings model warning, engine live cache status, cache topology, CVE/tool
  status, live cache metrics, and split category screenshots are exposed through
  `/qa/settings-coverage.visualManifests`.
- Chat token metrics, active tool header, approval card, running tool card,
  failed tool card, and streaming reasoning state are captured under
  `docs/visual-proofs/checkpoint-71`.
- Chat transcript copy, assistant-message copy, message stash, and
  latest-assistant stash are covered by `scripts/chat-actions-proof.py`.
- Activity Feed header copy, row copy, row copy-with-timestamp, filter changes,
  verbosity changes, copy-visible, and clear actions now route through AppState and expose
  `/state.activityFeedActions` with last action, status, count, summary, and
  clipboard preview. Covered by `scripts/activity-feed-actions-proof.py`.
- Sidebar create, switch, rename, and delete operation actions now route
  through AppState and expose `/state.sidebarActions` with last action,
  operation id/name, count, whether create stopped active generation, and
  summary. Covered by `scripts/sidebar-actions-proof.py` and
  `scripts/sidebar-create-stops-proof.py`.
- Per-turn request-audit badges are captured under
  `docs/visual-proofs/checkpoint-87`.
- Chat scroll locked/paused and reasoning expanded/collapsed states are captured
  under `docs/visual-proofs/checkpoint-72`.
- Tool cancellation state is covered by `scripts/live-turn-harness.py`; the
  harness uses an isolated app data directory and verifies the executor leaves
  running state after stop.
- Tab-bar activity screenshots are captured under
  `docs/visual-proofs/checkpoint-69`.
- Nested lifecycle strip screenshots are captured under
  `docs/visual-proofs/checkpoint-70`.
- OSINT screenshot artifact preview is captured under
  `docs/visual-proofs/checkpoint-90`.
- Report export status and seeded finding state are captured under
  `docs/visual-proofs/checkpoint-91`.
- Stash retrieval audit state is captured under
  `docs/visual-proofs/checkpoint-92`.
- Post-exploitation output attribution is captured under
  `docs/visual-proofs/checkpoint-94`.
- OSINT screenshot artifact actions are captured under
  `docs/visual-proofs/checkpoint-95`.
- OSINT copy actions are covered by `scripts/osint-copy-actions-proof.py`.
- Activity Feed copy and clear actions are covered by
  `scripts/activity-feed-actions-proof.py`.
- Web row context copy/stash actions are covered by
  `scripts/web-row-context-actions-proof.py`.
- Stash row context copy content/label actions are covered by
  `scripts/stash-row-context-actions-proof.py`.
- Web Verify queued/progress state is captured under
  `docs/visual-proofs/checkpoint-96`.
- Recon Full Recon running state is captured under
  `docs/visual-proofs/checkpoint-97`.
- Network Protocol Scan running state is captured under
  `docs/visual-proofs/checkpoint-98`.
- Creds Start Crack done state and CRACKED result badges are captured under
  `docs/visual-proofs/checkpoint-99`.
- Exploit search/prepare/execute stage badges are captured under
  `docs/visual-proofs/checkpoint-100`.
- Real MiniMax live-proof cache metrics parsed into Settings Engine are captured
  under `docs/visual-proofs/checkpoint-101`.
- Unsupported model-folder warning and blocked engine states are captured under
  `docs/visual-proofs/checkpoint-93`.
