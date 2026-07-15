# ExploitBot v1.5.2 — Discovery, Evidence, and Agent Loop Stability

This release focuses on making live operator sessions faster, calmer, and more
auditable.

## Highlights

- Reworked the chat header and panel geometry so status, cache, tool, and decode
  metrics remain readable across supported window sizes.
- Throttled streamed content, reasoning, telemetry, and tool previews to keep
  SwiftUI responsive during long generations and verbose command output.
- Added bounded direct-answer and post-tool finalization lanes for Qwen so
  simple no-tool questions and completed tool turns reach a clean final answer
  without reopening an unbounded reasoning loop.
- Hardened engine supervision: transient health-check failures no longer trigger
  immediate destructive restarts, while a confirmed process exit still does.
- Added intent-specific capability packs capped at eight schemas per ordinary
  model request, plus capability discovery for the full 50-tool registry.
- Added a compact context compiler and typed evidence, execution, and artifact
  stores so the model receives relevant findings instead of an ever-growing raw
  transcript.
- Added native local discovery for interfaces, routes, neighbors, Bonjour,
  Wi-Fi, and Bluetooth with permission-aware status. Discovery reports metadata
  only and does not execute pentest commands.
- Improved finding creation, report generation/export, stash organization,
  activity filtering, agent controls, and evidence provenance throughout the UI.

## Safety and scope

ExploitBot is intended for systems you own or are explicitly authorized to
test. Native discovery and capability discovery do not expand authorization;
active tools remain subject to operation scope and approval policy.
