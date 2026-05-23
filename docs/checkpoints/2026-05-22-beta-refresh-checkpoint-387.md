# Checkpoint 387 - Visual Tab Proof Family Coverage

## Goal

Expose screenshot-backed visual proof families by individual tab and roll that
accounting up through the top-level coverage index.

## Changes

- Added `/qa/visual-coverage.visualTabProofFamilies` for recon, web, network,
  creds, exploit, post, osint, report, and stash visual proof evidence.
- Added visual tab family count, key parity, and script file parity fields to
  `/qa/visual-coverage`.
- Mirrored the visual tab family fields through
  `/qa/coverage-index.groups.settingsAndVisuals`.
- Extended `scripts/visual-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py` to enforce the visual tab family
  contract.
- Added `visual-osint-artifact-actions-proof.py` to the top-level visual proof
  list so OSINT action evidence is not only visible inside the tab family map.

## Proof

- `python3 scripts/visual-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red visual proof first failed because `/qa/visual-coverage` did not expose
`visualTabProofFamilies`. A later red proof failed because
`visual-osint-artifact-actions-proof.py` was present in the OSINT tab family but
missing from the endpoint's top-level visual proof list.
