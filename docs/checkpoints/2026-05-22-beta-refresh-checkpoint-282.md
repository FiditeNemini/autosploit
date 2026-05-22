# Checkpoint 282 - Tool Flow Tab Activity Status Parity

## Goal
Expose a parity flag proving the visible tab activity status list and count agree.

## Changes
- Updated `scripts/tool-flow-coverage-proof.py` to require `tabActivityStatusParity`.
- Updated `scripts/coverage-index-proof.py` to require the tools/parsers group to mirror `tabActivityStatusParity`.
- Added `tabActivityStatusParity` to `/qa/tool-flow-coverage` and `/qa/coverage-index.groups.toolsAndParsers`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red tool-flow proof failed because tab activity statuses and count were exposed without an explicit parity flag. The green path makes the visible tool/tab status contract self-checking.
