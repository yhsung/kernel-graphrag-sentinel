#!/usr/bin/env python3
"""
Example usage of Module D: Data Flow Analysis

This script demonstrates how to use the data flow analysis capabilities
to track variables and data flows in C code.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.module_d import (
    VariableTracker,
    FlowBuilder,
    DataFlowIngestion,
)
from src.module_b.graph_store import Neo4jGraphStore


def example_variable_tracking():
    """Example 1: Extract variables from a C file."""
    print("=" * 60)
    print("Example 1: Variable Tracking")
    print("=" * 60)

    tracker = VariableTracker()

    # Use sample kernel C file
    sample_file = Path(__file__).parent.parent / "tests/fixtures/sample_kernel.c"

    if not sample_file.exists():
        print(f"Sample file not found: {sample_file}")
        return

    print(f"\nAnalyzing: {sample_file.name}\n")

    # Extract variables
    definitions, uses = tracker.extract_from_file(str(sample_file))

    print(f"Found {len(definitions)} variable definitions:")
    for var_def in definitions[:10]:  # Show first 10
        print(
            f"  - {var_def.name} ({var_def.var_type}) "
            f"in {var_def.scope} "
            f"[line {var_def.line_number}]"
            + (" 📌 parameter" if var_def.is_parameter else "")
            + (" 📍 pointer" if var_def.is_pointer else "")
        )

    print(f"\nFound {len(uses)} variable uses:")
    for var_use in uses[:10]:  # Show first 10
        print(
            f"  - {var_use.name} ({var_use.usage_type}) "
            f"in {var_use.function} "
            f"[line {var_use.line_number}]"
        )


def example_data_flow():
    """Example 2: Build data flow graph."""
    print("\n" + "=" * 60)
    print("Example 2: Data Flow Graph")
    print("=" * 60)

    builder = FlowBuilder()

    sample_file = Path(__file__).parent.parent / "tests/fixtures/sample_kernel.c"

    if not sample_file.exists():
        print(f"Sample file not found: {sample_file}")
        return

    print(f"\nBuilding data flows from: {sample_file.name}\n")

    # Build flows
    flows, def_use = builder.build_intra_procedural_flows(str(sample_file))

    print(f"Found {len(flows)} data flow edges:")
    for flow in flows[:15]:  # Show first 15
        flow_symbol = "→"
        if flow.to_var == "__RETURN__":
            flow_symbol = "↩️"

        print(
            f"  {flow.from_var} {flow_symbol} {flow.to_var} "
            f"({flow.flow_type.value}) "
            f"in {flow.function} "
            f"[line {flow.line_number}]"
        )


def example_neo4j_ingestion():
    """Example 3: Ingest data flow into Neo4j (requires running Neo4j)."""
    print("\n" + "=" * 60)
    print("Example 3: Neo4j Ingestion (Optional)")
    print("=" * 60)

    print("\nℹ️  This example requires Neo4j to be running.")
    print("To run Neo4j locally:")
    print("  docker run -p 7687:7687 -p 7474:7474 neo4j:latest")
    print("\nSet environment variables:")
    print("  export NEO4J_URI=bolt://localhost:7687")
    print("  export NEO4J_USERNAME=neo4j")
    print("  export NEO4J_PASSWORD=your_password")

    import os

    neo4j_uri = os.getenv("NEO4J_URI")
    if not neo4j_uri:
        print("\n⚠️  NEO4J_URI not set. Skipping Neo4j example.")
        return

    print(f"\n✅ Connecting to Neo4j at {neo4j_uri}...")

    try:
        # Connect to Neo4j
        graph_store = Neo4jGraphStore(
            uri=neo4j_uri,
            user=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
        )

        # Create ingestion pipeline
        ingestion = DataFlowIngestion(graph_store)

        # Setup schema
        print("Setting up data flow schema...")
        ingestion.setup_schema()

        # Ingest sample file
        sample_file = (
            Path(__file__).parent.parent / "tests/fixtures/sample_kernel.c"
        )

        print(f"\nIngesting: {sample_file.name}")
        stats = ingestion.ingest_file(str(sample_file), subsystem="sample")

        print(f"\n📊 Ingestion Results:")
        print(f"  Variables: {stats['variables']}")
        print(f"  Data flows: {stats['flows']}")
        print(f"  DEFINES relationships: {stats['defines_rels']}")
        print(f"  USES relationships: {stats['uses_rels']}")

        # Get statistics
        print(f"\n📈 Graph Statistics:")
        graph_stats = ingestion.get_variable_statistics()
        for key, value in graph_stats.items():
            print(f"  {key}: {value}")

        # Example queries
        print(f"\n🔍 Example Cypher Queries:")
        print("\n1. Find all pointer variables:")
        print("   MATCH (v:Variable {is_pointer: true}) RETURN v.name, v.type LIMIT 10")

        print("\n2. Find data flow chains:")
        print(
            "   MATCH path = (v1:Variable)-[:FLOWS_TO*1..3]->(v2:Variable) "
            "RETURN v1.name, v2.name, length(path)"
        )

        print("\n3. Find variables used but never defined:")
        print(
            "   MATCH (f:Function)-[:USES]->(v:Variable) "
            "WHERE NOT (f)-[:DEFINES]->(v) "
            "RETURN v.name, v.scope"
        )

        graph_store.close()
        print("\n✅ Neo4j ingestion complete!")

    except Exception as e:
        print(f"\n❌ Neo4j error: {e}")
        print("Make sure Neo4j is running and credentials are correct.")


def main():
    """Run all examples."""
    print("\n🔬 Module D: Data Flow Analysis Examples\n")

    # Run examples
    example_variable_tracking()
    example_data_flow()
    example_neo4j_ingestion()

    print("\n" + "=" * 60)
    print("✨ Examples complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
