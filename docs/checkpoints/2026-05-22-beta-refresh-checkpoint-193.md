# Checkpoint 193 - Tab Action Coverage Endpoint

## Goal

Expose per-tab direct action coverage through a machine-readable QA route so
copy buttons, row context actions, verify flows, report/finding actions, stash
controls, attribution, exports, and tab-specific action states can be audited
together.

## Changes

- Added `scripts/tab-action-coverage-proof.py`.
- Added `GET /qa/tab-action-coverage`, returning:
  - covered tabs in app order: Recon, Web, Network, Creds, Exploit, Post,
    OSINT, Report, and Stash
  - QA routes for each tab action seed and action endpoint
  - contract flags for copy actions, direct Web actions, row context actions,
    verification state, protocol/hash/exploit/post/OSINT actions, report
    generation/finding/export/agent actions, and Stash add/filter/copy/send/
    delete controls
  - proof scripts covering each contract
- Extended `scripts/app-qa-matrix-smoke-proof.py` to require the new route.
- Updated app flow and system review docs with the tab-action coverage route.

## Proof

```bash
python3 scripts/tab-action-coverage-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
python3 scripts/web-direct-actions-proof.py
```

## Notes

The red proof failed because `GET /qa/tab-action-coverage` did not exist. The
green proof verifies the route ties every per-tab action/copy/report/stash proof
cluster into one aggregate contract.
