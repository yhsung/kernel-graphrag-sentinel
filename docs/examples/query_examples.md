# Query Examples

This document provides practical examples of using Kernel-GraphRAG Sentinel for various kernel code analysis tasks.

---

## Table of Contents

1. [CLI Commands](#cli-commands)
2. [Common Analysis Workflows](#common-analysis-workflows)
3. [Neo4j Cypher Queries](#neo4j-cypher-queries)
4. [Python API Examples](#python-api-examples)

---

## CLI Commands

### Basic Subsystem Analysis

```bash
# Ingest ext4 filesystem code
python3 src/main.py ingest fs/ext4

# Ingest with database reset
python3 src/main.py ingest fs/ext4 --clear-db

# Skip preprocessing for faster parsing
python3 src/main.py ingest fs/ext4 --skip-preprocessing

# Complete pipeline (ingest + map tests + stats)
python3 src/main.py pipeline fs/ext4
```

### Function Impact Analysis

```bash
# Analyze impact of modifying a function
python3 src/main.py analyze ext4_map_blocks

# Deeper analysis (up to 5 hops in call chain)
python3 src/main.py analyze ext4_map_blocks --max-depth 5

# Save report to file
python3 src/main.py analyze ext4_map_blocks --output impact_report.txt

# Analyze critical allocation function
python3 src/main.py analyze ext4_mb_new_blocks_simple --max-depth 3
```

### Test Coverage Mapping

```bash
# Map KUnit tests for ext4
python3 src/main.py map-tests fs/ext4

# Map tests for btrfs filesystem
python3 src/main.py map-tests fs/btrfs
```

### Database Statistics and Queries

```bash
# Show database statistics
python3 src/main.py stats

# Find most frequently called functions
python3 src/main.py top-functions

# Top functions with at least 10 callers
python3 src/main.py top-functions --min-callers 10 --limit 50

# Top functions in specific subsystem
python3 src/main.py top-functions --subsystem ext4
```

### Configuration

```bash
# Generate configuration template
python3 src/main.py init-config --output my-config.yaml

# Use custom configuration
python3 src/main.py --config my-config.yaml pipeline fs/ext4

# Override kernel root path
python3 src/main.py --kernel-root /path/to/linux pipeline fs/ext4

# Enable verbose logging
python3 src/main.py -v pipeline fs/ext4
```

---

## Common Analysis Workflows

### Workflow 1: Before Modifying a Function

**Scenario**: You need to modify `ext4_map_blocks` and want to understand the impact.

```bash
# Step 1: Ensure subsystem is ingested
python3 src/main.py pipeline fs/ext4

# Step 2: Analyze the function
python3 src/main.py analyze ext4_map_blocks --max-depth 3

# Step 3: Review the impact report
# - Check how many functions will be affected
# - Identify which tests cover this function
# - Determine risk level

# Step 4: Run recommended tests after making changes
cd /path/to/linux-6.13
./tools/testing/kunit/kunit.py run --kunitconfig=fs/ext4
```

**Expected Output**:
```
IMPACT ANALYSIS: ext4_map_blocks
================================================================================
File: /workspaces/ubuntu/linux-6.13/fs/ext4/inode.c

SUMMARY
  Direct callers:       22
  Indirect callers:     45 (2-3 hops)
  Direct test coverage: 0
  Indirect test coverage: 3
  Total call chains:    67

RISK ASSESSMENT
  Risk Level: HIGH (widely used, limited test coverage)
================================================================================
```

### Workflow 2: Assessing Test Coverage

**Scenario**: You want to identify critical functions that lack test coverage.

```bash
# Step 1: Analyze entire subsystem
python3 src/main.py pipeline fs/ext4

# Step 2: Find most-called functions
python3 src/main.py top-functions --min-callers 15

# Step 3: For each critical function, check coverage
python3 src/main.py analyze ext4_get_block
python3 src/main.py analyze ext4_free_blocks
python3 src/main.py analyze ext4_read_bh

# Step 4: Identify functions that need tests
# Look for HIGH risk + zero test coverage
```

### Workflow 3: Analyzing a New Subsystem

**Scenario**: You're working on a different kernel subsystem.

```bash
# Example: Network IPv4 stack
export KERNEL_ROOT=/path/to/linux-6.13

# Ingest the subsystem
python3 src/main.py ingest net/ipv4 --skip-preprocessing

# Map tests (if KUnit tests exist)
python3 src/main.py map-tests net/ipv4

# Explore statistics
python3 src/main.py stats

# Find hotspots
python3 src/main.py top-functions --subsystem ipv4

# Example: btrfs filesystem
python3 src/main.py pipeline fs/btrfs
python3 src/main.py analyze btrfs_alloc_chunk --max-depth 4
```

### Workflow 4: Understanding Call Chains

**Scenario**: You want to trace how a function is ultimately called.

```bash
# Analyze with maximum depth
python3 src/main.py analyze ext4_mb_new_blocks_simple --max-depth 5

# Example output shows call chains:
# Chain 1: sys_write → vfs_write → ext4_file_write_iter →
#          ext4_da_write_begin → ext4_map_blocks →
#          ext4_ext_map_blocks → ext4_mb_new_blocks →
#          ext4_mb_new_blocks_simple

# This tells you:
# - User syscall: write()
# - VFS layer involvement
# - ext4-specific path
# - Allocation logic
```

### Workflow 5: Cross-Subsystem Analysis

**Scenario**: Understand interactions between subsystems.

```bash
# Ingest multiple related subsystems
python3 src/main.py ingest fs/ext4 --skip-preprocessing
python3 src/main.py ingest block --skip-preprocessing
python3 src/main.py ingest mm --skip-preprocessing

# Analyze a function that crosses boundaries
python3 src/main.py analyze ext4_submit_bio --max-depth 3

# This reveals:
# - ext4 → block layer interactions
# - Memory management involvement
# - I/O scheduler dependencies
```

---

## Neo4j Cypher Queries

### Direct Database Access

Connect to Neo4j Browser at `http://localhost:7474` (credentials: neo4j/password123)

### Query 1: Find a Specific Function

```cypher
// Find function by name
MATCH (f:Function {name: 'ext4_map_blocks'})
RETURN f.name, f.file_path, f.line_start, f.line_end, f.subsystem
```

### Query 2: Find All Callers of a Function

```cypher
// Direct callers (1-hop)
MATCH (caller:Function)-[:CALLS]->(f:Function {name: 'ext4_map_blocks'})
RETURN caller.name AS caller,
       caller.file_path AS file,
       caller.line_start AS line
ORDER BY caller.name
```

### Query 3: Multi-Hop Call Chains

```cypher
// Find all paths up to 3 hops deep
MATCH path = (caller:Function)-[:CALLS*1..3]->(f:Function {name: 'ext4_decode_extra_time'})
RETURN [node in nodes(path) | node.name] AS call_chain,
       length(path) AS depth,
       caller.name AS ultimate_caller
ORDER BY depth, ultimate_caller
LIMIT 20
```

### Query 4: Find Functions Without Tests

```cypher
// Functions with no test coverage
MATCH (f:Function)
WHERE NOT (f)<-[:COVERS]-(:TestCase)
RETURN f.name, f.file_path, f.subsystem
ORDER BY f.subsystem, f.name
LIMIT 50
```

### Query 5: Test Coverage Statistics

```cypher
// How many functions are covered by tests?
MATCH (f:Function)
OPTIONAL MATCH (f)<-[:COVERS]-(t:TestCase)
WITH f, count(t) AS test_count
RETURN
    f.subsystem AS subsystem,
    count(f) AS total_functions,
    sum(CASE WHEN test_count > 0 THEN 1 ELSE 0 END) AS covered_functions,
    sum(test_count) AS total_test_coverage
```

### Query 6: Find Highly-Connected Functions

```cypher
// Functions with many callers (hotspots)
MATCH (f:Function)<-[r:CALLS]-()
WITH f, count(r) AS caller_count
WHERE caller_count >= 10
RETURN f.name, f.file_path, caller_count
ORDER BY caller_count DESC
LIMIT 20
```

### Query 7: Find Leaf Functions

```cypher
// Functions that don't call anything else (leaf nodes)
MATCH (f:Function)
WHERE NOT (f)-[:CALLS]->()
RETURN f.name, f.file_path, f.subsystem
ORDER BY f.subsystem, f.name
LIMIT 30
```

### Query 8: Test Case Details

```cypher
// What does a specific test cover?
MATCH (t:TestCase {name: 'test_inode_timestamp_decode'})-[:COVERS]->(f:Function)
RETURN t.name AS test,
       t.file_path AS test_file,
       collect(f.name) AS tested_functions
```

### Query 9: Subsystem Statistics

```cypher
// Statistics per subsystem
MATCH (s:Subsystem)<-[:BELONGS_TO]-(file:File)
MATCH (file)-[:CONTAINS]->(f:Function)
OPTIONAL MATCH (f)<-[:COVERS]-(t:TestCase)
RETURN
    s.name AS subsystem,
    count(DISTINCT file) AS files,
    count(DISTINCT f) AS functions,
    count(DISTINCT t) AS test_cases
```

### Query 10: Static vs Exported Functions

```cypher
// Count static vs exported functions
MATCH (f:Function {subsystem: 'ext4'})
RETURN
    f.subsystem,
    count(CASE WHEN f.is_static THEN 1 END) AS static_functions,
    count(CASE WHEN NOT f.is_static THEN 1 END) AS exported_functions,
    count(f) AS total
```

### Query 11: File-Level Analysis

```cypher
// Which files have the most functions?
MATCH (file:File)-[:CONTAINS]->(f:Function)
WITH file, count(f) AS func_count
RETURN file.path AS file, func_count
ORDER BY func_count DESC
LIMIT 20
```

### Query 12: Circular Dependencies

```cypher
// Find potential circular call patterns (same function appears twice in chain)
MATCH path = (f:Function)-[:CALLS*2..5]->(f)
RETURN [node in nodes(path) | node.name] AS cycle,
       length(path) AS depth
LIMIT 10
```

---

## Python API Examples

### Example 1: Programmatic Analysis

```python
#!/usr/bin/env python3
"""
Custom analysis script using Kernel-GraphRAG Sentinel API
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Config
from module_b.graph_store import Neo4jGraphStore
from analysis.impact_analyzer import ImpactAnalyzer

# Load configuration
config = Config.from_defaults(
    kernel_root="/workspaces/ubuntu/linux-6.13"
)

# Connect to Neo4j
with Neo4jGraphStore(
    config.neo4j.url,
    config.neo4j.user,
    config.neo4j.password
) as store:
    # Get statistics
    stats = store.get_statistics()
    print(f"Database contains {stats['Function_count']} functions")

    # Analyze a function
    analyzer = ImpactAnalyzer(store)
    impact = analyzer.analyze_function_impact("ext4_map_blocks", max_depth=3)

    if impact:
        print(f"\nAnalyzing: {impact.function_name}")
        print(f"Direct callers: {len(impact.direct_callers)}")
        print(f"Indirect callers: {len(impact.indirect_callers)}")
        print(f"Test coverage: {len(impact.covering_tests)} tests")
    else:
        print("Function not found in database")
```

### Example 2: Custom Query

```python
#!/usr/bin/env python3
"""
Find all functions in a file
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Config
from module_b.graph_store import Neo4jGraphStore

config = Config.from_defaults()

with Neo4jGraphStore(
    config.neo4j.url,
    config.neo4j.user,
    config.neo4j.password
) as store:
    # Custom Cypher query
    query = """
    MATCH (f:Function)
    WHERE f.file_path CONTAINS 'inode.c'
    RETURN f.name, f.line_start, f.is_static
    ORDER BY f.line_start
    """

    results = store.execute_query(query)

    print(f"Functions in inode.c:")
    for record in results:
        static_marker = "[static]" if record['f.is_static'] else "[exported]"
        print(f"  {record['f.name']:40} {static_marker:12} line {record['f.line_start']}")
```

### Example 3: Batch Analysis

```python
#!/usr/bin/env python3
"""
Analyze multiple critical functions
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Config
from module_b.graph_store import Neo4jGraphStore
from analysis.impact_analyzer import ImpactAnalyzer

# Functions to analyze
CRITICAL_FUNCTIONS = [
    'ext4_map_blocks',
    'ext4_get_block',
    'ext4_free_blocks',
    'ext4_mb_new_blocks',
    'ext4_read_bh',
]

config = Config.from_defaults()

with Neo4jGraphStore(
    config.neo4j.url,
    config.neo4j.user,
    config.neo4j.password
) as store:
    analyzer = ImpactAnalyzer(store)

    results = []
    for func_name in CRITICAL_FUNCTIONS:
        impact = analyzer.analyze_function_impact(func_name, max_depth=2)
        if impact:
            results.append({
                'name': func_name,
                'callers': len(impact.direct_callers) + len(impact.indirect_callers),
                'tests': len(impact.covering_tests),
                'risk': impact.risk_level
            })

    # Print summary
    print(f"{'Function':<30} {'Callers':>10} {'Tests':>8} {'Risk':<10}")
    print("=" * 60)
    for r in sorted(results, key=lambda x: x['callers'], reverse=True):
        print(f"{r['name']:<30} {r['callers']:>10} {r['tests']:>8} {r['risk']:<10}")
```

### Example 4: Extract Function List

```python
#!/usr/bin/env python3
"""
Extract all functions from a subsystem for documentation
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from module_a.extractor import FunctionExtractor
import json

kernel_root = "/workspaces/ubuntu/linux-6.13"
subsystem = "fs/ext4"

extractor = FunctionExtractor(kernel_root)
functions, calls = extractor.extract_from_subsystem(subsystem)

# Group by file
by_file = {}
for func in functions:
    file_name = Path(func.file_path).name
    if file_name not in by_file:
        by_file[file_name] = []
    by_file[file_name].append({
        'name': func.name,
        'line': func.line_start,
        'static': func.is_static
    })

# Print organized output
for file_name in sorted(by_file.keys()):
    print(f"\n{file_name}:")
    for func in sorted(by_file[file_name], key=lambda x: x['line']):
        visibility = "static" if func['static'] else "export"
        print(f"  {func['name']:40} ({visibility}) - line {func['line']}")
```

---

## Advanced Queries

### Identify Uncovered Critical Paths

```cypher
// Functions with many callers but no tests
MATCH (f:Function)<-[r:CALLS]-()
WHERE NOT (f)<-[:COVERS]-(:TestCase)
WITH f, count(r) AS callers
WHERE callers >= 5
RETURN f.name, f.file_path, callers
ORDER BY callers DESC
```

### Trace from Syscall to Implementation

```cypher
// Find path from VFS functions to ext4 implementation
// (requires both VFS and ext4 to be ingested)
MATCH path = (vfs:Function)-[:CALLS*1..5]->(ext4:Function)
WHERE vfs.name STARTS WITH 'vfs_'
  AND ext4.subsystem = 'ext4'
RETURN [n in nodes(path) | n.name] AS syscall_path,
       length(path) AS hops
ORDER BY hops
LIMIT 20
```

### Test Redundancy Analysis

```cypher
// Find functions covered by multiple tests
MATCH (f:Function)<-[:COVERS]-(t:TestCase)
WITH f, collect(t.name) AS tests
WHERE size(tests) > 1
RETURN f.name AS function,
       size(tests) AS test_count,
       tests
ORDER BY test_count DESC
```

---

## Tips and Best Practices

### Performance Tips

1. **Use `--skip-preprocessing`** for faster parsing during development
2. **Create indexes** in Neo4j for frequently queried properties:
   ```cypher
   CREATE INDEX func_name_idx FOR (f:Function) ON (f.name)
   CREATE INDEX func_subsystem_idx FOR (f:Function) ON (f.subsystem)
   ```
3. **Limit query depth** to avoid exponential explosion: `--max-depth 3` is usually sufficient

### Analysis Best Practices

1. **Start shallow, go deeper**: Begin with depth 1-2, increase as needed
2. **Focus on non-static functions**: They're more likely to be called externally
3. **Check test coverage first**: Before modifying, ensure tests exist
4. **Save reports**: Use `--output` to document analysis for later reference

### Common Pitfalls

1. **External calls**: Functions outside the ingested subsystem won't appear in results
2. **Macro-generated code**: May be missed if preprocessing is skipped
3. **Function pointers**: Dynamic calls won't appear in static analysis
4. **Inline functions**: May not appear as separate nodes

---

## Example Reports

See the main README.md for full impact analysis report examples.

For more information:
- Configuration: See `examples/analyze_ext4.yaml`
- API Documentation: See source code docstrings
- Architecture: See `docs/DEVELOPMENT_PLAN.md`
