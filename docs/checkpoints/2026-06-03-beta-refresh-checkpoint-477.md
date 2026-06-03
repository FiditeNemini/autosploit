# Beta Refresh Checkpoint 477

Date: 2026-06-03

## Goal

Expose the user-facing tool/status/log/preview flow as one app-visible beta gate instead of leaving the evidence split across tab, parser, stash, report, and evidence lifecycle routes.

## Changes

- Added `GET /qa/live-status-preview-flow`.
- Wired the route into `/state.qaCoverage.stateRoutes`.
- Added rows for tool status indicators, agent status lines, activity-feed telemetry, result previews/parser coverage, stash preview/context handoff, report/finding/track management, and evidence lifecycle handoffs.
- Mirrored flow IDs, ready counts, blocked IDs, route parity, contract parity, and proof parity into the `toolsAndParsers` group of `/qa/coverage-index`.
- Mirrored ready count, contract parity, route parity, and proof parity into the `tabsAndSessions` group of `/qa/coverage-index`.
- Added `scripts/live-status-preview-flow-proof.py`.
- Updated `scripts/coverage-index-proof.py` to require the new route/proof and verify both coverage-index mirrors.
- Updated `README.md` with the new live status/log/preview flow gate and proof command.

## Proof

Red:

- `python3 scripts/live-status-preview-flow-proof.py`
- Initial failure: `/qa/live-status-preview-flow failed: {'error': 'unknown: GET /qa/live-status-preview-flow'}`

Green:

- `python3 scripts/live-status-preview-flow-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `swift build --package-path ExploitBot -c debug`
- `./script/package_release.sh --skip-notarize`
- `codesign --verify --verbose=2 release/ExploitBot-beta.dmg`
- `hdiutil verify release/ExploitBot-beta.dmg`
- Fresh local DMG SHA256: `8bf94bf623a569bc82979b84962a96cb72b4d3742b7c12da352e128f042b3c42`
- Notarization status: `not-submitted` for this local package build.

## Flow Rows

- `toolStatusIndicator`
- `agentStatusLine`
- `activityLogTelemetry`
- `resultPreviewParser`
- `stashPreviewContextHandoff`
- `reportFindingTrackManagement`
- `evidenceLifecycleHandoff`

## Remaining

- The broad active objective remains open until final app UI review, longer realistic chat/tool-call quality runs, and Qwen multimodal promotion are proven.
- This checkpoint proves route/index/source contracts for the user-facing status/log/preview flow; it does not replace the final hands-on release-window visual pass.
