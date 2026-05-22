# Checkpoint 221 - Coverage Index State Key Counts

## Goal

Make `/qa/coverage-index` summarize the state-key and action-state-key
accounting exposed by the lower-level coverage aggregates.

## Changes

- Strengthened `scripts/coverage-index-proof.py` to require state-key counts for
  chat/context, tools/parsers, and tabs/sessions groups.
- Updated `GET /qa/coverage-index` group metadata with `stateKeyCount` and
  `actionStateKeyCount` where relevant.
- Strengthened `scripts/app-qa-matrix-smoke-proof.py` so the top-level smoke
  proof catches missing coverage-index action-state accounting.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/coverage-index` exposed endpoint/proof counts
but not state-key accounting for the newly audited aggregate surfaces. The green
path makes those counts visible at the top-level QA index.
