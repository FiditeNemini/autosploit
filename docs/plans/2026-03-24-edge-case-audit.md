# exploitbot — Edge Case & Deep Behavior Audit

**Date:** 2026-03-24
**Purpose:** Systematic walkthrough of every user flow, identifying unhandled edge cases, race conditions, data loss scenarios, and UX failures.

---

## 1. Engine Startup & Model Loading

### Flow: App Launch → Engine Start → Model Load → Ready

| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| No model path configured | Engine start fails with "No model selected" | Medium | ✅ Handled — shows error in settings |
| Model path points to deleted folder | Engine crashes on load | High | ❌ No pre-validation of path before launch |
| Model files corrupted (partial download) | Engine crashes mid-load, Python traceback | High | ❌ No integrity check |
| Not enough RAM for model | Engine starts, OOM kill after partial load | Critical | ❌ No RAM check before loading |
| Port 8100-8199 all in use | findAvailablePort returns 0, start fails | Low | ✅ Handled — shows error |
| Python3 not installed | findPython returns nil, shows error | Medium | ✅ Handled |
| Engine dies mid-conversation | Health monitor detects crash | High | ✅ Handled — auto-restart after 2s |
| Engine restart loses model context | After crash+restart, conversation history intact but model has no memory | High | ❌ Need to re-send system prompt + recent context on reconnect |
| Two app instances launched | Both try to start engines, port conflicts | Medium | ❌ No single-instance lock |
| User changes model in settings while chat is active | Engine restarts, mid-stream response cut off | Medium | ❌ Should warn or stop generation first |
| baseURL still pointing to old port after restart | Chat sends to wrong port | High | ✅ Fixed — baseURL updated after healthy |
| Engine starts but model takes >60s to load (huge model) | Health check times out, shows error | Medium | ❌ Should extend timeout for large models or show progress |

### Missing: Engine Reconnection After Crash
When engine crashes and auto-restarts, the chat should:
1. Re-send system prompt (including phase guidance)
2. Re-send last N messages for context continuity
3. Show "Engine reconnected" banner
4. Resume Autopilot if it was running

---

## 2. Chat & Conversation

### Flow: User Types → Send → Stream → Tool Calls → Response

| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| Empty message sent | `guard !text.isEmpty` catches it | Low | ✅ Handled |
| Very long message (>100KB pasted) | Sent to model, may exceed context | Medium | ❌ No input length warning |
| Model returns malformed JSON in tool_call | JSON parse fails, tool_call ignored | Medium | ✅ Graceful — falls through to no tool calls |
| Model calls a tool that doesn't exist | buildCliArgs default case returns (toolName, []) | Medium | ❌ Should show "unknown tool" error, not try to execute |
| Model calls tool with missing required param | CLI args built with empty string "" | Medium | ❌ No parameter validation before execution |
| Tool execution takes >5 minutes | 300s timeout fires, SIGTERM sent | Low | ✅ Handled |
| Tool produces >1GB of output | stdoutData grows unbounded in memory | Critical | ❌ No output size limit on accumulation |
| Multiple tool calls in one response | Loop processes each sequentially | Low | ✅ Works |
| Model enters infinite loop (same tool repeatedly) | 20-iteration limit on conversation loop | Medium | ✅ Handled, but no user notification |
| User sends message while model is still responding | send() called while isStreaming=true | Medium | ❌ Should queue or reject, currently may corrupt state |
| User switches Op while model is mid-response | switchOp saves messages including partial response | Medium | ❌ Should stop generation first |
| Network error to localhost engine | URLSession throws, error shown in chat | Low | ✅ Handled |
| SSE stream disconnects mid-response | for-await loop exits, partial content kept | Medium | ✅ Partial response preserved |
| Model outputs markdown with unclosed code blocks | Text(.init()) may render oddly | Low | ❌ No markdown sanitization |
| Chat has 500+ messages (long session) | ScrollView performance degrades | Medium | ❌ No virtualization, LazyVStack helps but not enough for huge conversations |

### Missing: Message Send Guard
```swift
func send(_ text: String) {
    guard !isStreaming else { return }  // MISSING — should reject or queue
    ...
}
```

### Missing: Output Size Cap
```swift
// In readabilityHandler:
if stdoutData.count > 10_000_000 { // 10MB cap
    process.terminate()
    return
}
```

---

## 3. Tool Execution

### Flow: Model Calls Tool → ToolExecutor → Subprocess → Parse → Display

| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| Tool binary not installed | findBinary returns nil, error in ToolResult | Medium | ✅ Handled |
| Tool requires sudo (nmap SYN scan) | Fails with permission denied | Medium | ❌ No sudo prompt mechanism |
| Tool writes to filesystem (sqlmap output dir) | Files created in process working directory | Low | ✅ OK but cleanup not handled |
| Tool opens network connections that hang | Timeout kills after 300s | Low | ✅ Handled |
| Tool outputs non-UTF8 binary data | String(data:encoding:) returns nil | Medium | ❌ Falls through as empty string |
| Two tools running simultaneously | Not possible — sequential in loop | Low | ✅ By design |
| Tool path contains spaces | Process handles this natively | Low | ✅ OK |
| User's PATH doesn't include homebrew | buildEnvironment adds /opt/homebrew/bin | Low | ✅ Handled |
| Tool outputs ANSI color codes | Raw codes shown in chat | Low | ❌ No ANSI stripping for chat display |
| run_shell with dangerous command (rm -rf /) | Executes without guard | Critical | ❌ No blocklist for dangerous commands |
| Masscan/nmap scanning unauthorized targets | No scope enforcement | Critical | ❌ Scope checking not implemented |

### Missing: Dangerous Command Blocklist
```swift
let blockedPatterns = ["rm -rf /", "mkfs", "dd if=/dev/zero", ":(){ :|:& };:"]
for pattern in blockedPatterns {
    if command.contains(pattern) { return error }
}
```

### Missing: ANSI Stripping
```swift
extension String {
    var strippingANSI: String {
        replacingOccurrences(of: "\u{001B}\\[[0-9;]*m", with: "", options: .regularExpression)
    }
}
```

---

## 4. Interaction Modes

### Autopilot Edge Cases
| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| Model decides to scan out-of-scope target | No enforcement | Critical | ❌ Scope not checked against tool params |
| Model runs 20 iterations and hits limit | Loop ends silently | Medium | ❌ Should notify user "iteration limit reached" |
| User clicks Stop but tool is mid-execution | isStopped flag + toolExecutor.cancel() | Low | ✅ Handled |
| User switches to Copilot mid-Autopilot run | Next tool call shows approval card | Low | ✅ Works — mode checked per tool call |
| Phase auto-advance from model output "SCAN COMPLETE" | Checks uppercased content for keyword | Medium | ❌ False positive if model says "the SCAN COMPLETE took 5 min" in regular text |

### Copilot Edge Cases
| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| User never clicks Approve/Reject and walks away | Continuation suspended forever, no timeout | Medium | ❌ Should auto-timeout approval after N minutes |
| User clicks Approve on a stale approval (model moved on) | Continuation already nil, button does nothing | Low | ✅ Safe — nil check |
| Multiple tool calls in one model response | Each gets separate approval card sequentially | Low | ✅ Works |
| User rejects all tools, model keeps suggesting same ones | Model may loop until iteration limit | Medium | ❌ Should detect rejection pattern |

### Manual Mode Edge Cases
| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| Model still generates tool_calls in response | Shows "suggested" with command | Low | ✅ Handled |
| User asks "run nmap on X" expecting execution | Model shows suggestion but doesn't run | Medium | ❌ UX confusion — should show clearer "Manual mode: copy this command to terminal" |

---

## 5. Op Management

| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| Delete last remaining Op | Button disabled | Low | ✅ Handled |
| Create Op with empty name | Creates with "New Op" | Low | ❌ Should require non-empty name |
| Create Op with very long name (500+ chars) | No limit, may overflow sidebar | Low | ❌ Should truncate or limit |
| Switch Op while tool is running | Saves messages, switches | Medium | ❌ Should stop execution first or warn |
| Rename Op to duplicate name | Allowed | Low | ❌ Could confuse users but not a bug |
| Delete Op that has findings | Findings cascade-deleted via FK | Low | ✅ Handled by DB |
| 100+ Ops created | Sidebar scrolls | Low | ✅ ScrollView handles it |
| Op scope field never validated | Freeform text stored | Low | ❌ No validation of domain/IP format |

---

## 6. Stash System

| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| Stash 1000+ items | No warning | Medium | ❌ Should warn about large stash |
| Stash item with >1MB content | Stored in DB blob | Medium | ❌ Should truncate or warn |
| "Send to chat" sends entire stash content as user message | Model tries to process huge text | Medium | ❌ Should truncate for model context |
| Delete stash item that's referenced by a Finding | Finding evidence becomes orphaned | Medium | ❌ No referential integrity between stash and findings |
| Type auto-detection fails (ambiguous content) | Defaults to .raw | Low | ✅ Graceful fallback |

---

## 7. Findings & Reports

| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| Generate report with 0 findings | Button disabled | Low | ✅ Handled |
| Generate report with 100+ findings | HTML may be very large | Medium | ❌ No pagination in HTML |
| PDF export on very large report | WKWebView may timeout | Medium | ❌ No progress indicator or timeout handling |
| Finding with empty attack chain | Shows empty list | Low | ✅ OK |
| CVSS score entered as text "high" instead of number | TextField accepts it, may show 0.0 | Low | ❌ No input validation |
| Delete finding after report generated | Report becomes stale | Medium | ❌ No "report is stale" warning |
| Export PDF to read-only location | try? swallows error | Medium | ❌ User gets no feedback |

---

## 8. Terminal

| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| Terminal still running when app quits | Process orphaned | Medium | ❌ No terminal process cleanup on app exit |
| User runs long command in terminal | Terminal handles it | Low | ✅ SwiftTerm manages |
| Terminal and activity feed can't be visible simultaneously | Toggle replaces one with other | Low | ❌ UX limitation — should be resizable split |
| Terminal PATH doesn't include newly installed tools | PATH set at terminal creation time | Medium | ❌ Need to restart terminal after tool install |

---

## 9. Phase System

| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| Phase not persisted per-Op | Lost on restart | Medium | ❌ Should save to DB settings per Op |
| Phase stats (tools run) not persisted | Lost on restart/switch | Low | ❌ Ephemeral counter |
| Model says "SCAN COMPLETE" as part of a sentence | False positive advance | Medium | ❌ Should require exact match or structured signal |
| User manually advances phase while model is running tools | Phase changes mid-tool-execution | Low | ✅ Phase guidance updates for next model call |
| User goes back to SCAN after BREACH | Allowed but results from later phases still in ResultsStore | Low | ❌ Should optionally clear later-phase results |

---

## 10. Database & Persistence

| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| DB file locked by another process | GRDB may throw | Medium | ✅ WAL mode handles concurrent reads |
| DB migration fails on upgrade | try! crashes app | High | ✅ Fixed — crash recovery recreates DB |
| Very large DB (>1GB) | Performance degrades | Medium | ❌ No DB size monitoring or cleanup |
| Messages table grows unbounded | No cleanup mechanism | Medium | ❌ Should offer "clear old messages" |
| Settings key collision between ops | Settings are global, not per-Op | Medium | ❌ Engine config is global, should it be per-Op? |

---

## 11. Onboarding

| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| User skips model selection | No model loaded, engine can't start | High | ❌ Should require model or show clear warning |
| User selects model folder without safetensors | Validation checks config.json only | Medium | ❌ Should also check for .safetensors files |
| Language selection doesn't persist if app crashes before completing onboarding | Onboarding restarts | Low | ❌ Should persist language choice immediately |
| Model tier cards not clickable (just display) | Must use Browse button | Medium | ❌ UX confusion — tier cards should trigger download |

---

## 12. CVE Knowledge Base

| Edge Case | Current Behavior | Risk | Fix |
|-----------|-----------------|------|-----|
| NVD API rate limit hit (5 req/30s without key) | 6s sleep between requests | Medium | ✅ Handled |
| NVD API down | Import fails with error message | Low | ✅ Shows error |
| CVE DB empty (never imported) | search_cve returns empty | Medium | ❌ Should prompt user to import |
| Semantic search with empty query | May crash or return all | Low | ❌ No guard on empty query |
| 250K+ CVEs in DB, slow search | No indexing on all fields | Medium | ❌ Need proper indices |

---

## Priority Fixes (Critical/High Only)

### CRITICAL
1. **run_shell dangerous command blocklist** — rm -rf, mkfs, etc.
2. **Scope enforcement on tool targets** — check target params against Op scope
3. **Tool output size cap** — prevent OOM from massive tool output

### HIGH
4. **Send guard while streaming** — reject or queue new messages during generation
5. **Stop generation on Op switch** — don't leave orphan tasks
6. **Engine reconnection context** — re-send system prompt after crash/restart
7. **RAM check before model load** — warn if model exceeds available memory
8. **Model path validation** — check safetensors exist before engine launch
9. **Terminal cleanup on app exit** — kill terminal process


---

## TODO: Remaining Edge Case Fixes

### TODO-1: Scope Enforcement on Tool Targets
- **Files:** ToolDefinitions.swift (buildCliArgs), ChatService.swift (tool execution loop), AppState.swift (Op scope)
- **What:** Before executing any tool, extract the target parameter and check against the Op's scope field
- **Dependencies:** Op.scope must be parsed into allowed domains/IPs/CIDRs. Need a ScopeChecker utility.
- **Sub-items:**
  - [ ] Parse Op.scope text into structured allowed targets (domains, wildcards, CIDRs)
  - [ ] ScopeChecker.isInScope(target: String, scope: ParsedScope) → Bool
  - [ ] Check target param from tool_call arguments before execution
  - [ ] In Autopilot: block out-of-scope, log warning to activity feed
  - [ ] In Copilot: show warning on approval card "⚠ Target may be out of scope"
  - [ ] In Manual: no enforcement (user controls)
  - [ ] Scope enforcement toggle in Op settings (strict/warn/off)

### TODO-2: Engine Reconnection Context After Crash
- **Files:** EngineManager.swift (onCrash handler), ChatService.swift (system prompt), AppState.swift
- **What:** After engine crash+restart, re-send system prompt + phase guidance + last N messages so model has context
- **Dependencies:** Engine must be healthy before re-sending. ChatService.baseURL must be updated.
- **Sub-items:**
  - [ ] EngineManager.onCrash callback already exists — wire to AppState
  - [ ] After restart confirmed healthy, set chatService.baseURL
  - [ ] Re-inject phaseGuidance into chatService
  - [ ] Send last 10 messages as context (not full history — may exceed context window)
  - [ ] Show "Engine reconnected — context restored" banner in activity feed
  - [ ] If Autopilot was running, resume from where it left off

### TODO-3: RAM Check Before Model Load
- **Files:** EngineManager.swift (start method), SettingsView.swift, OnboardingView.swift
- **What:** Check ProcessInfo.processInfo.physicalMemory against estimated model RAM before launching engine
- **Dependencies:** Model size estimation from folder size or jang_config.json
- **Sub-items:**
  - [ ] Read model folder size (sum of .safetensors files)
  - [ ] Estimate RAM needed: folder size × 1.2 (overhead for KV cache, tokenizer, etc.)
  - [ ] Compare against physicalMemory
  - [ ] If insufficient: show warning dialog "Model needs ~X GB but you have Y GB. Continue anyway?"
  - [ ] User can override (some models fit in less than file size suggests due to quantization)
  - [ ] Show RAM estimate in model selection UI (Settings + Onboarding)

### TODO-4: Copilot Approval Timeout
- **Files:** ChatService.swift (approval continuation)
- **What:** Auto-reject approval after configurable timeout (default 5 minutes) to prevent infinite suspension
- **Dependencies:** None — self-contained in ChatService
- **Sub-items:**
  - [ ] Add timeout task alongside withCheckedContinuation
  - [ ] After timeout: auto-resume with .reject
  - [ ] Show "Approval timed out — tool call rejected" in chat
  - [ ] Configurable timeout in settings (1min, 5min, 15min, never)
  - [ ] Visual countdown on approval card (optional)

### TODO-5: Phase Persistence Per-Op in DB
- **Files:** AppState.swift, Database.swift, Op.swift
- **What:** Save current phase to DB when it changes, restore when Op is loaded
- **Dependencies:** Need new column in ops table or use settings table with op-scoped key
- **Sub-items:**
  - [ ] Add DB migration: ALTER TABLE ops ADD COLUMN currentPhase TEXT DEFAULT 'scan'
  - [ ] AppState.advancePhase() → save to DB
  - [ ] AppState.setPhase() → save to DB
  - [ ] AppState.switchOp() → load phase from DB
  - [ ] AppState.createOp() → initialize phase to 'scan' in DB
  - [ ] Also persist phaseToolsRun per-Op (or accept it resets on switch)

### TODO-6: Terminal Process Cleanup on App Exit
- **Files:** ExploitBotApp.swift, TerminalPanelView.swift
- **What:** Kill the terminal's shell process when the app quits
- **Dependencies:** Need reference to the LocalProcessTerminalView's process
- **Sub-items:**
  - [ ] Store terminal process reference in AppState or TerminalPanelView
  - [ ] On app willTerminate / scenePhase .background: send SIGTERM to terminal process
  - [ ] SwiftTerm's LocalProcessTerminalView may handle this automatically — verify
  - [ ] If multiple terminal tabs (future): kill all terminal processes
  - [ ] Also kill on window close if "minimize to tray" is disabled

### TODO-7: Model Path Validation (Check Safetensors Exist)
- **Files:** SettingsView.swift (pickModelFolder), OnboardingView.swift, EngineManager.swift (start)
- **What:** Before launching engine, verify model folder contains required files
- **Dependencies:** None — file system check
- **Sub-items:**
  - [ ] Check for config.json (already done in pickModelFolder)
  - [ ] Check for at least one .safetensors file
  - [ ] Check for tokenizer.json or tokenizer_config.json
  - [ ] Optional: check for jang_config.json → show "JANG format detected" badge
  - [ ] If missing files: show specific error "Missing: tokenizer.json, *.safetensors"
  - [ ] Validate BEFORE engine launch (not just in file picker — also in start())
  - [ ] Show validation result in Settings model card (✅ valid / ⚠ missing files)

---

## Final Review: Things To Think About

### Things That Work But Could Be Better
1. **Chat panel width is fixed 380px** — not resizable, can't be hidden to give more room to tool tabs
2. **Activity feed height fixed 180px** — not resizable
3. **No dark mode variants** — we're dark-only which is fine, but no accent color customization
4. **No undo for Op delete** — delete is permanent, no trash/archive
5. **Tab buttons send natural language to model** — works but model may interpret differently than intended. Consider sending structured tool calls directly from buttons instead

### Things That Could Break in Production
1. **Concurrent model access** — if two Ops somehow both send requests, the model will interleave. Currently prevented by send guard but could happen in edge cases
2. **Large conversation context** — no automatic summarization or truncation. Long pentesting sessions will eventually exceed context window
3. **Tool output encoding** — some tools output Latin-1 or other encodings, we assume UTF-8
4. **Homebrew path on Intel Macs** — we check /opt/homebrew/bin (arm64) but not /usr/local/bin first (Intel). Actually we do check both — OK
5. **Python version** — engine tested on 3.14, may have issues on 3.11/3.12

### Things Users Will Ask About
1. "How do I add my own tools?" — no custom tool definition UI
2. "Can I use OpenAI/Claude instead of local?" — no remote API support
3. "How do I export my findings to Jira/GitHub?" — no integration
4. "Can multiple users share an engine?" — no, single-user design
5. "Does it work on iPad?" — no, macOS only

### Cache Stack Verification (from vMLX)
- [x] prefix_cache.py — 1825 lines, identical to vMLX source
- [x] paged_cache.py — 1370 lines, identical to vMLX source
- [x] memory_cache.py — 778 lines, identical to vMLX source
- [x] scheduler.py — 2576 lines (52 fewer than vMLX — stripped multi-user batching)
- [x] disk_cache.py — present (not used in single-user but no harm)
- [x] block_disk_store.py — present
- [N/A] mllm_cache.py — correctly stripped (VLM only)
- [N/A] vision_embedding_cache.py — correctly stripped (VLM only)
- [x] KV cache quantization (none/q4/q8) — settings UI + engine support
- [x] Paged cache block size — configurable in EngineConfig (default 64)
- [x] Prefix cache memory % — configurable in EngineConfig (default 0.20)

All cache features from vMLX are present and functional for text-only inference.

---

## v1.0 Polish Items (Pre-Ship)

### QUICK FIXES
- [ ] Wire "Create Finding" buttons on VulnCards → findingPrefill + showFindingWizard
- [ ] Inference logs button (lazy — only captures when user has panel open)
- [ ] Chat panel resizable (drag handle on left edge)
- [ ] Activity feed resizable (drag handle on top edge)

### MEDIUM FEATURES
- [ ] Context window management (auto-summarize when approaching limit)
- [ ] Custom tool definitions (user adds JSON tool schemas via Settings)
- [ ] Scope enforcement (check tool targets against Op scope)

### NICE-TO-HAVE (post v1.0)
- [ ] Remote API support (OpenAI/Claude as alternative to local)
- [ ] Jira/GitHub issue integration for findings export
- [ ] Custom tool UI (visual tool builder)

---

## NEXT SESSION: Tool Bundling & Installation

### Plan
Bundle lightweight Go/Rust tools as arm64 binaries in .app Resources.
Heavy tools stay as user-installed via homebrew/pip.

### Bundle list (~150MB total):
- subfinder, dnsx, httpx, nuclei, katana (ProjectDiscovery suite)
- feroxbuster, ffuf, dalfox, arjun
- haiti, chisel, trufflehog
- sherlock, holehe
- testssl.sh, jwt_tool, graphqlmap
- exiftool, gowitness
- linpeas.sh, winpeas.exe (scripts, not binaries)
- seclists (wordlists, ~200MB — optional download)

### User-install list:
- nmap, masscan (brew install)
- hashcat (brew install)
- metasploit (brew install --cask metasploit)
- sqlmap, impacket, pwntools, pwncat (pip install)
- netexec, hydra (brew/pip)
- bettercap, tshark, sliver (brew)

### Steps for next session:
1. Download arm64 binaries for each bundled tool
2. Add to ExploitBot/Resources/tools/
3. Update ToolExecutor.findBinary() to check bundle Resources first
4. Update project.yml to include tools in extraResources
5. Test each tool executes from bundle
6. Rebuild DMG with bundled tools
