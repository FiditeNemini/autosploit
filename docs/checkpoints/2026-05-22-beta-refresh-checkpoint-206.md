# Checkpoint 206 - Tab Action Seed Route Coverage

## Goal

Make `/qa/tab-action-coverage` expose the seed routes behind copy, export, and
agent tab-action proofs.

## Changes

- Strengthened `scripts/tab-action-coverage-proof.py` to require the Network,
  Creds, Exploit, Post, Report export, and Report agent seed routes.
- Updated `GET /qa/tab-action-coverage` with those seed routes.
- Updated docs with tab-action seed route coverage.

## Proof

- `python3 scripts/tab-action-coverage-proof.py`
- `python3 scripts/network-copy-actions-proof.py`
- `python3 scripts/creds-copy-actions-proof.py`
- `python3 scripts/exploit-copy-actions-proof.py`
- `python3 scripts/post-copy-actions-proof.py`
- `python3 scripts/report-export-proof.py`
- `python3 scripts/report-agent-action-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/tab-action-coverage` named the focused copy,
export, and report-agent proofs but did not list every seed route those proofs
use. The green path keeps the existing tab contracts and makes the setup/action
route chain visible from the aggregate endpoint.
