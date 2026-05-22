# Checkpoint 125 - all-family tool fanout proof

## Scope

- Prove representative tool fanout across every major tool tab, not just a
  single `nmap` lane.

## Changes

- Added `scripts/tool-family-fanout-coverage-proof.py`.
  - Seeds deterministic Recon, Web, Network, Creds, Exploit, Post, and OSINT
    representative tool outputs.
  - Verifies each family has:
    - a visible chat tool card;
    - a recent activity-feed entry;
    - a tab activity status with the expected representative tool;
    - a parsed tab result;
    - a dynamic context-catalog hit.
- Added QA routes:
  - `POST /qa/seed-tool-family-fanout-fixture`;
  - `GET /qa/tool-family-fanout-coverage`.
- Added `linpeas` to `tabForTool(...)` so post-exploitation privilege
  escalation output maps to the Post tab during fanout/activity tracking.
- Updated the review docs and flow inventory so the broad "each tool family"
  proof is listed as covered.

## Verification

- `python3 scripts/tool-family-fanout-coverage-proof.py`

## Notes

- This is a deterministic fixture proof. Real external binary execution remains
  covered separately by `scripts/tool-fanout-status-proof.py` and live-turn
  harnesses.
