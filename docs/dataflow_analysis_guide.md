# Data Flow Analysis User Guide

**Module D - Variable Tracking and Data Flow Analysis**
**Kernel-GraphRAG Sentinel v0.2.0**

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [CLI Usage](#cli-usage)
5. [Python API](#python-api)
6. [Query Examples](#query-examples)
7. [Common Use Cases](#common-use-cases)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Module D provides intra-procedural data flow analysis for Linux kernel C code. It tracks how variables flow through functions, enabling security analysis, bug detection, and code understanding.

### What Can You Do?

- **Track variable definitions and uses** across functions
- **Analyze data flows** from sources to sinks
- **Identify security issues** (taint analysis, buffer overflows)
- **Understand dependencies** between variables
- **Trace parameter flows** through function bodies

### Key Features

- ✅ Variable extraction (parameters, locals, globals)
- ✅ Type information extraction
- ✅ Intra-procedural flow analysis
- ✅ Assignment and usage tracking
- ✅ Neo4j graph storage
- ✅ Cypher query interface

---

## Quick Start

### 1. Ingest Data Flows

```bash
# Ingest data flow for a subsystem
kgraph ingest-dataflow fs/ext4

# Or use full command
python src/main.py ingest-dataflow fs/ext4
```

### 2. Analyze Variable Flow

```bash
# Analyze a specific variable
kgraph dataflow inode --max-depth 5 --direction both

# Track buffer variable flows
kgraph dataflow buffer --function ext4_read_block --direction forward
```

### 3. Query the Graph

```bash
# Find all variables in a function
python src/main.py query "
MATCH (v:Variable)
WHERE v.scope = 'ext4_file_write_iter'
RETURN v.name, v.var_type, v.is_parameter
"
```

---

## Core Concepts

### Variable Types

Module D tracks three types of variables:

1. **Parameters** - Function parameters
   ```c
   int process_data(int input, char *buffer) {
       // input, buffer are parameters
   }
   ```

2. **Local Variables** - Variables declared in function scope
   ```c
   int process_data(int input) {
       int result = input * 2;  // result is local
       return result;
   }
   ```

3. **Global/Static Variables** - File or global scope
   ```c
   static int counter = 0;  // Static variable
   ```

### Data Flow Types

1. **Assignment Flow** - Variable A assigned to B
   ```c
   int a = 5;
   int b = a;  // Flow from a to b
   ```

2. **Operation Flow** - Variables used in expressions
   ```c
   int sum = a + b;  // Flow from a,b to sum
   ```

3. **Return Flow** - Variable flows to return value
   ```c
   return result;  // Flow from result to return
   ```

### Neo4j Schema

```
(Variable:Variable)
  - name: string
  - var_type: string (e.g., "int", "char*")
  - scope: string (function name)
  - file_path: string
  - line_number: int
  - is_parameter: boolean
  - is_pointer: boolean
  - is_static: boolean
  - initializer: string (optional)

(Variable)-[:FLOWS_TO]->(Variable)
  - flow_type: string ("assignment", "operation", "return")
  - line_number: int
  - context: string (code snippet)

(Variable)-[:DEFINES]->(Variable)
  - Indicates variable definition

(Variable)-[:USES]->(Variable)
  - Indicates variable usage
```

---

## CLI Usage

### Ingestion Commands

#### Ingest Data Flow for Subsystem

```bash
# Basic ingestion
kgraph ingest-dataflow fs/ext4

# With configuration
kgraph --config config.yaml ingest-dataflow fs/btrfs

# Ingest multiple subsystems
kgraph ingest-dataflow fs/ext4
kgraph ingest-dataflow fs/proc
kgraph ingest-dataflow mm/slub
```

### Analysis Commands

#### Analyze Variable Flow

```bash
# Analyze variable in all functions
kgraph dataflow inode

# Limit to specific function
kgraph dataflow buffer --function ext4_file_write_iter

# Control flow direction
kgraph dataflow count --direction forward   # What uses 'count'?
kgraph dataflow result --direction backward # What defines 'result'?
kgraph dataflow data --direction both       # Both directions

# Limit search depth
kgraph dataflow var --max-depth 3
```

### Query Commands

```bash
# Direct Cypher query
kgraph query "MATCH (v:Variable) RETURN count(v)"

# Multi-line query
kgraph query "
MATCH (v:Variable {is_parameter: true})
WHERE v.scope STARTS WITH 'ext4_'
RETURN v.scope, collect(v.name) as params
ORDER BY v.scope
LIMIT 10
"
```

---

## Python API

### Variable Extraction

```python
from src.module_d.variable_tracker import VariableTracker

# Initialize tracker
tracker = VariableTracker()

# Extract variables from file
defs, uses = tracker.extract_from_file("fs/ext4/inode.c")

# Process definitions
for var in defs:
    print(f"{var.name}: {var.var_type} in {var.scope}")
    if var.is_parameter:
        print(f"  -> Parameter")
    if var.initializer:
        print(f"  -> Initialized to: {var.initializer}")

# Process uses
for use in uses:
    print(f"{use.name} used in {use.function} at line {use.line_number}")
    print(f"  -> Context: {use.context}")
```

### Data Flow Building

```python
from src.module_d.flow_builder import FlowBuilder

# Initialize builder
builder = FlowBuilder()

# Build intra-procedural flows
flows, var_defs = builder.build_intra_procedural_flows("fs/ext4/inode.c")

# Process flows
for flow in flows:
    print(f"{flow.source_name} -> {flow.target_name}")
    print(f"  Type: {flow.flow_type}")
    print(f"  In function: {flow.source_scope}")
    print(f"  At line: {flow.line_number}")
```

### Neo4j Ingestion

```python
from src.module_d.flow_ingestion import DataFlowIngestion
from src.module_b.graph_store import Neo4jGraphStore

# Connect to Neo4j
store = Neo4jGraphStore(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password123"
)

# Initialize ingestion
ingestion = DataFlowIngestion(store)

# Setup schema (first time only)
ingestion.setup_schema()

# Ingest single file
stats = ingestion.ingest_file("fs/ext4/inode.c", subsystem="fs/ext4")
print(f"Ingested {stats['variables']} variables, {stats['flows']} flows")

# Ingest directory
stats = ingestion.ingest_directory("fs/ext4", subsystem="fs/ext4")
print(f"Processed {stats['files']} files")
print(f"Total variables: {stats['total_variables']}")

# Get statistics
stats = ingestion.get_variable_statistics()
print(f"Database contains {stats['total_variables']} variables")
```

---

## Query Examples

See [dataflow_query_examples.md](examples/dataflow_query_examples.md) for 22 comprehensive query examples.

### Quick Examples

#### 1. Find All Parameters in a Function

```cypher
MATCH (v:Variable {is_parameter: true})
WHERE v.scope = "ext4_file_write_iter"
RETURN v.name, v.var_type
ORDER BY v.line_number
```

#### 2. Track Data Flow from Parameter

```cypher
MATCH path = (param:Variable {is_parameter: true})-[:FLOWS_TO*1..5]->(v:Variable)
WHERE param.scope = "process_data" AND param.name = "input"
RETURN param.name, v.name, length(path) as depth
ORDER BY depth
```

#### 3. Find Buffer Variables

```cypher
MATCH (v:Variable)
WHERE v.var_type CONTAINS "char" OR v.name CONTAINS "buf"
RETURN v.name, v.var_type, v.scope, v.file_path
LIMIT 50
```

#### 4. Taint Analysis - Track User Input

```cypher
MATCH path = (source:Variable)-[:FLOWS_TO*1..7]->(sink:Variable)
WHERE source.name =~ ".*user.*" OR source.name =~ ".*input.*"
RETURN source.name, sink.name, length(path) as flow_depth
ORDER BY flow_depth DESC
LIMIT 20
```

---

## Common Use Cases

### 1. Security Taint Analysis

**Goal:** Find where user-controlled input flows to sensitive operations

```bash
# Step 1: Ingest the subsystem
kgraph ingest-dataflow fs/ext4

# Step 2: Query for taint flows
kgraph query "
MATCH path = (source:Variable)-[:FLOWS_TO*1..7]->(sink:Variable)
WHERE source.name =~ '.*user.*'
  AND (sink.name CONTAINS 'kmalloc' OR sink.name CONTAINS 'copy')
RETURN source.scope, source.name, sink.name, length(path)
ORDER BY length(path)
LIMIT 20
"
```

### 2. Buffer Overflow Detection

**Goal:** Find buffers and their size variables

```python
from src.module_d.variable_tracker import VariableTracker

tracker = VariableTracker()
defs, uses = tracker.extract_from_file("fs/ext4/inode.c")

# Find buffer declarations
buffers = [v for v in defs if 'buf' in v.name.lower() or 'char' in (v.var_type or '')]

# Find size variables
sizes = [v for v in defs if 'size' in v.name.lower() or 'len' in v.name.lower()]

# Correlate buffers with sizes in same function
for buf in buffers:
    related_sizes = [s for s in sizes if s.scope == buf.scope]
    print(f"Buffer: {buf.name} in {buf.scope}")
    for size in related_sizes:
        print(f"  Possible size: {size.name}")
```

### 3. Dead Variable Detection

**Goal:** Find variables that are defined but never used

```cypher
// Find variables with DEFINES but no USES or FLOWS_TO
MATCH (v:Variable)
WHERE NOT (v)-[:USES]->() AND NOT (v)-[:FLOWS_TO]->()
  AND v.is_parameter = false
RETURN v.name, v.scope, v.file_path, v.line_number
ORDER BY v.file_path, v.line_number
LIMIT 50
```

### 4. Parameter Flow Analysis

**Goal:** Understand how function parameters are used

```cypher
// Find all flows from a specific parameter
MATCH path = (param:Variable {is_parameter: true})-[:FLOWS_TO*]->(target:Variable)
WHERE param.scope = "ext4_file_write_iter" AND param.name = "iocb"
RETURN path
LIMIT 10
```

---

## Best Practices

### Ingestion Strategy

1. **Start Small** - Ingest one subsystem at a time
   ```bash
   kgraph ingest-dataflow fs/proc  # Small subsystem first
   ```

2. **Verify Schema** - Check schema creation succeeded
   ```bash
   kgraph query "SHOW CONSTRAINTS"
   ```

3. **Check Statistics** - Verify ingestion worked
   ```bash
   kgraph query "MATCH (v:Variable) RETURN count(v)"
   ```

### Query Optimization

1. **Use Indexes** - Schema creates these automatically
   ```cypher
   // Indexed queries are fast
   MATCH (v:Variable {name: "inode"})
   RETURN v
   ```

2. **Limit Depth** - Control path traversal depth
   ```cypher
   // Good - limited depth
   MATCH p = (a)-[:FLOWS_TO*1..5]->(b)

   // Bad - unlimited depth
   MATCH p = (a)-[:FLOWS_TO*]->(b)
   ```

3. **Filter Early** - Use WHERE clauses effectively
   ```cypher
   // Good - filter before traversal
   MATCH (v:Variable)
   WHERE v.scope = "specific_function"
   MATCH (v)-[:FLOWS_TO*]->(target)

   // Bad - filter after traversal
   MATCH (v)-[:FLOWS_TO*]->(target)
   WHERE v.scope = "specific_function"
   ```

### Analysis Workflow

1. **Ingest** → **Query** → **Analyze** → **Iterate**

```bash
# 1. Ingest
kgraph ingest-dataflow fs/ext4

# 2. Explore
kgraph query "MATCH (v:Variable) RETURN v.scope, count(v) GROUP BY v.scope LIMIT 10"

# 3. Deep dive
kgraph dataflow inode --function ext4_file_write_iter

# 4. Refine query based on findings
kgraph query "<your specific query>"
```

---

## Troubleshooting

### Issue: No Variables Found

**Problem:** Ingestion completed but queries return no results

**Solutions:**
```bash
# Check if data exists
kgraph query "MATCH (v:Variable) RETURN count(v)"

# Verify file was processed
kgraph query "MATCH (v:Variable) WHERE v.file_path CONTAINS 'inode.c' RETURN count(v)"

# Re-ingest with verbose output
kgraph ingest-dataflow fs/ext4 --verbose
```

### Issue: Parsing Errors

**Problem:** Many "Parsing resulted in errors" warnings

**Causes:**
- Preprocessor macros not expanded
- Complex C syntax (GNU extensions)
- Incomplete includes

**Solutions:**
```bash
# Enable C preprocessor (requires kernel config)
export ENABLE_CPP_PREPROCESSING=true
kgraph ingest-dataflow fs/ext4

# Or configure in YAML
# preprocessing:
#   enable_cpp: true
#   kernel_config: /path/to/.config
```

### Issue: Slow Queries

**Problem:** Queries take too long

**Solutions:**
```cypher
-- Use LIMIT
MATCH (v:Variable)-[:FLOWS_TO*]->(t:Variable)
RETURN v, t
LIMIT 100

-- Limit path depth
MATCH path = (v)-[:FLOWS_TO*1..3]->(t)  -- Max 3 hops

-- Use indexes (automatic)
MATCH (v:Variable {name: "specific_var"})  -- Fast with index

-- Profile query
PROFILE MATCH (v:Variable) RETURN v
```

### Issue: Out of Memory

**Problem:** Neo4j runs out of memory during ingestion

**Solutions:**
```bash
# Process smaller batches
kgraph ingest-dataflow fs/ext4/file.c  # Single file

# Increase Neo4j heap (neo4j.conf)
# dbms.memory.heap.initial_size=2g
# dbms.memory.heap.max_size=4g

# Process subsystems sequentially, not all at once
kgraph ingest-dataflow fs/ext4
# Wait for completion, then:
kgraph ingest-dataflow fs/btrfs
```

---

## Advanced Topics

### Custom Flow Analysis

Create custom flow analysis by combining Module D with your own code:

```python
from src.module_d.variable_tracker import VariableTracker
from src.module_d.flow_builder import FlowBuilder

class CustomAnalyzer:
    def __init__(self):
        self.tracker = VariableTracker()
        self.builder = FlowBuilder()

    def find_security_issues(self, file_path):
        """Find potential security issues."""
        defs, uses = self.tracker.extract_from_file(file_path)
        flows, _ = self.builder.build_intra_procedural_flows(file_path)

        # Find user-controlled inputs
        user_inputs = [v for v in defs if 'user' in v.name.lower()]

        # Find sensitive operations
        sensitive_uses = [u for u in uses if any(
            keyword in u.context.lower()
            for keyword in ['kmalloc', 'copy', 'memcpy']
        )]

        # Correlate
        for ui in user_inputs:
            for su in sensitive_uses:
                if ui.scope == su.function:
                    print(f"⚠️ User input '{ui.name}' used in '{su.context}'")
                    print(f"   Function: {ui.scope} at line {su.line_number}")

# Usage
analyzer = CustomAnalyzer()
analyzer.find_security_issues("fs/ext4/inode.c")
```

---

## Further Reading

- **Module D Source Code**: [src/module_d/](../src/module_d/)
- **Query Examples**: [dataflow_query_examples.md](examples/dataflow_query_examples.md)
- **Example Script**: [dataflow_example.py](examples/dataflow_example.py)
- **v0.2.0 Progress**: [v0.2.0_progress.md](v0.2.0_progress.md)
- **Neo4j Setup**: [neo4j_setup.md](neo4j_setup.md)

---

## Support

**Documentation:**
- [Project README](../README.md)
- [Development Plan](DEVELOPMENT_PLAN.md)
- [Architecture](architecture.md)

**GitHub:**
- Issue Tracker: [Create Issue](https://github.com/yourusername/kernel-graphrag-sentinel/issues)

---

**Last Updated:** 2025-12-28
**Version:** v0.2.0
**Module:** D - Data Flow Analysis
