# Token Limits for LLM Report Generation

## Overview

Different LLM providers and models have varying token limits for output generation. This document explains the token limits used in kernel-graphrag-sentinel for generating comprehensive impact analysis reports.

---

## Token Limits by Provider and Model

### Anthropic Claude

| Model | Max Output Tokens | Rationale |
|-------|-------------------|-----------|
| **Claude Sonnet 4.5** | 16,384 (16K) | Comprehensive reports with 10-11 sections, including optional automotive safety analysis |
| **Claude Haiku** | 8,192 (8K) | Shorter reports, sufficient for standard 10-section structure |
| **Default** | 4,096 (4K) | Conservative fallback for unknown models |

**Implementation:** Dynamic detection based on model name
```python
if "sonnet" in self.config.model.lower():
    max_tokens = 16384  # 16K for Sonnet
elif "haiku" in self.config.model.lower():
    max_tokens = 8192   # 8K for Haiku
else:
    max_tokens = 4096   # Conservative default
```

### OpenAI

| Model | Max Output Tokens | Rationale |
|-------|-------------------|-----------|
| **GPT-4o** | 16,384 (16K) | Full comprehensive reports |
| **GPT-5 / o1** | 16,384 (16K) | Reasoning models need more tokens for thinking process |
| **GPT-4o-mini** | 2,048 (2K) | Smaller context, shorter reports |
| **Default** | 2,048 (2K) | Conservative for standard models |

**Implementation:**
```python
max_tokens = 16384 if "gpt-5" in self.config.model or "o1" in self.config.model else 2048
```

### Google Gemini

| Model | Max Output Tokens | Rationale |
|-------|-------------------|-----------|
| **Gemini 2.0 Flash** | 8,192 (8K) | Standard comprehensive reports |
| **Gemini 3.0 Flash** | 8,192 (8K) | Same as 2.0 Flash |
| **Default** | 8,192 (8K) | Gemini's maximum |

### Local LLMs (Ollama, LM Studio)

| Provider | Max Output Tokens | Rationale |
|----------|-------------------|-----------|
| **Ollama** | Model-dependent | No explicit limit set, uses model default |
| **LM Studio** | 4,096 (4K) | Conservative for local models |

---

## Why 16K for Sonnet 4.5?

The comprehensive impact analysis report structure includes:

### Standard Report (10 sections) - ~6-10K tokens
1. Header Section
2. Executive Summary
3. Code Impact Analysis (with Mermaid diagram, data flow analysis)
4. Testing Requirements
5. Recommended New Tests
6. Risk Assessment
7. Implementation Recommendations
8. Escalation Criteria
9. Recommendations Summary
10. Conclusion

### With Automotive Extension (11 sections) - ~10-16K tokens
- Adds Section 11: Automotive Safety Analysis
  - ISO 26262 Functional Safety Analysis
  - ISO 21434 Cybersecurity Analysis
  - ASPICE Process Quality Requirements
  - Automotive-specific constraints
  - Compliance summary

**Token Breakdown:**
- Base report: 6,000-10,000 tokens
- Automotive extension: 3,000-6,000 tokens
- **Total max:** ~16,000 tokens

Setting `max_tokens=16384` ensures the report is never truncated, even with the most comprehensive automotive safety analysis.

---

## Historical Context

### Before (4K limit)
The example report at `docs/examples/reports/anthropic-claude-sonnet-4-5-cache-report.md` was **truncated at line 410** due to the 4K token limit. The report ended mid-sentence in Section 6 (Implementation Recommendations), missing:
- Rest of Phase 2-4 checklists
- Section 7: Escalation Criteria
- Section 8: Recommendations Summary
- Section 9: Conclusion

### After (16K limit)
With 16K tokens, the same report would be **complete**, including all sections and the automotive safety extension if applicable.

---

## Cost Implications

### Anthropic Pricing (as of 2025)
- **Input tokens:** $3.00 per 1M tokens
- **Output tokens:** $15.00 per 1M tokens
- **Cached input tokens:** $0.30 per 1M tokens (90% discount)

**Cost per report (with caching):**
```
First report (cache miss):
  Input:  8,500 tokens × $3.00/1M  = $0.0255
  Output: 10,000 tokens × $15.00/1M = $0.1500
  Total:  $0.1755

Second report (cache hit):
  Cached: 8,500 tokens × $0.30/1M  = $0.00255
  Input:  1,500 tokens × $3.00/1M  = $0.0045
  Output: 10,000 tokens × $15.00/1M = $0.1500
  Total:  $0.15705 (10% cheaper than first)

With 16K output (comprehensive):
  Output: 16,000 tokens × $15.00/1M = $0.2400
  Total:  ~$0.25 per report (second+ reports with cache)
```

**Per 100 reports (with 95% cache hit rate):**
- 100 × $0.25 = **$25** (comprehensive reports)
- vs. 100 × $0.10 = **$10** (truncated 4K reports)

**Trade-off:** $15 extra per 100 reports buys **complete, untruncated reports**.

---

## Recommendations

### When to Use 16K Limit
- ✅ Production reports for kernel mailing lists
- ✅ Safety-critical or automotive contexts
- ✅ Comprehensive documentation requirements
- ✅ When report completeness > cost concerns

### When to Use 4K-8K Limit
- ✅ Quick exploratory analysis
- ✅ Budget-constrained environments
- ✅ High-volume batch processing (>1000 reports/day)
- ✅ When summary is sufficient

### Override Token Limit
You can override the default by modifying `LLMConfig`:

```python
config = LLMConfig(
    provider="anthropic",
    model="claude-sonnet-4-5-20250929",
    api_key=api_key,
    temperature=0.7
)

# Override in API call (not currently exposed in config)
# Would require adding max_tokens to LLMConfig dataclass
```

---

## Future Improvements

1. **Expose `max_tokens` in LLMConfig:**
   ```python
   @dataclass
   class LLMConfig:
       provider: str
       model: str
       api_key: Optional[str]
       temperature: float = 0.7
       max_tokens: Optional[int] = None  # Auto-detect if None
   ```

2. **Dynamic adjustment based on context:**
   - Detect if automotive section needed
   - Set 16K for automotive, 8K for standard
   - Save ~$0.10 per standard report

3. **Streaming output:**
   - Allow partial report generation
   - Stop when reaching token limit gracefully
   - Append "... (truncated at X tokens)" notice

---

## Testing Token Limits

Run the test script to verify token limits work correctly:

```bash
export ANTHROPIC_API_KEY=your_key_here
python3 test_anthropic_cache.py
```

Check logs for:
```
DEBUG - Token usage - Input: 8500, Output: 15234, Cache creation: 8500, Cache read: 0
```

If output is consistently 4096 or 8192, the limit is being hit and should be increased.

---

## References

- [Anthropic API Documentation - Token Limits](https://docs.anthropic.com/claude/docs/models-overview)
- [OpenAI API - Max Tokens](https://platform.openai.com/docs/api-reference/chat/create#max_tokens)
- [Gemini API - Output Token Limits](https://ai.google.dev/gemini-api/docs/models/gemini)
