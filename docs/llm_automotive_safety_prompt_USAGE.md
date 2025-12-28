# Automotive Safety Extension - Usage Instructions

This document contains implementation instructions for using the automotive safety extension with the KV-cache optimized system prompt.

**📄 Main Automotive Prompt:** [llm_automotive_safety_prompt.md](llm_automotive_safety_prompt.md)
**📄 Base System Prompt:** [llm_report_system_prompt.md](llm_report_system_prompt.md)

---

## Table of Contents

- [When to Use This Extension](#when-to-use-this-extension)
- [KV-Cache Optimized Integration](#kv-cache-optimized-integration)
- [Cache Behavior](#cache-behavior)
- [Performance Metrics](#performance-metrics)
- [Implementation Examples](#implementation-examples)
- [Testing](#testing)

---

## When to Use This Extension

Append this extension to the base system prompt when the analysis context contains:

### Trigger Keywords
- **Automotive:** "automotive", "vehicle", "ECU", "AUTOSAR"
- **Embedded:** "embedded", "real-time", "hard real-time"
- **Safety:** "safety-critical", "functional safety", "ASIL"
- **Standards:** "ISO 26262", "ISO 21434", "ASPICE", "MISRA"
- **Timing:** "WCET", "timing analysis", "determinism"

### Detection Function

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

---

## KV-Cache Optimized Integration

This extension is designed to be appended to the base system prompt while preserving KV cache.

### Architecture

```
┌─────────────────────────────────────┐
│  Base System Prompt                 │  ← Cached (2,500 tokens)
│  - Role & Guidelines                │
│  - Report Structure (Sections 1-10) │
└─────────────────────────────────────┘
            │
            ├─── Normal Context
            │    └─► Use base only (Cache HIT: 95%)
            │
            └─── Automotive Context
                 ├─► Append Section 11
                 └─► Combined prompt cached (3,500 tokens)
                     (Cache HIT: 90% on future automotive requests)
```

### Integration Code

```python
# In llm_reporter.py
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent.parent / "docs"
SYSTEM_PROMPT_FILE = DOCS_DIR / "llm_report_system_prompt.md"
AUTOMOTIVE_PROMPT_FILE = DOCS_DIR / "llm_automotive_safety_prompt.md"

def _load_system_prompt(self) -> str:
    """Load base system prompt from file."""
    with open(SYSTEM_PROMPT_FILE, 'r') as f:
        content = f.read()
    # Extract content between ``` markers
    start = content.find("```\n") + 4
    end = content.rfind("\n```")
    return content[start:end]

def _load_automotive_prompt(self) -> str:
    """Load automotive safety extension."""
    with open(AUTOMOTIVE_PROMPT_FILE, 'r') as f:
        content = f.read()
    # Extract Section 11 content
    start = content.find("## 11. AUTOMOTIVE SAFETY ANALYSIS")
    end = content.find("# End of Automotive Safety Extension")
    return content[start:end].strip() if start != -1 and end != -1 else ""

def _build_system_prompt(self, context: str) -> str:
    """Build system prompt with optional automotive extension."""
    system_prompt = self._system_prompt_base

    # Append automotive extension if needed (still uses base cache)
    if self._is_automotive_context(context):
        if self._automotive_extension:
            system_prompt += "\n\n" + self._automotive_extension
            logger.info("Including automotive safety analysis (Section 11)")
        else:
            logger.warning("Automotive context detected but extension not loaded")

    return system_prompt
```

### Anthropic API Call with Caching

```python
def generate_report(self, context: str, function_name: str) -> str:
    """Generate report with prompt caching."""
    system_prompt = self._build_system_prompt(context)

    response = self.client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=16384,  # 16K for comprehensive reports
        temperature=0.7,
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

    # Log cache metrics
    usage = response.usage
    if hasattr(usage, 'cache_read_input_tokens'):
        logger.info(f"Cache HIT - Read {usage.cache_read_input_tokens} tokens")
    if hasattr(usage, 'cache_creation_input_tokens'):
        logger.info(f"Cache MISS - Created {usage.cache_creation_input_tokens} tokens")

    return response.content[0].text
```

---

## Cache Behavior

### Without Automotive Extension

**Request Flow:**
```
Request 1 (Normal):
  System: Base prompt (2,500 tokens)
  Cache: MISS - Create cache
  Cost: Full input token cost

Request 2 (Normal):
  System: Base prompt (2,500 tokens) ← IDENTICAL
  Cache: HIT - Read from cache (90% discount)
  Cost: ~10% of first request
```

**Metrics:**
- System prompt: Base only (~2,500 tokens)
- KV cache: 100% reusable across requests
- Cost: Only user message tokens processed after first request

### With Automotive Extension

**Request Flow:**
```
Request 1 (Automotive):
  System: Base + Auto (3,500 tokens)
  Cache: MISS - Create cache
  Cost: Full input token cost

Request 2 (Normal):
  System: Base only (2,500 tokens) ← DIFFERENT SIZE
  Cache: HIT for base portion only
  Cost: ~30% of first request (base cached, no auto)

Request 3 (Automotive):
  System: Base + Auto (3,500 tokens) ← MATCHES REQUEST 1
  Cache: HIT - Read from cache (90% discount)
  Cost: ~10% of first request
```

**Metrics:**
- System prompt: Base + Automotive (~3,500 tokens)
- KV cache: Base portion reused, automotive cached separately
- Cost: Automotive extension processed once, then cached
- Benefit: ~70% cache hit even with extension

---

## Performance Metrics

### Scenario 1: All General Analysis (No Automotive)

```
100 requests × 2,500 tokens = 250,000 tokens

Cache behavior:
  Request 1: MISS (2,500 tokens at full price)
  Requests 2-100: HIT (2,500 tokens at 10% price each)

Cost:
  Request 1: 2,500 × $3.00/1M = $0.0075
  Requests 2-100: 99 × 2,500 × $0.30/1M = $0.0743
  Total: $0.0818 (vs $0.75 without caching = 89% savings)
```

**Cache hit rate:** ~95%
**Tokens per request:** ~500 (user message only, after first)

### Scenario 2: All Automotive Analysis

```
100 requests × 3,500 tokens = 350,000 tokens

Cache behavior:
  Request 1: MISS (3,500 tokens at full price)
  Requests 2-100: HIT (3,500 tokens at 10% price each)

Cost:
  Request 1: 3,500 × $3.00/1M = $0.0105
  Requests 2-100: 99 × 3,500 × $0.30/1M = $0.1040
  Total: $0.1145 (vs $1.05 without caching = 89% savings)
```

**Cache hit rate:** ~90% (base + automotive cached)
**Tokens per request:** ~600 (user message only, after first)

### Scenario 3: Mixed Workload (80% general, 20% automotive)

```
80 general + 20 automotive requests

Cache behavior:
  Request 1 (general): MISS (2,500 tokens)
  Requests 2-80 (general): HIT (2,500 tokens each)
  Request 81 (automotive): MISS (3,500 tokens)
  Requests 82-100 (automotive): HIT (3,500 tokens each)

Cost:
  General: $0.0075 + (79 × 2,500 × $0.30/1M) = $0.0668
  Automotive: $0.0105 + (19 × 3,500 × $0.30/1M) = $0.0305
  Total: $0.0973 (vs $0.86 without caching = 89% savings)
```

**Overall cache hit rate:** ~93%
**Average tokens per request:** ~550

---

## Implementation Examples

### Example 1: Basic Integration

```python
class LLMReporter:
    def __init__(self, config, graph_store=None):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)

        # Load prompts once at initialization
        self._system_prompt_base = self._load_system_prompt()
        self._automotive_extension = self._load_automotive_prompt()

    def generate_impact_report(self, impact_data, function_name):
        context = self._build_context(impact_data, function_name)
        system_prompt = self._build_system_prompt(context)

        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=16384,
            system=[{"type": "text", "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": context}]
        )

        return response.content[0].text
```

### Example 2: With Cache Metrics Logging

```python
def generate_with_metrics(self, impact_data, function_name):
    """Generate report and log cache performance."""
    context = self._build_context(impact_data, function_name)
    system_prompt = self._build_system_prompt(context)

    is_automotive = self._is_automotive_context(context)
    logger.info(f"Automotive context: {is_automotive}")
    logger.info(f"System prompt size: {len(system_prompt)} chars")

    response = self.client.messages.create(
        model=self.config.model,
        max_tokens=16384,
        system=[{"type": "text", "text": system_prompt,
                "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": context}]
    )

    # Log metrics
    usage = response.usage
    cache_read = getattr(usage, 'cache_read_input_tokens', 0)
    cache_create = getattr(usage, 'cache_creation_input_tokens', 0)

    if cache_create > 0:
        logger.info(f"Cache MISS - Created: {cache_create} tokens")
    if cache_read > 0:
        hit_rate = (cache_read / usage.input_tokens * 100) if usage.input_tokens > 0 else 0
        logger.info(f"Cache HIT - Read: {cache_read} tokens ({hit_rate:.1f}% hit rate)")

    logger.info(f"Input: {usage.input_tokens}, Output: {usage.output_tokens}")

    return response.content[0].text
```

### Example 3: Manual Trigger (Override Auto-Detection)

```python
def generate_with_automotive(self, impact_data, function_name, force_automotive=False):
    """Generate report with optional forced automotive analysis."""
    context = self._build_context(impact_data, function_name)

    # Build prompt
    system_prompt = self._system_prompt_base

    # Force automotive or auto-detect
    if force_automotive or self._is_automotive_context(context):
        system_prompt += "\n\n" + self._automotive_extension
        logger.info("Including automotive safety analysis (Section 11)")

    # ... rest of API call
```

---

## Testing

### Test Automotive Context Detection

```python
# Test cases
test_contexts = [
    ("ext4 filesystem function", False),
    ("automotive ECU brake control", True),
    ("real-time scheduling with WCET < 10ms", True),
    ("ISO 26262 ASIL-D safety function", True),
    ("regular Linux driver", False),
]

for context, expected in test_contexts:
    result = reporter._is_automotive_context(context)
    assert result == expected, f"Failed for: {context}"
    print(f"✓ {context}: {result}")
```

### Test Cache Behavior

Use the provided test scripts:

```bash
# Test automotive detection and caching
python3 test_anthropic_cache.py

# Test with real functions
./scripts/test_cache_hit.sh anthropic claude-sonnet-4-5
```

### Verify Section 11 Inclusion

```python
# Generate automotive report
report = reporter.generate_impact_report(impact_data, "ecu_brake_control")

# Check for Section 11
assert "11. AUTOMOTIVE SAFETY ANALYSIS" in report
assert "ISO 26262" in report
assert "ASIL" in report
assert "WCET" in report

print("✅ Automotive section included correctly")
```

---

## Best Practices

### 1. Load Prompts Once
```python
# Good: Load at initialization
def __init__(self):
    self._system_prompt_base = self._load_system_prompt()
    self._automotive_extension = self._load_automotive_prompt()

# Bad: Load on every request
def generate_report(self):
    system_prompt = self._load_system_prompt()  # Inefficient!
```

### 2. Consistent Keyword Detection
```python
# Ensure keywords are lowercase and comprehensive
automotive_keywords = [
    "automotive", "embedded", "real-time", "safety-critical",
    "iso 26262", "iso 21434", "aspice", "asil",
    "ecu", "autosar", "misra", "functional safety",
    "wcet", "timing analysis", "hard real-time"
]

# Always use lowercase comparison
context_lower = context.lower()
return any(keyword in context_lower for keyword in automotive_keywords)
```

### 3. Monitor Cache Performance
```python
# Track metrics over time
metrics = {
    "total_requests": 0,
    "cache_hits": 0,
    "automotive_requests": 0,
}

# Update on each request
if cache_read > 0:
    metrics["cache_hits"] += 1
if is_automotive:
    metrics["automotive_requests"] += 1
metrics["total_requests"] += 1

# Log periodically
if metrics["total_requests"] % 100 == 0:
    hit_rate = metrics["cache_hits"] / metrics["total_requests"] * 100
    auto_rate = metrics["automotive_requests"] / metrics["total_requests"] * 100
    logger.info(f"Cache hit rate: {hit_rate:.1f}%, Automotive: {auto_rate:.1f}%")
```

### 4. Handle Missing Extension Gracefully
```python
def _build_system_prompt(self, context: str) -> str:
    system_prompt = self._system_prompt_base

    if self._is_automotive_context(context):
        if self._automotive_extension:
            system_prompt += "\n\n" + self._automotive_extension
        else:
            logger.warning("Automotive context detected but extension not loaded - continuing without Section 11")
            # Still generate report, just without automotive section

    return system_prompt
```

---

## Troubleshooting

### Extension Not Appearing in Report

**Issue:** Section 11 missing from automotive reports

**Solutions:**
- Verify keywords in context: `logger.info(f"Context: {context[:200]}")`
- Check detection result: `logger.info(f"Is automotive: {self._is_automotive_context(context)}")`
- Verify extension loaded: `logger.info(f"Extension size: {len(self._automotive_extension)}")`
- Check prompt markers: Ensure "## 11. AUTOMOTIVE" and "# End of Automotive Safety Extension" exist

### Cache Not Improving Performance

**Issue:** Every request shows Cache MISS

**Solutions:**
- Ensure system prompt is identical across requests
- Check if automotive detection is flickering (sometimes True, sometimes False for similar contexts)
- Verify cache TTL hasn't expired (5 minutes for Anthropic)
- Check model consistency (same model for all requests)

### Inconsistent Automotive Detection

**Issue:** Similar contexts yield different detection results

**Solutions:**
- Add logging: `logger.debug(f"Context keywords found: {[kw for kw in keywords if kw in context.lower()]}")`
- Expand keyword list if needed
- Consider adding user override parameter for manual control

---

## Related Documentation

- [llm_automotive_safety_prompt.md](llm_automotive_safety_prompt.md) - Main automotive extension
- [llm_report_system_prompt.md](llm_report_system_prompt.md) - Base system prompt
- [llm_report_system_prompt_USAGE.md](llm_report_system_prompt_USAGE.md) - Base prompt usage
- [TOKEN_LIMITS.md](TOKEN_LIMITS.md) - Token limits and cost analysis
- [../scripts/README.md](../scripts/README.md) - Test scripts documentation

---

## Version History

- **v1.0** (2025-12-28): Initial automotive extension usage guide
  - KV-cache integration strategy
  - Performance metrics and examples
  - Cache behavior documentation
  - Testing and troubleshooting guides
