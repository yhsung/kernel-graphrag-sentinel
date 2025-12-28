# Data Flow Analysis - v0.2.0 Feature Plan

**Status**: Planning Phase
**Target Release**: v0.2.0
**Priority**: High
**Complexity**: High

---

## Overview

Data flow analysis tracks how data moves through the kernel code, enabling developers to:
- Understand variable dependencies across functions
- Trace taint propagation for security analysis
- Identify uninitialized variable usage
- Track pointer aliasing and memory flow
- Detect data race conditions

## Use Cases

### 1. Security Analysis
**Scenario**: Tracking user input through the kernel
```c
// User input arrives here
ssize_t sys_read(int fd, char *buf, size_t count) {
    // Trace 'buf' through call chain
    return vfs_read(file, buf, count, &pos);
}
```

**Query**: "Show me all functions that handle data from user space parameter `buf`"

### 2. Bug Detection
**Scenario**: Finding uninitialized variable usage
```c
int process_data(void) {
    int result;  // Uninitialized
    if (condition) {
        result = calculate();
    }
    return result;  // Potential bug: used without initialization
}
```

**Query**: "Find all paths where `result` is used before being defined"

### 3. Impact Analysis Enhancement
**Scenario**: Understanding data dependencies
```c
int ext4_iget(struct super_block *sb, unsigned long ino) {
    struct inode *inode = iget_locked(sb, ino);
    // Trace what happens to 'inode' pointer
    return inode;
}
```

**Query**: "What functions modify data pointed to by return value of `ext4_iget`?"

---

## Architecture

### Module D: Data Flow Analysis

```
┌─────────────────────────────────────────────────────────────┐
│ Module D: Data Flow Analyzer                                │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Variable     │→ │ Flow Graph   │→ │ Taint        │     │
│  │ Tracker      │  │ Builder      │  │ Analyzer     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         ↓                  ↓                  ↓             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Def-Use      │  │ Inter-proc   │  │ Security     │     │
│  │ Chains       │  │ Flow         │  │ Checker      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Integration with Existing Modules

```
Module A (Parser)
    ↓
    Extract AST
    ↓
Module D (Data Flow)  ← NEW
    ↓
    Variable defs/uses, assignments, parameters
    ↓
Module B (Graph Store)
    ↓
    Store DEFINES, USES, FLOWS_TO relationships
    ↓
Module E (Analysis)
    ↓
    Combined control + data flow queries
```

---

## Technical Design

### 1. AST Analysis Extensions

#### Variable Definitions
Extract from tree-sitter AST:
- Function parameters
- Local variable declarations
- Global variable declarations
- Struct field assignments

```python
@dataclass
class VariableDefinition:
    """Represents a variable definition point."""
    name: str
    var_type: str  # int, char*, struct inode*, etc.
    scope: str     # function name or "global"
    file_path: str
    line_number: int
    is_parameter: bool
    is_pointer: bool
```

#### Variable Uses
Track all references:
- Variable reads
- Variable writes (assignments)
- Function arguments
- Return statements

```python
@dataclass
class VariableUse:
    """Represents a variable usage point."""
    name: str
    usage_type: str  # "read", "write", "argument", "return"
    function: str
    file_path: str
    line_number: int
    context: str  # Assignment, if condition, function call, etc.
```

### 2. Data Flow Graph

#### Intra-procedural Flow (Within Function)

```python
@dataclass
class DataFlowEdge:
    """Represents data flowing from one variable to another."""
    from_var: str
    to_var: str
    flow_type: str  # "assignment", "parameter", "return"
    function: str
    line_number: int
```

**Example**:
```c
int foo(int a) {
    int b = a;      // FLOWS_TO: a → b
    int c = b * 2;  // FLOWS_TO: b → c
    return c;       // FLOWS_TO: c → return
}
```

#### Inter-procedural Flow (Across Functions)

```python
@dataclass
class InterProcFlow:
    """Data flow between function calls."""
    caller_var: str
    caller_function: str
    callee_param: str
    callee_function: str
    argument_position: int
```

**Example**:
```c
int main() {
    int x = 10;
    int y = foo(x);  // PARAM_FLOW: x → foo::a
}

int foo(int a) {
    return a * 2;    // RETURN_FLOW: foo::result → main::y
}
```

### 3. Neo4j Graph Schema Extensions

#### New Node Types

```cypher
// Variable definition
CREATE (v:Variable {
  name: "inode",
  type: "struct inode*",
  scope: "ext4_iget",
  file: "fs/ext4/inode.c",
  line: 4520,
  is_parameter: true,
  is_pointer: true
})

// Data source (user input, file I/O, etc.)
CREATE (s:DataSource {
  name: "user_buffer",
  source_type: "USER_INPUT",
  function: "sys_read",
  file: "fs/read_write.c",
  line: 580
})
```

#### New Relationship Types

```cypher
// Variable definition
(f:Function)-[:DEFINES]->(v:Variable)

// Variable usage
(f:Function)-[:USES]->(v:Variable)

// Data flow within function
(v1:Variable)-[:FLOWS_TO {line: 42, flow_type: "assignment"}]->(v2:Variable)

// Parameter flow
(caller:Function)-[:PASSES {arg_pos: 0, var_name: "buf"}]->(callee:Function)

// Return flow
(callee:Function)-[:RETURNS {var_name: "result"}]->(caller:Function)

// Taint propagation
(source:DataSource)-[:TAINTS {depth: 3}]->(var:Variable)
```

### 4. Tree-Sitter Extraction Strategy

#### Phase 1: Extract All Variables

```python
def extract_variable_definitions(function_node: Node) -> List[VariableDefinition]:
    """
    Extract variable definitions from function AST.

    Handles:
    - Function parameters
    - Local variable declarations
    - Assignments
    """
    variables = []

    # Get parameters
    for param in get_function_parameters(function_node):
        var = VariableDefinition(
            name=param.name,
            var_type=param.type,
            scope=function_name,
            is_parameter=True,
            ...
        )
        variables.append(var)

    # Get local declarations
    for decl in find_declarations(function_node):
        # Handle: int x = 0;
        # Handle: struct inode *inode;
        ...

    return variables
```

#### Phase 2: Track Assignments

```python
def extract_data_flows(function_node: Node) -> List[DataFlowEdge]:
    """
    Extract data flow edges from assignments.

    Examples:
    - a = b        → FLOWS: b → a
    - a = b + c    → FLOWS: b → a, c → a
    - *p = q       → FLOWS: q → *p (pointer write)
    """
    flows = []

    # Find all assignment expressions
    assignments = find_nodes_by_type(function_node, "assignment_expression")

    for assign in assignments:
        left = get_assignment_left(assign)   # a
        right = get_assignment_right(assign) # b + c

        # Extract all variables on right side
        right_vars = extract_variables_from_expr(right)

        for var in right_vars:
            flows.append(DataFlowEdge(
                from_var=var,
                to_var=left,
                flow_type="assignment",
                ...
            ))

    return flows
```

#### Phase 3: Track Function Calls

```python
def extract_call_flows(function_node: Node, call_graph: Dict) -> List[InterProcFlow]:
    """
    Track data flow through function calls.

    Example:
    result = process_data(buffer, size);

    Flows:
    - buffer → process_data::param0
    - size → process_data::param1
    - process_data::return → result
    """
    flows = []

    call_sites = find_nodes_by_type(function_node, "call_expression")

    for call in call_sites:
        callee_name = get_callee_name(call)
        arguments = get_call_arguments(call)

        for i, arg in enumerate(arguments):
            arg_vars = extract_variables_from_expr(arg)

            for var in arg_vars:
                flows.append(InterProcFlow(
                    caller_var=var,
                    caller_function=current_function,
                    callee_param=f"param{i}",
                    callee_function=callee_name,
                    argument_position=i
                ))

    return flows
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1)

**Files to Create**:
```
src/module_d/
├── __init__.py
├── variable_tracker.py     # Extract variable definitions
├── flow_builder.py         # Build data flow graph
└── flow_schema.py          # Neo4j schema extensions
```

**Tasks**:
1. ✅ Design architecture (this document)
2. Create `variable_tracker.py`:
   - Extract function parameters
   - Extract local variable declarations
   - Extract global variables
3. Create `flow_schema.py`:
   - Define Variable node type
   - Define DEFINES, USES, FLOWS_TO relationships
4. Write unit tests for variable extraction

### Phase 2: Intra-procedural Analysis (Week 1-2)

**Tasks**:
1. Implement assignment tracking
2. Build def-use chains within functions
3. Handle pointer dereferencing
4. Store in Neo4j with new relationships
5. Write tests for flow tracking

### Phase 3: Inter-procedural Analysis (Week 2)

**Tasks**:
1. Track parameter passing
2. Track return value flow
3. Build complete call + data flow graph
4. Handle function pointers (best effort)
5. Integration tests

### Phase 4: Taint Analysis (Week 3)

**Files**:
```
src/module_d/
└── taint_analyzer.py       # Security taint tracking
```

**Tasks**:
1. Define taint sources (user input, file I/O)
2. Implement taint propagation rules
3. Track tainted data through call graph
4. Generate security reports
5. Add CLI command: `analyze-taint`

### Phase 5: CLI & Queries (Week 3)

**Tasks**:
1. Add CLI commands:
   - `dataflow --variable <name> --function <func>`
   - `taint-check --source <func>`
   - `find-uninitialized`
2. Create Cypher query templates
3. Update main.py with new commands

### Phase 6: Documentation & Testing (Week 4)

**Tasks**:
1. Write docs/data_flow_analysis.md
2. Create example queries
3. Achieve 60%+ test coverage
4. Performance optimization
5. Integration with existing impact analysis

---

## Example Queries

### Query 1: Find All Uses of a Variable

```cypher
// Find where parameter 'inode' is used
MATCH (f:Function {name: "ext4_iget"})-[:DEFINES]->(v:Variable {name: "inode"})
MATCH (v)-[:FLOWS_TO*1..5]->(used:Variable)
MATCH (user_func:Function)-[:USES]->(used)
RETURN user_func.name, used.name, used.line
ORDER BY used.line
```

### Query 2: Trace User Input

```cypher
// Find all variables tainted by user input
MATCH (source:DataSource {source_type: "USER_INPUT"})
MATCH (source)-[:TAINTS*1..10]->(v:Variable)
MATCH (f:Function)-[:USES]->(v)
RETURN f.name, v.name, f.file
```

### Query 3: Find Uninitialized Uses

```cypher
// Variables used before definition
MATCH (f:Function)-[:USES]->(v:Variable)
WHERE NOT EXISTS((f)-[:DEFINES]->(v))
  AND NOT v.is_parameter
RETURN f.name, v.name, v.line
```

### Query 4: Complete Data Flow Path

```cypher
// Trace data from source to sink
MATCH path = (source:Variable {name: "user_buf"})-[:FLOWS_TO*]->(sink:Variable {name: "kernel_buf"})
RETURN [n in nodes(path) | n.name] as flow_path,
       [r in relationships(path) | r.flow_type] as flow_types
```

---

## Success Criteria

### Functional Requirements
- [ ] Extract variable definitions from 100+ functions
- [ ] Build intra-procedural data flow graphs
- [ ] Track inter-procedural parameter/return flow
- [ ] Identify basic taint propagation
- [ ] Provide CLI commands for data flow queries
- [ ] Integrate with existing impact analysis

### Performance Requirements
- [ ] Parse 1,000 functions in < 2 minutes
- [ ] Data flow query response < 3 seconds
- [ ] Support flow depth up to 10 hops
- [ ] Memory usage < 4GB for ext4 subsystem

### Quality Requirements
- [ ] Test coverage ≥ 60% for Module D
- [ ] Documentation with 10+ example queries
- [ ] Handle 80%+ of common C patterns
- [ ] Graceful degradation for complex cases (macros, inline asm)

---

## Technical Challenges & Solutions

### Challenge 1: Pointer Aliasing
**Problem**: Multiple pointers to same data
```c
int *a = &x;
int *b = a;  // a and b are aliases
*b = 5;      // Affects x
```

**Solution**:
- Track pointer assignments as FLOWS_TO
- Use alias analysis for pointer writes
- Conservative approach: assume aliasing when uncertain

### Challenge 2: Struct Field Flow
**Problem**: Tracking data through struct fields
```c
struct data d;
d.field = user_input();
process(d.field);  // Need to track d.field separately
```

**Solution**:
- Represent struct fields as `struct_name.field_name`
- Create FLOWS_TO edges for field assignments
- v0.2.0: Basic support; v0.3.0: Complete struct tracking

### Challenge 3: Array Indexing
**Problem**: Data flow through arrays
```c
int arr[10];
arr[0] = user_input();
int x = arr[i];  // Unknown index
```

**Solution**:
- Conservative approach: arr[*] = single variable
- Track arr as a whole, not individual elements
- Future: Add array index analysis

### Challenge 4: Function Pointers
**Problem**: Indirect calls
```c
int (*fp)(int) = foo;
result = fp(data);  // Dynamic dispatch
```

**Solution**:
- Best-effort: track known assignments
- Flag uncertain flows for manual review
- Future: Points-to analysis

---

## Roadmap

### v0.2.0 (Current) - Basic Data Flow
- ✅ Architecture design
- Variable tracking
- Intra-procedural flow
- Inter-procedural flow
- Basic taint analysis
- CLI integration

### v0.3.0 - Advanced Features
- Struct field tracking
- Array analysis
- Pointer alias analysis
- Path-sensitive analysis
- Performance optimization

### v1.0 - Production Ready
- Complete C language coverage
- Integration with CI/CD
- Real-time analysis
- Advanced security checks
- IDE plugins

---

## References

- **LLVM Data Flow Analysis**: https://llvm.org/docs/ProgrammersManual.html#dataflow-analysis
- **Static Analysis Techniques**: "Principles of Program Analysis" by Nielson et al.
- **Taint Analysis**: "All You Ever Wanted to Know About Dynamic Taint Analysis" (Schwartz et al.)
- **Linux Kernel Security**: https://www.kernel.org/doc/html/latest/security/

---

**Next Steps**:
1. Review and approve architecture
2. Begin implementation of `variable_tracker.py`
3. Set up test infrastructure for Module D
