# Kernel-GraphRAG Sentinel Architecture

**Version**: 0.1.0
**Last Updated**: 2025-12-27

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Module Design](#module-design)
4. [Data Flow](#data-flow)
5. [Technology Stack](#technology-stack)
6. [Design Decisions](#design-decisions)
7. [Performance Considerations](#performance-considerations)
8. [Extension Points](#extension-points)

---

## System Overview

Kernel-GraphRAG Sentinel is a static analysis tool for Linux kernel code that combines tree-sitter parsing, graph database storage, and impact analysis to help developers understand code changes.

### Core Capabilities

- **Static Code Analysis**: Extract functions, calls, and relationships from C source
- **Graph Representation**: Store code structure in Neo4j for efficient traversal
- **Test Coverage Mapping**: Link KUnit tests to tested functions
- **Impact Analysis**: Identify affected code paths when modifying functions
- **Risk Assessment**: Evaluate change risk based on usage and test coverage

### Design Philosophy

1. **Subsystem-Focused**: Analyze specific kernel subsystems rather than the entire codebase
2. **Incremental**: Support adding multiple subsystems to the same database
3. **Pragmatic**: Balance accuracy with performance (e.g., optional preprocessing)
4. **Extensible**: Modular design for adding new analysis capabilities

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ CLI (Click)  │  │ YAML Config  │  │ Python API   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Application Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Extraction   │  │ Test Mapping │  │ Impact       │      │
│  │ Pipeline     │  │ Pipeline     │  │ Analyzer     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Core Modules Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Module A    │  │  Module B    │  │  Module C    │      │
│  │  C Parser    │  │  Graph Store │  │  Test Mapper │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Data Storage Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Neo4j Graph  │  │ File System  │  │ Kernel Source│      │
│  │ Database     │  │ (temp files) │  │ Tree         │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## Module Design

### Module A: C Code Parser

**Location**: `src/module_a/`

**Purpose**: Extract structured data from Linux kernel C source code

**Components**:

```
module_a/
├── preprocessor.py    # GCC preprocessor integration
├── parser.py          # tree-sitter C parser wrapper
└── extractor.py       # Function/call extraction orchestration
```

**Key Classes**:

- **`KernelPreprocessor`**: Runs `gcc -E` with kernel-specific includes
- **`CParser`**: Wraps tree-sitter C parser, provides AST traversal
- **`FunctionExtractor`**: High-level API for extracting functions and calls

**Data Structures**:

```python
@dataclass
class FunctionNode:
    name: str
    file_path: str
    line_start: int
    line_end: int
    subsystem: str
    is_static: bool

@dataclass
class CallEdge:
    caller: str          # Function making the call
    callee: str          # Function being called
    call_site_line: int
    file_path: str
```

**Algorithm** (Extraction Pipeline):

1. **Preprocessing** (optional):
   - Extract kernel include paths from Makefile
   - Run `gcc -E -D__KERNEL__` with includes
   - Return preprocessed C code

2. **Parsing**:
   - Parse C code into AST using tree-sitter
   - Handle parse errors gracefully (AST may be partial)

3. **Function Extraction**:
   - Query AST for `function_definition` nodes
   - Extract name, location, static/exported status
   - Create `FunctionNode` objects

4. **Call Extraction**:
   - Query AST for `call_expression` nodes
   - Determine containing function via line ranges
   - Create `CallEdge` objects

5. **Statistics**:
   - Count functions, calls, files processed
   - Identify uncalled functions
   - Calculate averages

**Performance**:
- ~30 seconds for 37 files (ext4)
- ~60 seconds for 65 files (btrfs)
- Scales linearly with file count

---

### Module B: Graph Database

**Location**: `src/module_b/`

**Purpose**: Store and query code relationships in Neo4j graph database

**Components**:

```
module_b/
├── schema.py          # Graph schema definitions
├── graph_store.py     # Neo4j driver wrapper
└── ingestion.py       # Bulk data ingestion pipeline
```

**Graph Schema**:

```cypher
// Nodes
(:Function {
    id: String,           // Unique identifier
    name: String,         // Function name
    file_path: String,    // Full path to source file
    line_start: Integer,  // Starting line number
    line_end: Integer,    // Ending line number
    subsystem: String,    // Subsystem name (e.g., "ext4")
    is_static: Boolean    // Static vs exported
})

(:TestCase {
    id: String,
    name: String,
    file_path: String,
    test_suite: String
})

(:File {
    id: String,
    path: String,
    subsystem: String,
    function_count: Integer
})

(:Subsystem {
    id: String,
    name: String,
    path: String,
    file_count: Integer,
    function_count: Integer
})

// Relationships
(:Function)-[:CALLS {
    call_site_line: Integer,
    file_path: String
}]->(:Function)

(:TestCase)-[:COVERS {
    coverage_type: String  // "direct" or "indirect"
}]->(:Function)

(:File)-[:CONTAINS]->(:Function)

(:File)-[:BELONGS_TO]->(:Subsystem)
```

**Indexes**:

```cypher
CREATE INDEX func_name_idx FOR (f:Function) ON (f.name);
CREATE INDEX func_subsystem_idx FOR (f:Function) ON (f.subsystem);
CREATE INDEX func_id_idx FOR (f:Function) ON (f.id);
CREATE CONSTRAINT func_id_unique FOR (f:Function) REQUIRE f.id IS UNIQUE;
```

**Key Classes**:

- **`Neo4jGraphStore`**: Connection management, batch operations, queries
- **`GraphIngestion`**: Orchestrates data ingestion from Module A
- **`GraphSchema`**: Defines node/relationship types and constraints

**Ingestion Pipeline**:

1. **Initialize Schema**:
   - Create constraints and indexes
   - Ensure unique IDs

2. **Ingest File Structure**:
   - Create `File` and `Subsystem` nodes
   - Create `BELONGS_TO` relationships

3. **Ingest Functions**:
   - Batch upsert `Function` nodes (1000 at a time)
   - Create `CONTAINS` relationships (File → Function)

4. **Ingest Calls**:
   - Resolve callee names to function IDs
   - Filter external/unresolved calls
   - Batch upsert `CALLS` relationships

5. **Return Statistics**:
   - Functions ingested, calls ingested, unresolved calls

**Performance**:
- Batch size: 1000 nodes/relationships per transaction
- ~10 seconds for 2,631 functions + 27,500 calls (btrfs)
- Writes are transactional (all-or-nothing per batch)

---

### Module C: KUnit Test Mapper

**Location**: `src/module_c/`

**Purpose**: Map KUnit test cases to the functions they test

**Components**:

```
module_c/
├── kunit_parser.py    # Parse KUnit test files
└── test_mapper.py     # Map tests to functions
```

**Mapping Strategy**:

1. **Find Test Files**:
   - Look for `*-test.c` files in subsystem
   - Parse with tree-sitter (same parser as Module A)

2. **Extract Test Cases**:
   - Find `KUNIT_CASE(test_name)` macros
   - Extract test function definitions

3. **Identify Tested Functions**:
   - Analyze function calls within test body
   - Apply heuristics:
     - `test_foo()` likely tests `foo()`
     - Direct function calls in test are covered
   - Filter out test infrastructure calls (KUNIT_ASSERT, etc.)

4. **Create COVERS Relationships**:
   - TestCase → Function edges in Neo4j
   - Mark coverage type (direct/indirect)

**Limitations**:
- Static analysis only (no execution)
- May miss indirect coverage through helpers
- Requires clear naming conventions

---

### Impact Analysis Module

**Location**: `src/analysis/`

**Purpose**: Analyze the impact of modifying a function

**Components**:

```
analysis/
├── queries.py           # Cypher query templates
└── impact_analyzer.py   # Analysis orchestration
```

**Analysis Algorithm**:

1. **Find Target Function**:
   ```cypher
   MATCH (f:Function {name: $func_name})
   RETURN f
   ```

2. **Find Direct Callers** (1-hop):
   ```cypher
   MATCH (caller)-[:CALLS]->(f)
   RETURN caller
   ```

3. **Find Indirect Callers** (multi-hop):
   ```cypher
   MATCH path = (caller)-[:CALLS*2..N]->(f)
   RETURN caller, path, length(path) as depth
   ```

4. **Find Direct Callees**:
   ```cypher
   MATCH (f)-[:CALLS]->(callee)
   RETURN callee
   ```

5. **Find Indirect Callees**:
   ```cypher
   MATCH path = (f)-[:CALLS*2..N]->(callee)
   RETURN callee, path, length(path) as depth
   ```

6. **Find Test Coverage**:
   ```cypher
   // Direct coverage
   MATCH (test:TestCase)-[:COVERS]->(f)
   RETURN test

   // Indirect coverage (tests covering callers)
   MATCH (test)-[:COVERS]->(caller)-[:CALLS*1..N]->(f)
   RETURN test
   ```

7. **Calculate Risk**:
   - **CRITICAL**: Many callers (>100), no tests
   - **HIGH**: Many callers (>50), few tests
   - **MEDIUM**: Some callers (10-50), some tests
   - **LOW**: Few callers (<10), good test coverage

**Output** (`ImpactResult` dataclass):

```python
@dataclass
class ImpactResult:
    function_name: str
    file_path: str
    line_start: int
    subsystem: str

    direct_callers: List[CallerInfo]
    indirect_callers: List[CallerInfo]
    direct_callees: List[CalleeInfo]
    indirect_callees: List[CalleeInfo]

    covering_tests: List[TestInfo]
    indirect_covering_tests: List[TestInfo]

    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    call_chain_count: int
```

**Report Generation**:
- Format as text with sections
- Limit output (e.g., show first 15 items, "+ N more")
- Include call chains with depth indicators

---

## Data Flow

### 1. Ingestion Flow

```
Kernel Source Files (*.c)
    │
    ├─> Module A: Preprocessor (optional)
    │       │
    │       └─> Preprocessed C code
    │
    ├─> Module A: Parser (tree-sitter)
    │       │
    │       └─> AST (Abstract Syntax Tree)
    │
    ├─> Module A: Extractor
    │       │
    │       └─> FunctionNode[], CallEdge[]
    │
    └─> Module B: Ingestion Pipeline
            │
            ├─> Create File/Subsystem nodes
            ├─> Create Function nodes (batched)
            ├─> Create CALLS relationships (batched)
            │
            └─> Neo4j Graph Database
```

### 2. Test Mapping Flow

```
KUnit Test Files (*-test.c)
    │
    ├─> Module C: KUnit Parser
    │       │
    │       └─> TestCase objects
    │
    ├─> Module C: Test Mapper
    │       │
    │       └─> Test-to-Function mappings
    │
    └─> Module B: Graph Store
            │
            └─> Create COVERS relationships
```

### 3. Analysis Flow

```
User Query: "analyze ext4_map_blocks"
    │
    ├─> Analysis Module: Impact Analyzer
    │       │
    │       ├─> Query 1: Find target function
    │       ├─> Query 2: Find callers (1-N hops)
    │       ├─> Query 3: Find callees (1-N hops)
    │       ├─> Query 4: Find test coverage
    │       │
    │       └─> Aggregate results → ImpactResult
    │
    └─> Format report
            │
            └─> Display to user (CLI)
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.12+ | Application development |
| Parser | tree-sitter-c | 0.23.5 | C code AST parsing |
| Database | Neo4j | 5.14+ | Graph storage and querying |
| Preprocessor | GCC (cpp) | - | Macro expansion |
| CLI | Click | 8.1+ | Command-line interface |
| Config | PyYAML | 6.0+ | Configuration management |

### Python Dependencies

**Parsing**:
- `tree-sitter`: Parser framework
- `tree-sitter-c`: C language grammar

**Graph Database**:
- `neo4j`: Python driver for Neo4j
- Cypher query language

**CLI & Config**:
- `click`: CLI framework
- `pyyaml`: YAML parsing
- `python-dotenv`: Environment variables

**Utilities**:
- `dataclasses`: Data structures
- `logging`: Structured logging
- `pathlib`: Path manipulation

### External Dependencies

- **Linux Kernel Source**: Target codebase (6.13+ tested)
- **Neo4j Server**: Running on `bolt://localhost:7687`
- **GCC**: For preprocessing (optional but recommended)

---

## Design Decisions

### 1. Why tree-sitter Over Other Parsers?

**Decision**: Use tree-sitter for C parsing

**Alternatives Considered**:
- **libclang**: More accurate but heavyweight, requires compilation database
- **pycparser**: Pure Python but struggles with kernel macros
- **regex/text parsing**: Fast but error-prone

**Rationale**:
- tree-sitter is fault-tolerant (partial AST on errors)
- No compilation database required
- Fast enough for our use case
- Can parse raw C without full preprocessing

**Trade-offs**:
- Less semantic understanding than libclang
- May miss macro-generated code without preprocessing

---

### 2. Why Neo4j Over Relational DB?

**Decision**: Use Neo4j graph database

**Alternatives Considered**:
- **PostgreSQL with recursive CTEs**: Can do graph queries but slower
- **SQLite**: Lightweight but poor for graph traversal
- **In-memory graph**: Fast but not persistent

**Rationale**:
- Call chains are inherently graph-structured
- Cypher queries for traversal are intuitive
- Multi-hop queries (`CALLS*1..3`) are concise
- Good performance for graph operations

**Trade-offs**:
- Requires separate database server
- Higher memory usage than SQLite
- Overkill for simple queries

---

### 3. Why Optional Preprocessing?

**Decision**: Make GCC preprocessing optional (skip by default)

**Rationale**:
- Kernel preprocessing requires full build environment
- Preprocessing is slow (~2-3x parsing time)
- Raw parsing catches most functions
- Can enable for accuracy when needed

**Impact**:
- Faster default behavior
- May miss macro-generated functions
- User can opt-in with `--enable-preprocessing`

---

### 4. Why Subsystem-Focused?

**Decision**: Analyze specific subsystems, not entire kernel

**Rationale**:
- Full kernel is 30M+ LOC (too large)
- Developers typically work on one subsystem
- Subsystem boundaries are well-defined
- Can add multiple subsystems incrementally

**Implementation**:
- Subsystem = directory path (e.g., `fs/ext4`)
- Auto-detect files in directory
- Support cross-subsystem calls (marked as external)

---

### 5. Why Batch Ingestion?

**Decision**: Batch Neo4j writes (1000 items per transaction)

**Rationale**:
- Neo4j write latency is ~10ms per transaction
- Batching reduces total time by 100x+
- Balance between memory and performance

**Trade-offs**:
- All-or-nothing per batch (transaction semantics)
- Slightly more complex error handling

---

## Performance Considerations

### Bottlenecks

1. **Parsing**: CPU-bound, scales with file size
   - Mitigation: Parallel parsing (future work)

2. **Neo4j Writes**: Network/disk I/O
   - Mitigation: Batch writes (1000/transaction)

3. **Call Resolution**: Many small queries
   - Mitigation: Build in-memory function ID map first

### Scalability

**Tested Workloads**:
- ext4: 37 files, 1,121 functions → ~40 seconds
- btrfs: 65 files, 2,631 functions → ~70 seconds
- Combined: 102 files, 3,746 functions in database

**Projected Scaling**:
- Small subsystem (< 50 files): < 1 minute
- Medium subsystem (50-200 files): 2-5 minutes
- Large subsystem (200-500 files): 5-15 minutes

**Optimization Opportunities**:
- Parallel file parsing (use multiprocessing)
- Preprocessing caching (cache preprocessed files)
- Graph query optimization (add more indexes)

---

## Extension Points

### Adding New Node Types

Example: Add struct definitions

1. **Define Schema** (`src/module_b/schema.py`):
   ```python
   class StructNode:
       id: str
       name: str
       file_path: str
       fields: List[str]
   ```

2. **Extract Data** (`src/module_a/extractor.py`):
   - Add tree-sitter query for `struct_specifier`
   - Create `StructNode` objects

3. **Ingest** (`src/module_b/ingestion.py`):
   - Add `ingest_structs()` method
   - Create relationships (e.g., `DEFINES`)

### Adding New Analysis Types

Example: Data flow analysis

1. **Define Queries** (`src/analysis/queries.py`):
   ```python
   DATA_FLOW_QUERY = """
   MATCH path = (source:Function)-[:CALLS*]->(sink:Function)
   WHERE source.name = $source AND sink.name = $sink
   RETURN path
   """
   ```

2. **Implement Analyzer** (`src/analysis/data_flow_analyzer.py`):
   - Create `DataFlowAnalyzer` class
   - Execute queries, aggregate results

3. **Add CLI Command** (`src/main.py`):
   - Add `@cli.command()` for new analysis
   - Wire up analyzer

### Adding LLM Integration

See `src/config.py` for LLM configuration structure. Future work:

1. Integrate OpenAI/Gemini/Claude API clients
2. Create prompt templates for impact analysis
3. Generate natural language reports from `ImpactResult`
4. Add `--llm` flag to `analyze` command

---

## Future Architecture Enhancements

### Short-term (v0.2.0)

- **LLM Reports**: Natural language impact summaries
- **Web UI**: Interactive graph visualization
- **Parallel Parsing**: Use multiprocessing for files

### Medium-term (v0.3.0)

- **Incremental Updates**: Only re-parse changed files
- **Cross-Subsystem Analysis**: Track dependencies between subsystems
- **Data Flow**: Variable/struct field flow analysis

### Long-term (v0.4.0+)

- **Historical Analysis**: Git integration for change tracking
- **Security Analysis**: Taint tracking, vulnerability detection
- **IDE Integration**: VS Code / Neovim plugins

---

## References

- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/)
- [tree-sitter Documentation](https://tree-sitter.github.io/)
- [Linux Kernel Coding Style](https://www.kernel.org/doc/html/latest/process/coding-style.html)
- [KUnit Testing Guide](https://www.kernel.org/doc/html/latest/dev-tools/kunit/)
