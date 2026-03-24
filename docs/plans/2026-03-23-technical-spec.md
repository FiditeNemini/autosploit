# exploitbot — Technical Specification

**Date:** 2026-03-23
**Status:** In progress — decisions being captured as brainstorming continues
**Companion:** See `2026-03-23-exploitbot-design.md` for product/UX design

---

## Decision Log

Every technical decision, numbered for cross-reference in test matrices.

### D001: UI Platform
- **Decision:** SwiftUI, macOS 14+
- **Rationale:** Native Mac feel, CRACK app proves the pattern works
- **Test surface:** All UI components, window management, dark mode, accessibility

### D002: Inference Engine
- **Decision:** vMLX engine (vllm-mlx), running as localhost server
- **Rationale:** All inference features already built — prefix cache, paged cache, KV quant, reasoning parsers, tool parsers, streaming, continuous batching
- **Branding:** "Powered by vMLX engine"
- **Implementation:** Spawn `vllm-mlx serve` on random localhost port at app launch, communicate via HTTP + SSE
- **Test surface:** Engine launch/shutdown, port allocation, health checks, crash recovery, orphan process cleanup

### D003: Engine IPC — Chat/Inference
- **Decision:** Standard HTTP + SSE streaming to vMLX's OpenAI-compatible API on localhost
- **Endpoints used:** `/v1/chat/completions` (streaming), `/v1/models`
- **Test surface:** Request formation, SSE parsing, stream interruption, timeout handling, error propagation

### D004: Engine IPC — Tool Invocation
- **Decision:** Hybrid — structured tool_call via vMLX tool calling + generic `run_shell` escape hatch
- **Implementation:**
  - Each pentesting tool defined as a function schema (name, description, parameters)
  - Model outputs `tool_call` → SwiftUI intercepts → runs subprocess → feeds result back
  - `run_shell` tool for arbitrary commands not covered by structured definitions
- **Test surface:** Tool call parsing (all 14 vMLX parsers), parameter validation, subprocess execution, result truncation, timeout, cancellation, shell injection prevention

### D005: Model Management
- **Decision:** Single model loaded at a time, multiple Ops share it
- **Implementation:** Model downloader with curated S/M/L/XL tiers + custom HuggingFace URL
- **Auto-detection:** RAM detection → tier recommendation, architecture detection from config.json
- **Test surface:** Download (progress, pause, resume, cancel, disk space check), model loading, model switching, JANG format detection, standard safetensors, GGUF detection

### D006: Ops System
- **Decision:** Named persistent workspaces with continuous model context across tool tabs
- **Implementation:**
  - Each Op has: name, status (active/paused/complete), full conversation history, tool outputs, findings, notes
  - Switching tabs within Op = same context
  - Switching Ops = different context
  - Multiple Ops can exist simultaneously, all share single loaded model
- **Test surface:** Op CRUD, context persistence, context switching, concurrent Ops, Op state transitions

### D007: Context Window Management
- **Decision:** User-configurable setting with 4 strategies
- **Options:**
  1. Auto-summarize (model condenses old context, preserving key findings)
  2. Sliding window with pinned items (drop oldest, pin important)
  3. Manual checkpointing (user-triggered summarize + reset)
  4. None / rely on cache stack (default for v1)
- **Setting location:** Model settings panel
- **Test surface:** Each strategy independently, strategy switching mid-Op, context size tracking, summarization quality, pinned item preservation

### D008: Stash (Cross-Op Artifact Sharing)
- **Decision:** Global persistent artifact store bridging all Ops
- **Artifact types:** Credential, Host/IP, Subdomain list, Port scan, Vulnerability, Code snippet, Screenshot, Raw output, Note
- **Operations:** Send to Stash (from any tool output/model response/selection), Pull from Stash (into any Op's chatbox/tool input)
- **Metadata per item:** Source Op, source tool/tab, timestamp, user-editable label/tag, type (auto-detected or user-set)
- **Test surface:** Stash CRUD, type auto-detection, cross-Op sharing, drag/send into chatbox, persistence, search/filter

### D009: Findings System
- **Decision:** Core deliverable object — confirmed exploitable vulnerability with full attack chain
- **Creation methods:**
  1. Manual — user marks output as Finding
  2. LLM-suggested — model recognizes vuln and prompts
  3. From Stash — promote artifact collection to Finding
- **Finding data model:**
  - Vulnerability details (CVE, type, severity/CVSS, affected target)
  - Attack chain (full path from initial access to exploitation, step by step)
  - Evidence (tool outputs, screenshots, request/response pairs, payloads)
  - Timeline (auto-tracked from Op history)
  - Reproduction steps (model-generated from attack chain)
  - Impact assessment (what attacker gains)
  - Remediation (model-generated fix recommendations)
- **Test surface:** Finding CRUD, each creation method, attack chain reconstruction accuracy, evidence attachment, CVSS scoring, Finding→Report pipeline

### D010: Report Generation
- **Decision:** LLM-generated professional pentest reports from Findings
- **Report sections:** Executive Summary, Scope & Methodology, Findings Summary, Detailed Findings, Attack Narrative, Remediation Roadmap, Appendix
- **Export formats:** PDF, Markdown, HTML, JSON
- **Customization:** Company branding (logo, colors, header/footer), template selection (full report, bug bounty, executive brief, technical writeup)
- **Localization:** Reports generated in user's selected language (en/ko/zh/es/ja)
- **Test surface:** Each export format, each template, each language, branding injection, Finding→section mapping, large report handling

### D011: Tool Installation
- **Decision:** Hybrid — bundle lightweight tools, lazy-install heavy ones
- **Bundled (in .app):** ProjectDiscovery Go suite (subfinder, dnsx, httpx, nuclei, katana), feroxbuster, ffuf, arjun, dalfox, haiti, chisel, sherlock, holehe, gowitness, exiftool, testssl.sh, jwt_tool, graphqlmap
- **Lazy-install (on first use):** metasploit (~1GB), hashcat, bettercap, hydra, nmap, masscan, netexec, impacket, pwncat, pwntools, sliver, tshark, snmpwalk, wpscan, trufflehog, seclists
- **Install methods:** homebrew, pip, go install (per-tool)
- **Tool path:** `~/.exploitbot/tools/` — added to engine's PATH so model can invoke
- **Test surface:** Each bundled tool present and executable, each lazy-install flow, PATH resolution, version detection, update mechanism, uninstall

### D012: Tool Registry (Function Schemas)
- **Decision:** Every integrated tool has a structured function definition
- **Schema per tool:** name, description, parameters (with types, required/optional, defaults, enums for flags)
- **Plus:** Generic `run_shell` tool for arbitrary commands
- **LLM receives:** Full tool registry as function definitions in the system prompt or tool list
- **Test surface:** Each tool schema validity, parameter validation, model invocation of each tool, result parsing per tool, `run_shell` safety (injection prevention)

### D013: Tool Execution Runtime
- **Decision:** Subprocess management with structured output parsing
- **Per execution:**
  - Spawn subprocess with tool binary + validated args
  - Stream stdout/stderr back to UI in real-time
  - Parse output into structured results where possible (per-tool parsers)
  - Enforce timeout (configurable per tool)
  - Support cancellation (SIGTERM → SIGKILL)
  - Feed structured result back to model context
- **Test surface:** Subprocess lifecycle, output parsing per tool, timeout enforcement, cancellation, concurrent tool execution, error handling (tool not found, permission denied, crash)

### D014: Internationalization (i18n)
- **Decision:** 5 languages — EN, KO, ZH, ES, JA
- **Implementation:**
  - Language picker on first boot (shown in all 5 languages simultaneously)
  - Settings → Language changeable anytime, no restart required
  - All UI strings externalized to Swift String Catalogs
  - Report generation in selected language
  - Model system prompt includes language preference
- **Test surface:** Each language renders correctly, language switching, no untranslated strings, CJK text rendering, RTL (not applicable but verify), report language output

### D015: Inference Settings (User-Exposed)
- **Decision:** Full vMLX inference stack exposed in model settings
- **Settings:**
  - **Sampling:** temperature, top_p, top_k, min_p, repetition_penalty, max_tokens, stop sequences
  - **Cache stack:** prefix cache (on/off, memory %), paged cache (on/off, block size), KV cache quantization (none/q4/q8, group size)
  - **Reasoning:** enable_thinking (auto/on/off), reasoning parser (auto-detect or manual)
  - **Tool calling:** tool call parser (auto-detect or manual), enable_auto_tool_choice
  - **Context management:** strategy selection (D007)
  - **Continuous batching:** (internal, not user-facing — but enabled for tool call parallelism)
- **Auto-detection:** Model architecture → recommended defaults for reasoning parser, tool parser, paged cache
- **Test surface:** Each setting independently, setting combinations, reset to defaults, per-Op overrides vs global, settings persistence

### D016: Reasoning Recognition
- **Decision:** Auto-detect reasoning models, show thinking blocks in UI
- **Supported parsers (from vMLX):** auto, qwen3, deepseek_r1, openai_gptoss
- **UI:** Collapsible reasoning/thinking block above model response (like vMLX's ReasoningBox)
- **Behavior:** When enable_thinking=true and model emits reasoning content, display separately. When false, suppress.
- **Template detection:** `_template_always_thinks()` check (from vMLX) for models that inject `<think>` regardless of flag
- **Test surface:** Each reasoning parser, thinking block display/collapse, enable_thinking toggle, template-always-thinks detection, streaming reasoning chunks

### D017: Per-Tab Bespoke UIs
- **Decision:** Each tool category tab has its own unique layout and controls
- **Tabs:**
  1. **Recon** — Target input, subdomain tree view, port table, live host list, network graph visualization
  2. **Web** — URL bar + request/response viewer, vulnerability cards by severity, template selector for nuclei, parameter discovery table
  3. **Network** — Network topology view, protocol-specific panels (SMB/LDAP/SNMP), packet capture viewer, tunnel manager
  4. **Credentials** — Hash input/identifier, cracking progress (GPU utilization), wordlist selector, brute force target config, credential vault
  5. **Exploit** — Payload builder, reverse shell listener status, metasploit module browser, exploit code editor
  6. **Post-Exploit** — Privilege escalation checklist, AD attack tree, lateral movement map, impacket command palette
  7. **OSINT** — Person/email/username search, results aggregation across platforms, metadata viewer, screenshot gallery
  8. **Reporting** — Findings list with severity, report preview, template selector, export buttons, branding config
  9. **Stash** — Artifact grid/list, type filter, search, drag-to-chatbox
- **Constants on every tab:** Chatbox, Terminal, Stash drawer, Op Controls
- **Test surface:** Each tab renders, tab-specific controls functional, tool invocation from each tab, results display per tab, tab switching preserves state, chatbox context continuity across tabs

### D018: Embedded Terminal
- **Decision:** Pop-open real shell accessible from any tab
- **Implementation:** SwiftUI wrapper around pseudoterminal (pty) — likely using a Swift terminal emulator library or custom pty fork/exec
- **Features:** Full interactive shell, copy/paste, scrollback, monospace rendering
- **PATH:** Includes `~/.exploitbot/tools/` and bundled tool paths
- **Test surface:** Terminal launch/close, command execution, interactive programs (vim, ssh), copy/paste, scrollback, PATH includes all tools, terminal output capture for model context

### D019: Data Persistence
- **Decision:** TBD — SQLite (like vMLX) or CoreData or JSON files
- **Schema needs:**
  - Ops (id, name, status, created, updated, model_config)
  - Messages (id, op_id, role, content, reasoning_content, tool_calls, tool_results, timestamp, tab_context)
  - Findings (id, op_id, vuln_type, severity, cvss, target, attack_chain, evidence, remediation, status)
  - Stash items (id, type, label, content, source_op, source_tool, timestamp, tags)
  - Settings (key-value, global + per-op overrides)
  - Downloaded models (path, size, format, architecture, last_used)
  - Installed tools (name, version, path, install_method, status)
- **Test surface:** CRUD for each entity, foreign key integrity, migration on schema changes, corruption recovery, concurrent access

### D020: First-Run Onboarding
- **Decision:** Multi-step guided setup
- **Steps:**
  1. Language selection (all 5 shown simultaneously)
  2. Model download (curated list with tier recommendation based on RAM)
  3. Tool installation status (bundled = ready, lazy = install buttons)
  4. Create first Op (name, optional target/scope description)
  5. Ready — drop into Op workspace
- **Test surface:** Each step independently, skip/back navigation, partial completion resume, network failure during download, disk space insufficient

### D021: App Lifecycle
- **Decision:** Mirrors vMLX patterns where applicable
- **Launch:** Start vMLX engine on localhost, verify health, restore last active Op
- **Quit:** Graceful engine shutdown (SIGTERM → timeout → SIGKILL), save all Op state, cleanup orphan processes
- **Crash recovery:** Detect orphan vMLX processes on launch (like vMLX's adoption), recover or kill
- **Single instance:** App lock to prevent multiple instances (SQLite corruption prevention)
- **Test surface:** Clean launch, clean quit, force quit recovery, orphan detection, single instance enforcement, engine crash mid-session

### D022: Model Architecture Detection
- **Decision:** Use vMLX's model-config-registry (detectModelConfigFromDir)
- **Detects:** model_type from config.json, auto-selects reasoning parser, tool parser, paged cache recommendation
- **UI impact:** Settings pre-filled with detected optimal values, "Reset to detected" button
- **Test surface:** Detection accuracy for each supported model family (65+), fallback for unknown models, JANG format detection, config.json parsing

### D023: Dual-Mode Interaction
- **Decision:** Every tab supports manual controls AND LLM-driven mode
- **Manual:** Direct tool controls (input fields, flags, options, run button)
- **LLM-driven:** User describes intent in chatbox, model selects tools and runs them
- **Bridge:** Model can explain manual controls, user can override model suggestions
- **Test surface:** Manual invocation of each tool, LLM invocation of each tool, mixed mode (start manual, continue with LLM), LLM override by user

### D024: Security — Shell Injection Prevention
- **Decision:** All tool invocations go through structured parameter validation
- **Implementation:**
  - Structured tool_calls have typed parameters — never interpolated into shell strings
  - `run_shell` tool requires explicit user confirmation before execution (unless in autonomous mode)
  - Subprocess uses argument arrays (not shell strings): `["/usr/bin/nmap", "-sV", target]`
  - Input sanitization: reject shell metacharacters in tool parameters
- **Test surface:** Injection attempts in each tool parameter, `run_shell` confirmation flow, metacharacter rejection, argument array construction

### D025: Interaction Modes (Autonomous / Assisted / Manual)
- **Decision:** Three distinct interaction modes, selectable per-Op
- **Modes:**
  1. **Autopilot** — User gives a starting prompt (e.g. "pentest acme.com, find everything exploitable"). Model runs autonomously — selects tools, executes them, chains results, pivots, creates Findings, generates report. No user input needed after initial prompt. `run_shell` executes without confirmation. All tool calls auto-approved.
  2. **Copilot** — Model suggests next steps and tool invocations, user approves/modifies before execution. `run_shell` requires confirmation. Structured tool_calls auto-approved but user can override parameters.
  3. **Manual** — User drives everything from tab UIs. Model is available in chatbox for questions/advice but doesn't auto-invoke tools. Pure human-driven pentesting with AI assist.
- **Switching:** Mode switchable mid-Op via Op Controls. Changing to Autopilot resumes autonomous execution from current state.
- **Default:** Copilot (safest for new users)
- **Test surface:** Each mode independently, mode switching mid-Op, Autopilot tool chain execution, Copilot approval/rejection flow, Manual chatbox-only behavior, `run_shell` confirmation gating per mode

### D026: Verbose Output / Activity Feed
- **Decision:** Real-time verbose activity feed showing ALL model actions, tool calls, and results
- **Implementation:**
  - **Activity Feed** — persistent scrolling log (like a build log) showing:
    - Model reasoning/thinking (collapsible)
    - Tool call invocations (tool name, parameters, command being run)
    - Tool stdout/stderr streaming in real-time
    - Tool completion status (success/fail/timeout)
    - Model interpretation of results
    - Decisions ("Found X, proceeding to Y because Z")
    - Stash/Finding creation events
  - **Verbosity levels:**
    1. **Minimal** — only results and decisions
    2. **Normal** — tool calls + results + decisions
    3. **Verbose** — everything including raw stdout/stderr, model reasoning, timing
    4. **Debug** — all of above + HTTP requests to engine, token counts, IPC messages
  - **Activity Feed location:** Below/alongside the chatbox on every tab. Auto-scrolls but user can scroll up to review. Filterable by type (tool calls only, errors only, etc.)
- **In Autopilot mode:** Activity Feed is the primary UI — user watches the model work, all actions streamed in real-time
- **Test surface:** Each verbosity level, real-time streaming of long-running tools, filter controls, auto-scroll behavior, Autopilot mode full-feed experience

### D027: PDF Report Rendering
- **Decision:** HTML → PDF via hidden WKWebView
- **Implementation:**
  - Generate styled HTML report from Findings data + LLM narrative
  - Render in offscreen WKWebView with `createPDF()` API
  - CSS handles page breaks, headers/footers, branding
  - Company logo injected as base64 data URI
- **Templates:** CSS template files per report type (full, bug bounty, executive, technical)
- **Test surface:** Each template renders correctly, page breaks, images/screenshots embedded, branding, CJK font rendering, large reports (50+ pages)

### D029: CVE Knowledge Base (Local Vector DB)
- **Decision:** Bundled CVE database with semantic search + structured CPE matching
- **Storage:** SQLite with `sqlite-vec` extension (same DB file or separate `cve.db`)
- **Data sources (pre-bundled, merged + deduplicated):**
  - NVD (National Vulnerability Database) — ~250K CVEs, CVSS scores, CPE data
  - Exploit-DB — mapped CVE→exploit links, PoC availability flags
  - CISA KEV (Known Exploited Vulnerabilities) — actively exploited CVEs flagged
  - GitHub Advisory Database — open source package vulns
  - VulnCheck / OSV — additional coverage for modern packages
- **Target coverage (prioritized for real-world pentesting):**
  - **Web servers:** Apache, nginx, IIS, Tomcat, Jetty, LiteSpeed, Caddy
  - **CMS:** WordPress (core + top 500 plugins), Drupal, Joomla, Magento, Ghost
  - **Frameworks:** Spring, Django, Rails, Laravel, Express, Next.js, ASP.NET
  - **CI/CD:** Jenkins, GitLab CI, GitHub Actions, TeamCity, Bamboo, ArgoCD
  - **Containers:** Docker, Kubernetes, Helm, containerd, Podman, OpenShift
  - **Databases:** MySQL, PostgreSQL, MongoDB, Redis, MSSQL, Oracle, Elasticsearch, CouchDB
  - **Mail:** Exchange, Postfix, Dovecot, Zimbra, Roundcube
  - **VPN/Remote:** OpenVPN, Fortinet, Pulse Secure, Citrix, PAN-OS, SonicWall, WireGuard
  - **Network equipment:** Cisco IOS/ASA, Juniper, MikroTik, Ubiquiti, pfSense
  - **Operating systems:** Windows (Server 2016-2025, 10, 11), Linux kernel, macOS, FreeBSD
  - **Active Directory:** AD CS, ADFS, Kerberos, LDAP, Group Policy, NTLM
  - **Cloud:** AWS (IAM, S3, Lambda, EC2), Azure (AD, Storage, Functions), GCP
  - **Programming languages/runtimes:** Node.js, Python (pip packages), Java (Maven), Ruby (gems), PHP (Composer), Go, Rust (crates)
  - **Monitoring/Observability:** Grafana, Prometheus, Zabbix, Nagios, Splunk, ELK
  - **File sharing:** Samba, NFS, FTP (vsftpd, ProFTPD), WebDAV, SharePoint
  - **Virtualization:** VMware (vCenter, ESXi), Proxmox, Hyper-V, QEMU/KVM
  - **IoT/embedded:** Firmware (common routers, cameras), MQTT, CoAP, BLE
  - **Authentication:** OAuth, SAML, JWT libraries, Keycloak, Okta, Auth0
  - **Crypto/TLS:** OpenSSL, GnuTLS, NSS, Let's Encrypt, certificate handling
  - **Desktop apps:** Electron apps, Chrome, Firefox, Office, Acrobat
- **Data per CVE:**
  - CVE ID (string, indexed)
  - Description (text)
  - CVSS v3.1 score (float) + vector string
  - Severity (critical/high/medium/low)
  - Affected products: CPE 2.3 strings (vendor:product:version_range)
  - Published date, modified date
  - References: exploit-db link, PoC URL, vendor advisory, patch URL
  - CISA KEV flag (boolean — actively exploited in the wild)
  - Exploit availability (none/poc/weaponized)
  - Embedding vector (float32[], from description + product names)
- **Search modes:**
  1. **Semantic:** "remote code execution in web servers" → vector cosine similarity via sqlite-vec
  2. **CPE match:** "apache:http_server:2.4.49" → version range matching
  3. **Keyword:** full-text search via FTS5 on description
  4. **CVSS filter:** "show all critical CVEs for nginx"
  5. **Combined:** semantic + CPE + severity filter
- **Embedding model:** Bundled small model — `nomic-embed-text-v1.5` (~275MB, runs on CPU, 768-dim vectors). Separate from the main inference model. Loaded on-demand for search, not always in memory.
- **User custom CVEs:**
  - "Add CVE" form: ID, description, affected product, severity, notes
  - Import from JSON/CSV
  - Custom CVEs stored in separate table, merged into search results
  - Custom CVEs can include private/internal vulnerability findings
  - Custom entries auto-embedded on save (using bundled embedding model)
  - Tag system for custom CVEs (e.g., "internal", "client-specific")
- **Updates:**
  - Auto-sync: check NVD/CISA KEV for new CVEs (configurable: daily/weekly/manual)
  - Delta updates: only download new/modified CVEs since last sync
  - Incremental embedding: only embed new CVEs (not re-embed entire DB)
  - Update notification: "47 new CVEs added" toast
  - Manual trigger: Settings → CVE Database → "Update Now"
  - Last sync timestamp displayed in Settings
- **Model integration:**
  - Tool `search_cve` added to tool registry (model can invoke)
  - System prompt tells model about CVE DB availability
  - Autopilot: after service detection (httpx/nmap), auto-searches CVE DB for matching versions
  - Results include: CVE ID, severity, description, exploit availability, CISA KEV status
  - Model can cross-reference multiple CVEs for attack chain planning
- **Size estimates:**
  - CVE data: ~500MB (250K CVEs with descriptions + CPE)
  - Embedding vectors: ~750MB (250K × 768 dims × 4 bytes)
  - Total: ~1.25 GB on disk (compressed ~600MB in app bundle, expanded on first run)
  - Or: download on first run instead of bundling (saves app size)
- **Test surface:** Semantic search accuracy, CPE version matching, FTS5 keyword search, custom CVE CRUD, embedding generation, delta updates, model invocation of search_cve tool, combined filter queries, CISA KEV flag filtering, exploit availability sorting

### D028: Data Persistence
- **Decision:** SQLite via GRDB.swift, WAL mode
- **Implementation:** Single `exploitbot.db` file at `~/.exploitbot/data/`
- **Schema:** See Database Schema section below
- **Migrations:** GRDB's built-in migration system, versioned
- **Backup:** Auto-backup on schema migration, manual export
- **Test surface:** CRUD for each entity, FK integrity, WAL concurrent access, migration, corruption recovery

---

## Feature Cross-Reference Matrix

For test planning — which features interact with which:

| Feature | Interacts With |
|---------|---------------|
| D002 Engine | D003, D004, D005, D015, D016, D021, D022 |
| D003 Chat IPC | D002, D006, D007, D015, D016 |
| D004 Tool Invocation | D002, D012, D013, D017, D023, D024 |
| D005 Model Management | D002, D015, D020, D022 |
| D006 Ops | D003, D007, D008, D009, D017, D019 |
| D007 Context Management | D003, D006, D015 |
| D008 Stash | D006, D009, D017, D019 |
| D009 Findings | D006, D008, D010, D019 |
| D010 Reports | D009, D014, D017 |
| D011 Tool Install | D012, D013, D018, D020 |
| D012 Tool Registry | D004, D011, D013, D023 |
| D013 Tool Execution | D004, D011, D012, D017, D024 |
| D014 i18n | D010, D017, D020 |
| D015 Inference Settings | D002, D003, D005, D007, D016, D022 |
| D016 Reasoning | D002, D003, D015, D022 |
| D017 Tab UIs | D004, D006, D008, D013, D014, D023 |
| D018 Terminal | D011, D013 |
| D019 Persistence | D006, D008, D009, D021 |
| D020 Onboarding | D005, D011, D014 |
| D021 Lifecycle | D002, D019 |
| D022 Model Detection | D002, D005, D015, D016 |
| D023 Dual-Mode | D004, D012, D017 |
| D024 Security | D004, D013 |

---

## Test Matrix Template

Each cell = test scenario where features A and B interact:

```
       D002 D003 D004 D005 D006 D007 D008 D009 D010 D011 D012 D013 D014 D015 D016 D017 D018 D019 D020 D021 D022 D023 D024
D002    —    ✓    ✓    ✓    .    .    .    .    .    .    .    .    .    ✓    ✓    .    .    .    .    ✓    ✓    .    .
D003         —    .    .    ✓    ✓    .    .    .    .    .    .    .    ✓    ✓    .    .    .    .    .    .    .    .
D004              —    .    .    .    .    .    .    .    ✓    ✓    .    .    .    ✓    .    .    .    .    .    ✓    ✓
D005                   —    .    .    .    .    .    .    .    .    .    ✓    .    .    .    .    ✓    .    ✓    .    .
D006                        —    ✓    ✓    ✓    .    .    .    .    .    .    .    ✓    .    ✓    .    .    .    .    .
D007                             —    .    .    .    .    .    .    .    ✓    .    .    .    .    .    .    .    .    .
D008                                  —    ✓    .    .    .    .    .    .    .    ✓    .    ✓    .    .    .    .    .
D009                                       —    ✓    .    .    .    .    .    .    .    .    ✓    .    .    .    .    .
D010                                            —    .    .    .    ✓    .    .    ✓    .    .    .    .    .    .    .
D011                                                 —    ✓    ✓    .    .    .    .    ✓    .    ✓    .    .    .    .
D012                                                      —    ✓    .    .    .    .    .    .    .    .    ✓    .
D013                                                           —    .    .    .    ✓    .    .    .    .    .    .    ✓
D014                                                                —    .    .    ✓    .    .    ✓    .    .    .    .
D015                                                                     —    ✓    .    .    .    .    .    ✓    .    .
D016                                                                          —    .    .    .    .    .    .    .    .
D017                                                                               —    .    .    .    .    .    ✓    .
D018                                                                                    —    .    .    .    .    .    .
D019                                                                                         —    .    ✓    .    .    .
D020                                                                                              —    .    .    .    .
D021                                                                                                   —    .    .    .
D022                                                                                                        —    .    .
D023                                                                                                             —    .
D024                                                                                                                  —
```

✓ = interaction exists, needs cross-feature test scenarios
. = no direct interaction

---

## Open Decisions (still in brainstorming)

- [ ] D019: Persistence technology (SQLite vs CoreData vs JSON)
- [ ] Per-tab bespoke UI detailed wireframes (D017)
- [ ] Report PDF rendering technology in Swift
- [ ] Terminal emulator library choice (D018)
- [ ] License (MIT? Apache 2.0? GPL?)
- [ ] Specific default model recommendation for first-run
