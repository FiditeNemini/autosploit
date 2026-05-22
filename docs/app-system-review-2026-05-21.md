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
- OpenAI-compatible `tools` still sends the full function schema to the engine.

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
- Automatic context injection is capped to 4 snippets. Settings stores a bounded
  maximum, but routine model turns stay lean and rely on `search_context` for
  deeper retrieval.
- Required proof: prompt with seeded assets/stash/CVEs injects only configured
  top snippets; disabling a source removes that source; semantic CVE mode calls
  the embedder when available.

Storage:

- Ops, messages, settings, stash, findings, and CVEs persist through
  `DatabaseManager`.
- ResultsStore state is session-ephemeral and rebuilt from tool output, not from
  stored chat history.
- Required proof: settings persist across relaunch; messages persist per op;
  context catalogue uses active session state and does not leak inactive op
  state.

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
- Chat path: all run buttons call `onRunCommand`, then `ContentView.sendToChat`.
- State: subdomains, ports, web hosts, crawl URLs from `ResultsStore`.
- Missing proof: tab-level running/progress/error badges tied to tool callbacks.

Web:

- Buttons: scan target, create finding, stash vuln, verify placeholder, CVE
  details, related CVE search.
- Chat path: scan/related CVE routes through chat; finding/stash are direct app
  state actions.
- Verify now routes through chat with a focused prompt containing target,
  finding title, source, CVE, and description for minimal safe evidence
  collection.
- State: web hosts, vulns, CVE lookup details.
- Missing work: visual proof for Verify and tool progress badges.

Network:

- Buttons: Scan, SMB shares/users/sessions/SAM/LSA/whoami, SNMP Walk, Start
  Capture, Start MITM, Create Tunnel.
- Chat path: every action sends a prompt to chat.
- State: network hosts plus raw output.
- Long-running lifecycle state now tracks capture/MITM/tunnel status as idle,
  running, done, failed, or canceled and is visible inside the relevant Network
  subtab.
- Missing proof: live UI screenshot coverage for the lifecycle strip.

Creds:

- Buttons: Start Crack, Brute Force, Scan Secrets.
- Chat path: sends prompts to chat.
- State: parsed credential/hash/secret findings.
- Cracking, brute force, and secret scan lifecycle state now tracks idle,
  running, done, failed, and canceled and is visible in the relevant Creds
  subtab.
- Missing proof: live UI screenshot coverage for the Creds lifecycle strips.

Exploit:

- Buttons: Search, Start Listener, Run Script, Generate Implant, Sliver listener.
- Chat path: sends prompts to chat.
- State: raw metasploit/sliver/session output.
- Listener, custom script, and implant lifecycle state now tracks idle, running,
  done, failed, and canceled and is visible in the relevant Exploit subtab.
- Missing proof: live UI screenshot coverage for the Exploit lifecycle strips.

Post:

- Buttons: Run LinPEAS, impacket Run, Pivot.
- Chat path: sends prompts to chat.
- State: raw post-exploitation output and network hosts.
- Missing proof: per-host/session status and output attribution.

OSINT:

- Buttons: Search for username/email/metadata/screenshot.
- Chat path: sends prompts to chat.
- State: parsed OSINT rows and screenshots.
- Missing proof: file path validation and screenshot artifact preview.

Report:

- Buttons: Generate, PDF, Markdown, Create Finding, delete finding.
- Chat path: report generation is direct app code, not model-driven.
- State: findings and report output.
- Missing proof: render/export artifact validation in automated QA.

Stash:

- Buttons: filters, search, add, copy, send to chat, delete.
- Chat path: send-to-chat injects bounded stash content into the active chat.
- State: persisted stash rows plus context catalogue source.
- Missing proof: source/op scoping and catalogue inclusion/exclusion tests.

Settings:

- Model folder only; Qwen/MiniMax warning.
- Runtime autodetect for generation/parser/cache.
- Context catalogue settings.
- Cache budgets/topology.
- Agent count/mode settings.
- CVE database and tool installer panels.
- Missing work: split engine restart from app-only Apply where possible.

## QA Matrix Required For Completion

Automated no-model gates:

- Swift build.
- Engine pytest.
- Static scans for removed zombie profile code and required context hooks.
- TestServer `/state`, `/messages`, `/results` smoke.
- Context catalogue seeded-state smoke.
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
  - proves tool callbacks update per-tab activity state that the tab bar can
    render as running/done/failed/canceled indicators;
  - proves model-issued `search_context` returns targeted catalogue facts;
  - proves automatic context injection stays at 4 snippets or fewer and tells
    the model to use `search_context` for more targeted retrieval;
  - proves prefix cache, prompt L2, paged cache, block L2, TurboQuant Q4, and
    model-folder generation defaults remain enabled in runtime config;
  - proves the new-context route clears chat state without changing model or
    cache defaults;
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
- Context packet observed in the outbound request body. Covered by
  `scripts/live-turn-harness.py`.
- Per-tab tool activity state. Covered by `scripts/live-turn-harness.py` for
  the Web/CVE path; visual screenshot coverage still needed.

Real-model gates:

- Qwen supported folder load.
- MiniMax supported folder load.
- Unsupported folder warning and blocked/clear error handling.
- Full prompt -> context catalogue -> stream -> tool call -> tab result loop.
- Prefix/L2/cache metrics visible when engine reports cached tokens.

Visual gates:

- Settings model and context sections.
- Chat scroll locked, paused, and relocked states.
- Reasoning expanded, streaming, collapsed, and manually reopened.
- Token metrics bar.
- Tool approval card, running tool card, failed tool card.
- Tab action running/progress/done/error states.

## Current Gaps To Close Next

1. Add visual screenshot coverage for per-tab tool action indicators.
2. Add test fixtures for context catalogue source inclusion/exclusion.
3. Split app-only Settings apply from engine restart.
4. Add live model verification scripts for Qwen and MiniMax folders.
