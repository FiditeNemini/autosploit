# Checkpoint 62 - Creds Lifecycle State

## Summary

Added explicit lifecycle state for credential operations. Hash cracking, online
bruteforce, and secret scanning now have visible status rows instead of only
showing parsed results after completion.

## Changes

- Added `CredsLifecycleItem` and `AppState.credsLifecycle`.
- Added credential lifecycle snapshots to TestServer `/state`.
- Updated tool activity callbacks to classify cracking, bruteforce, and secret
  scan commands by tool/command text.
- Creds lifecycle status transitions now cover:
  - `running`
  - `done`
  - `failed`
  - `canceled`
- Added `CredsLifecycleStrip` to the Cracking, Online Brute, and Secrets
  subtabs.
- Extended the live-turn harness with a long-running hashcat-style `run_shell`
  proof that starts under the Creds tab and is canceled through `/stop`.

## Verification

```bash
python3 scripts/live-turn-harness.py
swift build --package-path ExploitBot
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q
```
