# Checkpoint 315 - Tool Family Fanout Map Aggregate

## Goal

Make the top-level coverage index name the representative tool used for each
tool-family fanout proof.

## Changes

- Added `familyFanoutTools` to `/qa/coverage-index.groups.toolsAndParsers`.
- Extended `scripts/coverage-index-proof.py` to assert the family-to-tool map.
- Extended `scripts/app-qa-matrix-smoke-proof.py` to include the same aggregate
  family fanout map check.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the tools/parsers aggregate exposed
only the representative family fanout count. The green path now lists the exact
representative tool for recon, web, network, creds, exploit, post, and OSINT
fanout coverage.
