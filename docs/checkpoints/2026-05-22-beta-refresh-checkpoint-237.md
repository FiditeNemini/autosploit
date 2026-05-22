# Checkpoint 237 - Source-Derived Gap Ledger

## Goal

Make `/qa/gap-ledger` derive its current-gap list from the system review
document instead of duplicating the gap text in app code.

## Changes

- Updated `scripts/gap-ledger-proof.py` to require `sourceDerived=true` and an
  existing source path.
- Updated `GET /qa/gap-ledger` to read
  `docs/app-system-review-2026-05-21.md`.
- Added a parser for the `## Current Gaps To Close Next` numbered list.
- The endpoint still reports the current gap count, next gap, supported
  families, and Qwen VL blocked state.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/gap-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/gap-ledger` did not report source provenance.
The green path keeps the QA endpoint tied to the authoritative system-review
gap list while preserving the Qwen/MiniMax support boundary contract.
