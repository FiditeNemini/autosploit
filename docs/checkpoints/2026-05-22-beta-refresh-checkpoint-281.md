# Checkpoint 281 - Tool Flow Tab Activity Status Contract

## Goal
Make the visible tab activity/status indicator contract machine-readable from tool-flow coverage and the aggregate coverage index.

## Changes
- Updated `scripts/tool-flow-coverage-proof.py` to require visible tab activity statuses.
- Updated `scripts/coverage-index-proof.py` to require the tools/parsers group to mirror the tab activity status contract.
- Added `tabActivityStatuses`, `tabActivityStatusCount`, and `tabActivityIndicatorContract` to `/qa/tool-flow-coverage`.
- Mirrored those fields through `/qa/coverage-index.groups.toolsAndParsers`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red tool-flow proof failed because `/qa/tool-flow-coverage` named `tabActivities` as a state surface but did not expose the visible status states or indicator contract. The green path makes those tab activity visuals auditable.
