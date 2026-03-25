# exploitbot — Next Session Plan

**Date:** 2026-03-24
**Current state:** v1.0 functionally complete, 51 Swift files, 8,472 lines

---

## PRIORITY 1: Tool Bundling & Installation

Bundle arm64 tool binaries in .app Resources for zero-config experience.

**Bundle (~150MB):** subfinder, dnsx, httpx, nuclei, katana, feroxbuster, ffuf, dalfox, arjun, haiti, chisel, trufflehog, sherlock, holehe, testssl.sh, jwt_tool, graphqlmap, exiftool, gowitness, linpeas.sh, winpeas.exe

**User-install:** nmap, masscan, hashcat, metasploit, sqlmap, impacket, pwntools, pwncat, netexec, hydra, bettercap, tshark, sliver

**Steps:**
1. Download arm64 binaries for each bundled tool
2. Add to ExploitBot/Resources/tools/
3. Update ToolExecutor.findBinary() to check bundle Resources first
4. Update project.yml to include tools
5. Test each tool executes from bundle
6. Rebuild DMG

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
