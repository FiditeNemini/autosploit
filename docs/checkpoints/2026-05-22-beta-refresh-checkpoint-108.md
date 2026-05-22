# Checkpoint 108: CVE Settings Status

## Scope

- Make CVE Database settings progress/status script-checkable and visually
  proven.
- Keep live NVD import behavior unchanged.

## Changes

- Added deterministic QA CVE settings status seeding.
- `/state.cveDatabase` now exposes:
  - `isImporting`;
  - `importProgress`;
  - `totalCount`;
  - `kevCount`;
  - `lastSync`;
  - `searchResultCount`;
  - `activeSettingsCategory`.
- Added proofs:
  - `scripts/cve-settings-status-proof.py`;
  - `scripts/visual-cve-settings-status-proof.py`.

## Proof

Commands:

```bash
python3 scripts/cve-settings-status-proof.py
python3 scripts/visual-cve-settings-status-proof.py
```

Result:

- CVE Database settings opens on the CVE page with deterministic import
  progress, total/KEV counts, last-sync value, and two seeded CVE rows.
- Visual artifact:
  `docs/visual-proofs/checkpoint-108/cve-settings-import-status.png`.

## Boundary

This proves CVE settings status and import-progress visibility. It does not
perform a live NVD sync or prove real external API availability.
