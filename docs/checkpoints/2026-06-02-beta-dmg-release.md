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

## Current status

- Packaging completed.
- App notarization submission accepted, stapled, and validated.
- DMG notarization submission accepted, stapled, and validated.
- `spctl` accepts `release/ExploitBot.app` as `Notarized Developer ID`.
- `hdiutil verify release/ExploitBot-beta.dmg` passed.

## Final artifact

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
