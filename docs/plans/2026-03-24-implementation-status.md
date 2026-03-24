# exploitbot — Implementation Status

**Last updated:** 2026-03-24 (session 2 — engine integration)
**Total feature matrix items:** 1,307
**Engine checklist items:** 141 (18 verified)
**Technical decisions:** 35 (D001–D035)
**Swift source files:** 29
**Lines of Swift:** ~3,295
**Engine Python files:** 61
**Lines of Python:** ~29,387

---

## What's Built & Working

### Engine Integration
| Component | Status | Notes |
|-----------|--------|-------|
| EngineManager | ✅ Working | Spawns launch.py, health polling (120s), crash detection, start/stop |
| launch.py | ✅ Working | Correct CLI args matching vmlx_engine.server --help |
| Engine auto-detection | ✅ Working | Finds vmlx_engine via pip import, builds correct args |
| Model config detection | ✅ Working | 62 model families, auto-detects reasoning + tool parser |
| JANG format loading | ✅ Working | v2 mmap instant loading confirmed |
| Health monitoring | ✅ Working | 5s interval, detects crashes, updates UI |
| Engine log streaming | ✅ Working | Live stderr capture, shown in Settings |
| Dynamic port | ✅ Working | 8100-8199 range, ChatService.baseURL auto-updated |
| Settings persistence | ✅ Working | All engine config saved/loaded from SQLite |

### Settings UI
| Component | Status | Notes |
|-----------|--------|-------|
| Engine status indicator | ✅ Working | Green/gray dot, Starting.../Running/Stopped/Error |
| Start/Stop buttons | ✅ Working | Lifecycle control |
| Model path + Browse | ✅ Working | NSOpenPanel folder picker, validates config.json |
| Temperature slider | ✅ Working | 0.0-2.0 range |
| Max tokens | ✅ Working | Text input |
| Reasoning parser dropdown | ✅ Working | 6 options: auto, none, qwen3, deepseek_r1, openai_gptoss, mistral |
| Tool call parser dropdown | ✅ Working | 14 options: auto + all 13 model-specific parsers |
| KV cache quantization | ✅ Visual | Dropdown exists, not passed to engine (CLI doesn't support it) |
| Engine log viewer | ✅ Working | Collapsible, shows live engine output |
| Apply & Restart | ✅ Working | Saves config, stops engine, restarts with new settings |

### App Shell
| Component | Status | Notes |
|-----------|--------|-------|
| App icon | ✅ Working | Bot face in Dock (icns from SVG) |
| Dark theme | ✅ Working | 17 color extensions |
| Sidebar + Ops | ✅ Working | SQLite persisted, create/switch/delete |
| Tab bar (9 tabs) | ✅ Working | Per-tab accent colors |
| Settings button (⚙) | ✅ Working | Opens settings overlay |
| Mode selector | ✅ Working | Autopilot/Copilot/Manual |

### Chat System
| Component | Status | Notes |
|-----------|--------|-------|
| SSE streaming | ✅ Working | Token-by-token via URLSession.bytes |
| Reasoning blocks | ✅ Working | Appear during streaming, collapse after |
| Tool call parsing | ✅ Working | Accumulated from delta.tool_calls |
| Tool execution | ✅ Working | Subprocess with output streaming |
| Tool call loop | ✅ Working | Model → tool → result → model (up to 20 iterations) |
| Stop button | ✅ Working | isStopped flag at all async boundaries |
| Message persistence | ✅ Working | SQLite, saved on Op switch + app quit |
| Dynamic baseURL | ✅ Working | Updated from EngineManager after engine starts |
| Results ingestion | ✅ Working | Tool output parsed into ResultsStore for tab views |

### Tool Execution
| Component | Status | Notes |
|-----------|--------|-------|
| Subprocess spawning | ✅ Working | Argument arrays (no shell injection) |
| PATH resolution | ✅ Working | homebrew + system + ~/.exploitbot/tools |
| Output streaming | ✅ Working | Real-time via readabilityHandler |
| Timeout + cancel | ✅ Working | SIGTERM → 3s → SIGKILL |
| 15 tool CLI mappings | ✅ Working | subfinder through run_shell |

### Tab Views
| Tab | Status | Notes |
|-----|--------|-------|
| Recon | ✅ Real data | Shows tool results from ResultsStore |
| Web | ✅ Real data | Vuln cards from ResultsStore |
| Network | ✅ Real data | Host table from ResultsStore |
| OSINT | ✅ Real data | Platform results from ResultsStore |
| Report | ✅ Real data | Findings list from ResultsStore |
| Creds | ✅ Layout | Empty state, config form |
| Exploit | ✅ Layout | Empty state, search bar |
| Post | ✅ Layout | Empty state, session picker |
| Stash | ✅ Layout | Empty state, filters |

### Engine (ExploitBotEngine/)
| Component | Status | Notes |
|-----------|--------|-------|
| vmlx_engine core (61 files) | ✅ Copied | Stripped from vMLX, VLM removed |
| Reasoning parsers (5) | ✅ Present | qwen3, deepseek_r1, openai_gptoss, mistral, think |
| Tool call parsers (14) | ✅ Present | auto + 13 model-specific |
| Cache stack | ✅ Present | prefix, paged, memory-aware (disk stubbed) |
| Model config registry | ✅ Present | 62 families |
| JANG loader | ✅ Present | v2 mmap loading |
| ARCHITECTURE.md | ✅ Complete | Engine↔app connection, tool flow, SSE format |
| ENGINE_CHECKLIST.md | ✅ Complete | 141 items, 18 verified |

---

## What's NOT Built Yet

### High Priority
| Feature | Effort | Notes |
|---------|--------|-------|
| Activity feed (bottom panel) | Medium | Tool execution visibility |
| Onboarding flow | Medium | Language → model → tools → first Op |
| Model downloader | Medium | HuggingFace API, progress, pause/resume |
| Copilot approval cards | Medium | Inline approve/reject for tool calls |

### Medium Priority
| Feature | Effort | Notes |
|---------|--------|-------|
| Terminal (SwiftTerm) | Heavy | Embedded PTY |
| Stash system (real) | Medium | Save/load from DB, drawer UI |
| Finding creation wizard | Medium | Modal, pre-filled from tool output |
| Report generation | Heavy | HTML template → WKWebView PDF |
| Tool installation manager | Medium | Detect, install via brew/pip |

### Lower Priority
| Feature | Effort | Notes |
|---------|--------|-------|
| CVE knowledge base | Heavy | sqlite-vec, 250K CVEs, embeddings |
| i18n string catalogs | Medium | 5 languages |
| Keyboard shortcuts | Low | ⌘N, ⌘`, ⌘1-9, etc. |
| Import/export | Low | Ops, stash, findings as ZIP |
| Notifications | Low | macOS notification center |
| Auto-update | Medium | GitHub releases API |
| Testing framework (D030) | Heavy | XCUITest + LLM agent testing |
| Scope enforcement | Medium | Block out-of-scope targets |
| Audit logging | Low | Tool execution log file |

---

## Architecture Decisions (D001–D035)

| Decision | Summary | Status |
|----------|---------|--------|
| D001 | SwiftUI, macOS 14+ | Implemented |
| D002 | vMLX engine on localhost | Implemented |
| D003 | HTTP + SSE to OpenAI API | Implemented |
| D004 | Hybrid tool calling (structured + run_shell) | Implemented |
| D005 | Single model, curated tiers | Implemented (settings) |
| D006 | Named Ops with persistent context | Implemented |
| D007 | Context management (4 strategies) | Designed, not built |
| D008 | Stash (cross-Op artifacts) | Designed, not built |
| D009 | Findings system | Designed, not built |
| D010 | Report generation | Designed, not built |
| D011 | Hybrid tool install (bundled + lazy) | Designed, not built |
| D012 | Tool registry (39 schemas) | Implemented (15 in CLI mappings) |
| D013 | Tool execution runtime | Implemented |
| D014 | i18n (5 languages) | Designed, not built |
| D015 | Inference settings exposed | Implemented (settings UI) |
| D016 | Reasoning recognition | Implemented (auto-detect) |
| D017 | Per-tab bespoke UIs | Implemented (9 tabs) |
| D018 | SwiftTerm terminal | Designed, not built |
| D019/D028 | SQLite via GRDB | Implemented |
| D020 | First-run onboarding | Designed, not built |
| D021 | App lifecycle | Partially (engine start/stop, no orphan recovery) |
| D022 | Model architecture detection | Implemented (62 families) |
| D023 | Dual-mode (manual + LLM) | Partially (chat works, tab forms static) |
| D024 | Shell injection prevention | Implemented (argument arrays) |
| D025 | 3 interaction modes | UI exists, only Autopilot behavior implemented |
| D026 | Activity feed | Designed, not built |
| D027 | PDF reports (HTML → WKWebView) | Designed, not built |
| D029 | CVE knowledge base | Designed, embedder written, DB not built |
| D031 | .app bundle packaging | Implemented |
| D032 | NSTextField for chat input | Implemented |
| D033 | Tool results as user messages | Implemented |
| D034 | Thinking block lifecycle | Implemented |
| D035 | isStopped flag for cancel | Implemented |

---

## Source File Index

```
ExploitBot/Sources/ExploitBot/ (29 files, 3,295 lines)
├── App/
│   └── ExploitBotApp.swift
├── Models/
│   ├── AppState.swift              # Engine management, Op CRUD, message persistence
│   ├── ChatRole.swift
│   ├── Op.swift
│   ├── ToolResult.swift            # Parsed tool results for tabs
│   └── ToolTab.swift
├── Services/
│   ├── ChatService.swift           # SSE streaming, tool call loop, dynamic baseURL
│   ├── Database.swift              # GRDB SQLite (ops, messages, settings)
│   ├── EngineManager.swift         # Engine lifecycle, health check, port management
│   ├── ResultsStore.swift          # Ingests tool output, feeds tab views
│   ├── ToolDefinitions.swift       # 15 tool schemas + CLI arg builders
│   └── ToolExecutor.swift          # Subprocess management
├── Theme/
│   ├── Colors.swift
│   └── Fonts.swift
└── Views/
    ├── Chat/
    │   ├── ChatInputField.swift    # NSTextField wrapper
    │   └── ChatPanelView.swift
    ├── ContentView.swift
    ├── Settings/
    │   └── SettingsView.swift      # Engine config, model, parsers, cache
    ├── Sidebar/
    │   └── SidebarView.swift
    └── Tabs/
        ├── CredsTabView.swift
        ├── ExploitTabView.swift
        ├── NetworkTabView.swift
        ├── OSINTTabView.swift
        ├── PostExploitTabView.swift
        ├── ReconTabView.swift
        ├── ReportTabView.swift
        ├── StashTabView.swift
        ├── TabBarView.swift
        └── WebTabView.swift

ExploitBotEngine/ (61 Python files, 29,387 lines + support files)
├── launch.py                       # Engine launcher (correct CLI args)
├── cve_embedder.py                 # Standalone CVE embedding tool
├── pyproject.toml                  # Dependencies
├── ARCHITECTURE.md                 # Engine↔app connection docs
├── ENGINE_CHECKLIST.md             # 141 verification items
├── prompts/                        # System prompt templates (8 files)
├── tools/registry.json             # 39 tool schemas
└── vmlx_engine/                    # Inference engine (stripped vMLX)
```

---

## Build & Run

```bash
cd ~/exploitbot/ExploitBot
swift build
cp .build/debug/ExploitBot ../ExploitBotXcode/ExploitBot.app/Contents/MacOS/ExploitBot
open ../ExploitBotXcode/ExploitBot.app
```

Then: Settings ⚙ → Browse model → Apply & Restart Engine → Chat
