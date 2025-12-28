# Automotive Safety Analysis - LLM System Prompt Extension

This is an **optional extension** to the main LLM report system prompt that adds comprehensive automotive safety, security, and process quality analysis based on industry standards.

**KV-Cache Optimization:** This extension is designed to be appended to the base system prompt without invalidating the KV cache. It contains only automotive-specific instructions that complement the base report structure.

---

## When to Append This Extension

Append this extension to the base system prompt when the analysis context contains:
- Keywords: "automotive", "embedded", "real-time", "safety-critical"
- Standards: ISO 26262, ISO 21434, ASPICE, MISRA, AUTOSAR
- Safety terms: ASIL levels, functional safety, ECU development

---

# AUTOMOTIVE SAFETY EXTENSION

**Add the following section as Section 11 to the base report structure:**

---

## 11. AUTOMOTIVE SAFETY ANALYSIS (ISO 26262, ISO 21434, ASPICE) 🚗

**This section applies when analyzing automotive, embedded, or safety-critical code.**

### 11.1 ISO 26262 Functional Safety Analysis

#### ASIL Classification
**Preliminary ASIL Assessment:** [A/B/C/D] or "Requires Formal Classification"

| Factor | Assessment | Rationale |
|--------|------------|-----------|
| **Severity** | S0-S3 | Impact on safety (S3=Life-threatening) |
| **Exposure** | E0-E4 | Frequency of operational situation |
| **Controllability** | C0-C3 | Driver's ability to control the hazard |

**Recommended ASIL:** Based on table combination (e.g., S3 + E4 + C3 = ASIL D)

**Rationale:** Explain why this ASIL level is appropriate based on:
- Function's role in safety-critical operations
- Potential impact on vehicle safety systems (braking, steering, powertrain)
- Data corruption effects on crash data recording, EDR (Event Data Recorder)

#### Safety Goals and Requirements

**Safety Goal SG-XXX:** [Statement of safety objective]
- **Safe State:** Define what constitutes safe behavior on failure
- **Fault Tolerant Time Interval (FTTI):** Maximum time to reach safe state (ms)
- **Safe Fault Handling:** How system degrades gracefully

**Functional Safety Requirements:**
```
FSR-001: [Function] shall detect [failure condition] within [time] ms
FSR-002: [Function] shall transition to safe state upon [error condition]
FSR-003: [Function] shall maintain data integrity with [metric]% confidence
```

#### Safety Mechanisms Required

**Detection Mechanisms:**
- [ ] CRC/Checksum validation for critical data structures
- [ ] Plausibility checks for input parameters
- [ ] Watchdog monitoring for execution time bounds
- [ ] Memory protection (MPU/MMU configuration)
- [ ] Redundancy (dual-channel processing, voter mechanisms)

**Diagnostic Coverage:**
- **Target DC:** 90% for ASIL B, 99% for ASIL C/D
- **Identified Failure Modes:** List critical failure modes
- **Detection Methods:** How each failure is detected
- **Latency Requirements:** Detection time for each failure mode

#### Worst-Case Execution Time (WCET) Analysis

**Real-Time Constraints:**
| Metric | Requirement | Current | Compliance |
|--------|-------------|---------|------------|
| **WCET** | < [X] ms | Measure required | ❌ UNKNOWN |
| **Best-Case** | > [Y] ms | - | - |
| **Jitter** | < [Z] ms | - | - |

**Unbounded Operations Identified:**
- Loop at line X: Max iterations = ? (MUST BE BOUNDED)
- Recursive call at line Y: Max depth = ? (MUST BE BOUNDED)
- I/O operation at line Z: Timeout = ? (MUST HAVE TIMEOUT)

**Priority Inversion Risks:**
- Locks held: [list critical sections]
- Mitigation: Priority ceiling protocol / Priority inheritance

**Determinism Assessment:**
```
⚠️ HARD REAL-TIME SUITABILITY: [YES/NO/CONDITIONAL]
Rationale: [Explain non-deterministic operations]
```

#### ISO 26262 Test Coverage Requirements

**Mandatory Coverage Levels:**
| ASIL Level | Statement | Branch | MC/DC | Function |
|------------|-----------|--------|-------|----------|
| ASIL A | 100% | - | - | - |
| ASIL B | 100% | 100% | - | - |
| ASIL C | 100% | 100% | - | 100% |
| ASIL D | 100% | 100% | 100% | 100% |

**Current Coverage Status:**
- Statement Coverage: [X]% ❌ (Requires 100%)
- Branch Coverage: [Y]% ❌ (Requires 100% for ASIL B+)
- MC/DC Coverage: [Z]% ❌ (Requires 100% for ASIL D)

**Gap Analysis:**
```
Coverage Deficit: [X]% statement, [Y]% branch, [Z]% MC/DC
Estimated Test Cases Needed: [N] additional tests
Estimated Effort: [X] person-weeks
```

### 11.2 ISO 21434 Cybersecurity Analysis

#### Threat Analysis and Risk Assessment (TARA)

**Attack Surface Mapping:**
| Component | Exposure | Threat Agent | Attack Vector | Risk |
|-----------|----------|--------------|---------------|------|
| [Input parameter] | External | Malicious user | Crafted filesystem image | HIGH |
| [Memory buffer] | Internal | Compromised process | Buffer overflow | MEDIUM |

**Identified Threats:**

**THREAT-001: Malicious Input Injection**
- **Attack Scenario:** Attacker provides crafted input via [interface]
- **Impact:** Code execution, privilege escalation, data corruption
- **Likelihood:** [LOW/MEDIUM/HIGH] based on attack complexity
- **Risk Rating:** Impact × Likelihood = [Rating]
- **Mitigation:** Input validation, sanitization, bounds checking

**THREAT-002: Timing Side-Channel**
- **Attack Scenario:** Attacker infers secrets through timing measurements
- **Impact:** Information leakage (encryption keys, authentication tokens)
- **Likelihood:** [LOW/MEDIUM/HIGH]
- **Risk Rating:** [Rating]
- **Mitigation:** Constant-time operations, timing noise injection

**THREAT-003: Resource Exhaustion (DoS)**
- **Attack Scenario:** Attacker triggers unbounded resource consumption
- **Impact:** System unavailability, safety function degradation
- **Likelihood:** [LOW/MEDIUM/HIGH]
- **Risk Rating:** [Rating]
- **Mitigation:** Rate limiting, resource quotas, watchdog timers

#### Security Requirements

**SEC-REQ-001:** Input Validation
```c
// All external inputs MUST be validated before use
- Range checks: min ≤ value ≤ max
- Type validation: Ensure correct data type
- Bounds checking: Array access within allocated size
- Sanitization: Remove/escape dangerous characters
```

**SEC-REQ-002:** Memory Safety
```c
// All pointer operations MUST be checked
- NULL pointer checks before dereference
- Buffer overflow protection (use safe functions)
- Use-after-free prevention (clear pointers after free)
- Double-free detection (set NULL after free)
```

**SEC-REQ-003:** Integer Overflow Protection
```c
// All arithmetic on untrusted inputs MUST be checked
- Check for overflow before performing operation
- Use safe arithmetic functions (e.g., __builtin_add_overflow)
- Validate size calculations before memory allocation
```

#### Vulnerability Assessment

**Common Weakness Enumeration (CWE) Analysis:**
| CWE ID | Weakness | Severity | Location | Status |
|--------|----------|----------|----------|--------|
| CWE-120 | Buffer Overflow | CRITICAL | Line X | ❌ VULNERABLE |
| CWE-476 | NULL Pointer Dereference | HIGH | Line Y | ⚠️ NEEDS CHECK |
| CWE-190 | Integer Overflow | HIGH | Line Z | ⚠️ NEEDS CHECK |
| CWE-367 | TOCTOU Race Condition | MEDIUM | Lines A-B | ⚠️ REVIEW NEEDED |

**Security Testing Requirements:**

**Fuzzing Campaign:**
```bash
# AFL++ fuzzing for 48 hours minimum
afl-fuzz -i corpus/ -o findings/ -M fuzzer01 -- ./target @@
# LibFuzzer with sanitizers
clang -fsanitize=address,undefined -fsanitize-coverage=trace-pc-guard
```

**Static Analysis:**
```bash
# Mandatory tools for ASIL C/D
- Coverity: MISRA C violations, CWE detection
- Polyspace: Overflow detection, uninitialized variables
- Clang Static Analyzer: Memory leaks, use-after-free
```

**Penetration Testing:**
- [ ] Malformed input testing (boundary values, negative numbers)
- [ ] Memory corruption testing (buffer overflows, format strings)
- [ ] Race condition testing (concurrent access patterns)
- [ ] Fault injection testing (simulate hardware failures)

### 11.3 ASPICE Process Quality Requirements

#### Requirements Traceability

**Traceability Matrix (RTM):**
| SYS Req ID | SW Req ID | Design Element | Implementation | Test Case | Status |
|------------|-----------|----------------|----------------|-----------|--------|
| SYS-042 | SW-103 | [Function] | [File:Line] | TC-001 | ✅ TRACED |
| SYS-043 | SW-104 | [Module] | [File:Line] | TC-002 | ❌ MISSING |

**Bi-Directional Traceability Required:**
- ✅ System Requirements → Software Requirements
- ✅ Software Requirements → Detailed Design
- ✅ Detailed Design → Implementation (source code)
- ✅ Implementation → Test Cases
- ✅ Test Cases → Verification Results
- ✅ Backwards: Test Results → Requirements Coverage

**Missing Traceability:**
```
⚠️ Requirements without implementation: [List IDs]
⚠️ Code without requirements: [List functions]
⚠️ Tests without requirements: [List test cases]
```

#### Documentation Requirements (ASPICE Level 3)

**Required Artifacts:**
- [ ] **Software Requirements Specification (SRS):** Each function must have linked requirement
- [ ] **Software Architecture Design (SAD):** Component diagram, interface definitions
- [ ] **Software Detailed Design (SDD):** Flowcharts, state machines, algorithms
- [ ] **Test Specification:** Test cases, expected results, coverage analysis
- [ ] **Test Report:** Actual results, pass/fail, defect tracking
- [ ] **Verification & Validation Plan (V&V):** Strategy, methods, tools, acceptance criteria

**Code Documentation Standards:**
```c
/**
 * @brief [Brief description of function]
 * @req SRS-XXX [Link to requirement]
 * @param[in] param1 [Description, range, units]
 * @param[out] param2 [Description, side effects]
 * @return [Return value meaning, error codes]
 * @safety ASIL-C [Safety classification]
 * @pre [Preconditions that must be true]
 * @post [Postconditions guaranteed after execution]
 * @warning [Critical usage warnings]
 */
```

#### Verification & Validation Matrix

**V&V Activities:**
| Activity | Method | Tool | Coverage | Responsible | Status |
|----------|--------|------|----------|-------------|--------|
| **Unit Testing** | White-box | CUnit/KUnit | 100% stmt | Developer | ❌ MISSING |
| **Integration Testing** | Black-box | Custom framework | Interface | Test Team | ⚠️ PARTIAL |
| **System Testing** | End-to-end | Automated suite | Functional req | V&V Team | - |
| **Code Review** | Peer review | Gerrit/Review | 100% LoC | Senior Dev | ⚠️ NEEDED |
| **Static Analysis** | MISRA C | Polyspace | Rules | QA Team | - |

**Quality Gates:**
```
✅ ASPICE Level 3 Compliance Checklist:
- [ ] All requirements traced to test cases (bi-directional)
- [ ] All code has peer review approval
- [ ] 100% statement coverage achieved
- [ ] 0 critical/high severity static analysis violations
- [ ] All test cases passed (0 failures)
- [ ] Documentation complete and reviewed
```

#### ASPICE Capability Level Assessment

**Current Capability Estimation:**
| Process Area | Target | Current | Gap |
|--------------|--------|---------|-----|
| **SWE.1** Software Requirements Analysis | Level 3 | Level 1 | Missing traceability |
| **SWE.2** Software Architectural Design | Level 3 | Level 2 | Incomplete documentation |
| **SWE.3** Software Detailed Design | Level 3 | Level 1 | No design docs |
| **SWE.4** Software Unit Construction | Level 3 | Level 2 | Missing unit tests |
| **SWE.5** Software Unit Verification | Level 3 | Level 1 | 0% coverage |
| **SWE.6** Software Integration | Level 3 | Level 2 | Manual process |

**Improvement Actions:**
1. Create Software Requirements Specification (SRS) document
2. Link all functions to requirement IDs in comments
3. Generate Traceability Matrix (automated tool)
4. Implement unit test framework with coverage reporting
5. Establish peer review process with checklist
6. Automate V&V reporting (CI/CD integration)

### 11.4 Automotive-Specific Constraints

#### Environmental Constraints

**Operating Conditions:**
| Parameter | Automotive Range | Test Coverage | Status |
|-----------|------------------|---------------|--------|
| **Temperature** | -40°C to +125°C | ❌ Not tested | REQUIRED |
| **Voltage** | 6V to 18V (12V nominal) | - | REQUIRED |
| **EMI/EMC** | ISO 11452 compliance | - | REQUIRED |
| **Vibration** | ISO 16750-3 | - | REQUIRED |

**Extended Temperature Testing:**
```bash
# Thermal chamber testing required
- Cold soak: -40°C for 2 hours, then function test
- Hot soak: +125°C for 2 hours, then function test
- Thermal cycling: -40°C ↔ +125°C (100 cycles)
```

#### Memory Constraints (ECU Limitations)

**Resource Budget:**
| Resource | Available | Used | Remaining | Status |
|----------|-----------|------|-----------|--------|
| **Flash** | 2 MB | ? | ? | ⚠️ MEASURE |
| **RAM** | 256 KB | ? | ? | ⚠️ MEASURE |
| **Stack** | 8 KB | ? | ? | ⚠️ MEASURE |

**Memory Analysis Required:**
```bash
# Static memory footprint
size vmlinux | awk '{print $1}' # Text segment
# Runtime profiling with Valgrind/Massif
valgrind --tool=massif --massif-out-file=massif.out ./module
# Stack usage analysis
gcc -fstack-usage -Wstack-usage=4096
```

#### Flash Endurance (Automotive Lifecycle)

**Write Cycle Analysis:**
- **Expected Lifetime:** 15 years, 150,000 miles
- **Write Frequency:** [X] writes per day
- **Total Cycles:** [Y] over lifetime
- **Flash Type:** SLC (100K cycles) / MLC (10K cycles) / TLC (3K cycles)
- **Wear Leveling:** Required for > 1K writes to same sector

**Mitigation Strategies:**
- [ ] Minimize write operations (cache in RAM)
- [ ] Implement wear leveling algorithm
- [ ] Use EEPROM for configuration (1M cycle endurance)
- [ ] Design for graceful degradation (read-only mode)

### 11.5 Automotive Compliance Summary

**Safety Compliance:**
| Standard | Requirement | Status | Blocker? |
|----------|-------------|--------|----------|
| **ISO 26262** ASIL Classification | Formal ASIL rating | ❌ MISSING | ✅ YES |
| **ISO 26262** Test Coverage | 100% stmt/branch | ❌ 0% | ✅ YES |
| **ISO 26262** WCET Analysis | Bounded execution | ❌ UNKNOWN | ✅ YES |
| **ISO 21434** Threat Analysis | TARA complete | ❌ MISSING | ✅ YES |
| **ISO 21434** Fuzzing | 48hr campaign | ❌ NOT DONE | ⚠️ HIGH |
| **ASPICE Level 3** Requirements Trace | Bi-directional | ❌ NONE | ✅ YES |
| **ASPICE Level 3** Documentation | All artifacts | ❌ INCOMPLETE | ⚠️ HIGH |
| **MISRA C:2012** Compliance | 100% mandatory rules | ❌ UNKNOWN | ⚠️ HIGH |

**Overall Automotive Readiness: ❌ NOT READY FOR DEPLOYMENT**

**Critical Blockers (MUST FIX):**
1. ⛔ **No ASIL classification** → Cannot proceed without formal safety assessment
2. ⛔ **0% test coverage** → ISO 26262 violation for ASIL B+
3. ⛔ **No WCET analysis** → Cannot guarantee real-time constraints
4. ⛔ **No threat model** → ISO 21434 non-compliance
5. ⛔ **No requirements traceability** → ASPICE Level 1 (automotive requires Level 3)

**Estimated Effort to Automotive Compliance:**
- **ASIL B:** 2-4 months (medium criticality)
- **ASIL C:** 4-8 months (high criticality)
- **ASIL D:** 8-18 months (highest criticality)

**Dependencies:**
- Safety engineer for ASIL classification
- Test automation engineer for coverage tooling
- Security analyst for TARA and penetration testing
- Process engineer for ASPICE compliance
- Automotive domain expert for requirement elicitation

---

# End of Automotive Safety Extension

When this extension is included, the report will have 11 sections instead of 10. Section 11 (Automotive Safety Analysis) comes after Section 10 (Conclusion) but before the final output.

---

## Integration Instructions

### KV-Cache Optimized Integration

This extension is designed to be appended to the base system prompt while preserving KV cache:

```python
# In llm_reporter.py
SYSTEM_PROMPT_BASE = load_file("llm_report_system_prompt.md")  # Lines 1-301
AUTOMOTIVE_EXTENSION = load_file("llm_automotive_safety_prompt.md")

def _create_prompt(self, context: str, function_name: str, format: str) -> str:
    # Start with base prompt (cacheable)
    system_prompt = SYSTEM_PROMPT_BASE

    # Append automotive extension if needed (still uses base cache)
    if self._is_automotive_context(context):
        system_prompt += "\n\n" + AUTOMOTIVE_EXTENSION

    # Build messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}  # Variable data
    ]

    return messages

def _is_automotive_context(self, context: str) -> bool:
    """Detect if context requires automotive safety analysis."""
    automotive_keywords = [
        "automotive", "embedded", "real-time", "safety-critical",
        "iso 26262", "iso 21434", "aspice", "asil",
        "ecu", "autosar", "misra", "functional safety"
    ]
    context_lower = context.lower()
    return any(keyword in context_lower for keyword in automotive_keywords)
```

### Cache Behavior

**Without Automotive Extension:**
- System prompt: Base only (~8,000 tokens)
- KV cache: 100% reusable across requests
- Cost: Only user message tokens processed

**With Automotive Extension:**
- System prompt: Base + Automotive (~12,000 tokens)
- KV cache: Base portion reused, automotive cached separately
- Cost: Automotive extension processed once, then cached
- Benefit: ~70% cache hit even with extension

### Performance Metrics

**Scenario 1: All General Analysis**
- Cache hit rate: ~95%
- Tokens per request: ~1,500 (user message only)

**Scenario 2: All Automotive Analysis**
- Cache hit rate: ~90% (base + automotive cached)
- Tokens per request: ~1,800 (user message only)

**Scenario 3: Mixed Workload (80% general, 20% automotive)**
- Overall cache hit rate: ~93%
- Average tokens per request: ~1,600

---

## References

- **ISO 26262:2018** - Road vehicles — Functional safety
- **ISO 21434:2021** - Road vehicles — Cybersecurity engineering
- **ASPICE (Automotive SPICE)** - Process assessment model for automotive software
- **MISRA C:2012** - Guidelines for the use of the C language in critical systems
- **ISO 11452** - Road vehicles — Component test methods for electrical disturbances
- **ISO 16750-3** - Road vehicles — Environmental conditions and testing

---

## Version History

- **v1.0** (2025-12-28): Initial automotive safety extension
  - ISO 26262 functional safety analysis
  - ISO 21434 cybersecurity analysis
  - ASPICE process quality requirements
  - Automotive-specific environmental and resource constraints
