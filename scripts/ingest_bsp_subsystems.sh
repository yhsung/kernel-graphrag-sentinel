#!/bin/bash
# Ingest all critical BSP subsystems for kernel-graphrag-sentinel
# Based on: docs/bsp_porting_subsystems_ingestion_plan.md
# Total estimated time: ~40 minutes
echo "========================================="
echo "BSP Subsystem Ingestion Script"
echo "========================================="
echo ""
echo "This script will ingest Linux kernel BSP subsystems:"
echo "  - Phase 1: Foundation (6 min)"
echo "  - Phase 2: Hardware Control (20 min)"
echo "  - Phase 3: Buses & Power (15 min)"
echo ""
echo "Total estimated time: ~40 minutes"
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

# Phase 1: Foundation (~6 minutes)
echo "========================================="
echo "Phase 1: Foundation"
echo "========================================="
echo ""

echo "[1/3] Ingesting drivers/of (Device Tree)..."
echo "  Purpose: Device Tree parsing & platform device creation"
echo "  Files: 22, Est. time: ~30s"
python3 src/main.py pipeline drivers/of
python3 src/main.py ingest-dataflow drivers/of
python3 src/main.py map-tests drivers/of
echo "✅ drivers/of ingested"
echo ""

echo "[2/3] Ingesting drivers/base (Driver Core)..."
echo "  Purpose: Core driver model (platform drivers, buses)"
echo "  Files: 85, Est. time: ~2 min"
python3 src/main.py pipeline drivers/base
python3 src/main.py ingest-dataflow drivers/base
python3 src/main.py map-tests drivers/base
echo "✅ drivers/base ingested"
echo ""

echo "[3/3] Ingesting drivers/irqchip (Interrupt Controllers)..."
echo "  Purpose: Interrupt controller drivers (GIC, NVIC, etc.)"
echo "  Files: 143, Est. time: ~3 min"
python3 src/main.py pipeline drivers/irqchip
python3 src/main.py ingest-dataflow drivers/irqchip
python3 src/main.py map-tests drivers/irqchip
echo "✅ drivers/irqchip ingested"
echo ""

echo "========================================="
echo "✅ Phase 1 Complete!"
echo "========================================="
echo ""

# Phase 2: Hardware Control (~20 minutes)
echo "========================================="
echo "Phase 2: Hardware Control"
echo "========================================="
echo ""

echo "[1/4] Ingesting drivers/clk (Clock Framework)..."
echo "  Purpose: Common Clock Framework (CCF)"
echo "  Files: 1061, Est. time: ~8 min"
python3 src/main.py pipeline drivers/clk
python3 src/main.py ingest-dataflow drivers/clk
python3 src/main.py map-tests drivers/clk
echo "✅ drivers/clk ingested"
echo ""

echo "[2/4] Ingesting drivers/pinctrl (Pin Control)..."
echo "  Purpose: Pin multiplexing and electrical config"
echo "  Files: 450, Est. time: ~6 min"
python3 src/main.py pipeline drivers/pinctrl
python3 src/main.py ingest-dataflow drivers/pinctrl
python3 src/main.py map-tests drivers/pinctrl
echo "✅ drivers/pinctrl ingested"
echo ""

echo "[3/4] Ingesting drivers/gpio (GPIO)..."
echo "  Purpose: GPIO operations and chip drivers"
echo "  Files: 205, Est. time: ~4 min"
python3 src/main.py pipeline drivers/gpio
python3 src/main.py ingest-dataflow drivers/gpio
python3 src/main.py map-tests drivers/gpio
echo "✅ drivers/gpio ingested"
echo ""

echo "[4/4] Ingesting arch/arm64/kernel (ARM64 Architecture)..."
echo "  Purpose: ARM64 architecture-specific code"
echo "  Files: 79, Est. time: ~2 min"
python3 src/main.py pipeline arch/arm64/kernel
python3 src/main.py ingest-dataflow arch/arm64/kernel
python3 src/main.py map-tests arch/arm64/kernel
echo "✅ arch/arm64/kernel ingested"
echo ""

echo "========================================="
echo "✅ Phase 2 Complete!"
echo "========================================="
echo ""

# Phase 3: Buses & Power (~15 minutes)
echo "========================================="
echo "Phase 3: Buses & Power"
echo "========================================="
echo ""

echo "[1/6] Ingesting drivers/regulator (Voltage Regulators)..."
echo "  Purpose: Voltage regulator framework"
echo "  Files: 212, Est. time: ~4 min"
python3 src/main.py pipeline drivers/regulator
python3 src/main.py ingest-dataflow drivers/regulator
python3 src/main.py map-tests drivers/regulator
echo "✅ drivers/regulator ingested"
echo ""

echo "[2/6] Ingesting drivers/dma (DMA Engine)..."
echo "  Purpose: DMA engine framework"
echo "  Files: 165, Est. time: ~3 min"
python3 src/main.py pipeline drivers/dma
python3 src/main.py ingest-dataflow drivers/dma
python3 src/main.py map-tests drivers/dma
echo "✅ drivers/dma ingested"
echo ""

echo "[3/6] Ingesting drivers/i2c (I2C Bus)..."
echo "  Purpose: I2C bus infrastructure"
echo "  Files: 174, Est. time: ~3 min"
python3 src/main.py pipeline drivers/i2c
python3 src/main.py ingest-dataflow drivers/i2c
python3 src/main.py map-tests drivers/i2c
echo "✅ drivers/i2c ingested"
echo ""

echo "[4/6] Ingesting drivers/spi (SPI Bus)..."
echo "  Purpose: SPI bus infrastructure"
echo "  Files: 170, Est. time: ~3 min"
python3 src/main.py pipeline drivers/spi
python3 src/main.py ingest-dataflow drivers/spi
python3 src/main.py map-tests drivers/spi
echo "✅ drivers/spi ingested"
echo ""

echo "[5/6] Ingesting drivers/mmc/core (MMC/SD Core)..."
echo "  Purpose: MMC/SD/eMMC core"
echo "  Files: 26, Est. time: ~30s"
python3 src/main.py pipeline drivers/mmc/core
python3 src/main.py ingest-dataflow drivers/mmc/core
python3 src/main.py map-tests drivers/mmc/core
echo "✅ drivers/mmc/core ingested"
echo ""

echo "[6/6] Ingesting drivers/usb/core (USB Core)..."
echo "  Purpose: USB core infrastructure"
echo "  Files: 22, Est. time: ~30s"
python3 src/main.py pipeline drivers/usb/core
python3 src/main.py ingest-dataflow drivers/usb/core
python3 src/main.py map-tests drivers/usb/core
echo "✅ drivers/usb/core ingested"
echo ""

echo "========================================="
echo "✅ Phase 3 Complete!"
echo "========================================="
echo ""

# Final statistics
echo "========================================="
echo "✅ All BSP Subsystems Ingested!"
echo "========================================="
echo ""
echo "Generating final database statistics..."
python3 src/main.py stats
echo ""

echo "========================================="
echo "Next Steps"
echo "========================================="
echo ""
echo "1. Analyze Device Tree platform device creation:"
echo "   python3 src/main.py analyze of_platform_populate --max-depth 4 --llm"
echo ""
echo "2. Analyze clock enable flow:"
echo "   python3 src/main.py analyze clk_prepare_enable --max-depth 5"
echo ""
echo "3. Export platform driver registration graph:"
echo "   python3 src/main.py export-graph platform_driver_register --format mermaid"
echo ""
echo "4. Query all probe functions:"
echo "   python3 src/main.py query \"MATCH (f:Function) WHERE f.name =~ '.*_probe' RETURN f.name, f.file_path LIMIT 50\""
echo ""
echo "For more analysis examples, see:"
echo "  docs/bsp_porting_subsystems_ingestion_plan.md"
echo ""
echo "========================================="
echo "Ingestion Complete! 🎉"
echo "========================================="
