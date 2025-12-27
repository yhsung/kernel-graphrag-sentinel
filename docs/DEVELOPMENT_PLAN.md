# Kernel-GraphRAG Sentinel - Development Plan

**Project Status**: Phase 3 of 7 Complete (43%)
**Last Updated**: 2025-12-27
**Version**: 1.0.0-POC

---

## Executive Summary

Kernel-GraphRAG Sentinel is an AI-powered Linux kernel code analysis system that:
- Parses C source code using tree-sitter
- Builds call graphs in Neo4j graph database
- Maps KUnit test coverage to functions
- Provides AI-powered impact analysis for code changes
- Helps developers understand kernel code modification risks

**Target Use Case**: Before modifying a kernel function, query the system to understand:
- What other functions will be affected (call chains)
- Which tests cover this function
- What tests should be run or written
- Potential risk assessment via LLM analysis

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ User Interface (Phase 6)                                    │
│  - CLI commands (kgraph analyze, kgraph query)             │
│  - YAML configuration                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Module A: C Code Parser (Phase 2) ✅                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ preprocessor │→ │ parser       │→ │ extractor    │     │
│  │ (gcc -E)     │  │ (tree-sitter)│  │ (functions)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Module B: Graph Database (Phase 3) ✅                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ schema       │→ │ graph_store  │→ │ ingestion    │     │
│  │ (Neo4j)      │  │ (driver)     │  │ (pipeline)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Module C: Test Mapper (Phase 4) ⏳                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ kunit_parser │→ │ test_mapper  │→ │ coverage     │     │
│  │ (KUnit)      │  │ (mapping)    │  │ (analysis)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Impact Analysis + LLM (Phase 5) ⏳                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ queries      │→ │ analyzer     │→ │ llm_reporter │     │
│  │ (Cypher)     │  │ (call chains)│  │ (GPT-4/Gemini│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Core Technologies
- **Language**: Python 3.12+ with type hints
- **Parser**: tree-sitter-c 0.23.5 for C AST parsing
- **Database**: Neo4j (latest) for graph storage
- **Preprocessing**: GCC (cpp) for macro expansion

### Python Dependencies
- **Parsing**: `tree-sitter`, `tree-sitter-c`
- **Graph**: `neo4j`, `llama-index-core`, `llama-index-graph-stores-neo4j`
- **LLM**: `openai`, `google-generativeai`, `anthropic`
- **CLI**: `click`, `rich`, `pyyaml`
- **Testing**: `pytest`, `pytest-cov`

### Infrastructure
- **Development**: Dev container environment
- **Database**: Neo4j running on `bolt://localhost:7687`
- **Target**: Linux kernel 6.13+ source code

---

## Phase-by-Phase Development Plan

### Phase 1: Environment Setup ✅ COMPLETE

**Duration**: Day 1
**Status**: ✅ Completed

#### Objectives
- Set up complete development environment
- Install and configure Neo4j
- Set up tree-sitter-c parser
- Create project structure

#### Deliverables
- [x] Project directory structure created
- [x] Neo4j installed and running (bolt://localhost:7687)
- [x] tree-sitter-c compiled and working
- [x] `requirements.txt` with all dependencies
- [x] `.env.template` for configuration
- [x] Installation scripts (`install_neo4j.sh`, `setup_tree_sitter.sh`)

#### Validation Criteria
- ✅ Neo4j accessible via Python driver
- ✅ tree-sitter-c can parse C code
- ✅ All dependencies installed

#### Key Files Created
```
scripts/install_neo4j.sh
scripts/setup_tree_sitter.sh
requirements.txt
.env.template
.gitignore
```

---

### Phase 2: Module A - C Code Parser ✅ COMPLETE

**Duration**: Days 2-3
**Status**: ✅ Completed

#### Objectives
- Implement C source code parsing
- Handle kernel-specific macros
- Extract functions and call relationships

#### Components Implemented

**1. preprocessor.py (256 lines)**
- Kernel macro preprocessing with `gcc -E`
- Kernel-specific include path extraction
- Architecture-aware header resolution
- Fallback to raw parsing when preprocessing unavailable

**Key Features**:
```python
# Extract with macro expansion
preprocessor = KernelPreprocessor(kernel_root)
code = preprocessor.preprocess_file("fs/ext4/super.c")

# Automatic include path detection
include_paths = [
    "include/",
    "include/uapi/",
    "arch/arm64/include/",
    # ... auto-detected
]
```

**2. parser.py (257 lines)**
- tree-sitter C language parser integration
- Manual AST traversal for API compatibility
- Function definition extraction
- Function call relationship detection
- Struct definition parsing

**Key Features**:
```python
# Parse C code into AST
parser = CParser()
root = parser.parse(source_code)

# Extract functions and calls
functions = parser.find_functions(root)
calls = parser.find_function_calls(root)
```

**3. extractor.py (294 lines)**
- End-to-end extraction pipeline
- `FunctionNode` and `CallEdge` data structures
- Call graph construction
- Statistics and analysis utilities

**Key Features**:
```python
# Extract from entire subsystem
extractor = FunctionExtractor(kernel_root)
functions, calls = extractor.extract_from_subsystem("fs/ext4")

# Get statistics
stats = extractor.get_statistics(functions, calls)
```

#### Test Results - fs/ext4
- **1,136 functions** extracted (819 static, 317 exported)
- **13,017 call edges** identified
- **37 C source files** processed
- Average 11.5 function calls per function
- Processing time: ~30 seconds

#### Validation Criteria
- ✅ Successfully parse fs/ext4/super.c (7,499 lines)
- ✅ Extract ~225 functions from super.c
- ✅ Identify call relationships accurately
- ✅ Handle both static and exported functions

#### Key Files Created
```
src/module_a/__init__.py
src/module_a/preprocessor.py  (256 lines)
src/module_a/parser.py        (257 lines)
src/module_a/extractor.py     (294 lines)
```

---

### Phase 3: Module B - Neo4j Graph Integration ✅ COMPLETE

**Duration**: Days 4-5
**Status**: ✅ Completed

#### Objectives
- Design graph schema for kernel code
- Implement Neo4j driver integration
- Build data ingestion pipeline
- Ingest fs/ext4 subsystem

#### Components Implemented

**1. schema.py (251 lines)**
- Graph node definitions (Function, TestCase, File, Subsystem)
- Relationship types (CALLS, COVERS, CONTAINS, BELONGS_TO)
- Cypher query generators
- Schema constraints and indexes

**Graph Schema**:
```cypher
// Nodes
(:Function {id, name, file_path, line_start, line_end, subsystem, is_static})
(:TestCase {id, name, file_path, test_suite})
(:File {id, path, subsystem, function_count})
(:Subsystem {id, name, path, file_count, function_count})

// Relationships
(:Function)-[:CALLS {call_site_line, file_path}]->(:Function)
(:TestCase)-[:COVERS {coverage_type}]->(:Function)
(:File)-[:CONTAINS]->(:Function)
(:File)-[:BELONGS_TO]->(:Subsystem)
```

**2. graph_store.py (364 lines)**
- Neo4j driver with connection management
- Batch upsert operations (1000 nodes/batch)
- Transaction-based write operations
- Query execution with result mapping
- Graph statistics and monitoring
- Helper methods for call graph traversal

**Key Features**:
```python
# Initialize connection
store = Neo4jGraphStore(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password123"
)

# Batch operations
store.upsert_nodes_batch(nodes, batch_size=1000)
store.upsert_relationships_batch(rels, batch_size=1000)

# Query helpers
callers = store.get_function_callers("ext4_map_blocks", max_depth=3)
callees = store.get_function_callees("ext4_map_blocks", max_depth=3)
```

**3. ingestion.py (349 lines)**
- End-to-end data ingestion pipeline
- Function call resolution (internal vs external)
- File structure and subsystem hierarchy creation
- Batch processing with progress logging
- Integration between Module A and Module B

**Key Features**:
```python
# Complete ingestion
ingestion = GraphIngestion(graph_store)
stats = ingestion.ingest_subsystem_complete(functions, calls)

# Or use convenience function
stats = ingest_from_extractor(
    kernel_root="/path/to/linux",
    subsystem_path="fs/ext4",
    graph_store=store
)
```

#### Ingestion Results - fs/ext4
- **1,121 Function nodes** (deduplication applied)
- **37 File nodes**
- **1 Subsystem node** (ext4)
- **2,254 CALLS relationships** (internal calls only)
- **37 BELONGS_TO relationships** (File → Subsystem)
- **1,136 CONTAINS relationships** (File → Function)

**Notes**:
- ~10,763 external calls not ingested (kernel functions outside ext4)
- 1,385 unresolved function calls (macros/external symbols)
- Total ingestion time: ~10 seconds
- Batch processing: 1000 items per transaction

#### Validation Criteria
- ✅ All ext4 functions stored in Neo4j
- ✅ Call chains traversable via Cypher queries
- ✅ File and subsystem hierarchy created
- ✅ Schema constraints and indexes applied

#### Sample Queries Working
```cypher
// Find function by name
MATCH (f:Function {name: 'ext4_map_blocks'}) RETURN f

// Find who calls a function
MATCH (caller:Function)-[:CALLS]->(f:Function {name: 'ext4_read_bh'})
RETURN caller.name

// Multi-hop call chains
MATCH path = (f:Function)-[:CALLS*1..3]->(target:Function)
WHERE target.name = 'ext4_map_blocks'
RETURN [n in nodes(path) | n.name] as chain
```

#### Key Files Created
```
src/module_b/__init__.py
src/module_b/schema.py        (251 lines)
src/module_b/graph_store.py   (364 lines)
src/module_b/ingestion.py     (349 lines)
```

---

### Phase 4: Module C - KUnit Test Mapper ⏳ PENDING

**Duration**: Day 6
**Status**: ⏳ Pending

#### Objectives
- Parse KUnit test files
- Map test cases to tested functions
- Create COVERS relationships in graph
- Analyze test coverage gaps

#### Components to Implement

**1. kunit_parser.py**
- Detect KUnit test files (*-test.c)
- Parse test suite definitions
- Extract test case names
- Identify test macros (KUNIT_CASE, KUNIT_ASSERT, etc.)

**Key Features**:
```python
# Find KUnit tests in subsystem
tests = find_kunit_tests("fs/ext4")
# Expected: ['inode-test.c', 'mballoc-test.c']

# Parse test file
suite = parse_kunit_file("fs/ext4/inode-test.c")
# Returns: test cases, assertions, function calls
```

**2. test_mapper.py**
- Map test functions to tested functions
- Analyze test coverage patterns
- Detect direct vs indirect coverage
- Generate coverage reports

**Mapping Strategy**:
```python
# Direct mapping: test calls function directly
test_inode_timestamp_decode() → ext4_decode_extra_time()

# Indirect mapping: test calls function indirectly
test_mb_generate_buddy() → ext4_mb_generate_buddy() → helper_funcs()

# Pattern detection:
# - test_<name>() usually tests <name>()
# - Analyze function calls within test
```

**3. coverage.py**
- Coverage analysis utilities
- Gap detection (functions without tests)
- Coverage quality metrics
- Test recommendation engine

#### Target Test Files (fs/ext4)
- `inode-test.c` (284 lines, 16 test cases)
  - Tests: `ext4_decode_extra_time()`
  - Parameterized tests for timestamps

- `mballoc-test.c` (993 lines, 7 test cases)
  - Tests: multi-block allocation functions
  - Uses static stubs for mocking

#### Expected Results
- Parse 2 KUnit test files
- Map ~23 test cases to functions
- Create COVERS relationships in Neo4j
- Identify ~217 uncovered functions (from stats)

#### Validation Criteria
- [ ] Parse KUnit test files successfully
- [ ] Map test cases to functions accurately
- [ ] Create COVERS relationships in graph
- [ ] Query: `MATCH (t:TestCase)-[:COVERS]->(f:Function) RETURN count(*)`

#### Key Files to Create
```
src/module_c/__init__.py
src/module_c/kunit_parser.py   (~200 lines)
src/module_c/test_mapper.py    (~250 lines)
src/module_c/coverage.py       (~150 lines)
tests/test_kunit_parser.py
tests/fixtures/sample_kunit_test.c
```

---

### Phase 5: Impact Analysis + LLM Reporting ⏳ PENDING

**Duration**: Days 7-8
**Status**: ⏳ Pending

#### Objectives
- Implement call chain traversal queries
- Identify test coverage for affected functions
- Integrate LLM for human-readable reports
- Build impact analysis API

#### Components to Implement

**1. queries.py**
- Cypher query templates for common patterns
- Call chain analysis (1-3 hops)
- Test coverage lookup
- Impact scope calculation

**Query Templates**:
```python
# Impact query
IMPACT_QUERY = """
MATCH (target:Function {name: $func_name})
MATCH path = (caller:Function)-[:CALLS*1..{depth}]->(target)
OPTIONAL MATCH (caller)<-[:COVERS]-(test:TestCase)
RETURN caller, test, length(path) as distance,
       [n in nodes(path) | n.name] as call_chain
ORDER BY distance, caller.name
"""

# Coverage gap query
COVERAGE_GAP_QUERY = """
MATCH (f:Function)
WHERE NOT (f)<-[:COVERS]-(:TestCase)
RETURN f.name, f.subsystem, f.is_static
ORDER BY f.subsystem, f.name
"""
```

**2. impact_analyzer.py**
- Execute impact analysis queries
- Aggregate results
- Calculate risk metrics
- Format data for LLM

**Key Features**:
```python
analyzer = ImpactAnalyzer(graph_store)

# Analyze impact of modifying a function
impact = analyzer.analyze_function("ext4_map_blocks")
# Returns: {
#   "direct_callers": [...],
#   "indirect_callers": [...],
#   "affected_functions": 127,
#   "test_coverage": {
#     "covered": 45,
#     "uncovered": 82
#   },
#   "risk_level": "high"
# }
```

**3. llm_reporter.py**
- LLM integration (OpenAI/Gemini/Claude)
- Prompt engineering for kernel analysis
- Human-readable report generation
- Multiple output formats

**LLM Integration**:
```python
reporter = LLMReporter(provider="openai", model="gpt-4")

# Generate report
report = reporter.generate_impact_report(
    target_function="ext4_map_blocks",
    impact_data=impact,
    format="markdown"
)

# Output:
# """
# ## Impact Analysis: ext4_map_blocks
#
# ### Summary
# Modifying `ext4_map_blocks` will affect 127 functions across 3 layers...
#
# ### Direct Impact (1-hop)
# - ext4_get_block() - Used in read operations
# - ext4_writepage() - Used in write operations
# ...
#
# ### Test Coverage
# ⚠️ WARNING: 64% of affected functions lack test coverage
# ...
#
# ### Recommendations
# 1. Run tests: mballoc-test, inode-test
# 2. Add tests for: ext4_writepage_trans_blocks
# ...
# """
```

**Supported LLM Providers**:
- OpenAI (GPT-4, GPT-4-turbo)
- Google (Gemini 1.5 Pro)
- Anthropic (Claude 3.5 Sonnet)
- Ollama (Local models)

#### Expected Features
- Multi-hop call chain analysis (1-3 levels)
- Test coverage correlation
- Risk assessment (low/medium/high)
- Actionable recommendations
- Multiple output formats (text, markdown, JSON)

#### Validation Criteria
- [ ] Query impact of modifying `ext4_map_blocks`
- [ ] Identify affected functions accurately
- [ ] Find test coverage gaps
- [ ] Generate readable LLM report
- [ ] Support multiple LLM providers

#### Key Files to Create
```
src/analysis/__init__.py
src/analysis/queries.py         (~150 lines)
src/analysis/impact_analyzer.py (~300 lines)
src/analysis/llm_reporter.py    (~250 lines)
tests/test_impact_analyzer.py
```

---

### Phase 6: CLI Interface & Configuration ⏳ PENDING

**Duration**: Day 9
**Status**: ⏳ Pending

#### Objectives
- Create unified CLI interface
- YAML configuration support
- Logging and error handling
- End-to-end pipeline orchestration

#### Components to Implement

**1. main.py**
- CLI entry point with Click
- Command routing
- Progress display with Rich
- Error handling

**CLI Commands**:
```bash
# Analyze a subsystem
kgraph analyze fs/ext4 --config config.yaml

# Query impact
kgraph impact ext4_map_blocks --depth 3 --llm

# Show statistics
kgraph stats

# Query call chains
kgraph calls ext4_map_blocks --callers --depth 2

# Test coverage
kgraph coverage fs/ext4 --gaps
```

**2. config.py**
- YAML configuration loading
- Environment variable support
- Configuration validation with Pydantic
- Default values

**Configuration Schema**:
```yaml
# config.yaml
kernel:
  root: /workspaces/ubuntu/linux-6.13
  subsystem: fs/ext4

preprocessing:
  enable_cpp: true
  kernel_config: .config

database:
  neo4j_url: bolt://localhost:7687
  neo4j_user: neo4j
  neo4j_password: ${NEO4J_PASSWORD}

llm:
  provider: openai  # openai, gemini, anthropic, ollama
  model: gpt-4
  api_key: ${OPENAI_API_KEY}
  temperature: 0.3

analysis:
  max_call_depth: 3
  include_indirect_calls: true
  risk_threshold: 0.7

logging:
  level: INFO
  file: kernel-graphrag.log
  format: detailed
```

**3. Logging & Error Handling**
- Structured logging
- Progress bars for long operations
- Graceful error recovery
- User-friendly error messages

#### Expected Features
- Intuitive CLI with `--help` for all commands
- Configuration via YAML or environment variables
- Progress indicators for long operations
- Colored output with Rich
- Comprehensive error messages

#### Validation Criteria
- [ ] Run: `kgraph analyze fs/ext4`
- [ ] Run: `kgraph impact ext4_map_blocks --llm`
- [ ] Configuration loaded from YAML
- [ ] All phases work end-to-end
- [ ] Proper error handling

#### Key Files to Create
```
src/main.py              (~400 lines)
src/config.py            (~200 lines)
src/utils/logger.py      (~100 lines)
examples/analyze_ext4.yaml
```

---

### Phase 7: Documentation & Multi-Subsystem ⏳ PENDING

**Duration**: Day 10
**Status**: ⏳ Pending

#### Objectives
- Comprehensive documentation
- Test with multiple subsystems
- Performance optimization
- Edge case handling

#### Deliverables

**1. Documentation**
- [x] DEVELOPMENT_PLAN.md (this document)
- [ ] README.md (comprehensive)
- [ ] docs/architecture.md
- [ ] docs/macro_handling.md
- [ ] docs/neo4j_setup.md
- [ ] docs/API.md
- [ ] docs/EXAMPLES.md

**2. Multi-Subsystem Testing**
Test with additional kernel subsystems:
- fs/btrfs (~100 files)
- net/ipv4 (~200 files)
- drivers/gpu/drm (~500 files)

**Validation Points**:
- [ ] Successfully analyze fs/btrfs
- [ ] Successfully analyze net/ipv4
- [ ] Handle cross-subsystem calls
- [ ] Performance acceptable for large subsystems

**3. Performance Optimization**
- Parallel parsing (multiprocessing)
- Graph query optimization
- Caching mechanisms
- Incremental updates

**4. Edge Cases**
- Function pointers
- Macro function calls
- Inline functions
- Template-like patterns
- Cross-subsystem dependencies

#### Validation Criteria
- [ ] Documentation complete and clear
- [ ] 3+ subsystems analyzed successfully
- [ ] Performance metrics documented
- [ ] Known limitations documented
- [ ] Installation guide tested

#### Key Files to Create/Update
```
README.md                       (comprehensive)
docs/architecture.md
docs/macro_handling.md
docs/neo4j_setup.md
docs/API.md
docs/EXAMPLES.md
examples/analyze_btrfs.yaml
examples/query_examples.md
```

---

## Success Criteria

### Functional Requirements
- ✅ Parse C source code from Linux kernel
- ✅ Extract function definitions and calls
- ✅ Store in Neo4j graph database
- ✅ Query call chains with Cypher
- [ ] Map KUnit tests to functions
- [ ] Generate AI-powered impact reports
- [ ] Provide CLI interface
- [ ] Support configurable subsystems

### Non-Functional Requirements
- [ ] Process ext4 (37 files) in < 60 seconds
- [ ] Query response time < 2 seconds
- [ ] Support subsystems up to 500 files
- [ ] Clear documentation
- [ ] < 10% false positives in call mapping
- [ ] API coverage > 80% in tests

### Quality Metrics
- Code coverage: Target 80%+
- Type hints: 100% on public APIs
- Documentation: All public functions
- Error handling: Graceful degradation
- Logging: Comprehensive for debugging

---

## Current Status (Phase 3 Complete)

### What Works Now ✅

**1. C Code Parsing**
```bash
KERNEL_ROOT=/path/to/linux python src/module_a/extractor.py fs/ext4
```
- Extracts 1,136 functions from fs/ext4
- Identifies 13,017 call relationships
- Handles 37 C source files

**2. Neo4j Graph Storage**
```bash
KERNEL_ROOT=/path/to/linux python src/module_b/ingestion.py fs/ext4
```
- Ingests complete subsystem into Neo4j
- Creates function, file, and subsystem nodes
- Establishes call relationships

**3. Graph Queries**
```python
from src.module_b.graph_store import Neo4jGraphStore

with Neo4jGraphStore() as store:
    # Find who calls a function
    callers = store.get_function_callers("ext4_map_blocks", max_depth=3)

    # Find what a function calls
    callees = store.get_function_callees("ext4_map_blocks", max_depth=3)

    # Get statistics
    stats = store.get_statistics()
```

**4. Data in Neo4j**
- 1,121 Function nodes
- 37 File nodes
- 1 Subsystem node
- 2,254 CALLS relationships
- Ready for traversal queries

### What's Next 🎯

**Immediate: Phase 4** (KUnit Test Mapping)
- Parse inode-test.c and mballoc-test.c
- Map 23 test cases to functions
- Create COVERS relationships

**Short-term: Phase 5** (Impact Analysis)
- Implement Cypher queries for impact
- Integrate LLM (GPT-4/Gemini)
- Generate human-readable reports

**Medium-term: Phases 6-7** (Polish)
- CLI interface
- Configuration management
- Documentation
- Multi-subsystem support

---

## Known Limitations

### Current Limitations
1. **Macro Preprocessing**: Requires kernel headers to be generated (make defconfig)
   - **Workaround**: Currently skipping preprocessing, parsing raw C
   - **Impact**: Some macro-generated functions may be missed

2. **External Functions**: Calls to kernel functions outside subsystem not fully tracked
   - **Current**: ~10,763 external calls not ingested
   - **Reason**: Target functions not in database
   - **Future**: Could expand to multi-subsystem analysis

3. **Function Pointers**: Static analysis can't resolve dynamic calls
   - **Current**: Not detected
   - **Future**: Could add "potential call" edges with low confidence

4. **Cross-file Dependencies**: Only tracks direct calls
   - **Current**: No data flow analysis
   - **Future**: Could add advanced static analysis

### Planned Improvements
- Macro preprocessing with proper kernel build
- Cross-subsystem dependency tracking
- Function pointer analysis
- Data flow analysis
- Performance optimization for large codebases

---

## Risk Assessment

### Technical Risks

**1. Kernel Macro Complexity** (Medium Risk)
- **Issue**: Linux kernel uses extensive macros
- **Mitigation**: Fallback to raw parsing, future: proper cpp integration
- **Status**: Mitigated

**2. Graph Database Scale** (Low Risk)
- **Issue**: Full kernel = ~30M LOC, might stress Neo4j
- **Mitigation**: Subsystem-focused analysis, batch processing
- **Status**: Monitoring

**3. LLM API Costs** (Low Risk)
- **Issue**: GPT-4 API costs for large reports
- **Mitigation**: Support Ollama (local), caching, configurable
- **Status**: Design includes local options

**4. Tree-sitter API Changes** (Low Risk - Mitigated)
- **Issue**: tree-sitter API versions incompatible
- **Mitigation**: Manual traversal instead of query API
- **Status**: Resolved

### Schedule Risks

**1. Scope Creep** (Medium Risk)
- **Mitigation**: Clear phase boundaries, MVP focus
- **Status**: Managed with 7-phase plan

**2. Neo4j Learning Curve** (Low Risk)
- **Mitigation**: Well-documented Cypher examples
- **Status**: Phase 3 complete successfully

---

## Dependencies

### Critical Dependencies
- Linux kernel source (6.13+)
- Neo4j database (5.14+)
- GCC (for preprocessing)
- Python 3.12+

### Python Package Dependencies
- tree-sitter, tree-sitter-c
- neo4j driver
- llama-index (graph stores)
- openai / google-generativeai
- click, rich, pyyaml
- pytest (testing)

### Development Environment
- Dev container with systemd
- Neo4j running as service
- Git for version control
- Adequate RAM (4GB+) for Neo4j

---

## Performance Targets

### Phase 3 Performance (Actual)
- **Extraction**: ~30 seconds for 37 files (1,136 functions)
- **Ingestion**: ~10 seconds for 1,136 nodes + relationships
- **Total**: ~40 seconds for complete fs/ext4 analysis

### Target Performance (Future)
- **Small subsystem** (< 50 files): < 60 seconds
- **Medium subsystem** (50-200 files): < 5 minutes
- **Large subsystem** (200-500 files): < 15 minutes
- **Query latency**: < 2 seconds for most queries
- **LLM report**: < 30 seconds

### Optimization Strategies
- Parallel parsing (multiprocessing)
- Batch Neo4j operations (already implemented)
- Query result caching
- Incremental updates (only changed files)

---

## Testing Strategy

### Unit Tests (Target: 80% coverage)
- Module A: Parser, extractor functions
- Module B: Graph operations, schema
- Module C: KUnit parser, mapper
- Module D: Impact analysis, queries

### Integration Tests
- End-to-end: Extract → Ingest → Query
- Multi-subsystem analysis
- LLM integration
- CLI commands

### Test Data
- Fixtures: Sample C files
- Real data: fs/ext4 subsystem (37 files)
- Edge cases: Function pointers, macros, templates

### Current Test Coverage
- Phase 1: Manual validation ✅
- Phase 2: Tested on fs/ext4 ✅
- Phase 3: Tested with Neo4j ✅
- Phases 4-7: Tests to be added ⏳

---

## Future Enhancements (Post-POC)

### Advanced Features
1. **Historical Analysis**
   - Git integration for change tracking
   - Historical impact analysis
   - Regression detection

2. **Advanced Static Analysis**
   - Data flow analysis
   - Taint analysis
   - Security vulnerability detection

3. **Web Dashboard**
   - Visual call graph explorer
   - Interactive impact analysis
   - Test coverage heatmaps
   - Similar to deepwiki-open project

4. **CI/CD Integration**
   - Pre-commit hooks
   - Automated impact reports
   - Test requirement recommendations

5. **Multi-Repository Support**
   - Out-of-tree kernel modules
   - Related userspace tools
   - Cross-repository analysis

6. **Performance Optimization**
   - Distributed parsing
   - Graph database sharding
   - Result caching
   - Incremental analysis

---

## Appendix

### Glossary

- **AST**: Abstract Syntax Tree
- **Cypher**: Neo4j query language
- **GraphRAG**: Graph-based Retrieval Augmented Generation
- **KUnit**: Linux kernel unit testing framework
- **LLM**: Large Language Model
- **Neo4j**: Graph database management system
- **POC**: Proof of Concept
- **tree-sitter**: Parser generator and incremental parsing library

### References

- Linux Kernel: https://kernel.org
- Neo4j Documentation: https://neo4j.com/docs/
- tree-sitter: https://tree-sitter.github.io/
- KUnit: https://www.kernel.org/doc/html/latest/dev-tools/kunit/
- Original Plan: User-provided implementation guide

### Repository Structure

```
kernel-graphrag-sentinel/
├── src/
│   ├── module_a/         # C Code Parser (Phase 2) ✅
│   │   ├── preprocessor.py
│   │   ├── parser.py
│   │   └── extractor.py
│   ├── module_b/         # Graph Database (Phase 3) ✅
│   │   ├── schema.py
│   │   ├── graph_store.py
│   │   └── ingestion.py
│   ├── module_c/         # KUnit Mapper (Phase 4) ⏳
│   │   ├── kunit_parser.py
│   │   ├── test_mapper.py
│   │   └── coverage.py
│   ├── analysis/         # Impact Analysis (Phase 5) ⏳
│   │   ├── queries.py
│   │   ├── impact_analyzer.py
│   │   └── llm_reporter.py
│   ├── main.py           # CLI (Phase 6) ⏳
│   ├── config.py         # Configuration (Phase 6) ⏳
│   └── utils/
├── scripts/
│   ├── install_neo4j.sh
│   └── setup_tree_sitter.sh
├── tests/
├── examples/
│   └── analyze_ext4.yaml
├── docs/
│   ├── DEVELOPMENT_PLAN.md  (this file)
│   └── ...
├── requirements.txt
├── .env.template
└── README.md
```

---

**Last Updated**: 2025-12-27
**Next Milestone**: Phase 4 - KUnit Test Mapping
**Estimated Completion**: Phase 7 by Day 10
