# Checkpoint 234 - Global Audit Ledger

## Goal

Expose one QA endpoint that rolls proof-script, live-artifact, visual-capture,
and checkpoint-documentation ledgers into a single machine-readable audit
summary.

## Changes

- Added `scripts/audit-ledger-proof.py`.
- Added `GET /qa/audit-ledger`.
- The audit ledger reports proof count, visual manifest count, visual capture
  count, missing visual capture count, live proof count, live proof ok count,
  failed live proof count, checkpoint count, checkpoint completeness counts,
  latest checkpoint, and total ledger item count.
- Added `/qa/audit-ledger` to `/state.qaCoverage.stateRoutes`.
- Added the audit-ledger route, proof, and `auditLedgerCount` to
  `/qa/coverage-index.groups.appState`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/audit-ledger` did not exist. The green path
aggregates existing ledger helpers instead of duplicating their filesystem
scans, so the endpoint stays aligned with the underlying proof, artifact, and
checkpoint ledgers.
