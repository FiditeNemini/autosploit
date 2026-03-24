# exploitbot — Implementation Status

**Last updated:** 2026-03-24
**Total feature matrix items:** 1,307
**Swift source files:** 29
**Lines of Swift:** ~3,252

---

## What's Built & Working

### App Shell (SwiftUI)
| Component | File | Status | Notes |
|-----------|------|--------|-------|
| App entry | `App/ExploitBotApp.swift` | ✅ Working | macOS 14+, dark mode, .app bundle with Info.plist |
| Window | ContentView.swift | ✅ Working | HStack: Sidebar + (TabBar + Workspace + ChatPanel) |
| Color theme | `Theme/Colors.swift` | ✅ Working | 17 colors: bg-deep→bg-surface, borders, text scale, 7 accents |
| Font system | `Theme/Fonts.swift` | ✅ Working | Monospace at 9-13pt sizes |

### Sidebar
| Component | Status | Notes |
|-----------|--------|-------|
| Brand header (exploitbot logo) | ✅ | Bot emoji + monospace wordmark |
| New Op button (+) | ✅ Visual | Not wired to creation flow yet |
| Ops label | ✅ | |
| Ops list (4 sample ops) | ✅ Working | Click to switch active Op |
| Op status dots (green/amber/gray) | ✅ | Green glow shadow on active |
| Op metadata (mode + findings count) | ✅ | |
| Mode selector (Autopilot/Copilot/Manual) | ✅ Working | Segmented control, switches state |

### Tab Bar
| Component | Status | Notes |
|-----------|--------|-------|
| 9 tabs (Recon→Stash) | ✅ Working | Click to switch |
| Per-tab accent underline | ✅ | Blue/orange/cyan/amber/red/purple/green/gray/cyan |
| Terminal button | ✅ Visual | Not wired yet |
| Settings button | ✅ Visual | Not wired yet |

### Recon Tab
| Component | Status | Notes |
|-----------|--------|-------|
| Subtabs (Subdomains/Ports/Web Hosts/Crawl/OSINT) | ✅ Visual | Switching works, all show same table |
| Target input field | ✅ Visual | Styled, not wired to tool execution |
| "Full Recon" button | ✅ Visual | Not wired yet |
| Results table (8 sample rows) | ✅ | Columns: Subdomain, IP, Status, Server, Title |
| Status badges (200/403/302 colored) | ✅ | Green/amber/blue color coding |

### Chat Panel
| Component | Status | Notes |
|-----------|--------|-------|
| Header (model name + streaming indicator) | ✅ Working | Shows "streaming" with green dot |
| Settings button | ✅ Visual | Not wired |
| Clear button (⌫) | ✅ Working | Clears all messages |
| Message list (scrollable) | ✅ Working | Auto-scrolls on new content |
| User messages (right-aligned, dark bg) | ✅ Working | |
| Assistant messages (left-aligned, bordered) | ✅ Working | Markdown rendered via Text(.init()) |
| Thinking blocks (purple, italic) | ✅ Working | Appears during streaming, collapses after |
| Tool call cards (cyan, monospace) | ✅ Working | Shows tool name, status, command + output |
| Empty state (robot emoji + "Ready to pentest") | ✅ | |
| Streaming dots placeholder | ✅ | While waiting for first token |
| Text selection (.textSelection(.enabled)) | ✅ | On all message types |
| Input field (NSTextField wrapper) | ✅ Working | Proper keyboard input via NSViewRepresentable |
| Send button (↑ / ■) | ✅ Working | Toggles to red stop during streaming |
| Enter to send | ✅ Working | Via NSTextField delegate |
| Stop button | ✅ Working | isStopped flag checked at all async points |
| Attach button | ✅ Visual | Not wired |
| Stash button | ✅ Visual | Not wired |

### Chat Service (LLM Connection)
| Component | Status | Notes |
|-----------|--------|-------|
| Connect to vMLX on localhost:8000 | ✅ Working | OpenAI-compatible /v1/chat/completions |
| SSE streaming | ✅ Working | Token-by-token display |
| Reasoning content (thinking blocks) | ✅ Working | delta.reasoning_content parsed |
| System prompt | ✅ Working | Pentesting agent identity |
| Tool definitions sent to model | ✅ Working | 15 tools as OpenAI function format |
| Tool call parsing (streaming) | ✅ Working | Accumulated from delta.tool_calls |
| Conversation loop (tool call → execute → feed back) | ✅ Working | Up to 20 iterations |
| Stop/cancel mid-stream | ✅ Working | isStopped flag + Task.cancel |
| Tool results as user context | ✅ Working | Avoids tool role format issues |

### Tool Executor
| Component | Status | Notes |
|-----------|--------|-------|
| Subprocess spawning | ✅ Working | Process() with argument array |
| Binary path resolution | ✅ Working | Checks /opt/homebrew/bin, /usr/local/bin, /usr/bin, ~/.exploitbot/tools, `which` |
| PATH environment building | ✅ Working | Includes homebrew + system + custom paths |
| Stdout streaming to UI | ✅ Working | Real-time via readabilityHandler |
| Stderr capture | ✅ Working | |
| Exit code + duration tracking | ✅ Working | |
| Timeout enforcement | ✅ Working | SIGTERM → 3s → SIGKILL |
| Cancel support | ✅ Working | terminate() with kill fallback |
| Output truncation (3KB for UI) | ✅ Working | Full output preserved in tool message |

### Tool Definitions (CLI Mapping)
| Tool | CLI Args Built | Binary Found | Tested |
|------|---------------|-------------|--------|
| subfinder | ✅ | Depends on install | — |
| dnsx | ✅ | Depends on install | — |
| nmap | ✅ | Depends on install | — |
| httpx | ✅ | Depends on install | — |
| nuclei | ✅ | Depends on install | — |
| katana | ✅ | Depends on install | — |
| feroxbuster | ✅ | Depends on install | — |
| sqlmap | ✅ | Depends on install | — |
| dalfox | ✅ | Depends on install | — |
| hashcat | ✅ | Depends on install | — |
| hydra | ✅ | Depends on install | — |
| sherlock | ✅ | Depends on install | — |
| holehe | ✅ | Depends on install | — |
| search_cve | ✅ Defined | Not implemented | Needs CVE DB |
| run_shell | ✅ | /bin/zsh (system) | — |

---

## What's Not Built Yet

### Critical Path (needed for basic functionality)
- [ ] Other tab UIs (Web, Network, Creds, Exploit, Post, OSINT, Report, Stash) — currently show placeholder
- [ ] Op persistence (SQLite/GRDB) — currently in-memory only, lost on restart
- [ ] Message persistence — same, in-memory
- [ ] Op creation flow — New Op button not wired
- [ ] Model selection/switching — hardcoded to MiniMax on port 8000
- [ ] Settings UI — not built
- [ ] Onboarding flow — not built

### Important (needed for real pentesting)
- [ ] Activity feed (bottom panel)
- [ ] Terminal panel (SwiftTerm)
- [ ] Stash system (drawer + full tab)
- [ ] Finding creation wizard
- [ ] Report generation
- [ ] CVE knowledge base
- [ ] Model downloader
- [ ] Tool installation management
- [ ] Scope enforcement
- [ ] Context management strategies

### Polish
- [ ] Proper macOS app icon (currently default)
- [ ] Custom title bar (currently standard macOS)
- [ ] Keyboard shortcuts
- [ ] i18n string catalogs
- [ ] Notifications
- [ ] Import/export
- [ ] Audit logging

---

## Architecture Decisions Made During Implementation

### D031: App Bundle vs SPM Debug Build
- **Problem:** SPM debug executables don't receive macOS keyboard input (no proper entitlements/Info.plist)
- **Solution:** Build via SPM, then copy binary into a manually-created .app bundle with Info.plist
- **Location:** ExploitBotXcode/ExploitBot.app/
- **Future:** Migrate to proper Xcode project or use xcodegen

### D032: NSTextField for Chat Input
- **Problem:** SwiftUI TextField doesn't accept keyboard input reliably in complex layouts / hidden title bar windows
- **Solution:** NSViewRepresentable wrapping NSTextField with proper delegate for Enter-to-send
- **File:** Views/Chat/ChatInputField.swift

### D033: Tool Results as User Messages
- **Problem:** vMLX engine requires `role: "tool"` messages to follow an `assistant` message with `tool_calls` — proper format needs tracking tool_call IDs across the conversation
- **Solution:** Send tool results as `role: "user"` with `[Tool Result: name status]` prefix. Model understands this format and can continue reasoning.
- **Future:** Implement proper tool_calls tracking in assistant messages for native tool role support

### D034: Thinking Block Lifecycle
- **Problem:** Thinking blocks persisted in the chat after model finished reasoning, cluttering the view
- **Solution:** After streaming completes, remove the thinking message and store its content as `reasoningContent` on the assistant message. Thinking is visible during streaming, collapsed after.

### D035: Stop Mechanism
- **Problem:** Task.cancel() alone doesn't stop tool subprocess execution or mid-stream SSE
- **Solution:** `isStopped` boolean flag checked at every async boundary: loop iteration, before tool execution, during SSE line reading, after tool completes. Plus toolExecutor.cancel() sends SIGTERM to running process.

---

## Build & Run

```bash
cd ~/exploitbot/ExploitBot

# Build
swift build

# Copy to .app bundle (required for keyboard input)
cp .build/debug/ExploitBot ../ExploitBotXcode/ExploitBot.app/Contents/MacOS/ExploitBot

# Launch
open ../ExploitBotXcode/ExploitBot.app

# Or rebuild + launch in one command:
swift build && pkill -f ExploitBot; sleep 0.5; cp .build/debug/ExploitBot ../ExploitBotXcode/ExploitBot.app/Contents/MacOS/ExploitBot && open ../ExploitBotXcode/ExploitBot.app
```

### Prerequisites
- macOS 14+
- Xcode 26+ (for Swift toolchain)
- vMLX engine running on localhost:8000 with a loaded model
- Pentesting tools installed (homebrew/pip) for tool execution

---

## Source File Index

```
ExploitBot/Sources/ExploitBot/
├── App/
│   └── ExploitBotApp.swift          # @main entry, WindowGroup, dark mode
├── Models/
│   ├── AppState.swift               # @Observable: ops, activeTab, mode, chatService
│   ├── ChatRole.swift               # enum: user, assistant, thinking, toolCall
│   ├── Op.swift                     # Op struct + OpStatus + InteractionMode + samples
│   └── ToolTab.swift                # enum: 9 tabs with labels + accent colors
├── Services/
│   ├── ChatService.swift            # LLM connection, SSE streaming, tool call loop
│   ├── ToolDefinitions.swift        # 15 tool schemas + CLI argument builders
│   └── ToolExecutor.swift           # Subprocess management, output streaming, cancel
├── Theme/
│   ├── Colors.swift                 # 17 Color extensions (bg, border, text, accent)
│   └── Fonts.swift                  # Monospace font sizes
└── Views/
    ├── Chat/
    │   ├── ChatInputField.swift     # NSTextField wrapper (NSViewRepresentable)
    │   └── ChatPanelView.swift      # Chat panel: header, messages, bubbles, input
    ├── ContentView.swift            # Main layout: Sidebar + Tabs + Workspace + Chat
    ├── Sidebar/
    │   └── SidebarView.swift        # Op list, brand, mode selector
    └── Tabs/
        ├── ReconTabView.swift       # Recon tab: subtabs, target input, results table
        └── TabBarView.swift         # Tab bar: 9 tabs + toolbar buttons
```
