# Checkpoint 304 - Tab Activity Status Proof Map

## Goal
Tie each visible tab activity status to concrete proof scripts.

## Changes
- Added `/qa/tool-flow-coverage.tabActivityStatusProofs`.
- Added `tabActivityStatusProofCount` and `tabActivityStatusProofParity`.
- Mirrored status proof count/parity into `/qa/coverage-index.groups.toolsAndParsers`.
- Mirrored status proof count/parity into `/qa/coverage-index.groups.tabsAndSessions`.
- Added the relevant visual/action proofs to the tool-flow proof set.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`

## Notes
The red tool-flow proof failed because `/qa/tool-flow-coverage` named running,
done, failed, and canceled tab activity states but did not map those states to
the scripts that prove them. The green path adds that map and mirrors proof
count/parity through both tools/parsers and tabs/sessions coverage-index groups.
