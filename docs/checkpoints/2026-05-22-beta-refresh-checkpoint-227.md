# Checkpoint 227 - Tabs Session Index Counts

## Goal

Make `/qa/coverage-index.groups.tabsAndSessions` expose the mode and tab breadth
already proven by `/qa/session-coverage` and `/qa/tab-action-coverage`.

## Changes

- Strengthened `scripts/coverage-index-proof.py` to require interaction-mode
  count and covered tab count on the tabs/sessions group.
- Updated `GET /qa/coverage-index` so `tabsAndSessions` includes
  `interactionModeCount`, `coveredTabCount`, `stateKeyCount`, and
  `actionStateKeyCount`.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/session-coverage-proof.py`
- `python3 scripts/tab-action-coverage-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because the tabs/sessions group only exposed state-key
accounting. The green path keeps the focused session and tab-action routes as
the detailed contracts while making mode and tab breadth visible from the
top-level QA index.
