# 2026-06-02 Beta DMG Release

This checkpoint tracks the June 2 beta DMG release attempt and website handoff.
Do not add private SSH credentials, Apple notary passwords, or private signing
environment files to this document.

## Release target

- App: `release/ExploitBot.app`
- DMG: `release/ExploitBot-beta.dmg`
- Manifest: `release/release-manifest.json`
- Signing identity: Developer ID Application for ShieldStack LLC
- Notarization: app and DMG should both be submitted and stapled before public
  download links are updated.

## Release script updates

- `script/package_release.sh` now supports both notary keychain profiles and the
  same environment-variable style used by the vMLX release flow.
- The app is notarized and stapled before being copied into the DMG.
- The DMG is signed, submitted separately to Apple notary service, stapled, and
  validated.
- `release/release-manifest.json` records whether notarization completed and
  includes verification commands for signatures and stapled tickets.

## Required verification

```bash
codesign --verify --deep --strict --verbose=2 release/ExploitBot.app
codesign --verify --verbose=2 release/ExploitBot-beta.dmg
xcrun stapler validate release/ExploitBot.app
xcrun stapler validate release/ExploitBot-beta.dmg
spctl -a -vv --type execute release/ExploitBot.app
hdiutil verify release/ExploitBot-beta.dmg
python3 -m json.tool release/release-manifest.json >/dev/null
```

## Website handoff

- Retheme `exploit.bot` to match the current app's dark operational UI.
- Preserve the current logo/icon treatment.
- Keep mobile layout usable for hero, download CTA, screenshots, language
  selector, and feature cards.
- Replace old screenshots with current app screenshots for chat, recon, web,
  network, credentials, exploit, post-exploit, OSINT, supply-chain/CVE, stash,
  reports, settings/cache/runtime, and terminal.
- Update the primary download link to the current beta DMG.
- Show the current beta version and SHA256 from `release/release-manifest.json`.
- Keep i18n pages/content in sync for English, Korean, Chinese, Spanish, and
  Japanese.

## Website update completed

- Live site: `https://exploit.bot/`
- Replaced the old March landing page with a new app-matched dark operational
  theme.
- Preserved the exploitbot logo/icon treatment.
- Added the published beta DMG URL and SHA256 in the hero and download sections.
- Replaced stale `30+`/old model copy with current beta copy:
  - autonomous agent loop
  - 42 tool schemas
  - CVE import/search
  - supply-chain scanning
  - Qwen/MiniMax cache/runtime proofing
  - ZAYA visual beta path
- Added a language selector with EN/KO/ZH/ES/JA text coverage for the primary
  hero/navigation/feature surfaces.
- Uploaded current screenshot/proof assets for chat/tool status, recon, exploit,
  CVE import, runtime cache settings, tool paths, network, credentials, OSINT,
  and report export.
- Updated the OSINT and report gallery cards to use cropped, versioned
  screenshot assets so CDN immutable caching does not keep stale dark crops:
  `osint-username-results-v3.png` and `report-export-status-v3.png`.
- Replaced notification-contaminated chat/tool screenshots with cleaned
  versioned captures:
  `chat-tool-states-v4.png` and `tool-settings-status-v4.png`.
- Updated `robots.txt`, `sitemap.xml`, `llms.txt`, `llms-full.txt`,
  `security.txt`, `.well-known/security.txt`, and `site.webmanifest` on the
  server.
- Added localized browser title/description updates and full visible-copy
  i18n coverage for EN/KO/ZH/ES/JA.
- Backed up the previous server `index.html` under the server-local backup
  directory before replacing it.

## Website verification

- `curl -L --max-time 20 https://exploit.bot/`
- `curl -I -L --max-time 20 https://exploit.bot/assets/screenshots/chat-tool-states.png`
- `curl -I -L --max-time 20 https://exploit.bot/assets/screenshots/settings-cache-topology.png`
- `curl -I -L --max-time 20 https://exploit.bot/assets/screenshots/osint-username-results-v3.png`
- `curl -I -L --max-time 20 https://exploit.bot/assets/screenshots/report-export-status-v3.png`
- `curl -I -L --max-time 20 https://github.com/jjang-ai/exploitbot/releases/download/v0.1.0-beta/ExploitBot-beta.dmg`
- Parsed the live HTML with Python's standard `html.parser`.
- Confirmed the live page includes `v0.1.0-beta` and the DMG SHA256.
- Rendered verification used a temporary Playwright install under
  `/tmp/exploitbot-pw`:
  - desktop viewport: `1440x1000`
  - mobile viewport: `390x844`
  - all 11 images loaded
  - no console errors
  - no horizontal overflow
  - DMG CTA href matched the GitHub beta asset
  - language selector changed the hero text for KO/ZH/ES/JA/EN
- Additional scrolled viewport screenshot confirmed the OSINT and report cards
  render their active UI screenshots, not blank stale cached image slots.
- `node /tmp/exploitbot-pw/verify-site-i18n-visual.js`
  - live desktop viewport: `1440x1000`
  - live mobile viewport: `390x844`
  - language modes checked: EN, KO, ZH, ES, JA
  - all 11 images loaded in each language/viewport pair
  - no console/page errors
  - no missing `data-i18n` keys
  - no empty translated labels
  - no horizontal overflow
  - localized page title/description updated per language
  - DMG CTA href and SHA256 remained correct
  - stale screenshot references were absent
- Visual captures inspected:
  - `/tmp/exploitbot-site-shots/desktop-en-full.png`
  - `/tmp/exploitbot-site-shots/mobile-en-full.png`
  - `/tmp/exploitbot-site-shots/mobile-ja-full.png`
  - `/tmp/exploitbot-site-shots/desktop-gallery-en-current.png`
  - `/tmp/exploitbot-site-shots/mobile-gallery-en-current.png`
  - `/tmp/exploitbot-site-shots/mobile-gallery-i18n-current.png`
- Cloudflare cache purge succeeded for the public metadata files. Cloudflare's
  managed robots feature still prepends its Content-Signal block unless the
  zone-level Bot Management setting is changed with broader Cloudflare
  permissions; the origin `robots.txt` itself is current and clean.

## Current status

- Packaging completed.
- App notarization submission accepted, stapled, and validated.
- DMG notarization submission accepted, stapled, and validated.
- `spctl` accepts `release/ExploitBot.app` as `Notarized Developer ID`.
- `hdiutil verify release/ExploitBot-beta.dmg` passed.

## Final artifact

- GitHub prerelease: `https://github.com/jjang-ai/exploitbot/releases/tag/v0.1.0-beta`
- Public DMG URL: `https://github.com/jjang-ai/exploitbot/releases/download/v0.1.0-beta/ExploitBot-beta.dmg`
- Version: `0.1.0-beta`
- DMG: `release/ExploitBot-beta.dmg`
- DMG size: `539 MB`
- DMG SHA256: `078322b60ac1b4c4d490c7404ef4fa556da136df7ea864021b158df246e165a0`
- App binary SHA256: `7c20926fd7e5f5dc5df0f17c83aae1847ec799d652f709bb101205f771cf05d9`
- Notarization status: `submitted-and-stapled`
- Team ID: `55KGF2S5AY`
- Manifest: `release/release-manifest.json`

## Verification run

- `codesign --verify --deep --strict --verbose=2 release/ExploitBot.app`
- `codesign --verify --verbose=2 release/ExploitBot-beta.dmg`
- `xcrun stapler validate release/ExploitBot.app`
- `xcrun stapler validate release/ExploitBot-beta.dmg`
- `spctl -a -vv --type execute release/ExploitBot.app`
- `hdiutil verify release/ExploitBot-beta.dmg`
- `python3 -m json.tool release/release-manifest.json`
- `gh release view v0.1.0-beta --json name,tagName,isPrerelease,isDraft,url,assets,targetCommitish,publishedAt`
- `curl -I -L --max-time 30 https://github.com/jjang-ai/exploitbot/releases/download/v0.1.0-beta/ExploitBot-beta.dmg`

## June 3 repo proof refresh

- `python3 scripts/tool-registry-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/beta-readiness-coverage-proof.py`
- `python3 scripts/release-readiness-proof.py`
- `python3 scripts/agent-autopilot-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

Notes:

- `release-readiness-proof.py` now supports both verified lanes: notarized and
  stapled when notary credentials are present, or signed local package with
  `requires-notary-credentials` when the ignored local `release/` artifacts are
  rebuilt without notary credentials.
- `run_shell` remains available in the agent tool catalogue, and the destructive
  command blocklist is now exported through `/qa/tool-registry-coverage` and
  checked by the registry and coverage-index proofs.
