# Checkpoint 106: Web CVE Row Progress

## Scope

- Close the Web tab's remaining per-row CVE progress gap for vulnerability
  cards.
- Make CVE enrichment and active verification visible at both `/state` and UI
  level.

## Changes

- `/state.webCVERows` now exposes one record per vulnerability with a CVE:
  - `cve`;
  - `title`;
  - `target`;
  - row `status` (`pending`, `enriched`, or `verifying`);
  - `progressLabel`;
  - `hasDetails`.
- Web vulnerability cards now render a compact CVE progress chip:
  - `CVE pending`;
  - `CVE enriched`;
  - `CVE verifying`.
- The Web verify QA seed now includes an enriched CVE fixture so a queued verify
  row proves both enrichment and active row progress.

## Proof

Commands:

```bash
python3 scripts/web-verify-action-proof.py
python3 scripts/visual-web-verify-proof.py
```

Results:

- `scripts/web-verify-action-proof.py` verifies the global Web verify action,
  running Web tab activity, and row-level `CVE verifying` state.
- `scripts/visual-web-verify-proof.py` refreshed
  `docs/visual-proofs/checkpoint-96/web-verify-queued.png` and manifest text
  showing queued Verify plus the row-level CVE progress chip.

## Boundary

This covers Web vulnerability-card CVE row status. It does not replace real CVE
database import progress proof or real-model exploitation/verification behavior.
