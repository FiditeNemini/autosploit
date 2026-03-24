# exploitbot — Feature Cross-Links & Integration Points

Every connection between services/views that must exist for features to work.

## Currently Wired ✅

| From | To | How | Status |
|------|----|-----|--------|
| ChatService | EngineManager | `chatService.baseURL = engineManager.baseURL` | ✅ |
| ChatService → tool_calls | ToolExecutor | `toolExecutor.execute()` in tool call loop | ✅ |
| ChatService → tool results | ResultsStore | `onToolResult` callback → `resultsStore.ingest()` | ✅ |
| ChatService → tool start | ActivityFeed | `onToolStart` callback → `activityFeed.logToolStart()` | ✅ |
| ChatService → tool complete | ActivityFeed | `onToolComplete` callback → `activityFeed.logToolComplete()` | ✅ |
| ChatService → thinking | ActivityFeed | `onThinking` callback → `activityFeed.logThinking()` | ✅ |
| ChatService → tool start | AppState.activeTab | Auto-tab switching via `tabForTool()` | ✅ |
| Chat "📦 Stash" button | StashService | `onStash` callback → `stashService.stash()` | ✅ |
| Stash "→ Send" button | ChatService | `onSendToChat` callback → `chatService.send()` | ✅ |
| Settings | EngineManager | `startEngine()` / `stopEngine()` | ✅ |
| Settings | EngineConfig | `saveEngineConfig()` / `loadEngineConfig()` | ✅ |
| Op switching | ChatService | `saveCurrentMessages()` / `loadMessages()` | ✅ |
| Op switching | AppState.interactionMode | Mode loaded from Op | ✅ |
| Onboarding | EngineConfig | Saves model path | ✅ |
| Onboarding | Op creation | Creates first Op | ✅ |
| ResultsStore | Recon/Web/Network/OSINT/Report tabs | `@Bindable var resultsStore` | ✅ |

## NOT Wired Yet ❌ (needed for upcoming phases)

### Stash gaps (Phase A incomplete)
| From | To | What's needed | Priority |
|------|----|---------------|----------|
| Tool output in chat | StashService | "Stash this" on tool_call messages → stash the output | HIGH |
| Activity feed entries | StashService | "Stash" button on feed items | MEDIUM |
| ResultsStore vulns | StashService | "Stash" button on vuln cards in Web tab | MEDIUM |
| ResultsStore hosts | StashService | "Stash" button on host rows in Recon/Network tabs | MEDIUM |
| Auto-stash in Autopilot | StashService | Model creates stash items during autonomous operation | LOW |

### Finding gaps (Phase B — not built)
| From | To | What's needed | Priority |
|------|----|---------------|----------|
| FindingService | SQLite (findings table) | CRUD operations — table exists in schema | HIGH |
| Web tab vuln cards | FindingService | "Create Finding" button → wizard modal | HIGH |
| Post tab results | FindingService | "Create Finding" button → wizard modal | HIGH |
| StashService items | FindingService | "Promote to Finding" on stash items | MEDIUM |
| Chat messages | FindingService | Right-click → "Create Finding" | MEDIUM |
| FindingService | Report tab | Findings list from DB, not sample data | HIGH |
| FindingService → attack chain | ChatService messages | Auto-reconstruct from Op conversation | MEDIUM |

### Copilot gaps (Phase C — not built)
| From | To | What's needed | Priority |
|------|----|---------------|----------|
| ChatService tool_calls | Approval system | When mode==.copilot, don't auto-execute | HIGH |
| Approval card approve | ToolExecutor | Execute the pending tool | HIGH |
| Approval card reject | ChatService | Send rejection to model | HIGH |
| AppState.interactionMode | ChatService behavior | Autopilot=auto, Copilot=approve, Manual=no tools | HIGH |

### Report gaps (Phase D — not built)
| From | To | What's needed | Priority |
|------|----|---------------|----------|
| FindingService | Report template | All findings → HTML template | HIGH |
| Report template | WKWebView | Render HTML → preview | HIGH |
| WKWebView | PDF export | `createPDF()` | HIGH |
| EngineConfig (branding) | Report template | Company name, logo, header | MEDIUM |

### Engine gaps
| From | To | What's needed | Priority |
|------|----|---------------|----------|
| EngineManager | App quit | Kill engine on app termination | HIGH |
| EngineManager crash | Auto-restart | Detect crash → restart engine | MEDIUM |
| EngineManager | Orphan detection | On app launch, check PID file for stale process | MEDIUM |

---

## Data Flow Diagrams

### Chat → Tool → Results → Tabs
```
User types message
  → ChatService.send()
    → POST /v1/chat/completions (SSE stream)
      → delta.content → message bubble
      → delta.reasoning_content → thinking block
      → delta.tool_calls → ToolExecutor.execute()
        → subprocess runs tool
        → stdout → onToolResult → ResultsStore.ingest()
          → Recon tab: subdomains table
          → Web tab: vuln cards
          → Network tab: host table
          → OSINT tab: platform results
        → onToolStart → ActivityFeed.logToolStart()
        → onToolComplete → ActivityFeed.logToolComplete()
      → tool result sent back to model
      → model continues (may call more tools)
```

### Stash Flow
```
Source → StashService.stash() → SQLite stash_items → StashTabView

Sources:
  - Chat "📦 Stash" button → last assistant message
  - [TODO] Tool output card → stash tool output
  - [TODO] Vuln card → stash vulnerability info
  - [TODO] Host row → stash host/IP info
  - [TODO] Manual "+ Add" → user pastes content
  - [TODO] Autopilot → model auto-stashes interesting artifacts

Destinations:
  - Stash "→ Send" → inserts into chat as user message
  - [TODO] Stash "→ Finding" → opens Finding wizard
  - [TODO] Drag to tool input → fills parameter
```

### Engine Lifecycle
```
App launch
  → Check app.onboarded setting
    → No: show OnboardingView
      → User picks model, creates Op
      → completeOnboarding() → startEngine()
    → Yes: load saved EngineConfig
      → [TODO] Auto-start engine if model path set

Settings → Apply & Restart
  → saveEngineConfig()
  → stopEngine() → EngineManager.stop() → SIGTERM
  → startEngine() → EngineManager.start()
    → spawn launch.py --model <path> --port <port>
    → health check polling (120s)
    → chatService.baseURL = engineManager.baseURL
```
