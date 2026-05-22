# Checkpoint 288 - Context Retrieval Source Contract

## Goal
Make dynamic context coverage enumerate the bounded retrieval source families instead of only exposing snippet caps.

## Changes
- Added `/qa/context-coverage.retrievalSources`.
- Added `retrievalSourceCount` and `retrievalSourceParity`.
- Mirrored the retrieval source list/count/parity into `/qa/coverage-index.groups.chatAndContext`.
- Strengthened `scripts/context-coverage-proof.py`, `scripts/coverage-index-proof.py`, and `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/context-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red context coverage proof failed because `/qa/context-coverage` exposed bounded snippet caps and state keys, but not the source families allowed into dynamic retrieval. The green path names asset ports, findings, raw tool output, stash notes, and CVEs as bounded catalogue inputs.
