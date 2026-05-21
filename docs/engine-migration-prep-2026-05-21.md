# ExploitBot vMLX Engine Migration Prep — 2026-05-21

## Source Of Truth

- ExploitBot checkout: `/Users/eric/exploitbot`
- Fresh vMLX clone for import comparison: `/tmp/exploitbot-vmlx-latest`
- vMLX upstream: `jjang-ai/vmlx`
- Fresh clone commit: `f2b42ed778ae9aedb47a5f7b269e19485e3173f2`
- ExploitBot embedded engine path: `ExploitBotEngine/vmlx_engine`

The current ExploitBot copy is a stripped engine snapshot. The current vMLX engine has newer cache, loader, reasoning, parser, native-MTP, JANG/JANGTQ, and runtime patch surfaces. The migration should copy only runtime files needed by ExploitBot's local Python engine and keep app-irrelevant surfaces out.

## Keep Out Of ExploitBot For Now

- Electron panel code
- vMLX distributed mesh code
- MCP server/client code
- Gradio apps
- image generation, reranking, embeddings endpoints
- audio/TTS/STT paths
- broad release tooling and benchmarks except focused smoke scripts

These can be reintroduced later only if the app has a concrete workflow for them.

## Import Lanes

### Lane 1: Core Server And Engine

Bring current versions of:

- `vmlx_engine/server.py`
- `vmlx_engine/cli.py`
- `vmlx_engine/request.py`
- `vmlx_engine/scheduler.py`
- `vmlx_engine/engine/`
- `vmlx_engine/engine_core.py`
- `vmlx_engine/model_config_registry.py`
- `vmlx_engine/model_configs.py`
- `vmlx_engine/model_registry.py`
- `vmlx_engine/model_runner.py`
- `vmlx_engine/output_collector.py`
- `vmlx_engine/sampling.py`
- `vmlx_engine/logprobs.py`
- `vmlx_engine/errors.py`

ExploitBot-specific launch behavior should stay in `ExploitBotEngine/launch.py`: localhost-only default, PID file, and narrow CLI surface.

### Lane 2: JANG And JANGTQ Loading

Bring current versions of:

- `vmlx_engine/loaders/`
- `vmlx_engine/models/codebook.py`
- `vmlx_engine/models/codebook_expert_loader.py`
- `vmlx_engine/models/codebook_moe_integration.py`
- `vmlx_engine/models/flash_moe_integration.py`
- `vmlx_engine/models/zaya.py`
- `vmlx_engine/models/zaya1_vl.py` only if Qwen/ZAYA VL support is explicitly kept
- `vmlx_engine/cache/codebook_cache.py`
- `vmlx_engine/cache_record_validator.py`
- `vmlx_engine/metal/`
- `vmlx_engine/runtime_patches/`
- `vmlx_engine/utils/jang_loader.py`
- `vmlx_engine/utils/quant_shape_inference.py`
- `vmlx_engine/utils/head_dim_detection.py`
- `vmlx_engine/utils/flash_moe_loader.py`
- `vmlx_engine/utils/tokenizer.py`
- `vmlx_engine/utils/chat_templates.py`
- `vmlx_engine/utils/chat_template_kwargs.py`
- `vmlx_engine/utils/multi_eos.py`

The goal is load support for JANG affine and JANGTQ/JANGTQ_K artifacts, not a generic all-vMLX feature import.

### Lane 3: Prefix, Paged, L2 Disk, And TurboQuant KV

Bring current versions of:

- `vmlx_engine/prefix_cache.py`
- `vmlx_engine/paged_cache.py`
- `vmlx_engine/memory_cache.py`
- `vmlx_engine/block_disk_store.py`
- `vmlx_engine/disk_cache.py`
- `vmlx_engine/tq_disk_store.py`
- `vmlx_engine/utils/hybrid_tq_cache.py`
- `vmlx_engine/utils/cache_types.py`
- `vmlx_engine/utils/mamba_cache.py`
- `vmlx_engine/utils/memory_limits.py`
- `vmlx_engine/utils/ssm_companion_cache.py`
- `vmlx_engine/utils/ssm_companion_disk_store.py`
- `vmlx_engine/utils/single_batch_generator.py`
- `vmlx_engine/utils/dsv4_batch_generator.py`

MiniMax is KV-only topology, so its target path is full KV cache attention with prefix cache, paged cache, block L2, and TurboQuant encode/decode at storage boundaries. Qwen3.5/Qwen3.6 hybrid SSM must require matching KV pages plus companion SSM state; KV-only hits for hybrid models must be rejected or downgraded to a shorter complete checkpoint.

### Lane 4: Reasoning And Tool Parsers

Bring current versions of:

- `vmlx_engine/reasoning/`
- `vmlx_engine/tool_parsers/`
- `vmlx_engine/api/`

Reasoning parser targets to preserve: Qwen3, DeepSeek-R1, MiniMax M2, Mistral, GPT-OSS/GLM, Gemma4, and generic think tags.

Tool parser targets to preserve: Qwen, MiniMax, DeepSeek, DSML, Hermes, Llama, Mistral, Kimi, Hunyuan, ZAYA, Nemotron, GLM, Granite, Functionary, xLAM, Step3.5, Gemma3/4, and auto routing.

Autodetection requirements:

- The selected model folder is the source of truth for parser defaults.
- Parser lookup order:
  1. `jang_config.json` capability fields, when present.
  2. `config.json` / nested `text_config` architecture and `model_type`.
  3. tokenizer/chat-template hints.
  4. family registry fallback.
  5. explicit CLI/app override wins last.
- The API must expose the effective parser choices in `/health` and `/v1/models`
  so the Swift app can show what is actually active.
- Chat completions must use the effective reasoning parser for streaming and
  non-streaming responses. Thinking/reasoning text must be separated from
  visible content when the parser supports it.
- Tool calls must use the effective tool parser for streaming and non-streaming
  responses. Parsed tool calls must be returned through the OpenAI-compatible
  `tool_calls` API shape and must not be left as raw model text when a parser
  successfully extracts them.

### Lane 4B: Generation Config Loading And Application

Bring or preserve support for reading generation defaults from the selected
model folder:

- `generation_config.json`
- tokenizer-level chat-template defaults where applicable
- `jang_config.json` generation/capability fields where present
- model config defaults from `model_config_registry.py`

Application requirements:

- Load generation config during model startup, not lazily after the first
  request.
- Merge order:
  1. engine hard safety defaults
  2. model family defaults
  3. model-folder `generation_config.json`
  4. JANG capability defaults
  5. app/server CLI defaults
  6. per-request API fields
- Apply effective values to actual sampling/generation, including
  `temperature`, `top_p`, `top_k`, `min_p`, `repetition_penalty`, stop/eos
  tokens, max token defaults, and thinking/template kwargs when supported.
- Preserve per-request override behavior. A request that explicitly sets
  `temperature` or `max_tokens` must override folder defaults for that request
  only.
- Include the effective generation config, or at least a stable summary, in
  `/health` and `/v1/models` for debugging.
- Add a smoke test using a temporary model folder with `generation_config.json`
  to prove defaults are picked up and request overrides win.

### Lane 5: Native MTP Boundary

Bring only if needed for Qwen MTP proof:

- `vmlx_engine/native_mtp.py`
- `vmlx_engine/native_mtp_policy_suite.py`
- `vmlx_engine/patches/mlx_lm_mtp/`
- `vmlx_engine/patches/mlx_vlm_mtp/`

Do not enable MTP from metadata alone. Runtime activation must require config support, tensor evidence, loader support, and a real generation smoke.

## Correctness Gates

1. `python3 -m compileall -q ExploitBotEngine`
2. Import smoke: `PYTHONPATH=ExploitBotEngine python3 -c 'from vmlx_engine.server import app; print(len(app.routes))'`
3. CLI smoke: `python3 ExploitBotEngine/launch.py --help`
4. Server no-model health smoke if supported by the imported server.
5. MiniMax JANGTQ real generation smoke with:
   - prefix cache enabled
   - paged cache enabled
   - block L2 enabled
   - TurboQuant KV active
   - usage reporting cached tokens and cache detail
6. Qwen hybrid SSM smoke with:
   - first prompt cold
   - second prompt prefix hit only if SSM companion state exists
   - missing companion state rejected as KV-only unsafe
   - idle rederive queue counters visible
7. Tool-call smoke against a harmless local tool schema.
8. Reasoning parser smoke with thinking content separated from visible content.
9. Parser autodetect smoke for at least MiniMax and Qwen-family folders:
   `/health` reports the effective reasoning and tool parsers, and chat
   responses use them.
10. Generation config smoke with a temp model folder:
   folder defaults are loaded at startup, used by a request that omits those
   fields, and overridden by a request that supplies explicit values.

## Implemented Checkpoints

- Checkpoint 01: UI theme preview/assets and initial Graphite Ops app theme.
- Checkpoint 02: MiniMax M2 and Gemma4 reasoning parsers imported/registered
  from current vMLX, with MiniMax config autodetect using `minimax_m2`.
- Checkpoint 03: `effective_config` API metadata added to `/health` and
  `/v1/models`, covering selected parsers, generation defaults, prefix/paged
  cache settings, KV cache quantization, and prompt/block L2 disk cache config.
- Checkpoint 04: Swift `EngineManager` parses `/health.effective_config`, and
  Settings displays the live selected parser/generation/cache summary.
- Checkpoint 05: Prompt L2 disk cache stub replaced with current vMLX
  `DiskCacheManager`, TQ-native disk serializer, and cache-record validator.
- Checkpoint 06: Prompt L2 and block L2 disk cache flags wired through Swift
  settings, `launch.py`, `server.py`, and `SchedulerConfig`.
- Checkpoint 07: Standalone hybrid SSM companion cache, SSM L2 disk store, and
  Qwen hybrid TurboQuant helper imported from current vMLX; LLM scheduler now
  reports SSM companion stats and rejects KV-only hybrid restores without a
  complete companion entry.
- Checkpoint 08: SSM companion config is included in `/health.effective_config`,
  richer SSM stats are exposed through `/v1/cache/stats`, and Settings displays
  SSM runtime status.
- Checkpoint 09: Multi-agent monitor task moved onto `MainActor`, removing the
  Swift 6 sendability warnings from `swift build`.
- Checkpoint 10: Added repeatable bundled-Python no-model API smoke covering
  `/health.effective_config`, `/v1/cache/stats`, and `/v1/models`; real
  MiniMax/Qwen cache proof remains gated on clearing the existing heavy vMLX
  process or otherwise reserving memory for a safe run.
- Checkpoint 11: Tightened the Graphite Ops visual pass by removing explicit
  white foreground usage, replacing white onboarding selection indicators with
  accent-blue state, reducing visible rounded surfaces to the 8px theme radius,
  locking window resizing to content minimum size, and matching the chat drag
  handle minimum to the chat panel frame.
- Checkpoint 12: Launch-time parser autodetection now uses model-folder
  `config.json` / `text_config.model_type` through the model config registry
  after JANG capability fields, the registry has a direct JSON fallback when
  `mlx_lm` is unavailable, and tests prove configured tool parsers produce
  OpenAI-compatible `tool_calls`.
- Checkpoint 13: Model-folder generation defaults now cover `top_k`, `min_p`,
  `repetition_penalty`, and stop sequences in addition to temperature/top-p/max
  tokens, flow through launch/server flags, appear in effective runtime
  metadata, apply across API paths, and preserve per-request override priority.
- Checkpoint 14: Swift now preserves model-folder generation defaults by
  default instead of always overriding them from app settings, propagates that
  policy to chat requests and multi-agent chats, displays broader effective
  sampling metadata, and expands selectable-text/minimum-size coverage across
  onboarding, settings, sheets, and modal panels.
- Checkpoint 15: App-level `top_p` override wiring is now complete when model
  defaults are disabled: Settings exposes it, active and multi-agent chats carry
  it, and request bodies send `top_p` with temperature/max-token overrides.
- Checkpoint 16: Captured a current-build Settings visual proof showing the
  polished dark theme, model-default toggle, and disabled temperature/top-p/max
  token app overrides while model defaults are enabled.
- Checkpoint 17: Replaced bright native Settings/Onboarding switches and
  Settings sliders with dark custom controls, and converted Settings primary
  actions from filled blue blocks to darker stroked buttons.
- Checkpoint 18: Tightened Settings row layout for the app minimum size by
  giving labels a stable selectable column and controls a protected content
  width so rows scroll instead of squishing.
- Checkpoint 19: Hardened lower Settings subpanels by darkening CVE/model/tool
  action buttons, enabling more selectable text, allowing CVE/model text to
  wrap, and protecting the tool table with horizontal scrolling.
- Checkpoint 20: Added no-model regression coverage for nested
  `text_config.model_type` autodetection so Qwen wrapper models can still
  resolve parser defaults and inner SSM/Mamba cache-family metadata.
- Checkpoint 21: Extended effective runtime metadata with chat-template
  generation settings, proved `/health` and `/v1/models` expose the same
  parser/generation/cache contract under the bundled runtime, and updated the
  no-model API smoke to require those generation metadata keys.
- Checkpoint 22: Updated `/v1/cache/stats` TurboQuant detection for the current
  JANG and hybrid make-cache wrappers, exposing hybrid attention and companion
  layer metadata for future Qwen SSM cache debugging.
- Checkpoint 23: Added regression coverage proving non-streaming and streaming
  chat payloads expose separated reasoning through public `reasoning_content`
  while keeping the internal `reasoning` field out of serialized API output.
- Checkpoint 24: Replaced remaining native Settings picker/radio controls for
  model profile, parser selection, KV cache mode, and max agent count with a
  dark selectable/copyable option grid that matches the squared Graphite Ops
  theme and protects minimum layout width.
- Checkpoint 25: Updated Swift effective-config parsing and the Settings
  runtime summary so chat-template kwargs and custom-template state exposed by
  the engine are visible in the app.
- Checkpoint 26: Added Swift polling/parsing for `/v1/cache/stats` and a
  selectable Settings `Cache Runtime` panel covering TurboQuant, prompt/block
  L2, SSM companion, and memory diagnostics.
- Checkpoint 27: Replaced the main Activity Feed verbosity picker with a dark
  segmented selector and captured visual proof of the main app surface without
  that native popup control.
- Checkpoint 28: Replaced the finding creation wizard's vulnerability type,
  severity, and status native pickers with dark selectable controls, removed
  emoji-styled modal chrome, and squared the modal action backgrounds while
  preserving the existing stored finding values.
- Checkpoint 29: Replaced native picker controls in the network, report,
  post-exploitation, and credentials tabs with dark segmented controls while
  preserving the command/report values that those selectors feed.
- Checkpoint 30: Replaced the chat deploy-agent type menu and custom CVE
  severity picker with dark selectable controls, clearing the current native
  `Picker` scan under the SwiftUI `Views` tree.
- Checkpoint 31: Removed emoji-heavy action labels and empty-state marks across
  the main SwiftUI views, replacing them with plain text or SF Symbols while
  preserving command/action behavior.
- Checkpoint 32: Fixed the Python engine dependency contract by declaring
  `python-multipart`, added a `dev` test extra, locked engine dependencies with
  `uv.lock`, and proved the current engine suite with `22 passed`.
- Checkpoint 33: Added registry-derived model family/cache-type metadata to
  `/health` and `/v1/models`, parsed it in Swift, and displayed the effective
  family/topology in Settings so MiniMax KV and Qwen hybrid/Mamba cache paths
  are auditable without name guessing.
- Checkpoint 34: Removed the remaining emoji/text-symbol chrome emitted from
  service/model computed labels, tool statuses, activity feed exports, stash
  rows, phase logs, and localized onboarding navigation text.
- Checkpoint 35: Replaced tab toolbar text-glyph buttons with SF Symbols and
  stable icon-button sizing.
- Checkpoint 36: Added explicit cache topology metadata to effective runtime
  config, marking MiniMax as full-KV attention and Qwen3-next as hybrid
  SSM/attention with SSM companion requirements, and surfaced the topology in
  Settings.
- Checkpoint 37: Added Qwen hybrid-SSM and MiniMax full-KV topology warning
  regressions, surfaced cache topology warnings as a selectable Settings row,
  and made runtime config cells directly copyable.
- Checkpoint 38: Replaced remaining chat-panel emoji/text-glyph controls with
  SF Symbols and stable square icon buttons, including reasoning, clear,
  send/stop, agent status, deploy-add, and tool-output expand/collapse.
- Checkpoint 39: Added a repeatable SwiftPM app-bundle run script plus Codex
  Run action, then visually verified a darker, squared onboarding language
  screen without flag emoji or bright filled controls.
- Checkpoint 40: Replaced main-surface sidebar glyph controls and bright Recon
  toolbar actions with SF Symbol/dark bordered controls, then visually verified
  the main app window after restoring the temporary QA database state.
- Checkpoint 41: Added parser/generation provenance from launch defaults into
  `effective_config.sources`, covered model-folder versus CLI source reporting
  in tests, and surfaced selectable Sampling/Parser source rows in Settings.
- Checkpoint 42: Made TurboQuant KV modes first-class by accepting
  `turboquant-q4/q8` and `tq-q4/q8` through launcher/server/CLI paths,
  normalizing scheduler bit mapping, and adding TurboQuant Q4/Q8 Settings
  options.
- Checkpoint 43: Aligned Block L2 defaults with paged cache by enabling paged
  cache in the Python launcher's default path, keeping the Swift Settings
  default in sync, and adding a regression test for the default paged + Block
  L2 topology.
- Checkpoint 44: Aligned the direct server entrypoint with the same default
  cache topology by enabling prompt L2, paged cache, and Block L2 defaults in
  `vmlx_engine.server`, then extracting and testing scheduler config creation.
- Checkpoint 45: Extended model-folder generation defaults to include
  `enable_thinking` and `chat_template_kwargs`, passed those through the
  launcher/server path, and covered the behavior with launcher and server
  regressions.
- Checkpoint 46: Darkened remaining bright filled action controls, added darker
  sheet presentation backgrounds/minimum sizing for key sheets, removed the CVE
  sync emoji label, and visually checked onboarding, main, and Settings.
- Checkpoint 47: Centralized nested resize bounds for the chat and
  activity/terminal panels, raised their minimums, and updated drag handlers to
  render through clamped dimensions.
- Checkpoint 48: Added a shared dark semantic action button and replaced the
  remaining saturated filled actions in Network, Creds, Exploit, Post, and
  Report tabs with dark outlined controls.
- Checkpoint 49: Replaced the remaining SwiftUI alert confirmations with
  reusable dark in-app confirmation overlays for clear-chat and delete-op flows.
- Checkpoint 50: Removed the app's small/medium/large model-profile path from
  Settings, Onboarding, ChatService, AgentManager, AppState, and the local model
  selector. Users now select a model folder only; Swift inspects the folder for
  Qwen/MiniMax support and config files, warns that only Qwen and MiniMax are
  supported in the beta lane, and forces runtime autodetect for generation,
  reasoning parser, tool parser, TurboQuant KV cache, prefix cache, prompt L2,
  paged cache, and block L2 defaults. Added the app-flow inventory covering tab
  wiring, chat/session/context paths, dynamic catalogue requirements, visual
  tool-status requirements, and proof gates.
- Checkpoint 51: Added a Swift-side dynamic context catalogue for the app flow.
  Chat turns now ask `ContextCatalogService` for a prompt-aware packet that ranks
  assets, findings, recent tool output, stash entries, and CVE results before
  injection, instead of using a fixed ResultsStore summary. Settings gained a
  Context Catalog section controlling dynamic context, max snippets, source
  inclusion, and CVE assist mode (`off`, current results, or semantic embedding
  search with fallback). The settings persist locally and are wired to main chat
  plus newly deployed agents.
- Checkpoint 52: Added a whole-app system review matrix covering runtime/chat,
  context, tool loop, every tab's button wiring, and the proof matrix required
  for final agentic behavior. Tightened chat scroll behavior with an explicit
  lock/unlock control: locked mode follows streamed output, user dragging pauses
  auto-scroll, and the "Latest/New output" control relocks to the newest message.
- Checkpoint 53: Added `scripts/live-turn-harness.py`, a proof-driven mock model
  harness for app-level live turns. It launches a deterministic OpenAI-compatible
  streaming mock engine, connects the running app through QA server endpoints,
  seeds context, verifies outbound dynamic-context/tool-schema payloads, consumes
  streamed reasoning/content/usage metrics, and proves `search_cve` tool-call
  behavior across autopilot, manual, and copilot approval modes.

## Known Risk Areas

- ExploitBot currently has a custom stripped server contract. Replacing `server.py` wholesale may expose endpoints the app does not need.
- vMLX cache code has schema and runtime fingerprinting. Cache schema mismatches must invalidate old L2 entries rather than replaying them.
- Qwen hybrid SSM cache restore is correctness-sensitive. Do not trim recurrent state by slicing KV arrays.
- MiniMax public MTP is not available from released weights; do not represent MiniMax MTP as supported unless tensor evidence exists.
- JANGTQ2 can be quality-limited on some families. The app UI should label it as a memory tier rather than default premium tier.

## Next Implementation Shape

Do this in small commits:

1. Copy/import core support modules and make imports compile.
2. Restore ExploitBot launch/server contract.
3. Wire JANG/JANGTQ loaders.
4. Wire cache stack and health fields.
5. Wire parsers and API streaming.
6. Run real MiniMax JANGTQ and Qwen hybrid cache proofs.
7. Only then revise Swift UI around the chosen theme.
