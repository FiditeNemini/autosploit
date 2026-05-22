# Checkpoint 284 - Coverage Index Tabs Session Status Contract

## Goal
Mirror the visible tab activity status contract into `/qa/coverage-index.groups.tabsAndSessions`.

## Changes
- Updated `scripts/coverage-index-proof.py` to require the tabs/sessions group to mirror `tabActivityStatuses`.
- Added `tabActivityStatusCount`, `tabActivityStatusParity`, and `tabActivityIndicatorContract` checks for tabs/sessions.
- Mirrored the tool-flow tab activity status fields into `/qa/coverage-index.groups.tabsAndSessions`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red coverage-index proof failed because the tabs/sessions group exposed counts but not the tab activity visual status contract. The green path mirrors that contract into the tab/session-owned aggregate.
