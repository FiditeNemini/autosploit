# ExploitBot Tool Bundling Inventory

**Date:** 2026-03-25
**Total tools in ToolDefinitions.swift:** 35 (33 external tools + `search_cve` internal + `run_shell`)

---

## Summary

| Category | Count | Bundleable | Python-dependent | Optional/System |
|----------|-------|------------|------------------|-----------------|
| Recon | 7 | 5 | 2 | 0 |
| Web | 9 | 4 | 5 | 0 |
| Network | 5 | 1 | 1 | 3 |
| Credentials | 4 | 1 | 0 | 3 |
| Exploit | 3 | 0 | 1 | 2 |
| Post-exploit | 1 | 0 | 1 | 0 |
| OSINT | 4 | 2 | 2 | 0 |
| **Total** | **33** | **13** | **12** | **8** |

Estimated bundle sizes:
- **Always Bundle (single binaries):** ~180 MB uncompressed, ~90 MB compressed
- **Bundle with Python (embedded):** ~300 MB for Python runtime + packages
- **Optional Download:** 500+ MB (Metasploit, Sliver, SecLists, hashcat)

---

## GROUP 1: Always Bundle (Single Binary, Essential)

These are statically compiled Go or Rust binaries with arm64 macOS releases. They have zero runtime dependencies and can be dropped directly into `~/.exploitbot/tools/`.

---

```
TOOL: subfinder
  Binary name: subfinder
  Category: recon
  Language: Go
  Install method: go install / GitHub release download
  GitHub repo: projectdiscovery/subfinder
  Latest release URL pattern: https://github.com/projectdiscovery/subfinder/releases/latest
  Release asset pattern: subfinder_<version>_darwin_arm64.zip
  arm64 macOS binary available: YES
  Estimated binary size: ~28 MB
  Bundle priority: P1 (must bundle)
  Bundle method: single binary
  Dependencies: none
  Notes: Core recon tool. ProjectDiscovery uses goreleaser, consistent naming.
         Current version: v2.12.0
```

```
TOOL: dnsx
  Binary name: dnsx
  Category: recon
  Language: Go
  Install method: go install / GitHub release download
  GitHub repo: projectdiscovery/dnsx
  Latest release URL pattern: https://github.com/projectdiscovery/dnsx/releases/latest
  Release asset pattern: dnsx_<version>_darwin_arm64.zip
  arm64 macOS binary available: YES
  Estimated binary size: ~22 MB
  Bundle priority: P1 (must bundle)
  Bundle method: single binary
  Dependencies: none
  Notes: Fast DNS resolver, pairs with subfinder. Current version: v1.2.3
```

```
TOOL: httpx
  Binary name: httpx
  Category: recon
  Language: Go
  Install method: go install / GitHub release download
  GitHub repo: projectdiscovery/httpx
  Latest release URL pattern: https://github.com/projectdiscovery/httpx/releases/latest
  Release asset pattern: httpx_<version>_darwin_arm64.zip
  arm64 macOS binary available: YES
  Estimated binary size: ~32 MB
  Bundle priority: P1 (must bundle)
  Bundle method: single binary
  Dependencies: none
  Notes: HTTP probing with tech detection. Essential for web recon pipeline.
```

```
TOOL: nuclei
  Binary name: nuclei
  Category: web
  Language: Go
  Install method: go install / GitHub release download
  GitHub repo: projectdiscovery/nuclei
  Latest release URL pattern: https://github.com/projectdiscovery/nuclei/releases/latest
  Release asset pattern: nuclei_<version>_macOS_arm64.zip
  arm64 macOS binary available: YES
  Estimated binary size: ~48 MB
  Bundle priority: P1 (must bundle)
  Bundle method: single binary
  Dependencies: none (templates auto-downloaded on first run to ~/.nuclei-templates/)
  Notes: Flagship vuln scanner. Largest Go binary due to embedded template engine.
         Templates are ~300MB but downloaded on demand, NOT bundled.
         Note macOS naming convention differs from other PD tools (macOS vs darwin).
```

```
TOOL: katana
  Binary name: katana
  Category: recon
  Language: Go
  Install method: go install / GitHub release download
  GitHub repo: projectdiscovery/katana
  Latest release URL pattern: https://github.com/projectdiscovery/katana/releases/latest
  Release asset pattern: katana_<version>_darwin_arm64.zip
  arm64 macOS binary available: YES
  Estimated binary size: ~30 MB
  Bundle priority: P1 (must bundle)
  Bundle method: single binary
  Dependencies: none (headless mode requires Chrome, but non-headless works standalone)
  Notes: Web crawler, critical for endpoint discovery before nuclei/dalfox.
```

```
TOOL: dalfox
  Binary name: dalfox
  Category: web
  Language: Go
  Install method: go install / GitHub release download
  GitHub repo: hahwul/dalfox
  Latest release URL pattern: https://github.com/hahwul/dalfox/releases/latest
  Release asset pattern: dalfox_<version>_darwin_arm64.tar.gz
  arm64 macOS binary available: YES
  Estimated binary size: ~18 MB
  Bundle priority: P1 (must bundle)
  Bundle method: single binary
  Dependencies: none
  Notes: XSS scanner. Current version: v2.12.0. Uses tar.gz not zip.
```

```
TOOL: feroxbuster
  Binary name: feroxbuster
  Category: web
  Language: Rust
  Install method: brew / GitHub release download
  GitHub repo: epi052/feroxbuster
  Latest release URL pattern: https://github.com/epi052/feroxbuster/releases/latest
  Release asset pattern: aarch64-macos-feroxbuster.tar.gz
  arm64 macOS binary available: YES
  Estimated binary size: ~2.5 MB (very compact Rust binary)
  Bundle priority: P1 (must bundle)
  Bundle method: single binary
  Dependencies: none
  Notes: Extremely small binary. Recursive dir brute-forcer. Asset naming uses
         "aarch64-macos" not "darwin_arm64" — handle in download logic.
```

```
TOOL: ffuf
  Binary name: ffuf
  Category: web
  Language: Go
  Install method: go install / GitHub release download
  GitHub repo: ffuf/ffuf
  Latest release URL pattern: https://github.com/ffuf/ffuf/releases/latest
  Release asset pattern: ffuf_<version>_darwin_arm64.tar.gz
  arm64 macOS binary available: YES
  Estimated binary size: ~8 MB
  Bundle priority: P1 (must bundle)
  Bundle method: single binary
  Dependencies: none
  Notes: General purpose web fuzzer. Very popular, lightweight.
```

```
TOOL: trufflehog
  Binary name: trufflehog
  Category: credentials
  Language: Go
  Install method: brew / GitHub release download
  GitHub repo: trufflesecurity/trufflehog
  Latest release URL pattern: https://github.com/trufflesecurity/trufflehog/releases/latest
  Release asset pattern: trufflehog_<version>_darwin_arm64.tar.gz
  arm64 macOS binary available: YES
  Estimated binary size: ~90 MB
  Bundle priority: P1 (must bundle)
  Bundle method: single binary
  Dependencies: none
  Notes: Secret scanner. Largest Go binary here due to embedded detectors for
         800+ secret types. Current version: v3.94.0. Consider downloading
         on demand if bundle size is a concern. Has install script:
         curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh
```

```
TOOL: chisel
  Binary name: chisel
  Category: network
  Language: Go
  Install method: go install / GitHub release download
  GitHub repo: jpillora/chisel
  Latest release URL pattern: https://github.com/jpillora/chisel/releases/latest
  Release asset pattern: chisel_<version>_darwin_arm64.gz
  arm64 macOS binary available: YES
  Estimated binary size: ~3.9 MB (gzipped)
  Bundle priority: P1 (must bundle)
  Bundle method: single binary
  Dependencies: none
  Notes: TCP/UDP tunnel over HTTP. Current version: v1.11.5. Uses .gz (not tar.gz).
         Essential for port forwarding in engagements.
```

```
TOOL: gowitness
  Binary name: gowitness
  Category: osint
  Language: Go
  Install method: go install / GitHub release download
  GitHub repo: sensepost/gowitness
  Latest release URL pattern: https://github.com/sensepost/gowitness/releases/latest
  Release asset pattern: gowitness-<version>-darwin-arm64
  arm64 macOS binary available: YES
  Estimated binary size: ~18 MB
  Bundle priority: P2 (should bundle)
  Bundle method: single binary
  Dependencies: Chrome/Chromium for screenshots (headless mode)
  Notes: Raw binary (no archive). Current version: v3.1.1. Requires Chrome
         to be installed for actual screenshot functionality.
         Uses hyphens in naming, not underscores.
```

```
TOOL: testssl
  Binary name: testssl.sh
  Category: web
  Language: Bash
  Install method: brew / git clone
  GitHub repo: drwetter/testssl.sh (also mirrored at testssl/testssl.sh)
  Latest release URL pattern: https://github.com/drwetter/testssl.sh/releases/latest
  arm64 macOS binary available: N/A (pure bash script)
  Estimated binary size: ~5 MB (script + bundled openssl + support files)
  Bundle priority: P1 (must bundle)
  Bundle method: script directory (testssl.sh + etc/ + bin/ + doc/)
  Dependencies: bash 3+, bundled openssl binary (included in release tarball)
  Notes: Current version: v3.2.0, dev branch 3.3dev. The release tarball includes
         a statically compiled openssl for testing. Script + support ~5MB.
         Must preserve directory structure, not just the .sh file.
```

```
TOOL: exiftool
  Binary name: exiftool
  Category: osint
  Language: Perl
  Install method: brew install exiftool
  GitHub repo: exiftool/exiftool
  Latest release URL pattern: https://github.com/exiftool/exiftool/releases/latest
  arm64 macOS binary available: N/A (Perl script, platform-independent)
  Estimated binary size: ~7 MB (script + lib directory)
  Bundle priority: P1 (must bundle)
  Bundle method: script + lib directory
  Dependencies: Perl 5.004+ (included in macOS by default)
  Notes: Current version: v13.53. macOS ships with Perl, so this just works.
         Bundle the exiftool script + lib/ directory. No compilation needed.
```

**Always Bundle subtotal: ~310 MB uncompressed, ~150 MB compressed (13 tools)**

---

## GROUP 2: Bundle with Python (Embedded Python Required)

These tools require Python 3 runtime. ExploitBot should bundle a minimal Python 3.12 environment (~50 MB) with these packages pre-installed via `pip install --target`.

---

```
TOOL: sqlmap
  Binary name: sqlmap
  Category: web
  Language: Python
  Install method: pip3 install sqlmap
  GitHub repo: sqlmapproject/sqlmap
  Latest release URL pattern: https://github.com/sqlmapproject/sqlmap/releases/latest
  arm64 macOS binary available: N/A (pure Python)
  Estimated package size: ~12 MB
  Bundle priority: P1 (must bundle)
  Bundle method: python package (pip install --target)
  Dependencies: Python 3.x (no native extensions)
  Notes: Pure Python, zero C dependencies. Can run with any Python 3.x.
         Critical SQL injection tool — must be available out of box.
```

```
TOOL: arjun
  Binary name: arjun
  Category: web
  Language: Python
  Install method: pip3 install arjun
  GitHub repo: s0md3v/Arjun
  Latest release URL pattern: https://github.com/s0md3v/Arjun/releases/latest
  arm64 macOS binary available: N/A (pure Python)
  Estimated package size: ~2 MB
  Bundle priority: P2 (should bundle)
  Bundle method: python package
  Dependencies: Python 3, requests
  Notes: Current version: v2.2.7. Hidden HTTP parameter discovery.
         Small and lightweight. Depends on requests library.
```

```
TOOL: sherlock
  Binary name: sherlock
  Category: osint
  Language: Python
  Install method: pip3 install sherlock-project
  GitHub repo: sherlock-project/sherlock
  Latest release URL pattern: https://github.com/sherlock-project/sherlock/releases/latest
  arm64 macOS binary available: N/A (pure Python)
  Estimated package size: ~5 MB (+ dependencies)
  Bundle priority: P2 (should bundle)
  Bundle method: python package
  Dependencies: Python 3.8+, requests, colorama, stem (optional Tor)
  Notes: Package name on PyPI is "sherlock-project" (not "sherlock").
         Current version: v0.15.0. Username OSINT across 400+ platforms.
```

```
TOOL: holehe
  Binary name: holehe
  Category: osint
  Language: Python
  Install method: pip3 install holehe
  GitHub repo: megadose/holehe
  Latest release URL pattern: https://github.com/megadose/holehe/releases/latest
  arm64 macOS binary available: N/A (pure Python)
  Estimated package size: ~2 MB
  Bundle priority: P2 (should bundle)
  Bundle method: python package
  Dependencies: Python 3, httpx[http2], aiohttp, trio
  Notes: Email OSINT tool. Async Python with httpx. Checks 120+ sites.
```

```
TOOL: impacket
  Binary name: secretsdump.py (also: impacket-secretsdump, psexec.py, etc.)
  Category: post-exploit
  Language: Python
  Install method: pip3 install impacket
  GitHub repo: fortra/impacket
  Latest release URL pattern: https://github.com/fortra/impacket/releases/latest
  arm64 macOS binary available: N/A (Python with C extensions)
  Estimated package size: ~15 MB (+ pycryptodome, ldap3, etc.)
  Bundle priority: P1 (must bundle)
  Bundle method: python package
  Dependencies: Python 3.9+, pycryptodome, ldap3, pyasn1, six
  Notes: Current version: v0.13.0. THE AD/Windows attack toolkit.
         Has C extensions (pycryptodome) that need compilation or pre-built wheels.
         Critical for any internal network pentest. Multiple entry points:
         secretsdump, psexec, wmiexec, GetUserSPNs, smbclient, etc.
         ToolDefinitions invokes as: python3 -m impacket.<script>
```

```
TOOL: netexec
  Binary name: netexec (alt: nxc)
  Category: network
  Language: Python
  Install method: pip3 install netexec / pipx
  GitHub repo: Pennyw0rth/NetExec
  Latest release URL pattern: https://github.com/Pennyw0rth/NetExec/releases/latest
  arm64 macOS binary available: NO (only Windows/Ubuntu PyInstaller binaries)
  Estimated package size: ~20 MB (heavy dependencies)
  Bundle priority: P2 (should bundle)
  Bundle method: python package
  Dependencies: Python 3.8+, impacket, paramiko, beautifulsoup4, lxml, many more
  Notes: Successor to CrackMapExec. Heavy dependency tree overlaps with impacket.
         No prebuilt macOS binary — must be pip installed. Network enumeration
         and exploitation tool for SMB/WinRM/LDAP/RDP.
```

```
TOOL: pwncat
  Binary name: pwncat-cs (alt: pwncat)
  Category: exploit
  Language: Python
  Install method: pip3 install pwncat-cs
  GitHub repo: calebstewart/pwncat
  Latest release URL pattern: https://github.com/calebstewart/pwncat/releases/latest
  arm64 macOS binary available: N/A (pure Python)
  Estimated package size: ~8 MB
  Bundle priority: P2 (should bundle)
  Bundle method: python package
  Dependencies: Python 3.9+, paramiko, prompt_toolkit, rich, ZODB
  Notes: Current version: v0.5.0. Reverse shell handler with auto-upgrade.
         Package is "pwncat-cs" on PyPI (not "pwncat", which is a different tool).
```

```
TOOL: theHarvester
  Binary name: theHarvester (alt: theharvester)
  Category: recon
  Language: Python
  Install method: pip3 install theHarvester / pipx
  GitHub repo: laramies/theHarvester
  Latest release URL pattern: https://github.com/laramies/theHarvester/releases/latest
  arm64 macOS binary available: N/A (pure Python)
  Estimated package size: ~5 MB
  Bundle priority: P2 (should bundle)
  Bundle method: python package
  Dependencies: Python 3.12+, aiohttp, aiodns, beautifulsoup4, shodan, etc.
  Notes: OSINT for emails/subdomains/IPs. Requires Python 3.12+ (strict).
         Many API integrations (Shodan, Censys, etc.) that need API keys.
```

```
TOOL: graphqlmap
  Binary name: graphqlmap
  Category: web
  Language: Python
  Install method: pip3 install graphqlmap / git clone
  GitHub repo: swisskyrepo/GraphQLmap
  Latest release URL pattern: https://github.com/swisskyrepo/GraphQLmap/releases/latest
  arm64 macOS binary available: N/A (pure Python)
  Estimated package size: ~1 MB
  Bundle priority: P3 (optional)
  Bundle method: python package or git clone
  Dependencies: Python 3.6+, requests
  Notes: Version 1.0. GraphQL introspection and injection. Niche tool.
         Very small. Not on PyPI — install from git clone + pip.
```

```
TOOL: jwt_tool
  Binary name: jwt_tool (alt: jwt_tool.py)
  Category: web
  Language: Python
  Install method: git clone + pip install deps
  GitHub repo: ticarpi/jwt_tool
  Latest release URL pattern: https://github.com/ticarpi/jwt_tool/releases/latest
  arm64 macOS binary available: N/A (Python script)
  Estimated package size: ~1 MB
  Bundle priority: P3 (optional)
  Bundle method: script + python deps
  Dependencies: Python 3, termcolor, pycryptodomex, requests
  Notes: Current version: v2.3.0. JWT testing toolkit. Single Python script
         with manual dependency install. Not a proper pip package.
         Bundle as script in tools directory.
```

**Python bundle subtotal: ~50 MB Python runtime + ~70 MB packages = ~120 MB**

---

## GROUP 3: Optional Download (Too Large or Complex)

These tools are too large, require special runtimes, or have complex installation needs. Offer as one-click download from within the app.

---

```
TOOL: metasploit
  Binary name: msfconsole
  Category: exploit
  Language: Ruby
  Install method: brew install --cask metasploit / installer from rapid7
  GitHub repo: rapid7/metasploit-framework
  Latest release URL pattern: https://github.com/rapid7/metasploit-framework/releases/latest
  arm64 macOS binary available: YES (via official installer)
  Estimated install size: ~500 MB
  Bundle priority: P3 (optional download)
  Bundle method: official installer or brew cask
  Dependencies: Ruby, PostgreSQL (for database), many gems
  Notes: Massive framework. Official installer from https://metasploit.com.
         Too large and complex to bundle. Detect if installed, offer install link.
         brew install --cask metasploit handles everything.
```

```
TOOL: sliver
  Binary name: sliver-client (alt: sliver)
  Category: exploit
  Language: Go
  Install method: brew install sliver / curl installer
  GitHub repo: BishopFox/sliver
  Latest release URL pattern: https://github.com/BishopFox/sliver/releases/latest
  arm64 macOS binary available: YES
  Estimated install size: ~290 MB (server) / ~16 MB (client only)
  Bundle priority: P3 (optional download)
  Bundle method: official installer
  Dependencies: none (statically compiled)
  Notes: C2 framework. The server binary is massive (~290 MB) because it
         embeds cross-compilers for implant generation. The client alone
         is ~16 MB. Most users need the full server.
         Install: curl https://sliver.sh/install | sudo bash
```

```
TOOL: hashcat
  Binary name: hashcat
  Category: credentials
  Language: C
  Install method: brew install hashcat
  GitHub repo: hashcat/hashcat
  Latest release URL pattern: https://github.com/hashcat/hashcat/releases/latest
  arm64 macOS binary available: YES (with Metal GPU backend)
  Estimated binary size: ~15 MB (binary) + ~50 MB (OpenCL kernels)
  Bundle priority: P3 (optional download)
  Bundle method: homebrew or compile from source
  Dependencies: Metal framework (macOS GPU), OpenCL runtime
  Notes: GPU-accelerated password cracker. v6.2.6+ supports Apple Metal.
         Needs Metal-compatible GPU and OpenCL kernels compiled for target.
         Not practical to bundle — too dependent on GPU/driver state.
         brew install hashcat handles Metal setup correctly.
```

```
TOOL: SecLists (wordlists)
  Binary name: N/A (data files)
  Category: support data
  Language: N/A
  Install method: git clone / GitHub release download
  GitHub repo: danielmiessler/SecLists
  Latest release URL pattern: https://github.com/danielmiessler/SecLists/releases/latest
  arm64 macOS binary available: N/A
  Estimated size: ~1.2 GB (full), ~50 MB (curated subset)
  Bundle priority: P3 (optional download)
  Bundle method: curated subset or on-demand download
  Dependencies: none
  Notes: Current version: 2026.1. Essential wordlists for ffuf, feroxbuster,
         hydra. Too large to bundle in full. STRATEGY: Bundle a curated
         mini-wordlist set (~50 MB) covering common-web-content, passwords-top-1M,
         and offer full SecLists as optional download.
```

---

## GROUP 4: System Tools (User Must Install)

These tools have system-level dependencies (root access, kernel modules, complex native libraries) that cannot be reliably bundled.

---

```
TOOL: nmap
  Binary name: nmap
  Category: recon
  Language: C/C++
  Install method: brew install nmap
  GitHub repo: nmap/nmap
  Latest release URL pattern: https://nmap.org/dist/ (not GitHub releases)
  arm64 macOS binary available: YES (via Homebrew bottle)
  Estimated binary size: ~8 MB (binary) + ~25 MB (NSE scripts, data files)
  Bundle priority: P2 (should bundle — attempt, fallback to system)
  Bundle method: homebrew bottle extraction or compile from source
  Dependencies: libpcap, OpenSSL, lua (for NSE scripts)
  Notes: Core scanning tool but complex to bundle due to shared library deps.
         Homebrew bottle for arm64 works well. NSE script library is large.
         STRATEGY: Check for system nmap first, offer brew install if missing.
         Could potentially bundle a static build but risky across macOS versions.
```

```
TOOL: masscan
  Binary name: masscan
  Category: recon
  Language: C
  Install method: brew install masscan
  GitHub repo: robertdavidgraham/masscan
  Latest release URL pattern: https://github.com/robertdavidgraham/masscan/releases/latest
  arm64 macOS binary available: YES (via Homebrew bottle, compiles from source)
  Estimated binary size: ~1 MB
  Bundle priority: P3 (optional — user installs)
  Bundle method: homebrew
  Dependencies: libpcap (raw socket access, may need root/sudo)
  Notes: Requires root/sudo for raw packet sending. Cannot be meaningfully
         bundled because it needs elevated privileges anyway.
         Tiny binary but root requirement makes bundling less useful.
```

```
TOOL: hydra
  Binary name: hydra
  Category: credentials
  Language: C
  Install method: brew install hydra
  GitHub repo: vanhauser-thc/thc-hydra
  Latest release URL pattern: https://github.com/vanhauser-thc/thc-hydra/releases/latest
  arm64 macOS binary available: YES (via Homebrew bottle)
  Estimated binary size: ~2 MB
  Bundle priority: P3 (optional — user installs)
  Bundle method: homebrew
  Dependencies: OpenSSL, libssh (NOT from Homebrew — must compile from source on macOS),
                various protocol libraries (mysql, postgres, etc.)
  Notes: Current version: v9.6. Online brute-forcer. Complex shared lib
         dependencies make bundling unreliable. libssh from Homebrew causes
         issues on macOS — must be compiled from source. Best left to user.
```

```
TOOL: tshark
  Binary name: tshark
  Category: network
  Language: C
  Install method: brew install wireshark
  GitHub repo: wireshark/wireshark
  Latest release URL pattern: https://github.com/wireshark/wireshark/releases/latest
  arm64 macOS binary available: YES (via Homebrew)
  Estimated binary size: ~80 MB (wireshark suite)
  Bundle priority: P3 (optional — user installs)
  Bundle method: homebrew (installs full wireshark)
  Dependencies: libpcap, GLib, GnuTLS, libgcrypt, many dissector libraries
  Notes: CLI version of Wireshark. Enormous dependency tree.
         brew install wireshark also installs the GUI. Cannot be bundled.
```

```
TOOL: bettercap
  Binary name: bettercap
  Category: network
  Language: Go
  Install method: brew install bettercap
  GitHub repo: bettercap/bettercap
  Latest release URL pattern: https://github.com/bettercap/bettercap/releases/latest
  arm64 macOS binary available: YES (v2.33.0+)
  Estimated binary size: ~25 MB
  Bundle priority: P3 (optional — user installs)
  Bundle method: homebrew or GitHub release
  Dependencies: libpcap, libusb (for BLE/HID), root/sudo for packet capture
  Notes: Network MITM framework. Requires root for most operations.
         Has arm64 darwin releases. Could theoretically bundle but root
         requirement diminishes the value.
```

```
TOOL: wpscan
  Binary name: wpscan
  Category: web
  Language: Ruby
  Install method: brew install wpscanteam/tap/wpscan / gem install wpscan
  GitHub repo: wpscanteam/wpscan
  Latest release URL pattern: https://github.com/wpscanteam/wpscan/releases/latest
  arm64 macOS binary available: N/A (Ruby gem)
  Estimated package size: ~15 MB (gem + dependencies)
  Bundle priority: P3 (optional — user installs)
  Bundle method: homebrew or gem install
  Dependencies: Ruby 2.7+, curl, various native gems
  Notes: WordPress vulnerability scanner. Ruby dependency makes bundling complex.
         Would need to embed Ruby runtime (another ~100 MB). Not worth it.
         macOS ships with Ruby removed since Ventura — needs brew Ruby.
```

```
TOOL: snmpwalk
  Binary name: snmpwalk
  Category: network
  Language: C
  Install method: brew install net-snmp
  GitHub repo: net-snmp/net-snmp (SourceForge primarily)
  Latest release URL pattern: https://github.com/net-snmp/net-snmp/releases/latest
  arm64 macOS binary available: YES (via Homebrew bottle)
  Estimated binary size: ~5 MB (full net-snmp suite)
  Bundle priority: P3 (optional — user installs)
  Bundle method: homebrew
  Dependencies: OpenSSL, shared SNMP libraries
  Notes: Part of net-snmp package. Niche use case. Shared library deps
         make bundling impractical.
```

```
TOOL: haiti
  Binary name: haiti
  Category: credentials
  Language: Ruby
  Install method: gem install haiti-hash
  GitHub repo: noraj/haiti
  Latest release URL pattern: https://github.com/noraj/haiti/releases/latest
  arm64 macOS binary available: N/A (Ruby gem)
  Estimated package size: ~2 MB
  Bundle priority: P3 (optional — user installs)
  Bundle method: gem install
  Dependencies: Ruby 2.7+
  Notes: Hash type identifier. Lightweight but requires Ruby.
         BUG in ToolInstaller.swift: installMethod says "pip" but installCommand
         uses "gem install haiti-hash". Fix the installMethod to "gem".
```

---

## Cross-Reference: Binary Name Mapping

The app's `ToolDefinitions.buildCliArgs()` maps tool names to binary names. Verify these match what gets bundled:

| Tool Name | Binary Called | Alt Binaries (detection) | Notes |
|-----------|-------------|-------------------------|-------|
| subfinder | `subfinder` | — | |
| dnsx | `dnsx` | — | |
| nmap | `nmap` | — | |
| httpx | `httpx` | — | |
| nuclei | `nuclei` | — | |
| katana | `katana` | — | |
| feroxbuster | `feroxbuster` | — | |
| sqlmap | `sqlmap` | — | |
| dalfox | `dalfox` | — | |
| hashcat | `hashcat` | — | |
| hydra | `hydra` | — | |
| sherlock | `sherlock` | — | |
| holehe | `holehe` | — | |
| masscan | `masscan` | — | |
| theharvester | `theHarvester` | `theharvester` | Case difference! |
| ffuf | `ffuf` | — | |
| arjun | `arjun` | — | |
| wpscan | `wpscan` | — | |
| testssl | `testssl.sh` | `testssl` | Has .sh extension |
| graphqlmap | `graphqlmap` | — | |
| jwt_tool | `jwt_tool` | `jwt_tool.py` | |
| netexec | `netexec` | `nxc` | |
| snmpwalk | `snmpwalk` | — | |
| tshark | `tshark` | — | |
| bettercap | `bettercap` | — | |
| chisel | `chisel` | — | |
| haiti | `haiti` | — | |
| trufflehog | `trufflehog` | — | |
| metasploit | `msfconsole` | — | |
| pwncat | `pwncat-cs` | `pwncat` | |
| sliver | `sliver-client` | `sliver` | |
| impacket | `python3 -m impacket.<script>` | `secretsdump.py`, `impacket-secretsdump` | Special invocation |
| exiftool | `exiftool` | — | |
| gowitness | `gowitness` | — | |

---

## Bugs Found in ToolInstaller.swift

1. **Line 229 — haiti installMethod mismatch:** `installMethod: "pip"` but `installCommand: "gem install haiti-hash"`. Should be `installMethod: "gem"`.

2. **General — no bundled tool path priority:** Detection checks `/opt/homebrew/bin`, `/usr/local/bin`, `/usr/bin`, `~/.exploitbot/tools`, `~/.local/bin` but `~/.exploitbot/tools` is 4th in priority. For bundled tools, it should be checked FIRST to prefer the app's bundled version.

3. **No version pinning:** All `go install` commands use `@latest` and pip commands don't pin versions. Bundled tools should pin to tested versions for reproducibility.

---

## Recommended Bundle Architecture

```
ExploitBot.app/
  Contents/
    Resources/
      tools/
        bin/                          # Single binary tools (~180 MB)
          subfinder
          dnsx
          httpx
          nuclei
          katana
          dalfox
          feroxbuster
          ffuf
          trufflehog
          chisel
          gowitness
          exiftool                    # Perl script (macOS has Perl)
        testssl/                      # testssl.sh directory
          testssl.sh
          etc/
          bin/openssl.Darwin.arm64
        python/                       # Embedded Python (~50 MB)
          bin/python3
          lib/python3.12/
            site-packages/
              sqlmap/
              arjun/
              sherlock_project/
              holehe/
              impacket/
              netexec/
              pwncat/
              theharvester/
        wordlists/                    # Curated mini-set (~20 MB)
          common.txt
          passwords-top-1m.txt
          subdomains-top-10k.txt
```

**Estimated total bundle addition: ~250-350 MB compressed**

---

## Download Priority Matrix

| Priority | Action | Tools | User Experience |
|----------|--------|-------|-----------------|
| P1 | Bundle in .app | 13 single binaries + testssl + exiftool | Works instantly on first launch |
| P1 | Bundle Python + packages | sqlmap, impacket, sherlock, holehe, arjun, netexec, pwncat, theHarvester | Works instantly on first launch |
| P2 | One-click download from app | metasploit, sliver, hashcat, SecLists, wpscan | Download button in Tools panel |
| P3 | Show install instructions | nmap, masscan, hydra, tshark, bettercap, snmpwalk, haiti | "brew install X" hint with copy button |

---

## GitHub Release URL Patterns (for auto-updater)

```
# ProjectDiscovery tools (consistent pattern)
https://github.com/projectdiscovery/{tool}/releases/download/v{ver}/{tool}_{ver}_{os}_{arch}.zip

# Exceptions to PD pattern:
nuclei: nuclei_{ver}_macOS_{arch}.zip  (macOS not darwin)

# Other Go tools
https://github.com/hahwul/dalfox/releases/download/v{ver}/dalfox_{ver}_darwin_arm64.tar.gz
https://github.com/ffuf/ffuf/releases/download/v{ver}/ffuf_{ver}_darwin_arm64.tar.gz
https://github.com/trufflesecurity/trufflehog/releases/download/v{ver}/trufflehog_{ver}_darwin_arm64.tar.gz
https://github.com/jpillora/chisel/releases/download/v{ver}/chisel_{ver}_darwin_arm64.gz
https://github.com/sensepost/gowitness/releases/download/{ver}/gowitness-{ver}-darwin-arm64

# Rust tools
https://github.com/epi052/feroxbuster/releases/download/v{ver}/aarch64-macos-feroxbuster.tar.gz

# Scripts
https://github.com/drwetter/testssl.sh/releases/download/v{ver}/testssl.sh-{ver}.tar.gz
https://github.com/exiftool/exiftool/releases/download/{ver}/Image-ExifTool-{ver}.tar.gz
```

---

Sources:
- [projectdiscovery/subfinder](https://github.com/projectdiscovery/subfinder/releases)
- [projectdiscovery/dnsx](https://github.com/projectdiscovery/dnsx/releases)
- [projectdiscovery/httpx](https://github.com/projectdiscovery/httpx/releases)
- [projectdiscovery/nuclei](https://github.com/projectdiscovery/nuclei/releases)
- [projectdiscovery/katana](https://github.com/projectdiscovery/katana/releases)
- [hahwul/dalfox](https://github.com/hahwul/dalfox/releases)
- [epi052/feroxbuster](https://github.com/epi052/feroxbuster/releases)
- [ffuf/ffuf](https://github.com/ffuf/ffuf/releases)
- [trufflesecurity/trufflehog](https://github.com/trufflesecurity/trufflehog/releases)
- [jpillora/chisel](https://github.com/jpillora/chisel/releases)
- [sensepost/gowitness](https://github.com/sensepost/gowitness/releases)
- [drwetter/testssl.sh](https://github.com/drwetter/testssl.sh/releases)
- [exiftool/exiftool](https://github.com/exiftool/exiftool/releases)
- [sqlmapproject/sqlmap](https://github.com/sqlmapproject/sqlmap)
- [s0md3v/Arjun](https://github.com/s0md3v/Arjun/releases)
- [sherlock-project/sherlock](https://github.com/sherlock-project/sherlock/releases)
- [megadose/holehe](https://github.com/megadose/holehe)
- [fortra/impacket](https://github.com/fortra/impacket/releases)
- [Pennyw0rth/NetExec](https://github.com/Pennyw0rth/NetExec/releases)
- [calebstewart/pwncat](https://github.com/calebstewart/pwncat/releases)
- [laramies/theHarvester](https://github.com/laramies/theHarvester/releases)
- [swisskyrepo/GraphQLmap](https://github.com/swisskyrepo/GraphQLmap)
- [ticarpi/jwt_tool](https://github.com/ticarpi/jwt_tool/releases)
- [rapid7/metasploit-framework](https://github.com/rapid7/metasploit-framework)
- [BishopFox/sliver](https://github.com/BishopFox/sliver/releases)
- [hashcat/hashcat](https://github.com/hashcat/hashcat/releases)
- [danielmiessler/SecLists](https://github.com/danielmiessler/SecLists/releases)
- [nmap/nmap](https://github.com/nmap/nmap)
- [robertdavidgraham/masscan](https://github.com/robertdavidgraham/masscan/releases)
- [vanhauser-thc/thc-hydra](https://github.com/vanhauser-thc/thc-hydra/releases)
- [bettercap/bettercap](https://github.com/bettercap/bettercap/releases)
- [wpscanteam/wpscan](https://github.com/wpscanteam/wpscan/releases)
- [noraj/haiti](https://github.com/noraj/haiti/releases)
