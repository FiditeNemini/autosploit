# Checkpoint 196 - Coverage Index Endpoint

## Goal

Expose the complete aggregate QA coverage map through one machine-readable
endpoint so missing coverage routes, groups, or proof scripts are visible in one
place.

## Changes

- Added `scripts/coverage-index-proof.py`.
- Added `GET /qa/coverage-index`, returning:
  - all core state/API smoke endpoints
  - all aggregate QA endpoints for chat/context, runtime/cache,
    settings/visuals, tools/parsers, tabs/sessions, and app state
  - grouped endpoint/proof mappings
  - aggregate endpoint and proof counts
- Extended `scripts/app-qa-matrix-smoke-proof.py` to require the coverage index.
- Updated app flow and system review docs with the coverage index gate.

## Proof

```bash
python3 scripts/coverage-index-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
swift build --package-path ExploitBot
git diff --check
```

## Notes

The red proof failed because `GET /qa/coverage-index` did not exist. The green
proof verifies the index names the expected endpoints, groups, and proof scripts
and that every named proof file exists.
