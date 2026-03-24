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
  <a href="https://exploit.bot">Website</a> •
  <a href="#features">Features</a> •
  <a href="#install">Install</a> •
  <a href="#models">Models</a> •
  <a href="#tools">Tools</a> •
  <a href="docs/plans/2026-03-23-exploitbot-design.md">Design Doc</a>
</p>

---

AI-powered penetration testing toolkit with local LLM inference. No cloud. No guardrails. Open source.

exploitbot runs uncensored models locally on your Mac via [MLX](https://github.com/ml-explore/mlx), integrated with 30+ real pentesting tools, and generates professional pentest reports from findings.

<p align="center">
  <img src="assets/screenshots/main-workspace.png" alt="exploitbot workspace" width="900">
</p>

## Features

**Local AI Inference** — Uncensored models running on Apple Silicon via the [vMLX engine](https://github.com/jjang-ai/vmlx). No API keys, no cloud, no content filtering. Your pentest stays on your machine.

**Ops System** — Named persistent workspaces for each engagement. Switch between targets without losing context. The LLM remembers everything across tool tabs.

**3 Interaction Modes**
- **Autopilot** — Give a target, watch it work. Full autonomous recon → exploitation → reporting.
- **Copilot** — AI suggests tools, you approve. Each action explained with risk level.
- **Manual** — You drive, AI advises. Full tool controls with chat-based guidance.

**30+ Integrated Tools** — subfinder, nmap, nuclei, sqlmap, hashcat, metasploit, impacket, and more. Each tool has a bespoke UI — not a generic wrapper.

**Stash** — Cross-op artifact sharing. Drop credentials, hosts, payloads from any engagement, pull them into any other.

**Findings → Reports** — The endgame. Confirmed vulnerabilities auto-capture attack chains, evidence, and impact. Generate professional pentest reports in PDF, Markdown, HTML, or JSON.

**CVE Knowledge Base** — Local database of 250K+ CVEs with semantic search. Auto-enriches findings with CVE data, CVSS scores, and exploit availability.

**5 Languages** — Full interface and report generation in English, 한국어, 中文, Español, 日本語.

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
cd exploitbot/ExploitBot

# Build
swift build

# Create .app bundle and launch
cp .build/debug/ExploitBot ../ExploitBotXcode/ExploitBot.app/Contents/MacOS/ExploitBot
open ../ExploitBotXcode/ExploitBot.app
```

**Prerequisites:**
- macOS 14+ on Apple Silicon
- Xcode 16+ (Swift toolchain)
- A vMLX-compatible model running on localhost:8000 (see [vMLX](https://github.com/jjang-ai/vmlx))
- Pentesting tools installed via homebrew/pip for tool execution

<a name="models"></a>
## Models

exploitbot includes a model downloader with curated uncensored models from [dealignai](https://huggingface.co/dealignai):

| Tier | Model | Size | RAM |
|------|-------|------|-----|
| **S** | [Qwen3.5-VL-122B-A10B-UNCENSORED-JANG_2S](https://huggingface.co/dealignai/Qwen3.5-VL-122B-A10B-UNCENSORED-JANG_2S) | ~30 GB | 32+ GB |
| **M** | [MiniMax-M2.5-UNCENSORED-JANG_2L](https://huggingface.co/dealignai/MiniMax-M2.5-UNCENSORED-JANG_2L) | ~60 GB | 64+ GB |
| **L** | [Qwen3.5-VL-397B-A17B-UNCENSORED-JANG_1L](https://huggingface.co/dealignai/Qwen3.5-VL-397B-A17B-UNCENSORED-JANG_1L) | ~112 GB | 128+ GB |

You can also load any JANG or MLX-compatible model folder from your local disk.

<a name="tools"></a>
## Tools

39 integrated pentesting tools across 8 categories:

| Category | Tools |
|----------|-------|
| **Recon** | subfinder, dnsx, nmap, masscan, httpx, katana, theHarvester |
| **Web** | nuclei, sqlmap, dalfox, feroxbuster, ffuf, arjun, wpscan, testssl, graphqlmap, jwt_tool |
| **Network** | netexec, snmpwalk, tshark, bettercap, chisel |
| **Credentials** | hashcat, hydra, haiti, trufflehog, seclists |
| **Exploit** | metasploit, pwncat, pwntools, sliver |
| **Post-Exploit** | linpeas, winpeas, impacket |
| **OSINT** | sherlock, holehe, exiftool, gowitness |
| **General** | search_cve (local CVE DB), run_shell |

Lightweight tools are bundled in the app. Heavy tools (metasploit, hashcat, etc.) are installed on first use via homebrew/pip.

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
- [Tool Registry](ExploitBotEngine/tools/registry.json) — 39 tool schemas with CLI mappings
- [System Prompts](ExploitBotEngine/prompts/) — Base + per-tab LLM instruction templates

## License

Open source. License TBD.

## Disclaimer

exploitbot is designed for authorized security testing, penetration testing engagements, CTF competitions, and security research. Always obtain proper authorization before testing any system you do not own. The developers are not responsible for misuse.

---

<p align="center">
  <a href="https://exploit.bot">exploit.bot</a> · Powered by vMLX engine · Built for Apple Silicon
</p>
