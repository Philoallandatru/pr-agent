#!/bin/bash
# Start Polling Service with Tokenizer Pre-download
#
# This script ensures modelscope tokenizers are downloaded before starting
# the polling service to avoid lock contention issues.

set -e

# Configuration
CACHE_DIR="${TOKENIZER_CACHE_DIR:-/data/tokenizers}"
MODELSCOPE_MODEL_ID="${MODELSCOPE_MODEL_ID:-Qwen/Qwen3.6-35B-A3B-FP8}"

echo "=================================================="
echo "PR-Agent Polling Service Startup"
echo "=================================================="
echo "Cache directory: $CACHE_DIR"
echo "ModelScope model: $MODELSCOPE_MODEL_ID"
echo ""

# Check if tokenizer is already cached
echo "Checking tokenizer cache..."
if python -m pr_agent.algo.tokenizer_manager info --cache-dir "$CACHE_DIR" 2>/dev/null | grep -q "modelscope:$MODELSCOPE_MODEL_ID"; then
    echo "✓ Tokenizer already cached"
else
    echo "Tokenizer not found in cache, downloading..."
    python -m pr_agent.algo.tokenizer_manager download \
        --modelscope-model-id "$MODELSCOPE_MODEL_ID" \
        --cache-dir "$CACHE_DIR"

    if [ $? -eq 0 ]; then
        echo "✓ Tokenizer downloaded successfully"
    else
        echo "✗ Failed to download tokenizer"
        exit 1
    fi
fi

echo ""
echo "Tokenizer cache info:"
python -m pr_agent.algo.tokenizer_manager info --cache-dir "$CACHE_DIR"

echo ""
echo "=================================================="
echo "Starting Polling Service..."
echo "=================================================="

# Start the polling service
# Adjust the command below based on your deployment method
exec python -m pr_agent.servers.bitbucket_server_polling
