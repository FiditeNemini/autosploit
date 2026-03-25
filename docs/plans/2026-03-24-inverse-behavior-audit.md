# exploitbot — Inverse Behavior & Edge Case Audit

**Date:** 2026-03-24
**Method:** For each component, ask "what happens when X" for every possible state combination.

---

## 1. BUTTONS — What does each button do in every state?

### Chat Send Button (↑ / ■)
| State | Action | Behavior | OK? |
|-------|--------|----------|-----|
| Idle + text entered | Click | Sends message, starts streaming | ✅ |
| Idle + empty text | Click | Nothing (guard !text.isEmpty) | ✅ |
| Streaming | Click | Stops generation (isStopped=true) | ✅ |
| Streaming + approval pending | Click | Stops + rejects approval | ✅ |
| No engine running | Click | Sends request, gets connection error in chat | ⚠️ Should show "Engine not running" |

### Tab Run Buttons (Full Recon, Scan, Search, etc.)
| State | Action | Behavior | OK? |
|-------|--------|----------|-----|
| Empty target field | Click | guard !target.isEmpty returns | ✅ |
| Target entered + idle | Click | Sends natural language to chatService | ✅ |
| Target entered + streaming | Click | chatService.send() rejected by isStreaming guard | ✅ |
| No engine running | Click | Request fails, error in chat | ⚠️ Should check engine first |

### Stop Button (⏹ in chat)
| State | Action | Behavior | OK? |
|-------|--------|----------|-----|
| Not streaming | Click | Does nothing (sendMessage checks isStreaming) | ✅ |
| Streaming text | Click | Sets isStopped, cancels task | ✅ |
| Tool executing | Click | isStopped + toolExecutor.cancel() + SIGTERM | ✅ |
| Approval pending | Click | Rejects approval continuation | ✅ |
| Multiple tools chaining | Click | Stops after current tool | ✅ |

### New Op Button (+)
| State | Action | Behavior | OK? |
|-------|--------|----------|-----|
| Idle | Click | Creates "New Op", switches to it | ✅ |
| Streaming | Click | Creates op (doesn't stop streaming) | ⚠️ Should stop first |
| 100+ ops | Click | Creates another, sidebar scrolls | ✅ |

### Mode Selector (Autopilot/Copilot/Manual)
| State | Action | Behavior | OK? |
|-------|--------|----------|-----|
| Idle | Switch | Updates mode in state + chatService + DB | ✅ |
| Mid-streaming | Switch | Mode changes, next tool call uses new mode | ✅ |
| Approval pending + switch to Autopilot | Switch | Approval still pending (dangling) | ⚠️ Should auto-approve or reject |

### Phase Buttons (Next Phase →, click phase name)
| State | Action | Behavior | OK? |
|-------|--------|----------|-----|
| Idle | Click Next | Advances phase, logs to feed | ✅ |
| Already at BREACH | Click Next | No-op (advancePhase returns early) | ✅ |
| Click same phase | Click | setPhase to same — no-op effectively | ✅ |
| Mid-streaming | Click | Phase changes, next model call gets new guidance | ✅ |

### Terminal Toggle (⌨)
| State | Action | Behavior | OK? |
|-------|--------|----------|-----|
| Terminal hidden | Click | Shows terminal, hides activity feed | ✅ |
| Terminal shown | Click | Hides terminal, shows activity feed | ✅ |
| Mid-tool-execution | Click | Terminal toggle doesn't affect tool execution | ✅ |

### Settings (⚙)
| State | Action | Behavior | OK? |
|-------|--------|----------|-----|
| Idle | Click | Opens settings overlay | ✅ |
| Mid-streaming | Click | Settings open, streaming continues behind | ✅ |
| Settings open + Apply | Click | Saves config, restarts engine | ✅ |
| Settings open + streaming | Apply | Should stop streaming first | ⚠️ Engine restart kills connection |

---

## 2. PANELS — State combinations

### Chat Panel + Activity Feed
| Scenario | Expected | Actual | OK? |
|----------|----------|--------|-----|
| Tool runs → activity feed updates | Real-time entries | ✅ Works | ✅ |
| Tool runs → chat shows tool card | Cyan card with output | ✅ Works | ✅ |
| Resize chat panel very narrow (280px) | Bubbles wrap | Works but may look cramped | ⚠️ |
| Resize activity feed to 80px | Only 2-3 entries visible | Works | ✅ |

### Terminal Panel
| Scenario | Expected | Actual | OK? |
|----------|----------|--------|-----|
| Terminal open + tool runs via chat | Tool runs in subprocess (not terminal) | Correct — separate | ✅ |
| Type in terminal while model streaming | Both work independently | ✅ | ✅ |
| App quit with terminal open | Terminal process should be killed | Not verified | ⚠️ |

---

## 3. PAGES/TABS — Switching during operations

| Scenario | Expected | Actual | OK? |
|----------|----------|--------|-----|
| Switch tab while model streaming | Chat continues, tab changes visually | ✅ | ✅ |
| Switch tab while tool executing | Tool continues, results appear in correct tab | ✅ | ✅ |
| Auto-tab tracking switches tab | User sees relevant tab | ✅ | ✅ |
| User manually switches tab during auto-track | User's choice should stick | ⚠️ Next tool call may switch it back |
| Switch to Report tab with 0 findings | Shows empty state with "Create Finding" button | ✅ | ✅ |
| Switch to Stash tab with 0 items | Shows "Stash is empty" | ✅ | ✅ |

---

## 4. TOOLS — Execution edge cases

| Scenario | Expected | Actual | OK? |
|----------|----------|--------|-----|
| Tool not installed | ToolResult with "not found" error | ✅ | ✅ |
| Tool installed but wrong version | Tool runs, may produce unexpected output | Handled by parser | ✅ |
| Tool outputs >10MB | Process killed at 10MB cap | ✅ | ✅ |
| Tool hangs forever | 300s timeout → SIGTERM → SIGKILL | ✅ | ✅ |
| Tool requires sudo | Permission denied error | ⚠️ No sudo prompt mechanism |
| run_shell with "rm -rf /" | Blocked by dangerous command blocklist | ✅ | ✅ |
| Tool called with out-of-scope target | Blocked by ScopeChecker | ✅ | ✅ |
| Tool returns non-UTF8 binary output | strippingANSI may produce empty string | ⚠️ Could show "[binary output]" |
| 39th tool (run_shell) called in Manual mode | Shows "suggested" message | ✅ | ✅ |

---

## 5. STASH — Operations

| Scenario | Expected | Actual | OK? |
|----------|----------|--------|-----|
| Stash from chat (📦 button) | Content saved to DB | ✅ | ✅ |
| Stash from VulnCard | Not wired yet | ⚠️ onStash callback is nil |
| Delete stash item | Removed from DB + UI | ✅ | ✅ |
| "→ Send" stash item to chat | Content sent as user message | ✅ | ✅ |
| Send very large stash item (>100KB) | Entire content sent to model | ⚠️ Should truncate |
| Switch ops | Stash stays (global) | ✅ | ✅ |
| 1000+ stash items | No warning | ⚠️ Should warn |
| Search stash | Filters by label+content | ✅ | ✅ |

---

## 6. CONVERSATION CONTEXT

| Scenario | Expected | Actual | OK? |
|----------|----------|--------|-----|
| Short conversation (<100 messages) | All sent to model | ✅ | ✅ |
| Long conversation (>500 messages) | Sliding window trims old messages | ✅ | ✅ |
| Clear context (⌘K) | All messages removed | ✅ | ✅ |
| Clear context during streaming | Should stop first, then clear | ⚠️ Currently just clears |
| Switch ops | Messages saved, new op loaded | ✅ | ✅ |
| App restart | Messages restored from DB | ✅ | ✅ |
| Approval card in saved messages | Loaded as .approval role | ✅ Fixed | ✅ |
| Phase guidance in system prompt | Updated per phase | ✅ | ✅ |
| Scope in system prompt | Not included | ⚠️ Model doesn't know the scope textually |

---

## 7. LOADING MODELS

| Scenario | Expected | Actual | OK? |
|----------|----------|--------|-----|
| Valid model path | Engine loads, health check passes | ✅ | ✅ |
| Invalid model path | Error shown in settings | ✅ | ✅ |
| Model folder missing safetensors | Engine crashes on load | ⚠️ Should pre-validate |
| VLM model (has vision_config) | Loaded as text-only | ✅ Fixed | ✅ |
| JANG v2 model | Instant mmap load | ✅ | ✅ |
| Model exceeds RAM | OOM kill | ⚠️ No pre-check |
| Change model while chatting | Engine restarts, chat disconnects | ⚠️ Should warn user |
| Engine health check fails repeatedly | Shows error | ✅ | ✅ |
| Engine crash mid-conversation | Auto-restart after 2s | ✅ | ✅ |

---

## 8. SWITCHING (Ops, Modes, Tabs)

| Scenario | Expected | Actual | OK? |
|----------|----------|--------|-----|
| Switch op while streaming | Stops streaming, saves, switches | ✅ | ✅ |
| Switch op | Messages saved + loaded, results cleared | ✅ | ✅ |
| Switch op | Phase resets to SCAN | ✅ | ✅ |
| Switch op | Mode synced from Op to ChatService | ✅ | ✅ |
| Switch op | Scope synced from Op to ChatService | ✅ | ✅ |
| Switch mode while idle | Persisted to DB + ChatService | ✅ | ✅ |
| Switch mode during approval | Approval still pending | ⚠️ Should resolve |
| Switch tab during auto-track | Auto-track may override user choice | ⚠️ |
| Delete current op | Switches to next op | ✅ | ✅ |
| Rename op | Updated in sidebar + DB | ✅ | ✅ |

---

## 9. STOP BUTTON — Comprehensive

| Scenario | Expected | Actual | OK? |
|----------|----------|--------|-----|
| Stop during text streaming | Partial text preserved | ✅ | ✅ |
| Stop during thinking block | Thinking collapses, partial content kept | ✅ | ✅ |
| Stop during tool execution | SIGTERM → 3s → SIGKILL to process | ✅ | ✅ |
| Stop during approval wait | Approval rejected, loop exits | ✅ | ✅ |
| Stop when nothing is running | No-op | ✅ | ✅ |
| Double-click stop rapidly | Second click is no-op (already stopped) | ✅ | ✅ |
| Stop then immediately send new message | New message starts fresh | ✅ | ✅ |

---

## ISSUES FOUND (to fix)

### HIGH
1. **New Op while streaming** — should stop generation first
2. **Settings Apply while streaming** — should stop generation first
3. **Mode switch while approval pending** — should resolve approval
4. **Clear context while streaming** — should stop first
5. **Scope not in system prompt** — model should know scope textually

### MEDIUM
6. **Send button when engine not running** — should show "Engine not running"
7. **Auto-tab tracking overrides user manual tab switch** — need "follow agent" to disable after manual switch
8. **Large stash item sent to chat** — should truncate for model context
9. **Model change while chatting** — should warn user

### LOW
10. **VulnCard Stash button** — onStash callback nil, needs wiring
11. **Non-UTF8 tool output** — should show "[binary output]" placeholder
12. **Terminal cleanup on quit** — need to verify SwiftTerm handles it
