# Combined Call Graph & Data Flow Analysis Example

This example demonstrates how to generate a comprehensive analysis report that combines both call graph analysis (Module B) and data flow analysis (Module D) using `src/main.py`.

---

## Overview

The `analyze` command in Kernel-GraphRAG Sentinel automatically combines:
- **Call Graph Analysis** (Module B): Who calls this function, what it calls
- **Data Flow Analysis** (Module D): Variables, parameters, data flows
- **LLM Report Generation**: AI-powered professional impact analysis

---

## Prerequisites

### 1. Ensure Neo4j is Running
```bash
# Check Neo4j status
sudo systemctl status neo4j

# Or start Neo4j if needed
sudo systemctl start neo4j
```

### 2. Configure Environment Variables
```bash
# Edit .env file
cat > .env << 'EOF'
# Neo4j Configuration
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# LLM Provider Configuration
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=devstral-small-2:24b

# Analysis Configuration
MAX_CALL_DEPTH=3
ENABLE_CPP_PREPROCESSING=true
EOF
```

### 3. Ensure Data is Ingested

#### Ingest Call Graph Data
```bash
# Ingest call graph and functions
python3 src/main.py pipeline fs/ext4
```

#### Ingest Data Flow Data
```bash
# Ingest variable tracking and data flows
python3 src/main.py ingest-dataflow fs/ext4
```

---

## Step-by-Step Example: ext4_do_writepages

### Step 1: Verify Function Exists in Database

```bash
python3 src/main.py query "
MATCH (f:Function {name: 'ext4_do_writepages'})
OPTIONAL MATCH (caller:Function)-[:CALLS]->(f)
OPTIONAL MATCH (f)-[:CALLS]->(callee:Function)
OPTIONAL MATCH (v:Variable {scope: f.name})
RETURN f.name, f.file_path,
       count(DISTINCT caller) as callers,
       count(DISTINCT callee) as callees,
       count(DISTINCT v) as variables
"
```

**Expected Output:**
```
f.name                | f.file_path                           | callers | callees | variables
ext4_do_writepages    | /path/to/linux-6.13/fs/ext4/inode.c  | 2       | 11      | 13
```

### Step 2: View Variables in the Function

```bash
python3 src/main.py query "
MATCH (v:Variable {scope: 'ext4_do_writepages'})
RETURN v.name, v.type, v.is_parameter, v.is_pointer
ORDER BY v.is_parameter DESC, v.name
"
```

**Expected Output:**
```
v.name          | v.type              | v.is_parameter | v.is_pointer
mpd             | struct mpage_da_... | true           | true
wbc             | struct writeback... | true           | true
ret             | int                 | false          | false
io_done         | bool                | false          | false
...
```

### Step 3: Analyze Data Flows

```bash
# Forward flow analysis - what does 'ret' flow into?
python3 src/main.py dataflow ret --function ext4_do_writepages --direction forward --max-depth 3

# Backward flow analysis - what flows into 'ret'?
python3 src/main.py dataflow ret --function ext4_do_writepages --direction backward --max-depth 3
```

### Step 4: Generate Combined Analysis Report

#### Method 1: Using Environment Variables

```bash
# Set LLM provider via environment
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=devstral-small-2:24b

# Generate report
python3 src/main.py analyze ext4_do_writepages \
    --llm \
    --output docs/examples/reports/devstral-small-2-24b-call-data-report.md
```

#### Method 2: Using Configuration File

Create `config.yaml`:
```yaml
subsystem: "fs/ext4"
kernel_source: "/workspaces/ubuntu/linux-6.13"

neo4j:
  url: "bolt://localhost:7687"
  user: "neo4j"
  password: "password123"

llm:
  provider: "ollama"
  model: "devstral-small-2:24b"
  temperature: 0.7

analysis:
  max_call_depth: 3
  include_indirect_calls: true
```

Then run:
```bash
python3 src/main.py --config config.yaml analyze ext4_do_writepages \
    --llm \
    --output docs/examples/reports/devstral-small-2-24b-call-data-report.md
```

#### Method 3: One-Liner with Inline Provider

```bash
python3 src/main.py analyze ext4_do_writepages \
    --llm \
    --provider ollama \
    --model devstral-small-2:24b \
    --output docs/examples/reports/devstral-small-2-24b-call-data-report.md
```

---

## What Gets Included in the Report

The generated report combines multiple data sources:

### 1. Call Graph Analysis (Module B)
- Direct callers (functions calling `ext4_do_writepages`)
- Direct callees (functions called by `ext4_do_writepages`)
- Indirect callers (depth 1-3)
- Indirect callees (depth 1-3)
- Call chain analysis
- Mermaid diagram visualization

### 2. Data Flow Analysis (Module D)
- Function parameters:
  - `struct mpage_da_data *mpd`
  - `struct writeback_control *wbc`
- Local variables:
  - `int ret`
  - `bool io_done`
  - `struct ext4_io_submit io_submit`
  - ... (13 total variables)
- Variable types and pointer analysis
- Data flow relationships (if available)

### 3. Test Coverage Analysis
- KUnit test mapping
- Direct test coverage
- Indirect test coverage
- Test gap identification

### 4. LLM-Generated Insights
The LLM (Devstral in this case) analyzes all the data and generates:

#### Section 1: Header
- Function name and file path
- Risk level with emoji (🟢🟡🔴⚫)
- Report date

#### Section 2: Executive Summary
- 2-3 sentence overview
- Key risk factors
- Test coverage status

#### Section 3: Code Impact Analysis
- **Affected Components Table**
  - Direct Callers: Impact level
  - Indirect Callers: Impact level
  - Public Interface: NONE/LOW/CRITICAL
  - Dependent Code: External dependencies

- **Scope of Change**
  - Entry points count: 2 callers
  - Call sites: 11 callees
  - Abstraction layers
  - Visibility (internal/external)

- **Call Graph Visualization**
  - Mermaid diagram showing function relationships
  - Highlighted target function
  - Direct callers and callees visualized

#### Section 4: Testing Requirements
- Existing test coverage (✅/❌/⚠️)
- Mandatory tests to run
- Specific commands for functional tests
- Regression test paths

#### Section 5: Recommended New Tests
- Unit test cases needed
- Integration test scenarios
- Specific test code examples

#### Section 6: Risk Assessment
- Risk level justification table
- Potential failure modes
- Security implications

#### Section 7: Implementation Recommendations
- Phase-by-phase checklist
  - Phase 1: Preparation
  - Phase 2: Development
  - Phase 3: Testing
  - Phase 4: Validation

#### Section 8: Escalation Criteria
- Conditions requiring escalation
- When to stop and seek help

#### Section 9: Recommendations Summary
- Priority table (CRITICAL/HIGH/MEDIUM/LOW)
- Action items
- Owner assignments

#### Section 10: Conclusion
- Final recommendation
- Go/No-go decision

---

## Data Flow-Specific Insights

When data flow analysis is available, the report includes:

### Variable Security Analysis
```
⚠️ Parameter 'wbc' (writeback_control pointer):
   - User-controlled via writeback system
   - Potential for invalid page ranges
   - Requires validation before use

⚠️ Variable 'ret' (return value):
   - Flows from multiple callees
   - Error codes must be properly propagated
   - Critical for error handling
```

### Data Flow Patterns
```
Data Flow Chain Example:
  mpd->io_submit → io_submit (local copy)
  io_submit → ext4_io_submit_init() (initialization)
  ret ← mpage_prepare_extent_to_map() (error handling)
  ret → return value (propagation)
```

### Buffer and Pointer Analysis
```
Pointers requiring NULL checks:
  - mpd (struct mpage_da_data*)
  - wbc (struct writeback_control*)
  - mpd->inode
  - mpd->io_submit

Buffer-related variables:
  - io_submit.io_bio (I/O buffer)
  - Pages tracked via wbc->pages[]
```

---

## Advanced Usage

### Generate Reports for Multiple Functions

```bash
#!/bin/bash
# generate_reports.sh

FUNCTIONS=(
    "ext4_do_writepages"
    "ext4_write_begin"
    "ext4_write_end"
    "ext4_map_blocks"
)

for func in "${FUNCTIONS[@]}"; do
    echo "Generating report for $func..."
    python3 src/main.py analyze "$func" \
        --llm \
        --provider ollama \
        --model devstral-small-2:24b \
        --output "docs/examples/reports/${func}_report.md"
done
```

### Compare Different LLM Providers

```bash
# Generate with Devstral
export OLLAMA_MODEL=devstral-small-2:24b
python3 src/main.py analyze ext4_do_writepages --llm \
    --output reports/devstral_report.md

# Generate with Qwen
export OLLAMA_MODEL=qwen3-vl:30b
python3 src/main.py analyze ext4_do_writepages --llm \
    --output reports/qwen_report.md

# Generate with Gemini
export LLM_PROVIDER=gemini
export GEMINI_MODEL=gemini-2.0-flash-exp
python3 src/main.py analyze ext4_do_writepages --llm \
    --output reports/gemini_report.md
```

### Extract Specific Data for Custom Analysis

```python
#!/usr/bin/env python3
"""Custom analysis combining call graph and data flow."""

from src.module_b.graph_store import Neo4jGraphStore
from src.analysis.impact_analyzer import ImpactAnalyzer
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to Neo4j
store = Neo4jGraphStore(
    uri=os.getenv('NEO4J_URL'),
    user=os.getenv('NEO4J_USER'),
    password=os.getenv('NEO4J_PASSWORD')
)

# Analyze function
analyzer = ImpactAnalyzer(store, max_depth=3)
impact_result = analyzer.analyze_function_impact("ext4_do_writepages")

# Get call graph data
print("Call Graph:")
print(f"  Direct callers: {len(impact_result.direct_callers)}")
print(f"  Direct callees: {len(impact_result.direct_callees)}")

# Get data flow data
query = '''
MATCH (v:Variable {scope: "ext4_do_writepages"})
RETURN v.name, v.type, v.is_parameter, v.is_pointer
ORDER BY v.is_parameter DESC
'''
variables = store.execute_query(query)

print("\nData Flow:")
print(f"  Total variables: {len(variables)}")
params = [v for v in variables if v['v.is_parameter']]
print(f"  Parameters: {len(params)}")
for p in params:
    ptr = '*' if p['v.is_pointer'] else ''
    print(f"    - {p['v.type']}{ptr} {p['v.name']}")

store.close()
```

---

## Troubleshooting

### Issue: "Function not found"
```bash
# Verify function exists
python3 src/main.py query "MATCH (f:Function {name: 'your_function'}) RETURN f"

# If not found, re-ingest
python3 src/main.py pipeline fs/ext4
```

### Issue: "No variables found"
```bash
# Check if data flow was ingested
python3 src/main.py query "MATCH (v:Variable) RETURN count(v)"

# If zero, ingest data flows
python3 src/main.py ingest-dataflow fs/ext4
```

### Issue: "LLM connection failed"
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Verify model is downloaded
ollama list | grep devstral

# Pull model if needed
ollama pull devstral-small-2:24b
```

### Issue: "Report is empty or incomplete"
```bash
# Check Neo4j connection
python3 -c "
from src.module_b.graph_store import Neo4jGraphStore
store = Neo4jGraphStore('bolt://localhost:7687', 'neo4j', 'password123')
result = store.execute_query('MATCH (f:Function) RETURN count(f)')
print(f'Functions in DB: {result[0][\"count(f)\"]}')
store.close()
"

# Verify both datasets exist
python3 src/main.py query "
MATCH (f:Function {name: 'ext4_do_writepages'})
OPTIONAL MATCH (v:Variable {scope: f.name})
RETURN count(f) as funcs, count(v) as vars
"
```

---

## Expected Output

### Console Output
```
Analyzing impact for: ext4_do_writepages
Max call depth: 3
LLM provider: ollama (devstral-small-2:24b)

🤖 Generating AI-powered report...
Report written to docs/examples/reports/devstral-small-2-24b-call-data-report.md
```

### Report Statistics
- **Report Length**: ~150-200 lines
- **Generation Time**: ~2-3 minutes (depending on LLM)
- **Sections**: 10 comprehensive sections
- **Mermaid Diagram**: 1 call graph visualization
- **Variables Listed**: 13 (parameters + locals)
- **Functions Analyzed**: 2 callers + 11 callees
- **Risk Assessment**: Based on test coverage and complexity

---

## Real-World Use Cases

### 1. Pre-Modification Risk Assessment
Before modifying `ext4_do_writepages`, generate a report to understand:
- Which functions depend on it (callers)
- What it depends on (callees)
- What variables are involved
- Where tests are needed

### 2. Security Audit
Identify security concerns:
- User-controlled input parameters
- Buffer/pointer variables requiring validation
- Data flow from untrusted sources
- Missing boundary checks

### 3. Refactoring Planning
Understand the scope:
- How many call sites need updating
- What data structures are involved
- Which tests cover this code
- What the blast radius is

### 4. Code Review Assistance
Generate comprehensive context for reviewers:
- Full call graph visualization
- Variable usage patterns
- Test coverage gaps
- Risk assessment

---

## Summary

The `src/main.py analyze` command provides a **one-stop solution** for comprehensive code analysis:

```bash
# Single command combines:
python3 src/main.py analyze <function_name> --llm --output <report.md>
```

**What you get:**
- ✅ Call graph analysis (Module B)
- ✅ Data flow analysis (Module D)
- ✅ Test coverage mapping (Module C)
- ✅ LLM-powered insights
- ✅ Risk assessment
- ✅ Actionable recommendations
- ✅ Professional markdown report

**No manual work required** - the tool automatically:
1. Queries Neo4j for call graph data
2. Retrieves variable and data flow information
3. Builds comprehensive context
4. Generates Mermaid visualization
5. Sends to LLM with structured prompt
6. Saves formatted report

---

**Generated by:** Kernel-GraphRAG Sentinel v0.2.0
**Last Updated:** 2025-12-28
**Example Function:** ext4_do_writepages
**LLM Provider:** Ollama (devstral-small-2:24b)
