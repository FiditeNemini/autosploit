# exploitbot — Build Order (dependency-sorted)

Each phase builds on the previous. Smallest effort first, unlocking the most downstream features.

---

## Phase A: Stash (enables Findings, Reports, cross-Op sharing)
**Effort:** ~2 hours
**Unlocks:** Finding wizard, Report generation, cross-Op workflows

Everything downstream (Findings, Reports) needs Stash to hold artifacts.

### Tasks:
1. Stash data model in SQLite (stash_items table already exists in schema)
2. StashService — CRUD operations (save, fetch, delete, search, filter by type)
3. Add "Stash this" action to:
   - Chat messages (right-click or button)
   - Tool call output cards
   - Tool results in activity feed
4. Stash drawer UI (right-side overlay, already mocked in P6)
   - Type filter tabs (All/Creds/Hosts/Vulns/Code/Raw)
   - Search input
   - Item list with type icons + metadata
   - "→ Send" button per item (inserts into chat)
5. Stash tab (full view, already has layout shell)
   - Wire to real StashService data instead of sample data
6. Auto-type detection (regex: IPs, hashes, URLs, emails → set type)
7. "Send to Op" — picker to insert stash item into another Op's chat

### Dependencies: SQLite (done), Chat system (done)
### Blocks: Finding wizard, Report generation

---

## Phase B: Finding Wizard (enables Reports)
**Effort:** ~3 hours
**Unlocks:** Report generation, professional deliverables

### Tasks:
1. Finding data model (findings table already in schema)
2. FindingService — CRUD operations
3. Finding creation wizard modal (already mocked in P3):
   - Pre-fill from tool output or stash item
   - Title, vuln type, severity, CVSS, target, description
   - Attack chain (auto-reconstruct from Op messages)
   - Evidence (auto-attach from recent tool outputs)
   - Impact + Remediation (model-generated fields)
   - CVE ID field
   - Status (confirmed/unconfirmed/false_positive)
4. "Create Finding" button wired on:
   - Vulnerability cards in Web tab
   - Post-exploit results
   - Stash items (promote to Finding)
   - Chat messages (right-click)
5. Findings list in Report tab (already has layout, wire to real data)
6. Finding edit/delete

### Dependencies: Stash (for evidence attachment), SQLite (done)
### Blocks: Report generation

---

## Phase C: Copilot Approval Cards (enables safe tool calling)
**Effort:** ~2 hours
**Unlocks:** Safe mode for live target pentesting

### Tasks:
1. Approval state in ChatService:
   - When mode == .copilot and model returns tool_calls:
     - Don't auto-execute
     - Create pending approval with tool name, args, description
     - Wait for user action
2. ApprovalCardView (inline in chat, already mocked in P4):
   - Tool name + safety tag (safe/active/dangerous)
   - Description of what the tool does
   - Command preview
   - Editable parameters
   - Approve / Modify / Reject buttons
3. Approval logic:
   - Approve → execute tool normally
   - Modify → expand params for editing, then execute
   - Reject → send rejection to model, model suggests alternative
4. Safety classification:
   - Safe (passive): subfinder, dnsx, theHarvester, haiti, sherlock, holehe
   - Active (sends probes): httpx, nuclei, katana, feroxbuster, ffuf, nmap
   - Dangerous (modifies target): sqlmap --os-shell, metasploit, run_shell
5. Auto-approve option for safe tools (setting)

### Dependencies: Chat + tool system (done), Mode selector (done)
### Blocks: Nothing — but required for real pentesting on live targets

---

## Phase D: Report Generation (the deliverable)
**Effort:** ~4 hours
**Unlocks:** Professional pentest reports

### Tasks:
1. Report template system:
   - HTML template with CSS for each report type
   - Full Pentest Report (all sections)
   - Bug Bounty Submission (per-vuln)
   - Executive Brief (summary only)
   - Technical Writeup (narrative)
2. LLM report generation:
   - Send all Findings + Op context to model
   - Model writes: executive summary, attack narrative, remediation roadmap
   - Per-section regenerate button
3. Report preview in Report tab (render HTML in WKWebView)
4. Export:
   - PDF via WKWebView.createPDF()
   - Markdown via string formatting
   - HTML (standalone, CSS inlined)
   - JSON (structured findings data)
5. Branding:
   - Company name, logo, header text from Settings
   - Inject into HTML template

### Dependencies: Findings (Phase B), Stash (Phase A)
### Blocks: Nothing — this is an endpoint

---

## Phase E: Tool Installer (enables new users)
**Effort:** ~2 hours
**Unlocks:** New users can get started without manual brew/pip installs

### Tasks:
1. ToolStatusService — detect which tools are installed:
   - For each tool in registry: check if binary exists via `which`
   - Track: installed/missing/version
2. Tool install execution:
   - homebrew: `brew install nmap`
   - pip: `pip3 install sqlmap`
   - go: `go install github.com/...`
   - Per-tool install command in registry.json
3. Tool status UI in Settings:
   - List all 39 tools with status (installed ✓ / missing ✗)
   - Install button per tool
   - "Install All Missing" button
4. Onboarding step 2.5 (between Model and First Op):
   - Show tool status grid
   - Bundled tools = ready
   - Missing tools = install buttons
5. Tool path override in Settings (advanced)

### Dependencies: Tool registry (done)
### Blocks: Nothing — but improves onboarding

---

## Phase F: Model Downloader (enables easy model setup)
**Effort:** ~4 hours
**Unlocks:** Users don't need to manually download models

### Tasks:
1. HuggingFace download service:
   - API: list model files, get sizes
   - Download with progress (URLSession with delegate)
   - Pause/resume (HTTP range requests)
   - Cancel with cleanup
   - Disk space check before download
2. Download UI:
   - Progress bar (bytes/total, speed, ETA)
   - Pause/Resume/Cancel buttons
   - Download location: ~/.exploitbot/models/
3. Wire into onboarding Step 2:
   - Click tier card → starts download
   - Progress shown inline
4. Wire into Settings:
   - "Download New Model" button
   - Downloaded models list with delete button

### Dependencies: Settings UI (done)
### Blocks: Nothing — but dramatically improves UX

---

## Phase G: Terminal (SwiftTerm)
**Effort:** ~3 hours
**Unlocks:** Manual shell access, SSH sessions

### Tasks:
1. Add SwiftTerm dependency to Package.swift
2. TerminalView — NSViewRepresentable wrapping SwiftTerm
3. Terminal panel (bottom overlay, already mocked in P6):
   - Toggle with ⌘` or Terminal button
   - Multiple tabs (zsh 1, zsh 2, ssh sessions)
   - "Send to Chat" button
   - "Stash Selection" button
4. PATH setup: include ~/.exploitbot/tools/ + bundled paths
5. Working directory: ~/.exploitbot/ops/{current_op}/

### Dependencies: None
### Blocks: Nothing — independent feature

---

## Phase H: CVE Knowledge Base
**Effort:** ~8 hours (biggest item)
**Unlocks:** Automated vulnerability matching

### Tasks:
1. CVE database schema in SQLite (separate cve.db)
2. NVD data ingestion script (download + parse JSON)
3. Embedding generation via cve_embedder.py (already written)
4. sqlite-vec integration for vector search
5. search_cve tool implementation (model can call it)
6. CVE search UI in Settings
7. Auto-search after service detection (httpx/nmap results → CVE lookup)
8. Finding enrichment (auto-fill CVE ID, CVSS from DB)

### Dependencies: Findings (Phase B), Embedder (done)
### Blocks: Nothing — enhancement

---

## Summary: Build Order

```
Phase A: Stash ──────────┐
                         ├─→ Phase B: Findings ──→ Phase D: Reports
Phase C: Copilot Cards   │
                         │
Phase E: Tool Installer  │
Phase F: Model Downloader│
Phase G: Terminal        │
                         │
Phase H: CVE KB ─────────┘ (after Findings)
```

**Optimal sequence:** A → B → C → D → E → F → G → H

A + B + C can be parallelized (independent). D depends on A + B.
E, F, G are fully independent — can be done in any order.
H depends on B.
