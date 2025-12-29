# Kernel-GraphRAG Sentinel - Development Plan v0.3.0

**Version**: 0.3.0 "Inter-Procedural Analysis"
**Target Release Date**: Q1 2026
**Status**: Planning Phase
**Last Updated**: 2025-12-29

---

## Executive Summary

Version 0.3.0 builds upon the strong foundation of v0.1.0 (call graph analysis) and v0.2.0 (intra-procedural data flow) by introducing **inter-procedural data flow analysis** and addressing critical non-functional requirements from v0.1.0-v0.2.0 technical debt.

**Primary Goals:**
1. Complete v0.2.0 non-functional requirements (test coverage, performance benchmarks)
2. Implement inter-procedural data flow analysis
3. Add pointer aliasing analysis
4. Introduce control flow analysis
5. Achieve production-grade quality metrics

**Key Metrics:**
- Test coverage: 70% → 85%+
- Query performance: < 0.5s (currently 0.264s)
- Processing throughput: Document actual ext4 benchmark
- False positive rate: < 10% (validated)

---

## Phase 1: Technical Debt Resolution (Priority: CRITICAL)

**Duration**: 2 weeks
**Status**: Planning

### 1.1 Test Coverage Improvement

**Current State:**
- 112 passing tests, 48 failing tests (70% pass rate)
- Module D (dataflow): 13 test failures
- Module C (KUnit parser): 35 test failures

**Objectives:**
- Fix all 48 failing tests
- Achieve 85%+ code coverage
- Add integration tests for new v0.2.0 features

**Tasks:**

#### Fix Module D Dataflow Tests (13 failures)
```bash
# Failing tests:
- test_complex_assignment_flow
- test_pointer_assignment_flow
- test_extract_function_parameters
- test_extract_local_variables
- test_extract_variable_uses_assignment
- test_pointer_type_detection
- test_initializer_extraction
- test_complex_expressions
- test_struct_types
- test_multiple_functions
```

**Action Items:**
1. Update `VariableTracker` API to match test expectations
2. Enhance pointer type detection logic
3. Fix initializer extraction for complex declarations
4. Improve struct type parsing
5. Add test fixtures for edge cases

#### Fix Module C KUnit Parser Tests (35 failures)
```bash
# Root cause: API signature changes
# KUnitParser.__init__() signature mismatch
```

**Action Items:**
1. Update `KUnitParser` constructor to accept `kernel_root` parameter
2. Refactor test fixtures to use new API
3. Add backward compatibility layer if needed
4. Document API changes in migration guide

#### Add Missing Test Coverage
**Targets:**
- `flow_builder.py`: Add tests for complex flows
- `flow_ingestion.py`: Add end-to-end ingestion tests
- `llm_reporter.py`: Mock LLM responses for testing
- `impact_analyzer.py`: Test edge cases (no callers, deep recursion)

**Deliverables:**
- [ ] All 160 tests passing (100% pass rate)
- [ ] Code coverage report: 85%+
- [ ] Updated TESTING.md with coverage guidelines
- [ ] CI/CD integration for automated testing

---

### 1.2 Performance Benchmarking & Optimization

**Current State:**
- ❓ ext4 ingestion time: Not measured on clean database
- ✅ Query response time: 0.264s (target: < 2s) ✅ EXCEEDED
- ❓ Subsystem support: 1,669 files tested (500 file target likely achieved)

**Objectives:**
- Document baseline performance metrics
- Optimize bottlenecks
- Achieve < 60s for ext4 ingestion

**Tasks:**

#### Benchmark ext4 Ingestion
```bash
# Test scenario: Clean database, fs/ext4 only
# Files: 37
# Expected functions: ~1,136
# Target: < 60 seconds
```

**Action Items:**
1. Create benchmark script (`scripts/benchmark_ext4.sh`)
2. Run on clean Neo4j instance
3. Measure: parsing time, ingestion time, total time
4. Document results in DEVELOPMENT_PLAN.md
5. Compare with v0.1.0 baseline

#### Performance Optimization
**Targets:**
- Parallel parsing: Use multiprocessing for file parsing
- Batch size tuning: Optimize Neo4j batch operations
- Query optimization: Add indexes for common queries
- Memory profiling: Identify memory leaks in large subsystems

**Deliverables:**
- [ ] Benchmark script with repeatable results
- [ ] Performance report (markdown format)
- [ ] Optimization recommendations document
- [ ] Updated non-functional requirements status

---

### 1.3 Call Mapping Accuracy Validation

**Current State:**
- ❓ False positive rate: Not validated
- 62,065 CALLS relationships in database
- No systematic validation process

**Objectives:**
- Establish validation methodology
- Achieve < 10% false positive rate
- Document accuracy metrics

**Tasks:**

#### Manual Validation Process
```bash
# Sample size: 100 random CALLS relationships
# Validation method: Manual code inspection
# Criteria: Call actually exists in source code
```

**Action Items:**
1. Create validation script to sample random calls
2. Export sample to CSV with source locations
3. Manual verification by kernel expert
4. Calculate false positive/negative rates
5. Identify common failure patterns

#### Accuracy Improvement
**Common Issues:**
- Macro-generated function calls
- Function pointers (not detected)
- Conditional compilation (#ifdef)
- Cross-subsystem calls

**Deliverables:**
- [ ] Validation report with metrics
- [ ] Known limitations documentation
- [ ] Accuracy improvement roadmap
- [ ] Updated README with accuracy claims

---

## Phase 2: Inter-Procedural Data Flow Analysis (Priority: HIGH)

**Duration**: 4 weeks
**Status**: Design Phase

### 2.1 Architecture Design

**Current Limitation:**
v0.2.0 provides **intra-procedural** (within-function) data flow analysis only.

**New Capability:**
Track data flows **across function boundaries** through call chains.

**Example Use Case:**
```c
// File: fs/ext4/inode.c
int ext4_write_inode(struct inode *inode) {
    struct ext4_inode_info *ei = EXT4_I(inode);
    return ext4_do_update_inode(inode, ei);  // Flow: inode → ei
}

// File: fs/ext4/inode.c
int ext4_do_update_inode(struct inode *inode, struct ext4_inode_info *ei) {
    ei->i_disksize = inode->i_size;  // Flow continues
}

// Inter-procedural flow:
// ext4_write_inode::inode → ext4_do_update_inode::inode → ei::i_disksize
```

**Graph Schema Extension:**
```cypher
// New relationship type
(:Variable)-[:FLOWS_TO_PARAM {
    from_function: "caller",
    to_function: "callee",
    argument_position: 0,
    call_site_line: 1234
}]->(:Variable)

// New relationship type
(:Variable)<-[:RETURNS_TO {
    from_function: "callee",
    to_function: "caller",
    call_site_line: 1234
}]-(:Variable)
```

**Deliverables:**
- [ ] Inter-procedural flow schema design document
- [ ] Neo4j schema updates
- [ ] Python data structures for cross-function flows
- [ ] Query patterns for inter-procedural analysis

---

### 2.2 Implementation

**Components:**

#### 2.2.1 Argument Mapping
**File**: `src/module_d/interprocedural_flow.py` (~400 lines)

```python
class InterProceduralFlowAnalyzer:
    """Analyze data flows across function boundaries."""

    def map_call_arguments(self, caller_func, callee_func, call_site):
        """Map caller's arguments to callee's parameters."""
        # Example: map(arg1, arg2, arg3) → param(a, b, c)
        pass

    def track_return_values(self, callee_func, caller_func, call_site):
        """Track return value flows back to caller."""
        pass

    def build_cross_function_flows(self, call_chain):
        """Build complete data flow through call chain."""
        pass
```

#### 2.2.2 Parameter Binding
**Algorithm:**
```python
# Step 1: Extract call site arguments
call_args = extract_call_arguments(call_node)  # ["inode", "ei"]

# Step 2: Get callee parameter definitions
params = get_function_parameters(callee)  # ["struct inode *inode", "struct ext4_inode_info *ei"]

# Step 3: Create FLOWS_TO_PARAM relationships
for i, (arg, param) in enumerate(zip(call_args, params)):
    create_flow(
        from_var=arg,
        to_var=param,
        flow_type="FLOWS_TO_PARAM",
        argument_position=i
    )
```

#### 2.2.3 Return Value Tracking
**Algorithm:**
```python
# Step 1: Find return statements in callee
returns = find_return_statements(callee_function)

# Step 2: Track returned variables
for ret in returns:
    returned_var = extract_return_expression(ret)

# Step 3: Map to caller's assignment
caller_var = get_assignment_target(call_site)
create_flow(returned_var, caller_var, "RETURNS_TO")
```

**Deliverables:**
- [ ] `interprocedural_flow.py` implementation
- [ ] Unit tests for argument mapping
- [ ] Integration tests with real kernel code
- [ ] CLI command: `kgraph interprocedural-flow <function>`

---

### 2.3 Query Capabilities

**New Cypher Queries:**

#### End-to-End Taint Tracking
```cypher
// Track user input through multiple function calls
MATCH path = (source:Variable)-[:FLOWS_TO|FLOWS_TO_PARAM|RETURNS_TO*1..10]->(sink:Variable)
WHERE source.name =~ ".*user.*"
  AND sink.scope <> source.scope  // Cross-function
RETURN
  [n in nodes(path) | n.name + " (" + n.scope + ")"] as flow_chain,
  length(path) as hops
ORDER BY hops DESC
LIMIT 20
```

#### Cross-Function Buffer Tracking
```cypher
// Find buffers passed through function calls
MATCH (buf:Variable)-[:FLOWS_TO_PARAM]->(param:Variable)
WHERE buf.name =~ ".*buf.*"
RETURN buf.scope, param.scope, param.name
```

**Deliverables:**
- [ ] Query examples documentation
- [ ] Use case scenarios (security analysis)
- [ ] Performance benchmarks for deep flows (10+ hops)

---

## Phase 3: Pointer Aliasing Analysis (Priority: MEDIUM)

**Duration**: 3 weeks
**Status**: Research Phase

### 3.1 Problem Statement

**Current Limitation:**
Cannot track pointer relationships and aliasing.

**Example:**
```c
int *p = &x;
int *q = p;  // q aliases p, both point to x
*q = 10;     // Actually modifies x, but not tracked
```

**Impact:**
- Data flow analysis incomplete for pointer-heavy code
- False negatives in vulnerability detection
- Limited usefulness for kernel code (heavily pointer-based)

---

### 3.2 Solution Design

**Approach: May-Alias Analysis**

Track potential pointer targets with confidence levels.

**Graph Schema:**
```cypher
(:Variable)-[:MAY_ALIAS {
    confidence: 0.8,  // 0.0-1.0
    alias_type: "address_of" | "assignment" | "parameter_binding",
    file_path: "...",
    line_number: 123
}]->(:Variable)
```

**Alias Types:**
1. **Direct Address-Of**: `int *p = &x;` (confidence: 1.0)
2. **Pointer Assignment**: `int *q = p;` (confidence: 0.9)
3. **Parameter Binding**: Function calls (confidence: 0.8)
4. **Array-to-Pointer Decay**: `int *p = array;` (confidence: 1.0)
5. **Return Value**: `int *p = get_ptr();` (confidence: 0.5)

**Implementation:**
```python
class PointerAliasAnalyzer:
    def analyze_address_of(self, expr):
        """Handle &variable expressions."""
        pass

    def analyze_pointer_assignment(self, lhs, rhs):
        """Handle pointer = pointer."""
        pass

    def propagate_aliases_through_calls(self, call_chain):
        """Track aliases across function boundaries."""
        pass
```

**Deliverables:**
- [ ] Alias detection algorithm
- [ ] May-alias relationship ingestion
- [ ] Query patterns for alias chains
- [ ] Documentation with examples

---

## Phase 4: Control Flow Analysis (Priority: MEDIUM)

**Duration**: 3 weeks
**Status**: Design Phase

### 4.1 Control Flow Graph (CFG) Construction

**Objective:**
Build basic block-level control flow graphs for functions.

**Graph Schema:**
```cypher
(:BasicBlock {
    id: "func_bb_0",
    function: "ext4_write_inode",
    start_line: 10,
    end_line: 15,
    block_type: "entry" | "conditional" | "loop" | "exit"
})

(:BasicBlock)-[:FLOWS_TO {
    condition: "true" | "false" | "unconditional",
    line_number: 12
}]->(:BasicBlock)
```

**Use Cases:**
1. **Path Analysis**: Find execution paths from entry to exit
2. **Reachability**: Determine if code is reachable
3. **Dominance Analysis**: Identify critical code paths
4. **Loop Detection**: Find loops and potential infinite loops

**Implementation:**
```python
class ControlFlowAnalyzer:
    def build_cfg(self, function_ast):
        """Construct control flow graph from AST."""
        pass

    def identify_basic_blocks(self, function_ast):
        """Split function into basic blocks."""
        pass

    def add_control_flow_edges(self, blocks):
        """Add edges based on control flow."""
        pass
```

**Deliverables:**
- [ ] CFG construction algorithm
- [ ] BasicBlock node type in Neo4j
- [ ] Path finding queries
- [ ] Visualization support (Mermaid diagrams)

---

### 4.2 Path-Sensitive Data Flow

**Objective:**
Combine CFG with data flow for path-sensitive analysis.

**Example:**
```c
int x = 0;
if (condition) {
    x = tainted_input();  // Path 1: x is tainted
} else {
    x = 10;               // Path 2: x is safe
}
use(x);  // Is x tainted? Depends on path!
```

**Query:**
```cypher
// Find paths where tainted data reaches use site
MATCH path = (bb_entry:BasicBlock)-[:FLOWS_TO*]->(bb_use:BasicBlock)
WHERE bb_entry contains tainted variable
  AND bb_use contains use site
RETURN path
```

**Deliverables:**
- [ ] Path-sensitive flow queries
- [ ] Condition tracking
- [ ] False positive reduction documentation

---

## Phase 5: Quality Assurance & Production Hardening

**Duration**: 2 weeks
**Status**: Planning

### 5.1 Non-Functional Requirements Completion

**Checklist from v0.1.0 DEVELOPMENT_PLAN.md:**

- [x] ✅ Query response time < 2 seconds (ACHIEVED: 0.264s)
- [x] ✅ Clear documentation (ACHIEVED: Comprehensive docs)
- [ ] ⏳ Process ext4 (37 files) in < 60 seconds (MEASURE & OPTIMIZE)
- [ ] ⏳ Support subsystems up to 500 files (VALIDATE)
- [ ] ⏳ < 10% false positives in call mapping (VALIDATE)
- [ ] ⏳ API coverage > 80% in tests (ACHIEVE: Currently 70%)

**Target:**
- **5/6 complete** → **6/6 complete** (100%)

---

### 5.2 Integration Testing

**Test Scenarios:**

#### End-to-End Workflow Tests
```bash
# Test 1: Complete analysis pipeline
./scripts/test_e2e_workflow.sh

# Test 2: Multi-subsystem analysis
./scripts/test_multi_subsystem.sh fs/ext4 fs/btrfs

# Test 3: Data flow + call graph integration
./scripts/test_integrated_analysis.sh
```

#### Stress Testing
```bash
# Test large subsystem (drivers/net)
kgraph pipeline drivers/net  # ~2000 files

# Measure: memory usage, time, database size
```

**Deliverables:**
- [ ] End-to-end test suite
- [ ] Stress test results
- [ ] Resource usage profiling
- [ ] Scalability recommendations

---

### 5.3 Documentation Completion

**Pending from v0.1.0:**
- [ ] `docs/architecture.md` - System architecture deep dive
- [ ] `docs/API.md` - Complete Python API reference
- [ ] `docs/neo4j_schema_v0.3.0.md` - Updated schema with inter-procedural flows

**New for v0.3.0:**
- [ ] `docs/interprocedural_flow_guide.md` - User guide for cross-function analysis
- [ ] `docs/pointer_aliasing_guide.md` - Alias analysis documentation
- [ ] `docs/control_flow_guide.md` - CFG analysis guide
- [ ] `docs/performance_benchmarks.md` - Official benchmark results

**Deliverables:**
- [ ] 7 new/updated documentation files
- [ ] API reference with examples
- [ ] Tutorial videos (optional)

---

## Success Criteria

### Functional Requirements (v0.3.0)

- [ ] **Inter-procedural data flow**: Track variables across 3+ function calls
- [ ] **Pointer aliasing**: Detect pointer aliases with confidence levels
- [ ] **Control flow analysis**: Generate CFGs for any function
- [ ] **Path-sensitive analysis**: Find execution paths in CFG
- [ ] **Integration**: All modules work together seamlessly

### Non-Functional Requirements (Complete v0.1.0 Debt)

- [ ] **Test coverage**: 85%+ (currently 70%)
- [ ] **Performance**: ext4 ingestion < 60s (documented)
- [ ] **Scalability**: 500-file subsystem support (validated)
- [ ] **Accuracy**: < 10% false positive rate (measured)
- [ ] **Documentation**: Complete (architecture.md, API.md)

### Quality Metrics

- [ ] **Zero failing tests**: 160/160 passing (100%)
- [ ] **Memory efficiency**: < 4GB RAM for large subsystems
- [ ] **Query performance**: < 1s for 90% of queries
- [ ] **Code quality**: Pylint score > 8.0
- [ ] **Type coverage**: 100% type hints on public APIs

---

## Risk Assessment

### Technical Risks

**1. Inter-procedural Analysis Complexity** (HIGH)
- **Risk**: Combinatorial explosion in deep call chains
- **Mitigation**: Limit max depth to 5-7 hops, caching, incremental analysis
- **Fallback**: Provide depth limits and sampling strategies

**2. Pointer Aliasing Accuracy** (MEDIUM)
- **Risk**: May-alias analysis has inherent false positives
- **Mitigation**: Confidence levels, allow user to adjust thresholds
- **Fallback**: Document limitations, provide manual override

**3. Performance Degradation** (MEDIUM)
- **Risk**: Inter-procedural + pointer + CFG may be slow
- **Mitigation**: Profile early, optimize hot paths, use caching
- **Fallback**: Make advanced analysis optional

**4. Graph Database Scaling** (LOW)
- **Risk**: Neo4j may struggle with millions of new relationships
- **Mitigation**: Index optimization, relationship pruning, batch operations
- **Fallback**: Recommend Neo4j Enterprise for large deployments

### Schedule Risks

**1. Scope Creep** (MEDIUM)
- **Mitigation**: Strict phase boundaries, MVP focus, defer non-critical features
- **Status**: Well-defined phases with clear deliverables

**2. Testing Overhead** (LOW)
- **Mitigation**: Automated test generation, CI/CD integration
- **Status**: Strong test foundation from v0.1.0-v0.2.0

---

## Dependencies

### Technical Dependencies

**Required:**
- Neo4j 5.14+ (existing)
- Python 3.12+ (existing)
- tree-sitter-c (existing)
- 8GB+ RAM (new requirement for large analyses)

**Optional:**
- Neo4j Enterprise (for > 1000 file subsystems)
- GPU acceleration (for future ML-based analysis)

### Process Dependencies

**Blockers:**
- v0.2.0 test failures must be resolved before starting Phase 2
- Performance benchmarks must be complete before optimization
- Validation methodology must be established before claiming accuracy

---

## Timeline

### Development Schedule (14 weeks total)

| Week | Phase | Milestone |
|------|-------|-----------|
| 1-2 | Phase 1.1 | Fix all failing tests, achieve 85% coverage |
| 3 | Phase 1.2 | Benchmark ext4, document performance |
| 4 | Phase 1.3 | Validate call mapping accuracy |
| 5-8 | Phase 2 | Inter-procedural flow implementation |
| 9-11 | Phase 3 | Pointer aliasing analysis |
| 12-14 | Phase 4 | Control flow analysis |
| 15-16 | Phase 5 | QA, documentation, release prep |

### Milestones

- **Week 4**: ✅ All v0.1.0 non-functional requirements complete
- **Week 8**: ✅ Inter-procedural analysis working
- **Week 11**: ✅ Pointer aliasing integrated
- **Week 14**: ✅ CFG construction complete
- **Week 16**: 🚀 v0.3.0 Release

---

## Release Readiness Checklist

### Code Quality
- [ ] Zero failing tests (160/160 passing)
- [ ] 85%+ code coverage
- [ ] Pylint score > 8.0
- [ ] All public APIs have type hints
- [ ] No security vulnerabilities (Bandit scan)

### Functionality
- [ ] Inter-procedural flow working on fs/ext4
- [ ] Pointer aliasing detection validated
- [ ] CFG construction for 10+ kernel functions
- [ ] All CLI commands functional
- [ ] LLM integration working (5 providers)

### Documentation
- [ ] architecture.md complete
- [ ] API.md complete
- [ ] 3 new user guides (interprocedural, pointer, CFG)
- [ ] Performance benchmarks documented
- [ ] Migration guide from v0.2.0

### Testing
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] End-to-end tests passing
- [ ] Stress tests passing (large subsystems)
- [ ] Regression tests from v0.1.0-v0.2.0

### Performance
- [ ] ext4 ingestion < 60s
- [ ] Query response < 1s (90% of queries)
- [ ] Memory usage < 4GB (large subsystems)
- [ ] Database size documented

---

## Post-Release (v0.4.0 Planning)

### Future Enhancements

**From v0.2.0 Roadmap:**
- Machine learning-based vulnerability detection
- Automated patch suggestion
- CI/CD pipeline integration
- Web UI for visualization

**New Ideas:**
- Differential analysis (git integration)
- Historical trend analysis
- Multi-repository support
- Cloud deployment guides

---

## Appendix

### Glossary

- **CFG**: Control Flow Graph - directed graph showing execution flow
- **Inter-procedural**: Analysis across function boundaries
- **Intra-procedural**: Analysis within a single function
- **May-alias**: Two pointers that might point to same memory
- **Must-alias**: Two pointers guaranteed to point to same memory
- **Path-sensitive**: Analysis that considers control flow paths
- **Taint analysis**: Tracking untrusted data through the system

### References

- v0.1.0 DEVELOPMENT_PLAN.md (existing)
- v0.2.0 RELEASE_NOTES.md (existing)
- Non-functional requirements analysis (this session)
- Linux kernel coding standards
- Neo4j performance tuning guides

---

**Document Version**: 1.0
**Last Updated**: 2025-12-29
**Status**: Draft - Ready for Review
**Next Review**: After Phase 1 completion

---

## Change Log

### 2025-12-29
- Initial draft created
- Based on v0.2.0 roadmap and non-functional requirements analysis
- 5 phases defined with 16-week timeline
- Success criteria and risk assessment complete

---

**Prepared by:** Claude Sonnet 4.5
**Generated with:** [Claude Code](https://claude.com/claude-code)
