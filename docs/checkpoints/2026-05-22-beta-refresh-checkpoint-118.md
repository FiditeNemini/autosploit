# Checkpoint 118: Result Parser Routing Proof

## Scope

- Prove representative tool output reaches tab/result state through
  `ResultsStore.ingest(...)`.
- Cover structured parser branches across Recon, Web, Network, Creds, Exploit,
  Post, OSINT, screenshot artifacts, and raw-only tools.
- Expose proof-grade parser coverage through QA routes instead of relying on
  broad `/results` counts alone.

## Changes

- Added `scripts/result-parser-routing-proof.py`.
- Added `POST /qa/seed-result-parser-fixture`.
- Added `GET /qa/result-parser-coverage`.
- The fixture seeds representative output for:
  - structured tools including `subfinder`, `dnsx`, `httpx`, `nuclei`, `nmap`,
    `katana`, `feroxbuster`, `ffuf`, `dalfox`, `sqlmap`, `haiti`,
    `trufflehog`, `holehe`, `exiftool`, `masscan`, `netexec`, `hydra`,
    `wpscan`, `testssl`, `theharvester`, `arjun`, `jwt_tool`, `hashcat`,
    `snmpwalk`, `metasploit`, `impacket`, `linpeas`, `gowitness`, and
    `graphqlmap`;
  - raw-only tools `tshark`, `bettercap`, `chisel`, `pwncat`, and `sliver`.
- Updated the system review and flow inventory so this parser-routing proof is
  part of the repeatable QA matrix.

## Proof

Command:

```bash
python3 scripts/result-parser-routing-proof.py
```

Result:

- The proof first failed because `POST /qa/seed-result-parser-fixture` did not
  exist.
- After wiring the QA fixture and coverage endpoint, it proved:
  - every expected structured parser emitted tab/result state;
  - raw-only tools were preserved as raw output;
  - parsed state crossed all major collections: subdomains, web hosts, vulns,
    ports, network hosts, OSINT entries, post attribution, screenshots, and raw
    results;
  - `/results` exposes parsed `nmap` port data and screenshot artifact preview
    metadata.

## Boundary

This is representative parser coverage. It proves current parser branches route
known output shapes into app state, but it does not claim exhaustive coverage of
every possible real-world output variant from every external tool version.
