# Trace Collection Framework Ingestion Plan

**Kernel-GraphRAG Sentinel: SW/HW Tracing & PMU Performance Analysis**

This guide provides a structured approach to ingesting Linux kernel subsystems for software and hardware tracing, Performance Monitoring Unit (PMU) analysis, and system profiling work.

---

## 🎯 Executive Summary

For tracing framework development, performance analysis, and PMU integration, you need subsystems that expose hardware counters, implement tracing infrastructure, and provide observability into system behavior. This guide focuses on ftrace, perf events, hardware tracing (CoreSight, Intel PT), eBPF, and PMU drivers.

**Quick Start:** Begin with Phase 1 (kernel/trace, kernel/events) - these form the core of Linux tracing infrastructure.

---

## 📊 Subsystem Priority Matrix

### Critical Priority (Phase 1) - Core Tracing Infrastructure

| Subsystem | Files | Est. Time | Purpose | Why Critical |
|-----------|-------|-----------|---------|--------------|
| **kernel/trace** | 64 | ~3min | Ftrace infrastructure (function tracer, event tracing) | Foundation of kernel tracing |
| **kernel/events** | 6 | ~30s | Perf events core (PMU abstraction layer) | Hardware counter abstraction |
| **arch/arm64/kernel** (perf*.c) | 2 | ~15s | ARM64 PMU implementation | Architecture-specific PMU driver |
| **drivers/perf** | 59 | ~3min | SoC-specific PMU drivers (ARM, RISC-V) | Vendor PMU implementations |

**Phase 1 Total:** ~7 minutes, 131 files

### High Priority (Phase 2) - Hardware Tracing

| Subsystem | Files | Est. Time | Purpose | Why Important |
|-----------|-------|-----------|---------|---------------|
| **drivers/hwtracing/coresight** | 44 | ~2min | ARM CoreSight (ETM, ETB, STM) | ARM hardware trace capture |
| **drivers/hwtracing/intel_th** | 9 | ~30s | Intel Trace Hub | Intel hardware tracing |
| **drivers/hwtracing/stm** | 9 | ~30s | System Trace Module | Generic STM support |
| **kernel/bpf** | 55 | ~3min | eBPF runtime and verifier | Programmable tracing backend |

**Phase 2 Total:** ~6 minutes, 117 files

### Medium Priority (Phase 3) - Profiling & Timing

| Subsystem | Files | Est. Time | Purpose | Use Case |
|-----------|-------|-----------|---------|----------|
| **kernel/sched** | 31 | ~2min | Scheduler internals | Task scheduling traces |
| **kernel/time** | 32 | ~2min | Timekeeping and clocksources | Timestamp infrastructure |
| **kernel/locking** | 21 | ~1min | Lock contention tracking | Lock profiling |
| **kernel/printk** | 7 | ~30s | Kernel log buffer | Early boot tracing |

**Phase 3 Total:** ~6 minutes, 91 files

### Low Priority (Phase 4) - Extended Instrumentation

| Subsystem | Files | Est. Time | Purpose | When Needed |
|-----------|-------|-----------|---------|-------------|
| **kernel/irq** | ~20 | ~1min | IRQ subsystem | Interrupt latency tracing |
| **mm/** | 161 | ~7min | Memory management | Memory allocation tracing |
| **drivers/base** | 85 | ~2min | Driver core | Device probe timing |
| **arch/arm64/kvm** | ~50 | ~3min | KVM hypervisor | VM entry/exit tracing |

---

## 🚀 Recommended Ingestion Sequence

### Phase 1: Core Tracing Infrastructure (Start Here!)

```bash
# 1. Ftrace - Function tracing, event tracing, trace buffers
python3 src/main.py pipeline kernel/trace

# 2. Perf Events Core - PMU abstraction layer
python3 src/main.py pipeline kernel/events

# 3. ARM64 PMU Driver - Architecture-specific counters
python3 src/main.py pipeline arch/arm64/kernel

# 4. SoC PMU Drivers - Vendor-specific PMU implementations
python3 src/main.py pipeline drivers/perf

# Verify
python3 src/main.py stats
```

**What You Gain:**
- Understand ftrace event registration and ring buffer management
- Map PMU event lifecycle from registration to read
- Trace hardware counter overflow handling
- Analyze vendor PMU driver implementations

### Phase 2: Hardware Tracing

```bash
# 5. ARM CoreSight - ETM, ETB, STM hardware trace
python3 src/main.py pipeline drivers/hwtracing/coresight

# 6. Intel Trace Hub - Intel PT hardware tracing
python3 src/main.py pipeline drivers/hwtracing/intel_th

# 7. STM Generic Support - System Trace Module
python3 src/main.py pipeline drivers/hwtracing/stm

# 8. eBPF Runtime - Programmable tracing
python3 src/main.py pipeline kernel/bpf
```

**What You Gain:**
- CoreSight topology discovery and trace path setup
- Hardware trace buffer configuration
- eBPF program attachment to tracepoints and PMU events
- Intel PT packet decoder integration

### Phase 3: Profiling & Timing

```bash
# 9. Scheduler - Task scheduling events
python3 src/main.py pipeline kernel/sched

# 10. Timekeeping - Clocksource and timestamps
python3 src/main.py pipeline kernel/time

# 11. Locking - Lock contention profiling
python3 src/main.py pipeline kernel/locking

# 12. Printk - Early boot and kernel logging
python3 src/main.py pipeline kernel/printk
```

**What You Gain:**
- Scheduler tracepoint locations and context switch paths
- Clocksource selection and timestamp precision
- Lock acquisition/release tracing points
- Early boot trace buffer setup

---

## 📜 Quick Ingestion Script

Save as `scripts/ingest_trace_subsystems.sh`:

```bash
#!/bin/bash
# Ingest all critical tracing subsystems for kernel-graphrag-sentinel
# Total estimated time: ~20 minutes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "========================================="
echo "Trace Framework Ingestion Script"
echo "========================================="
echo ""

# Phase 1: Core Tracing Infrastructure (~7 minutes)
echo "=== Phase 1: Core Tracing (7 min) ==="
echo "[1/4] Ingesting kernel/trace (Ftrace)..."
python3 src/main.py pipeline kernel/trace

echo "[2/4] Ingesting kernel/events (Perf Events Core)..."
python3 src/main.py pipeline kernel/events

echo "[3/4] Ingesting arch/arm64/kernel (ARM64 PMU)..."
python3 src/main.py pipeline arch/arm64/kernel

echo "[4/4] Ingesting drivers/perf (SoC PMU Drivers)..."
python3 src/main.py pipeline drivers/perf

echo ""
echo "Phase 1 Complete! Core tracing subsystems ingested."
echo ""

# Phase 2: Hardware Tracing (~6 minutes)
echo "=== Phase 2: Hardware Tracing (6 min) ==="
echo "[1/4] Ingesting drivers/hwtracing/coresight (ARM CoreSight)..."
python3 src/main.py pipeline drivers/hwtracing/coresight

echo "[2/4] Ingesting drivers/hwtracing/intel_th (Intel Trace Hub)..."
python3 src/main.py pipeline drivers/hwtracing/intel_th

echo "[3/4] Ingesting drivers/hwtracing/stm (STM)..."
python3 src/main.py pipeline drivers/hwtracing/stm

echo "[4/4] Ingesting kernel/bpf (eBPF Runtime)..."
python3 src/main.py pipeline kernel/bpf

echo ""
echo "Phase 2 Complete! Hardware tracing subsystems ingested."
echo ""

# Phase 3: Profiling & Timing (~6 minutes)
echo "=== Phase 3: Profiling & Timing (6 min) ==="
echo "[1/4] Ingesting kernel/sched (Scheduler)..."
python3 src/main.py pipeline kernel/sched

echo "[2/4] Ingesting kernel/time (Timekeeping)..."
python3 src/main.py pipeline kernel/time

echo "[3/4] Ingesting kernel/locking (Lock Profiling)..."
python3 src/main.py pipeline kernel/locking

echo "[4/4] Ingesting kernel/printk (Kernel Logging)..."
python3 src/main.py pipeline kernel/printk

echo ""
echo "========================================="
echo "✅ All Trace Subsystems Ingested!"
echo "========================================="
echo ""

# Show final statistics
python3 src/main.py stats

echo ""
echo "Next Steps:"
echo "  1. Analyze ftrace: python3 src/main.py analyze trace_event_reg --llm"
echo "  2. Analyze PMU: python3 src/main.py analyze perf_event_open --max-depth 5"
echo "  3. Export call graph: python3 src/main.py export-graph ring_buffer_write --format mermaid"
echo ""
```

Make it executable:
```bash
chmod +x scripts/ingest_trace_subsystems.sh
./scripts/ingest_trace_subsystems.sh
```

---

## 🔍 Tracing-Specific Analysis Use Cases

### 1. Ftrace Event Registration Flow

**Question:** How does a kernel subsystem register a tracepoint with ftrace?

```bash
# Analyze event registration
python3 src/main.py analyze trace_event_reg --max-depth 4 --llm

# Find all tracepoint definitions
python3 src/main.py query "
MATCH (f:Function)
WHERE f.name =~ '.*trace_event.*' OR f.name =~ '.*tracepoint.*'
RETURN f.name, f.file_path, f.line_start
ORDER BY f.name
LIMIT 50
"

# Visualize event registration path
python3 src/main.py export-graph trace_event_reg --format mermaid -o ftrace_event_reg.md
```

**Output:** Complete flow from TRACE_EVENT() macro to ftrace ring buffer write.

### 2. Perf Event Lifecycle

**Question:** What happens from perf_event_open() to PMU counter read?

```bash
# Analyze perf_event_open syscall
python3 src/main.py analyze perf_event_open --max-depth 6 --llm

# Find PMU registration functions
python3 src/main.py query "
MATCH (f:Function)
WHERE f.name =~ '.*perf_pmu_register.*' OR f.name =~ '.*pmu_register.*'
RETURN f.name, f.file_path
ORDER BY f.file_path
"

# Export perf event lifecycle
python3 src/main.py export-graph perf_event_open --format dot -o perf_lifecycle.dot
dot -Tpng perf_lifecycle.dot -o perf_lifecycle.png
```

**Use Case:** Understanding PMU event configuration and overflow interrupts.

### 3. PMU Counter Overflow Handling

**Question:** How are PMU overflow interrupts handled?

```bash
# Analyze overflow interrupt path
python3 src/main.py analyze perf_event_overflow --max-depth 5

# Find all PMU interrupt handlers
python3 src/main.py query "
MATCH (f:Function)
WHERE f.name =~ '.*pmu.*irq.*' OR f.name =~ '.*armv8pmu_handle_irq.*'
RETURN f.name, f.file_path, f.line_start
ORDER BY f.name
"
```

**Use Case:** Debugging PMU interrupt storms or missed samples.

### 4. CoreSight Trace Path Setup

**Question:** How does CoreSight configure a trace path from source to sink?

```bash
# Analyze CoreSight path building
python3 src/main.py analyze coresight_build_path --max-depth 4 --llm

# Find all CoreSight device types
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'coresight'
  AND (f.name =~ '.*_enable.*' OR f.name =~ '.*_disable.*')
RETURN f.name, f.file_path
ORDER BY f.file_path
LIMIT 30
"
```

**Use Case:** ARM ETM trace collection setup for instruction trace.

### 5. eBPF Program Attachment

**Question:** How does an eBPF program attach to a tracepoint?

```bash
# Analyze eBPF attachment
python3 src/main.py analyze bpf_tracepoint_prog_attach --max-depth 5

# Find eBPF verifier entry points
python3 src/main.py query "
MATCH (f:Function)
WHERE f.name =~ '.*bpf_verifier.*' OR f.name =~ '.*bpf_check.*'
RETURN f.name, f.file_path
ORDER BY f.name
"

# Export eBPF attach flow
python3 src/main.py export-graph bpf_prog_attach --format mermaid
```

**Use Case:** Building custom eBPF-based tracing tools.

### 6. Ring Buffer Write Path

**Question:** How does ftrace write events to the ring buffer?

```bash
# Analyze ring buffer write
python3 src/main.py analyze ring_buffer_write --max-depth 4

# Find ring buffer allocation functions
python3 src/main.py query "
MATCH (f:Function)
WHERE f.name =~ '.*ring_buffer.*alloc.*' OR f.name =~ '.*ring_buffer.*reserve.*'
RETURN f.name, f.file_path
"
```

**Use Case:** Understanding ftrace performance and buffer sizing.

### 7. Scheduler Tracepoint Analysis

**Question:** Where are scheduler tracepoints located in the code?

```bash
# Find all scheduler tracepoints
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'kernel/sched'
  AND f.name =~ '.*trace.*'
RETURN f.name, f.file_path, f.line_start
ORDER BY f.file_path, f.line_start
"

# Analyze context switch path
python3 src/main.py analyze __schedule --max-depth 3 --llm
```

**Use Case:** Instrumenting scheduler for latency analysis.

### 8. Data Flow Analysis for Trace Data

**Question:** How does trace data flow from event to userspace?

```bash
# Ingest data flow for tracing subsystem
python3 src/main.py ingest-dataflow kernel/trace

# Track ring_buffer variable flows
python3 src/main.py dataflow ring_buffer --max-depth 5 --direction both

# Query trace data propagation
python3 src/main.py query "
MATCH path = (source:Variable)-[:FLOWS_TO*1..5]->(sink:Variable)
WHERE source.scope =~ '.*trace.*event.*'
  AND sink.scope =~ '.*ring_buffer.*'
RETURN source.scope, source.name, sink.scope, sink.name, length(path)
ORDER BY length(path) DESC
LIMIT 20
"
```

**Use Case:** Understanding trace data security and isolation.

---

## 🎯 Architecture-Specific PMU Drivers

### ARM64 PMU

```bash
# ARM64 PMU core
python3 src/main.py pipeline arch/arm64/kernel

# Analyze ARMv8 PMU driver
python3 src/main.py analyze armv8pmu_handle_irq --max-depth 4

# Find all ARM PMU events
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path =~ '.*arm.*pmu.*'
  AND f.name =~ '.*event.*'
RETURN f.name, f.file_path
"
```

### x86 PMU (Intel/AMD)

```bash
# x86 PMU core
python3 src/main.py pipeline arch/x86/events

# Intel PMU specific
python3 src/main.py pipeline arch/x86/events/intel

# AMD PMU specific
python3 src/main.py pipeline arch/x86/events/amd
```

### RISC-V PMU

```bash
# RISC-V SBI PMU
python3 src/main.py pipeline arch/riscv/kernel

# Analyze RISC-V PMU driver
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'riscv'
  AND f.name =~ '.*pmu.*'
RETURN f.name, f.file_path
"
```

---

## 🏢 Vendor-Specific PMU Drivers

### ARM SoC Vendors

#### ARM Cortex PMU (Generic)

```bash
# ARM Cortex-A/R/M PMU events
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'drivers/perf'
  AND f.file_path =~ '.*arm.*'
RETURN f.name, f.file_path
ORDER BY f.file_path
"
```

#### Qualcomm (Snapdragon)

```bash
# Qualcomm Kryo PMU
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'qcom'
  AND f.name =~ '.*pmu.*'
RETURN f.name, f.file_path
"
```

#### HiSilicon (Huawei Kirin)

```bash
# HiSilicon interconnect PMU
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'hisi'
  AND f.file_path CONTAINS 'perf'
RETURN f.name, f.file_path
"
```

#### NVIDIA (Tegra/Jetson)

```bash
# NVIDIA PMU drivers
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'tegra'
  AND f.name =~ '.*pmu.*'
RETURN f.name, f.file_path
"
```

### Intel Specific Tracing

```bash
# Intel Processor Trace (PT)
python3 src/main.py pipeline drivers/hwtracing/intel_th

# Intel PEBS (Precise Event Based Sampling)
python3 src/main.py pipeline arch/x86/events/intel

# Analyze Intel PT setup
python3 src/main.py analyze intel_pt_event_add --max-depth 4
```

---

## 🎪 Domain-Specific Tracing Extensions

### Real-Time Performance Analysis

```bash
# Interrupt latency tracing
python3 src/main.py pipeline kernel/irq

# Preemption tracking
python3 src/main.py pipeline kernel/sched

# Lock contention profiling
python3 src/main.py pipeline kernel/locking

# Query all scheduler tracepoints
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'kernel/sched'
  AND f.name =~ '.*trace.*'
RETURN f.name, f.file_path, f.line_start
ORDER BY f.line_start
"
```

### Memory Performance Tracing

```bash
# Memory allocator tracing
python3 src/main.py pipeline mm

# Page fault tracing
python3 src/main.py analyze do_page_fault --max-depth 3

# Find all memory tracepoints
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'mm/'
  AND f.name =~ '.*trace.*'
RETURN f.name, f.file_path
"
```

### Network Performance Tracing

```bash
# Network stack tracing
python3 src/main.py pipeline net/core

# Find network tracepoints
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'net/'
  AND f.name =~ '.*trace.*'
RETURN f.name, f.file_path
LIMIT 50
"
```

### Block I/O Tracing

```bash
# Block layer tracing
python3 src/main.py pipeline block

# Analyze block I/O submission
python3 src/main.py analyze submit_bio --max-depth 3

# Find block layer tracepoints
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'block/'
  AND f.name =~ '.*trace.*'
RETURN f.name, f.file_path
"
```

### Power Management Tracing

```bash
# CPU idle/frequency tracing
python3 src/main.py pipeline drivers/cpuidle
python3 src/main.py pipeline drivers/cpufreq

# Device PM tracing
python3 src/main.py pipeline drivers/base/power

# Find all PM tracepoints
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path =~ '.*cpuidle.*|.*cpufreq.*|.*power.*'
  AND f.name =~ '.*trace.*'
RETURN f.name, f.file_path
"
```

---

## 📊 Expected Database Statistics

After completing all three phases, you should have approximately:

```bash
python3 src/main.py stats
```

**Expected Output:**
```json
{
  "Function_count": 8000-12000,
  "CALLS_count": 25000-40000,
  "File_count": 300-400,
  "Subsystem_count": 12-15,
  "TestCase_count": 20-50,
  "COVERS_count": 50-100
}
```

---

## 💡 Best Practices

### 1. Start with Core Tracing Infrastructure

```bash
# Always begin with kernel/trace and kernel/events
python3 src/main.py pipeline kernel/trace
python3 src/main.py analyze trace_event_reg --llm  # Validate
python3 src/main.py pipeline kernel/events         # Continue
```

### 2. Generate Documentation for Complex Tracing Paths

```bash
# Create comprehensive PMU documentation
python3 src/main.py analyze perf_event_open --llm --output docs/pmu_event_lifecycle.md

# Document ftrace internals
python3 src/main.py analyze ring_buffer_write --llm --output docs/ftrace_ring_buffer.md
```

### 3. Visualize Trace Data Flow

```bash
# Mermaid diagram for ftrace event flow
python3 src/main.py export-graph trace_event_reg --format mermaid -o docs/ftrace_event_flow.md

# Graphviz for PMU interrupt handling
python3 src/main.py export-graph perf_event_overflow --format dot -o pmu_irq_flow.dot
dot -Tpng pmu_irq_flow.dot -o pmu_irq_flow.png
```

### 4. Query Tracepoint Locations

```bash
# Find all tracepoints in a subsystem
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'kernel/sched'
  AND f.name =~ '.*trace.*sched.*'
RETURN f.name, f.file_path, f.line_start
ORDER BY f.file_path, f.line_start
" > sched_tracepoints.txt
```

### 5. Data Flow Analysis for Trace Security

```bash
# Analyze trace data isolation
python3 src/main.py ingest-dataflow kernel/trace

# Check for trace data leaks
python3 src/main.py query "
MATCH path = (source:Variable)-[:FLOWS_TO*1..7]->(sink:Variable)
WHERE source.name =~ '.*user.*|.*unsafe.*'
  AND sink.scope =~ '.*ring_buffer.*|.*trace.*'
RETURN source.scope, source.name, sink.scope, length(path)
ORDER BY length(path) DESC
LIMIT 20
"
```

---

## 🐛 Troubleshooting

### Large Subsystems (kernel/trace, kernel/bpf)

These subsystems have many files and complex call graphs:

```bash
# Increase Neo4j memory if needed
sudo nano /etc/neo4j/neo4j.conf
# Set: server.memory.heap.max_size=4g

# Restart Neo4j
sudo systemctl restart neo4j
```

### Preprocessing Complexity

Tracing code often uses complex macros:

```bash
# Skip preprocessing for faster ingestion (may miss some macro-generated code)
python3 src/main.py ingest kernel/trace --skip-preprocessing

# Or enable for complete analysis (slower)
python3 src/main.py ingest kernel/trace  # Default: preprocessing enabled
```

### Partial Failures

If ingestion fails partway:

```bash
# Clear database and restart
python3 src/main.py ingest kernel/trace --clear-db
```

---

## 📈 Performance Expectations

| Subsystem | Files | Functions | Calls | Ingest Time |
|-----------|-------|-----------|-------|-------------|
| kernel/trace | 64 | ~2000 | ~6000 | 3min |
| kernel/events | 6 | ~150 | ~400 | 30s |
| drivers/perf | 59 | ~1500 | ~4000 | 3min |
| drivers/hwtracing/coresight | 44 | ~1200 | ~3500 | 2min |
| kernel/bpf | 55 | ~1800 | ~5000 | 3min |

---

## 🎯 Advanced Analysis Techniques

### 1. Cross-Subsystem Tracepoint Discovery

```bash
# Find all functions that invoke trace_*() helpers
python3 src/main.py query "
MATCH (caller:Function)-[:CALLS]->(tracefn:Function)
WHERE tracefn.name =~ 'trace_.*'
RETURN caller.file_path, caller.name, tracefn.name
ORDER BY caller.file_path
LIMIT 100
"
```

### 2. PMU Event Dependency Analysis

```bash
# Find PMU event enable/disable pairs
python3 src/main.py query "
MATCH (enable:Function)-[:CALLS*1..3]->(disable:Function)
WHERE enable.name =~ '.*pmu.*enable.*'
  AND disable.name =~ '.*pmu.*disable.*'
RETURN enable.name, disable.name, enable.file_path
"
```

### 3. Trace Buffer Sizing Impact

```bash
# Analyze ring buffer allocation
python3 src/main.py analyze ring_buffer_alloc --max-depth 3 --llm

# Find buffer size validation
python3 src/main.py query "
MATCH (f:Function)
WHERE f.name =~ '.*ring_buffer.*size.*'
RETURN f.name, f.file_path
"
```

### 4. eBPF Map Integration with Tracing

```bash
# Find eBPF map helpers used in tracing
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'kernel/bpf'
  AND f.name =~ '.*map.*'
RETURN f.name, f.file_path
ORDER BY f.name
"
```

---

## 🗺️ Use Case Scenarios

### Scenario 1: Building a Custom Profiler

**Goal:** Understand perf internals to build a custom profiling tool

```bash
# Phase 1: Understand perf event lifecycle
python3 src/main.py analyze perf_event_open --max-depth 6 --llm
python3 src/main.py export-graph perf_event_open --format mermaid

# Phase 2: Analyze sample collection
python3 src/main.py analyze perf_event_overflow --max-depth 4
python3 src/main.py analyze perf_output_sample --max-depth 3

# Phase 3: Study mmap ring buffer
python3 src/main.py analyze perf_mmap --max-depth 4
```

### Scenario 2: ARM CoreSight Trace Setup

**Goal:** Configure ETM trace collection on ARM SoC

```bash
# Understand CoreSight topology
python3 src/main.py analyze coresight_build_path --max-depth 5 --llm

# Analyze ETM configuration
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'coresight'
  AND f.name =~ '.*etm.*enable.*'
RETURN f.name, f.file_path, f.line_start
"

# Export CoreSight setup flow
python3 src/main.py export-graph coresight_enable --format dot
```

### Scenario 3: Ftrace Event Development

**Goal:** Add new ftrace events to a kernel subsystem

```bash
# Study event registration
python3 src/main.py analyze trace_event_reg --llm --output ftrace_howto.md

# Find existing event examples
python3 src/main.py query "
MATCH (f:Function)
WHERE f.name =~ 'trace_event_.*'
RETURN f.name, f.file_path
ORDER BY f.file_path
LIMIT 50
"
```

### Scenario 4: PMU Driver Porting

**Goal:** Port PMU driver to new ARM SoC

```bash
# Study existing ARM PMU drivers
python3 src/main.py top-functions --subsystem drivers/perf

# Analyze PMU registration
python3 src/main.py analyze perf_pmu_register --max-depth 4 --llm

# Find PMU interrupt handling patterns
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'drivers/perf'
  AND f.name =~ '.*irq.*'
RETURN f.name, f.file_path
"
```

---

## 🔬 Related Kernel Infrastructure

### Debugfs Integration

```bash
# Debugfs is used by ftrace and tracing tools
python3 src/main.py pipeline fs/debugfs

# Find debugfs operations in tracing
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'kernel/trace'
  AND f.name =~ '.*debugfs.*'
RETURN f.name, f.file_path
"
```

### Sysfs Integration

```bash
# Many PMU drivers expose sysfs interfaces
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'drivers/perf'
  AND f.name =~ '.*sysfs.*|.*attr.*'
RETURN f.name, f.file_path
"
```

---

## 📚 Related Documentation

- [Architecture Overview](architecture.md) - System design and graph schema
- [Data Flow Analysis Guide](dataflow_analysis_guide.md) - Variable tracking
- [BSP Porting Plan](bsp_porting_subsystems_ingestion_plan.md) - Hardware enablement
- [Query Examples](examples/query_examples.md) - 30+ Cypher queries
- [Neo4j Setup Guide](neo4j_setup.md) - Database tuning

---

## 🎯 Summary

**For SW/HW tracing and PMU work, prioritize:**

1. **kernel/trace** - Ftrace infrastructure foundation
2. **kernel/events** - Perf events PMU abstraction
3. **drivers/perf** - SoC-specific PMU drivers
4. **drivers/hwtracing/coresight** - ARM hardware trace (if ARM)
5. **kernel/bpf** - eBPF programmable tracing
6. **kernel/sched** - Scheduler tracepoints

These six subsystems provide comprehensive tracing analysis capabilities.

**Total investment:** ~20 minutes for all three phases.

---

## 🔍 Quick Reference Commands

### Essential Tracing Analyses

```bash
# Ftrace event registration
python3 src/main.py analyze trace_event_reg --llm

# PMU event lifecycle
python3 src/main.py analyze perf_event_open --max-depth 5

# Ring buffer write path
python3 src/main.py analyze ring_buffer_write --max-depth 3

# CoreSight trace setup (ARM)
python3 src/main.py analyze coresight_build_path --max-depth 4

# eBPF program attachment
python3 src/main.py analyze bpf_prog_attach --max-depth 4
```

### Find All Tracepoints

```bash
# Scheduler tracepoints
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'kernel/sched'
  AND f.name =~ '.*trace.*'
RETURN f.name, f.file_path, f.line_start
"

# Memory tracepoints
python3 src/main.py query "
MATCH (f:Function)
WHERE f.file_path CONTAINS 'mm/'
  AND f.name =~ '.*trace.*'
RETURN f.name, f.file_path
"

# All tracepoints across kernel
python3 src/main.py query "
MATCH (f:Function)
WHERE f.name =~ 'trace_.*'
RETURN f.name, f.file_path
ORDER BY f.file_path
LIMIT 100
"
```

---

**Built for performance engineers and tracing developers** 🔬📊
