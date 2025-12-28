"""
Module D: Data Flow Ingestion
Ingests variables and data flow edges into Neo4j graph database.
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.module_b.graph_store import Neo4jGraphStore
from src.module_d.variable_tracker import VariableDefinition, VariableUse, VariableTracker
from src.module_d.flow_builder import FlowBuilder, DataFlowEdge, InterProcFlow
from src.module_d.flow_schema import (
    VariableNode,
    FlowRelationship,
    FlowType,
    get_variable_node_query,
    get_flow_relationship_query,
    get_defines_relationship_query,
    get_uses_relationship_query,
    get_schema_setup_queries,
)

logger = logging.getLogger(__name__)


class DataFlowIngestion:
    """Handles ingestion of data flow information into Neo4j."""

    def __init__(self, graph_store: Neo4jGraphStore):
        """
        Initialize data flow ingestion.

        Args:
            graph_store: Neo4j graph store instance
        """
        self.graph_store = graph_store
        self.variable_tracker = VariableTracker()
        self.flow_builder = FlowBuilder()

    def setup_schema(self):
        """
        Create data flow schema (constraints and indexes) in Neo4j.

        This should be called once before ingesting data.
        """
        logger.info("Setting up data flow schema in Neo4j")

        queries = get_schema_setup_queries()

        for query in queries:
            try:
                self.graph_store.execute_query(query)
                logger.debug(f"Executed schema query: {query[:50]}...")
            except Exception as e:
                logger.warning(f"Schema query failed (may already exist): {e}")

        logger.info("Data flow schema setup complete")

    def ingest_file(self, source_file: str, subsystem: str) -> Dict[str, int]:
        """
        Ingest variables and data flows from a single C file.

        Args:
            source_file: Path to C source file
            subsystem: Subsystem name (e.g., "ext4")

        Returns:
            Dictionary with counts of ingested items
        """
        logger.info(f"Ingesting data flow from {source_file}")

        stats = {
            "variables": 0,
            "flows": 0,
            "defines_rels": 0,
            "uses_rels": 0,
        }

        # Extract variables
        var_definitions, var_uses = self.variable_tracker.extract_from_file(source_file)

        # Extract data flows
        data_flows, _ = self.flow_builder.build_intra_procedural_flows(source_file)

        # Ingest variables
        for var_def in var_definitions:
            self._ingest_variable(var_def)
            stats["variables"] += 1

        # Create DEFINES relationships (Function -> Variable)
        for var_def in var_definitions:
            if self._create_defines_relationship(var_def, source_file):
                stats["defines_rels"] += 1

        # Create USES relationships (Function -> Variable)
        for var_use in var_uses:
            if self._create_uses_relationship(var_use, source_file):
                stats["uses_rels"] += 1

        # Ingest data flows
        for flow in data_flows:
            if self._ingest_flow(flow):
                stats["flows"] += 1

        logger.info(
            f"Ingested {stats['variables']} variables, {stats['flows']} flows, "
            f"{stats['defines_rels']} DEFINES, {stats['uses_rels']} USES"
        )

        return stats

    def _ingest_variable(self, var_def: VariableDefinition) -> bool:
        """
        Ingest a single variable definition into Neo4j.

        Args:
            var_def: Variable definition to ingest

        Returns:
            True if successful, False otherwise
        """
        try:
            var_node = VariableNode(
                name=var_def.name,
                var_type=var_def.var_type,
                scope=var_def.scope,
                file_path=var_def.file_path,
                line_number=var_def.line_number,
                is_parameter=var_def.is_parameter,
                is_pointer=var_def.is_pointer,
                is_static=var_def.is_static,
            )

            query = get_variable_node_query(var_node)
            params = var_node.to_cypher_properties()
            params["id"] = var_node.id

            self.graph_store.execute_query(query, params)
            return True

        except Exception as e:
            logger.error(f"Failed to ingest variable {var_def.name}: {e}")
            return False

    def _ingest_flow(self, flow: DataFlowEdge) -> bool:
        """
        Ingest a data flow edge into Neo4j.

        Args:
            flow: Data flow edge to ingest

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create variable IDs
            from_id = f"{flow.file_path}::{flow.function}::{flow.from_var}"
            to_id = f"{flow.file_path}::{flow.function}::{flow.to_var}"

            flow_rel = FlowRelationship(
                from_id=from_id,
                to_id=to_id,
                flow_type=flow.flow_type,
                line_number=flow.line_number,
                confidence=flow.confidence,
            )

            query = get_flow_relationship_query(flow_rel)
            params = flow_rel.to_cypher_properties()
            params["from_id"] = from_id
            params["to_id"] = to_id

            self.graph_store.execute_query(query, params)
            return True

        except Exception as e:
            logger.error(f"Failed to ingest flow {flow.from_var} -> {flow.to_var}: {e}")
            return False

    def _create_defines_relationship(
        self, var_def: VariableDefinition, source_file: str
    ) -> bool:
        """
        Create DEFINES relationship from Function to Variable.

        Args:
            var_def: Variable definition
            source_file: Source file path

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create variable ID
            var_id = f"{var_def.file_path}::{var_def.scope}::{var_def.name}"

            # Create function ID (assuming Function nodes exist from Module B)
            func_id = f"{source_file}::{var_def.scope}"

            query = get_defines_relationship_query(func_id, var_id)
            params = {"function_id": func_id, "variable_id": var_id}

            self.graph_store.execute_query(query, params)
            return True

        except Exception as e:
            logger.debug(
                f"Could not create DEFINES relationship for {var_def.name}: {e}"
            )
            return False

    def _create_uses_relationship(
        self, var_use: VariableUse, source_file: str
    ) -> bool:
        """
        Create USES relationship from Function to Variable.

        Args:
            var_use: Variable use
            source_file: Source file path

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create variable ID (need to find the actual variable definition)
            # For now, assume variable is defined in the same function
            var_id = f"{var_use.file_path}::{var_use.function}::{var_use.name}"

            # Create function ID
            func_id = f"{source_file}::{var_use.function}"

            query = get_uses_relationship_query(func_id, var_id, var_use.line_number)
            params = {
                "function_id": func_id,
                "variable_id": var_id,
                "line": var_use.line_number,
            }

            self.graph_store.execute_query(query, params)
            return True

        except Exception as e:
            logger.debug(f"Could not create USES relationship for {var_use.name}: {e}")
            return False

    def ingest_directory(
        self, directory: str, subsystem: str, pattern: str = "*.c"
    ) -> Dict[str, int]:
        """
        Ingest all C files in a directory.

        Args:
            directory: Directory path
            subsystem: Subsystem name
            pattern: File pattern (default: "*.c")

        Returns:
            Dictionary with total counts
        """
        logger.info(f"Ingesting data flow from directory: {directory}")

        total_stats = {
            "files": 0,
            "variables": 0,
            "flows": 0,
            "defines_rels": 0,
            "uses_rels": 0,
        }

        dir_path = Path(directory)

        for source_file in dir_path.glob(pattern):
            try:
                file_stats = self.ingest_file(str(source_file), subsystem)

                total_stats["files"] += 1
                total_stats["variables"] += file_stats["variables"]
                total_stats["flows"] += file_stats["flows"]
                total_stats["defines_rels"] += file_stats["defines_rels"]
                total_stats["uses_rels"] += file_stats["uses_rels"]

            except Exception as e:
                logger.error(f"Failed to ingest {source_file}: {e}")

        logger.info(
            f"Completed ingestion: {total_stats['files']} files, "
            f"{total_stats['variables']} variables, {total_stats['flows']} flows"
        )

        return total_stats

    def get_variable_statistics(self) -> Dict[str, int]:
        """
        Get statistics about variables in the graph.

        Returns:
            Dictionary with variable statistics
        """
        stats = {}

        # Total variables
        query = "MATCH (v:Variable) RETURN count(v) as count"
        result = self.graph_store.execute_query(query)
        stats["total_variables"] = result[0]["count"] if result else 0

        # Variables by type
        query = """
        MATCH (v:Variable)
        RETURN v.is_parameter as is_param, count(v) as count
        """
        result = self.graph_store.execute_query(query)
        stats["parameters"] = sum(r["count"] for r in result if r["is_param"])
        stats["locals"] = sum(r["count"] for r in result if not r["is_param"])

        # Total flows
        query = "MATCH ()-[r:FLOWS_TO]->() RETURN count(r) as count"
        result = self.graph_store.execute_query(query)
        stats["total_flows"] = result[0]["count"] if result else 0

        return stats
