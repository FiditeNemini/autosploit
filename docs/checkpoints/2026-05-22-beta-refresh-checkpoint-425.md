# Beta Refresh Checkpoint 425

## Goal

Expose a source-owned Swift theme inventory so action buttons, branding, color
tokens, overlays, controls, clipboard helpers, typography, and navigation
controls are grouped, documented, mirrored into coverage, and tied to proof
owners.

## Changes

- Added `scripts/theme-inventory-proof.py`.
- Added `/qa/theme-inventory`.
- Added `/qa/theme-inventory` to `/state.qaCoverage.stateRoutes`.
- Added source parsing for Swift files under
  `ExploitBot/Sources/ExploitBot/Theme`.
- Added grouping and proof-owner mapping for action buttons, branding, color
  tokens, overlays, controls, clipboard, typography, and navigation controls.
- Added static design-token inventory and corner-radius extraction.
- Added the `max-corner-radius-8` professional shape policy to the QA payload.
- Mirrored theme file counts, type counts, function counts, static-token
  counts, group counts, max corner radius, shape policy, and proof-file parity
  into `/qa/coverage-index.groups.settingsAndVisuals`.
- Updated coverage-index and app matrix proofs to require the theme inventory
  endpoint and mirror.
- Updated the system review and flow inventory docs with the theme inventory
  contract.

## Proof

- `python3 scripts/theme-inventory-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/theme-inventory` did not exist. The green
path keeps `ExploitBot/Sources/ExploitBot/Theme` as the authority and uses the
coverage index as the mirror, so future theme primitives, color tokens, font
tokens, clipboard helpers, controls, or radius policy changes must appear in
the source-derived inventory.
