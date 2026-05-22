# Checkpoint 121: Tool Fanout Status Proof

## Scope

- Prove a model-issued external tool call fans out through the full app surface.
- Cover chat tool card output, activity feed status, tab activity, parsed result
  state, and dynamic context retrieval in one deterministic loop.
- Expose recent activity-feed entries through `/state` for status/proof
  surfaces instead of only exposing an activity count.

## Changes

- Added `scripts/tool-fanout-status-proof.py`.
- Added `/state.feedRecent`, a bounded snapshot of recent activity entries with
  icon, text, tool name, and duration.
- Updated the system review and flow inventory so model-tool fanout is a
  repeatable proof gate.

## Proof

Command:

```bash
python3 scripts/tool-fanout-status-proof.py
```

Result:

- The proof first failed because the fake `nmap` binary was not discovered by
  the app process.
- After using the production `which` fallback through `PATH`, the proof reached
  the intended red state: `/state` exposed only an activity count, not the
  recent activity records needed to prove visible start/complete status.
- After adding `feedRecent`, the proof passed and verified:
  - a mock model calls `nmap`;
  - `ToolExecutor` runs a fake executable through the normal subprocess path;
  - the chat tool card contains `443/tcp open https Apache httpd 2.4.49`;
  - the Recon tab activity shows `lastTool=nmap`, `status=done`, and a count;
  - `/state.feedRecent` includes `Running nmap` and completion status text;
  - `/results.ports` contains parsed `443/https` Apache service data;
  - the dynamic context catalogue retrieves the parsed service evidence.

## Boundary

This proof uses a fake executable to make external-tool execution deterministic.
It proves ExploitBot's app fanout plumbing, not the real `nmap` binary's scan
accuracy.
