# LLM Provider Configuration Guide

## Table of Contents
- [Overview](#overview)
- [Supported Providers](#supported-providers)
- [Quick Start](#quick-start)
- [Provider Comparison](#provider-comparison)
- [Configuration Methods](#configuration-methods)
- [Rate Limits & Costs](#rate-limits--costs)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

Kernel-GraphRAG Sentinel supports multiple LLM providers for generating AI-powered impact analysis reports. Choose the provider that best fits your needs based on cost, speed, quality, and rate limits.

**Supported providers:**
- **Anthropic** (Claude) - Recommended for production
- **OpenAI** (GPT models) - Good alternative with reasoning models
- **Google Gemini** - Fast and free tier available
- **Ollama** - Local models, unlimited usage, no API costs
- **LM Studio** - Local models with OpenAI-compatible API, GUI-based

---

## Supported Providers

### 1. Anthropic Claude (Recommended)

**Models:**
- `claude-sonnet-3-5` - Best quality, highest cost
- `claude-haiku-4-5` - Fast, cost-effective (recommended)
- `claude-opus-3-5` - Highest intelligence

**Pros:**
- Excellent report quality (200+ line reports)
- Fast response times (~15-20 seconds)
- Generous free tier (1,000 requests/day)
- Best structured output with tables and checklists

**Cons:**
- Requires API key
- Rate limits on free tier (50 requests/minute)

**Best for:** Production use, formal documentation, team reviews

---

### 2. OpenAI

**Models:**
- `gpt-4o` - Latest multimodal model
- `gpt-4-turbo` - Fast GPT-4
- `gpt-5-nano-2025-08-07` - Reasoning model (requires 16K+ tokens)
- `o1-preview` - Advanced reasoning

**Pros:**
- Reasoning models available (gpt-5, o1)
- Wide adoption and documentation
- Good quality reports (~115 lines)

**Cons:**
- Reasoning models need high token limits (16K+)
- Some models have parameter restrictions (temperature)
- Costs can add up quickly

**Best for:** Teams already using OpenAI, reasoning-intensive analysis

**Special considerations:**
- Reasoning models (gpt-5*, o1*) use tokens for internal thinking
- Requires `max_completion_tokens: 16384` for reasoning models
- Some models only support default temperature=1.0

---

### 3. Google Gemini

**Models:**
- `gemini-2.0-flash-exp` - Experimental, fast
- `gemini-1.5-flash` - Stable, fast
- `gemini-1.5-pro` - Higher quality

**Pros:**
- Very fast responses
- Generous free tier (1,500 requests/day)
- Good for rapid development

**Cons:**
- Free tier quota can be exhausted quickly
- Report quality varies

**Best for:** Development, quick testing, high-volume batch processing

---

### 4. Ollama (Local)

**Models:**
- `qwen3-vl:30b` - Vision-language model (recommended)
- `llama3` - General purpose
- `mistral` - Fast and efficient
- Any model from [ollama.com/library](https://ollama.com/library)

**Pros:**
- **Unlimited usage** - no rate limits or costs
- Complete privacy - runs locally
- No internet required after model download
- Great for development and testing

**Cons:**
- Requires local GPU/CPU resources
- Slower than cloud APIs (~30-60 seconds)
- Quality may vary by model

**Best for:** Development, testing, unlimited batch analysis, privacy-sensitive work

**Setup:**
```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the model
ollama pull qwen3-vl:30b

# Verify it's running
ollama list
```

---

### 5. LM Studio (Local with GUI)

**Models:**
- Any GGUF model from Hugging Face
- Examples: `llama-3-8b`, `mistral-7b`, `qwen-14b`
- Browse models at [huggingface.co](https://huggingface.co/models?library=gguf)

**Pros:**
- **User-friendly GUI** - no command line required
- **Unlimited usage** - no rate limits or API costs
- **OpenAI-compatible API** - drop-in replacement
- Complete privacy - runs locally
- Easy model management with download interface
- Real-time inference monitoring
- Cross-platform (Windows, macOS, Linux)

**Cons:**
- Requires local GPU/CPU resources
- Slower than cloud APIs (depends on hardware)
- GUI application needs to stay running
- Quality depends on chosen model

**Best for:** Users who prefer GUI over CLI, local development, privacy-sensitive work

**Setup:**

1. **Download and install LM Studio:**
   - Visit [lmstudio.ai](https://lmstudio.ai)
   - Download for your platform (Windows/Mac/Linux)
   - Install the application

2. **Download a model:**
   - Open LM Studio
   - Click "Search" tab
   - Search for models (e.g., "llama-3", "mistral", "qwen")
   - Click download on your preferred model
   - Wait for download to complete

3. **Start the local server:**
   - Click "Local Server" tab in LM Studio
   - Select your downloaded model
   - Click "Start Server"
   - Default URL: `http://localhost:1234/v1`

4. **Configure Kernel-GraphRAG Sentinel:**

```bash
# In .env file
LLM_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=local-model  # Use the model name shown in LM Studio
```

5. **Test the connection:**

```bash
# Verify LM Studio server is running
curl http://localhost:1234/v1/models

# Run analysis
python3 src/main.py analyze show_val_kb --llm
```

**Tips:**
- Use quantized models (Q4, Q5) for faster inference on consumer hardware
- Larger models (13B, 30B) provide better quality but need more RAM
- Monitor GPU/CPU usage in LM Studio's interface
- LM Studio supports both CPU and GPU acceleration

---

## Quick Start

### Method 1: Using .env File (Recommended)

1. **Edit `.env` file:**

```bash
# Choose your provider
LLM_PROVIDER=anthropic  # Options: anthropic, openai, gemini, ollama, lmstudio

# Configure provider-specific settings:

# Anthropic (recommended)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
ANTHROPIC_MODEL=claude-haiku-4-5

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_MODEL=gpt-4o

# Google Gemini
GEMINI_API_KEY=AIzaSyxxxxx
GEMINI_MODEL=gemini-1.5-flash

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3-vl:30b

# LM Studio (local with GUI)
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=local-model
```

2. **Run analysis:**

```bash
python3 src/main.py analyze <function_name> --llm
```

### Method 2: YAML Configuration File

Create a custom config file:

```yaml
# my-config.yaml
kernel:
  root: /path/to/linux
  subsystem: fs/ext4

llm:
  provider: anthropic
  model: claude-haiku-4-5
  api_key: ${ANTHROPIC_API_KEY}  # Read from environment
  temperature: 0.7

analysis:
  max_call_depth: 3
  max_results: 100
```

Use it:

```bash
python3 src/main.py --config my-config.yaml analyze <function_name> --llm
```

### Method 3: Environment Variable Override (One-time)

Override for a single command:

```bash
# Use Ollama for this analysis only
LLM_PROVIDER=ollama python3 src/main.py analyze ext4_map_blocks --llm

# Use Anthropic for this analysis only
LLM_PROVIDER=anthropic python3 src/main.py analyze ext4_map_blocks --llm
```

---

## Provider Comparison

### Quality Comparison

| Provider | Report Length | Structure | Detail Level | Response Time |
|----------|---------------|-----------|--------------|---------------|
| Anthropic (claude-haiku-4-5) | 200+ lines | ⭐⭐⭐⭐⭐ Excellent | Very High | ~18s |
| OpenAI (gpt-5-nano) | 115+ lines | ⭐⭐⭐⭐ Good | High | ~32s |
| Gemini (gemini-1.5-flash) | 80-100 lines | ⭐⭐⭐ Good | Medium | ~10s |
| Ollama (qwen3-vl:30b) | 150+ lines | ⭐⭐⭐⭐ Good | High | ~45s |
| LM Studio (varies by model) | Varies | ⭐⭐⭐⭐ Good | Medium-High | ~30-60s |

### Cost Comparison

| Provider | Input Cost | Output Cost | Free Tier | Best Use Case |
|----------|-----------|-------------|-----------|---------------|
| **Anthropic** | $0.25/1M | $1.25/1M | 1,000 req/day | Production |
| **OpenAI** | $0.15/1M | $0.60/1M | 500 req/min | Reasoning tasks |
| **Gemini** | Free | Free | 1,500 req/day | Development |
| **Ollama** | **FREE** | **FREE** | **Unlimited** | Testing/Privacy |
| **LM Studio** | **FREE** | **FREE** | **Unlimited** | GUI users/Privacy |

**Average cost per analysis:**
- Anthropic: ~$0.001 per report
- OpenAI: ~$0.0008 per report
- Gemini: $0 (free tier)
- Ollama: $0 (local)
- LM Studio: $0 (local)

---

## Configuration Methods

### Priority Order

Configuration is loaded in this priority order (highest to lowest):

1. Command-line environment variables (one-time override)
2. `.env` file in project root (persistent default)
3. YAML configuration file (via `--config` flag)
4. System environment variables
5. Built-in defaults

### Complete .env Template

```bash
# Kernel-GraphRAG Sentinel LLM Configuration

# ==== LLM Provider Selection ====
# Choose one: anthropic, openai, gemini, ollama, lmstudio
LLM_PROVIDER=anthropic

# ==== Anthropic Claude Configuration ====
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
ANTHROPIC_MODEL=claude-haiku-4-5
# Options: claude-sonnet-3-5, claude-haiku-4-5, claude-opus-3-5

# ==== OpenAI Configuration ====
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_MODEL=gpt-4o
# Options: gpt-4o, gpt-4-turbo, gpt-5-nano-2025-08-07, o1-preview

# ==== Google Gemini Configuration ====
GEMINI_API_KEY=AIzaSy-your-key-here
GEMINI_MODEL=gemini-1.5-flash
# Options: gemini-2.0-flash-exp, gemini-1.5-flash, gemini-1.5-pro

# ==== Ollama Configuration (Local) ====
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3-vl:30b
# Options: qwen3-vl:30b, llama3, mistral, any model from ollama.com/library

# ==== LM Studio Configuration (Local with GUI) ====
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=local-model
# Use the model name shown in LM Studio's Local Server tab
# Examples: llama-3-8b, mistral-7b, qwen-14b

# ==== LLM Parameters (Optional) ====
# Note: Some models have restrictions (e.g., gpt-5-nano only supports temperature=1.0)
LLM_TEMPERATURE=0.7  # Range: 0.0-1.0 (0=deterministic, 1=creative)
```

---

## Rate Limits & Costs

### Rate Limit Details

#### Anthropic Claude
- **Free Tier:**
  - 1,000 requests per day
  - 50 requests per minute
  - 40,000 tokens per minute
- **Paid Tier:**
  - No daily limit
  - Higher RPM based on usage tier

#### OpenAI
- **Free Tier (Tier 1):**
  - 500 requests per minute
  - 200,000 tokens per minute
- **Paid Tier (Tier 2):**
  - 5,000 requests per minute
  - 2,000,000 tokens per minute

#### Google Gemini
- **Free Tier:**
  - 15 requests per minute
  - 1,000,000 tokens per minute
  - 1,500 requests per day
- **Paid Tier:**
  - Higher limits available

#### Ollama (Local)
- **No rate limits** - unlimited usage
- **No costs** - runs on your hardware

#### LM Studio (Local)
- **No rate limits** - unlimited usage
- **No costs** - runs on your hardware
- Performance depends on local hardware specs

### Rate Limit Handling

**Current implementation:**
- Automatic retry for parameter errors (temperature, max_tokens)
- Empty response detection
- Error logging with full response details

**Best practices to avoid rate limits:**
1. Use Anthropic for production (1,000/day is generous)
2. Use Ollama for development/testing (unlimited)
3. Switch providers if you hit a limit
4. Batch analyses during off-peak hours

**Future enhancements (not yet implemented):**
- Automatic retry with exponential backoff
- Provider fallback (Anthropic → Ollama if rate limited)
- Request queuing for batch analyses

---

## Troubleshooting

### Common Issues

#### 1. "API key not found" Error

**Problem:**
```
ValueError: Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.
```

**Solution:**
```bash
# Add API key to .env file
echo "ANTHROPIC_API_KEY=sk-ant-api03-your-key" >> .env

# Or set environment variable
export ANTHROPIC_API_KEY=sk-ant-api03-your-key
```

#### 2. "Unsupported parameter: 'max_tokens'" Error

**Problem:**
```
Error code: 400 - Unsupported parameter: 'max_tokens' is not supported with this model.
Use 'max_completion_tokens' instead.
```

**Solution:**
This is automatically handled for newer OpenAI models. If you see this error, update to the latest version:
```bash
git pull origin master
```

#### 3. "temperature does not support 0.7" Error

**Problem:**
```
Error code: 400 - Unsupported value: 'temperature' does not support 0.7 with this model.
Only the default (1) value is supported.
```

**Solution:**
Some models (e.g., gpt-5-nano) only support default temperature. This is automatically handled with retry logic. The system will:
1. Try with configured temperature
2. Detect the error
3. Automatically retry with default temperature

#### 4. Empty LLM Response

**Problem:**
```
Report written to report.md
# But file is empty or contains "Error: LLM returned empty response"
```

**Solution:**
This happens with reasoning models (gpt-5, o1) that use all tokens for thinking:

```bash
# The system automatically uses 16K tokens for reasoning models
# If you still get empty responses, switch to a different model:

# Switch to Anthropic (recommended)
LLM_PROVIDER=anthropic python3 src/main.py analyze <function> --llm

# Or use Ollama (unlimited)
LLM_PROVIDER=ollama python3 src/main.py analyze <function> --llm
```

#### 5. "Module 'anthropic' not found"

**Problem:**
```
ImportError: anthropic not installed. Run: pip install anthropic
```

**Solution:**
```bash
pip install anthropic
```

#### 6. Ollama Connection Error

**Problem:**
```
ConnectionError: Cannot connect to Ollama at http://localhost:11434
```

**Solution:**
```bash
# Start Ollama service
ollama serve

# Or in Docker environment, use correct URL:
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

---

## Best Practices

### Choosing a Provider

**Use Anthropic when:**
- You need production-quality reports
- You want structured output (tables, checklists)
- You're okay with API costs (~$0.001/report)
- You need fast responses (~18s)

**Use OpenAI when:**
- You need reasoning capabilities (gpt-5, o1)
- Your team already uses OpenAI
- You want good quality at medium cost

**Use Gemini when:**
- You need very fast responses (~10s)
- You're in development/testing phase
- You want a free tier option

**Use Ollama when:**
- You need unlimited usage
- Privacy is critical (local processing)
- You don't want API costs
- You have good hardware (GPU recommended)

### Switching Strategy

```bash
# Development workflow:
LLM_PROVIDER=ollama  # Unlimited testing

# Final validation before commit:
LLM_PROVIDER=anthropic  # High-quality report

# Batch analysis (if you hit rate limits):
LLM_PROVIDER=ollama  # Process 100+ functions

# Production documentation:
LLM_PROVIDER=anthropic  # Best formatting
```

### Token Usage Optimization

**Average token usage per analysis:**
- Input: ~300-400 tokens (impact data)
- Output: ~1,500-2,500 tokens (report)
- Total: ~2,000-3,000 tokens

**With Anthropic free tier (40K TPM):**
- ~13-20 analyses per minute
- ~300-400 analyses per day (before daily limit)

**With OpenAI free tier (200K TPM):**
- ~66-100 analyses per minute
- ~500 analyses per minute limit (RPM constraint)

### Report Quality Tips

1. **Provide more context:**
   ```bash
   # Deeper analysis = better reports
   python3 src/main.py analyze <function> --llm --max-depth 3
   ```

2. **Use appropriate models:**
   - Complex analysis: claude-sonnet-3-5, gpt-4o
   - Quick checks: claude-haiku-4-5, gemini-1.5-flash
   - Unlimited testing: ollama (qwen3-vl:30b)

3. **Save important reports:**
   ```bash
   python3 src/main.py analyze <function> --llm --output critical_function_report.md
   ```

---

## Advanced Configuration

### Custom Temperature per Provider

Some providers have temperature restrictions:

```bash
# Anthropic: 0.0-1.0 (full range)
ANTHROPIC_MODEL=claude-haiku-4-5  # Supports any temperature

# OpenAI: Model-dependent
OPENAI_MODEL=gpt-4o               # Supports 0.0-2.0
OPENAI_MODEL=gpt-5-nano-2025-08-07  # Only supports 1.0 (automatic)

# Gemini: 0.0-1.0
GEMINI_MODEL=gemini-1.5-flash     # Supports 0.0-1.0

# Ollama: Depends on model
OLLAMA_MODEL=qwen3-vl:30b         # Usually supports 0.0-2.0
```

### Model-Specific Notes

**OpenAI Reasoning Models (gpt-5*, o1*):**
- Use all tokens for internal "thinking"
- Require `max_completion_tokens: 16384` (handled automatically)
- Only support default temperature=1.0 (handled automatically)
- Generate very detailed reasoning chains

**Anthropic Claude Haiku:**
- Best balance of speed, cost, and quality
- Excellent at structured output (tables, lists)
- Fast response times (~15-20s)

**Ollama qwen3-vl:30b:**
- Vision-language model (can process images)
- Good quality, slower than APIs
- Requires ~20GB RAM

---

## Examples

### Example 1: Production Analysis with Anthropic

```bash
# Configure .env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
ANTHROPIC_MODEL=claude-haiku-4-5

# Run analysis
python3 src/main.py analyze ext4_file_write_iter --llm --max-depth 3 --output production_report.md

# Result: 200+ line detailed report in ~18 seconds
```

### Example 2: Unlimited Testing with Ollama

```bash
# Configure .env
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3-vl:30b

# Run batch analysis
for func in ext4_map_blocks ext4_get_block ext4_free_blocks; do
    python3 src/main.py analyze $func --llm --output reports/${func}_report.md
done

# Result: Unlimited analyses, no API costs
```

### Example 3: Quick Check with Gemini

```bash
# One-time override
LLM_PROVIDER=gemini python3 src/main.py analyze show_val_kb --llm --max-depth 1

# Result: Fast report (~10s) for quick validation
```

### Example 4: Comparing Providers

```bash
# Test same function with all providers
function="ext4_map_blocks"

LLM_PROVIDER=anthropic python3 src/main.py analyze $function --llm --output anthropic_report.md
LLM_PROVIDER=openai python3 src/main.py analyze $function --llm --output openai_report.md
LLM_PROVIDER=gemini python3 src/main.py analyze $function --llm --output gemini_report.md
LLM_PROVIDER=ollama python3 src/main.py analyze $function --llm --output ollama_report.md

# Compare report quality, length, and formatting
wc -l *_report.md
```

---

## Related Documentation

- [Architecture Overview](architecture.md) - System design
- [Neo4j Setup Guide](neo4j_setup.md) - Database configuration
- [Macro Handling Guide](macro_handling.md) - C preprocessor integration
- [Query Examples](../examples/query_examples.md) - Cypher queries

---

## Summary

**Quick recommendations:**

- **For production:** Use **Anthropic** (claude-haiku-4-5)
  - Best quality, fast, generous free tier

- **For development:** Use **Ollama** (qwen3-vl:30b)
  - Unlimited usage, no costs, good quality

- **For quick tests:** Use **Gemini** (gemini-1.5-flash)
  - Very fast, free tier available

- **For reasoning:** Use **OpenAI** (gpt-5-nano or o1-preview)
  - Advanced reasoning capabilities

**Switching providers is easy:**
```bash
# Edit .env and change line 15:
LLM_PROVIDER=anthropic  # or openai, gemini, ollama
```

All providers are configured and ready to use! 🚀
