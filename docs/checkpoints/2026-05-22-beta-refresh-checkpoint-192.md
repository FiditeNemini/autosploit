# Checkpoint 192 - Session Coverage Endpoint

## Goal

Expose app-session workflow coverage through a machine-readable QA route so
onboarding, mode selection, sidebar operation actions, overlays, model-folder
pickers, persistence, saved messages, restored results, finding wizard submit,
tab switching, phase changes, and activity feed controls can be audited
together.

## Changes

- Added `scripts/session-coverage-proof.py`.
- Added `GET /qa/session-coverage`, returning:
  - available interaction modes in app order
  - supported overlay and sidebar action names
  - QA routes for onboarding, sidebar, overlays, model-folder pickers,
    persistence, saving messages, finding wizard submit, and manual tab switch
  - contract flags for mode selection, pending-approval rejection, sidebar CRUD,
    create-op stop behavior, overlay actions, model-folder pickers, persistence
    across relaunch, saved messages, result-store rebuild, finding wizard
    submit, tab switch actions, phase actions, and activity feed actions
  - proof scripts covering each contract
- Extended `scripts/app-qa-matrix-smoke-proof.py` to require the new route.
- Updated app flow and system review docs with the session coverage route.

## Proof

```bash
python3 scripts/session-coverage-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
python3 scripts/window-overlay-actions-proof.py
```

## Notes

The red proof failed because `GET /qa/session-coverage` did not exist. The
green proof verifies the route ties the cross-app session workflows and their
focused proof scripts into one aggregate contract.
