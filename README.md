<p align="center">
  <img src="assets/icons/app-icon.svg" width="128" height="128" alt="exploitbot">
</p>

<h1 align="center">exploit<sub style="font-weight:300">bot</sub></h1>

<p align="center">
  <strong>Autonomous pentesting on Apple Silicon</strong>
</p>

<p align="center">
  <img src="assets/badges/badge-version.svg" alt="version">
  <img src="assets/badges/badge-platform.svg" alt="platform">
  <img src="assets/badges/badge-license.svg" alt="license">
  <img src="assets/badges/badge-mlx.svg" alt="engine">
</p>

<p align="center">
  <a href="https://github.com/jjang-ai/exploitbot/releases">
    <img src="https://img.shields.io/badge/Download-DMG%20(v0.1.0--beta)-blue?style=for-the-badge&logo=apple" alt="Download DMG">
  </a>
</p>

<p align="center">
  <a href="https://exploit.bot">Website</a> •
  <a href="#features">Features</a> •
  <a href="#install">Install</a> •
  <a href="#models">Models</a> •
  <a href="#tools">Tools</a>
</p>

---

AI-powered penetration testing toolkit with local LLM inference. No cloud dependency, runs entirely on Apple Silicon.

exploitbot runs local models on Apple Silicon via [MLX](https://github.com/ml-explore/mlx), integrates real pentesting tools, and generates professional pentest reports from findings.

<p align="center">
  <img src="assets/screenshots/main-workspace.png" alt="exploitbot workspace" width="900">
</p>

## Features

**Local AI Inference** — vMLX-based models run on-device via Apple Silicon, with no API keys required.

**Ops System** — Named persistent workspaces for each engagement. Switch between targets without losing context. The LLM remembers evidence and findings across tabs.

**3 Interaction Modes**
- **Autopilot** — Give a target, watch it work. Full autonomous recon → exploitation → reporting.
- **Copilot** — AI suggests tools, you approve. Each action explained with risk level.
- **Manual** — You drive, AI advises. Full tool controls with chat-based guidance.

**42 Integrated Functions** — from recon and web to exploit, OSINT, report, and supply-chain workflows. Callback tools (`search_cve`, `lookup_cve`, `search_context`) and `run_shell` are part of the same tool surface so you can mix operator-invoked and context tools per tab.

**Stash** — Cross-op artifact sharing. Drop credentials, hosts, payloads from any engagement, pull them into any other.

**Findings → Reports** — The endgame. Confirmed vulnerabilities auto-capture attack chains, evidence, and impact. Generate professional pentest reports in PDF, Markdown, HTML, or JSON.

**CVE Knowledge Base + Import** — Local CVE database with semantic search plus list import support (CSV/JSON) and include filters.

**Supply-Chain + CVE Ops** — Supply-chain discovery and CVE lifecycle workflows now include `trufflehog`, `syft`, `grype`, and `osv_scanner` action coverage in the same tool/agent state system as other recon modules.

**5 Languages** — Full interface and report generation in English, 한국어, 中文, Español, 日本語.

**Live Tool Telemetry** — Tool execution status updates are emitted per button/tab (queued, running, done, error), written to logs, and tracked in chat/panel history with CVE and stash workflow visibility.

## Beta Readiness (May 26, 2026)

- ✅ **Release app proofing is in place**: signed DMG/package path, manifest checks, bundled Python/engine runtime verification.
- ✅ **Qwen family verification** is running on the smallest local target first (`Qwen3.6-27B-JANG_4M-MTP`) and includes hybrid cache + SSM + TurboQuant assertions.
- ✅ **MiniMax verification** includes repeat cache hit checks and TurboQuant path checks in live/release harnesses.
- ✅ **Supply-chain + CVE surfaces** are covered by live UI/agent proofs for tab actions, tool path routing, and import workflows.
- ⚠️ **Known blockers**:
  - Beta packaging remains blocked until a local notary profile is configured (`notarizationProfile` gate).
  - Qwen multimodal promotion is tracked as a documented gap pending loader/prefix-cache/prefix-routing proofs for the beta lane.

## Screenshots

<table>
  <tr>
    <td><img src="assets/screenshots/tab-web.png" alt="Web vulnerabilities"></td>
    <td><img src="assets/screenshots/tab-exploit.png" alt="Exploitation"></td>
  </tr>
  <tr>
    <td><em>Web vulnerability scanner with CVSS cards</em></td>
    <td><em>Metasploit module browser + payload config</em></td>
  </tr>
  <tr>
    <td><img src="assets/screenshots/tab-creds.png" alt="Credential cracking"></td>
    <td><img src="assets/screenshots/tab-osint.png" alt="OSINT"></td>
  </tr>
  <tr>
    <td><em>GPU-accelerated hash cracking via Metal</em></td>
    <td><em>Username OSINT across 400+ platforms</em></td>
  </tr>
</table>

<a name="install"></a>
## Install

### Download

Download the signed DMG from [Releases](https://github.com/jjang-ai/exploitbot/releases).

Requires **macOS 14+** and **Apple Silicon** (M1/M2/M3/M4).

### Build from Source

```bash
git clone https://github.com/jjang-ai/exploitbot.git
cd exploitbot

# Build and run local verification app
./script/build_and_run.sh --verify
```

**Prerequisites:**
- macOS 14+ on Apple Silicon
- Xcode 16+ (Swift toolchain)
- A vMLX-compatible model running on localhost:8000 (see [vMLX](https://github.com/jjang-ai/vmlx))
- Pentesting tools installed via homebrew/pip for tool execution

<a name="models"></a>
## Models

exploitbot is model-folder driven and currently supports:

- **Qwen text** (`qwen`) with JANG/JANGTQ/MXFP4 folders.
- **MiniMax text** (`minimax`).
- **ZAYA1-VL** (`zaya1`/`zaya1-vl`).

Use local folders from:

```bash
export EXPLOITBOT_MODELS=/Users/eric/models
export EXPLOITBOT_RELEASE_QWEN_MODEL=${EXPLOITBOT_MODELS}/JANGQ/Qwen3.6-27B-JANG_4M-MTP

# Smallest local Qwen smoke target (lower RAM)
${EXPLOITBOT_MODELS}/JANGQ/Qwen3.6-27B-JANG_4M-MTP

# JANGTQ and MXFP4 variants
${EXPLOITBOT_MODELS}/dealign.ai/Qwen3.6-35B-A3B-JANGTQ-CRACK
${EXPLOITBOT_MODELS}/JANGQ/Qwen3.6-35B-A3B-MXFP4-MTP

# Compact visual model
${EXPLOITBOT_MODELS}/JANGQ/ZAYA1-VL-8B-JANGTQ4
```

For runtime checks, start with the smallest Qwen target first to keep RAM pressure low.
The command examples below also default to this model.

<a name="tools"></a>
## Tools

42 tool definitions across 8 operational areas:

| Category | Tools |
|----------|-------|
| **Recon** | subfinder, dnsx, nmap, masscan, httpx, katana, theHarvester |
| **Web** | nuclei, sqlmap, dalfox, feroxbuster, ffuf, arjun, wpscan, testssl, graphqlmap, jwt_tool |
| **Network** | netexec, snmpwalk, tshark, bettercap, chisel |
| **Credentials** | hashcat, hydra, haiti, trufflehog |
| **Exploit** | metasploit, pwncat, pwntools, sliver |
| **Post-Exploit** | linpeas, winpeas, impacket |
| **OSINT** | sherlock, holehe, exiftool, gowitness |
| **Supply-Chain** | trufflehog, syft, grype, osv_scanner |
| **General / Report / Stash** | search_cve (local CVE DB), lookup_cve, search_context, run_shell |

Lightweight tools are bundled in the app. Heavy tools are installed on first use via homebrew/pip.

## Architecture

- **UI:** SwiftUI (native macOS 14+)
- **Inference:** vMLX engine (MLX on Apple Silicon) — localhost server, OpenAI-compatible API
- **IPC:** HTTP + SSE streaming to local vMLX server
- **Persistence:** SQLite (GRDB.swift) with WAL mode
- **Terminal:** SwiftTerm (embedded pty)
- **Reports:** HTML → PDF via WKWebView
- **CVE DB:** SQLite + sqlite-vec (semantic search with nomic-embed-text)

## Documentation

- [Design Document](docs/plans/2026-03-23-exploitbot-design.md) — Product and UX design
- [Technical Specification](docs/plans/2026-03-23-technical-spec.md) — 29 technical decisions with rationale
- [Feature Matrix](docs/plans/2026-03-23-exhaustive-feature-matrix.md) — 1,307 checkable items for QA
- [Tool Definitions](ExploitBot/Sources/ExploitBot/Services/ToolDefinitions.swift) — 42 tool schemas in-app
- [Tool Registry](ExploitBotEngine/tools/registry.json) — external CLI mappings for supported binaries (39 entries)
- [System Prompts](ExploitBotEngine/prompts/) — Base + per-tab LLM instruction templates

### Runtime Verification

- `swift build --package-path ExploitBot -c debug`
- `python3 scripts/release-readiness-proof.py`
- `python3 scripts/verify-live-models.py --qwen ${EXPLOITBOT_MODELS}/JANGQ/Qwen3.6-27B-JANG_4M-MTP --metadata-only`
- `python3 scripts/verify-live-models.py --qwen ${EXPLOITBOT_RELEASE_QWEN_MODEL} --restart-replay --require-ssm-companion-hit`
- `python3 scripts/release-app-live-qwen-proof.py`
- `EXPLOITBOT_RELEASE_QWEN_MODEL=${EXPLOITBOT_RELEASE_QWEN_MODEL} python3 scripts/release-app-qwen-cross-restart-cache-proof.py`
- `python3 scripts/release-app-live-minimax-proof.py`
- `python3 scripts/zaya-visual-live-proof.py`
- `python3 scripts/agent-live-tool-status-proof.py`
- `python3 scripts/supply-chain-cve-ui-proof.py`
- `python3 scripts/cve-settings-actions-proof.py`
- `python3 scripts/terminal-tool-paths-proof.py`

## License

Open source. License TBD.

## Disclaimer

exploitbot is designed for authorized security testing, penetration testing engagements, CTF competitions, and security research. Always obtain proper authorization before testing any system you do not own. The developers are not responsible for misuse.

---

<p align="center">
  <a href="https://exploit.bot">exploit.bot</a> · Powered by vMLX engine · Built for Apple Silicon
</p>
