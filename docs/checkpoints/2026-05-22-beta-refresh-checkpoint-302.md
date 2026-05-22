# Checkpoint 302 - Context Retrieval Source Proof Map

## Goal
Tie each dynamic-context retrieval source to concrete proof scripts.

## Changes
- Added `/qa/context-coverage.retrievalSourceProofs`.
- Added `retrievalSourceProofCount` and `retrievalSourceProofParity`.
- Mirrored retrieval-source proof count/parity into
  `/qa/coverage-index.groups.chatAndContext`.
- Added `semantic-cve-proof.py` and `tool-fanout-status-proof.py` to the
  context coverage proof set because CVE and tool-output sources depend on
  those paths.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/context-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`

## Notes
The red context coverage proof failed because `/qa/context-coverage` exposed
retrieval source list/count/parity but not the proof map for asset ports,
findings, tool output, stash notes, and CVE context. The green path adds that map
and mirrors proof count/parity through the coverage index.
