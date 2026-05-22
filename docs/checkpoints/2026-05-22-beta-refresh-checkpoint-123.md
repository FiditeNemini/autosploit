# Checkpoint 123 - OSINT artifact action feedback

## Scope

- Make OSINT screenshot artifact actions more observable in state and visible
  on the row.

## Changes

- `OSINTArtifactActionState` now records:
  - `status`;
  - `summary`;
  - `lastAction`;
  - validated path/byte metadata;
  - recent action history.
- `/state.osintArtifactAction` exposes the new status and summary fields.
- `/state.osintArtifacts[*].actionLabels` exposes deterministic user-facing
  labels for open, reveal, and copy-path actions.
- `OSINTTabView` receives the artifact action state and shows the latest
  artifact action summary inline on the matching artifact row.
- `scripts/osint-artifact-actions-proof.py` now proves action status, summary,
  labels, file validation, and action history.
- `scripts/visual-osint-artifact-actions-proof.py` now triggers the open action
  before capture so the screenshot includes inline opened-artifact feedback.

## Verification

- `python3 scripts/osint-artifact-actions-proof.py`
- `python3 scripts/visual-osint-artifact-actions-proof.py`

## Notes

- This keeps artifact actions local and deterministic for QA. The proof uses a
  temporary screenshot fixture rather than a live external OSINT tool run.
