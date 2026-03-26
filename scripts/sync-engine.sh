#!/bin/bash
# ExploitBot Engine Sync Script
# Syncs vMLX engine updates from production while preserving exploitbot-specific additions.
#
# Usage: ./scripts/sync-engine.sh [/path/to/vmlx]
# Default: ~/mlx/vllm-mlx

set -e

PROD="${1:-$HOME/mlx/vllm-mlx}/vmlx_engine"
EB="$(dirname "$0")/../ExploitBotEngine/vmlx_engine"

if [ ! -d "$PROD" ]; then
  echo "ERROR: Production vMLX not found at $PROD"
  exit 1
fi

echo "=== ExploitBot Engine Sync ==="
echo "FROM: $PROD"
echo "TO:   $EB"
echo ""

# Step 1: Safe copies (no exploitbot-specific content to preserve)
echo "--- Step 1: Safe file copies ---"
SAFE_FILES="cli.py utils/jang_loader.py utils/cache_types.py utils/mamba_cache.py utils/chat_templates.py utils/tokenizer.py"
for f in $SAFE_FILES; do
  if [ -f "$PROD/$f" ]; then
    cp "$PROD/$f" "$EB/$f"
    echo "  ✓ $f"
  fi
done

# Step 2: server.py — merge production changes but keep exploitbot cache flags
echo ""
echo "--- Step 2: server.py (merge with exploitbot additions) ---"

# Save exploitbot-specific blocks
CACHE_BLOCK='    # Cache settings (exploitbot)
    parser.add_argument("--enable-prefix-cache", type=str, default="true", choices=["true", "false"])
    parser.add_argument("--cache-memory-percent", type=float, default=0.30)
    parser.add_argument("--use-paged-cache", type=str, default="false", choices=["true", "false"])
    parser.add_argument("--paged-cache-block-size", type=int, default=64)
    parser.add_argument("--kv-cache-quantization", type=str, default="none", choices=["none", "q4", "q8"])
    parser.add_argument("--kv-cache-group-size", type=int, default=64)'

SCHED_BLOCK='    # Build scheduler config from cache CLI flags
    from .scheduler import SchedulerConfig
    sched_config = SchedulerConfig(
        enable_prefix_cache=(args.enable_prefix_cache == "true"),
        cache_memory_percent=args.cache_memory_percent,
        use_paged_cache=(args.use_paged_cache == "true"),
        paged_cache_block_size=args.paged_cache_block_size,
        kv_cache_quantization=args.kv_cache_quantization,
        kv_cache_group_size=args.kv_cache_group_size,
    )'

# Copy production server.py
cp "$PROD/server.py" "$EB/server.py"

# Insert cache CLI args before "args = parser.parse_args()"
python3 -c "
content = open('$EB/server.py').read()
cache_block = '''$CACHE_BLOCK'''
content = content.replace(
    '    args = parser.parse_args()',
    cache_block + '\n\n    args = parser.parse_args()'
)
open('$EB/server.py', 'w').write(content)
print('  ✓ server.py: cache CLI args inserted')
"

# Insert SchedulerConfig before load_model
python3 -c "
content = open('$EB/server.py').read()
sched_block = '''$SCHED_BLOCK'''
# Find load_model call and add scheduler_config
old = '''    # Load model before starting server
    load_model(
        args.model,
        use_batching=args.continuous_batching,
        max_tokens=args.max_tokens,
        force_mllm=args.mllm,
        served_model_name=args.served_model_name,
    )'''
new = sched_block + '''

    # Load model before starting server
    load_model(
        args.model,
        use_batching=args.continuous_batching,
        scheduler_config=sched_config,
        max_tokens=args.max_tokens,
        force_mllm=args.mllm,
        served_model_name=args.served_model_name,
    )'''
if old in content:
    content = content.replace(old, new)
    open('$EB/server.py', 'w').write(content)
    print('  ✓ server.py: SchedulerConfig block inserted')
else:
    print('  ⚠ server.py: load_model pattern not found — manual merge needed')
"

# Step 3: Skip files that exploitbot doesn't need
echo ""
echo "--- Step 3: Skipped (not needed) ---"
echo "  - audio/, mcp/, commands/ (not used)"
echo "  - embedding.py, image_gen.py, gradio_*.py, speculative.py (not used)"
echo "  - mllm_cache.py, multimodal_processor.py (VLM-only)"

# Step 4: Verify
echo ""
echo "--- Step 4: Verification ---"
grep -q "kv-cache-quantization" "$EB/server.py" && echo "  ✓ Cache CLI args present" || echo "  ✗ Cache CLI args MISSING"
grep -q "scheduler_config=sched_config" "$EB/server.py" && echo "  ✓ SchedulerConfig passed to load_model" || echo "  ✗ SchedulerConfig MISSING"

python3 -c "
import sys
sys.path.insert(0, '$(dirname $EB)')
from vmlx_engine.scheduler import SchedulerConfig
print('  ✓ Scheduler imports OK')
" 2>/dev/null || echo "  ✗ Scheduler import FAILED"

python3 -c "
import sys
sys.path.insert(0, '$(dirname $EB)')
from vmlx_engine.server import app
print('  ✓ Server imports OK')
" 2>/dev/null || echo "  ✗ Server import FAILED"

echo ""
echo "=== Sync complete ==="
