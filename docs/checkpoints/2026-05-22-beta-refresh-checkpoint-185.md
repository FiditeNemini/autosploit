# Checkpoint 185 - Subtab Coverage Endpoint

## Goal

Expose the shared subtab registry through a machine-readable QA route so the
state-backed tab surfaces can be audited without scraping view code.

## Changes

- Added `scripts/subtab-coverage-proof.py`.
- Added `GET /qa/subtab-coverage`, returning each covered tab's:
  - default subtab
  - current active subtab
  - valid subtab labels from `validSubtabs(for:)`
  - proof script name
  - subtab count
- Extended `scripts/app-qa-matrix-smoke-proof.py` to require
  `/qa/subtab-coverage` as part of the app-wide QA route contract.
- Updated the app flow and system review docs with the new audit route.

## Proof

```bash
python3 scripts/subtab-coverage-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
python3 scripts/web-subtab-state-proof.py
```

## Notes

The red proof failed because `GET /qa/subtab-coverage` did not exist. The green
proof verifies the route reflects both registry defaults and live active subtab
changes after a `/qa/tool-subtab` selection.
