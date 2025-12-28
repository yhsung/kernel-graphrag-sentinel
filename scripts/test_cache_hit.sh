#!/bin/bash
# test_cache_hit.sh - Test LLM prompt caching with 3 sequential requests
#
# This script demonstrates KV-cache optimization by running 3 impact analyses
# back-to-back within the cache TTL window (5 minutes for Anthropic).
#
# Expected results (for Anthropic):
#   Test 1: Cache MISS - Creates cache (~2,158 tokens)
#   Test 2: Cache HIT  - Reads cache (~85% hit rate)
#   Test 3: Cache HIT  - Reads cache (~85% hit rate)
#
# Usage:
#   ./scripts/test_cache_hit.sh [PROVIDER] [MODEL]
#
# Examples:
#   ./scripts/test_cache_hit.sh anthropic claude-sonnet-4-5
#   ./scripts/test_cache_hit.sh openai gpt-4o
#   ./scripts/test_cache_hit.sh gemini gemini-2.0-flash-exp
#   ./scripts/test_cache_hit.sh lmstudio mistralai/devstral-small-2-2512
#
# Defaults: anthropic claude-sonnet-4-5

set -e  # Exit on error

cd /workspaces/ubuntu/kernel-graphrag-sentinel

# Show help if requested
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [PROVIDER] [MODEL]"
    echo ""
    echo "Test LLM prompt caching by running 3 sequential impact analyses."
    echo ""
    echo "Arguments:"
    echo "  PROVIDER  LLM provider (default: anthropic)"
    echo "            Options: anthropic, openai, gemini, lmstudio, ollama"
    echo "  MODEL     Model name (default: claude-sonnet-4-5)"
    echo ""
    echo "Examples:"
    echo "  $0                                          # Use defaults (anthropic, claude-sonnet-4-5)"
    echo "  $0 anthropic claude-sonnet-4-5              # Anthropic Claude Sonnet 4.5"
    echo "  $0 anthropic claude-haiku-4-5               # Anthropic Claude Haiku 4.5"
    echo "  $0 openai gpt-4o                            # OpenAI GPT-4o"
    echo "  $0 gemini gemini-2.0-flash-exp              # Google Gemini 2.0 Flash"
    echo "  $0 lmstudio mistralai/devstral-small-2-2512 # LM Studio with Mistral"
    echo "  $0 ollama llama3.2                          # Ollama with Llama 3.2"
    echo ""
    echo "Note: Only Anthropic supports native prompt caching with cache metrics."
    echo "      Other providers will generate reports without cache logging."
    exit 0
fi

# Parse command-line arguments
LLM_PROVIDER=${1:-anthropic}
LLM_MODEL=${2:-claude-sonnet-4-5}

# Set environment variables
export LLM_PROVIDER
export ANTHROPIC_MODEL="${LLM_MODEL}"
export OPENAI_MODEL="${LLM_MODEL}"
export GEMINI_MODEL="${LLM_MODEL}"
export LLM_MODEL

echo "========================================================================"
echo "LLM Prompt Cache Test - 3 Sequential Requests"
echo "========================================================================"
echo ""
echo "Configuration:"
echo "  Provider: ${LLM_PROVIDER}"
echo "  Model:    ${LLM_MODEL}"
echo ""
echo "Testing KV-cache optimization"
echo "  - Anthropic: 5-minute cache TTL"
echo "  - Other providers: May not support caching (will show no cache logs)"
echo ""
echo "Functions to analyze:"
echo "  1. ext4_file_mmap       (ext4 filesystem)"
echo "  2. btrfs_file_llseek    (btrfs filesystem)"
echo "  3. ext4_file_write_iter (ext4 filesystem)"
echo ""
echo "Press Ctrl+C to cancel, or wait 3 seconds to continue..."
sleep 3
echo ""

START_TIME=$(date +%s)

echo "========================================================================"
echo "Test 1: First request (Cache MISS expected)"
echo "========================================================================"
echo "Function: ext4_file_mmap"
echo "Started: $(date '+%H:%M:%S')"
echo ""

python3 src/main.py analyze ext4_file_mmap --llm \
  --output ./docs/examples/reports/cache-test-1.md 2>&1 | \
  grep -E "(Cache MISS|Cache HIT|Generated LLM report|INFO - Initialized)"

TEST1_TIME=$(date +%s)
ELAPSED1=$((TEST1_TIME - START_TIME))
echo "Completed: $(date '+%H:%M:%S') (took ${ELAPSED1}s)"
echo ""

echo "========================================================================"
echo "Test 2: Second request within 5 min (Cache HIT expected)"
echo "========================================================================"
echo "Function: btrfs_file_llseek"
echo "Started: $(date '+%H:%M:%S')"
echo ""

python3 src/main.py analyze btrfs_file_llseek --llm \
  --output ./docs/examples/reports/cache-test-2.md 2>&1 | \
  grep -E "(Cache MISS|Cache HIT|Generated LLM report|INFO - Initialized)"

TEST2_TIME=$(date +%s)
ELAPSED2=$((TEST2_TIME - TEST1_TIME))
TOTAL2=$((TEST2_TIME - START_TIME))
echo "Completed: $(date '+%H:%M:%S') (took ${ELAPSED2}s, total ${TOTAL2}s)"
echo ""

echo "========================================================================"
echo "Test 3: Third request (Cache HIT expected)"
echo "========================================================================"
echo "Function: ext4_file_write_iter"
echo "Started: $(date '+%H:%M:%S')"
echo ""

python3 src/main.py analyze ext4_file_write_iter --llm \
  --output ./docs/examples/reports/cache-test-3.md 2>&1 | \
  grep -E "(Cache MISS|Cache HIT|Generated LLM report|INFO - Initialized)"

TEST3_TIME=$(date +%s)
ELAPSED3=$((TEST3_TIME - TEST2_TIME))
TOTAL3=$((TEST3_TIME - START_TIME))
echo "Completed: $(date '+%H:%M:%S') (took ${ELAPSED3}s, total ${TOTAL3}s)"
echo ""

END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

echo "========================================================================"
echo "Test Summary"
echo "========================================================================"
echo ""
echo "Provider: ${LLM_PROVIDER}"
echo "Model:    ${LLM_MODEL}"
echo "Total time: ${TOTAL_TIME} seconds"
echo ""

# Provider-specific cache expectations
if [ "${LLM_PROVIDER}" = "anthropic" ]; then
    echo "Cache Status (Anthropic):"
    echo "  - Test 1: Should show 'Cache MISS - Created cache: 2158 tokens'"
    echo "  - Test 2: Should show 'Cache HIT - Read 2158 tokens (XX% cache hit rate)'"
    echo "  - Test 3: Should show 'Cache HIT - Read 2158 tokens (XX% cache hit rate)'"
    echo ""

    if [ $TOTAL_TIME -lt 300 ]; then
        echo "✅ All tests completed within 5-minute cache window (${TOTAL_TIME}s < 300s)"
    else
        echo "⚠️  Warning: Tests took longer than 5 minutes (${TOTAL_TIME}s > 300s)"
        echo "   Cache may have expired between requests!"
    fi
else
    echo "Cache Status (${LLM_PROVIDER}):"
    echo "  - ${LLM_PROVIDER} may not support native prompt caching"
    echo "  - No cache logs expected for non-Anthropic providers"
    echo "  - Reports generated successfully"
    echo ""
    echo "✅ All tests completed in ${TOTAL_TIME} seconds"
fi

echo ""
echo "Reports generated:"
echo "  - ./docs/examples/reports/cache-test-1.md"
echo "  - ./docs/examples/reports/cache-test-2.md"
echo "  - ./docs/examples/reports/cache-test-3.md"
echo ""
echo "To verify cache hits, check the logs above for 'Cache HIT' messages."
echo ""
echo "✅ Cache test completed!"