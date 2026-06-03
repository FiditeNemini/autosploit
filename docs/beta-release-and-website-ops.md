# Beta Release and Website Ops

This document is safe to keep in the public repository. Do not add SSH passwords,
Apple notary passwords, keychain profile secrets, private `.env.signing` files, or
server-only paths that were shared out of band.

## Local release prerequisites

- Apple Silicon Mac with Xcode command line tools.
- Valid Developer ID Application certificate in the login keychain.
- vMLX-compatible bundled Python runtime at
  `/Applications/vMLX.app/Contents/Resources/bundled-python`, or set
  `EXPLOITBOT_BUNDLED_PYTHON_SOURCE` to another compatible `bundled-python`
  directory.
- Notary credentials provided through one of these secure local mechanisms:
  - `EXPLOITBOT_NOTARY_PROFILE=<keychain-profile>`
  - `NOTARIZE_APPLE_ID`, `NOTARIZE_TEAM_ID`, and `NOTARIZE_PASSWORD`

## Build a signed beta DMG

Unsigned local package:

```bash
./script/package_release.sh --skip-notarize
```

Notarized package using a keychain profile:

```bash
EXPLOITBOT_NOTARY_PROFILE=<profile-name> ./script/package_release.sh --notarize
```

Notarized package using a local signing environment file:

```bash
set +x
source /path/to/private/.env.signing
./script/package_release.sh --notarize
```

The script stages:

- `release/ExploitBot.app`
- `release/ExploitBot-beta.dmg`
- `release/release-manifest.json`

The script signs nested bundled Python Mach-O files, signs the app with hardened
runtime, notarizes and staples the app, builds the DMG with an `/Applications`
symlink, signs the DMG, notarizes and staples the DMG, then writes manifest
hashes.

## Required release verification

Run these checks after packaging:

```bash
codesign --verify --deep --strict --verbose=2 release/ExploitBot.app
codesign --verify --verbose=2 release/ExploitBot-beta.dmg
xcrun stapler validate release/ExploitBot.app
xcrun stapler validate release/ExploitBot-beta.dmg
spctl -a -vv --type execute release/ExploitBot.app
hdiutil verify release/ExploitBot-beta.dmg
python3 -m json.tool release/release-manifest.json >/dev/null
```

For a release smoke without loading a large model:

```bash
swift build --package-path ExploitBot -c debug
PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python -m pytest \
  ExploitBotEngine/testsuite/test_model_config_registry.py \
  ExploitBotEngine/testsuite/test_live_model_verifier.py -q
python3 scripts/tool-registry-coverage-proof.py
python3 scripts/cve-settings-actions-proof.py
python3 scripts/agent-loop-coverage-proof.py
```

For a release smoke with the smallest local Qwen target, use the existing live
proof scripts and keep only one model process running at a time:

```bash
EXPLOITBOT_RELEASE_QWEN_MODEL=/Users/eric/models/JANGQ/Qwen3.6-27B-JANG_4M-MTP \
  python3 scripts/release-app-live-qwen-proof.py
```

## GitHub release checklist

- Confirm `git status --short` is clean or only contains intended release doc
  edits.
- Confirm `release/release-manifest.json` reports
  `notarizationStatus: submitted-and-stapled`.
- Create or update the beta GitHub release.
- Attach `release/ExploitBot-beta.dmg`.
- Include the SHA256 from `release/release-manifest.json`.
- Do not include private server credentials, private signing files, or AI
  attribution in release notes.

## Website update checklist

The production website is managed out of band. Do not commit private SSH
credentials or server-only operational details to this repository.

Before editing the website:

- Confirm the latest DMG SHA256 and version from `release/release-manifest.json`.
- Prepare current screenshots from `assets/screenshots/` and
  `docs/visual-proofs/`.
- Retheme the site to match the current app: dark operational workspace,
  compact cards, restrained borders, app accent colors, and the existing
  exploitbot logo/icon treatment.
- Verify mobile layouts first: hero/download CTA, screenshot galleries, feature
  cards, language selector, and footer must remain usable on narrow screens.
- Update the download button to point at the current beta DMG and show the
  current beta version/hash.
- Update product copy for:
  - autonomous agent loop
  - local MLX inference
  - 42 integrated tool schemas
  - CVE import/search
  - supply-chain scanning
  - Qwen MXFP4-MTP hybrid SSM cache/runtime support
  - MiniMax full-KV cache/runtime support
  - MiniMax JANG_K metadata scope when full live load is not part of the pass
- Add or refresh screenshots for each major panel/tab:
  - Chat/autonomous agent loop with live tool status
  - Recon
  - Web
  - Network
  - Credentials
  - Exploit
  - Post-exploit
  - OSINT
  - Supply-chain/CVE Intel
  - Stash
  - Reports
  - Settings/cache/runtime
  - Terminal/tool paths
- Keep the language selector/i18n content in sync for English, Korean, Chinese,
  Spanish, and Japanese.
- Verify the site renders on desktop and mobile widths.
- Verify the download URL returns `200` and the linked artifact hash matches the
  GitHub release artifact.

After editing the website:

```bash
curl -I https://exploit.bot/
curl -I https://exploit.bot/<download-path>
```

Record public, non-secret website changes in a release checkpoint. Keep private
SSH details in the secure handoff channel only.
