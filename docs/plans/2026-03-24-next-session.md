# exploitbot — Next Session Plan

**Date:** 2026-03-24
**Current state:** v1.0 functionally complete, 51 Swift files, 8,472 lines

---

## PRIORITY 0: Inference Metrics + Logs Visibility

### Token Speed Display
- [ ] Tokens per second (tok/s) shown during streaming in chat header
- [ ] Time to first token (TTFT) displayed after first token arrives
- [ ] Prompt processing speed (prompt tokens/sec) shown during prefill
- [ ] Parse from SSE `usage` field: `prompt_tokens`, `completion_tokens`, `prompt_tokens_details.cached_tokens`
- [ ] Display format: "12.3 tok/s · TTFT 1.2s · 150 prompt (64 cached)"
- [ ] Only shown during/after streaming (not when idle)

### Inference Log Access
- [ ] Inference log button should be visible from main UI (not buried in Settings)
- [ ] Add log icon button (📋) in chat header next to reasoning toggle
- [ ] Click opens a slide-out panel or sheet showing real-time engine logs
- [ ] InferenceLogView already built — just needs to be accessible from chat, not just Settings
- [ ] Auto-scroll, copy, clear buttons already implemented

## PRIORITY 1: Ship ALL Tools With The App

**Philosophy:** Bundle EVERYTHING. Users should not need homebrew, pip, or any deps. App works out of the box. Users with their own installs don't get conflicts — our tools are sandboxed in the .app bundle.

**Bundle ALL as arm64 in .app/Contents/Resources/tools/:**

Go/Rust (single binary): subfinder, dnsx, httpx, nuclei, katana, feroxbuster, ffuf, dalfox, arjun, haiti, chisel, trufflehog, gowitness, netexec

Python (bundle with embedded Python or PyInstaller): sqlmap, impacket, sherlock, holehe, pwncat, pwntools

C/system (static arm64 builds): nmap, masscan, hashcat (Metal), hydra, tshark

Scripts (tiny, always bundle): testssl.sh, linpeas.sh, winpeas.exe, jwt_tool.py, graphqlmap.py

**Heavy/Optional (download on first use, NOT bundled):**
- metasploit (~1GB) — download button in Settings
- sliver C2 (~100MB) — download button
- seclists wordlists (~200MB) — download button
- bettercap — download button

**User custom tools:** Settings → Tools → "Add Custom Tool" → point to any binary, define schema

**CVE embeddings:** Ship small starter set (~5K critical CVEs). Full 250K DB available via "Import" button. Users can add custom CVEs.

**Steps:**
1. Download/compile arm64 binaries for all bundled tools
2. Create Resources/tools/ directory in Xcode project
3. Update ToolExecutor.findBinary() to check bundle FIRST
4. Update project.yml extraResources
5. Test each tool from bundle path
6. Add custom tool UI in Settings
7. Rebuild DMG (~300-500MB with all tools)

## PRIORITY 2: Test All Tools Against DVWA/Juice Shop

Test targets running on exploit.team:
- DVWA: test.exploit.bot (port 9090) — SQLi, XSS, file upload, command injection
- Juice Shop: juice.exploit.bot (port 9091) — modern OWASP vulns

Test each tool category:
- Recon: subfinder, nmap, httpx against test.exploit.bot
- Web: nuclei, sqlmap, dalfox against DVWA
- Creds: hashcat against DVWA password hashes
- OSINT: sherlock against known test usernames

## PRIORITY 3: Settings That Should Take Effect

Verified working:
- [x] Engine port (dynamic, from EngineManager)
- [x] Model path (from Settings → EngineConfig → launch.py)
- [x] Reasoning parser (from Settings → launch.py --reasoning-parser)
- [x] Tool call parser (from Settings → launch.py --tool-call-parser)
- [x] Temperature (from Settings → ChatService.temperature → API body)
- [x] Max tokens (from Settings → ChatService.maxTokens → API body)
- [x] KV cache quantization (from Settings → launch.py)
- [x] Enable reasoning toggle (💭 button → enable_thinking in API)
- [x] Interaction mode (sidebar → ChatService.interactionMode)
- [x] Scope (Op creation → ChatService.scopePatterns)
- [x] Phase (Phase indicator → ChatService.phaseGuidance)
- [x] Language (Onboarding → Localizer.shared)

Need verification:
- [ ] Temperature change takes effect without engine restart
- [ ] Max tokens change takes effect without engine restart
- [ ] Model name correctly sent in API requests (fixed this session)

## PRIORITY 4: Remaining Fixes

### From inverse behavior audit:
- [ ] Settings Apply while streaming — should warn/stop first
- [ ] Auto-tab tracking override after manual tab switch (15s pause implemented, verify)
- [ ] VulnCard Stash button wiring
- [ ] Terminal process cleanup on app exit

### From edge case audit:
- [ ] Copilot approval timeout (auto-reject after 5 min)
- [ ] Phase persistence per-Op in DB
- [ ] Model path validation (check safetensors before launch)
- [ ] RAM check before model load

### Hardcoded values to consider making configurable:
- maxIterations = 20 (tool call loop limit)
- maxContextChars = 100_000 (context window cap)
- maxOutputSize = 10_000_000 (tool output cap)
- toolTimeout = 300 (seconds)
- bottomPanelHeight / chatPanelWidth defaults
- Port range 8100-8199

## PRIORITY 5: Polish

- [ ] App icon in DMG (asset catalog issue)
- [ ] New screenshots for website (app has changed significantly)
- [ ] Update exploit.bot website with final screenshots
- [ ] GitHub Release with DMG upload
- [ ] README update with final build instructions

## Files Changed This Session (key ones)

- `ChatService.swift` — removed hardcoded model name, temperature, max_tokens; now reads from properties set by AppState
- `EngineManager.swift` — PYTHONPATH fix, 50KB log buffer
- `launch.py` — ENGINE_DIR + PYTHONPATH in subprocess env
- `ChatPanelView.swift` — reasoning toggle, collapsible blocks, resizable
- `ContentView.swift` — resizable panels, auto-tab-tracking pause
- `SidebarView.swift` — stop on new op, reject approval on mode switch, persist mode to DB
- `ScopeChecker.swift` — new: domain/wildcard/CIDR scope enforcement
- `ReasoningBlock.swift` — new: vMLX-style collapsible thinking display
- `InferenceLogView.swift` — new: engine log viewer with copy/clear
- `SubtabBar.swift` — new: scrollable subtabs (no truncation)
- `BotIcon.swift` — new: loads custom icon from Resources
