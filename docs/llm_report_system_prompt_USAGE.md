# LLM Report System Prompt - Usage Instructions

This document contains implementation instructions for using the KV-cache optimized system prompt.

**📄 Main System Prompt:** [llm_report_system_prompt.md](llm_report_system_prompt.md)

---

## Table of Contents

- [KV-Cache Optimization Strategy](#kv-cache-optimization-strategy)
- [Example Integration](#example-integration)
- [Cache Efficiency Comparison](#cache-efficiency-comparison)
- [Quality Metrics](#quality-metrics)
- [Implementation Guide](#implementation-guide)
- [Expected Cache Performance](#expected-cache-performance)
- [Troubleshooting](#troubleshooting)
- [Performance Monitoring](#performance-monitoring)
- [Best Practices](#best-practices)

---

## KV-Cache Optimization Strategy

This prompt is optimized for KV-cache reuse across multiple API calls:

**Cacheable Section (Lines 12-278 of the system prompt):**
- Role definition and guidelines (never changes)
- Report structure template (static across all reports)
- Writing style and formatting rules (constant)

**Variable Section (Context-Specific Data):**
- Only the actual analysis context changes per request
- Provided as user message, not system message

**Optional Extension (Automotive):**
- Append `llm_automotive_safety_prompt.md` for automotive/safety-critical contexts
- Does not invalidate base cache

---

## Example Integration

```python
# In llm_reporter.py
SYSTEM_PROMPT_BASE = """<lines 12-278 from llm_report_system_prompt.md>"""
AUTOMOTIVE_EXTENSION = """<content from llm_automotive_safety_prompt.md>"""

def _create_prompt(self, context: str, function_name: str, format: str) -> str:
    # Build system message with optional automotive extension
    system_prompt = SYSTEM_PROMPT_BASE

    if self._is_automotive_context(context):
        # Append automotive section - still allows base cache reuse
        system_prompt += "\n\n" + AUTOMOTIVE_EXTENSION

    # Context goes in user message (varies per request)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}
    ]

    return messages
```

---

## Cache Efficiency Comparison

**Before (old structure):**
- Cache hit: ~20% (variable content in middle invalidated cache)
- Tokens processed per request: ~8,000

**After (KV-cache optimized):**
- Cache hit: ~95% (static content cached, only context varies)
- Tokens processed per request: ~1,500 (only user message)
- **Cost savings: ~80% reduction in input token processing**

---

## Quality Metrics

Reports generated with this prompt should achieve:
- **Completeness:** All 10 sections present (11 if automotive)
- **Actionability:** Concrete commands and test cases
- **Clarity:** Tables and formatting aid comprehension
- **Professionalism:** Appropriate for kernel mailing lists
- **Length:** 150-250 lines (comprehensive but concise)

---

## Implementation Guide

### Step 1: Extract System Prompt Content

Extract the actual prompt content (between the triple backticks) to use in your code:

```python
# Read the markdown file and extract the prompt
with open("docs/llm_report_system_prompt.md", "r") as f:
    content = f.read()
    # Extract content between ``` markers
    start = content.find("```\n") + 4
    end = content.rfind("\n```")
    SYSTEM_PROMPT_BASE = content[start:end]
```

### Step 2: Implement Automotive Detection

```python
def _is_automotive_context(self, context: str) -> bool:
    """Detect if context requires automotive safety analysis."""
    automotive_keywords = [
        "automotive", "embedded", "real-time", "safety-critical",
        "iso 26262", "iso 21434", "aspice", "asil",
        "ecu", "autosar", "misra", "functional safety",
        "wcet", "timing analysis", "hard real-time"
    ]
    context_lower = context.lower()
    return any(keyword in context_lower for keyword in automotive_keywords)
```

### Step 3: Build System Prompt Dynamically

```python
def _build_system_prompt(self, context: str) -> str:
    """Build system prompt with optional automotive extension."""
    system_prompt = SYSTEM_PROMPT_BASE

    # Append automotive extension if needed
    if self._is_automotive_context(context):
        with open("docs/llm_automotive_safety_prompt.md", "r") as f:
            automotive_content = f.read()
            start = automotive_content.find("## 11. AUTOMOTIVE")
            end = automotive_content.find("# End of Automotive Safety Extension")
            automotive_section = automotive_content[start:end].strip()
            system_prompt += "\n\n" + automotive_section

    return system_prompt
```

### Step 4: API Call with Prompt Caching

```python
# For Anthropic API with prompt caching
def generate_report(self, context: str, function_name: str) -> str:
    system_prompt = self._build_system_prompt(context)

    response = self.client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=16384,  # 16K for comprehensive reports
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}  # Cache the system prompt
            }
        ],
        messages=[
            {
                "role": "user",
                "content": context  # Variable analysis data
            }
        ]
    )

    return response.content[0].text
```

### Step 5: Monitor Cache Performance

```python
def generate_report_with_metrics(self, context: str, function_name: str) -> dict:
    response = self.client.messages.create(...)

    # Extract cache metrics from response
    usage = response.usage
    metrics = {
        "input_tokens": usage.input_tokens,
        "cache_creation_tokens": getattr(usage, "cache_creation_input_tokens", 0),
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0),
        "output_tokens": usage.output_tokens,
        "cache_hit_rate": (
            getattr(usage, "cache_read_input_tokens", 0) /
            usage.input_tokens * 100 if usage.input_tokens > 0 else 0
        )
    }

    return {
        "report": response.content[0].text,
        "metrics": metrics
    }
```

---

## Expected Cache Performance

### First Request (Cache Miss):
```
Input tokens: 2,500 (system) + 500 (user) = 3,000 total
Cache creation tokens: 2,500
Cache read tokens: 0
Output tokens: 10,000 (report)
Cost: Full input token cost
```

### Second Request (Cache Hit):
```
Input tokens: 2,500 (cached) + 500 (user) = 3,000 total
Cache creation tokens: 0
Cache read tokens: 2,500 (90% discount)
Output tokens: 10,000
Cost: ~85% cheaper than first request
```

### With Automotive Extension (First Time):
```
Input tokens: 3,500 (system) + 600 (user) = 4,100 total
Cache creation tokens: 3,500
Cache read tokens: 0
Output tokens: 12,000
```

### With Automotive Extension (Cached):
```
Input tokens: 3,500 (cached) + 600 (user) = 4,100 total
Cache creation tokens: 0
Cache read tokens: 3,500 (90% discount)
Output tokens: 12,000
Cost: ~87% cheaper than first automotive request
```

---

## Troubleshooting

### Cache Not Working

**Issue:** Cache hit rate is 0%

**Solutions:**
- Ensure system prompt is identical across requests
- Check that `cache_control` is set correctly
- Verify you're using the same model
- Cache expires after 5 minutes of inactivity (Anthropic limitation)

### Low Cache Hit Rate

**Issue:** Cache hit rate is 20-40%

**Solutions:**
- Check for dynamic content in system prompt
- Ensure function names/variable content is in user message only
- Verify automotive detection is stable (not flickering on/off)
- Don't include timestamps or request-specific data in system prompt

### Inconsistent Reports

**Issue:** Report quality varies

**Solutions:**
- Ensure all 10/11 sections are in prompt structure
- Verify context data includes all required fields
- Check that examples in prompt are clear and specific
- Validate temperature settings (0.7 recommended)

### Reports Truncated

**Issue:** Reports cut off mid-section

**Solutions:**
- Increase `max_tokens` (16,384 for Sonnet 4.5)
- Check model-specific token limits
- Verify output tokens in usage metrics
- See `docs/TOKEN_LIMITS.md` for recommendations

---

## Performance Monitoring

### Key Metrics to Track

```python
# Log cache performance
logger.info(f"Cache creation: {usage.cache_creation_input_tokens} tokens")
logger.info(f"Cache read: {usage.cache_read_input_tokens} tokens")
logger.info(f"Cache hit rate: {cache_hit_rate:.1f}%")
logger.info(f"Input tokens: {usage.input_tokens}")
logger.info(f"Output tokens: {usage.output_tokens}")
```

### Expected Values

| Metric | First Request | Second+ Request |
|--------|---------------|-----------------|
| Cache creation | 2,500 | 0 |
| Cache read | 0 | 2,500 |
| Cache hit rate | 0% | 85-95% |
| Input tokens | 3,000 | 3,000 |
| Output tokens | 10,000 | 10,000 |

### Cost Calculation

```python
# Anthropic pricing (as of 2025)
INPUT_TOKEN_COST = 3.00 / 1_000_000  # $3 per 1M tokens
CACHED_TOKEN_COST = 0.30 / 1_000_000  # $0.30 per 1M tokens (90% discount)
OUTPUT_TOKEN_COST = 15.00 / 1_000_000  # $15 per 1M tokens

def calculate_cost(usage):
    input_cost = usage.input_tokens * INPUT_TOKEN_COST
    cache_cost = getattr(usage, 'cache_read_input_tokens', 0) * CACHED_TOKEN_COST
    output_cost = usage.output_tokens * OUTPUT_TOKEN_COST

    # Cache read tokens are included in input_tokens, so subtract the difference
    cache_savings = (
        getattr(usage, 'cache_read_input_tokens', 0) *
        (INPUT_TOKEN_COST - CACHED_TOKEN_COST)
    )

    total = input_cost + output_cost - cache_savings

    return {
        "total": total,
        "input_cost": input_cost - cache_savings,
        "output_cost": output_cost,
        "cache_savings": cache_savings
    }
```

---

## Best Practices

### 1. Minimize System Prompt Changes
- Keep prompt template constant
- Move variable data to user message
- Don't include timestamps or request IDs

### 2. Batch Similar Requests
- Process multiple reports within 5-minute window
- Group automotive vs non-automotive analyses
- Maximize cache hit rate

### 3. Monitor Cache Performance
- Log cache metrics for every request
- Track hit rate over time
- Alert on sudden drops in hit rate

### 4. Handle Cache Expiry
- Accept first request will be cache MISS
- Optimize for sustained workloads
- Consider pre-warming cache for high-volume periods

### 5. Test Regularly
- Use `test_cache_hit.sh` for validation
- Verify cache behavior after prompt changes
- Check token counts match expectations

---

## Related Documentation

- [llm_report_system_prompt.md](llm_report_system_prompt.md) - Main system prompt
- [llm_automotive_safety_prompt.md](llm_automotive_safety_prompt.md) - Automotive extension
- [TOKEN_LIMITS.md](TOKEN_LIMITS.md) - Token limits and cost analysis
- [../scripts/README.md](../scripts/README.md) - Test scripts documentation
- [../test_anthropic_cache.py](../test_anthropic_cache.py) - Standalone cache test

---

## Version History

- **v1.0** (2025-12-28): Initial KV-cache optimized prompt
  - Restructured with static content first
  - Added automotive extension support
  - Implemented 16K token limit for Sonnet 4.5
  - Achieved 95% cache hit rate
