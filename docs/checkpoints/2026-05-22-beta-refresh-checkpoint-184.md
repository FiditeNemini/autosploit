# Checkpoint 184 - QA Matrix Subtab Coverage

## Goal

Make the app-wide QA matrix expose and verify the shared subtab-state proof
contract after moving all visible `SubtabBar` surfaces onto AppState.

## Changes

- Extended `scripts/app-qa-matrix-smoke-proof.py` to require:
  - `/state.qaCoverage.subtabStateTabs`
  - `/state.qaCoverage.subtabStateProofs`
- Added the eight shared subtab proof gates to `qaCoverageSnapshot()`:
  Recon, Web, Network, Creds, Exploit, Post, OSINT, and Report.
- Updated the app flow and system review docs so the QA matrix documents this
  coverage explicitly.

## Proof

```bash
python3 scripts/app-qa-matrix-smoke-proof.py
python3 scripts/report-subtab-state-proof.py
```

## Notes

The red run failed because `/state.qaCoverage` did not advertise subtab proof
coverage. The green run verifies that the app-level QA matrix now names every
shared subtab-state proof gate.
