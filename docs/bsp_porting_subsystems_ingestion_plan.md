# BSP Porting Subsystems Ingestion Plan

**Kernel-GraphRAG Sentinel: BSP Development Focus**

This guide provides a structured approach to ingesting Linux kernel subsystems specifically for Board Support Package (BSP) development and hardware enablement work.

---

## 🎯 Executive Summary

For BSP porting, you need different subsystems than filesystem or network development. This guide focuses on hardware abstraction, driver frameworks, and platform-specific infrastructure critical for bringing up new hardware platforms.

**Quick Start:** Begin with Phase 1 (Device Tree, Driver Core, IRQ) - these three subsystems form the foundation of any BSP.

---

## 📊 Subsystem Priority Matrix

### Critical Priority (Phase 1) - Foundation

| Subsystem | Files | Est. Time | Purpose | Why Critical |
|-----------|-------|-----------|---------|--------------|
| **drivers/of** | 22 | ~30s | Device Tree parsing & platform device creation | Heart of BSP - parses hardware description |
| **drivers/base** | 85 | ~2min | Core driver model (platform drivers, buses) | Driver registration, probe mechanism |
| **drivers/irqchip** | 143 | ~3min | Interrupt controller drivers (GIC, NVIC, etc.) | Critical for boot and interrupt handling |

**Phase 1 Total:** ~6 minutes, 250 files

### High Priority (Phase 2) - Hardware Control

| Subsystem | Files | Est. Time | Purpose | Why Important |
|-----------|-------|-----------|---------|---------------|
| **drivers/clk** | 1061 | ~8min | Common Clock Framework (CCF) | Every peripheral needs clock management |
| **drivers/pinctrl** | 450 | ~6min | Pin multiplexing and electrical config | Configure pins before using peripherals |
| **drivers/gpio** | 205 | ~4min | GPIO operations and chip drivers | Digital I/O control |
| **arch/arm64/kernel** | 79 | ~2min | ARM64 architecture-specific code | Boot, exceptions, ARM-specific features |

**Phase 2 Total:** ~20 minutes, 1795 files

### Medium Priority (Phase 3) - Buses & Power

| Subsystem | Files | Est. Time | Purpose | Use Case |
|-----------|-------|-----------|---------|----------|
| **drivers/regulator** | 212 | ~4min | Voltage regulator framework | Power domain management, PMIC control |
| **drivers/dma** | 165 | ~3min | DMA engine framework | High-speed memory transfers |
| **drivers/i2c** | 174 | ~3min | I2C bus infrastructure | PMICs, sensors, touchscreens |
| **drivers/spi** | 170 | ~3min | SPI bus infrastructure | Flash storage, displays, sensors |
| **drivers/mmc/core** | 26 | ~30s | MMC/SD/eMMC core | Storage interface |
| **drivers/usb/core** | 22 | ~30s | USB core infrastructure | USB host/device support |

**Phase 3 Total:** ~15 minutes, 769 files

### Low Priority (Phase 4) - Specialized

| Subsystem | Files | Est. Time | Purpose | When Needed |
|-----------|-------|-----------|---------|-------------|
| **drivers/pci** | 196 | ~4min | PCIe infrastructure | Desktop/server platforms |
| **drivers/net/ethernet** | ~300 | ~5min | Ethernet drivers | Network connectivity |
| **drivers/watchdog** | ~300 | ~5min | Watchdog timer drivers | System reliability |
| **drivers/thermal** | ~200 | ~4min | Thermal management | Temperature monitoring |
| **drivers/pwm** | ~150 | ~3min | PWM framework | Backlight, motor control |
| **drivers/iio** | ~500 | ~8min | Industrial I/O (sensors) | Automotive, IoT applications |

---

## 🚀 Recommended Ingestion Sequence

### Phase 1: Foundation (Start Here!)

```bash
# 1. Device Tree - Hardware description parsing
python3 src/main.py pipeline drivers/of

# 2. Driver Core - Platform device model
python3 src/main.py pipeline drivers/base

# 3. Interrupt Controllers - IRQ handling
python3 src/main.py pipeline drivers/irqchip

# Verify
python3 src/main.py stats
```

**What You Gain:**
- Understand how Device Tree bindings create platform devices
- Map driver probe/remove sequences
- Trace interrupt handling from hardware to handler

### Phase 2: Hardware Control

```bash
# 4. Clock Framework - Peripheral clock management
python3 src/main.py pipeline drivers/clk

# 5. Pin Control - Muxing and electrical configuration
python3 src/main.py pipeline drivers/pinctrl

# 6. GPIO - Digital I/O
python3 src/main.py pipeline drivers/gpio

# 7. Architecture-Specific (ARM64 example)
python3 src/main.py pipeline arch/arm64/kernel
```

**What You Gain:**
- Clock dependency chains for any peripheral
- Pin muxing requirements before driver initialization
- GPIO request/configuration flows

### Phase 3: Buses & Power

```bash
# 8. Voltage Regulators - Power domains
python3 src/main.py pipeline drivers/regulator

# 9. DMA Engine - High-speed transfers
python3 src/main.py pipeline drivers/dma

# 10. I2C - Common peripheral bus
python3 src/main.py pipeline drivers/i2c

# 11. SPI - Serial peripheral interface
python3 src/main.py pipeline drivers/spi

# 12. MMC - eMMC/SD storage
python3 src/main.py pipeline drivers/mmc/core

# 13. USB - Universal Serial Bus
python3 src/main.py pipeline drivers/usb/core
```

**What You Gain:**
- Complete bus infrastructure understanding
- Power sequencing dependencies
- DMA channel allocation and usage patterns

---

## 📜 Quick Ingestion Script

Save as `scripts/ingest_bsp_subsystems.sh`:

```bash
#!/bin/bash
# Ingest all critical BSP subsystems for kernel-graphrag-sentinel
# Total estimated time: ~40 minutes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "========================================="
echo "BSP Subsystem Ingestion Script"
echo "========================================="
echo ""

# Phase 1: Foundation (~6 minutes)
echo "=== Phase 1: Foundation (6 min) ==="
echo "[1/3] Ingesting drivers/of (Device Tree)..."
python3 src/main.py pipeline drivers/of

echo "[2/3] Ingesting drivers/base (Driver Core)..."
python3 src/main.py pipeline drivers/base

echo "[3/3] Ingesting drivers/irqchip (Interrupt Controllers)..."
python3 src/main.py pipeline drivers/irqchip

echo ""
echo "Phase 1 Complete! Foundation subsystems ingested."
echo ""

# Phase 2: Hardware Control (~20 minutes)
echo "=== Phase 2: Hardware Control (20 min) ==="
echo "[1/4] Ingesting drivers/clk (Clock Framework)..."
python3 src/main.py pipeline drivers/clk

echo "[2/4] Ingesting drivers/pinctrl (Pin Control)..."
python3 src/main.py pipeline drivers/pinctrl

echo "[3/4] Ingesting drivers/gpio (GPIO)..."
python3 src/main.py pipeline drivers/gpio

echo "[4/4] Ingesting arch/arm64/kernel (ARM64 Architecture)..."
python3 src/main.py pipeline arch/arm64/kernel

echo ""
echo "Phase 2 Complete! Hardware control subsystems ingested."
echo ""

# Phase 3: Buses & Power (~15 minutes)
echo "=== Phase 3: Buses & Power (15 min) ==="
echo "[1/6] Ingesting drivers/regulator (Voltage Regulators)..."
python3 src/main.py pipeline drivers/regulator

echo "[2/6] Ingesting drivers/dma (DMA Engine)..."
python3 src/main.py pipeline drivers/dma

echo "[3/6] Ingesting drivers/i2c (I2C Bus)..."
python3 src/main.py pipeline drivers/i2c

echo "[4/6] Ingesting drivers/spi (SPI Bus)..."
python3 src/main.py pipeline drivers/spi

echo "[5/6] Ingesting drivers/mmc/core (MMC/SD Core)..."
python3 src/main.py pipeline drivers/mmc/core

echo "[6/6] Ingesting drivers/usb/core (USB Core)..."
python3 src/main.py pipeline drivers/usb/core

echo ""
echo "========================================="
echo "✅ All BSP Subsystems Ingested!"
echo "========================================="
echo ""

# Show final statistics
python3 src/main.py stats

echo ""
echo "Next Steps:"
echo "  1. Analyze key functions: python3 src/main.py analyze platform_driver_register"
echo "  2. Export call graphs: python3 src/main.py export-graph of_platform_populate --format mermaid"
echo "  3. Query relationships: python3 src/main.py query 'MATCH (f:Function) RETURN count(f)'"
echo ""
```

Make it executable:
```bash
chmod +x scripts/ingest_bsp_subsystems.sh
./scripts/ingest_bsp_subsystems.sh
```

---

## 🔍 BSP-Specific Analysis Use Cases

### 1. Device Tree Platform Device Creation

**Question:** How does a device in the Device Tree become a platform device?

```bash
# Analyze the core function
python3 src/main.py analyze of_platform_populate --max-depth 4 --llm

# Find all "compatible" matching functions
python3 src/main.py query "
MATCH (f:Function)
WHERE f.name =~ '.*of_match.*' OR f.name =~ '.*compatible.*'
RETURN f.name, f.file_path, f.line_start
ORDER BY f.name
LIMIT 30
"
```

**Output:** Complete call chain from Device Tree parsing to driver probe.

### 2. Clock Dependency Analysis

**Question:** What happens when I enable a clock?

```bash
# Deep dive into clock enable
python3 src/main.py analyze clk_prepare_enable --max-depth 5

# Find all clock provider registration
python3 src/main.py query "
MATCH (f:Function)
WHERE f.name =~ '.*clk_register.*' OR f.name =~ '.*clk_hw_register.*'
RETURN f.name, f.file_path
ORDER BY f.name
"

# Export clock enable call graph
python3 src/main.py export-graph clk_prepare_enable --format mermaid -o clk_enable_flow.md
```

**Use Case:** Understanding clock parent/child relationships before adding new clock driver.

### 3. GPIO Configuration Flow

**Question:** What's the complete flow from GPIO request to line configuration?

```bash
# Analyze GPIO request
python3 src/main.py analyze gpio_request --max-depth 3

# Find GPIO-to-pinctrl interactions
python3 src/main.py query "
MATCH path = (pinctrl:Function)-[:CALLS*1..3]->(gpio:Function)
WHERE pinctrl.file_path CONTAINS 'pinctrl'
  AND gpio.file_path CONTAINS 'gpio'
RETURN pinctrl.name, gpio.name, length(path) as depth
ORDER BY depth
LIMIT 20
"
```

**Use Case:** Debugging GPIO muxing issues in new board bring-up.

### 4. Platform Driver Registration

**Question:** What happens when platform_driver_register() is called?

```bash
# Generate comprehensive report
python3 src/main.py analyze platform_driver_register --llm --output platform_driver_guide.md

# Find all probe functions
python3 src/main.py query "
MATCH (f:Function)
WHERE f.name =~ '.*_probe' OR f.name = 'probe'
RETURN f.name, f.file_path
ORDER BY f.file_path
LIMIT 50
"
```

**Output:** Documentation-quality guide for driver development.

### 5. Interrupt Handling Chain

**Question:** Trace interrupt from hardware assertion to handler execution

```bash
# Analyze handle_irq with deep tracing
python3 src/main.py analyze handle_irq --max-depth 6 --llm

# Find all IRQ chip drivers
python3 src/main.py top-functions --subsystem irqchip --min-callers 5

# Visualize interrupt flow
python3 src/main.py export-graph handle_domain_irq --format dot -o irq_flow.dot
dot -Tpng irq_flow.dot -o irq_flow.png
```

**Use Case:** Adding interrupt controller support for new SoC.

### 6. I2C Transfer Flow

**Question:** What happens during an I2C transaction?

```bash
# Analyze I2C transfer
python3 src/main.py analyze i2c_transfer --max-depth 4

# Find I2C adapter registration
python3 src/main.py query "
MATCH (f:Function)
WHERE f.name =~ '.*i2c_add.*adapter.*'
RETURN f.name, f.file_path
"
```

**Use Case:** Debugging I2C communication issues with PMIC or sensors.

### 7. Data Flow Analysis for Device Tree Properties

**Question:** How are Device Tree properties propagated through the system?

```bash
# Ingest data flow for Device Tree subsystem
python3 src/main.py ingest-dataflow drivers/of

# Track "compatible" string usage
python3 src/main.py dataflow compatible --max-depth 5 --direction both

# Query taint analysis for DT data
python3 src/main.py query "
MATCH path = (source:Variable)-[:FLOWS_TO*1..5]->(sink:Variable)
WHERE source.name =~ '.*compatible.*' OR source.name =~ '.*of_node.*'
RETURN source.scope, source.name, sink.scope, sink.name, length(path)
ORDER BY length(path) DESC
LIMIT 20
"
```

**Use Case:** Security analysis of Device Tree parsing code.

---

## 🎯 Architecture-Specific Additions

### ARM64 Platforms

```bash
# Core kernel
python3 src/main.py pipeline arch/arm64/kernel

# Memory management
python3 src/main.py pipeline arch/arm64/mm

# KVM virtualization (if needed)
python3 src/main.py pipeline arch/arm64/kvm
```

### ARM32 Platforms

```bash
python3 src/main.py pipeline arch/arm/kernel
python3 src/main.py pipeline arch/arm/mm
python3 src/main.py pipeline arch/arm/mach-*  # Specific to your SoC vendor
```

### RISC-V Platforms

```bash
python3 src/main.py pipeline arch/riscv/kernel
python3 src/main.py pipeline arch/riscv/mm
```

### x86_64 Platforms

```bash
python3 src/main.py pipeline arch/x86/kernel
python3 src/main.py pipeline arch/x86/platform
```

---

## 🏢 Vendor-Specific Subsystems

### Qualcomm (Snapdragon, QCS, etc.)

```bash
# Qualcomm-specific drivers
python3 src/main.py pipeline drivers/clk/qcom
python3 src/main.py pipeline drivers/pinctrl/qcom
python3 src/main.py pipeline drivers/soc/qcom

# ARM System MMU (SMMU) - common on Qualcomm
python3 src/main.py pipeline drivers/iommu
```

### NXP (i.MX, Layerscape)

```bash
# i.MX specific
python3 src/main.py pipeline drivers/clk/imx
python3 src/main.py pipeline drivers/pinctrl/freescale
python3 src/main.py pipeline drivers/soc/imx
```

### Texas Instruments (AM335x, AM62x, etc.)

```bash
# TI-specific
python3 src/main.py pipeline drivers/clk/ti
python3 src/main.py pipeline drivers/soc/ti
```

### Rockchip (RK3588, RK3399, etc.)

```bash
# Rockchip-specific
python3 src/main.py pipeline drivers/clk/rockchip
python3 src/main.py pipeline drivers/pinctrl/rockchip
```

### MediaTek

```bash
# MediaTek-specific
python3 src/main.py pipeline drivers/clk/mediatek
python3 src/main.py pipeline drivers/pinctrl/mediatek
python3 src/main.py pipeline drivers/soc/mediatek
```

---

## 🎪 Domain-Specific Extensions

### Automotive BSP

```bash
# CAN bus
python3 src/main.py pipeline drivers/net/can

# Industrial I/O (sensors)
python3 src/main.py pipeline drivers/iio

# Watchdog (safety)
python3 src/main.py pipeline drivers/watchdog

# Real-time (if using PREEMPT_RT)
python3 src/main.py pipeline kernel/locking
```

### IoT/Embedded BSP

```bash
# Low-power management
python3 src/main.py pipeline drivers/cpuidle
python3 src/main.py pipeline drivers/cpufreq

# Sensors
python3 src/main.py pipeline drivers/iio

# Wireless
python3 src/main.py pipeline drivers/net/wireless
```

### Industrial BSP

```bash
# Fieldbus protocols
python3 src/main.py pipeline drivers/net/ethernet

# Industrial I/O
python3 src/main.py pipeline drivers/iio

# PWM (motor control)
python3 src/main.py pipeline drivers/pwm

# Counter (encoders)
python3 src/main.py pipeline drivers/counter
```

### Multimedia BSP

```bash
# V4L2 (cameras)
python3 src/main.py pipeline drivers/media/v4l2-core

# Display (DRM/KMS)
python3 src/main.py pipeline drivers/gpu/drm

# Audio (ALSA)
python3 src/main.py pipeline sound/core
python3 src/main.py pipeline sound/soc
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
  "Function_count": 15000-20000,
  "CALLS_count": 40000-60000,
  "File_count": 800-1000,
  "Subsystem_count": 13-15,
  "TestCase_count": 50-100,
  "COVERS_count": 100-200
}
```

---

## 💡 Best Practices

### 1. Start Small, Expand Gradually

Don't ingest everything at once. Start with Phase 1, validate results, then expand.

```bash
# Good approach
python3 src/main.py pipeline drivers/of
python3 src/main.py analyze of_platform_populate  # Validate
python3 src/main.py pipeline drivers/base         # Then continue
```

### 2. Use LLM Reports for Complex Functions

```bash
# Generate comprehensive documentation
python3 src/main.py analyze platform_driver_register --llm --output docs/platform_driver_analysis.md
```

### 3. Export Call Graphs for Documentation

```bash
# Mermaid format - embeddable in Markdown
python3 src/main.py export-graph clk_prepare_enable --format mermaid -o docs/clk_enable_flow.md

# DOT format - render with Graphviz
python3 src/main.py export-graph gpio_request --format dot -o gpio_flow.dot
dot -Tpng gpio_flow.dot -o gpio_flow.png
```

### 4. Create Custom Queries for Your SoC

Save common queries in a script:

```bash
# scripts/analyze_platform_device.sh
#!/bin/bash
echo "=== Platform Device Creation Flow ==="
python3 src/main.py analyze of_platform_populate --max-depth 3

echo "=== All Platform Drivers ==="
python3 src/main.py query "
MATCH (f:Function)
WHERE f.name =~ '.*_probe'
  AND f.file_path CONTAINS 'drivers/'
RETURN f.name, f.file_path
ORDER BY f.file_path
"
```

### 5. Leverage Data Flow for Security Analysis

```bash
# Analyze Device Tree input handling
python3 src/main.py ingest-dataflow drivers/of
python3 src/main.py dataflow of_node --max-depth 5

# Taint analysis for external inputs
python3 src/main.py query "
MATCH path = (source:Variable)-[:FLOWS_TO*1..5]->(sink:Variable)
WHERE source.name =~ '.*of_.*|.*dt_.*'
RETURN source.scope, sink.scope, length(path)
ORDER BY length(path) DESC
LIMIT 20
"
```

---

## 🐛 Troubleshooting

### Neo4j Memory Issues

For large subsystems like `drivers/clk` (1061 files), you may need to increase Neo4j heap:

Edit `/etc/neo4j/neo4j.conf`:
```ini
server.memory.heap.initial_size=2g
server.memory.heap.max_size=4g
```

Restart Neo4j:
```bash
sudo systemctl restart neo4j
```

### Long Preprocessing Times

For subsystems with complex macros, preprocessing can be slow. Skip if needed:

```bash
python3 src/main.py ingest drivers/clk --skip-preprocessing
```

### Partial Ingestion

If ingestion fails midway, clear and restart:

```bash
python3 src/main.py ingest drivers/clk --clear-db
```

---

## 📈 Performance Expectations

| Subsystem Size | Files | Functions | Calls | Ingest Time |
|----------------|-------|-----------|-------|-------------|
| Small (drivers/of) | 22 | ~200 | ~500 | 30s |
| Medium (drivers/base) | 85 | ~800 | ~2000 | 2min |
| Large (drivers/clk) | 1061 | ~5000 | ~15000 | 8min |
| Very Large (drivers/net) | 2000+ | ~10000 | ~30000 | 15-20min |

---

## 🗺️ Future Enhancements

### Planned for v0.3.0

- **Device Tree Binding Validation**: Automatic checking of DT bindings against driver code
- **Power Sequence Analysis**: Regulator dependency graph visualization
- **Clock Tree Visualization**: Parent-child clock relationships
- **Cross-Subsystem Dependency Detection**: Automatic detection of layering violations

### Planned for v0.4.0

- **BSP Bring-up Checklist Generator**: Automated analysis of required drivers for a platform
- **Driver Template Generator**: Generate skeleton drivers based on similar existing drivers
- **ABI Stability Checking**: Detect changes to exported symbols and driver APIs

---

## 📚 Related Documentation

- [Architecture Overview](architecture.md) - System design and graph schema
- [Data Flow Analysis Guide](dataflow_analysis_guide.md) - Variable tracking for security
- [LLM Provider Guide](llm_provider_guide.md) - AI-powered report configuration
- [Query Examples](examples/query_examples.md) - 30+ Neo4j Cypher queries
- [Neo4j Setup Guide](neo4j_setup.md) - Database installation and tuning

---

## 🎯 Summary

**For BSP porting work, prioritize:**

1. **drivers/of** - Device Tree foundation
2. **drivers/base** - Driver core infrastructure
3. **drivers/irqchip** - Interrupt handling
4. **drivers/clk** - Clock management
5. **drivers/pinctrl** - Pin configuration
6. **drivers/gpio** - GPIO control

These six subsystems provide 80% of the value for BSP development.

**Total investment:** ~20 minutes of ingestion time for comprehensive BSP analysis capabilities.

---

**Built for hardware enablement teams** 🔧
