# Checkpoint 134: Exploit Copy Actions

Date: 2026-05-22

## Changes

- Added `ExploitCopyActionState` and `/state.exploitCopyActions` so Exploit
  copy controls expose copied kind, count, clipboard preview, and summary.
- Routed Exploit toolbar and output/template copy operations through AppState
  for Metasploit, Reverse Shells, Custom, and C2 (Sliver).
- Added QA seed/copy routes:
  - `POST /qa/seed-exploit-copy-actions`
  - `POST /qa/exploit-copy`
- Added `scripts/exploit-copy-actions-proof.py`, which starts the app test
  server, seeds representative Metasploit output, reverse shell templates,
  custom script state, and Sliver output, then verifies copy state plus Exploit
  tab activity.
- Updated the system review and flow inventory docs to include the new Exploit
  copy proof surface.

## Verification

- `python3 scripts/exploit-copy-actions-proof.py`
- `python3 scripts/exploit-action-differentiation-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`
