# Test Scripts

This directory contains test scripts for kernel-graphrag-sentinel.

## test_cache_hit.sh

Test LLM prompt caching by running 3 sequential impact analyses.

### Usage

```bash
./scripts/test_cache_hit.sh [PROVIDER] [MODEL]
```

### Arguments

- **PROVIDER** - LLM provider (default: `anthropic`)
  - Options: `anthropic`, `openai`, `gemini`, `lmstudio`, `ollama`
- **MODEL** - Model name (default: `claude-sonnet-4-5`)

### Examples

```bash
# Use defaults (Anthropic Claude Sonnet 4.5)
./scripts/test_cache_hit.sh

# Anthropic Claude Haiku 4.5
./scripts/test_cache_hit.sh anthropic claude-haiku-4-5

# OpenAI GPT-4o
./scripts/test_cache_hit.sh openai gpt-4o

# Google Gemini 2.0 Flash
./scripts/test_cache_hit.sh gemini gemini-2.0-flash-exp

# LM Studio with Mistral
./scripts/test_cache_hit.sh lmstudio mistralai/devstral-small-2-2512

# Ollama with Llama
./scripts/test_cache_hit.sh ollama llama3.2
```

### What It Tests

The script runs 3 impact analyses back-to-back:
1. `ext4_file_mmap` - ext4 filesystem
2. `btrfs_file_llseek` - btrfs filesystem  
3. `ext4_file_write_iter` - ext4 filesystem

### Expected Results (Anthropic Only)

**Anthropic Claude** supports native prompt caching:

```
Test 1: Cache MISS - Created cache: 2158 tokens
Test 2: Cache HIT  - Read 2158 tokens (85% cache hit rate)
Test 3: Cache HIT  - Read 2158 tokens (85% cache hit rate)
```

**Other providers** (OpenAI, Gemini, local models) do not show cache logs but will:
- Generate complete reports successfully
- Reuse the same system prompt internally (if supported)
- Complete faster on subsequent requests (varies by provider)

### Cache Behavior

#### Anthropic
- **Cache TTL:** 5 minutes
- **Minimum cacheable size:** 1,024 tokens
- **Cache block size:** 128 tokens (rounded up)
- **System prompt size:** ~2,158 tokens (cached)
- **Cost savings:** ~90% discount on cached tokens

#### Other Providers
- **OpenAI:** No native caching (as of 2025)
- **Gemini:** No native caching (as of 2025)
- **Local (LM Studio, Ollama):** No caching metrics

### Verifying Cache Hits

Look for these log messages:

```
INFO - Cache MISS - Created cache: 2158 tokens
INFO - Cache HIT - Read 2158 tokens (85.2% cache hit rate)
```

If you see **Cache MISS** on all 3 tests, the cache likely expired between requests (5-minute TTL).

### Reports Generated

Reports are saved to:
- `./docs/examples/reports/cache-test-1.md`
- `./docs/examples/reports/cache-test-2.md`
- `./docs/examples/reports/cache-test-3.md`

### Troubleshooting

**All Cache MISS:**
- Tests took > 5 minutes (cache expired)
- Run tests faster or reduce analysis complexity

**No cache logs:**
- You're using a non-Anthropic provider (expected)
- Check provider-specific documentation for caching support

**Script fails:**
- Ensure API keys are set (`ANTHROPIC_API_KEY`, etc.)
- Verify functions exist in database
- Check Neo4j connection

### Related Documentation

- [docs/TOKEN_LIMITS.md](../docs/TOKEN_LIMITS.md) - Token limits and cost analysis
- [docs/llm_report_system_prompt.md](../docs/llm_report_system_prompt.md) - KV-cache optimized prompts
- [test_anthropic_cache.py](../test_anthropic_cache.py) - Standalone cache test

---

## Other Scripts

More test scripts coming soon!
