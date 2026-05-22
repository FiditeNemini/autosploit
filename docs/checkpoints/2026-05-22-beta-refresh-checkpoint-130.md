# Beta Refresh Checkpoint 130 - Web Direct Actions

## Changed

- Added `scripts/web-direct-actions-proof.py` to cover Web tab direct actions:
  Create Finding, Stash, Copy, and Search Related CVEs.
- Added `/state.webDirectActions` with:
  - direct action labels;
  - last action/status;
  - finding wizard visibility and prefill fields;
  - stash count and preview;
  - clipboard preview;
  - queued related-CVE prompt.
- Added QA routes:
  - `/qa/seed-web-direct-actions`
  - `/qa/web-create-finding`
  - `/qa/web-stash`
  - `/qa/web-copy`
  - `/qa/web-search-related`
- Routed Web tab vulnerability-card Stash, Copy, and Search Related CVEs
  through AppState handlers. Create Finding already used a callback and now
  records a direct action state before opening the finding wizard.

## Proof

- `python3 scripts/web-direct-actions-proof.py`
- `python3 scripts/web-verify-action-proof.py`
- `python3 scripts/stash-actions-proof.py`
- `python3 scripts/context-catalog-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

This closes the Web tab direct action-state gap. Verify/CVE row progress remains
covered by the existing Web verify proofs.
