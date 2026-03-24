# exploitbot — Feature Cross-Links & Integration Points

**Last updated:** 2026-03-24 (post Phase H + parsers + CVE auto + crash recovery)

Every connection between services/views that exists or needs to exist.

---

## Currently Wired ✅ (38 connections)

### Chat ↔ Engine
| From | To | How |
|------|----|-----|
| ChatService | EngineManager | `chatService.baseURL = engineManager.baseURL` after engine starts |
| ChatService | vMLX engine | HTTP POST `/v1/chat/completions` (SSE streaming) |
| EngineManager | Python process | `launch.py --model <path> --port <port>` subprocess |
| EngineManager | Health check | GET `/health` polling (120s startup, 5s monitor) |
| EngineManager crash | AppState | `onCrash` callback → auto-restart after 2s delay |

### Chat ↔ Tools
| From | To | How |
|------|----|-----|
| ChatService → tool_calls | ToolExecutor | `toolExecutor.execute(binary, args)` subprocess |
| ChatService → search_cve | CVEService | `onSearchCVE` callback → `cveService.searchForModel()` (builtin, no subprocess) |
| ChatService → tool_calls | Copilot approval | When mode==.copilot, show ApprovalCard, await user action |
| ChatService → tool_calls | Manual mode | When mode==.manual, show suggestion only, don't execute |
| ToolDefinitions | ChatService | 37 tool schemas sent as `tools` parameter in API request |

### Chat ↔ UI
| From | To | How |
|------|----|-----|
| ChatService → tool results | ResultsStore | `onToolResult` callback → `resultsStore.ingest()` |
| ChatService → tool start | ActivityFeed | `onToolStart` callback → `activityFeed.logToolStart()` |
| ChatService → tool complete | ActivityFeed | `onToolComplete` callback → `activityFeed.logToolComplete()` |
| ChatService → thinking | ActivityFeed | `onThinking` callback → `activityFeed.logThinking()` |
| ChatService → tool start | AppState.activeTab | Auto-tab switching via `tabForTool()` |
| ChatService → phase complete | AppState.currentPhase | `onPhaseComplete` → `advancePhase()` |
| Chat "📦 Stash" button | StashService | `onStash` callback on messages + tool outputs |
| Chat tool output 📦 | StashService | `onStash` on ChatBubble for toolCall + assistant roles |
| Stash "→ Send" button | ChatService | `onSendToChat` → `chatService.send(content)` |

### ResultsStore ↔ Tabs
| From | To | How |
|------|----|-----|
| ResultsStore.subdomains | ReconTabView | `@Bindable var resultsStore` |
| ResultsStore.webHosts | ReconTabView + WebTabView | Shared data |
| ResultsStore.vulns | WebTabView | VulnEntry cards with CVSS |
| ResultsStore.ports | ReconTabView (Ports subtab) | PortEntry table |
| ResultsStore.networkHosts | NetworkTabView | NetworkHostEntry table |
| ResultsStore.osintResults | OSINTTabView | Platform results |
| ResultsStore.vulns | ReportTabView | Findings list (via FindingService) |

### ResultsStore ↔ CVE Auto-Search
| From | To | How |
|------|----|-----|
| httpx server header | ResultsStore.onServiceDetected | Parses "Apache/2.4.49" → (product, version) |
| nmap service version | ResultsStore.onServiceDetected | Open ports with version → (service, version) |
| onServiceDetected | CVEService.search() | Auto-queries CVE DB with product+version |
| onServiceDetected | ActivityFeed | Logs "Auto CVE search: apache 2.4.49" + result count |

### Persistence
| From | To | How |
|------|----|-----|
| Op switching | ChatService messages | `saveCurrentMessages()` / `loadMessages()` (SQLite) |
| Op switching | ResultsStore | `clear()` on switch |
| Settings | EngineConfig | `saveEngineConfig()` / `loadEngineConfig()` (SQLite settings table) |
| StashService | SQLite stash_items | `saveStashItem()` / `fetchStashItems()` |
| FindingService | SQLite findings | `saveFinding()` / `fetchFindings()` |
| CVEService | SQLite cves + cves_fts | FTS5 search, CPE match, severity filter |
| App quit | Messages | `saveCurrentMessages()` on scenePhase change |
| Onboarding | Settings + Op | Saves language, model path, creates first Op |

### Tool Installation
| From | To | How |
|------|----|-----|
| ToolInstaller | `which` + path check | Detects 34 tools across homebrew/pip/go/system |
| ToolInstaller | `brew install` / `pip3 install` | Subprocess for installation |
| Settings → Tools | ToolInstaller | ToolSettingsView displays status, install buttons |

### Model Download
| From | To | How |
|------|----|-----|
| ModelDownloader | `huggingface-cli download` | Subprocess for HF model download |
| Settings → Model | ModelDownloadView | 3 curated tiers + downloaded list |
| Download complete | EngineConfig.modelPath | "Use This Model" sets path |

---

## Tool Result Parser Coverage (22/39)

| Parser | Tools | Output Type |
|--------|-------|-------------|
| line_per_result | subfinder, dnsx | SubdomainEntry |
| jsonl | httpx, katana, feroxbuster, ffuf, dalfox, trufflehog | WebHostEntry / VulnEntry |
| nuclei_jsonl | nuclei | VulnEntry with CVE/severity/tags |
| nmap_text | nmap | PortEntry with service/version |
| masscan_json | masscan | PortEntry with host |
| netexec_text | netexec | NetworkHostEntry with signing/Pwn3d |
| sqlmap_text | sqlmap | VulnEntry (injection detection) |
| hydra_text | hydra | VulnEntry (valid credentials) |
| wpscan_json | wpscan | VulnEntry + OSINTEntry (users) |
| testssl_json | testssl | VulnEntry (TLS findings) |
| sherlock_text | sherlock | OSINTEntry (platform results) |
| holehe_text | holehe | OSINTEntry (email registration) |
| harvester_text | theHarvester | OSINTEntry + SubdomainEntry |
| exiftool_json | exiftool | OSINTEntry (metadata) |
| raw_text | 17 remaining tools | rawResults only |

---

## Data Flow: Complete Request Lifecycle

```
User types "pentest acme.com"
  ↓
ChatService.send()
  → POST /v1/chat/completions {messages, tools: 37 schemas, stream: true}
  → SSE stream:
    → delta.reasoning_content → thinking bubble (collapses after)
    → delta.content → assistant bubble (streaming)
    → delta.tool_calls → accumulated by index
  → finish_reason: "tool_calls"
  ↓
Tool Call Loop (up to 20 iterations):
  → If mode == .copilot → show ApprovalCard, await approve/reject
  → If mode == .manual → show suggestion only, break loop
  → If tool == "search_cve" → onSearchCVE → CVEService.searchForModel() → return text
  → Else → ToolExecutor.execute(binary, args) → subprocess
    → stdout → onToolResult → ResultsStore.ingest()
      → Parsed into tab data (subdomains, vulns, ports, hosts, osint)
      → If httpx/nmap: onServiceDetected → CVE auto-search
    → onToolStart → ActivityFeed + auto-tab switch
    → onToolComplete → ActivityFeed
  → Tool result sent back to model as user message
  → Model continues (may call more tools)
  ↓
User clicks "📦 Stash" on any message
  → StashService.stash() → SQLite stash_items
  → onItemStashed → ActivityFeed
  ↓
User clicks "⚡ Create Finding" on vuln card
  → FindingWizardView opens (prefilled)
  → FindingService.createFinding() → SQLite findings
  → onFindingCreated → ActivityFeed
  ↓
User clicks "Generate Report" in Report tab
  → ReportService.generateReport(findings) → HTML
  → Preview in WKWebView
  → Export: PDF (createPDF), Markdown, JSON
```
