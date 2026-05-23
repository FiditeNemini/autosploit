# Beta Refresh Checkpoint 423

## Goal

Expose a source-owned Python runtime inventory so engine modules, parser
modules, cache/SSM modules, engine tests, proof scripts, and data pipeline
scripts are grouped, documented, mirrored into coverage, and tied to proof
owners.

## Changes

- Added `scripts/python-runtime-inventory-proof.py`.
- Added `/qa/python-runtime-inventory`.
- Added `/qa/python-runtime-inventory` to `/state.qaCoverage.stateRoutes`.
- Added source parsing for Python files under `ExploitBotEngine` and `scripts`.
- Added grouping and proof-owner mapping for engine runtime, API adapters,
  reasoning parsers, tool parsers, cache/SSM, engine tests, QA proofs, and data
  pipelines.
- Mirrored Python runtime file counts, class counts, function counts, group
  counts, and proof-file parity into
  `/qa/coverage-index.groups.runtimeAndCache`.
- Updated coverage-index and app matrix proofs to require the Python runtime
  inventory endpoint and mirror.
- Updated the system review and flow inventory docs with the Python runtime
  inventory contract.

## Proof

- `python3 scripts/python-runtime-inventory-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/python-runtime-inventory` did not exist. The
green path keeps `ExploitBotEngine` and `scripts` as the authority and uses
coverage-index as the mirror, so future runtime, parser, cache, test, proof, or
pipeline Python additions must appear in the source-derived inventory.
