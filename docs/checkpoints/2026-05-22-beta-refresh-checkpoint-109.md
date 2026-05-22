# Checkpoint 109: Tools Settings Status

## Scope

- Add a proofable status contract for the Tools settings panel.
- Make installed/missing/installing/error tool rows visible in state and visual
  proof.

## Changes

- Added deterministic QA tool status seeding.
- `/state.toolSettings` now exposes:
  - installed, missing, installing, and error counts;
  - `isInstalling`;
  - install log text;
  - active settings category;
  - per-tool name, category, install method, status, version, and path.
- Added proofs:
  - `scripts/tool-settings-status-proof.py`;
  - `scripts/visual-tool-settings-status-proof.py`.

## Proof

Commands:

```bash
python3 scripts/tool-settings-status-proof.py
python3 scripts/visual-tool-settings-status-proof.py
```

Result:

- Tools settings shows seeded installed, missing, installing, and error rows.
- `/state.toolSettings` reports the same counts and per-tool statuses.
- Visual artifact:
  `docs/visual-proofs/checkpoint-109/tool-settings-status.png`.

## Boundary

This proves the settings status contract and visible install/detection states.
It does not run live package installation.
