# Checkpoint 61 - Network Lifecycle State

## Summary

Added explicit lifecycle state for long-running Network tab operations. Capture,
MITM, and tunnel actions now have status rows in the Network panel instead of
only raw output after completion.

## Changes

- Added `NetworkLifecycleItem` and `AppState.networkLifecycle`.
- Added lifecycle snapshots to TestServer `/state`.
- Updated tool activity callbacks to classify Network capture, MITM, and tunnel
  commands by tool/command text.
- Network lifecycle status transitions now cover:
  - `running`
  - `done`
  - `failed`
  - `canceled`
- Added `NetworkLifecycleStrip` to the Capture, MITM, and Tunnels subtabs.
- Extended the live-turn harness with a long-running capture-style `run_shell`
  proof that starts under the Network tab and is canceled through `/stop`.

## Verification

```bash
python3 scripts/live-turn-harness.py
swift build --package-path ExploitBot
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q
```
