# Checkpoint 259 - Audit Proof Surface Names

## Goal
Expose the normalized proof-category surface names through `/qa/audit-ledger` so tools can inspect the audit breadth directly instead of seeing only the surface count.

## Changes
- Updated `scripts/audit-ledger-proof.py` to require `proofCategorySurfaces`.
- Added `proofCategorySurfaces` to `/qa/audit-ledger`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red proof failed because `/qa/audit-ledger` exposed the proof surface count without naming the normalized proof surfaces. The green path makes the audit rollup report `agent`, `chat`, `context`, `runtime`, `settings`, `tabs`, `tools`, and `visual` explicitly.
