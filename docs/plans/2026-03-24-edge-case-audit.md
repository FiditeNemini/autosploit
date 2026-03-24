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

