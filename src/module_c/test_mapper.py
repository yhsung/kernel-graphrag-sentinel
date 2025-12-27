"""
Module C: Test Mapper
Maps KUnit test cases to tested functions in the Neo4j graph.
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.module_c.kunit_parser import KUnitParser, TestCase, TestSuite, find_kunit_test_files
from src.module_b.graph_store import Neo4jGraphStore
from src.module_b.schema import TestCaseGraphNode, CoversRelationship

logger = logging.getLogger(__name__)


class TestMapper:
    """Maps KUnit test cases to tested functions in the graph database."""

    def __init__(self, graph_store: Neo4jGraphStore):
        """
        Initialize the test mapper.

        Args:
            graph_store: Neo4jGraphStore instance
        """
        self.graph_store = graph_store
        self.parser = KUnitParser()

    def ingest_test_cases(self, test_cases: List[TestCase]) -> int:
        """
        Ingest test case nodes into the graph.

        Args:
            test_cases: List of TestCase objects

        Returns:
            Number of test cases ingested
        """
        logger.info(f"Ingesting {len(test_cases)} test cases...")

        # Convert to graph nodes
        graph_nodes = []
        for tc in test_cases:
            node = TestCaseGraphNode(
                name=tc.name,
                file_path=tc.file_path,
                test_suite=tc.test_suite,
                line_start=tc.line_start,
                line_end=tc.line_end
            )
            graph_nodes.append(node)

        # Batch upsert
        self.graph_store.upsert_nodes_batch(graph_nodes)

        logger.info(f"Successfully ingested {len(test_cases)} test cases")
        return len(test_cases)

    def create_covers_relationships(self, test_cases: List[TestCase]) -> Tuple[int, int]:
        """
        Create COVERS relationships between test cases and tested functions.

        Args:
            test_cases: List of TestCase objects with tested_functions

        Returns:
            Tuple of (successful_mappings, failed_mappings)
        """
        logger.info("Creating COVERS relationships...")

        # Get all functions from the graph for name resolution
        function_lookup = self._build_function_lookup()

        successful = 0
        failed = 0
        unresolved_functions = set()

        graph_rels = []

        for tc in test_cases:
            test_id = f"{tc.file_path}::{tc.name}"

            for tested_func_name in tc.tested_functions:
                # Try to resolve function name to actual function node
                function_ids = self._resolve_function_name(tested_func_name, function_lookup)

                if function_ids:
                    # Create COVERS relationship for each match
                    for func_id in function_ids:
                        rel = CoversRelationship(
                            test_id=test_id,
                            function_id=func_id,
                            coverage_type="direct"
                        )
                        graph_rels.append(rel)
                        successful += 1
                else:
                    # Function not found in graph (likely a macro or external function)
                    unresolved_functions.add(tested_func_name)
                    failed += 1

        # Batch upsert relationships
        if graph_rels:
            self.graph_store.upsert_relationships_batch(graph_rels)

        if unresolved_functions:
            logger.warning(f"Failed to resolve {len(unresolved_functions)} tested functions")
            logger.debug(f"Unresolved functions: {list(unresolved_functions)[:20]}")

        logger.info(f"Created {successful} COVERS relationships ({failed} unresolved)")
        return successful, failed

    def _build_function_lookup(self) -> Dict[str, List[str]]:
        """
        Build a lookup table of function names to function IDs.

        Returns:
            Dict mapping function name to list of function IDs
        """
        logger.info("Building function lookup table...")

        query = """
        MATCH (f:Function)
        RETURN f.name as name, f.id as id
        """

        results = self.graph_store.execute_query(query)

        lookup = {}
        for record in results:
            func_name = record['name']
            func_id = record['id']

            if func_name not in lookup:
                lookup[func_name] = []
            lookup[func_name].append(func_id)

        logger.info(f"Built lookup table with {len(lookup)} unique function names")
        return lookup

    def _resolve_function_name(self, func_name: str,
                                 function_lookup: Dict[str, List[str]]) -> List[str]:
        """
        Resolve a function name to function IDs in the graph.

        Args:
            func_name: Name of the tested function
            function_lookup: Lookup table from _build_function_lookup

        Returns:
            List of matching function IDs (may be empty if not found)
        """
        # Direct match
        if func_name in function_lookup:
            return function_lookup[func_name]

        # No match found
        return []

    def map_subsystem_tests(self, kernel_root: str, subsystem_path: str) -> Dict:
        """
        Complete test mapping pipeline for a subsystem.

        Args:
            kernel_root: Path to Linux kernel source root
            subsystem_path: Relative path to subsystem (e.g., "fs/ext4")

        Returns:
            Statistics dictionary
        """
        logger.info(f"Mapping tests for {subsystem_path}...")

        full_subsystem_path = str(Path(kernel_root) / subsystem_path)

        # Find test files
        test_files = find_kunit_test_files(full_subsystem_path)

        if not test_files:
            logger.warning(f"No KUnit test files found in {subsystem_path}")
            return {
                'test_files': 0,
                'test_cases': 0,
                'test_suites': 0,
                'covers_created': 0,
                'unresolved': 0
            }

        # Parse test files
        all_test_cases = []
        all_test_suites = []

        for test_file in test_files:
            test_cases, test_suites = self.parser.parse_test_file(test_file)

            # Update file_path in suites
            for suite in test_suites:
                suite.file_path = test_file

            all_test_cases.extend(test_cases)
            all_test_suites.extend(test_suites)

        # Ingest test cases into graph
        test_cases_count = self.ingest_test_cases(all_test_cases)

        # Create COVERS relationships
        successful, failed = self.create_covers_relationships(all_test_cases)

        stats = {
            'test_files': len(test_files),
            'test_cases': test_cases_count,
            'test_suites': len(all_test_suites),
            'covers_created': successful,
            'unresolved': failed
        }

        logger.info("Test mapping complete")
        logger.info(f"Statistics: {stats}")

        return stats


if __name__ == "__main__":
    import os
    import json

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python test_mapper.py <subsystem_path>")
        print("Example: python test_mapper.py fs/ext4")
        sys.exit(1)

    kernel_root = os.getenv("KERNEL_ROOT", "/workspaces/ubuntu/linux-6.13")
    subsystem_path = sys.argv[1]

    neo4j_url = os.getenv("NEO4J_URL", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")

    with Neo4jGraphStore(neo4j_url, neo4j_user, neo4j_password) as store:
        # Create test mapper
        mapper = TestMapper(store)

        # Map subsystem tests
        stats = mapper.map_subsystem_tests(kernel_root, subsystem_path)

        print("\n=== Test Mapping Complete ===")
        print(json.dumps(stats, indent=2))

        # Show database statistics
        db_stats = store.get_statistics()
        print("\n=== Database Statistics ===")
        print(json.dumps(db_stats, indent=2))

        # Show sample COVERS relationships
        print("\n=== Sample COVERS Relationships ===")
        query = """
        MATCH (t:TestCase)-[r:COVERS]->(f:Function)
        RETURN t.name as test_case, f.name as function
        LIMIT 10
        """
        results = store.execute_query(query)
        for record in results:
            print(f"  {record['test_case']} → {record['function']}")
