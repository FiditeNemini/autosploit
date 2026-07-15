# ExploitBot v1.5.3 — Bounded Reasoning and Responsive Live Streaming

This hotfix addresses a main-thread freeze found during the final v1.5.2 demo
drive.

## Fixes

- Treats explicit one-tool requests followed by summary, answer, reply, or
  report language as bounded turns, freezes the request to the one named tool,
  and disables unnecessary Qwen reasoning for the deterministic call and final.
- Publishes accumulated reasoning and answer text to SwiftUI at a fixed 10 Hz
  cadence, with an explicit main-actor yield after each visible update. Every
  SSE delta remains accumulated immediately and the final tail is preserved.
- Renders bounded live and completed previews for long reasoning and assistant
  responses. The full transcript remains available to Copy and Stash without
  repeatedly laying out the entire growing string.
- Keeps the full capability inventory in its visible tool card while sending
  only the grounded callback outcome to the bounded final request, preventing
  raw inventory copying and unwanted count narration.
- Uses Apple's non-accelerated notary upload path to avoid the transient S3
  acceleration failure observed during the previous release.

## Safety and scope

ExploitBot is intended for systems you own or are explicitly authorized to
test. This release does not broaden tool scope or bypass approval policy.
