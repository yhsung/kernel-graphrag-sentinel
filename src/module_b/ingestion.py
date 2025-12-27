"""
Module B: Data Ingestion
Ingests extracted kernel code data into Neo4j graph database.
"""

import sys
from pathlib import Path
from typing import List, Tuple, Optional
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.module_a.extractor import FunctionNode, CallEdge, FunctionExtractor
from src.module_b.graph_store import Neo4jGraphStore
from src.module_b.schema import (
    FunctionGraphNode, CallsRelationship,
    FileGraphNode, SubsystemGraphNode,
    ContainsRelationship, BelongsToRelationship
)

logger = logging.getLogger(__name__)


class GraphIngestion:
    """Handles ingestion of kernel code analysis data into Neo4j."""

    def __init__(self, graph_store: Neo4jGraphStore):
        """
        Initialize the ingestion manager.

        Args:
            graph_store: Neo4jGraphStore instance
        """
        self.graph_store = graph_store

    def ingest_functions(self, functions: List[FunctionNode]) -> int:
        """
        Ingest function nodes into the graph.

        Args:
            functions: List of FunctionNode objects from extractor

        Returns:
            Number of functions ingested
        """
        logger.info(f"Ingesting {len(functions)} functions...")

        # Convert to graph nodes
        graph_nodes = []
        for func in functions:
            node = FunctionGraphNode(
                name=func.name,
                file_path=func.file_path,
                line_start=func.line_start,
                line_end=func.line_end,
                subsystem=func.subsystem,
                is_static=func.is_static
            )
            graph_nodes.append(node)

        # Batch upsert
        self.graph_store.upsert_nodes_batch(graph_nodes)

        logger.info(f"Successfully ingested {len(functions)} functions")
        return len(functions)

    def ingest_calls(self, calls: List[CallEdge]) -> int:
        """
        Ingest function call relationships into the graph.

        Args:
            calls: List of CallEdge objects from extractor

        Returns:
            Number of call relationships ingested
        """
        logger.info(f"Ingesting {len(calls)} call relationships...")

        # Convert to graph relationships
        graph_rels = []
        for call in calls:
            # Create caller and callee IDs
            caller_id = f"{call.file_path}::{call.caller}"
            # For callee, we need to find the actual function node
            # For now, use a simplified ID (may need enhancement)
            callee_id = f"*::{call.callee}"  # Wildcard for now

            rel = CallsRelationship(
                caller_id=caller_id,
                callee_id=callee_id,
                call_site_line=call.call_site_line,
                file_path=call.file_path
            )
            graph_rels.append(rel)

        # Batch upsert
        self.graph_store.upsert_relationships_batch(graph_rels)

        logger.info(f"Successfully ingested {len(calls)} call relationships")
        return len(calls)

    def ingest_calls_with_resolution(self, calls: List[CallEdge],
                                       functions: List[FunctionNode]) -> int:
        """
        Ingest call relationships with proper function resolution.

        Args:
            calls: List of CallEdge objects
            functions: List of FunctionNode objects for resolution

        Returns:
            Number of call relationships ingested
        """
        logger.info(f"Ingesting {len(calls)} call relationships with function resolution...")

        # Build function lookup by name
        func_lookup = {}
        for func in functions:
            if func.name not in func_lookup:
                func_lookup[func.name] = []
            func_lookup[func.name].append(func)

        # Convert to graph relationships
        graph_rels = []
        unresolved_callees = set()

        for call in calls:
            caller_id = f"{call.file_path}::{call.caller}"

            # Try to resolve callee to actual function
            if call.callee in func_lookup:
                callee_funcs = func_lookup[call.callee]
                # If multiple matches, prefer same subsystem or first match
                callee_func = callee_funcs[0]  # Simplified: take first match

                callee_id = f"{callee_func.file_path}::{callee_func.name}"
            else:
                # External function or macro
                callee_id = f"external::{call.callee}"
                unresolved_callees.add(call.callee)

            rel = CallsRelationship(
                caller_id=caller_id,
                callee_id=callee_id,
                call_site_line=call.call_site_line,
                file_path=call.file_path
            )
            graph_rels.append(rel)

        if unresolved_callees:
            logger.warning(f"Found {len(unresolved_callees)} unresolved function calls (external/macros)")
            logger.debug(f"Sample unresolved: {list(unresolved_callees)[:10]}")

        # Batch upsert
        self.graph_store.upsert_relationships_batch(graph_rels)

        logger.info(f"Successfully ingested {len(calls)} call relationships")
        return len(calls)

    def ingest_file_structure(self, functions: List[FunctionNode]) -> int:
        """
        Create file and subsystem nodes and relationships.

        Args:
            functions: List of FunctionNode objects

        Returns:
            Number of file nodes created
        """
        logger.info("Ingesting file structure...")

        # Extract unique files and subsystems
        files_data = {}
        subsystems_data = {}

        for func in functions:
            # Track file
            if func.file_path not in files_data:
                files_data[func.file_path] = {
                    'subsystem': func.subsystem,
                    'function_count': 0
                }
            files_data[func.file_path]['function_count'] += 1

            # Track subsystem
            if func.subsystem not in subsystems_data:
                subsystems_data[func.subsystem] = {
                    'files': set(),
                    'function_count': 0
                }
            subsystems_data[func.subsystem]['files'].add(func.file_path)
            subsystems_data[func.subsystem]['function_count'] += 1

        # Create file nodes
        file_nodes = []
        for file_path, data in files_data.items():
            node = FileGraphNode(
                file_path=file_path,
                subsystem=data['subsystem'],
                function_count=data['function_count']
            )
            file_nodes.append(node)

        self.graph_store.upsert_nodes_batch(file_nodes)

        # Create subsystem nodes
        subsystem_nodes = []
        for subsystem_name, data in subsystems_data.items():
            # Extract path from first file
            first_file = next(iter(data['files']))
            subsystem_path = str(Path(first_file).parent)

            node = SubsystemGraphNode(
                name=subsystem_name,
                path=subsystem_path,
                file_count=len(data['files']),
                function_count=data['function_count']
            )
            subsystem_nodes.append(node)

        self.graph_store.upsert_nodes_batch(subsystem_nodes)

        # Create relationships: File BELONGS_TO Subsystem
        file_rels = []
        for file_path, data in files_data.items():
            rel = BelongsToRelationship(
                item_id=file_path,
                parent_id=data['subsystem']
            )
            file_rels.append(rel)

        self.graph_store.upsert_relationships_batch(file_rels)

        # Create relationships: File CONTAINS Function
        contains_rels = []
        for func in functions:
            rel = ContainsRelationship(
                container_id=func.file_path,
                contained_id=f"{func.file_path}::{func.name}"
            )
            contains_rels.append(rel)

        self.graph_store.upsert_relationships_batch(contains_rels)

        logger.info(f"Ingested {len(file_nodes)} files and {len(subsystem_nodes)} subsystems")
        return len(file_nodes)

    def ingest_subsystem_complete(self, functions: List[FunctionNode],
                                    calls: List[CallEdge]) -> dict:
        """
        Complete ingestion pipeline for a subsystem.

        Args:
            functions: List of FunctionNode objects
            calls: List of CallEdge objects

        Returns:
            Statistics dictionary
        """
        logger.info("Starting complete subsystem ingestion...")

        stats = {
            'functions_ingested': 0,
            'calls_ingested': 0,
            'files_created': 0
        }

        # Step 1: Ingest file structure
        stats['files_created'] = self.ingest_file_structure(functions)

        # Step 2: Ingest functions
        stats['functions_ingested'] = self.ingest_functions(functions)

        # Step 3: Ingest calls with resolution
        stats['calls_ingested'] = self.ingest_calls_with_resolution(calls, functions)

        logger.info("Complete subsystem ingestion finished")
        logger.info(f"Statistics: {stats}")

        return stats


def ingest_from_extractor(kernel_root: str, subsystem_path: str,
                           graph_store: Neo4jGraphStore,
                           skip_preprocessing: bool = True) -> dict:
    """
    Extract and ingest a kernel subsystem into Neo4j.

    Args:
        kernel_root: Path to Linux kernel source root
        subsystem_path: Relative path to subsystem (e.g., "fs/ext4")
        graph_store: Neo4jGraphStore instance
        skip_preprocessing: Whether to skip macro preprocessing

    Returns:
        Ingestion statistics
    """
    logger.info(f"Extracting and ingesting {subsystem_path}...")

    # Extract data
    extractor = FunctionExtractor(kernel_root)
    functions, calls = extractor.extract_from_subsystem(subsystem_path, skip_preprocessing)

    # Ingest into graph
    ingestion = GraphIngestion(graph_store)
    stats = ingestion.ingest_subsystem_complete(functions, calls)

    # Add extraction stats
    stats['extraction_stats'] = extractor.get_statistics(functions, calls)

    return stats


if __name__ == "__main__":
    import os
    import json

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python ingestion.py <subsystem_path>")
        print("Example: python ingestion.py fs/ext4")
        sys.exit(1)

    kernel_root = os.getenv("KERNEL_ROOT", "/workspaces/ubuntu/linux-6.13")
    subsystem_path = sys.argv[1]

    neo4j_url = os.getenv("NEO4J_URL", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")

    with Neo4jGraphStore(neo4j_url, neo4j_user, neo4j_password) as store:
        # Initialize schema
        store.initialize_schema()

        # Ingest subsystem
        stats = ingest_from_extractor(kernel_root, subsystem_path, store)

        print("\n=== Ingestion Complete ===")
        print(json.dumps(stats, indent=2))

        # Show database statistics
        db_stats = store.get_statistics()
        print("\n=== Database Statistics ===")
        print(json.dumps(db_stats, indent=2))
