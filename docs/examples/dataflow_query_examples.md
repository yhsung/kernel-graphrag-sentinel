# Data Flow Query Examples

This guide provides practical examples for querying and analyzing data flow in Linux kernel code using Kernel-GraphRAG Sentinel v0.2.0.

## Table of Contents

1. [Basic Queries](#basic-queries)
2. [Security Analysis](#security-analysis)
3. [Buffer Tracking](#buffer-tracking)
4. [Taint Analysis](#taint-analysis)
5. [Cross-Function Flows](#cross-function-flows)
6. [Advanced Patterns](#advanced-patterns)

## Prerequisites

Before running these queries, you need to ingest data flow information:

```bash
# Ingest call graph and functions
kgraph pipeline fs/ext4

# Ingest data flow information
kgraph ingest-dataflow fs/ext4
```

## Basic Queries

### 1. Find All Variables in a Function

**Cypher Query:**
```cypher
MATCH (v:Variable)
WHERE v.scope = "ext4_map_blocks"
RETURN v.name, v.type, v.is_parameter, v.is_pointer
ORDER BY v.line_number
```

**CLI Command:**
```bash
# Not directly supported, use Neo4j browser or cypher-shell
```

### 2. Trace Data Flow for a Variable

**CLI Command:**
```bash
# Forward flow (what this variable flows INTO)
kgraph dataflow inode --direction forward --max-depth 3

# Backward flow (what flows INTO this variable)
kgraph dataflow result --direction backward --max-depth 3

# Both directions
kgraph dataflow buffer --direction both
```

**Cypher Query:**
```cypher
// Forward flow
MATCH path = (v1:Variable {name: "inode"})-[:FLOWS_TO*1..3]->(v2:Variable)
RETURN v1.name, v2.name, length(path) as depth
ORDER BY depth, v2.name

// Backward flow
MATCH path = (v1:Variable)-[:FLOWS_TO*1..3]->(v2:Variable {name: "result"})
RETURN v1.name, v2.name, length(path) as depth
ORDER BY depth, v1.name
```

### 3. Find Variables That Reach Return Values

**Cypher Query:**
```cypher
MATCH path = (v:Variable)-[:FLOWS_TO*]->(ret:Variable {name: "__RETURN__"})
WHERE v.scope = "ext4_get_block"
RETURN v.name, v.type, v.is_parameter, length(path) as depth
ORDER BY depth
LIMIT 20
```

**Use Case**: Understand which variables influence the return value of a function.

### 4. List All Pointer Variables

**Cypher Query:**
```cypher
MATCH (v:Variable)
WHERE v.is_pointer = true AND v.file_path =~ ".*ext4.*"
RETURN v.name, v.type, v.scope, v.file_path
LIMIT 50
```

**Use Case**: Identify all pointer variables for memory safety analysis.

## Security Analysis

### 5. Track User-Controlled Input

**Scenario**: Find all variables that originate from user input parameters.

**Cypher Query:**
```cypher
// Find all variables that flow from function parameters
MATCH path = (param:Variable {is_parameter: true})-[:FLOWS_TO*1..5]->(v:Variable)
WHERE param.scope = "ext4_ioctl"
RETURN param.name, v.name, v.scope, length(path) as depth
ORDER BY depth
LIMIT 100
```

**Use Case**: Identify potential attack surfaces by tracking user-controlled data.

### 6. Find Unchecked Variables

**Cypher Query:**
```cypher
// Variables used without being checked (heuristic: not in conditionals)
MATCH (f:Function)-[:USES]->(v:Variable)
WHERE NOT (f)-[:DEFINES]->(v)  // Not defined locally (external input)
RETURN v.name, v.scope, f.name as using_function, v.line_number
LIMIT 50
```

**Use Case**: Identify variables that might need validation.

### 7. Sensitive Data Propagation

**Scenario**: Track how sensitive data (e.g., credentials, keys) propagates through code.

**Cypher Query:**
```cypher
// Track variables with "key", "password", or "secret" in name
MATCH path = (sensitive:Variable)-[:FLOWS_TO*1..10]->(v:Variable)
WHERE sensitive.name =~ "(?i).*(key|password|secret|token).*"
RETURN sensitive.name, v.name, v.scope, length(path) as depth
ORDER BY depth
LIMIT 100
```

**Use Case**: Data leak prevention and security auditing.

## Buffer Tracking

### 8. Track Buffer Through Function

**CLI Command:**
```bash
kgraph dataflow buffer --function ext4_read_block --max-depth 5
```

**Cypher Query:**
```cypher
MATCH path = (v1:Variable)-[:FLOWS_TO*1..5]-(v2:Variable)
WHERE (v1.name = "buffer" OR v2.name = "buffer")
  AND v1.scope = "ext4_read_block"
RETURN DISTINCT
  v1.name, v1.type, v1.is_pointer,
  v2.name, v2.type, v2.is_pointer,
  length(path) as depth
ORDER BY depth
```

**Use Case**: Buffer overflow analysis and bounds checking.

### 9. Find Buffer Size Variables

**Cypher Query:**
```cypher
// Find variables with "size", "len", or "count" in name
MATCH (v:Variable)
WHERE v.name =~ "(?i).*(size|len|length|count|num).*"
  AND v.file_path =~ ".*ext4.*"
RETURN v.name, v.type, v.scope, v.file_path
ORDER BY v.scope, v.name
LIMIT 100
```

**Use Case**: Identify size variables for bounds checking analysis.

### 10. Track Buffer with Its Size

**Cypher Query:**
```cypher
// Find buffers and their associated size variables
MATCH (buf:Variable), (size:Variable)
WHERE buf.scope = size.scope
  AND buf.name =~ "(?i).*(buf|data|ptr).*"
  AND size.name =~ "(?i).*(size|len).*"
  AND buf.line_number < size.line_number + 5  // Close in proximity
RETURN buf.name, buf.type, size.name, size.type, buf.scope
LIMIT 50
```

**Use Case**: Buffer-size pair analysis for overflow prevention.

## Taint Analysis

### 11. Simple Taint Propagation

**Scenario**: Track tainted data from source to sink.

**Cypher Query:**
```cypher
// Find paths from taint source to sensitive sinks
MATCH path = (source:Variable)-[:FLOWS_TO*1..10]->(sink:Variable)
WHERE source.name = "user_input"  // Taint source
  AND sink.name =~ "(?i).*(exec|command|query).*"  // Sensitive sink
RETURN
  nodes(path)[0].name as source,
  nodes(path)[-1].name as sink,
  [n IN nodes(path) | n.name] as flow_chain,
  length(path) as depth
ORDER BY depth
LIMIT 20
```

**Use Case**: Detect potential code injection or SQL injection vulnerabilities.

### 12. Find Sanitization Points

**Cypher Query:**
```cypher
// Find variables that go through validation functions
MATCH path = (tainted:Variable)-[:FLOWS_TO*]->(validated:Variable)
WHERE tainted.scope =~ "(?i).*(input|request|param).*"
  AND validated.scope =~ "(?i).*(validate|sanitize|check|verify).*"
RETURN tainted.name, tainted.scope, validated.name, validated.scope, length(path)
LIMIT 50
```

**Use Case**: Verify input validation coverage.

### 13. Cross-Boundary Data Flow

**Cypher Query:**
```cypher
// Track data crossing trust boundaries (e.g., kernel ↔ user space)
MATCH path = (v1:Variable)-[:FLOWS_TO*1..5]->(v2:Variable)
WHERE v1.scope =~ "(?i).*(ioctl|syscall|user).*"  // User space
  AND v2.scope =~ "(?i).*(kernel|internal).*"     // Kernel space
RETURN v1.name, v1.scope, v2.name, v2.scope, length(path) as depth
ORDER BY depth
LIMIT 50
```

**Use Case**: Trust boundary violation detection.

## Cross-Function Flows

### 14. Inter-Procedural Data Flow

**Cypher Query:**
```cypher
// Track data flow across function calls
MATCH (f1:Function)-[:CALLS]->(f2:Function)
MATCH (v1:Variable {scope: f1.name})-[:FLOWS_TO*]->(v2:Variable {scope: f2.name})
RETURN f1.name, v1.name, f2.name, v2.name
LIMIT 100
```

**Use Case**: Understand cross-function data dependencies.

### 15. Find Data Flow Through Call Chain

**Cypher Query:**
```cypher
// Find variables that flow through a call chain
MATCH callPath = (f1:Function)-[:CALLS*2..4]->(f4:Function)
MATCH dataPath = (v1:Variable {scope: f1.name})-[:FLOWS_TO*]->(v4:Variable {scope: f4.name})
RETURN
  [f IN nodes(callPath) | f.name] as call_chain,
  v1.name as start_var,
  v4.name as end_var,
  length(callPath) as call_depth,
  length(dataPath) as data_depth
LIMIT 20
```

**Use Case**: Deep impact analysis across call chains.

### 16. Return Value Propagation

**Cypher Query:**
```cypher
// Track how return values propagate to callers
MATCH (callee:Function)<-[:CALLS]-(caller:Function)
MATCH (ret:Variable {name: "__RETURN__", scope: callee.name})
MATCH (ret)-[:FLOWS_TO*0..3]->(v:Variable {scope: callee.name})
MATCH (caller_var:Variable {scope: caller.name})
RETURN callee.name, v.name, caller.name, caller_var.name
LIMIT 50
```

**Use Case**: Understand how function return values affect callers.

## Advanced Patterns

### 17. Find Complex Data Flow Patterns

**Cypher Query:**
```cypher
// Find A → B → C → D patterns (linear chains)
MATCH path = (a:Variable)-[:FLOWS_TO]->(b:Variable)-[:FLOWS_TO]->(c:Variable)-[:FLOWS_TO]->(d:Variable)
WHERE a.scope = "ext4_write_begin"
RETURN a.name, b.name, c.name, d.name, a.scope
LIMIT 20
```

**Use Case**: Identify long transformation chains.

### 18. Find Data Flow Cycles

**Cypher Query:**
```cypher
// Find variables that flow back to themselves (potential infinite loops)
MATCH path = (v:Variable)-[:FLOWS_TO*2..5]->(v)
RETURN v.name, v.scope, length(path) as cycle_length
LIMIT 20
```

**Use Case**: Detect circular dependencies and potential bugs.

### 19. Find Common Flow Destinations

**Cypher Query:**
```cypher
// Find variables that many other variables flow into (data aggregators)
MATCH (v1:Variable)-[:FLOWS_TO]->(v2:Variable)
WITH v2, count(v1) as inflow_count
WHERE inflow_count > 5
RETURN v2.name, v2.type, v2.scope, inflow_count
ORDER BY inflow_count DESC
LIMIT 20
```

**Use Case**: Identify critical aggregation points.

### 20. Find Isolated Variables

**Cypher Query:**
```cypher
// Find variables with no data flows (potentially unused)
MATCH (v:Variable)
WHERE NOT (v)-[:FLOWS_TO]-()
  AND NOT ()-[:FLOWS_TO]->(v)
  AND v.scope <> "global"
RETURN v.name, v.type, v.scope, v.file_path
LIMIT 50
```

**Use Case**: Dead code detection and cleanup.

### 21. Statistical Analysis

**Cypher Query:**
```cypher
// Get data flow statistics per function
MATCH (v:Variable)
WITH v.scope as function_name,
     count(v) as var_count,
     sum(CASE WHEN v.is_parameter THEN 1 ELSE 0 END) as param_count,
     sum(CASE WHEN v.is_pointer THEN 1 ELSE 0 END) as pointer_count
ORDER BY var_count DESC
RETURN function_name, var_count, param_count, pointer_count
LIMIT 20
```

**Use Case**: Code complexity metrics and refactoring candidates.

### 22. Find High-Risk Variables

**Cypher Query:**
```cypher
// Variables that are pointers, used in multiple places, and flow to many targets
MATCH (v:Variable)-[:FLOWS_TO]->(target:Variable)
WHERE v.is_pointer = true
WITH v, count(DISTINCT target) as fan_out
WHERE fan_out > 3
RETURN v.name, v.type, v.scope, fan_out
ORDER BY fan_out DESC
LIMIT 20
```

**Use Case**: Identify high-risk variables for focused testing.

## Using CLI Commands

### Basic Usage

```bash
# Analyze forward flow
kgraph dataflow inode --direction forward --max-depth 3

# Analyze backward flow
kgraph dataflow result --direction backward --max-depth 5

# Limit to specific function
kgraph dataflow buffer --function ext4_read_block

# Both directions
kgraph dataflow error_code --direction both --max-depth 4
```

### Workflow Example

```bash
# 1. Ingest subsystem
kgraph pipeline fs/ext4

# 2. Ingest data flow
kgraph ingest-dataflow fs/ext4

# 3. Analyze specific variable
kgraph dataflow inode --max-depth 5

# 4. Limit to function scope
kgraph dataflow buffer --function ext4_write_begin --direction forward

# 5. Check database statistics
kgraph stats
```

## Best Practices

1. **Start Small**: Begin with small depth values (2-3) and increase as needed
2. **Use Function Filters**: When possible, limit queries to specific functions
3. **Combine with Call Graph**: Use Module B's call graph alongside data flow for comprehensive analysis
4. **Validate Results**: Cross-reference findings with source code
5. **Pattern Recognition**: Look for common patterns (source→sanitize→sink)
6. **Performance**: For large codebases, use indexes and limit result sets

## Common Use Cases Summary

| Use Case | Example Query Number | Key Pattern |
|----------|---------------------|-------------|
| Buffer Overflow Analysis | 8, 9, 10 | Track buffers and sizes |
| Taint Analysis | 11, 12, 13 | Source → Sink paths |
| Security Audit | 5, 6, 7 | User input tracking |
| Impact Analysis | 3, 14, 15 | Return value propagation |
| Code Quality | 17, 19, 20, 21 | Complexity metrics |
| Memory Safety | 4, 22 | Pointer tracking |

## Next Steps

1. **Customize Queries**: Adapt these examples to your specific subsystem
2. **Build Reports**: Use query results to generate security reports
3. **Automate Checks**: Integrate queries into CI/CD pipelines
4. **Combine with LLM**: Use `kgraph analyze --llm` for AI-powered insights
5. **Visualization**: Export graphs with `kgraph export-graph` for visual analysis

## References

- [Data Flow Analysis Architecture](data_flow_analysis_plan.md)
- [Neo4j Cypher Documentation](https://neo4j.com/docs/cypher-manual/)
- [v0.2.0 Progress Report](v0.2.0_progress.md)

---

**Version**: 0.2.0-dev
**Last Updated**: December 28, 2025
**Status**: Week 2 Complete
