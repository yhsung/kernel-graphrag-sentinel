# Log Coverage Analyzer - Development Plan v0.5.0 (Revised)

## Executive Summary

**Problem**: Kernel developers struggle with error logging - too many critical error paths have no logs, making production debugging extremely difficult. When a bug report comes in with "EXT4-fs error" in dmesg, developers waste hours tracing back to find the exact source.

**Solution**: Automatically identify unlogged error paths, suggest log placements, and provide quick dmesg → code lookup.

**Target Users**: Kernel developers, BSP bring-up engineers, production support teams

**Timeline**: 5 weeks (down from 10)

**Success Metric**: Reduce "find this error in code" from 30-60 minutes to <1 minute

---

## What Changed (and Why)

| Original (Rejected) | Revised (Practical) | Rationale |
|---------------------|---------------------|-----------|
| Log intention classification (7 categories) | Coverage gap detection | Devs need to know "what's missing" not classify what exists |
| LLM-powered clustering by feature | Group by function only | Simpler, sufficient |
| 75+ log function variants | 20 core functions | 80% of value, 20% effort |
| Forward + backward context analysis | Backward only (error paths) | Focus on coverage |
| 10 weeks, 170+ tests | 5 weeks, 50 tests | Focused, achievable |
| LLM for classification, clustering | LLM for reports only | Reduce cost, reduce hallucinations |

---

## Table of Contents

1. [Real-World Problem](#1-real-world-problem)
2. [Use Cases](#2-use-cases)
3. [Feature Requirements](#3-feature-requirements)
4. [Architecture](#4-architecture)
5. [Implementation Phases](#5-implementation-phases)
6. [Success Metrics](#6-success-metrics)

---

## 1. Real-World Problem

### The Current Situation (Painful)

```
Scenario 1: Production Bug Report
User: "I'm seeing 'EXT4-fs error (device sda1): ext4_writepage' in dmesg"

Step 1: Search codebase for the error message
  $ grep -r "ext4_writepage" fs/ext4/
  (Results: 200+ matches, need to find exact one)

Step 2: Find which log function generates this
  (Read kernel printk documentation, check if it's ext4_error, pr_err, etc.)
  (Another 10-15 minutes)

Step 3: Understand the error path
  (Manually trace back through code to find what triggers this log)
  (Another 20-30 minutes of code reading)

Total time: 30-60 minutes per error
With 10+ errors per day: 5-10 hours wasted


Scenario 2: Adding Error Logging
Dev: "I need to add error logs to this function"

Step 1: Find all error paths
  (Manually grep for "return -ERR", "goto err_", etc.)
  (Easy to miss paths)

Step 2: Determine which paths already have logs
  (Read code, check for printk, pr_err, etc.)
  (Time-consuming, error-prone)

Step 3: Add logs without being redundant
  (Am I adding too many logs? Too few?)
  (No clear guidance)

Result: Inconsistent logging, bugs slip through
```

### The Proposed Solution (Automated)

```
Scenario 1: Production Bug Report
User: "I'm seeing 'EXT4-fs error (device sda1): ext4_writepage' in dmesg"

Step 1: Quick lookup
  $ kgraph logs dmesg "ext4_writepage"

  Output:
  ✓ Found: fs/ext4/inode.c:2145
    Function: ext4_writepages
    Log function: ext4_error_inode
    Error condition: if (ret < 0)
    Callers that reach this: 23 functions
    Syscall paths: sys_write → ... → ext4_writepages

  Output: 5-10 seconds


Scenario 2: Adding Error Logging
Dev: "Check error logging coverage in ext4_writepages"

  $ kgraph logs coverage ext4_writepages --suggest

  Output:
  ext4_writepages: 33% coverage (2/6 error paths logged)

  Logged paths:
    ✓ Line 2178: ret = -EIO, log: ext4_error_inode(...)

  Unlogged paths (gaps):
    ✗ Line 2145: return -ENOMEM (no log)
       → Suggest: pr_err("allocation failed: ENOMEM")
    ✗ Line 2167: goto err_unlock (no log)
       → Suggest: pr_err("lock contention: %d", ret)
    ✗ Line 2190: return -EIO (no log)
       → Suggest: ext4_error("I/O error in writepages")

  Redundant logs:
    ⚠️ "ext4 write failed" logged 3 times in same call chain:
       - ext4_writepages (line 2145)
       - ext4_do_writepages (line 2234)
       - mpage_submit_page (line 2356)

  Result: Clear action items, better logging
```

---

## 2. Use Cases

### Use Case 1: Kernel Developer - Improve Error Logging

**Scenario**: Developer writes new function, wants to ensure proper error logging.

**Before**:
- Manually grep for error returns
- Forget to add logs in some paths
- Inconsistent logging style

**After**:
```bash
# Check coverage
kgraph logs coverage my_new_function --suggest

# Apply suggestions
# (Copy-paste suggested log statements into code)

# Verify improvement
kgraph logs coverage my_new_function

Output:
  ✓ my_new_function: 100% coverage (4/4 error paths logged)
  ✓ No redundant logs detected
  ✓ Proper severity levels (KERN_ERR for errors, KERN_DEBUG for tracing)
```

### Use Case 2: BSP Bring-up - Find Missing Logs

**Scenario**: Bringing up new ARM64 board, seeing random crashes but no useful logs.

**Before**:
- Add printk() calls everywhere (log pollution)
- Reboot and test (slow)
- Still miss critical paths

**After**:
```bash
# Find all unlogged error paths in critical drivers
kgraph logs gaps drivers/gpio --suggest

Output:
  Found 47 unlogged error paths in drivers/gpio

  Critical gaps (high priority):
    1. gpio_request: 0% coverage (0/3 paths)
       → Line 234: return -ENODEV (no log)
       → Line 245: return -EBUSY (no log)
       → Line 256: return -EINVAL (no log)

    2. gpio_direction_output: 25% coverage (1/4 paths)
       → [3 more unlogged paths]

# Focus on high-impact functions first
# Add logs where they matter most
```

### Use Case 3: Production Support - Quick dmesg Lookup

**Scenario**: Production system logs show error, need to find source quickly.

**Before**:
- Grep for error message (200+ matches)
- Read code to find which match
- Trace call chain manually
- 30-60 minutes wasted

**After**:
```bash
# Quick lookup
kgraph logs dmesg "gpio: failed to request"

Output:
  ✓ Found: drivers/gpio/gpiolib.c:567
    Function: gpio_request
    Log function: pr_err
    Error message: "gpio: failed to request GPIO %d: %d\n"
    Error variables: gpio, ret
    Triggered when: ret < 0 (all error paths)

    Call chain from syscalls:
      - sys_ioctl → gpio_ioctl → gpio_request
      - sys_write → gpio_write → gpio_request

    Recent changes:
      - Line 567 modified in commit 7a8b9c (2 weeks ago)
      - Suggestion: Check if recent commit introduced bug

# Immediate context, can start debugging right away
```

### Use Case 4: Code Review - Check Logging Quality

**Scenario**: Reviewing patch that adds error handling.

**Before**:
- Manually check each error path
- Easy to miss missing logs
- Inconsistent reviews

**After**:
```bash
# Before patch
kgraph logs coverage ext4_writepages --suggest
# Shows 3 missing logs

# Apply patch
# (Developer adds logs)

# After patch
kgraph logs coverage ext4_writepages

Output:
  ✓ ext4_writepages: 100% coverage (6/6 paths logged)
  ✓ Proper severity levels
  ✓ No redundant logs

# Objective review criteria
```

---

## 3. Feature Requirements

### Core Features (MVP)

#### FR1: Log Extraction (Simplified)
- Extract 20 core logging functions:
  ```python
  CORE_LOG_FUNCTIONS = {
      # Core logging (8 severity levels)
      'printk', 'pr_emerg', 'pr_alert', 'pr_crit',
      'pr_err', 'pr_warn', 'pr_notice', 'pr_info', 'pr_debug',

      # Device logging (common ones)
      'dev_err', 'dev_warn', 'dev_info', 'dev_dbg',

      # Common subsystem wrappers
      'ext4_error', 'ext4_warning', 'ext4_msg',
      # (add other subsystems as needed)
  }
  ```
- Extract format strings and arguments
- Identify log level (KERN_ERR, KERN_DEBUG, etc.)
- **Skip**: 75+ variants, conditional compilation, once/ratelimited variants (handle later if needed)

#### FR2: Error Path Detection
- Find all error return paths:
  - `return -ERRNO` statements
  - `goto err_label` statements
  - Error cleanup paths
- For each path, check if log exists before return/goto
- Calculate coverage percentage

#### FR3: Log Gap Detection
- Identify unlogged error paths
- Suggest log placement with:
  - Log function (pr_err, dev_err, subsystem wrapper)
  - Severity level
  - Suggested log message with arguments
  - Example code snippet

#### FR4: Redundant Log Detection
- Find same error logged multiple times in call chain
- Detect duplicate log messages
- Flag log pollution (too many logs in same function)

#### FR5: dmesg → Code Lookup
- Search logs by message pattern
- Return exact location (file, line, function)
- Show call chain context
- Link to error conditions

#### FR6: Simple Reporting
- Coverage percentage per function
- List of unlogged paths with suggestions
- Redundant log warnings
- Markdown format (optional LLM enhancement)

#### FR7: CLI Interface
```bash
kgraph logs extract <subsystem>                    # Extract logs
kgraph logs coverage <function> [--suggest]        # Check coverage
kgraph logs gaps <function> [--suggest]            # Show gaps only
kgraph logs find <message-pattern>                 # Search logs
kgraph logs dmesg <error-message>                  # dmesg lookup
kgraph logs report <subsystem> [--llm]             # Generate report
```

### Explicitly Out of Scope (to keep it realistic)

❌ Log intention classification (7 categories) - overkill
❌ LLM for classification - too slow, too expensive
❌ Feature-based grouping - interesting but not critical
❌ LogPatternNode - academic
❌ Forward context analysis - not needed for coverage
❌ 75+ log function variants - handle basics first
❌ Bug correlation from dmesg - too error-prone
❌ Compliance, performance, security log categories - niche use cases
❌ Log heatmap visualization - nice to have, not MVP

---

## 4. Architecture

### Simplified Module F Structure

```
src/module_f/
├── __init__.py
├── log_extractor.py       # Extract logs from AST (20 core functions)
├── error_path_detector.py # Find error return paths
├── coverage_analyzer.py   # Calculate coverage, find gaps, suggest logs
├── redundant_detector.py  # Find duplicate/redundant logs
├── log_search.py          # dmesg → code lookup
├── log_reporter.py        # Generate coverage reports
└── schema.py              # Minimal log schema
```

### Database Schema (Minimal)

```cypher
// LogStatement node
CREATE (l:LogStatement {
    id: "fs/ext4/inode.c::2145",
    function: "ext4_writepages",
    file_path: "fs/ext4/inode.c",
    line_number: 2145,
    log_function: "ext4_error",
    log_level: "KERN_ERR",
    severity: 3,
    format_string: "ext4 writepage failed: %d",
    arguments: ["ret"],
    in_error_path: true,
    error_condition: "if (ret < 0)"
})

// Single relationship
CREATE (f:Function)-[:EMITS_LOG]->(l:LogStatement)

// No LogGroup, LogPattern, FOLLOWS_LOG, etc.
// Use existing CALLS relationships for call chain analysis
```

### Data Flow

```
1. Log Extraction
   ├─ Parse C files with tree-sitter
   ├─ Find calls to 20 core log functions
   ├─ Extract format string and arguments
   └─ Create LogStatement nodes

2. Error Path Detection
   ├─ Parse function AST
   ├─ Find all return statements with error codes
   ├─ Find all goto error_label statements
   ├─ Build list of error exit points
   └─ Return error path list

3. Coverage Analysis
   ├─ For each error path:
   │  ├─ Check if LogStatement exists before return/goto
   │  └─ Mark as logged or unlogged
   ├─ Calculate: coverage = logged_paths / total_paths
   ├─ Identify gaps (unlogged paths)
   └─ Generate suggestions

4. Redundancy Detection
   ├─ Find logs with same format string in call chain
   ├─ Detect multiple logs in same error path
   └─ Flag redundancies

5. dmesg Lookup
   ├─ Parse error message from user
   ├─ Search LogStatement.format_string
   ├─ Return exact matches
   └─ Show call chain context

6. Report Generation
   ├─ Coverage percentage
   ├─ Unlogged paths with suggestions
   ├─ Redundancy warnings
   └─ Optional LLM enhancement (insights, not classification)
```

---

## 5. Implementation Phases

### Phase 1: Log Extraction (Week 1)

**Objectives**: Extract 20 core logging functions, store in Neo4j

**Tasks**:
1. Create log schema (1 day)
2. Implement LogExtractor (2 days)
   - Parse 20 core log functions
   - Extract format strings and arguments
   - Detect if in error path (AST: parent if_statement)
3. CLI: `kgraph logs extract` (1 day)
4. Testing (1 day)
   - Unit tests for extractor
   - Test with ext4 subsystem (expect 50-100 logs)

**Deliverables**:
- Working log extraction
- LogStatement nodes in Neo4j
- `kgraph logs list` command

---

### Phase 2: Error Path Detection (Week 2)

**Objectives**: Find all error return paths, calculate coverage

**Tasks**:
1. Implement ErrorPathDetector (3 days)
   - Parse function AST
   - Find `return -ERRNO` statements
   - Find `goto err_label` statements
   - Build error path list with line numbers
2. Calculate coverage (2 days)
   - For each error path, check for LogStatement before return
   - Calculate coverage percentage
   - Identify unlogged paths
3. Testing (2 days)
   - Unit tests for path detection
   - Validate against real functions (ext4_writepages, etc.)

**Deliverables**:
- `kgraph logs coverage <function>` command
- Accurate error path detection
- Coverage percentage calculation

**Example Output**:
```bash
$ kgraph logs coverage ext4_writepages

ext4_writepages: 33% coverage (2/6 error paths)

Error paths:
  ✓ Line 2178: return -EIO [LOGGED]
    → ext4_error_inode(..., "I/O error")

  ✗ Line 2145: return -ENOMEM [NOT LOGGED]
  ✗ Line 2167: goto err_unlock [NOT LOGGED]
  ✗ Line 2190: return -EIO [NOT LOGGED]
  ✗ Line 2211: goto err_out [NOT LOGGED]
  ✗ Line 2234: return -EFAULT [NOT LOGGED]
```

---

### Phase 3: Gap Detection & Suggestions (Week 3)

**Objectives**: Suggest log placements for unlogged paths

**Tasks**:
1. Implement suggestion algorithm (3 days)
   - Determine log function (pr_err, dev_err, subsystem wrapper)
   - Determine severity level
   - Generate log message with arguments
   - Create code snippet suggestions
2. Redundancy detection (2 days)
   - Find duplicate log messages in call chain
   - Detect multiple logs in same error path
3. CLI: `kgraph logs gaps --suggest` (2 days)

**Deliverables**:
- Automatic log placement suggestions
- Redundancy detection
- Actionable recommendations

**Example Output**:
```bash
$ kgraph logs gaps ext4_writepages --suggest

ext4_writepages: 4 unlogged error paths

Gap 1: Line 2145
  Error: return -ENOMEM
  Suggestion: Add pr_err() before return
  Code:
    if (!page) {
  +     pr_err("ext4: failed to allocate page\n");
        return -ENOMEM;
    }

Gap 2: Line 2167
  Error: goto err_unlock
  Suggestion: Add ext4_error() before goto
  Code:
    if (ret < 0) {
  +     ext4_error_inode(inode, __func__, __LINE__, 0,
  +                       "lock contention: %d", ret);
        goto err_unlock;
    }

[... 2 more gaps ...]

Redundant logs detected:
  ⚠️ "ext4 write failed" appears 3 times in call chain:
     - ext4_writepages:2145 (pr_err)
     - ext4_do_writepages:2234 (pr_err)
     - mpage_submit_page:2356 (pr_err)
  → Consider logging at top level only
```

---

### Phase 4: dmesg Lookup (Week 4)

**Objectives**: Quick dmesg → code lookup

**Tasks**:
1. Implement LogSearch (2 days)
   - Full-text search on format_string
   - Fuzzy matching for partial messages
   - Return exact matches with context
2. Call chain tracing (2 days)
   - Use existing ImpactAnalyzer
   - Show syscall paths
   - Show error conditions
3. CLI: `kgraph logs dmesg` (1 day)

**Deliverables**:
- `kgraph logs dmesg <message>` command
- Fast error message lookup
- Contextual information

**Example Output**:
```bash
$ kgraph logs dmesg "ext4 writepage failed"

Found 3 matches:

1. fs/ext4/inode.c:2145 (exact match)
   Function: ext4_writepages
   Log function: ext4_error_inode
   Log message: "ext4 writepage failed: %d"
   Arguments: ret
   Error condition: if (ret < 0)

   Syscall paths:
     - sys_write (2 hops) → vfs_write → ext4_write_iter → ext4_writepages
     - sys_fallocate (3 hops) → vfs_fallocate → ext4_fallocate → ext4_writepages

   Recent changes:
     - Line 2145 modified in commit 7a8b9c (2024-02-15)

[... 2 more matches ...]
```

---

### Phase 5: Reporting & Polish (Week 5)

**Objectives**: Generate reports, documentation, examples

**Tasks**:
1. Implement LogReporter (2 days)
   - Markdown report generation
   - Per-function coverage reports
   - Per-subsystem summary
2. Optional LLM enhancement (1 day)
   - Add insights section to reports
   - NOT for classification (only for analysis)
3. Documentation (1 day)
   - User guide
   - Tutorial
   - Real examples
4. Examples & testing (1 day)
   - 3 real examples (ext4, gpio, mm)
   - Bug fixes

**Deliverables**:
- `kgraph logs report <subsystem>` command
- Complete documentation
- Stable release

**Example Report**:
```markdown
# Log Coverage Report: fs/ext4

Generated: 2024-03-15
Total functions analyzed: 156
Functions with error paths: 89

## Summary

- **Overall coverage**: 54% (48% logged, 52% unlogged)
- **Total error paths**: 234
- **Logged paths**: 126
- **Unlogged paths**: 108

## Critical Gaps (High Priority)

1. **ext4_writepages** - 33% coverage (2/6 logged)
   - Impact: HIGH (called from sys_write, sys_fallocate)
   - Action: Add 4 error logs

2. **ext4_new_inode** - 25% coverage (1/4 logged)
   - Impact: HIGH (called from ext4_create, ext4_mkdir)
   - Action: Add 3 error logs

[... more gaps ...]

## Redundant Logs

- "ext4 allocation failed" logged 5 times across call chain
- "ext4 lock failed" logged 3 times
- Consider consolidating to top-level callers

## Recommendations

1. Add error logs to all paths in ext4_writepages (HIGH priority)
2. Consolidate redundant logs in allocation functions
3. Add logs to ext4_new_inode error paths
4. Review coverage for all functions reachable from syscalls

[...]
```

---

## 6. Success Metrics

### Functional Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Error path detection accuracy | 95%+ | Manual verification of 50 functions |
| Log suggestion accuracy | 80%+ | Developer survey (are suggestions useful?) |
| dmesg lookup time | <5 seconds | Performance benchmark |
| Coverage calculation accuracy | 95%+ | Manual spot checks |

### User Feedback

**Survey kernel developers** after 1 month of use:
- "Reduced time to find error source from 30-60 min to <1 min" ✓
- "Suggestions are accurate and actionable" ✓
- "Easy to use CLI" ✓
- "Helped improve logging quality in my code" ✓

### Adoption

- **5+ kernel teams** using it regularly
- **100+ functions** analyzed for coverage
- **20%+ improvement** in error logging coverage

---

## Appendix: Why This is Better

| Aspect | Original Plan | Revised Plan |
|--------|---------------|--------------|
| **Timeline** | 10 weeks | 5 weeks |
| **Core Value** | Classify logs by intention | Find missing error logs |
| **Complexity** | 9 components, LLM everywhere | 4 components, LLM optional |
| **User Workflow** | "Classify all logs" (interesting but...) | "Fix my logging" (actionable) |
| **LLM Usage** | Classification, clustering (slow, expensive) | Reports only (fast, cheap) |
| **Testing** | 170+ tests | 50 tests (focused) |
| **Real-world use** | Academic | Production debugging |

---

**Document Version**: 2.0 (Revised)
**Last Updated**: 2025-01-05
**Status**: Ready for Implementation
