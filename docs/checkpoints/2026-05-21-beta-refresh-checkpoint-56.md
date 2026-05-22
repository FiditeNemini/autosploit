# Checkpoint 56 - Per-Tab Tool Activity State

## Summary

Added a compact per-tab activity model so tool usage has a visible UI surface
outside chat cards and the activity feed. The tab bar can now show whether a
tab's last tool is running, done, failed, or canceled.

## Changes

- Added `ToolTabActivity` and `AppState.tabActivities`.
- Wired `ChatService.onToolStart`, `onToolComplete`, and `onToolCancel` into
  tab activity updates.
- Added `tabActivities` to TestServer `/state`.
- Updated `TabBarView` to draw a compact status indicator and tooltip for tabs
  with activity.
- Extended the live-turn harness with a Web/CVE status proof using a mock
  model-issued `search_cve` tool call.
- Fixed a Web tab render-side effect: `lookupCVEDetails(for:)` no longer calls
  `cveService.search(...)` from inside view rendering.

## Verification

```bash
python3 scripts/live-turn-harness.py
```

## Remaining Work

- Add screenshot coverage for tab-bar activity indicators.
- Add model-callable catalogue search.
- Add real Qwen and MiniMax model-folder live-turn scripts.
