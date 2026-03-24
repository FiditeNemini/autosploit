# exploitbot — Data Flow & Component Wiring Map

**Last updated:** 2026-03-24
**Swift files:** 33
**Lines:** ~4,504

---

## Service Dependency Graph

```
User Input (ChatInputField)
    │
    ▼
ChatService.send(text)
    │
    ├──► SSE stream to vMLX engine (localhost:{port}/v1/chat/completions)
    │       ├── delta.content → messages[].content (streaming)
    │       ├── delta.reasoning_content → messages[].thinking (streaming, collapses after)
    │       └── delta.tool_calls → accumulated, parsed on [DONE]
    │
    ├──► Tool Call Loop (up to 20 iterations)
    │       │
    │       ├── [Copilot mode] → Approval card shown → waits for user
    │       │                     ├── Approve → continues
    │       │                     └── Reject → skips tool, model notified
    │       │
    │       ├── ToolDefinitions.buildCliArgs(name, args) → (binary, [args])
    │       │
    │       ├── ToolExecutor.execute(binary, args)
    │       │       ├── Process() with argument array
    │       │       ├── stdout streaming → currentOutput
    │       │       ├── stderr captured
    │       │       └── Returns ToolResult (stdout, stderr, exitCode, duration)
    │       │
    │       ├──► Callbacks fired:
    │       │       ├── onToolStart(name, cmd) ──► ActivityFeed.logToolStart()
    │       │       │                          ──► Auto-tab tracking (followAgent)
    │       │       ├── onToolComplete(name, ok, dur, summary) ──► ActivityFeed.logToolComplete()
    │       │       └── onToolResult(name, output) ──► ResultsStore.ingest()
    │       │
    │       └── Tool result fed back to model as [Tool Result: name] user message
    │
    └──► onThinking(text) ──► ActivityFeed.logThinking()
```

## ResultsStore → Tab View Mapping

```
ResultsStore.ingest(toolName, output)
    │
    ├── "subfinder" → subdomains: [SubdomainEntry]
    │                    └──► ReconTabView (Subdomains subtab)
    │
    ├── "httpx"     → webHosts: [WebHostEntry]
    │                    └──► ReconTabView (Web Hosts subtab)
    │
    ├── "nmap"      → ports: [PortEntry]
    │                    └──► ReconTabView (Ports subtab)
    │
    ├── "nuclei"    → vulns: [VulnEntry]
    │                    ├──► WebTabView (vulnerability cards)
    │                    └──► ReportTabView (findings list)
    │
    ├── "sherlock"  → osintResults: [OSINTEntry]
    │                    └──► OSINTTabView (platform results)
    │
    └── all tools   → rawResults: [(tool, output, timestamp)]
                         └──► Available for any tab to access
```

## Auto-Tab Tracking Map (AppState.tabForTool)

```
Tool Name                → ToolTab
─────────────────────────────────────
subfinder, dnsx, nmap,   → .recon
masscan, httpx, katana,
theHarvester

nuclei, sqlmap, dalfox,  → .web
feroxbuster, ffuf, arjun,
wpscan, testssl,
graphqlmap, jwt_tool

netexec, snmpwalk,       → .network
tshark, bettercap, chisel

hashcat, hydra, haiti,   → .creds
trufflehog

metasploit, pwncat,      → .exploit
pwntools, sliver

linpeas, winpeas,         → .post
impacket

sherlock, holehe,         → .osint
exiftool, gowitness

run_shell, search_cve    → nil (stay on current tab)
```

## Database Schema → Swift Usage

```
Table: ops
  ├── AppState.createOp() → INSERT
  ├── AppState.loadOps() → SELECT all, map to [Op]
  ├── AppState.deleteOp() → DELETE (cascades messages)
  └── AppState.updateOpStatus() → UPDATE status

Table: messages
  ├── AppState.saveCurrentMessages() → DELETE old + INSERT all current
  ├── AppState.loadMessages() → SELECT by opId, map to [ChatMessage]
  └── AppState.deleteMessages() → DELETE by opId

Table: stashItems
  ├── StashService.stash() → INSERT via Database.saveStashItem()
  ├── StashService.load() → SELECT all via Database.fetchStashItems()
  └── StashService.delete() → DELETE via Database.deleteStashItem()

Table: findings
  ├── (Not yet wired — other agent building FindingWizard)
  └── Schema: id, opId, title, vulnType, severity, cvssScore, target,
      description, attackChain, evidence, impact, remediation, status, cveId

Table: settings
  ├── AppState.loadEngineConfig() → getSetting(key) for each engine param
  ├── AppState.saveEngineConfig() → setSetting(key, value) for each param
  └── Keys: engine.modelPath, engine.reasoningParser, engine.toolCallParser,
      engine.kvCacheQuantization, engine.temperature, engine.maxTokens
```

## Interaction Mode Flow

```
Sidebar mode selector
    │
    ├── state.interactionMode = mode
    ├── state.chatService.interactionMode = mode
    └── state.activityFeed.logModeChange(mode.label)

ChatService.runConversationLoop():
    │
    ├── mode == .autopilot
    │       └── Tools execute immediately, no gating
    │
    ├── mode == .copilot
    │       ├── Show approval card (ChatMessage.approval)
    │       ├── Set pendingApproval + approvalContinuation
    │       ├── await withCheckedContinuation (pauses loop)
    │       ├── User clicks Approve → approveToolCall() resumes with .approve
    │       └── User clicks Reject → rejectToolCall() resumes with .reject
    │
    └── mode == .manual
            └── (Not implemented — currently same as autopilot)
            └── TODO: should not auto-invoke tools, chat only
```

## Engine Lifecycle

```
App Launch
    └── AppState.init()
            ├── loadEngineConfig() from DB settings
            ├── Wire callbacks (onToolResult, onToolStart, etc.)
            └── If onboarding complete:
                    └── startEngine() → EngineManager.start(config)
                            ├── findPython() → /opt/homebrew/bin/python3
                            ├── findAvailablePort() → 8100-8199
                            ├── Process(launch.py --model X --port Y)
                            ├── waitForHealth() → poll /health every 1s
                            ├── chatService.baseURL = engineManager.baseURL
                            └── startHealthMonitor() → ping every 5s

Settings → Apply & Restart
    └── saveEngineConfig() → DB
            └── stopEngine() → start again with new config

App Quit
    └── saveCurrentMessages()
            └── engineManager.stop() → SIGTERM → 3s → SIGINT
```

## View → Service Dependencies

| View | Services Used | Data Consumed |
|------|--------------|---------------|
| ContentView | AppState (all) | Routes to tabs, shows settings/onboarding |
| SidebarView | AppState.ops, .interactionMode, .chatService | Op list, mode selector |
| TabBarView | AppState.activeTab | Tab selection |
| ChatPanelView | ChatService | messages, isStreaming, approve/reject |
| ActivityFeedView | ActivityFeed | entries, filters, verbosity |
| ReconTabView | ResultsStore | subdomains, ports, webHosts |
| WebTabView | ResultsStore | vulns |
| NetworkTabView | ResultsStore | networkHosts (empty — no parser yet) |
| OSINTTabView | ResultsStore | osintResults |
| ReportTabView | ResultsStore | vulns (as findings proxy) |
| StashTabView | StashService | items, filtered, search |
| CredsTabView | (none) | Local @State only |
| ExploitTabView | (none) | Empty state |
| PostExploitTabView | (none) | Empty state |
| SettingsView | AppState (engineManager, engineConfig) | Engine status, config |
| OnboardingView | AppState | Language, model path, first Op |

## ToolDefinitions Coverage

| Tool | JSON Schema | Swift Schema | CLI Builder | ResultsStore Parser |
|------|------------|-------------|-------------|-------------------|
| subfinder | ✅ | ✅ | ✅ | ✅ |
| dnsx | ✅ | ✅ | ✅ | ❌ |
| nmap | ✅ | ✅ | ✅ | ✅ |
| masscan | ✅ | ❌ | ❌ | ❌ |
| httpx | ✅ | ✅ | ✅ | ✅ |
| katana | ✅ | ✅ | ✅ | ❌ |
| theHarvester | ✅ | ❌ | ❌ | ❌ |
| nuclei | ✅ | ✅ | ✅ | ✅ |
| sqlmap | ✅ | ✅ | ✅ | ❌ |
| dalfox | ✅ | ✅ | ✅ | ❌ |
| feroxbuster | ✅ | ✅ | ✅ | ❌ |
| ffuf | ✅ | ❌ | ❌ | ❌ |
| arjun | ✅ | ❌ | ❌ | ❌ |
| wpscan | ✅ | ❌ | ❌ | ❌ |
| testssl | ✅ | ❌ | ❌ | ❌ |
| graphqlmap | ✅ | ❌ | ❌ | ❌ |
| jwt_tool | ✅ | ❌ | ❌ | ❌ |
| netexec | ✅ | ❌ | ❌ | ❌ |
| snmpwalk | ✅ | ❌ | ❌ | ❌ |
| tshark | ✅ | ❌ | ❌ | ❌ |
| bettercap | ✅ | ❌ | ❌ | ❌ |
| chisel | ✅ | ❌ | ❌ | ❌ |
| hashcat | ✅ | ✅ | ✅ | ❌ |
| hydra | ✅ | ✅ | ✅ | ❌ |
| haiti | ✅ | ❌ | ❌ | ❌ |
| trufflehog | ✅ | ❌ | ❌ | ❌ |
| metasploit | ✅ | ❌ | ❌ | ❌ |
| pwncat | ✅ | ❌ | ❌ | ❌ |
| pwntools | ✅ | ❌ | ❌ | ❌ |
| sliver | ✅ | ❌ | ❌ | ❌ |
| linpeas | ✅ | ❌ | ❌ | ❌ |
| winpeas | ✅ | ❌ | ❌ | ❌ |
| impacket | ✅ | ❌ | ❌ | ❌ |
| sherlock | ✅ | ✅ | ✅ | ✅ |
| holehe | ✅ | ✅ | ✅ | ❌ |
| exiftool | ✅ | ❌ | ❌ | ❌ |
| gowitness | ✅ | ❌ | ❌ | ❌ |
| search_cve | ✅ | ✅ | ❌ (builtin) | ❌ |
| run_shell | ✅ | ✅ | ✅ | ❌ |

**Summary:** 39 JSON schemas, 15 Swift schemas, 15 CLI builders, 5 parsers
