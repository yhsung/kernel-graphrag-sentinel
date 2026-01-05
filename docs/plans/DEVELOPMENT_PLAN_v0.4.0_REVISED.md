# CVE Impact Analyzer - Development Plan v0.4.0 (Revised)

## Executive Summary

**Problem**: Kernel developers spend hours manually tracing CVE impact through codebases. When a CVE is announced, they must grep code, read call chains, and guess affected paths - all while under pressure to ship security patches.

**Solution**: Automate CVE impact analysis by mapping CVE descriptions to kernel code using the existing callgraph infrastructure, showing developers exactly what code paths to review and test.

**Target Users**: Kernel security teams, BSP developers backporting fixes, distro maintainers tracking CVEs

**Timeline**: 6 weeks (down from 11)

**Success Metric**: Reduce CVE impact analysis from 2-4 hours to 5-10 minutes

---

## What Changed (and Why)

| Original (Rejected) | Revised (Practical) | Rationale |
|---------------------|---------------------|-----------|
| Defect trees with probability modeling | CVE impact scope | Real workflow: CVE → find affected code |
| AND/OR gate propagation | Reachability analysis | Simpler, more reliable |
| Pattern detection (10+ patterns) | CVE description → code mapping | Directly solves the problem |
| 11 weeks, 110+ tests | 6 weeks, 60 tests | Focused, achievable |
| LLM-powered pattern matching | LLM for CVE parsing only | Reduce hallucination risk |

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

### The Current Workflow (Painful)

```
Day 1: CVE-2024-1234 announced - "buffer overflow in ext4 writepages"

Step 1: Find the vulnerable function
  $ git grep -r "ext4_writepages"
  (Results: 3 files, 200+ lines to review)

Step 2: Understand call chain
  (Manually trace: sys_write → vfs_write → ext4_write → ext4_writepages)
  (Takes 30-60 minutes of code reading)

Step 3: Find all affected code paths
  (More grepping, more manual tracing)
  (Another 1-2 hours)

Step 4: Check if your kernel version is affected
  (Compare git commits, check if patches applied)
  (Another 30-60 minutes)

Total time: 2-4 hours per CVE
With 50+ CVEs per kernel release: 100-200 hours of manual work
```

### The Proposed Workflow (Automated)

```
Step 1: Ingest CVE
  $ kgraph cve import CVE-2024-1234

Step 2: Get impact report
  $ kgraph cve impact CVE-2024-1234 --subsystem fs/ext4

  Output:
  ✓ Vulnerable function: ext4_writepages (fs/ext4/inode.c:2145)
  ✓ Affected paths from syscalls:
      - sys_write → vfs_write → ext4_write → ext4_writepages [REACHABLE]
      - sys_write → vfs_write → ext4_write_iter → ext4_writepages [REACHABLE]
  ✓ Downstream impact: 23 functions call ext4_writepages
  ✓ Reachable from user input: YES (sys_write)
  ✓ Risk assessment: HIGH

Total time: 5-10 minutes
```

---

## 2. Use Cases

### Use Case 1: Kernel Security Team - Triage CVEs

**Scenario**: Linux kernel security team receives 50 CVEs for the upcoming release. Need to prioritize which affect their codebase.

**Before**: Spend weeks manually reviewing each CVE

**After**:
```bash
# Import all CVEs from NVD feed
kgraph cve import-batch nvd-2024.json

# Get prioritized report
kgraph cve report --severity critical,high --sort reachability

Output:
  CVE-2024-1234 (CRITICAL)
    ✓ Affects your codebase: YES
    ✓ Reachable from syscalls: 2 paths
    ✓ Downstream functions: 23
    ⚠️  NO TEST COVERAGE

  CVE-2024-5678 (HIGH)
    ✓ Affects your codebase: NO (function not in your .config)

# Focus only on relevant CVEs
```

### Use Case 2: BSP Developer - Backport Security Fixes

**Scenario**: Building BSP for ARM64 SoC running kernel 5.15. Need to backport security fixes from 6.6.

**Before**:
- Read each CVE
- Check if affected code exists in 5.15
- Manually apply patches
- Hope nothing breaks

**After**:
```bash
# Check which CVEs affect my kernel version
kgraph cve check --kernel-version 5.15 --subsystem fs/ext4,net/ipv4

Output:
  CVE-2024-1234: AFFECTED (ext4_writepages exists in 5.15)
    → Patch available: commit 7a8b9c (6.6-rc1)
    → Can backport: YES (no dependencies)

  CVE-2024-5678: NOT AFFECTED (ipv4 function added in 6.1)

# Generate backport checklist
kgraph cve backport-checklist --version 5.15 --output todo.md
```

### Use Case 3: Distro Maintainer - Patch Verification

**Scenario**: Shipping kernel 6.1.35 with security patches. Need to verify all patches actually cover the vulnerable paths.

**Before**:
- Apply patches
- Run basic tests
- Hope for the best

**After**:
```bash
# Apply patch and verify coverage
kgraph cve verify-patch CVE-2024-1234 --patch-file 0001-fix-ext4.patch

Output:
  ✓ Patch adds check at line 2145
  ✓ Covers all syscall entry points (2 paths)
  ✓ Downstream impact mitigated (23 callers)
  ⚠️  Suggestion: Add test in fs/ext4/inode_test.c

# Generate test coverage report
kgraph cve test-gaps CVE-2024-1234
```

---

## 3. Feature Requirements

### Core Features (MVP)

#### FR1: CVE Ingestion
- Import from NVD JSON feed
- Parse CVE descriptions with LLM to extract:
  - Affected function name
  - Vulnerability type (buffer overflow, NULL deref, race, etc.)
  - Kernel version range
  - Commit hash (if available)
- Store in Neo4j with minimal schema

#### FR2: Impact Analysis
- Given CVE + function, find:
  - All upstream callers (who calls this function?)
  - All syscalls that reach it (is it user-accessible?)
  - All downstream callees (what breaks if we patch it?)
  - Test coverage (are there tests?)
- **No probability modeling** - just binary reachable/not-reachable

#### FR3: Version Awareness
- Check if function exists in specific kernel version
- Compare against CONFIG_ options (is it compiled in?)
- Check if patch already applied (git commit detection)

#### FR4: Simple Reporting
- Markdown reports with:
  - Affected functions
  - Call paths from syscalls
  - Downstream impact
  - Test coverage gaps
  - Suggested patches

#### FR5: CLI Interface
```bash
kgraph cve import <cve-id|json-file>
kgraph cve impact <cve-id> [--subsystem <path>]
kgraph cve check --kernel-version <ver> [--subsystem <path>]
kgraph cve backport-checklist --version <ver> [--output file.md]
kgraph cve verify-patch <cve-id> --patch-file <file>
kgraph cve test-gaps <cve-id>
```

### Explicitly Out of Scope (to keep it realistic)

❌ Probability modeling (too complex, unreliable)
❌ Defect pattern detection (use separate tool like Coverity, Sparse)
❌ AND/OR gate logic (academic, not practical)
❌ DefectPatternNode, MATCHES_LOG_PATTERN (over-engineered)
❌ LLM for everything (only use for CVE parsing, not analysis)

---

## 4. Architecture

### Simplified Module E Structure

```
src/module_e/
├── __init__.py
├── cve_importer.py          # Import CVE from NVD, parse with LLM
├── impact_analyzer.py       # Reachability analysis (uses existing callgraph)
├── version_checker.py       # Check if function exists in kernel version
├── test_coverage.py         # Check test coverage (uses existing Module C)
├── cve_reporter.py          # Generate markdown reports
└── schema.py                # Minimal CVE node schema
```

### Database Schema (Simplified)

```cypher
// CVE node
CREATE (c:CVE {
    id: "CVE-2024-1234",
    description: "Buffer overflow in ext4_writepages",
    affected_function: "ext4_writepages",
    file_path: "fs/ext4/inode.c",
    line_number: 2145,
    vulnerability_type: "buffer_overflow",
    severity: "CRITICAL",
    cvss_score: 9.8,
    cwe_id: "CWE-787",
    kernel_version_affected: "6.0-6.6",
    fixed_commit: "7a8b9c1d2e3f",
    discovered_date: "2024-03-15"
})

// Single relationship
CREATE (c:CVE)-[:AFFECTS_FUNCTION]->(f:Function)

// No complex relationships (no CAUSES, PROPAGATES_TO, etc.)
// Use existing CALLS relationships from callgraph
```

### Data Flow

```
1. CVE Import
   ├─ Parse NVD JSON → extract CVE metadata
   ├─ Use LLM to parse description → extract function name
   ├─ Verify function exists in codebase
   └─ Store CVE node in Neo4j

2. Impact Analysis
   ├─ Query: (c:CVE)-[:AFFECTS_FUNCTION]->(f:Function)
   ├─ Find callers: ImpactAnalyzer.get_callers_multi_hop(f, max_depth=5)
   ├─ Find syscalls: Filter callers starting with "sys_"
   ├─ Find callees: ImpactAnalyzer.get_callees_multi_hop(f, max_depth=3)
   ├─ Check test coverage: Module C KUnit mapping
   └─ Return impact report

3. Version Check
   ├─ Check if function exists in kernel version X
   ├─ Check git history for patch application
   ├─ Check CONFIG_ dependencies
   └─ Return version compatibility report

4. Report Generation
   ├─ Combine impact + version + test data
   ├─ Generate markdown with:
   │  - Summary (affected function, severity)
   │  - Reachable paths from syscalls
   │  - Downstream impact
   │  - Test coverage gaps
   │  - Recommendations
   └─ Save to file or stdout
```

---

## 5. Implementation Phases

### Phase 1: CVE Import & Parsing (Week 1)

**Objectives**: Import CVEs, parse descriptions, store in Neo4j

**Tasks**:
1. Create CVE schema (1 day)
2. Implement CVEImporter (2 days)
   - NVD JSON parsing
   - LLM integration for function name extraction
   - Error handling (CVE descriptions don't always mention function names)
3. CLI: `kgraph cve import` (1 day)
4. Testing (1 day)
   - Unit tests for importer
   - Test with 10 real CVEs

**Deliverables**:
- Working CVE import
- Can parse CVE descriptions
- CVE nodes in Neo4j

**Example LLM Prompt**:
```
You are a Linux kernel security expert. Extract the following from this CVE description:

CVE: CVE-2024-1234
Description: A buffer overflow vulnerability in ext4_writepages() function in fs/ext4/inode.c
allows local users to cause a denial of service or execute arbitrary code via crafted
filesystem operations.

Extract:
1. Function name (exact): ext4_writepages
2. File path: fs/ext4/inode.c
3. Vulnerability type: buffer_overflow
4. Affected component: filesystem

Return JSON format only.
```

---

### Phase 2: Impact Analysis (Week 2-3)

**Objectives**: Find callers, callees, syscalls, test coverage

**Tasks**:
1. Implement ImpactAnalyzer (3 days)
   - Find all callers (use existing ImpactAnalyzer.get_callers_multi_hop)
   - Find syscalls (filter for "sys_" prefix)
   - Find callees (use existing ImpactAnalyzer.get_callees_multi_hop)
   - Build reachability report
2. Test coverage integration (2 days)
   - Use existing Module C KUnit mapping
   - Check if tests exist for affected function
3. CLI: `kgraph cve impact` (1 day)
4. Testing (3 days)
   - Unit tests for impact analysis
   - Integration test with real CVEs (CVE-2021-3490, CVE-2022-0847)
   - Validate syscall detection

**Deliverables**:
- `kgraph cve impact` command
- Accurate caller/callee detection
- Syscall reachability analysis
- Test coverage reporting

**Example Output**:
```bash
$ kgraph cve impact CVE-2024-1234

CVE-2024-1234: Buffer Overflow in ext4_writepages
Severity: CRITICAL (CVSS 9.8)

Affected Function:
  ext4_writepages (fs/ext4/inode.c:2145)

Reachable from Syscalls:
  ✓ sys_write (2 hops)
    Path: sys_write → vfs_write → ext4_write_iter → ext4_writepages

  ✓ sys_fallocate (3 hops)
    Path: sys_fallocate → vfs_fallocate → ext4_fallocate → ext4_writepages

Downstream Impact (23 functions):
  ext4_do_writepages, ext4_bio_write_page, mpage_submit_page, ...

Test Coverage:
  ⚠️  NO KUnit tests found for ext4_writepages
  ⚠️  Callers with tests: 1/23 (4%)

Risk Assessment: HIGH
  - User-accessible: YES (2 syscalls)
  - Test coverage: POOR
  - Downstream blast radius: LARGE (23 functions)
```

---

### Phase 3: Version Checking (Week 4)

**Objectives**: Check CVE applicability to specific kernel versions

**Tasks**:
1. Implement VersionChecker (3 days)
   - Check if function exists in kernel version X
   - Check git history for patch application
   - Check CONFIG_ dependencies
2. CLI: `kgraph cve check --kernel-version` (1 day)
3. Testing (1 day)
   - Test with multiple kernel versions (5.15, 6.1, 6.6)

**Deliverables**:
- Version-aware CVE checking
- Backport verification

**Example Output**:
```bash
$ kgraph cve check --kernel-version 5.15 --subsystem fs/ext4

CVE-2024-1234:
  ✓ AFFECTS kernel 5.15
    - Function ext4_writepages exists in 5.15
    - Patch NOT applied (commit 7a8b9c not in 5.15 branch)
    - Can backport: YES (no dependencies)

CVE-2024-5678:
  ✗ NOT AFFECTED kernel 5.15
    - Function ipv6_frag_init added in kernel 6.1

Summary: 1 CVE affects kernel 5.15, 0 CVEs already fixed
```

---

### Phase 4: Reporting & Integration (Week 5)

**Objectives**: Generate useful reports, complete workflow

**Tasks**:
1. Implement CVEReporter (3 days)
   - Markdown report generation
   - Backport checklist
   - Patch verification
2. CLI commands (2 days):
   - `kgraph cve report`
   - `kgraph cve backport-checklist`
   - `kgraph cve verify-patch`
3. Integration testing (2 days)
   - End-to-end workflow: import → check → impact → report
   - Test with real subsystems (ext4, net/ipv4)

**Deliverables**:
- Complete CVE analysis workflow
- Markdown reports
- Backport verification

**Example Report**:
```markdown
# CVE Impact Report: fs/ext4 (Kernel 5.15)

Generated: 2024-03-15
Total CVEs analyzed: 12

## Critical CVEs (Affecting Your Kernel)

### CVE-2024-1234 - Buffer Overflow in ext4_writepages
- **Severity**: CRITICAL (CVSS 9.8)
- **Status**: ⚠️ AFFECTS kernel 5.15
- **User-accessible**: YES (sys_write, sys_fallocate)
- **Test Coverage**: POOR (0% coverage)
- **Patch Available**: YES (commit 7a8b9c in 6.6-rc1)
- **Can Backport**: YES

**Action Required**: Backport patch ASAP

**Affected Paths**:
- sys_write → vfs_write → ext4_write_iter → ext4_writepages
- sys_fallocate → vfs_fallocate → ext4_fallocate → ext4_writepages

**Downstream Impact**: 23 functions

**Recommended Tests**:
- Add KUnit test for ext4_writepages with crafted input
- Test syscall paths with malicious input

---

## High CVEs

[Similar format for HIGH severity CVEs]

## Summary

- **Critical CVEs affecting your kernel**: 1
- **High CVEs affecting your kernel**: 3
- **Total patches to backport**: 4
- **Estimated time**: 2-4 hours (vs 20-40 hours manual)
```

---

### Phase 5: Polish & Documentation (Week 6)

**Objectives**: Documentation, examples, bug fixes

**Tasks**:
1. Documentation (3 days)
   - User guide: `docs/cve_analysis_guide.md`
   - Tutorial: "Analyzing your first CVE"
   - Real examples with CVE-2021-3490, CVE-2022-0847
2. Examples (1 day)
   - 5 real CVE case studies
   - Backport workflow examples
3. Bug fixes (2 days)
   - Fix issues found in testing
   - Performance optimization

**Deliverables**:
- Complete documentation (20+ pages)
- 5 real CVE examples
- Stable, tested release

---

## 6. Success Metrics

### Functional Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| CVE import accuracy | 90%+ | Test with 50 real CVEs, verify function extraction |
| Impact analysis accuracy | 95%+ | Manual verification of syscall reachability |
| Version check accuracy | 95%+ | Test against real kernel trees |
| Time savings | 80%+ | Compare to manual analysis (2-4 hrs → 10-20 min) |

### User Feedback

**Survey kernel developers** after 1 month of use:
- "Reduced CVE triage time from hours to minutes" ✓
- "Accurately identified affected code paths" ✓
- "Easy to use CLI" ✓
- "Reports are actionable" ✓

### Adoption

- **3+ kernel teams** using it regularly
- **100+ CVEs** analyzed in production
- **Positive feedback** on LKML or kernel Slack

---

## Appendix: Why This is Better

| Aspect | Original Plan | Revised Plan |
|--------|---------------|--------------|
| **Timeline** | 11 weeks | 6 weeks |
| **Complexity** | Probability modeling, AND/OR gates, pattern detection | Simple reachability analysis |
| **User Value** | Unclear ("defect trees"?) | Clear: "Save 2-4 hours per CVE" |
| **Accuracy** | LLM hallucination risk (pattern matching) | LLM only for parsing (human reviews output) |
| **Maintenance** | Complex schema, many node types | Simple CVE node, reuse existing graph |
| **Testing** | 110+ tests (overkill) | 60 tests (focused) |
| **Real-world use** | Academic | Direct workflow for kernel security teams |

---

**Document Version**: 2.0 (Revised)
**Last Updated**: 2025-01-05
**Status**: Ready for Implementation
