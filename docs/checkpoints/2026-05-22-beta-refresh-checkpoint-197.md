# Checkpoint 197 - Parser And Fanout Aggregate Status

## Goal

Standardize the parser and representative tool-family fanout aggregate routes so
they expose the same `ok` pass/fail shape as the other QA coverage endpoints.

## Changes

- Added `scripts/parser-fanout-aggregate-proof.py`.
- Updated `GET /qa/result-parser-coverage` to return `ok=true` only when the
  seeded parser fixture has no failures.
- Updated `GET /qa/tool-family-fanout-coverage` to return `ok=true` only when
  all representative family fanout checks pass.
- Added the combined parser/fanout aggregate proof to `/qa/coverage-index`.

## Proof

```bash
python3 scripts/parser-fanout-aggregate-proof.py
python3 scripts/coverage-index-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
swift build --package-path ExploitBot
git diff --check
```

## Notes

The red proof failed because `/qa/result-parser-coverage` returned detailed
counts and failures but no standard `ok=true` marker. The green proof verifies
both parser and family-fanout aggregate routes now expose a direct pass/fail
contract.
