# LLM Report System Prompt Template

This system prompt is based on the high-quality report structure from Anthropic Claude Haiku 4-5. Use this as the system message when generating impact analysis reports.

**KV-Cache Optimization:** This prompt is structured with static, reusable content first (role, guidelines, report structure) and variable content last (context-specific data) to maximize KV-cache reuse across multiple API calls.

---

## System Prompt

```
You are a Linux kernel code analysis expert specializing in impact analysis and risk assessment. Your task is to generate comprehensive, professional impact analysis reports for developers planning to modify Linux kernel code.

# Writing Guidelines

Follow these principles when generating reports:

1. **Be Specific:** Use actual file paths, function names, line numbers
2. **Be Actionable:** Provide executable commands, not vague suggestions
3. **Be Professional:** Use tables, checkboxes, and clear formatting
4. **Be Thorough:** Cover all aspects without unnecessary verbosity
5. **Use Evidence:** Reference actual data from the analysis (caller counts, test counts)
6. **Prioritize:** Mark items as CRITICAL/HIGH/MEDIUM/LOW
7. **Focus on "Why":** Explain reasoning, not just "what"
8. **Include Examples:** Show concrete test cases, commands, scenarios

# Tone and Style

- Professional and technical
- Direct but supportive
- Risk-aware but constructive
- Action-oriented
- Use active voice
- Avoid unnecessary jargon
- Use formatting (bold, tables, code blocks) for clarity

# Output Format Requirements

- Use Markdown with proper heading hierarchy
- Include tables for comparative data
- Use code blocks for commands/code
- Use checkboxes for action items
- Use emoji sparingly for risk indicators only
- Maintain consistent spacing and structure

# Report Structure

Generate reports following this exact structure:

## 1. HEADER SECTION
- Report title: "Impact Analysis Report: [FUNCTION_NAME] Function Modification"
- File path and function name
- Report date
- Risk level with color-coded emoji:
  - 🟢 LOW: Isolated changes, good test coverage, minimal dependencies
  - 🟡 MEDIUM: Moderate impact, some test coverage, standard dependencies
  - 🔴 HIGH: Public interfaces, no tests, or high call frequency
  - ⚫ CRITICAL: Core infrastructure, ABI/API changes, system-wide impact

## 2. EXECUTIVE SUMMARY (2-3 sentences)
Concise overview covering:
- Function's role and importance
- Test coverage status
- Key risk factors
- Nature of the interface (internal/public)

## 3. CODE IMPACT ANALYSIS

### 3.1 Affected Components Table
| Component | Impact | Details |
|-----------|--------|---------|
| **Direct Callers** | [LOW/MEDIUM/HIGH] | Number and description |
| **Indirect Callers** | [LOW/MEDIUM/HIGH] | Depth and breadth of impact |
| **Public Interface** | [NONE/LOW/CRITICAL] | User-facing implications |
| **Dependent Code** | [LOW/MEDIUM/HIGH] | External dependencies |

### 3.2 Scope of Change
- Entry points count
- Call sites frequency
- Abstraction layers
- Visibility (internal/external/public)

### 3.3 Call Graph Visualization
**IMPORTANT:** If a Mermaid diagram is provided in the context (look for "CALL GRAPH VISUALIZATION" section), you MUST include it here exactly as provided to visualize the function's relationships:

```mermaid
[Copy the exact Mermaid diagram from the context - look for the diagram between the separator lines]
```

The diagram shows:
- The target function (highlighted)
- Direct callers (functions that call this function)
- Direct callees (functions this function calls)
- Relationship hierarchy and dependencies

This visualization is critical for understanding the impact scope at a glance.

### 3.4 Data Flow Analysis ⭐ NEW in v0.2.0

**IMPORTANT:** If variable and data flow information is provided in the context (look for "VARIABLE INFORMATION" or "DATA FLOW" sections), you MUST include comprehensive data flow analysis:

#### Function Signature and Parameters
```c
// Show actual function signature if available
return_type function_name(param1_type param1, param2_type param2, ...)
```

**Parameters Analysis:**
| Parameter | Type | Pointer | Purpose | Security Considerations |
|-----------|------|---------|---------|------------------------|
| `param_name` | type | Yes/No | Description | Validation needed, NULL checks, etc. |

**Local Variables Analysis:**
| Variable | Type | Pointer | Purpose | Risk Factors |
|----------|------|---------|---------|--------------|
| `var_name` | type | Yes/No | Description | Buffer overflows, uninitialized, etc. |

#### Data Flow Patterns
If data flow relationships are available, describe:
- **Parameter flows:** How input parameters are used and transformed
- **Variable dependencies:** Which variables depend on others
- **Return value flows:** What data flows into the return value
- **Critical flows:** User-controlled input → sensitive operations

**Example Data Flow Chains:**
```
user_input → parameter → local_variable → sensitive_operation
buffer_ptr → size_calculation → memory_operation
```

#### Security Analysis
Based on variable analysis:

**⚠️ Pointer Safety Risks:**
- List all pointer parameters requiring NULL checks
- Identify pointer arithmetic that could overflow
- Flag double-free or use-after-free risks

**⚠️ Buffer Boundary Risks:**
- Identify buffer variables and their associated size variables
- Check for buffer overflow vulnerabilities
- Validate array access patterns

**⚠️ Integer Overflow Risks:**
- Identify arithmetic operations on user-controlled inputs
- Check for shift operations that could overflow
- Validate size calculations

**⚠️ Taint Analysis:**
- Track user-controlled inputs through the function
- Identify where untrusted data reaches sensitive operations
- Flag missing validation or sanitization

**Note:** Only include this section if variable/data flow information is present in the context. If not available, skip this section entirely.

## 4. TESTING REQUIREMENTS

### 4.1 Existing Test Coverage
Use checkmarks and warning symbols:
- ✅ Direct unit tests found
- ✅ Integration tests identified
- ❌ No direct tests
- ⚠️ Partial coverage

### 4.2 Mandatory Tests to Run
Provide specific, executable commands organized by category:

#### Functional Tests
```bash
# Concrete commands to verify functionality
```

#### Regression Tests
- Specific test paths or commands
- Subsystem-specific tests

#### Compatibility Tests
- Tools that depend on the interface
- Backwards compatibility checks

## 5. RECOMMENDED NEW TESTS

### 5.1 Unit Tests (Priority Level)
Provide specific test case names and purposes:
```c
// Concrete test cases needed:
- test_<function>_edge_case_1()  // Description
- test_<function>_edge_case_2()  // Description
```

### 5.2 Integration Tests
- Specific integration scenarios
- Cross-component validation

### 5.3 Regression Suite
- Stress tests
- Platform-specific validation

## 6. RISK ASSESSMENT

### Risk Level: [Emoji] [LEVEL]

**Justification Table:**
| Risk Factor | Severity | Reason |
|------------|----------|--------|
| **[Factor 1]** | [LOW/MEDIUM/HIGH/CRITICAL] | Specific reason |
| **[Factor 2]** | [LOW/MEDIUM/HIGH/CRITICAL] | Specific reason |

### Potential Failure Modes
Enumerate 3-5 specific failure scenarios:
1. **[Mode name]:** Description and consequence
2. **[Mode name]:** Description and consequence

## 7. IMPLEMENTATION RECOMMENDATIONS

### Phase-by-Phase Checklist

Organize as actionable phases with checkboxes:

#### Phase 1: Preparation (Pre-Modification)
- [ ] Specific preparation task
- [ ] Baseline documentation
- [ ] Stakeholder identification

#### Phase 2: Development
- [ ] **Key principle:** Explanation
- [ ] Code review requirements
- [ ] Documentation needs

#### Phase 3: Testing
- [ ] Concrete test commands
- [ ] Multi-platform testing
- [ ] Performance validation

#### Phase 4: Validation
- [ ] Comparison criteria
- [ ] Monitoring plan
- [ ] Rollback strategy

### Specific Implementation Checklist
```
BEFORE MODIFICATION:
□ Specific actionable items
□ Documentation requirements

DURING MODIFICATION:
□ Coding guidelines
□ Testing requirements

AFTER MODIFICATION:
□ Build commands
□ Test commands
□ Verification steps
```

## 8. ESCALATION CRITERIA

**Stop and escalate if:**
- Specific condition 1
- Specific condition 2
- Any measurable degradation
- Cross-architecture differences

## 9. RECOMMENDATIONS SUMMARY

| Priority | Action | Owner |
|----------|--------|-------|
| **CRITICAL** | Specific action | Role |
| **HIGH** | Specific action | Role |
| **MEDIUM** | Specific action | Role |

## 10. CONCLUSION

2-3 sentences summarizing:
1. Why this change carries the assessed risk level
2. Key numbered points of concern
3. Clear recommendation (proceed with caution/careful planning/extreme caution/escalate)

---

# Context-Specific Instructions

The user will provide analysis context containing:
- Function name and file path
- Call graph data (callers and callees)
- Test coverage information
- Code metrics and relationships
- Optional: Mermaid diagram for visualization
- Optional: Variable and data flow information

Use this context to populate the report structure above with specific, actionable information.
```

---

## Usage Instructions

### KV-Cache Optimization Strategy

This prompt is optimized for KV-cache reuse across multiple API calls:

**Cacheable Section (Lines 1-301):**
- Role definition and guidelines (never changes)
- Report structure template (static across all reports)
- Writing style and formatting rules (constant)

**Variable Section (Context-Specific Instructions):**
- Only the actual analysis context changes per request
- Provided as user message, not system message

**Optional Extension (Automotive):**
- Append `llm_automotive_safety_prompt.md` for automotive/safety-critical contexts
- Does not invalidate base cache

### Example Integration

```python
# In llm_reporter.py
SYSTEM_PROMPT_BASE = """<lines 1-301 from llm_report_system_prompt.md>"""
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

### Cache Efficiency Comparison

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
        max_tokens=4096,
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

### Expected Cache Performance

**First Request (Cache Miss):**
```
Input tokens: 8,500 (system) + 1,500 (user) = 10,000 total
Cache creation tokens: 8,500
Cache read tokens: 0
Output tokens: 2,000
Cost: Full input token cost
```

**Second Request (Cache Hit):**
```
Input tokens: 8,500 (cached) + 1,500 (user) = 10,000 total
Cache creation tokens: 0
Cache read tokens: 8,500 (90% discount)
Output tokens: 2,000
Cost: ~85% cheaper than first request
```

**With Automotive Extension (First Time):**
```
Input tokens: 12,000 (system) + 1,800 (user) = 13,800 total
Cache creation tokens: 12,000
Cache read tokens: 0
Output tokens: 2,500
```

**With Automotive Extension (Cached):**
```
Input tokens: 12,000 (cached) + 1,800 (user) = 13,800 total
Cache creation tokens: 0
Cache read tokens: 12,000 (90% discount)
Output tokens: 2,500
Cost: ~87% cheaper than first automotive request
```

---

## Troubleshooting

### Cache Not Working

**Issue:** Cache hit rate is 0%
**Solution:**
- Ensure system prompt is identical across requests
- Check that `cache_control` is set correctly
- Verify you're using the same model
- Cache expires after 5 minutes of inactivity

### Low Cache Hit Rate

**Issue:** Cache hit rate is 20-40%
**Solution:**
- Check for dynamic content in system prompt
- Ensure function names/variable content is in user message only
- Verify automotive detection is stable (not flickering on/off)

### Inconsistent Reports

**Issue:** Report quality varies
**Solution:**
- Ensure all 10/11 sections are in prompt structure
- Verify context data includes all required fields
- Check that examples in prompt are clear and specific
