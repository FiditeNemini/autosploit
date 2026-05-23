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
- Chat transcript copy, per-message copy, tool-output copy, per-message stash,
  and latest-assistant stash now route through AppState. `/state.chatActions`
  exposes action status, role, count, clipboard preview, and last stash item;
  stash actions update `/state.stashActions` through `recordStashAdd`.
  Covered by `scripts/chat-actions-proof.py`; `/qa/chat-coverage.stateKeys`
  now lists the chat, control, context, visual, stash, and feed state surfaces.
- Chat header reasoning, request-context inspector, and new-context controls
  now route through AppState. `/state.chatControlActions` exposes last action,
  reasoning state, inspector visibility, context generation, and summary;
  covered by `scripts/chat-control-actions-proof.py`.
- Activity Feed copy, filter, verbosity, and clear actions route through AppState.
  `/state.activityFeedActions` exposes status, last action, count, summary, and
  preview/filter/verbosity label; covered by
  `scripts/activity-feed-actions-proof.py`.
- Manual tab switching now routes through AppState instead of only mutating the
  active-tab binding. `/state.tabSwitchActions` exposes from/to tab,
  follow-agent pause state, and summary; covered by
  `scripts/tab-switch-action-proof.py`.
- Phase controls now route through AppState with `/state.phaseActions` exposing
  from/to phase, reset tool count, active phase guidance, and summary; covered
  by `scripts/phase-action-proof.py`.
- Required proof: stream with reasoning on/off, metrics visible after usage,
  manual scroll pause while output streams, relock jump, stop button cancels the
  stream session.

Interaction modes:

- `SidebarView` and onboarding choose `autopilot`, `copilot`, or `manual`.
- Onboarding and Sidebar mode selection share `AppState.selectInteractionMode`
  / `completeOnboarding` wiring, and `/state.modeSelection` exposes available
  mode IDs/labels, selected mode, active op mode, source, onboarding visibility,
  and whether a pending copilot approval was rejected during a mode switch.
- `/qa/session-coverage` aggregates onboarding, Sidebar mode selection,
  pending-approval rejection, sidebar CRUD, create-op stop behavior, overlays,
  model-folder pickers, persistence/relaunch, saved messages, result rebuild,
  finding wizard submit, tab switch actions, phase actions, and Activity Feed
  controls. It also exposes session workflow surface list/count/parity and
  workflow surface proof map/count/parity plus `stateKeys` for the `/state`
  surfaces used by those workflow proofs.
- Autopilot executes model tool calls directly.
- Copilot shows an approval card before tool execution.
- Manual converts model tool calls into suggested commands and stops.
- Agents always run as autopilot after deployment.
- Onboarding/sidebar selection proof is covered by
  `scripts/mode-selection-flow-proof.py`: onboarding creates a manual-mode op
  from a Qwen fixture folder without starting the engine, Sidebar switches the
  active op to autopilot, rejects a seeded pending approval, persists the op
  mode, and records mode-change activity.
- Main-chat mode proof is covered by `scripts/live-turn-harness.py`: the same
  mock tool call executes in autopilot, becomes a suggestion in manual mode, and
  pauses behind an approval card in copilot before execution.
- Deployed-agent autopilot proof is covered by
  `scripts/agent-autopilot-proof.py`: a typed Web agent inherits the mock engine
  connection, model-folder generation-default policy, loop limit, reasoning
  setting, context catalogue wiring, prompt-ranked tool schemas, and typed
  prompt override, then autonomously runs a `search_cve` tool loop to
  completion.
- Agent header/settings actions are covered by `scripts/agent-actions-proof.py`:
  deploy, switch, remove, and clear actions route through AppState and expose
  `/state.agentActions` with agent id/name/type, count, task-send/message-count
  telemetry, summary, and activity. Deploy task-send telemetry is covered by
  `scripts/agent-deploy-task-send-proof.py`.
- Agent Settings controls are covered by
  `scripts/agent-settings-actions-proof.py`: multi-agent enable/disable and
  max-concurrent changes route through AppState, persist settings, update
  `/state.agentActions`, and clear active agents when disabling full-auto
  multi-agent mode.
- `/qa/agent-loop-coverage` now exposes the agent route list, contract flags,
  action telemetry field list, proof count, deploy-sheet/task-send proof
  references, loop-phase list/count/parity, and phase-to-proof map/count/parity
  so the full agentic-loop surface is auditable from one aggregate endpoint.
- Deployed-agent on-demand context retrieval is covered by
  `scripts/agent-search-context-proof.py`: an agent autonomously calls
  `search_context`, receives shared parsed-result catalogue facts from the main
  session, and sends that tool result back into the next model request.

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
- Non-CVE catalogue records are durably embedded with a deterministic local
  vector signature in `catalogEmbeddings` for assets, findings, raw tool output,
  and stash items. The selected sources for each automatic context packet are
  persisted on the assistant turn through `messages.contextSelections`, so later
  audits can see what was retrieved without replaying the ranker.
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
- Durable non-CVE catalogue embedding and assistant-turn retrieval selection
  persistence are covered by `scripts/catalog-embedding-audit-proof.py`.
- `/qa/context-coverage.stateKeys` ties that aggregate back to
  `/state.contextCatalog`, `/state.requestContext`, `/state.contextWindow`,
  `/state.catalogEmbeddings`, `/state.stashRetrieval`, `/state.cveSemantic`,
  and persisted message context/tool-schema audits.
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

- `ToolDefinitions.forModel()` exposes 38 prompt-ranked tool schemas, with
  built-in callbacks always visible and external tools selected by prompt/tab
  relevance.
- `ToolDefinitions.buildCliArgs(...)` maps parsed model tool calls to CLI
  binaries/arguments.
- Built-ins `search_context`, `search_cve`, and `lookup_cve` route to app
  callbacks instead of subprocesses.
- External tools route through `ToolExecutor.execute(...)`.
- Full registry coverage is exposed through `/qa/tool-coverage` and covered by
  `scripts/tool-registry-coverage-proof.py`: every model-visible tool has an
  execution type, tab ownership unless intentionally global, CLI routing sample,
  structured-vs-raw result mode, and a standard `ok` aggregate status.

Result fanout:

- `ChatService` appends tool cards.
- `onToolStart` logs activity, increments phase tool count, and auto-switches
  tabs through `AppState.tabForTool(...)`.
- `onToolComplete` logs success/failure and duration.
- `onToolResult` feeds `ResultsStore.ingest(...)`.
- `ResultsStore` parses known tool output into tab state and fires auto-CVE
  callbacks for service versions and CVE IDs.
- End-to-end fanout for a model-issued external tool call is covered by
  `scripts/tool-fanout-status-proof.py`: a mock model calls `nmap`, a fake
  binary returns service output, and the proof verifies the chat tool card,
  recent activity-feed entries, Recon tab status, parsed `/results` port, and
  context-catalog retrieval.
- Representative all-family fanout is covered by
  `scripts/tool-family-fanout-coverage-proof.py`: deterministic Recon, Web,
  Network, Creds, Exploit, Post, and OSINT fixtures each prove a visible chat
  tool card, activity-feed entry, tab activity status, parsed tab result, and
  context-catalog hit. `/qa/tool-flow-coverage.stateKeys` ties that aggregate to
  message tool cards, tab activity, activity feed, result rows, and context
  catalogue state. `/qa/tool-flow-coverage.tabActivityStatuses` names the
  visible tab indicator states (`running`, `done`, `failed`, `canceled`) and
  exposes status count/parity plus the `status-dot-running-ring` indicator
  contract. It also exposes tab activity status proof map/count/parity, tying
  each status to its proof scripts. It also exposes `toolVisualSurfaces`,
  `toolVisualSurfaceCount`, and
  `toolVisualSurfaceParity`, plus visual-surface proof map/count/parity, for
  chat tool cards, activity-feed status, tab status indicators, parsed result
  rows, context-catalog hits, and expandable tool output. Parser and
  family-fanout aggregate routes now also
  expose a standard `ok` status, covered by
  `scripts/parser-fanout-aggregate-proof.py`.
- Activity Feed copy and clear controls now route through AppState. The header
  copy, row copy, row copy-with-timestamp, copy-visible, and clear actions
  expose `/state.activityFeedActions` with last action, status, count, summary,
  and clipboard preview. Covered by `scripts/activity-feed-actions-proof.py`.
- Representative parser routing is covered by
  `scripts/result-parser-routing-proof.py`: it seeds outputs for structured
  recon, web, network, creds, exploit, post, OSINT, screenshot, and raw-only
  tools, then verifies parsed tab collections plus `/results` exposure.
- Parsed-result context retrieval is covered by
  `scripts/result-context-catalog-proof.py`: it reuses the parser fixture and
  proves parsed credentials, nmap assets, nuclei findings, and post-exploitation
  attribution rows are searchable catalogue items with persisted non-CVE
  embeddings.
- Required proof: each tool family can produce a visible chat card, activity
  entry, tab result, and context-catalog item from representative output. Covered
  by `scripts/tool-family-fanout-coverage-proof.py`.

## Page And Button Coverage

Recon:

- Buttons: Full Recon, Crawl, OSINT/theHarvester, copy controls.
- Chat path: run buttons record a Recon action state, then send the generated
  prompt to chat.
- State: subdomains, ports, web hosts, crawl URLs from `ResultsStore`, plus
  `/state.reconAction` for the latest Full Recon/Crawl/Harvest action and
  `/state.reconCopyActions` for the latest copy operation.
- Recon action status is covered by `scripts/recon-action-status-proof.py`: a
  seeded Full Recon records target, generated command, running status, and Recon
  tab activity with `lastTool=full_recon`.
- Recon copy controls are covered by `scripts/recon-copy-actions-proof.py`: the
  proof seeds subdomains, ports, web hosts, crawl URLs, and OSINT rows, then
  verifies each copy path records clipboard preview, count, kind, and Recon tab
  activity with `lastTool=copy_recon`.
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
- State: web hosts, vulns, CVE lookup details, queued Verify action state, and
  `/state.webDirectActions` for Create Finding/Stash/Copy/Search Related CVEs
  labels, finding prefill, stash count/preview, clipboard preview, and queued
  related-CVE prompt.
- Direct Web action coverage is handled by
  `scripts/web-direct-actions-proof.py`: it seeds an Apache CVE finding,
  opens the finding wizard with prefilled fields, stashes the finding, copies
  the finding text, queues a related CVE search through chat, and verifies Web
  tab activity exposes `search_related_cve`. Header Copy for the filtered web
  list routes through AppState and is covered by
  `scripts/web-header-copy-proof.py`.
- Web row context-menu copy actions for title, target, and details now route
  through AppState and `/state.webDirectActions`; context-menu stash updates
  both Web direct-action state and `/state.stashActions`. Covered by
  `scripts/web-row-context-actions-proof.py`.
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
  protocol scan, `/state.networkCopyActions` for the latest copy operation, and
  long-running lifecycle state for Capture/MITM/Tunnel.
- Protocol Scan action state is covered by
  `scripts/network-protocol-action-proof.py`: a seeded SMB netexec scan records
  target, protocol, credential context, generated command, running status, and
  Network tab activity with `lastTool=netexec`.
- Visible Protocol Scan running state is captured under
  `docs/visual-proofs/checkpoint-98`.
- Network copy controls are covered by `scripts/network-copy-actions-proof.py`:
  the proof seeds protocol host rows, SNMP rows, capture output, MITM output,
  and tunnel output, then verifies each copy path records clipboard preview,
  count, kind, and Network tab activity with `lastTool=copy_network`.
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
  latest hash-cracking action, `/state.credsCopyActions` for the latest copy
  operation, and `/results.creds` rows with CRACKED/BRUTE/SECRET/CRED badges.
- Hash-cracking action/result state is covered by
  `scripts/creds-action-results-proof.py`: a seeded hashcat result set records
  target, generated haiti/hashcat command, done status, result count, Creds tab
  activity with `lastTool=hashcat`, and CRACKED result badges.
- Visible Start Crack done state and credential result badges are captured under
  `docs/visual-proofs/checkpoint-99`.
- Creds copy controls are covered by `scripts/creds-copy-actions-proof.py`: the
  proof seeds cracked hashcat results, a Hydra brute-force finding, and a
  TruffleHog secret finding, then verifies Cracking, Online Brute, Secrets, and
  Vault copy paths record clipboard preview, count, kind, and Creds tab
  activity with `lastTool=copy_creds`.
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
  search/prepare/execute stage history, plus `/state.exploitCopyActions` for
  the latest copy operation.
- Search/prepare/execute differentiation is covered by
  `scripts/exploit-action-differentiation-proof.py`: seeded state records
  SEARCH done with `metasploit`, PREPARE done with `manual_plan`, EXECUTE
  running with `run_shell`, and Exploit tab activity with `lastTool=execute`.
- Visible SEARCH/PREPARE/EXECUTE stage badges are captured under
  `docs/visual-proofs/checkpoint-100`.
- Exploit copy controls are covered by `scripts/exploit-copy-actions-proof.py`:
  the proof seeds Metasploit output, reverse-shell templates, custom script
  lifecycle state, and Sliver output, then verifies each copy path records
  clipboard preview, count, kind, and Exploit tab activity with
  `lastTool=copy_exploit`.
- Listener, custom script, and implant lifecycle state now tracks idle, running,
  done, failed, and canceled and is visible in the relevant Exploit subtab.
- Live UI screenshot coverage for Reverse Shells, Custom, and C2 lifecycle
  strips is captured by `scripts/visual-tab-proof.py`.

Post:

- Buttons: Run LinPEAS, impacket Run, Pivot.
- Chat path: sends prompts to chat.
- State: raw post-exploitation output, network hosts, and structured
  per-host/session output attribution, plus `/state.postCopyActions` for the
  latest copy operation.
- Privilege escalation, AD/impacket, and lateral movement lifecycle state now
  tracks idle, running, done, failed, and canceled and is visible in the
  relevant Post subtab.
- Live UI screenshot coverage for PrivEsc, AD Attacks, and Lateral lifecycle
  strips is captured by `scripts/visual-tab-proof.py`.
- Post copy controls are covered by `scripts/post-copy-actions-proof.py`: the
  proof seeds LinPEAS output, impacket output, a compromised lateral host, and
  attribution rows, then verifies PrivEsc, AD Attacks, Lateral, and Attribution
  copy paths record clipboard preview, count, kind, and Post tab activity with
  `lastTool=copy_post`.
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
- Copy controls for username, email, metadata, screenshots, and all OSINT rows
  now route through `AppState.recordOSINTCopy`; `/state.osintCopyActions`
  exposes copied kind, row count, clipboard preview, and summary, with tab
  activity marked as `copy_osint`. Covered by
  `scripts/osint-copy-actions-proof.py`.
- Screenshot artifact path validation and preview metadata are covered by
  `scripts/osint-screenshot-artifact-proof.py`; visible preview state is
  captured under `docs/visual-proofs/checkpoint-90`.
- Screenshot artifact row actions are covered by
  `scripts/osint-artifact-actions-proof.py`: artifact rows expose open, reveal,
  and copy-path actions when the file exists, and `/state.osintArtifactAction`
  tracks status, summary, last action, validated path, byte count, and action
  history. `/state.osintArtifacts[*].actionLabels` exposes the user-facing row
  action labels.
- Visible artifact action controls are captured under
  `docs/visual-proofs/checkpoint-95`.

Report:

- Buttons: Generate, PDF, Markdown, Create Finding, delete finding.
- Chat path: report generation is direct app code, not model-driven.
- State: findings, generated report output, `/state.reportRenderActions` for
  visible Generate, last export status/artifacts, and
  `/state.reportFindingActions` for Create Finding/Delete finding labels,
  wizard visibility, current row metadata, and last created/deleted IDs.
- Visible Generate coverage is handled by
  `scripts/report-generate-action-proof.py`: it seeds a deterministic finding,
  runs the AppState generate path, and verifies generated HTML size/preview,
  finding count, and activity-feed state.
- Create/delete finding action coverage is handled by
  `scripts/report-finding-actions-proof.py`: it starts from an empty Report
  page, opens the finding wizard, submits a deterministic confirmed finding,
  verifies the row delete action label, deletes the row, and checks Report tab
  activity exposes `delete_finding` completion. Visible Report row delete
  wiring is covered by `scripts/report-visible-delete-wiring-proof.py`, which
  prevents the delete button from bypassing AppState. The visible finding
  wizard submit button now routes through AppState and is covered by
  `scripts/finding-wizard-submit-proof.py`.
- Render/export artifact validation is covered by
  `scripts/report-export-proof.py`: it seeds a deterministic critical finding,
  exports HTML, Markdown, JSON, and PDF into a QA directory, validates paths,
  bytes, expected content markers, and `%PDF`, and exposes the metadata through
  `/state.reportExport`.
- Visible PDF/Markdown export button coverage is handled by
  `scripts/report-visible-export-actions-proof.py`: it drives the AppState
  export action route for both toolbar actions, verifies generated artifact
  metadata through `/state.reportExport`, and checks activity-feed visibility.
- Visible report export state is captured under
  `docs/visual-proofs/checkpoint-91`.

Stash:

- Buttons: filters, search, add, copy, send to chat, delete.
- Chat path: send-to-chat injects bounded stash content into the active chat.
  It routes through AppState chat-control send telemetry; covered by
  `scripts/stash-send-chat-control-proof.py`.
- State: persisted stash rows, query-scored context catalogue source, and
  `/state.stashActions` for Filter/Add/Copy All/Copy/Send/Delete labels, item
  rows, active filter, filtered count, clipboard preview, last action, and last
  item/deleted IDs.
- Row context-menu Copy Content and Copy Label now route through the same
  AppState copy handler and update `/state.stashActions`; covered by
  `scripts/stash-row-context-actions-proof.py`.
- Stash action coverage is handled by `scripts/stash-actions-proof.py`: it
  seeds a stash row, adds a deterministic item, filters rows, copies all rows,
  copies one row, sends one row into chat with the bounded stash-content path,
  deletes that row, and verifies Stash tab activity exposes `delete_stash`
  completion.
- Aggregate per-tab direct action coverage is exposed through
  `/qa/tab-action-coverage` and verified by
  `scripts/tab-action-coverage-proof.py`, which checks the route, action seed/
  action route list, copy/export/agent seed routes, contracts, focused proof
  scripts, covered tabs, tab action surface list/count/parity, tab action
  surface proof map/count/parity, action-state keys, and proof file existence.
- Aggregate chat/control coverage is exposed through `/qa/chat-coverage` and
  verified by `scripts/chat-coverage-proof.py`, which checks Send/Stop,
  reasoning, approval, copy/stash, tool-output expansion, request-audit,
  context inspector, scroll-lock visual, token counter, tool-action/Stash chat
  handoff, visible cache-session header badges, header badge proof
  map/count/parity, cache-session field proof map/count/parity, and
  cache-preserving visible-new-context contracts for the
  `prefix-cache-l2-turboquant` response path. The broad app QA matrix also
  checks the chat cache badge list, count, parity, proof count, and proof
  parity.
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
- Split Settings category/page coverage is exposed through
  `/state.settingsCategoryCoverage` and covered by
  `scripts/settings-category-coverage-proof.py`, which verifies all Settings
  pages can be selected through the QA route and have title/subtitle/detail/icon
  and page-section metadata.
- `/qa/settings-coverage` aggregates Settings category structure, supported
  model-family warnings, parser/generation autodetect, cache-response method,
  app-only apply, engine Start/Stop actions, context/cache/agent controls,
  CVE/tool/log action coverage, visual Settings proof scripts, and proof-count
  metadata. It also exposes Settings surface list/count/parity for engine/model/
  runtime, context/cache, agents, CVEs, tools, inference logs, and visual status
  proofs, plus Settings surface proof map/count/parity. It now also exposes the checked-in Settings visual manifest paths and
  `visualManifestCount` for matrix-level visual accounting.
- App-only settings can now be applied without restarting the engine; model,
  cache, and engine runtime changes still use Apply & Restart Engine.
- App-only apply is covered by `scripts/settings-apply-proof.py`.
- Settings engine Start/Stop actions expose `/state.settingsEngineActions` with
  previous/current running state, model label, health status, and summary.
  Stop action coverage is handled by `scripts/settings-engine-actions-proof.py`.

## QA Matrix Required For Completion

Automated no-model gates:

- Swift build.
- Engine pytest.
- Static scans for removed zombie profile code and required context hooks via
  `scripts/app-qa-matrix-smoke-proof.py`.
- TestServer `/state`, `/messages`, `/results` smoke via
  `scripts/app-qa-matrix-smoke-proof.py`; `/state.qaCoverage` exposes the
  profile-removal, context-hook, route-coverage, and shared subtab-state proof
  contract. `/qa/subtab-coverage` exposes the live registry/default/active
  subtab state, subtab QA routes, and proof-count metadata for audit.
  `/qa/agent-loop-coverage` exposes manual, copilot,
  autopilot, deployed-agent loop guarantees, agent action/settings/deploy
  routes, deploy-sheet/task-send controls, action telemetry fields, and the
  agent-loop state-key list/count plus visual state keys for active agent
  chat/results/feed routing, context snippets, exposed tool-schema audit state,
  loop-phase list/count/parity, and phase-proof map/count/parity. `/qa/tool-flow-coverage` exposes the registry/parser/fanout/
  context-catalog proof contract for model-issued tool calls, including the
  parser, tool-catalog, and family-fanout fixture seed routes, proof-count
  metadata, `stateKeys`, tool-schema cap/policy/route, structured/raw
  result-mode counts, plus the visible tab activity status count/parity and
  indicator contract. The broad app QA matrix also checks that tab activity
  status contract.
  `/qa/runtime-coverage` exposes the runtime/model/cache proof contract for
  Qwen/MiniMax support, parser autodetect, model-folder generation defaults,
  prefix-cache/L2/TurboQuant response mode, unsupported-start blocking, the
  runtime route list, proof-count metadata, runtime cache component
  list/count/parity, runtime cache component proof map/count/parity, and
  checked-in live proof artifact paths for Qwen/MiniMax replay, prefix-skip,
  no-thinking, and catalogue-shape gates, plus
  `liveProofArtifactCount` for top-level matrix assertions.
  `/qa/context-coverage` exposes the dynamic context proof contract for bounded
  catalogue injection, `search_context`, request-audit persistence, parsed
  result-to-context routing, deployed-agent retrieval, durable embeddings,
  targeted stash retrieval, new-context cache preservation, the `/context/new`
  route, proof-count metadata, `stateKeys`, and retrieval source
  list/count/parity plus retrieval-source proof map/count/parity for the
  context audit surfaces. It also exposes `contextDeliveryModes`,
  `contextDeliveryModeCount`, and
  `contextDeliveryModeParity`, plus delivery-mode proof map/count/parity, so
  automatic bounded injection, on-demand `search_context`, persisted turn audit,
  durable embeddings, and active-scope stash retrieval are visible as separate
  anti-context-flooding paths tied to concrete proof scripts.
  `/qa/visual-coverage` exposes screenshot-backed UI proof coverage for chat,
  scroll lock, Settings, context inspector, request-audit badges, tab activity,
  subtab lifecycle strips, OSINT screenshots, reports, stash retrieval,
  unsupported models, post attribution, tool action panels, live cache stats,
  CVE/tool settings pages, visual surface list/count/parity, visual surface
  proof map/count/parity, visual manifests, capture-count minimums, and
  proof-count metadata, plus the QA routes used to seed or switch each visual
  proof state.
  `/qa/session-coverage` exposes cross-app session workflow proof coverage for
  onboarding/mode selection, Sidebar operations, overlays, model-folder pickers,
  persistence/relaunch, saved messages, result rebuild, finding wizard submit,
  tab switching, phase changes, and Activity Feed controls, and lists the
  `/phase`, `/qa/seed-activity-actions`, and `/qa/activity-action` routes with
  proof-count metadata, session workflow surface list/count/parity, workflow
  surface proof map/count/parity, plus `stateKeys`.
  `/qa/tab-action-coverage` exposes per-tab direct action proof coverage for
  copy buttons, row context actions, verify/protocol/hash/exploit/post/OSINT
  actions, report generation/finding/export/agent actions, Stash controls, and
  the seed routes behind those focused proofs, including OSINT screenshot
  artifact setup. It also exposes tab action surface list/count/parity and
  tab action surface proof map/count/parity plus `actionStateKeys`, tying the aggregate to the
  `/state` surfaces each proof validates.
  `/qa/chat-coverage` exposes chat/control proof coverage for streaming usage
  metrics, token counters, reasoning controls, approval controls, tool-output
  expansion, request-audit badges, context inspector state, scroll-lock visuals,
  tool-action/Stash chat handoff, visible cache-session header badges, header
  badge proof map/count/parity,
  `cacheResponsesInferenceMethod`, `newModelSessionBehavior`, cache-session
  field list/count/parity, cache-session field proof map/count/parity, and cache-preserving new-context
  behavior for the `prefix-cache-l2-turboquant` response path. It also exposes `stateKeys`
  for `chatActions`, `chatControlActions`, chat/message storage, request
  context, context-window state, QA chat visual state, stash handoff, and the
  activity feed.
  `/qa/coverage-index` exposes the aggregate QA map across app state,
  chat/context, runtime/cache, settings/visuals, tools/parsers, and tabs/
  sessions; `scripts/coverage-index-proof.py` verifies each group has endpoint
  and proof counts, endpoint lists, proof lists, and existing proof files. The
  tabs/sessions group mirrors the visible tab activity status list/count/parity
  plus indicator contract from tool-flow coverage. The app-state group also
  exposes `/state.qaCoverage` state-route
  list/count, context hook list/count, subtab state tab list/count, subtab
  state proof list/count, and the
  `/qa/proof-ledger` proof count, source proof-ledger category counts/category
  surfaces, source proof-ledger category map, source category-surface count,
  category other count, category total count, and category parity across all local proof scripts. It also exposes proof category counts
  and normalized surface names for agent, chat, context, runtime, settings,
  tabs, tools, and visual proof surfaces, plus a direct
  `/qa/proof-ledger` category counts/surfaces/surface-count/other-count/total/parity
  rollup, proof-category surface count consumed by the broad app QA matrix, and a total
  category count that must match the proof ledger count, including the `other`
  bucket, and mirrors the source proof-ledger `other` count as
  `proofLedgerCategoryOtherCount`. It also exposes an explicit proof-category parity flag consumed by
  both the coverage-index proof and the broad app QA matrix. It also exposes
  `/qa/audit-ledger` source proof-ledger category other count, so the audit
  rollup preserves the same uncategorized proof accounting as the source ledger.
  It also exposes
  `/qa/artifact-ledger`
  visual manifest and live-proof counts so screenshot and live JSON evidence
  stay machine-auditable, including missing visual capture count.
  The chat/context group mirrors `/qa/chat-coverage.headerCacheBadges`,
  `headerCacheBadgeCount`, `headerCacheBadgeParity`,
  `headerCacheBadgeProofCount`, `headerCacheBadgeProofParity`,
  `cacheSessionIndicator`, and `newContextSessionBoundary`, plus
  `cacheResponsesInferenceMethod`,
  `newModelSessionBehavior`, cache-session field list/count/parity, cache-session
  field proof map/count/parity, and it
  mirrors `/qa/context-coverage` retrieval source list/count/parity plus
  retrieval source proof map/count/parity and context delivery mode
  list/count/parity plus delivery proof map/count/parity, so
  the aggregate coverage map carries the same visible cache-session and bounded
  dynamic-context source contracts as the detailed endpoints.
  `/qa/checkpoint-ledger` exposes checkpoint documentation count,
  completeness count, completion ratio, complete checkpoint paths, incomplete
  checkpoint paths, latest checkpoint, and latest checkpoint number using numeric checkpoint ordering; the checkpoint,
  complete, and incomplete path lists also use that numeric order. The
  `/qa/audit-ledger` route combines proof counts, source proof-ledger category
  counts/surfaces/surface-count/total/parity, proof category counts/surface
  names/surface count/total/parity, live artifact counts, visual capture
  counts, missing/failed artifact counts, and checkpoint completeness counts/
  ratio plus the current gap count into one machine-readable audit rollup.
  It also exposes the missing visual capture paths, failed live-proof paths,
  complete and incomplete checkpoint paths, latest checkpoint number, gap
  source/path flags, current-gap list, supported-family list,
  unsupported-multimodal block flag, open gap IDs, and structured gap contracts
  directly for triage.
  `scripts/app-qa-matrix-smoke-proof.py`
  now fetches all four ledger routes directly and cross-checks their counts
  against the coverage-index app-state group. The coverage-index app-state
  group also carries `/qa/checkpoint-ledger.checkpointCompletionRatio`, so the
  top-level QA summary reports checkpoint documentation completeness, not just
  checkpoint count. It also carries complete and incomplete checkpoint counts
  and path lists from `/qa/checkpoint-ledger`, plus
  `/qa/checkpoint-ledger.checkpoints`, `/qa/checkpoint-ledger.latestCheckpoint`,
  and `latestCheckpointNumber`, so the same aggregate identifies the current
  documentation frontier and its completion breakdown. It also carries
  `/qa/artifact-ledger.visualManifests`, `/qa/artifact-ledger.liveProofs`, and
  `/qa/artifact-ledger.liveProofStatus`, plus
  `/qa/artifact-ledger.visualCaptureCount`,
  `/qa/artifact-ledger.visualCaptureStatus`, `liveProofOkCount`,
  `missingVisualCaptures`, `failedLiveProofCount`, and `failedLiveProofs`, so the aggregate preserves
  artifact evidence paths and pass/fail status instead of only artifact counts.
  It also carries
  `/qa/audit-ledger.proofCount`, source proof-ledger category counts/surfaces/
  surface-count/category-map/other-count/total/parity, normalized
  proof-category counts, proof-category surface names/surface count,
  proof-category total count, and proof-category parity, so the top-level index
  proves the audit rollup is exposing named proof-surface breadth and validated
  all-category accounting, not just total ledger size. It also carries
  `/qa/audit-ledger` artifact, checkpoint, and current-gap rollup counts, so the
  same top-level QA index cross-checks audit totals against source ledger
  domains. It also carries audit missing-capture, complete/incomplete
  checkpoint, checkpoint completion ratio, latest checkpoint path/number, gap
  source/path, current-gap, open-gap, next-gap, supported-family,
  unsupported-multimodal block, gap-contract lists/maps, and the audit-owned
  `gapContractCount` surfaced as `auditGapContractCount`, so audit detail is not
  reduced to counts while the audit contract count remains machine-checkable in
  the aggregate. It also carries
  `/qa/audit-ledger.liveProofOkCount`, `failedLiveProofCount`, and
  `failedLiveProofs`, so failed live JSON evidence remains visible from the
  top-level QA index. It also carries
  `/qa/audit-ledger.proofLedgerCategoryOtherCount` as
  `auditProofLedgerCategoryOtherCount`, and the broad app QA matrix cross-checks
  both source and audit `other` proof counts through `/qa/coverage-index`. It also carries
  `/qa/gap-ledger.openGapIds`, `openGapCount`, `gapContracts`,
  `gapContractCount`, Qwen multimodal blocked-kind count, required-work count,
  and enforcement-proof count, plus gap source/path flags, current-gap list, next-gap
  text, supported-family list, and unsupported-multimodal block flag, so the
  top-level QA summary names the remaining gap and preserves both the
  source-derived warning boundary and the structured contract map. `/qa/gap-ledger` reads this
  document's current-gap section and exposes the currently documented gap, the
  Qwen/MiniMax support boundary, the Qwen VL block state, `openGapIds`,
  `openGapCount`, and the `qwenMultimodalRuntime` contract with blocked model kinds plus count fields for blocked kinds, required runtime work, and enforcement
  proofs, including a dedicated Qwen multimodal engine-start block proof. The
  runtime/cache group also exposes `supportedFamilies`,
  `cacheResponseMethod`, `cacheResponsesInferenceMethod`,
  `newModelSessionBehavior`, runtime contract map/count, route list/count,
  proof list/count, cache component list/count/parity, cache component
  proof map/count/parity, live proof family matrix, and live proof artifact
  map/count for Qwen/MiniMax-only support, the
  `prefix-cache-l2-turboquant` response path, cache-preserving new-context
  boundary, and the checked-in Qwen/MiniMax
  live replay artifact set. The chat/context group exposes chat route
  list/count, contract map/count, proof list/count/file parity, state-key list/count,
  context search tool name, automatic/current injection caps, context route
  list/count, contract map/count, proof list/count/file parity, state-key list/count,
  retrieval-source proof map/count/parity, and delivery-mode proof
  map/count/parity. The settings/visuals group exposes Settings surface
  list/count/parity, Settings surface proof map/count/parity, visual surface list/count/parity,
  Settings category list/count/current category, Settings route list/count,
  contract map/count, proof list/count/file parity, settings visual manifest list/count,
  visual surface proof map/count/parity, visual route list/count, contract
  map/count, proof list/count, visual manifest list/count, minimum capture
  count, and actual screenshot capture count. The
  tools/parsers group exposes registry tool
  count, callback count, always-visible tool count, bounded catalogue limit,
  registry tab list, full registry tool list, registry failure list/count,
  representative family fanout count and family-to-tool map, structured/raw
  parser tool sets, seeded result-parser counts, parsed
  structured tool list, raw-only preserved tool list, representative
  result-parser artifact lists for subdomains, URLs, vulnerability
  sources/titles, ports, network hosts, OSINT platforms, post labels, and raw
  tools, parser failure list/count, state-key count, tool-flow proof count,
  route-owned proof list/file parity, tool/callback counters, route
  list/count, family list/count, state-key list, contract map/count,
  dynamic tool-schema cap/policy/route, structured/raw result-mode counts,
  tab activity status proof map/count/parity, and model-tool visual surface
  list/count/parity plus proof map/count/parity from `/qa/tool-flow-coverage`.
  The tabs/sessions group exposes
  interaction-mode count, covered tab
  count, session state-key count, subtab tab maps and proof count,
  session route list/count, contract map/count, proof list/count/file parity, state-key
  list/count,
  session workflow surface list/count/parity,
  session workflow surface proof map/count/parity,
  tab action tab list, route list/count, contract map/count, proof list/count/file parity,
  action-state-key list/count,
  tab action surface list/count/parity, tab action surface proof map/count/parity,
  action-state-key count, agent-loop
  state-key list/count, agent-loop visual state keys, agent-loop phase-proof
  map/count/parity, agent-loop current mode, max-iteration guard, proof count/list/file parity,
  visual-state-key count, mode behavior/count, deployed-agent inheritance/status
  contract/count, route-owned route list/count, route-owned contract flags/count,
  route-owned action telemetry field list/count, and tab activity status proof count/parity. Chat/context
  also exposes state-key count.
- Full tool-registry coverage via `scripts/tool-registry-coverage-proof.py`.
- Representative tool-output parser routing via
  `scripts/result-parser-routing-proof.py`.
- Parsed result-to-context retrieval via `scripts/result-context-catalog-proof.py`.
- Model tool fanout status via `scripts/tool-fanout-status-proof.py`.
- Representative all-family fanout via
  `scripts/tool-family-fanout-coverage-proof.py`.
- Engine no-model metadata via `scripts/engine-no-model-metadata-proof.py`,
  proving `/health` and `/v1/models` share parser, generation, topology,
  prefix/cache L2, TurboQuant, SSM companion, and cache-response method fields.
- Context catalogue seeded-state smoke.
- Context catalogue source inclusion/exclusion and active-op stash scoping via
  `scripts/context-catalog-proof.py`.
- Settings category split-page coverage via
  `scripts/settings-category-coverage-proof.py`.
- Aggregate Settings QA contract via `scripts/settings-coverage-proof.py`.
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
  - proves Web CVE rows expose per-row progress/enrichment status through
    `/state.webCVERows` and the visible card chip;
  - proves Report can queue an agent-draft prompt from confirmed findings
    through `/state.reportAction` and Report tab activity;
  - proves CVE Database settings expose import/count/search status through
    `/state.cveDatabase`;
  - proves CVE Database Quick Import, Full Sync, Search, and custom-save
    controls route through AppState and expose `/state.cveSettingsActions`;
  - proves Tools settings expose installed/missing/installing/error status
    through `/state.toolSettings`;
  - proves Tools settings Refresh, Install, and Install All Missing controls
    route through AppState and expose `/state.toolSettingsActions`;
  - proves Inference Log copy/clear routes through AppState and expose
    `/state.inferenceLogActions`;
  - proves Chat send, stop, approve, reject, and clear/new-context controls
    route through AppState and expose `/state.chatControlActions`;
  - proves AppState tool-action prompt queues route through chat-control send
    telemetry instead of bypassing it;
  - proves terminal, settings, and finding-wizard overlay actions route through
    AppState and expose `/state.windowOverlayActions`;
  - proves model-issued `search_context` returns targeted catalogue facts;
  - proves automatic context injection stays at 4 snippets or fewer and tells
    the model to use `search_context` for more targeted retrieval;
  - proves web-tab tool schemas are query bounded and do not include unrelated
    OSINT/exploit schemas in the request body;
  - proves `/state.requestContext` exposes whether context was injected, how
    many snippets were selected, and which tool schemas were exposed;
  - proves `/state.catalogEmbeddings` exposes durable non-CVE catalogue vectors
    and assistant turns persist bounded selected-source retrieval audits;
  - proves the expandable chat request-context inspector can show the bounded
    context packet preview and exposed tool schema names;
  - proves semantic CVE mode invokes the embedder path when stored embeddings
    are available and exposes semantic state through `/state.cveSemantic`;
  - proves prefix cache, prompt L2, paged cache, block L2, TurboQuant Q4, and
    model-folder generation defaults remain enabled in runtime config;
  - proves the new-context route clears chat state and token/cached counters
    without changing model or cache defaults;
  - proves `/state.contextWindow` increments the visible context generation and
    reports the preserved prefix-cache/L2/TurboQuant cache-response path;
  - proves the chat header surfaces that context generation and cache-preserved
    state in the visual chat screenshot;
  - proves `search_cve` tool calls execute under autopilot;
  - proves manual mode converts tool calls into suggestions;
  - proves copilot mode pauses for approval and executes after approval.
  - proves `/qa/agent-loop-coverage` names the model/tool loop phases from user
    prompt through dynamic context, schema selection, streaming, mode/scope
    policy, execution, result storage, and loop re-entry, with each phase mapped
    to concrete proof scripts.
  - proves a deployed typed agent runs in forced autopilot, inherits runtime
    defaults, uses bounded dynamic context/tool schemas, preserves its type
    prompt override, executes a tool, and completes autonomously through
    `scripts/agent-autopilot-proof.py`.
  - proves a deployed agent can use `search_context` to pull parsed main-session
    catalogue facts into its own autonomous tool loop through
    `scripts/agent-search-context-proof.py`.

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
- Web CVE row progress. Covered by `scripts/web-verify-action-proof.py` and
  `scripts/visual-web-verify-proof.py`, which verify row-level CVE id,
  enrichment, active `CVE verifying` progress, and visible queued card state.
- Report agent-draft loop. Covered by `scripts/report-agent-action-proof.py`
  and `scripts/visual-report-agent-proof.py`, which verify the report prompt,
  queued action state, Report tab activity, and visible agent-report status
  strip.
- CVE settings status. Covered by `scripts/cve-settings-status-proof.py` and
  `scripts/visual-cve-settings-status-proof.py`, which verify deterministic
  import progress, total/KEV counts, last sync, search-result count, and visible
  CVE Database settings state.
- Tools settings status. Covered by `scripts/tool-settings-status-proof.py` and
  `scripts/visual-tool-settings-status-proof.py`, which verify deterministic
  installed/missing/installing/error counts, per-tool rows, and install log.
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
  are accepted, Qwen VL/multimodal fixtures expose `isMultimodal=true` and are
  blocked as not yet supported, and an unsupported fixture exposes the required
  Qwen/MiniMax parser/cache warning through `/state.modelFolderInfo`.
- Unsupported folder start-blocking is covered by
  `scripts/unsupported-model-start-proof.py`: an unsupported fixture cannot
  start the engine, `engineRunning` remains false, `/state.engineError` carries
  the Qwen/MiniMax blocking message, and `healthStatus` becomes `blocked`.
- Qwen multimodal/VL start-blocking is covered by
  `scripts/qwen-multimodal-start-proof.py`: a Qwen VL/JANGTQ fixture keeps
  `family=Qwen`, exposes `isMultimodal=true`, remains unsupported, leaves the
  engine stopped, sets `healthStatus=blocked`, and reports the multimodal-not-yet-supported
  error instead of applying text-only parser/cache assumptions.
- Engine no-model metadata is covered by
  `scripts/engine-no-model-metadata-proof.py`: a fixture-backed no-model Qwen
  hybrid server reports `status=no_model`; `/health.effective_config` and
  `/v1/models[].metadata` agree on parser autodetect, generation defaults and
  provenance, hybrid SSM topology, prefix cache, prompt L2, paged cache, block
  L2, TurboQuant Q4, SSM companion L2, and the
  `prefix-cache-l2-turboquant` response method used for long-context sessions.
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
- Partial-block block L2 proof is captured at
  `docs/live-proofs/checkpoint-102-block-l2-partial-proof.json`. The same
  direct MLX proof now writes, reopens, and promotes both a full 4-token
  quantized KV block and a 3-token final partial block with `disk_writes=2`,
  `disk_hits=2`, and empty remaining prompts for both.
- SSM re-derive status proof is captured at
  `docs/live-proofs/checkpoint-103-ssm-rederive-status-proof.json`. It proves
  the hybrid SSM companion path records queued and completed rederive states,
  scheduler cache stats include the `rederive` object, and the Swift app parser
  exposes the same counters through `/state.engineCacheStats`.
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
- Prefix/L2/cache metrics visibility is script-checkable after real engine load,
  and the Settings UI now has a real-cache-payload visual proof. `scripts/live-cache-stats-ui-proof.py`
  replays checked-in Qwen and MiniMax live `/v1/cache/stats` payloads into the
  app parser: Qwen proves prefix reuse plus SSM companion disk counters, and
  MiniMax proves prefix reuse plus prompt L2 and block L2 counters. The visual
  Settings capture is generated from the MiniMax strict live-proof payload by
  `scripts/visual-live-cache-stats-proof.py`.
- Full-block block L2 quantized write/read/promotion is covered by
  `scripts/prove-block-l2-cache.py`; a full real-model cross-run block L2 hit
  remains open.
- New-context reset semantics are covered by `scripts/live-turn-harness.py` and
  `scripts/context-window-cache-proof.py`: the mock-engine app clears chat plus
  prompt/completion/cached counters while preserving prefix, prompt L2, paged,
  block L2, TurboQuant Q4, model-folder generation-default flags, and parsed
  engine cache stats. `/state.contextWindow` exposes the context generation and
  `prefix-cache-l2-turboquant` response method marker, explicit cache-response
  inference method, new-context session boundary, and new-model-session behavior.
  The visible header route is covered by `scripts/chat-control-actions-proof.py`.
- Chat-panel visual context/cache status is covered by
  `scripts/visual-chat-proof.py`, which seeds a running cache-ready engine state
  and captures the `ctx N`, `cache preserved`, `prefix/l2/tq`, and
  `new ctx keeps cache` header indicators through `/state.qaChatVisual.headerBadges`
  and the checkpoint-71 screenshot.
- Parsed engine cache runtime counters are exposed through
  `/state.engineCacheStats` and covered by `scripts/cache-stats-state-proof.py`
  plus `scripts/live-cache-stats-ui-proof.py` for TurboQuant, prefix-cache
  hits/tokens saved, prompt L2, block L2, SSM companion disk, and memory
  counters.
- MiniMax real-model restart replay is covered by
  `scripts/verify-live-models.py --restart-replay` and
  `docs/live-proofs/checkpoint-110-minimax-restart-replay-live.json`: the first
  process writes prompt/block L2 entries, the second process reloads the same
  cache root, and the replay request reports 55 cached prompt tokens plus
  `disk_cache.hits=1`.
- MiniMax real-model block-L2-only restart replay is covered by
  `scripts/verify-live-models.py --block-l2-only-replay` and
  `docs/live-proofs/checkpoint-111-minimax-block-l2-restart-replay-live.json`:
  prompt L2 is disabled, the first process writes two block L2 entries, and the
  replay process reports 64 cached prompt tokens, `block_disk_cache.disk_hits=1`,
  and `scheduler_cache.tokens_saved=64`.
- Qwen hybrid real-model block-L2 replay plus SSM re-derive fallback is covered
  by `scripts/verify-live-models.py --block-l2-only-replay
  --require-ssm-rederive` and
  `docs/live-proofs/checkpoint-112-qwen-hybrid-block-l2-ssm-restart-replay-live.json`:
  prompt L2 is disabled, the replay process reports `block_l2_hits_delta=1`
  and `scheduler_tokens_saved_delta=64`, then records SSM re-derive
  `requested=true`, `completed=true`, `reason=missing_companion`, and no
  failures.
- Qwen hybrid full prefix skip is covered by
  `scripts/verify-live-models.py --block-l2-only-replay
  --require-ssm-companion-hit` and
  `docs/live-proofs/checkpoint-113-qwen-hybrid-full-prefix-skip-live.json`:
  prompt L2 is disabled, replay reports `block_l2_hits_delta=2`,
  `ssm_l2_hits_delta=1`, `scheduler_tokens_saved_delta=112`, `cached_tokens=112`,
  and no rederive fallback.
- Qwen hybrid catalogue/tool-schema prompt shape is covered by the same verifier
  mode and
  `docs/live-proofs/checkpoint-115-qwen-hybrid-catalogue-prefix-shape-live.json`:
  prompt L2 is disabled, the replay process restores the longer dynamic-context
  prefix through block L2 plus SSM companion L2 with `block_l2_hits_delta=3`,
  `ssm_l2_hits_delta=1`, `scheduler_tokens_saved_delta=168`,
  `cached_tokens=168`, and no rederive fallback.
- MiniMax forced no-thinking API output is covered by
  `scripts/verify-live-models.py --enable-thinking false` and
  `docs/live-proofs/checkpoint-114-minimax-no-thinking-live.json`: the request
  explicitly sends `enable_thinking=false`, the response has non-empty
  assistant `content`, no `reasoning_content`, model-folder generation/parser
  metadata, TurboQuant Q4 KV metadata, prefix/paged/prompt-L2/block-L2 cache
  metadata, and repeat prompt reuse with `cached_tokens=51`.
- Reasoning/tool parser API shaping is covered by
  `scripts/prove-parser-api.py` and `testsuite/test_tool_parser_api.py`.
- Responses API continuation storage is covered by
  `ExploitBotEngine/testsuite/test_responses_session_store.py`, including a
  parent -> child -> grandchild chain that proves stored child responses carry
  the fully resolved ancestor context into the next `previous_response_id`
  request.
- Settings/message/result-store persistence is covered by
  `scripts/persistence-proof.py`.
- Per-turn request context/tool-schema audit persistence is covered by
  `scripts/request-audit-proof.py`.

Visual gates:

- Settings model warning, engine live cache status, and cache topology sections
  are captured under `docs/visual-proofs/checkpoint-73`.
- CVE Database import/status state is captured under
  `docs/visual-proofs/checkpoint-108`.
- Tools install/detection status state is captured under
  `docs/visual-proofs/checkpoint-109`.
- Chat scroll locked, paused/new-output, and relock-ready states are captured
  under `docs/visual-proofs/checkpoint-72`.
- Aggregate screenshot-backed UI proof coverage is exposed through
  `/qa/visual-coverage` and verified by `scripts/visual-coverage-proof.py`,
  which checks the route, required visual proof scripts, required manifests,
  listed capture artifact existence, visual surface list/count/parity, visual
  surface proof map/count/parity, and `actualCaptureCount`.
- Settings-specific screenshot-backed UI proof coverage is also exposed through
  `/qa/settings-coverage.visualManifests` and verified by
  `scripts/settings-coverage-proof.py`.
- The top-level `/qa/coverage-index.groups.settingsAndVisuals` aggregate now
  rolls up Settings surface list/count/parity, Settings surface proof
  count/parity, visual surface list/count/parity, visual surface proof
  count/parity, settings visual manifest count, full visual manifest count, and
  actual screenshot capture count for matrix-level proof accounting.
- Chat control action state for reasoning, context inspector, and new context
  is covered by `scripts/chat-control-actions-proof.py`.
- Chat copy/stash action state is covered by `scripts/chat-actions-proof.py`.
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
- Real live-proof cache metrics parsed into the Settings Engine tab are captured
  under `docs/visual-proofs/checkpoint-101`.
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
- OSINT copy action state for username/email/metadata/screenshots/all rows is
  covered by `scripts/osint-copy-actions-proof.py`.
- Web row context copy/stash action state is covered by
  `scripts/web-row-context-actions-proof.py`.
- Stash row context copy content/label action state is covered by
  `scripts/stash-row-context-actions-proof.py`.
- Activity Feed copy-entry/copy-timestamp/copy-visible/clear state is covered
  by `scripts/activity-feed-actions-proof.py`.
- Sidebar create/switch/rename/delete operation actions route through AppState
  and expose `/state.sidebarActions`; covered by
  `scripts/sidebar-actions-proof.py`. The sidebar create path also routes
  active generation stop through AppState before creating the new op; covered
  by `scripts/sidebar-create-stops-proof.py`.
- Web Verify queued/progress state is captured under
  `docs/visual-proofs/checkpoint-96`.
- Recon Full Recon running state is captured under
  `docs/visual-proofs/checkpoint-97`.
- Remaining visual gap: none currently listed here; real live-proof cache
  metrics UI state is covered by checkpoint-101. Fresh real-model UI attachment
  can still be rerun when the user wants an expensive full-load screenshot.

## Current Gaps To Close Next

1. Add the real Qwen multimodal runtime path and prefix-cache key discipline
   once the app intentionally promotes a multimodal Qwen model into the
   supported beta lane. Until then, Qwen VL folders are detected but blocked.
