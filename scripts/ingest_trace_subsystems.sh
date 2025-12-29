#!/bin/bash
# Ingest all critical tracing subsystems for kernel-graphrag-sentinel
# Based on: docs/trace_collection_framework_ingestion_plan.md
# Total estimated time: ~20 minutes

echo "========================================="
echo "Trace Framework Ingestion Script"
echo "========================================="
echo ""
echo "This script will ingest Linux kernel tracing subsystems:"
echo "  - Phase 1: Core Tracing Infrastructure (7 min)"
echo "  - Phase 2: Hardware Tracing (6 min)"
echo "  - Phase 3: Profiling & Timing (6 min)"
echo ""
echo "Total estimated time: ~20 minutes"
echo ""

# Check if Neo4j is running
echo "Checking Neo4j connection..."
if ! python3 -c "from src.module_b.graph_store import Neo4jGraphStore; Neo4jGraphStore().execute_query('RETURN 1')" 2>/dev/null; then
    echo "❌ ERROR: Cannot connect to Neo4j"
    echo "Please ensure Neo4j is running:"
    echo "  sudo systemctl start neo4j"
    exit 1
fi
echo "✅ Neo4j is running"
echo ""

# Phase 1: Core Tracing Infrastructure (~7 minutes)
echo "========================================="
echo "Phase 1: Core Tracing Infrastructure"
echo "========================================="
echo ""

echo "[1/4] Ingesting kernel/trace (Ftrace)..."
echo "  Purpose: Ftrace infrastructure (function tracer, event tracing)"
echo "  Files: 64, Est. time: ~3 min"
python3 src/main.py pipeline kernel/trace
python3 src/main.py ingest-dataflow kernel/trace
python3 src/main.py map-tests kernel/trace
echo "✅ kernel/trace ingested"
echo ""

echo "[2/4] Ingesting kernel/events (Perf Events Core)..."
echo "  Purpose: Perf events core (PMU abstraction layer)"
echo "  Files: 6, Est. time: ~30s"
python3 src/main.py pipeline kernel/events
python3 src/main.py ingest-dataflow kernel/events
python3 src/main.py map-tests kernel/events
echo "✅ kernel/events ingested"
echo ""

echo "[3/4] Ingesting arch/arm64/kernel (ARM64 PMU)..."
echo "  Purpose: ARM64 PMU implementation"
echo "  Files: 2, Est. time: ~15s"
python3 src/main.py pipeline arch/arm64/kernel
python3 src/main.py ingest-dataflow arch/arm64/kernel
python3 src/main.py map-tests arch/arm64/kernel
echo "✅ arch/arm64/kernel ingested"
echo ""

echo "[4/4] Ingesting drivers/perf (SoC PMU Drivers)..."
echo "  Purpose: SoC-specific PMU drivers (ARM, RISC-V)"
echo "  Files: 59, Est. time: ~3 min"
python3 src/main.py pipeline drivers/perf
python3 src/main.py ingest-dataflow drivers/perf
python3 src/main.py map-tests drivers/perf
echo "✅ drivers/perf ingested"
echo ""

echo "========================================="
echo "✅ Phase 1 Complete!"
echo "========================================="
echo ""

# Phase 2: Hardware Tracing (~6 minutes)
echo "========================================="
echo "Phase 2: Hardware Tracing"
echo "========================================="
echo ""

echo "[1/4] Ingesting drivers/hwtracing/coresight (ARM CoreSight)..."
echo "  Purpose: ARM CoreSight (ETM, ETB, STM)"
echo "  Files: 44, Est. time: ~2 min"
python3 src/main.py pipeline drivers/hwtracing/coresight
python3 src/main.py ingest-dataflow drivers/hwtracing/coresight
python3 src/main.py map-tests drivers/hwtracing/coresight
echo "✅ drivers/hwtracing/coresight ingested"
echo ""

echo "[2/4] Ingesting drivers/hwtracing/intel_th (Intel Trace Hub)..."
echo "  Purpose: Intel Trace Hub"
echo "  Files: 9, Est. time: ~30s"
python3 src/main.py pipeline drivers/hwtracing/intel_th
python3 src/main.py ingest-dataflow drivers/hwtracing/intel_th
python3 src/main.py map-tests drivers/hwtracing/intel_th
echo "✅ drivers/hwtracing/intel_th ingested"
echo ""

echo "[3/4] Ingesting drivers/hwtracing/stm (STM)..."
echo "  Purpose: System Trace Module"
echo "  Files: 9, Est. time: ~30s"
python3 src/main.py pipeline drivers/hwtracing/stm
python3 src/main.py ingest-dataflow drivers/hwtracing/stm
python3 src/main.py map-tests drivers/hwtracing/stm
echo "✅ drivers/hwtracing/stm ingested"
echo ""

echo "[4/4] Ingesting kernel/bpf (eBPF Runtime)..."
echo "  Purpose: eBPF runtime and verifier"
echo "  Files: 55, Est. time: ~3 min"
python3 src/main.py pipeline kernel/bpf
python3 src/main.py ingest-dataflow kernel/bpf
python3 src/main.py map-tests kernel/bpf
echo "✅ kernel/bpf ingested"
echo ""

echo "========================================="
echo "✅ Phase 2 Complete!"
echo "========================================="
echo ""

# Phase 3: Profiling & Timing (~6 minutes)
echo "========================================="
echo "Phase 3: Profiling & Timing"
echo "========================================="
echo ""

echo "[1/4] Ingesting kernel/sched (Scheduler)..."
echo "  Purpose: Scheduler internals"
echo "  Files: 31, Est. time: ~2 min"
python3 src/main.py pipeline kernel/sched
python3 src/main.py ingest-dataflow kernel/sched
python3 src/main.py map-tests kernel/sched
echo "✅ kernel/sched ingested"
echo ""

echo "[2/4] Ingesting kernel/time (Timekeeping)..."
echo "  Purpose: Timekeeping and clocksources"
echo "  Files: 32, Est. time: ~2 min"
python3 src/main.py pipeline kernel/time
python3 src/main.py ingest-dataflow kernel/time
python3 src/main.py map-tests kernel/time
echo "✅ kernel/time ingested"
echo ""

echo "[3/4] Ingesting kernel/locking (Lock Profiling)..."
echo "  Purpose: Lock contention tracking"
echo "  Files: 21, Est. time: ~1 min"
python3 src/main.py pipeline kernel/locking
python3 src/main.py ingest-dataflow kernel/locking
python3 src/main.py map-tests kernel/locking
echo "✅ kernel/locking ingested"
echo ""

echo "[4/4] Ingesting kernel/printk (Kernel Logging)..."
echo "  Purpose: Kernel log buffer"
echo "  Files: 7, Est. time: ~30s"
python3 src/main.py pipeline kernel/printk
python3 src/main.py ingest-dataflow kernel/printk
python3 src/main.py map-tests kernel/printk
echo "✅ kernel/printk ingested"
echo ""

echo "========================================="
echo "✅ Phase 3 Complete!"
echo "========================================="
echo ""

# Final statistics
echo "========================================="
echo "✅ All Trace Subsystems Ingested!"
echo "========================================="
echo ""
echo "Generating final database statistics..."
python3 src/main.py stats
echo ""

echo "========================================="
echo "Next Steps"
echo "========================================="
echo ""
echo "1. Analyze ftrace event registration:"
echo "   python3 src/main.py analyze trace_event_reg --max-depth 5 --llm"
echo ""
echo "2. Analyze perf event context scheduling:"
echo "   python3 src/main.py analyze perf_event_context_sched_in --max-depth 5"
echo ""
echo "3. Analyze ring buffer write operation:"
echo "   python3 src/main.py analyze ring_buffer_write --max-depth 4"
echo ""
echo "4. Export perf sample preparation call graph:"
echo "   python3 src/main.py export-graph perf_prepare_sample --format mermaid"
echo ""
echo "5. Show most called functions in tracing:"
echo "   python3 src/main.py top-functions --subsystem trace --min-callers 5"
echo ""
echo "For more analysis examples, see:"
echo "  docs/trace_collection_framework_ingestion_plan.md"
echo ""
echo "========================================="
echo "Ingestion Complete! 🎉"
echo "========================================="
