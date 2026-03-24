# exploitbot — Exhaustive Feature Matrix

**Purpose:** Complete enumeration of every feature, sub-feature, setting, interaction, edge case, and cross-cutting concern. Used for test matrix generation and implementation tracking.

---

## F001: App Lifecycle

### F001.1: Launch Sequence
- [x] App opens to last active Op (or onboarding if first run) — onboarding check via showOnboarding flag
- [x] vMLX engine spawned on random localhost port — EngineManager finds port 8100-8199
- [x] Engine health check (HTTP ping to /health with model_loaded check)
- [x] Health check retry with backoff (60 attempts, 1s interval = 60s max wait)
- [x] Model auto-loaded if previously selected — loadEngineConfig() reads from DB settings
- [ ] Orphan vMLX process detection on launch (PID file check)
- [ ] Orphan adoption or kill decision
- [x] Port collision detection — EngineManager tries bind() to verify port available
- [x] Port re-selection on collision — iterates 8100-8199 until one works
- [ ] Single instance lock (prevent double-launch)
- [ ] Second launch attempt shows "already running" and focuses existing window
- [ ] Restore window position/size from last session
- [ ] Restore active tab within active Op

### F001.2: Shutdown Sequence
- [x] Save all Op state (messages) — saveCurrentMessages() on scenePhase change
- [ ] Save window position/size
- [x] Send SIGTERM to vMLX engine — EngineManager.stop() calls process.terminate()
- [x] Wait up to 3s for graceful shutdown — DispatchQueue delay before SIGINT
- [x] SIGKILL if still alive after timeout — process.interrupt() after 3s
- [x] Kill all active tool subprocesses — ToolExecutor.cancel() sends SIGTERM
- [ ] Remove PID file
- [ ] Cleanup temp files (/tmp/exploitbot_*)
- [ ] Database WAL checkpoint on exit

### F001.3: Crash Recovery
- [ ] Detect unclean shutdown on next launch (PID file exists but process dead)
- [ ] Database integrity check (PRAGMA integrity_check)
- [ ] Corrupt DB → rename to .corrupt.timestamp, recreate, show dialog
- [x] Recover in-flight Op state from WAL journal — GRDB WAL mode handles this automatically
- [ ] Show "Recovered from crash" banner with details

### F001.4: Background Behavior
- [ ] Menu bar tray icon (optional, configurable)
- [ ] Close window = minimize to tray (if enabled) or quit
- [ ] Tray menu: Show/Quit/Current Op status
- [x] Long-running tools continue when window minimized — subprocess runs independent of UI
- [x] Autopilot continues when window minimized — Task runs in background
- [ ] macOS notification when Autopilot finds a vulnerability (if minimized)

---

## F002: Onboarding (First Run)

### F002.1: Language Selection
- [ ] Step indicator: dot 1 active, dots 2-4 inactive
- [ ] Title: "Choose your language" displayed in current language
- [ ] Description text: explains what language affects (menus, tools, reports)
- [ ] 5 language cards in grid:
  - [ ] 🇺🇸 English card (default selected)
  - [ ] 🇰🇷 한국어 (Korean) card
  - [ ] 🇨🇳 中文 (Chinese) card
  - [ ] 🇪🇸 Español (Spanish) card
  - [ ] 🇯🇵 日本語 (Japanese) card
- [ ] Each card shows: flag emoji, native name, English name
- [ ] Click card → selected border style (white border)
- [ ] Click card → ALL UI text immediately translates:
  - [ ] Screen title translates
  - [ ] Screen description translates
  - [ ] Step labels translate (Language/Model/Tools/First Op → 언어/모델/도구/첫 Op etc.)
  - [ ] Button text translates (Continue → 계속 etc.)
  - [ ] All subsequent screens pre-translated
- [ ] Only one card selectable at a time
- [ ] Back button: hidden (first screen)
- [ ] Skip button: hidden (language required)
- [ ] Continue button: enabled always (default English)
- [ ] Language stored in settings DB
- [ ] Language persists across app restarts

### F002.2: Model Download
- [ ] Step indicator: dot 1 done (✓), dot 2 active
- [ ] Title: "Download a model" (translated)
- [ ] Description: explains tier selection (translated)
- [ ] RAM detection banner:
  - [ ] Auto-detect via ProcessInfo.processInfo.physicalMemory
  - [ ] Display: "Detected: X GB Unified Memory"
  - [ ] Tiers exceeding RAM are dimmed/disabled
  - [ ] Banner color: blue info style
- [ ] 3 tier cards (S/M/L):
  - [ ] **S card** (~30 GB, 32+ GB RAM):
    - [ ] Model: Qwen3.5-VL-122B-A10B-UNCENSORED-JANG_2S
    - [ ] HF link: dealignai org (clickable, opens browser)
    - [ ] "UNCENSORED" badge in green
    - [ ] Vision capable indicator
  - [ ] **M card** (~60 GB, 64+ GB RAM):
    - [ ] Model: MiniMax-M2.5-UNCENSORED-JANG_2L
    - [ ] "REC" recommended badge (top-right)
    - [ ] HF link: dealignai org
    - [ ] "UNCENSORED" badge in green
  - [ ] **L card** (~112 GB, 128+ GB RAM):
    - [ ] Model: Qwen3.5-VL-397B-A17B-UNCENSORED-JANG_1L
    - [ ] HF link: dealignai org
    - [ ] "UNCENSORED" badge in green
    - [ ] Vision capable indicator
- [ ] Click tier card → selected border, starts download
- [ ] Only one tier selectable at a time
- [ ] Custom HuggingFace URL input:
  - [ ] Text field below tier cards
  - [ ] Label: "Or paste a HuggingFace model URL:"
  - [ ] Placeholder: "https://huggingface.co/..."
  - [ ] URL validation on blur (check HF API for model existence)
  - [ ] Invalid URL → red border + error message
- [ ] **"Load Local Model" button** (below custom URL):
  - [ ] Label: "Or select a model folder already on your Mac"
  - [ ] Opens native macOS folder picker (NSOpenPanel)
  - [ ] Validates folder contents:
    - [ ] Must contain: config.json + tokenizer.json/tokenizer_config.json + *.safetensors
    - [ ] JANG detection: checks for jang_config.json → reads profile, bits, group_size
    - [ ] Standard MLX detection: config.json model_type + safetensors
    - [ ] Architecture detection via detectModelConfigFromDir() (same as vMLX)
  - [ ] Shows detected model info card:
    - [ ] Model name (from config.json model_type or folder name)
    - [ ] Architecture (Qwen2.5, MiniMax, Llama, etc.)
    - [ ] Format badge: "JANG 2-bit" / "JANG 4-bit" / "MLX fp16" / "MLX q4" etc.
    - [ ] JANG profile if applicable (JANG_1L, JANG_2L, JANG_2S, JANG_4M, JANG_6M)
    - [ ] Total size on disk
    - [ ] Estimated RAM requirement (from model size + cache overhead)
    - [ ] RAM warning if model exceeds detected system memory
  - [ ] Invalid folder → error: "Not a valid MLX/JANG model. Missing: [files]"
  - [ ] "Use This Model" button → stores path reference (not copied), proceeds
  - [ ] Scan common paths option:
    - [ ] ~/.cache/huggingface/hub/
    - [ ] ~/models/
    - [ ] Shows found JANG/MLX models in a list
    - [ ] Click to select
- [ ] Download progress area (appears when tier selected):
  - [ ] Progress bar: gradient fill (blue→purple), percentage width
  - [ ] Left text: model name + format
  - [ ] Right text: "X.X GB / Y GB · Z MB/s · ~N min left"
  - [ ] Pause button: ⏸ toggles to ▶ Resume
  - [ ] Cancel button: ✕ with red text
  - [ ] Pause state: progress bar frozen, speed shows "paused"
  - [ ] Cancel: hides progress area, resets selection
  - [ ] Complete state: bar turns green, text shows "Complete ✓"
  - [ ] Download uses HTTP range requests for resume after pause
- [ ] Disk space check:
  - [ ] Before download starts: compare needed vs available
  - [ ] Insufficient: warning banner "Need X GB, only Y GB available"
  - [ ] Download blocked until space freed
- [ ] Network failure during download:
  - [ ] Auto-pause with notification
  - [ ] "Retry" button appears
  - [ ] Already-downloaded bytes preserved for resume
- [ ] "Skip for now" button visible
- [ ] Back button: returns to language selection
- [ ] Continue button: disabled until download complete or skipped

### F002.3: Tool Installation
- [ ] Step indicator: dots 1-2 done (✓), dot 3 active
- [ ] Title: "Tool status" (translated)
- [ ] Description: explains bundled vs installable (translated)
- [ ] Summary bar: "22 bundled ✓" (green) + "16 need install" (gray)
- [ ] Tool grid (3 columns, scrollable):
  - [ ] Each tool item shows:
    - [ ] Status icon: green ✓ (installed), gray — (missing), blue ⟳ (installing)
    - [ ] Tool name (monospace)
    - [ ] Tag: "bundled" (green) or "install" (blue, clickable)
  - [ ] 22 bundled tools listed with green status:
    - [ ] subfinder, dnsx, httpx, nuclei, katana, feroxbuster, ffuf, dalfox, arjun, chisel, haiti, trufflehog, testssl.sh, sherlock, holehe, exiftool, gowitness, jwt_tool, graphqlmap, linpeas, winpeas, seclists
  - [ ] 16 installable tools listed with gray status:
    - [ ] nmap, masscan, sqlmap, wpscan, theHarvester, hashcat, hydra, netexec, snmpwalk, tshark, bettercap, impacket, metasploit, pwncat, pwntools, sliver
- [ ] Click "install" tag on individual tool:
  - [ ] Status changes to blue ⟳ (installing)
  - [ ] Install command runs (homebrew/pip/go)
  - [ ] Success: changes to green ✓ + "bundled" → "installed" tag
  - [ ] Failure: changes to red ✗ + "retry" tag + error tooltip
- [ ] "Install All" button:
  - [ ] Installs all missing tools sequentially
  - [ ] Progress shown per tool
  - [ ] Partial failure: shows which failed, others continue
- [ ] Dependency detection:
  - [ ] Homebrew: check `which brew`, prompt install if missing
  - [ ] Python3: check `which python3`
  - [ ] Go: check `which go` (only if needed)
  - [ ] Xcode CLI: check `xcode-select -p`
  - [ ] Missing dependency: banner "Homebrew required for some tools. Install?"
- [ ] PATH verification:
  - [ ] After each install: verify binary executable from app's PATH
  - [ ] PATH includes: ~/.exploitbot/tools/ + bundled tool paths
- [ ] "Skip for now" button visible
- [ ] Back button: returns to model download
- [ ] Continue button: always enabled (tools optional for basic use)

### F002.4: First Op Creation
- [ ] Step indicator: dots 1-3 done (✓), dot 4 active
- [ ] Title: "Create your first Op" (translated)
- [ ] Description: explains what an Op is (translated)
- [ ] Op Name field:
  - [ ] Text input, required
  - [ ] Placeholder: "e.g. Acme Corp External, Bug Bounty H1, Lab Practice"
  - [ ] Validation: non-empty, max 100 chars
  - [ ] Empty on submit: red border + "Name required" message
- [ ] Scope textarea:
  - [ ] Label: "Scope (optional)"
  - [ ] Sublabel: "In-scope targets — one per line. Domains, IPs, CIDR ranges."
  - [ ] Monospace font
  - [ ] Placeholder: "acme.com\n*.acme.com\n104.21.32.0/24"
  - [ ] Resizable vertically
  - [ ] Supports: domains, wildcards (*.domain.com), IPs, CIDR notation
  - [ ] Validation: each line checked for valid format
- [ ] Interaction Mode selector (3 cards):
  - [ ] **Autopilot card** (🤖):
    - [ ] Name: "Autopilot"
    - [ ] Description: "Full autonomous. Give a prompt, watch it work."
    - [ ] Selected by default
    - [ ] Selected state: white border
  - [ ] **Copilot card** (🤝):
    - [ ] Name: "Copilot"
    - [ ] Description: "AI suggests, you approve. Safer for live targets."
  - [ ] **Manual card** (🎯):
    - [ ] Name: "Manual"
    - [ ] Description: "You drive. AI assists in chat only."
  - [ ] Only one selectable at a time
- [ ] Scope enforcement toggle:
  - [ ] Toggle switch + label: "Enforce scope (block out-of-scope targets)"
  - [ ] Default: on (checked)
  - [ ] Toggle track: green when on, gray when off
- [ ] Back button: returns to tool installation
- [ ] Skip button: hidden (Op required to proceed)
- [ ] "Start Op →" button:
  - [ ] Validates Op name
  - [ ] Creates Op in database
  - [ ] Sets as active Op
  - [ ] Transitions to main workspace
  - [ ] Op appears in sidebar immediately

---

## F003: Ops System

### F003.1: Op CRUD
- [x] Create new Op (name, mode) — AppState.createOp(), DB insert, appears in sidebar
  - [ ] Name validation (non-empty, max 100 chars)
  - [x] Scope field stored in DB schema (column exists)
  - [ ] Scope not exposed in creation UI yet (onboarding has it, sidebar + doesn't)
- [ ] Rename Op (inline edit in sidebar)
- [ ] Duplicate Op (copies settings, not conversation)
- [x] Delete Op — AppState.deleteOp(), cascades messages in DB
  - [ ] Confirmation dialog before delete
- [ ] Archive Op (hides from sidebar, retrievable)
- [ ] Unarchive Op

### F003.2: Op State
- [x] Status: active / paused / complete — OpStatus enum defined, stored in DB
- [x] Active = currently interacting with model
- [x] Paused = model context preserved but not active
- [x] Complete = Op marked done
  - [ ] Read-only enforcement for complete Ops not implemented
- [ ] Status auto-set: active when user interacts, paused when switching
- [ ] Manual status change via Op Controls

### F003.3: Op Scope Definition
- [x] In-scope targets: scope column in DB ops table
- [ ] Out-of-scope targets: not in DB schema yet
- [ ] Scope displayed in Op header/info panel
- [ ] Model receives scope in system prompt — base prompt has {{SCOPE_TARGETS}} template but not populated
- [ ] Tool invocations validated against scope in Copilot/Manual mode
- [ ] Autopilot mode: scope enforced, model warned if attempting out-of-scope

### F003.4: Op Context Persistence
- [x] Full message history stored in SQLite — messages table with all fields
- [x] Messages include: role, content, reasoningContent, toolName, toolStatus, tabContext, timestamp
  - [ ] token_count column not in schema
- [x] Context rebuilt from DB when switching back to Op — loadMessages(for:)
- [ ] Context token count tracked and displayed — ChatPanelView shows "0 tokens" hardcoded
- [ ] Context limit warning (approaching model's max context)
- [ ] Context management strategy applied per D007 setting

### F003.5: Op Switching
- [x] Click Op in sidebar → switches to that Op — switchOp(to:) in AppState
- [x] Previous Op messages saved — saveCurrentMessages() called before switch
- [ ] New Op's last active tab restored
- [x] Chatbox shows new Op's conversation history — loadMessages(for:) repopulates
- [ ] Activity feed shows new Op's activity — feed not persisted per-Op yet
- [ ] Stash remains global (doesn't switch) — stash not implemented yet
- [ ] Engine context switch: system prompt updated with new Op scope
- [x] Switching speed: instant UI, messages loaded synchronously from DB

### F003.6: Concurrent Ops
- [x] Multiple Ops can exist simultaneously — all stored in DB
- [ ] Background Op's Autopilot continues running — only focused Op runs
- [ ] Background Op tool results accumulated
- [ ] Notification when background Op finds something
- [ ] "Op is running in background" indicator in sidebar

---

## F004: Chat System

### F004.1: Message Input
- [x] Single-line text input with Enter to send — NSTextField wrapper (ChatInputField.swift)
  - [ ] Multi-line support (Shift+Enter for newline) — not implemented, single line only
- [x] Send button (↑ circle, toggles to ■ stop during streaming)
- [ ] Attach file button — visual placeholder only, no handler
- [ ] Paste image from clipboard
- [x] Paste text from clipboard — NSTextField supports cmd+V natively
- [ ] "Pull from Stash" button — visual placeholder only
- [ ] Character/token count indicator
- [ ] Input disabled while model is generating — can still type but send becomes stop
- [x] Stop generation button — sends isStopped flag, cancels task, kills tool subprocess
- [ ] Input history (up arrow for previous messages)

### F004.2: Message Display
- [x] User messages: right-aligned, bgSurface background
- [x] Assistant messages: left-aligned, bgInput with border
- [x] Tool call messages: cyan cards with tool name, status badge, command + output
- [x] Tool result messages: output shown in tool call card (not collapsible yet)
  - [ ] Collapsible output blocks for long results
- [x] Reasoning blocks: purple italic "💭 Thinking..." — appears during streaming, collapses after
- [ ] Code blocks: syntax-highlighted, copy button — markdown renders inline code only
- [x] Markdown rendering — Text(.init(text)) renders basic markdown (bold, italic, code, links)
  - [ ] Tables, headers, lists not fully styled
- [ ] Image display (screenshots, evidence)
- [ ] Long messages: "Show more" truncation — tool output truncated to 3KB but no UI toggle
- [ ] Timestamp on each message
- [ ] "Copy" button on each message
- [x] Text selection enabled on all message types — .textSelection(.enabled)
- [ ] "Stash this" button on each assistant message
- [ ] "Create Finding" button on relevant messages
- [ ] Scroll to bottom button when scrolled up
- [x] Auto-scroll during streaming — onChange of messages.count and currentStreamingContent
- [x] Message streaming: tokens appear as received (SSE delta.content)
- [x] Streaming reasoning: thinking block populates in real-time (delta.reasoning_content)
- [x] Empty state: robot emoji + "Ready to pentest" + "Give me a target and scope"
- [x] Streaming dots placeholder while waiting for first token

### F004.3: Chat Context Awareness
- [x] System prompt: professional red team operator identity with tool list
  - [ ] Dynamic injection of Op name, scope, mode — hardcoded prompt, {{templates}} not populated
- [ ] Tab switch appended to context
- [x] Tool results appended to context automatically — sent as [Tool Result: name] user messages
- [ ] Stash items pulled into chat
- [ ] Finding creation noted in context
- [x] Context continuity across tab switches — same ChatService.messages array

### F004.4: Chat Actions
- [x] Clear context — ⌫ button clears all messages
  - [ ] Confirmation dialog before clearing
- [ ] Export chat as Markdown
- [ ] Search within chat (cmd+F)
- [ ] Jump to message by timestamp or tool call
- [ ] Regenerate last response
- [ ] Edit and re-send a previous user message

---

## F005: Activity Feed

### F005.1: Feed Content
- [x] Model reasoning/thinking (logged after completion, truncated to 200 chars)
- [x] Tool call initiation (tool name + full command logged)
- [ ] Tool stdout streaming (real-time, character-by-character for long-running)
- [ ] Tool stderr streaming (in red/warning color)
- [x] Tool completion (success ✓ / failure ✗ with line count summary)
- [x] Tool duration (elapsed time in seconds)
- [ ] Model interpretation of results
- [ ] Model decisions ("Found X, proceeding to Y because Z")
- [ ] Stash events ("Stashed credential from hydra output") — stash not built yet
- [ ] Finding events ("Created Finding: CVE-2021-41773 on dev.acme.com") — findings not built yet
- [x] Mode transitions (logModeChange method exists, not wired to mode selector yet)
- [x] Error events (logError method exists)
- [ ] Context management events ("Summarizing old context...", "Pinned item preserved")

### F005.2: Feed UI
- [x] Scrolling log panel (bottom panel, 180px fixed height)
- [x] Auto-scroll during active output (onChange of entries.count)
- [ ] Pause auto-scroll when user scrolls up
- [ ] Resume auto-scroll button
- [x] Timestamp on each entry (HH:mm format)
- [x] Color-coded by type (tool=cyan, error=red, finding=green, reasoning=purple)
- [x] Filter buttons: All / Tools / Errors / Findings / Reasoning
- [ ] Search within feed
- [ ] Copy entry text
- [ ] Click tool call entry → scrolls to corresponding chat message
- [ ] Collapsible sections (group all output from one tool call)
- [x] Clear feed (Clear button in header)

### F005.3: Verbosity Levels
- [x] Minimal: results and decisions only (filters out toolOutput + thinking)
- [x] Normal: tool calls + results + decisions (default, filters out toolOutput)
- [x] Verbose: everything including raw stdout/stderr, model reasoning, timing
- [x] Debug: all above (currently same as verbose — HTTP/IPC logging not implemented)
- [x] Verbosity toggle in header bar (Picker dropdown)
- [x] Higher verbosity levels include all lower levels

---

## F006: Interaction Modes

### F006.1: Autopilot Mode
- [ ] **Controls bar:**
  - [ ] Mode badge: "🤖 AUTOPILOT" (green badge with border)
  - [ ] Phase indicator: "Exploitation Phase" + stats ("14 tools run · 23 findings")
  - [ ] Pause button (⏸) → suspends after current tool finishes
  - [ ] Stop button (⏹, red) → terminates current tool + stops Autopilot
  - [ ] Resume button (appears when paused)
- [ ] **Activity feed as primary UI:**
  - [ ] Full-height scrolling feed (no separate tool area — feed IS the interface)
  - [ ] Phase section headers: "Phase 1 — Reconnaissance (14:23 – 14:25)" (sticky)
  - [ ] Thinking blocks: purple italic background, model reasoning visible
  - [ ] Tool executions: tool name (cyan), command preview block, streaming output
  - [ ] Tool completions: success (green ✓) / failure (red ✗) with duration
  - [ ] Vulnerability warnings: severity badge + CVE + target + CVSS
  - [ ] Finding creation events: "★ Finding #1 created: [title]" (green, bold)
  - [ ] Stash events: "📦 Stashed: [items]"
  - [ ] Shell establishment: "Shell established!" with Session badge
  - [ ] Assessment completion: "📊 Assessment complete" with View Report / View Stash / Export PDF buttons
  - [ ] Verbose mode: raw tool stdout in collapsible code blocks
- [ ] **Behavior:**
  - [ ] User provides starting prompt → model takes over completely
  - [ ] Model selects tools autonomously, chains results
  - [ ] All tool calls auto-approved (no confirmation dialogs)
  - [ ] `run_shell` auto-approved (no confirmation)
  - [ ] Model chains phases: recon → scanning → exploitation → post-exploit → report
  - [ ] Model creates Findings automatically when vulns confirmed
  - [ ] Model creates Stash items for interesting artifacts
  - [ ] Model generates report when assessment complete (or user requests)
  - [ ] Scope enforcement: model warned/blocked from out-of-scope targets
  - [ ] Loop detection: after 3 identical tool calls, pause and notify user
- [ ] **Background mode:**
  - [ ] Autopilot continues if user switches to another Op
  - [ ] Sidebar shows "running" indicator for background Autopilot Op
  - [ ] macOS notification when background Autopilot finds critical vuln
- [ ] **Status bar (bottom):**
  - [ ] Green dot + "Autopilot running" (or "Paused")
  - [ ] Model name
  - [ ] Token count
  - [ ] Tools run count
  - [ ] Findings count
  - [ ] Active sessions list

### F006.2: Copilot Mode
- [ ] **Controls bar:**
  - [ ] Mode badge: "🤝 COPILOT" (blue badge with border)
  - [ ] Phase indicator + stats
  - [ ] "Switch to Autopilot" button
- [x] **Approval cards** (inline in chat, not modal):
  - [x] Card background: blue border with blue tint
  - [x] Header: tool icon + "Tool Request: [name]" + safety tag
  - [x] Safety tags (computed from tool name):
    - [x] "safe · passive" (green) — subfinder, dnsx, theHarvester, sherlock, holehe, etc.
    - [x] "safe · active recon" (green) — httpx, katana, gowitness
    - [x] "active · sends probes" (amber) — nuclei, sqlmap, dalfox, nmap, etc.
    - [x] "dangerous · exploitation" (red) — metasploit, pwncat, sliver, run_shell, etc.
  - [ ] Description: what the tool does and why — not shown, only command
  - [x] Command preview: full command in monospace block
  - [ ] Editable parameters: not implemented, approve/reject only
  - [x] **2 action buttons (Modify not implemented):**
    - [x] ✓ Approve (green) → resumes execution via CheckedContinuation
    - [ ] ✎ Modify → not implemented
    - [x] ✕ Reject (red outline) → logged as rejected, model sees rejection message
  - [ ] Tool chain approval: each tool approved individually (no batching)
  - [x] Approval stays until user acts (pauses conversation loop via async continuation)
- [x] **Behavior:**
  - [x] Model proposes tool → approval card shown → execution paused
  - [ ] Safe tools auto-approved (configurable) — all tools require approval currently
  - [x] All tools require approval in Copilot mode
  - [x] `run_shell` requires approval with full command visible
  - [x] User can type in chatbox while waiting for approval (but no parallel flows)
  - [ ] User can invoke tools manually from tab UIs
  - [ ] Multiple pending approvals queue — currently one at a time
- [ ] **Status bar:**
  - [ ] Blue dot + "Copilot · awaiting approval"
  - [ ] Pending approval count
- [x] **Cross-feature:**
  - [x] Mode synced from sidebar selector to ChatService.interactionMode
  - [x] Mode change logged to activity feed
  - [x] Auto-tab tracking fires on approve (not on propose)

### F006.3: Manual Mode
- [ ] **Controls bar:**
  - [ ] Mode badge: "🎯 MANUAL" (gray badge)
  - [ ] Active tab + tool indicator
  - [ ] "Switch to Copilot" button
- [ ] **Split view layout:**
  - [ ] Left: full tool parameter form (every option for the selected tool)
    - [ ] Tool name + description header
    - [ ] Form fields matching tool schema: text inputs, dropdowns, toggles
    - [ ] Command preview (monospace block, updates live as form changes)
    - [ ] "▶ Run [tool]" button
    - [ ] Results area below (table, cards, or raw output depending on tool)
  - [ ] Right: chat panel (advisor only, 380px)
    - [ ] Header: "Chat (advisor only)"
    - [ ] Message history (user questions, model advice)
    - [ ] Input: "Ask for advice..." placeholder
    - [ ] Send button
- [ ] **Behavior:**
  - [ ] Model does NOT auto-invoke tools
  - [ ] All tool execution initiated from left-panel forms
  - [ ] Model available in chat for:
    - [ ] "What should I try next?" → suggests but doesn't execute
    - [ ] "Analyze this output" → interprets pasted results
    - [ ] "Write me a payload for X" → generates code/commands
    - [ ] "Explain this CVE" → provides context
  - [ ] Tab UIs are the primary interface (chat is secondary)
  - [ ] Tool results auto-sent to chat context (model sees what you ran)
- [ ] **Status bar:**
  - [ ] Gray dot + "Manual mode"
  - [ ] "Chat only — no auto tool execution"

### F006.4: Mode Switching
- [ ] Mode selector: segmented control in sidebar footer (Autopilot/Copilot/Manual)
- [ ] Also accessible from controls bar ("Switch to X" button)
- [ ] Switching mid-Op preserves all state (messages, findings, stash, tool results)
- [ ] Switching to Autopilot: model reviews current findings and continues from current state
- [ ] Switching from Autopilot to Copilot: current tool finishes, then model proposes next step as approval card
- [ ] Switching to Manual: model stops all pending actions, UI switches to tool form view
- [ ] Notification toast: "Mode changed to [X]"
- [ ] Activity feed logs mode change event

### F006.5: Auto-Tab Tracking (Agent Execution)
- [ ] When model invokes a tool, UI auto-switches to the relevant tab
- [ ] **Tool → Tab mapping:**
  - [ ] subfinder, dnsx, nmap, masscan, httpx, katana, theHarvester → Recon tab
  - [ ] nuclei, sqlmap, dalfox, feroxbuster, ffuf, arjun, wpscan, testssl, graphqlmap, jwt_tool → Web tab
  - [ ] netexec, snmpwalk, tshark, bettercap, chisel → Network tab
  - [ ] hashcat, hydra, haiti, trufflehog → Creds tab
  - [ ] metasploit, pwncat, pwntools, sliver → Exploit tab
  - [ ] linpeas, winpeas, impacket → Post tab
  - [ ] sherlock, holehe, exiftool, gowitness → OSINT tab
  - [ ] run_shell → stays on current tab (no switch)
  - [ ] search_cve → stays on current tab (no switch)
- [ ] **Behavior:**
  - [ ] Auto-tracking enabled by default in Autopilot mode
  - [ ] Auto-tracking optional in Copilot mode (toggle in settings)
  - [ ] Auto-tracking disabled in Manual mode (user controls tabs)
  - [ ] Tab switch happens when tool START is logged (not on completion)
  - [ ] Tab switch is visual only — does not interrupt user if they manually switch away
  - [ ] "Follow agent" toggle button in controls bar — user can disable mid-session
  - [ ] When disabled, a subtle indicator shows which tab has new results ("● 3 new" badge on tab)
- [ ] **Cross-feature dependencies:**
  - [ ] Requires: onToolStart callback (F005 Activity Feed) — already implemented
  - [ ] Requires: ToolTab mapping from tool name — new lookup function needed
  - [ ] Requires: state.activeTab binding (F011 Tabs) — already implemented
  - [ ] Affects: ActivityFeedView should highlight which tab is being auto-tracked
  - [ ] Affects: Tab bar should show "new results" indicator when user has tracking disabled

### F006.6: Pentesting Phase System (Scan → Detect → Breach)
- [ ] **Three explicit phases:**
  - [ ] **Phase 1: SCAN** — Context gathering via tools
    - [ ] Objective: map attack surface (subdomains, ports, services, tech stacks)
    - [ ] Tools used: subfinder, dnsx, nmap, masscan, httpx, katana, theHarvester
    - [ ] Auto-tabs: Recon
    - [ ] Completion criteria: model determines sufficient coverage
    - [ ] Output: populated Recon tab with all discovered assets
  - [ ] **Phase 2: DETECT** — Vulnerability identification from context
    - [ ] Objective: find exploitable vulnerabilities in discovered services
    - [ ] Tools used: nuclei, sqlmap, dalfox, feroxbuster, arjun, wpscan, testssl, search_cve
    - [ ] Auto-tabs: Web, Network
    - [ ] Completion criteria: all high-value targets scanned, CVEs matched
    - [ ] Output: populated Web tab with vuln cards, CVE matches
  - [ ] **Phase 3: BREACH** — Exploitation and post-exploitation
    - [ ] Objective: exploit confirmed vulns, establish access, escalate, exfiltrate
    - [ ] Tools used: metasploit, pwncat, pwntools, sliver, linpeas, winpeas, impacket, hashcat, hydra
    - [ ] Auto-tabs: Exploit, Post, Creds
    - [ ] Completion criteria: access obtained or all exploitation paths exhausted
    - [ ] Output: active sessions, cracked credentials, privilege escalation results
- [ ] **Phase indicator UI:**
  - [ ] Displayed in controls bar: "Phase 1: SCAN" / "Phase 2: DETECT" / "Phase 3: BREACH"
  - [ ] Phase progress: filled dots (●●○) showing current phase
  - [ ] Phase stats: "12 hosts found" / "3 vulns confirmed" / "1 shell established"
  - [ ] Color per phase: SCAN=blue, DETECT=orange, BREACH=red
  - [ ] Phase transition logged in activity feed with section header
- [ ] **Phase control:**
  - [ ] Phases auto-advance in Autopilot mode (model decides when to move on)
  - [ ] User can manually advance phase ("Skip to Detect", "Skip to Breach")
  - [ ] User can go back to previous phase ("Return to Scan")
  - [ ] Phase restart: re-run current phase with new parameters
  - [ ] Phase can be skipped entirely (e.g., user already has recon data)
- [ ] **System prompt integration:**
  - [ ] Phase-specific instructions injected into system prompt
  - [ ] Phase 1 prompt emphasizes: completeness, no exploitation, passive first then active
  - [ ] Phase 2 prompt emphasizes: matching CVEs, testing all entry points, risk assessment
  - [ ] Phase 3 prompt emphasizes: exploit selection, shell stabilization, persistence, evidence collection
  - [ ] Phase transition prompt: "Recon complete. Moving to vulnerability detection. You found: [summary]"
- [ ] **Cross-feature dependencies:**
  - [ ] Requires: Activity Feed phase section headers (F005.1) — partially implemented
  - [ ] Requires: Auto-tab tracking (F006.5) — new feature
  - [ ] Requires: System prompt template variables (base.md {{PHASE}}) — needs addition
  - [ ] Affects: ResultsStore should track which phase produced each result
  - [ ] Affects: Findings should record which phase they were discovered in
  - [ ] Affects: Report generation should group findings by phase
  - [ ] Affects: Stash items should tag with source phase
  - [ ] Affects: Activity Feed should show phase transitions as sticky headers
  - [ ] Requires: ChatService needs phase state + transition logic
  - [ ] Requires: AppState needs currentPhase property
  - [ ] Requires: Op model needs phase field in DB (which phase is active/last)
- [ ] **Report integration:**
  - [ ] Attack Narrative section organized by phase
  - [ ] Phase timeline in report: "Scan: 14:23-14:25, Detect: 14:25-14:30, Breach: 14:30-14:45"
  - [ ] Phase-specific findings grouping in report summary

---

## F007: Tool System

### F007.1: Tool Registry
- [x] 39 tools defined in registry.json (was 38, added search_cve)
- [x] Each tool: name, category, description, binary, parameters, cli_mapping, output_parser, result_type
- [x] Each parameter: type, required, default, enum, description
- [ ] Registry loaded at app launch — currently hardcoded in ToolDefinitions.swift (15 tools), not loaded from JSON
- [ ] Registry validated (all binaries found or marked missing)
- [x] Tool schemas converted to OpenAI function format for model — ToolDefinitions.forModel()
  - [ ] Only 15 of 39 tools have Swift function schemas (others in JSON only)

### F007.2: Tool Execution
- [x] Subprocess spawned with argument array (Process + arguments, never shell interpolation)
- [x] Environment: PATH includes /opt/homebrew/bin + /usr/local/bin + ~/.exploitbot/tools/
- [ ] Working directory: not set per-Op yet (uses process default)
- [x] stdout captured and streamed to activity feed — readabilityHandler + onToolStart callback
- [x] stderr captured — stored in ToolResult.stderr
  - [ ] Not streamed separately to activity feed (combined on completion)
- [x] Exit code captured — process.terminationStatus
- [x] Execution time tracked — Date interval in ToolResult.duration
- [x] Timeout enforcement — 300s default per tool
- [x] Timeout action: SIGTERM → 3s → SIGKILL (via DispatchQueue delay)
- [x] Cancellation: ToolExecutor.cancel() sends SIGTERM + 3s SIGKILL
- [x] Output truncation: 3KB for chat display, full output in tool message
  - [ ] 50KB limit for model context not enforced separately
- [ ] Full output preserved in Stash — Stash not implemented
- [ ] Root-required tools: sudo prompt not implemented
- [ ] Tool not found: returns error in ToolResult but no install button in UI

### F007.3: Tool Chaining (Piping)
- [x] Model can chain tools — conversation loop feeds results back, model decides next tool
  - [ ] Not true OS-level piping (stdout→stdin), uses model context instead
- [ ] Piping via temp files
- [ ] Piping via stdin_support flag
- [x] Chain displayed in activity feed — each tool logged sequentially
- [x] Chain failure: model sees error output and can adjust strategy
- [ ] Parallel tool execution — sequential only (one at a time)
- [ ] Concurrent tool limit: not configurable

### F007.4: Tool Output Parsing (ResultsStore.swift)
- [x] ResultsStore @Observable ingests tool output and parses into typed collections
- [x] Parser types IMPLEMENTED in ResultsStore.ingest():
  - [x] line_per_result: subfinder → SubdomainEntry[] (one subdomain per line)
  - [x] jsonl: httpx → WebHostEntry[] (url, status_code, title, webserver, tech)
  - [x] jsonl: nuclei → VulnEntry[] (template-id, severity, matched-at, description, CVE)
  - [x] text: nmap → PortEntry[] (port/proto, state, service, version from table output)
  - [x] text: sherlock → OSINTEntry[] (platform, url, found from [+] lines)
- [ ] Parser types NOT YET IMPLEMENTED (defined in registry.json but no Swift parser):
  - [ ] dnsx, katana (line parsers needed)
  - [ ] masscan_json, arjun_json, ffuf_json, wpscan_json, testssl_json
  - [ ] sqlmap_log, netexec_text, snmp_text, tshark_text
  - [ ] bettercap_events, hashcat_status, hydra_text, haiti_text
  - [ ] msf_console, pwncat_events, sliver_text
  - [ ] linpeas_ansi, winpeas_ansi, impacket_text
  - [ ] holehe_csv, exiftool_json, gowitness_db
  - [ ] theharvester_xml
- [x] Raw output always stored in rawResults[] regardless of parser
- [x] Parsed data feeds into tab views via @Observable binding
- [ ] Parse failures: no fallback logging implemented
- [ ] Structured data displayed in tab-specific UI components
- [ ] Structured data also serialized into model context
- [ ] Parse failures: fall back to raw_text, log warning

### F007.5: Tool Installation Management
- [ ] Tool status tracked in DB: installed/missing/outdated/installing
- [ ] Version detection: run tool --version or equivalent
- [ ] Update check: compare installed vs latest (homebrew/pip/go)
- [ ] Update button per tool in Settings → Tools
- [ ] "Update All" button
- [ ] Uninstall button (for lazy-installed tools only)
- [ ] Bundled tools: not uninstallable, auto-updated with app updates
- [ ] Seclists: downloaded to ~/.exploitbot/wordlists/
- [ ] Seclists version/update management
- [ ] Nuclei templates: auto-update on app launch (nuclei -ut)
- [ ] Nuclei template update frequency: configurable (daily/weekly/manual)

### F007.6: Tool Security
- [ ] Parameter validation against schema before execution
- [ ] Shell metacharacter rejection in all parameters
- [ ] Argument array construction (no shell expansion)
- [ ] Scope validation: target params checked against Op scope
- [ ] Dangerous tool warnings (tools that modify target: sqlmap --os-shell, metasploit exploits)
- [ ] Copilot mode: dangerous tools require extra confirmation
- [ ] Autopilot mode: dangerous tools logged prominently in activity feed
- [ ] No tool can write to app directories or system paths

---

## F008: Stash System

### F008.1: Adding to Stash
- [ ] Right-click any tool output → "Stash this"
- [ ] Select text in chat → "Stash selection"
- [ ] Right-click assistant message → "Stash this response"
- [ ] Model auto-stashes in Autopilot (configurable)
- [ ] Stash from tab-specific UI (e.g., "Stash these subdomains" button on recon results)
- [ ] Bulk stash: select multiple items → "Stash all"
- [ ] Type auto-detection from content (regex patterns for IPs, hashes, emails, URLs)
- [ ] Manual type override after stashing

### F008.2: Stash UI
- [ ] Drawer/panel accessible from every tab (icon in Op Controls bar)
- [ ] List view: label, type icon, source Op, timestamp
- [ ] Grid view: visual cards (especially for screenshots)
- [ ] Filter by type (credential, host, vuln, code, etc.)
- [ ] Filter by source Op
- [ ] Search by content/label
- [ ] Sort by: date, type, source Op
- [ ] Select multiple items
- [ ] Delete items (single, bulk)
- [ ] Edit label/tags inline
- [ ] Preview: click item → expanded view with full content

### F008.3: Using Stash Items
- [ ] Drag item into chatbox → inserts content as message
- [ ] Drag item into tool parameter field → fills parameter
- [ ] "Send to Op" → pick target Op → inserts into that Op's chat
- [ ] "Send to Tab" → pick target Op + tab → opens tab with item ready
- [ ] "Promote to Finding" → creates Finding from Stash item(s)
- [ ] "Export" → copy to clipboard or save to file
- [ ] Stash items referenced in chat show inline preview

### F008.4: Stash Persistence
- [ ] Stored in SQLite stash_items table
- [ ] Global scope (not per-Op)
- [ ] Survives app restart
- [ ] Export all stash as JSON
- [ ] Import stash from JSON
- [ ] Max stash size: warn at 1000 items, suggest cleanup

---

## F009: Findings System

### F009.1: Finding Creation — Wizard UI
- [ ] **Trigger points:**
  - [ ] "⚡ Create Finding" button on vulnerability cards (Web tab)
  - [ ] "⚡ Create Finding" button on LinPEAS/WinPEAS results (Post tab)
  - [ ] "⚡ Finding" button on Stash items
  - [ ] Right-click assistant message → "Create Finding from this"
  - [ ] LLM-suggested: model prompts "Create a Finding?" (Copilot mode)
  - [ ] LLM auto-creates (Autopilot mode — no wizard shown, logged in activity feed)
- [ ] **Wizard modal overlay:**
  - [ ] Dark backdrop with blur (rgba(0,0,0,0.6) + backdrop-filter: blur(8px))
  - [ ] 700px wide panel, max 80vh height, scrollable body
  - [ ] Header: "⚡ Create Finding" title + close (✕) button
  - [ ] Footer: "Cancel" (secondary) + "Create Finding" (primary) buttons
- [ ] **Form fields (all pre-filled where possible):**
  - [ ] Title: text input, pre-filled from CVE description or tool finding name
  - [ ] Vulnerability Type: dropdown (RCE, SQLi, XSS, Path Traversal, Misconfig, Privesc, Info Disclosure, SSRF, CSRF, File Upload, Deserialization, Auth Bypass, IDOR, XXE, Command Injection, Other)
  - [ ] Severity: dropdown (Critical, High, Medium, Low, Info) — pre-selected from tool output
  - [ ] CVSS Score: numeric input (0.0-10.0) — pre-filled from CVE DB if CVE matched
  - [ ] Target: monospace text input — pre-filled from tool target parameter
  - [ ] Description: textarea — pre-filled from CVE description or model-generated
- [ ] **Attack Chain section:**
  - [ ] Label: "Attack Chain (auto-reconstructed from Op context)"
  - [ ] Numbered steps in a contained box:
    - [ ] Each step: circle number + description text
    - [ ] Tool names in bold within step text
    - [ ] Steps auto-populated by model from Op conversation history
    - [ ] Add step button (+)
    - [ ] Remove step button (✕ per step)
    - [ ] Drag to reorder steps
    - [ ] Edit step text inline
- [ ] **Evidence section:**
  - [ ] Label: "Evidence (auto-attached from tool outputs)"
  - [ ] Evidence items list, each showing:
    - [ ] Icon by type (📄 output, 💻 code, 🖥 session, 📸 screenshot)
    - [ ] Description text
    - [ ] Remove button (✕)
  - [ ] "Add Evidence" button → file picker
  - [ ] "From Stash" button → Stash picker (select items to attach)
  - [ ] Auto-attached: relevant tool outputs from the Op that led to this finding
- [ ] **Impact textarea:**
  - [ ] Label: "Impact (model-generated)"
  - [ ] Pre-filled by model: what an attacker can achieve
  - [ ] Editable by user
- [ ] **Remediation textarea:**
  - [ ] Label: "Remediation (model-generated)"
  - [ ] Pre-filled by model: numbered fix steps
  - [ ] Editable by user
- [ ] **Bottom row:**
  - [ ] CVE ID: monospace input — pre-filled if CVE detected, auto-suggest from CVE DB
  - [ ] Status: dropdown (Confirmed, Unconfirmed, False Positive) — default based on tool confidence
- [ ] **Validation:**
  - [ ] Title required
  - [ ] Target required
  - [ ] Severity required
  - [ ] Empty fields highlighted with warning (not blocking)
- [ ] **On "Create Finding":**
  - [ ] Saved to findings table in SQLite
  - [ ] Appears in Reporting tab findings list
  - [ ] Notification toast: "Finding created: [title]"
  - [ ] Activity feed event logged
  - [ ] If Stash items were source → linked, not copied

### F009.2: Finding Management
- [ ] Findings list in Reporting tab left panel (filterable by severity, status)
- [ ] Finding card shows: severity badge, CVSS, title, target, status, source tool
- [ ] Click finding card → opens Finding detail/edit view (same wizard form, pre-filled)
- [ ] **Status transitions:**
  - [ ] confirmed → remediated (after fix verified)
  - [ ] unconfirmed → confirmed (after manual verification)
  - [ ] any → false_positive (mark as not real)
  - [ ] Status change logged in activity feed
- [ ] Severity change: CVSS auto-suggests based on vuln type, but user override allowed
- [ ] **Evidence management:**
  - [ ] Add evidence from file picker, Stash, or clipboard
  - [ ] Remove evidence items
  - [ ] Reorder evidence
  - [ ] Preview evidence inline
- [ ] **Attack chain editor:**
  - [ ] Add/remove/reorder steps
  - [ ] Edit step descriptions
  - [ ] Model "Regenerate chain" button (re-analyzes Op context)
- [ ] Duplicate detection: warn if same CVE ID + target already exists as a Finding
- [ ] Link findings: select related findings that form a multi-step attack chain
- [ ] Delete finding with confirmation ("This cannot be undone")
- [ ] Finding edit history (last modified timestamp)

### F009.3: Finding Evidence
- [ ] Tool outputs (structured JSON from parsers)
- [ ] Screenshots (from gowitness or manual capture)
- [ ] Request/response pairs (HTTP traffic)
- [ ] Payloads used (exploit code, injection strings)
- [ ] Command outputs (raw terminal output)
- [ ] Files (downloaded from target, configs, etc.)
- [ ] Each evidence item: type, timestamp, source tool, content
- [ ] Evidence viewable inline in Finding detail
- [ ] Evidence exportable individually

---

## F010: Report Generation

### F010.1: Report Content (LLM-Generated)
- [ ] Executive Summary: 1-2 paragraphs, non-technical, business impact
- [ ] Scope & Methodology: what was tested, tools used, constraints, dates
- [ ] Findings Summary: table of all findings by severity with counts
- [ ] Detailed Findings (per Finding):
  - Title, severity, CVSS score
  - Description (what the vulnerability is)
  - Affected assets (targets)
  - Attack chain / reproduction steps
  - Evidence (screenshots, outputs, payloads)
  - Impact (what an attacker could achieve)
  - Remediation (specific fix recommendations)
- [ ] Attack Narrative: chronological story of the entire engagement
- [ ] Remediation Roadmap: prioritized fix recommendations
- [ ] Appendix: raw tool outputs, full scan results

### F010.2: Report Templates
- [ ] Full pentest report (all sections)
- [ ] Bug bounty submission (compact, per-vulnerability)
- [ ] Executive brief (summary + findings table only)
- [ ] Technical writeup (detailed technical narrative)
- [ ] Custom template support (user-created CSS + section selection)
- [ ] Each template: CSS file + section configuration

### F010.3: Report Branding
- [ ] Company logo upload (stored in settings)
- [ ] Company name
- [ ] Primary color / accent color
- [ ] Header text (e.g., "CONFIDENTIAL")
- [ ] Footer text (e.g., "Page X of Y")
- [ ] Cover page toggle
- [ ] Assessor name / contact info

### F010.4: Report Export
- [ ] PDF: via HTML → WKWebView.createPDF()
- [ ] Markdown: raw .md file
- [ ] HTML: standalone styled file (all CSS/images inlined)
- [ ] JSON: structured data (machine-readable findings)
- [ ] Export location: user picks save path via NSSavePanel
- [ ] Export progress indicator (for large PDFs)
- [ ] Preview before export (in-app rendered view)

### F010.5: Report Localization
- [ ] Report generated in app's selected language
- [ ] Model instructed to write in target language
- [ ] Section headers in target language
- [ ] Date/time formatting per locale
- [ ] CVSS descriptions in target language
- [ ] Severity labels in target language (Critical/높음/严重/Crítico/重大)

---

## F011: Per-Tab UIs

### F011.1: Recon Tab
- [ ] Target input bar (domain/IP, with "Scan" button)
- [ ] Subtab: Subdomains (tree view, sortable table)
- [ ] Subtab: Ports (port table with service info, filterable)
- [ ] Subtab: Web Hosts (live hosts with status, title, tech)
- [ ] Subtab: Crawl Results (URL tree from katana)
- [ ] Subtab: OSINT Harvest (emails, IPs, metadata)
- [ ] Quick actions: "Full Recon" button (runs subfinder → dnsx → httpx → katana pipeline)
- [ ] Manual tool controls: per-tool parameter forms
- [ ] Results displayed in structured tables/trees
- [ ] Export results button (CSV, JSON)
- [ ] "Stash all subdomains" / "Stash all live hosts" bulk action
- [ ] Network graph visualization (optional, D3-like)
- [ ] Accent color: blue

### F011.2: Web Tab
- [ ] URL input bar (target URL)
- [ ] Subtab: Vuln Scanner (nuclei results by severity)
- [ ] Subtab: SQLi (sqlmap interface + results)
- [ ] Subtab: XSS (dalfox interface + results)
- [ ] Subtab: Directories (feroxbuster/ffuf results tree)
- [ ] Subtab: Parameters (arjun discovered params)
- [ ] Subtab: CMS (wpscan results)
- [ ] Subtab: SSL/TLS (testssl results with grade)
- [ ] Subtab: GraphQL (introspection schema viewer)
- [ ] Subtab: JWT (token decoder + attack interface)
- [ ] Vulnerability cards: severity badge, CVE, description, "Create Finding" button
- [ ] Request/response viewer (for manual inspection)
- [ ] Template selector (nuclei tag filter)
- [ ] Accent color: orange

### F011.3: Network Tab
- [ ] Target input bar (IP/range)
- [ ] Subtab: Protocol Attacks (netexec — SMB/WinRM/LDAP/RDP)
- [ ] Subtab: SNMP (snmpwalk MIB browser)
- [ ] Subtab: Packet Capture (tshark live view)
- [ ] Subtab: MITM (bettercap controls)
- [ ] Subtab: Tunnels (chisel tunnel manager)
- [ ] Credential input panel (for authenticated attacks)
- [ ] Share enumeration results table
- [ ] User enumeration results
- [ ] Session list (active connections)
- [ ] Accent color: cyan

### F011.4: Credentials Tab
- [ ] Hash input area (paste hashes, upload file)
- [ ] Hash identifier (haiti — auto-detect on paste)
- [ ] Subtab: Cracking (hashcat GPU attack)
  - [ ] Attack mode selector (dict, brute, hybrid)
  - [ ] Wordlist picker (seclists browser)
  - [ ] Rule file picker
  - [ ] Mask builder (visual)
  - [ ] GPU utilization graph (Metal performance)
  - [ ] Cracking progress (speed, estimated time, cracked count)
  - [ ] Cracked hashes table
- [ ] Subtab: Online Brute (hydra)
  - [ ] Target + protocol selector
  - [ ] Username/password lists
  - [ ] Live progress (attempts, found)
- [ ] Subtab: Secret Scanning (trufflehog)
  - [ ] Repo/path input
  - [ ] Results: secret type, file, line, snippet
- [ ] Credential vault: all found credentials stored
- [ ] Vault entries: username, password/hash, source tool, target, timestamp
- [ ] Vault entries linkable to Findings as evidence
- [ ] Accent color: amber

### F011.5: Exploit Tab
- [ ] Subtab: Metasploit
  - [ ] Module search (by CVE, name, type)
  - [ ] Module detail view (description, options, targets)
  - [ ] Option configuration form
  - [ ] Payload selector
  - [ ] "Run Exploit" button
  - [ ] Session manager (active meterpreter/shell sessions)
- [ ] Subtab: Reverse Shells
  - [ ] Listener setup (pwncat — host, port, protocol)
  - [ ] Payload generator (one-liners for bash, python, powershell, etc.)
  - [ ] Active listeners list
  - [ ] Connected sessions
- [ ] Subtab: Custom Exploits
  - [ ] Code editor (syntax highlighted)
  - [ ] LLM assist: "Generate exploit for [CVE/description]"
  - [ ] Execute button with confirmation
  - [ ] Output panel
- [ ] Subtab: C2 (sliver)
  - [ ] Implant generator
  - [ ] Listener management
  - [ ] Session interaction
- [ ] Accent color: red

### F011.6: Post-Exploit Tab
- [ ] Subtab: Privilege Escalation
  - [ ] LinPEAS/WinPEAS launcher (requires active session)
  - [ ] Results: color-coded findings (95%/red, 70%/yellow, default)
  - [ ] Suggested exploits from results
- [ ] Subtab: AD Attacks (impacket)
  - [ ] Script selector (secretsdump, psexec, GetUserSPNs, etc.)
  - [ ] Target + credential input
  - [ ] Results panel
- [ ] Subtab: Lateral Movement
  - [ ] Network map of compromised hosts
  - [ ] Move from session A to target B
  - [ ] Credential reuse across hosts
- [ ] Accent color: purple

### F011.7: OSINT Tab
- [ ] Subtab: Username (sherlock)
  - [ ] Username input → 400+ platform results
  - [ ] Results: platform, URL, status, profile link
- [ ] Subtab: Email (holehe)
  - [ ] Email input → registration check
  - [ ] Results: site, registered (yes/no), method
- [ ] Subtab: Metadata (exiftool)
  - [ ] File drop zone (drag files in)
  - [ ] Metadata table (all tags)
  - [ ] GPS map (if location data present)
- [ ] Subtab: Screenshots (gowitness)
  - [ ] Gallery grid of captured screenshots
  - [ ] Click → full-size view
  - [ ] Bulk screenshot trigger
- [ ] Accent color: green

### F011.8: Reporting Tab
- [ ] Split view layout: findings list (left, 380px) + report preview (right)
- [ ] **Left panel — Findings list:**
  - [ ] Severity summary bar: 4 cards (CRIT/HIGH/MED/LOW) with counts, colored left borders
  - [ ] Finding cards, each showing:
    - [ ] Severity badge (CRITICAL/HIGH/MEDIUM/LOW/INFO)
    - [ ] CVSS score (monospace)
    - [ ] Confirmation status: confirmed (green) / unconfirmed (amber) / false_positive (red)
    - [ ] Finding title (bold)
    - [ ] Target + source tool (dim monospace)
  - [ ] Cards sorted by severity (critical first), then CVSS score
  - [ ] Click card → scrolls report preview to that finding
  - [ ] Right-click card → Edit Finding / Delete / Change Status
  - [ ] Drag card to reorder (custom report ordering)
- [ ] **Right panel — Report preview:**
  - [ ] Rendered as styled white document (light background, serif body)
  - [ ] "CONFIDENTIAL" header banner
  - [ ] Report metadata: client, date, assessor, classification
  - [ ] Sections rendered:
    - [ ] Executive Summary (1-2 paragraphs, non-technical)
    - [ ] Findings Summary table (all findings, severity, CVSS, target, status)
    - [ ] Detailed Findings (per finding: description, attack chain, impact, remediation)
    - [ ] Attack Narrative (chronological engagement story)
    - [ ] Remediation Roadmap
  - [ ] Finding boxes: colored left border by severity, CVSS badge
  - [ ] Code blocks with monospace font
  - [ ] Scrollable independently from left panel
  - [ ] Live preview: updates as findings are added/edited
- [ ] **Toolbar:**
  - [ ] Subtabs: Findings / Preview / Branding
  - [ ] Template selector dropdown: Full Pentest Report, Bug Bounty, Executive Brief, Technical Writeup
  - [ ] "Generate Report" button → LLM writes all sections
  - [ ] "Export PDF" button (blue)
  - [ ] "Export MD" button
  - [ ] "Export HTML" button
  - [ ] "Export JSON" button
- [ ] **Branding subtab:**
  - [ ] Company logo upload (drag or click to browse)
  - [ ] Company name text input
  - [ ] Primary color picker
  - [ ] Header text (e.g., "CONFIDENTIAL")
  - [ ] Footer text (e.g., "Page X of Y")
  - [ ] Assessor name / contact info
  - [ ] Preview updates live with branding changes
- [ ] **Generation features:**
  - [ ] "Generate Report" sends all Findings + Op context to model
  - [ ] Model writes executive summary, attack narrative, remediation roadmap
  - [ ] Per-section regenerate button (re-generate just that section)
  - [ ] Section editor: click any section text to edit inline
  - [ ] Report language matches app language setting
  - [ ] Generation progress indicator
  - [ ] Cancel generation button
- [ ] **Report history:**
  - [ ] Previously generated reports stored with timestamp
  - [ ] "History" button → list of past reports
  - [ ] Re-export any historical report
- [ ] Accent color: gray/neutral

### F011.9: Stash Tab (full view)
- [ ] Full-width layout (no split — Stash gets full content area)
- [ ] **Toolbar:**
  - [ ] Type filter tabs: All / Credentials / Hosts / Vulns / Code / Raw
  - [ ] Search input (searches label + content)
  - [ ] Op filter dropdown: All Ops / specific Op names
  - [ ] Export button (exports filtered set as JSON)
- [ ] **Item count summary:** "14 items · 3 credentials · 4 hosts · 3 vulns · 2 code · 2 raw"
- [ ] **Stash item list:** each item shows:
  - [ ] Type icon: 🔑 (credential), 🌐 (host/IP), ⚠️ (vulnerability), 💻 (code), 📄 (raw), 📝 (note)
  - [ ] Type icon background: amber (cred), blue (host), red (vuln), purple (code), gray (raw), green (note)
  - [ ] Label text (primary, bold)
  - [ ] Metadata line: type name · source tab · source Op · timestamp
  - [ ] Action buttons (right side):
    - [ ] "→ Send" — opens picker: which Op + which tab's chatbox
    - [ ] "⚡ Finding" — opens Finding wizard pre-filled from this item (for vuln/cred types)
    - [ ] "📋 Copy" — copies content to clipboard (for code types)
  - [ ] Click item → expanded view with full content
  - [ ] Hover → subtle border highlight
- [ ] **Bulk actions:**
  - [ ] Select multiple items (checkbox or shift+click)
  - [ ] Bulk delete
  - [ ] Bulk export
  - [ ] Bulk promote to Finding
- [ ] **Empty state:** "Stash is empty. Stash items from tool outputs, chat, or right-click menus."
- [ ] Accent color: cyan

---

## F012: Terminal

### F012.1: Terminal Emulator
- [ ] SwiftTerm-based terminal (NSViewRepresentable wrapper)
- [ ] Full interactive shell (/bin/zsh)
- [ ] ANSI color support (standard 16 colors)
- [ ] 256-color and true color support
- [ ] Unicode/emoji support
- [ ] Scrollback buffer (10,000 lines default, configurable)
- [ ] Selection and copy (⌘C)
- [ ] Paste (⌘V)
- [ ] Find in terminal (⌘F)
- [ ] Clear terminal (⌘K)
- [ ] Font: JetBrains Mono (matching app theme)
- [ ] Font size adjustable (⌘+/⌘-)
- [ ] Blinking cursor (block style)
- [ ] Colored prompt: user@exploitbot path ❯

### F012.2: Terminal Integration
- [ ] PATH includes: ~/.exploitbot/tools/ + bundled tool paths + system PATH
- [ ] Working directory: ~/.exploitbot/ops/{current_op_id}/
- [ ] **Header buttons:**
  - [ ] 💬 "Send to Chat" — captures visible output, inserts into Op chatbox
  - [ ] 📦 "Stash Selection" — stashes selected text as raw output artifact
  - [ ] ⤢ "Full Screen" — terminal expands to full workspace area
  - [ ] ✕ "Close" — hides terminal panel (⌘`)
- [ ] **Multiple terminal tabs:**
  - [ ] Tab bar in terminal header: "zsh 1", "zsh 2", etc.
  - [ ] SSH sessions shown with hostname: "ssh · dev.acme.com"
  - [ ] "+" button to add new tab
  - [ ] Click tab to switch, close tab with middle-click or ✕
  - [ ] Each tab is independent shell session
- [ ] Terminal history persists across app restarts (per-Op)
- [ ] SSH sessions supported (full interactive PTY)
- [ ] tmux/screen supported (pass-through)
- [ ] Right-click context menu: Copy / Paste / Stash / Send to Chat / Search CVE DB

### F012.3: Terminal UI
- [ ] **Position:** Bottom panel overlay (default), slides up from bottom
- [ ] **Height:** 320px default, resizable via drag handle on top border
- [ ] **Toggle:** ⌘` keyboard shortcut (or click Terminal button in tab bar)
- [ ] **Background:** Near-black with slight transparency (backdrop-filter: blur)
- [ ] **Border:** Top border separating from workspace content
- [ ] **Coexistence:** Terminal + Stash drawer can both be open simultaneously
- [ ] **Minimized state:** When closed, "Terminal" button in toolbar shows it's available
- [ ] **Full-screen mode:** Terminal expands to fill entire workspace area (tabs still visible above)
- [ ] Minimized indicator when closed ("Terminal" button in bottom bar)

### F012.4: Stash Drawer (Overlay)
- [ ] **Position:** Right-side overlay (360px), slides in from right edge
- [ ] **Trigger:** ⌘⇧S or click Stash icon in toolbar
- [ ] **Background:** Near-black with blur (backdrop-filter), drop shadow left
- [ ] **Header:** "📦 Stash" title + item count badge + close (✕) button
- [ ] **Filter tabs:** All / 🔑 Creds / 🌐 Hosts / ⚠️ Vulns / 💻 Code / 📄 Raw
- [ ] **Search input:** below filters, searches label + content
- [ ] **Item list:** scrollable, each item shows:
  - [ ] Type icon (colored background matching type)
  - [ ] Label text (truncated with ellipsis)
  - [ ] Metadata line (source + timestamp)
  - [ ] "→" send button (appears on hover)
  - [ ] Draggable: drag item to chatbox or tool input fields
- [ ] **Drag hint:** "Drag items to chatbox or tool inputs" at bottom
- [ ] **Footer buttons:** Export / Full View (opens Stash tab)
- [ ] **Coexistence:** Can be open simultaneously with Terminal panel
- [ ] **Close:** ✕ button or ⌘⇧S toggle or click outside

### F012.5: Context Menu (Right-Click Overlay)
- [ ] Appears on right-click over: tool output, chat messages, terminal text, results tables
- [ ] **Menu items:**
  - [ ] 📋 Copy (⌘C)
  - [ ] 📦 Stash this
  - [ ] ⚡ Create Finding
  - [ ] — separator —
  - [ ] 💬 Send to Chat
  - [ ] → Send to Op... (opens Op picker submenu)
  - [ ] — separator —
  - [ ] 🔍 Search CVE DB (pre-fills search with selected text)
  - [ ] 🌐 Look up on Exploit-DB (opens browser)
- [ ] Keyboard shortcuts shown (right-aligned, monospace, dim)
- [ ] Menu dismissed on click outside or Escape
- [ ] Menu positioned near cursor, constrained to window bounds
- [ ] Items grayed out when not applicable (e.g., "Create Finding" only on vuln-related content)

---

## F013: Settings

### F013.0: Settings Navigation
- [ ] Settings window: separate from main workspace (or sheet overlay)
- [ ] Left nav sidebar (200px) with 8 pages:
  - [ ] ⚙ General
  - [ ] 🧠 Model
  - [ ] ⚡ Inference
  - [ ] 🔧 Tools
  - [ ] 🛡 CVE Database
  - [ ] 📄 Reports
  - [ ] ⌨ Shortcuts
  - [ ] ℹ About
- [ ] Click nav item → shows corresponding page in right content area
- [ ] Active nav item highlighted
- [ ] Keyboard shortcut to open settings: ⌘,

### F013.1: General Settings
- [ ] **Language section:**
  - [ ] Interface Language dropdown: English / 한국어 / 中文 / Español / 日本語
  - [ ] Change takes effect immediately (no restart)
- [ ] **Window section:**
  - [ ] Close button behavior: dropdown (Quit app / Minimize to tray)
  - [ ] Start on login: toggle switch
- [ ] **Updates section:**
  - [ ] Check for updates on launch: toggle (default on)
  - [ ] Current version display (monospace)
- [ ] **Data section:**
  - [ ] Data directory display (~/.exploitbot/) + "Open in Finder" button
  - [ ] Database size display (e.g., "124 MB")
  - [ ] "Export all data" button + description "Ops, findings, stash, settings as ZIP backup"
  - [ ] "Clear Everything" button (red, danger) + warning "Deletes all Ops, findings, stash. Cannot be undone."
  - [ ] Clear confirmation dialog before executing

### F013.2: Model Settings
- [ ] Current model display (name, size, format, architecture, path)
- [ ] "Change Model" → model list with switch/download
- [ ] Model download page (curated S/M/L + custom URL)
- [ ] **"Load Local Model" button:**
  - [ ] Opens native macOS folder picker (NSOpenPanel, directory mode)
  - [ ] User selects a model folder on disk
  - [ ] Validation: check for required files:
    - [ ] config.json (required — architecture detection)
    - [ ] tokenizer.json or tokenizer_config.json (required)
    - [ ] *.safetensors files (standard MLX/JANG format)
    - [ ] jang_config.json (optional — JANG format detection, profile info)
    - [ ] model.safetensors.index.json (optional — sharded model index)
  - [ ] Invalid folder: red error "Missing required files: config.json, tokenizer.json"
  - [ ] Valid folder: show detected info:
    - [ ] Model name (from config.json or folder name)
    - [ ] Architecture (from model_type in config.json)
    - [ ] Format: JANG (if jang_config.json) or standard MLX safetensors
    - [ ] JANG profile (if applicable: JANG_1L, JANG_2L, JANG_2S, JANG_4M, etc.)
    - [ ] Quantization info (bits, group size)
    - [ ] Total size on disk
    - [ ] Estimated RAM requirement
  - [ ] "Load" button → adds to model list, starts engine with this model
  - [ ] Path stored in DB (not copied — references original location)
  - [ ] Model appears in model list alongside downloaded models
  - [ ] Removable from list (removes reference, NOT the files)
- [ ] **Scan common paths button:**
  - [ ] Auto-scans for models in:
    - [ ] ~/.cache/huggingface/hub/ (HuggingFace default cache)
    - [ ] ~/models/ (common user location)
    - [ ] ~/.exploitbot/models/ (app download location)
    - [ ] /Volumes/*/ (external drives)
  - [ ] Shows found models with format/size/architecture
  - [ ] User picks which to add to model list
- [ ] Downloaded models list (size, last used, path, delete button)
- [ ] Local models list (size, path, format, remove-from-list button)
- [ ] Model storage directory (configurable default download location)
- [ ] Inference settings (D015):
  - Temperature (slider 0.0–2.0, default 0.7)
  - Top-p (slider 0.0–1.0, default 0.9)
  - Top-k (integer, default 40)
  - Min-p (slider 0.0–1.0, default 0.05)
  - Repetition penalty (slider 1.0–2.0, default 1.1)
  - Max tokens (integer, default 4096)
  - Stop sequences (text input, comma-separated)
- [ ] Cache settings:
  - Prefix cache: toggle + memory % slider
  - Paged cache: toggle + block size
  - KV cache quantization: none/q4/q8 + group size
- [ ] Reasoning settings:
  - Enable thinking: auto/on/off
  - Reasoning parser: auto/qwen3/deepseek_r1/openai_gptoss
- [ ] Tool calling settings:
  - Tool call parser: auto (or manual selection)
  - Enable auto tool choice: toggle
- [ ] Context management strategy: none/auto_summarize/sliding_window/checkpoint
- [ ] Reset to detected defaults button
- [ ] Per-Op overrides indicator ("This Op overrides: temperature, max_tokens")

### F013.3: Tool Settings
- [ ] Installed tools list with version, path, status
- [ ] Per-tool: update button, reinstall button, uninstall button (lazy only)
- [ ] "Install All Missing" button
- [ ] "Update All" button
- [ ] Tool binary path overrides (custom paths)
- [ ] Seclists management (download, update, path)
- [ ] Nuclei template management (update, path, custom templates)
- [ ] Default timeout per tool category
- [ ] Concurrent tool execution limit (slider 1–10)

### F013.4: Report Settings
- [ ] Default template
- [ ] Company branding (logo, name, colors, header/footer)
- [ ] Default export format
- [ ] Assessor name / contact info
- [ ] Custom CSS for reports (advanced)
- [ ] Report language override (separate from UI language)

### F013.5: Keyboard Shortcuts
- [ ] Customizable keybindings (or fixed with reference)
- [ ] Defaults:
  - Cmd+N: New Op
  - Cmd+T: New terminal tab
  - Cmd+`: Toggle terminal
  - Cmd+1-8: Switch tool tabs
  - Cmd+Shift+S: Open Stash
  - Cmd+Enter: Send chat message
  - Cmd+.: Stop generation
  - Cmd+K: Clear chat
  - Cmd+,: Settings
  - Cmd+F: Search in chat/terminal

### F013.6: Privacy & Security Settings
- [ ] Autopilot: require scope definition (enforce, warn, or off)
- [ ] Tool execution logging (always log every command to audit file)
- [ ] Audit log location
- [ ] Auto-lock after inactivity (optional, with time setting)
- [ ] Lock screen with password/TouchID to resume
- [ ] Clear model context on Op pause/switch

### F013.7: CVE Database Settings
- [ ] **Status cards (3-column):**
  - [ ] Total CVEs count (e.g., 248,714)
  - [ ] CISA KEV count (e.g., 1,247) in red
  - [ ] DB size on disk (e.g., 1.2 GB)
- [ ] Last synced timestamp
- [ ] Sync frequency: dropdown (Daily / Weekly / Manual)
- [ ] Embedding model status: "nomic-embed-text-v1.5 (275 MB, CPU)" + loaded/unloaded indicator
- [ ] "Update Now" button (blue, primary)
- [ ] Update progress display during sync
- [ ] **Custom CVEs section:**
  - [ ] Custom CVE count display
  - [ ] "+ Add CVE" button → opens add form
  - [ ] "Import JSON" button → file picker
  - [ ] "Export" button → save custom CVEs
  - [ ] List of custom CVE IDs
- [ ] **Test Search:**
  - [ ] Input field with placeholder "Try: apache path traversal"
  - [ ] "Search" button
  - [ ] Results preview below

### F013.8: About Page
- [ ] App icon (bot emoji, large)
- [ ] App name: "exploitbot" with thin "bot"
- [ ] Version number (monospace)
- [ ] Tagline: "Autonomous pentesting on Apple Silicon"
- [ ] "Powered by vMLX engine · MLX inference"
- [ ] Link buttons: exploit.bot / GitHub / Report Issue
- [ ] "Open source · jjang-ai/exploitbot"

---

## F014: Internationalization (Detailed)

### F014.1: UI Strings
- [ ] Every user-visible string in String Catalog
- [ ] Pluralization rules per language
- [ ] String interpolation (e.g., "Found {count} subdomains")
- [ ] Accessibility labels localized
- [ ] Menu items localized
- [ ] Error messages localized
- [ ] Tool names NOT localized (they're proper nouns)
- [ ] Tool descriptions localized

### F014.2: CJK Considerations
- [ ] Korean, Chinese, Japanese text rendering correct
- [ ] Font fallbacks for CJK characters (PingFang SC, Hiragino, Apple SD Gothic Neo)
- [ ] Input method support (IME for CJK)
- [ ] Text wrapping correct for CJK (no mid-character breaks)
- [ ] Search works with CJK input
- [ ] Sorting considers locale-appropriate collation

### F014.3: Date/Time
- [ ] Timestamps in locale-appropriate format
- [ ] Relative time ("5 minutes ago") in each language
- [ ] Date pickers in locale format

### F014.4: Numbers
- [ ] File sizes formatted per locale (1,234 vs 1.234)
- [ ] CVSS scores always use decimal point (standard)

---

## F015: Data Management

### F015.1: Storage Locations
- [ ] ~/.exploitbot/data/exploitbot.db (SQLite database)
- [ ] ~/.exploitbot/models/ (downloaded models)
- [ ] ~/.exploitbot/tools/ (lazy-installed tool binaries)
- [ ] ~/.exploitbot/wordlists/ (seclists, custom wordlists)
- [ ] ~/.exploitbot/evidence/ (screenshots, captured files)
- [ ] ~/.exploitbot/reports/ (generated reports)
- [ ] ~/.exploitbot/templates/ (nuclei custom templates)
- [ ] ~/.exploitbot/logs/ (app logs, audit logs)
- [ ] ~/.exploitbot/config.json (settings that don't go in DB)
- [ ] /tmp/exploitbot_* (ephemeral tool outputs)

### F015.2: Database Operations
- [ ] WAL mode for concurrent access
- [ ] Auto-vacuum (incremental)
- [ ] Backup on schema migration
- [ ] Manual backup (Settings → Export Data)
- [ ] Import data from backup
- [ ] Database size monitoring (warn if > 1GB)
- [ ] Periodic temp file cleanup

### F015.3: Model Storage
- [ ] Models stored as downloaded (safetensors/JANG files)
- [ ] Model metadata tracked in DB (path, size, format, architecture)
- [ ] Delete model button (with confirmation, shows freed space)
- [ ] Model storage disk usage indicator
- [ ] Auto-detect models already downloaded to common paths (~/.cache/huggingface/)

---

## F016: Notifications

### F016.1: In-App Notifications
- [ ] Toast notifications for: Finding created, tool completed, tool failed, model error, download complete
- [ ] Toast position: top-right
- [ ] Toast duration: 5 seconds (configurable)
- [ ] Toast actions: "View", "Dismiss"
- [ ] Click toast → navigates to relevant Op/tab/finding

### F016.2: System Notifications
- [ ] macOS notification center integration
- [ ] Notify when: Autopilot finds critical vuln, tool completed (background), report generated
- [ ] Notification only when app is minimized/background
- [ ] Notification click → brings app to front, navigates to context
- [ ] Notification sound: optional (configurable)

---

## F017: Import/Export

### F017.1: Import
- [ ] Import target list (text file: one target per line)
- [ ] Import nmap XML results
- [ ] Import scope definition file
- [ ] Import Stash from JSON
- [ ] Import Op from backup file
- [ ] Drag-and-drop file into app → auto-detect type

### F017.2: Export
- [ ] Export Op as JSON/ZIP (messages, findings, stash items, evidence)
- [ ] Export all Stash as JSON
- [ ] Export findings as CSV
- [ ] Export findings as JSON
- [ ] Export tool results (per-tool, per-scan)
- [ ] Export report (F010.4)
- [ ] Export audit log

---

## F021: CVE Knowledge Base

### F021.1: CVE Database
- [ ] SQLite database with sqlite-vec extension for vector search
- [ ] Separate file: ~/.exploitbot/data/cve.db (or same DB, separate tables)
- [ ] ~250K CVEs from merged sources
- [ ] Each CVE record:
  - [ ] CVE ID (indexed, unique)
  - [ ] Description (full text, FTS5 indexed)
  - [ ] CVSS v3.1 score (float, indexed)
  - [ ] CVSS vector string
  - [ ] Severity level (critical/high/medium/low)
  - [ ] CPE 2.3 strings (affected products with version ranges)
  - [ ] Published date (indexed)
  - [ ] Modified date
  - [ ] References array (exploit-db, PoC, vendor advisory, patch URL)
  - [ ] CISA KEV flag (boolean — actively exploited)
  - [ ] Exploit availability (none/poc/weaponized)
  - [ ] Embedding vector (768-dim float32, via sqlite-vec)
- [ ] Indexes: CVE ID, CVSS score, severity, published date, CPE vendor+product

### F021.2: Data Sources (pre-bundled, merged + deduplicated)
- [ ] NVD (National Vulnerability Database) — primary source, ~250K CVEs
- [ ] Exploit-DB — CVE→exploit mapping, PoC availability
- [ ] CISA KEV (Known Exploited Vulnerabilities) — actively exploited flag
- [ ] GitHub Advisory Database — open source package vulnerabilities
- [ ] VulnCheck / OSV — modern package ecosystem coverage

### F021.3: Product Coverage (prioritized for real pentesting)
- [ ] Web servers: Apache, nginx, IIS, Tomcat, Jetty, LiteSpeed, Caddy
- [ ] CMS: WordPress (core + top 500 plugins), Drupal, Joomla, Magento, Ghost
- [ ] Frameworks: Spring, Django, Rails, Laravel, Express, Next.js, ASP.NET
- [ ] CI/CD: Jenkins, GitLab CI, GitHub Actions, TeamCity, Bamboo, ArgoCD
- [ ] Containers: Docker, Kubernetes, Helm, containerd, Podman, OpenShift
- [ ] Databases: MySQL, PostgreSQL, MongoDB, Redis, MSSQL, Oracle, Elasticsearch, CouchDB
- [ ] Mail: Exchange, Postfix, Dovecot, Zimbra, Roundcube
- [ ] VPN/Remote: OpenVPN, Fortinet, Pulse Secure, Citrix, PAN-OS, SonicWall, WireGuard
- [ ] Network equipment: Cisco IOS/ASA, Juniper, MikroTik, Ubiquiti, pfSense
- [ ] OS: Windows (Server 2016-2025, 10, 11), Linux kernel, macOS, FreeBSD
- [ ] Active Directory: AD CS, ADFS, Kerberos, LDAP, Group Policy, NTLM
- [ ] Cloud: AWS (IAM, S3, Lambda, EC2), Azure (AD, Storage, Functions), GCP
- [ ] Languages/runtimes: Node.js, Python packages, Java (Maven), Ruby (gems), PHP, Go, Rust
- [ ] Monitoring: Grafana, Prometheus, Zabbix, Nagios, Splunk, ELK stack
- [ ] File sharing: Samba, NFS, FTP (vsftpd, ProFTPD), WebDAV, SharePoint
- [ ] Virtualization: VMware (vCenter, ESXi), Proxmox, Hyper-V, QEMU/KVM
- [ ] IoT/embedded: common router/camera firmware, MQTT, CoAP, BLE stacks
- [ ] Auth: OAuth libraries, SAML, JWT libraries, Keycloak, Okta, Auth0
- [ ] Crypto/TLS: OpenSSL, GnuTLS, NSS, certificate handling libs
- [ ] Desktop: Electron apps, Chrome, Firefox, Office, Acrobat

### F021.4: Search Modes
- [ ] **Semantic search:** natural language query → sqlite-vec cosine similarity
  - [ ] "remote code execution in web servers" → matching CVEs ranked by relevance
  - [ ] "privilege escalation linux kernel" → kernel privesc CVEs
  - [ ] Uses nomic-embed-text-v1.5 embedding model (bundled, ~275MB, CPU)
  - [ ] Embedding model loaded on-demand (not always in memory)
- [ ] **CPE match:** structured vendor:product:version query
  - [ ] Exact version match + version range evaluation
  - [ ] "apache:http_server:2.4.49" → CVE-2021-41773, CVE-2021-42013
  - [ ] Version range logic: versionStartIncluding, versionEndExcluding
- [ ] **Keyword search:** FTS5 full-text search on description
  - [ ] Boolean operators: AND, OR, NOT
  - [ ] Prefix matching: "overflow*"
- [ ] **Combined mode (default):** semantic + CPE + keyword, results merged and ranked
- [ ] **Filters (stackable on any mode):**
  - [ ] Minimum severity (critical/high/medium/low)
  - [ ] Minimum CVSS score (0.0-10.0 slider)
  - [ ] Exploit available only (boolean)
  - [ ] CISA KEV only (boolean — actively exploited in the wild)
  - [ ] Published after date
  - [ ] Vendor filter
  - [ ] Product filter
  - [ ] Max results (default 20)

### F021.5: User Custom CVEs
- [ ] "Add CVE" form accessible from Settings → CVE Database
  - [ ] CVE ID field (auto-generate if internal: "CUSTOM-YYYY-NNNN")
  - [ ] Description textarea
  - [ ] Affected product (vendor, product, version)
  - [ ] Severity selector
  - [ ] CVSS score input
  - [ ] References (URLs, one per line)
  - [ ] Notes textarea (private annotations)
  - [ ] Tags (comma-separated, e.g. "internal", "client-specific", "zero-day")
- [ ] Import custom CVEs from JSON or CSV file
- [ ] Custom CVEs stored in separate table (user_cves)
- [ ] Custom CVEs merged into search results alongside NVD data
- [ ] Custom CVEs auto-embedded on save (using bundled embedding model)
- [ ] Custom CVEs editable and deletable
- [ ] Export custom CVEs as JSON
- [ ] Custom CVE count shown in Settings

### F021.6: CVE Database Updates
- [ ] Auto-sync frequency: configurable (daily/weekly/manual), default weekly
- [ ] Delta updates: only download new/modified CVEs since last sync timestamp
- [ ] NVD API 2.0: paginated requests with resultsPerPage + startIndex
- [ ] CISA KEV: single JSON file, ~50KB, check weekly
- [ ] Incremental embedding: only embed newly added CVEs
- [ ] Update progress: "Syncing CVEs... 1,247 new, 89 modified"
- [ ] Update notification toast: "CVE database updated: 47 new CVEs"
- [ ] Manual trigger: Settings → CVE Database → "Update Now" button
- [ ] Last sync timestamp displayed in Settings
- [ ] Update errors: retry with backoff, show error in Settings
- [ ] Offline mode: gracefully handle no internet (use stale data with warning)

### F021.7: CVE Integration with Tools
- [ ] `search_cve` tool in registry (model can invoke like any other tool)
- [ ] System prompt tells model: "You have a local CVE database with 250K+ CVEs. Use search_cve to find vulnerabilities for detected services."
- [ ] **Autopilot integration:**
  - [ ] After httpx/nmap service detection → auto-search CVE DB for matching versions
  - [ ] Prioritize CISA KEV (actively exploited) and weaponized exploit CVEs
  - [ ] Cross-reference multiple CVEs for attack chain planning
- [ ] **Tab integration:**
  - [ ] Web tab: "Search CVEs" button next to detected server version
  - [ ] Recon tab: auto-enrich port scan results with CVE counts per service
  - [ ] Exploit tab: CVE search feeds into metasploit module search
- [ ] **Finding enrichment:**
  - [ ] When creating a Finding, auto-suggest matching CVE ID
  - [ ] Auto-fill CVSS score from CVE data
  - [ ] Auto-fill description from CVE data
  - [ ] Link to references (exploit-db, vendor advisory)
- [ ] **Report enrichment:**
  - [ ] Findings in reports include CVE links
  - [ ] "Exploited in the wild" (CISA KEV) badge on findings
  - [ ] Remediation auto-populated from vendor advisory links

### F021.8: CVE Database UI (Settings page)
- [ ] Database statistics: total CVEs, last sync, DB size on disk
- [ ] Breakdown by severity: pie chart or bar (critical/high/medium/low)
- [ ] Top affected vendors (bar chart)
- [ ] Recent additions (list of last 20 new CVEs)
- [ ] "Update Now" button with progress
- [ ] Sync frequency selector (daily/weekly/manual)
- [ ] Custom CVEs section: list, add, import, export
- [ ] Search test: input field to test queries against the DB
- [ ] Embedding model status: loaded/unloaded, size, version

---

## F018: macOS Integration

### F018.1: Native macOS Features
- [ ] Menu bar: File (New Op, Open, Export), Edit (Undo, Copy, Paste, Find), View (tabs, terminal, stash), Window, Help
- [ ] Touch Bar support (if applicable — probably not, focus on keyboard)
- [ ] Spotlight integration (search Ops, Findings?)
- [ ] Services menu integration
- [ ] Dock badge: number of critical findings found
- [ ] Full-screen mode support
- [ ] Split view support (two exploitbot windows side by side)
- [ ] Appearance: follows system dark mode (but we're always dark)

### F018.2: Code Signing & Entitlements
- [ ] Developer ID Application: ShieldStack LLC
- [ ] Hardened runtime
- [ ] Entitlements:
  - com.apple.security.cs.allow-unsigned-executable-memory (for Python/tool execution)
  - com.apple.security.network.client (outbound connections)
  - com.apple.security.network.server (localhost server)
  - com.apple.security.files.user-selected.read-write (file access)
  - com.apple.security.files.downloads.read-write (downloads)
  - com.apple.security.process.exec (spawn tools)
- [ ] NOT sandboxed (needs full system access for tools)
- [ ] Notarization (if Apple service is working)

### F018.3: Distribution
- [ ] DMG with app + drag-to-Applications
- [ ] DMG background image (branded)
- [ ] Universal binary (arm64 only? or arm64+x86_64?)
- [ ] Minimum macOS version: 14.0
- [ ] GitHub Releases page
- [ ] Auto-update: check GitHub releases API for newer version
- [ ] Auto-update download + "Restart to update" prompt

---

## F019: Error Handling (Cross-Cutting)

### F019.1: Engine Errors
- [ ] Engine fails to start → dialog with error details + "Retry" + "Settings" buttons
- [ ] Engine crashes mid-session → auto-restart attempt, notify user, preserve context
- [ ] Engine OOM → model too large for RAM warning + suggest smaller model
- [ ] Engine port in use → auto-select different port
- [ ] Engine unresponsive → health check timeout → restart

### F019.2: Tool Errors
- [ ] Tool not found → "Install [tool]?" prompt with install button
- [ ] Tool permission denied → explain root requirement, offer sudo
- [ ] Tool timeout → show partial output, offer retry with longer timeout
- [ ] Tool crash/segfault → show exit code, stderr, suggest retry
- [ ] Tool output parse failure → show raw output, warn about parser
- [ ] Network error (tool can't reach target) → connection refused / timeout messages

### F019.3: Model Errors
- [ ] Model generates invalid tool call (bad parameters) → validate, show error, ask model to retry
- [ ] Model enters loop (repeating same action) → detect after 3 identical calls, pause and notify user
- [ ] Model exceeds context window → apply context management strategy
- [ ] Model generates harmful suggestion → scope enforcement catches it
- [ ] Streaming error (SSE disconnect) → auto-reconnect, append partial response

### F019.4: Data Errors
- [ ] Database corruption → detection, backup, recovery (F001.3)
- [ ] Settings file corruption → reset to defaults, notify user
- [ ] Model file corruption → re-download prompt
- [ ] Evidence file missing → warning icon, "Re-capture" button

---

## F020: Performance

### F020.1: UI Performance
- [ ] Smooth scrolling in chat (< 16ms frame time)
- [ ] Tab switching < 100ms
- [ ] Op switching < 500ms (UI), context re-send async
- [ ] Stash drawer open/close < 200ms
- [ ] Terminal typing latency < 50ms
- [ ] Activity feed handles 10,000+ entries without lag (virtualized list)
- [ ] Chat handles 1,000+ messages without lag (virtualized list)

### F020.2: Memory
- [ ] App memory usage monitoring (shown in debug verbosity)
- [ ] Model memory usage monitoring (GPU memory via vMLX /v1/stats)
- [ ] Memory pressure warning (system memory low)
- [ ] Aggressive model unload if system memory critical

### F020.3: Disk
- [ ] Disk usage by category (models, evidence, DB, tools, wordlists)
- [ ] Disk usage visible in Settings
- [ ] Temp file cleanup on app launch (stale /tmp/exploitbot_* older than 24h)
- [ ] Evidence auto-cleanup: warn if evidence dir > 5GB

---

## Cross-Feature Interaction Matrix (Expanded)

For each pair, specific test scenarios:

### Engine × Ops
- Engine crash while Op is in Autopilot → Op pauses, activity feed shows error, Autopilot resumes after engine restart
- Switch Op while tool is running → tool continues for previous Op (background)

### Stash × Findings
- Promote multiple Stash items to Finding → wizard pre-fills from items
- Delete Stash item that's referenced by Finding → warning, evidence preserved (copied, not linked)

### Autopilot × Tool Security
- Autopilot mode: model tries to scan out-of-scope target → scope enforcement blocks, model notified
- Autopilot mode: model tries `run_shell rm -rf /` → parameter validation catches dangerous commands (configurable blocklist)

### i18n × Reports
- Generate report in Korean for English Op → model translates findings
- CVSS labels in Chinese → proper translation, not transliterated

### Terminal × Tool Execution
- User runs tool manually in terminal → output NOT auto-captured into Op context (separate from structured tool calls)
- User runs tool in terminal → can manually "Send to chat" → then model sees it

### Chat × Activity Feed
- Same event appears in both (chat shows message, feed shows tool invocation)
- Scroll position independent between chat and feed
- Click event in feed → scrolls to corresponding chat message

### Model Detection × Inference Settings
- Load JANG model → auto-detect architecture → pre-fill reasoning parser + tool parser + cache settings
- User overrides detected settings → warning "Overriding detected [X] with [Y]"
- Reset button restores detected defaults

### Findings × Report
- Delete Finding after report generated → report references orphaned finding → re-generate warning
- Edit Finding after report generated → "Report is stale, regenerate?" prompt
- Zero findings → report generation grayed out or generates "No vulnerabilities found" report

---

## Supplementary Concerns

### S001: Audit Trail
- [ ] Every tool execution logged: timestamp, tool, parameters, target, exit code, duration
- [ ] Audit log separate from app DB (plain text or structured log file)
- [ ] Audit log location: ~/.exploitbot/logs/audit.log
- [ ] Audit log rotation (daily, keep 90 days)
- [ ] Audit log exportable
- [ ] Audit log includes: who started the Op, what mode, scope definition

### S002: Credential Handling
- [ ] Found credentials stored encrypted in DB (at-rest encryption)
- [ ] Credential display: masked by default, click to reveal
- [ ] Credential copy: copies to clipboard, auto-clears after 30s
- [ ] Never log credentials in plain text to audit log
- [ ] Never send credentials to model as plain text? (or do, since it's local)
- [ ] Actually: model IS local, so credentials in model context is fine

### S003: Evidence Integrity
- [ ] Evidence hash (SHA-256) stored with each evidence item
- [ ] Evidence immutable after creation (modifications = new version)
- [ ] Evidence chain: timestamp + hash proves when captured
- [ ] Evidence export includes hashes for verification

### S004: Auto-Update System
- [ ] Check GitHub releases API for latest version
- [ ] Compare semver: current vs latest
- [ ] Show "Update available" banner with changelog
- [ ] "Download Update" → downloads DMG in background
- [ ] "Install Update" → closes app, opens DMG, runs installer
- [ ] Skip version option ("Don't remind me about this version")
- [ ] Check frequency: daily (configurable)

### S005: Crash Reporting
- [ ] Crash log written to ~/.exploitbot/logs/crash.log
- [ ] Crash dialog: "exploitbot crashed. Send report?" (opt-in)
- [ ] Crash report includes: stack trace, OS version, app version, last 50 activity feed entries (no credentials/targets)
- [ ] Or: no crash reporting (open source, users file GitHub issues)

### S006: Accessibility
- [ ] VoiceOver support for all UI elements
- [ ] Keyboard navigation for all controls
- [ ] Focus indicators visible
- [ ] High contrast mode support (system-level)
- [ ] Reduced motion support (system-level, disable animations)
- [ ] Font scaling support (system text size)
- [ ] Screen reader labels on tool status icons, severity badges

### S007: Dangerous Command Blocklist
- [ ] Configurable blocklist for `run_shell` (even in Autopilot)
- [ ] Default blocked patterns: `rm -rf /`, `mkfs`, `dd if=/dev/zero`, `:(){ :|:& };:`, format/wipe commands
- [ ] Model-generated `run_shell` validated against blocklist before execution
- [ ] Bypass: user can override in Copilot/Manual mode
- [ ] Bypass NOT available in Autopilot (safety net)

### S008: Scope Enforcement Details
- [ ] Scope defined as: included_targets (domains, IPs, CIDRs) + excluded_targets
- [ ] Wildcard support: *.acme.com
- [ ] Tool parameter validation: target/url/host params checked against scope
- [ ] DNS resolution check: resolved IP checked against scope
- [ ] Enforcement levels (per-Op setting):
  - Strict: block all out-of-scope tool calls
  - Warn: allow but flag prominently in activity feed
  - Off: no enforcement (CTF/lab mode)
- [ ] System prompt includes scope for model awareness

### S009: Wordlist Management
- [ ] Seclists auto-download location: ~/.exploitbot/wordlists/seclists/
- [ ] Custom wordlist upload/import
- [ ] Wordlist browser (tree view of seclists directory)
- [ ] Wordlist picker in tool parameter forms (file browser)
- [ ] Wordlist size preview (line count)
- [ ] Frequently used wordlists: quick-access list

### S010: Evidence Screenshot Capture
- [ ] Manual screenshot: button to capture current tool output as image
- [ ] Screenshot stored as PNG in evidence directory
- [ ] Screenshot auto-attached to relevant Finding
- [ ] Viewport screenshot (what's visible)
- [ ] Full-page screenshot (for web content)
- [ ] Screenshot annotation (draw arrows, highlight boxes) — v2 feature?
