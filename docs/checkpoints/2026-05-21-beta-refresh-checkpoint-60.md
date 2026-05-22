# Checkpoint 60 - Web Verify Action

## Summary

Converted the Web vulnerability card `Verify` control from a placeholder into a
real chat action.

## Changes

- Added `onVerify` to `VulnCard`.
- Wired the Web tab's `Verify` button to send a focused verification prompt to
  the chat/tool loop.
- The prompt includes target, finding title, source, CVE, and description so the
  agent can run minimal safe probes and gather evidence without guessing.
- Updated the system review matrix to remove the Verify placeholder gap.

## Verification

```bash
swift build --package-path ExploitBot
```
