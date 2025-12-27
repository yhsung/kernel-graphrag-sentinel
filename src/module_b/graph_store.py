"""
Module B: Neo4j Graph Store
Handles Neo4j database connections and operations.
"""

from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError
import logging

from .schema import (
    GraphNode, GraphRelationship,
    get_node_merge_query, get_relationship_merge_query,
    SCHEMA_CONSTRAINTS, SCHEMA_INDEXES
)

logger = logging.getLogger(__name__)


class Neo4jGraphStore:
    """Manages Neo4j graph database connections and operations."""

    def __init__(self, uri: str = "bolt://localhost:7687",
                 user: str = "neo4j", password: str = "password123"):
        """
        Initialize Neo4j connection.

        Args:
            uri: Neo4j bolt URI
            user: Database username
            password: Database password
        """
        self.uri = uri
        self.user = user
        self._driver: Optional[Driver] = None

        try:
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
            self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {uri}")
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        """Close the Neo4j driver connection."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not initialized")

        parameters = parameters or {}

        with self._driver.session() as session:
            result = session.run(query, parameters)
            return [dict(record) for record in result]

    def execute_write(self, query: str, parameters: Dict[str, Any] = None) -> Any:
        """
        Execute a write query in a transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Query result
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not initialized")

        parameters = parameters or {}

        def _execute(tx):
            result = tx.run(query, parameters)
            return result.single()

        with self._driver.session() as session:
            return session.execute_write(_execute)

    def initialize_schema(self):
        """Create constraints and indexes for the graph schema."""
        logger.info("Initializing graph schema...")

        # Create constraints
        for constraint in SCHEMA_CONSTRAINTS.strip().split(';'):
            constraint = constraint.strip()
            if constraint and not constraint.startswith('//'):
                try:
                    self.execute_write(constraint)
                    logger.debug(f"Created constraint: {constraint[:50]}...")
                except Exception as e:
                    logger.warning(f"Constraint creation failed (may already exist): {e}")

        # Create indexes
        for index in SCHEMA_INDEXES.strip().split(';'):
            index = index.strip()
            if index and not index.startswith('//'):
                try:
                    self.execute_write(index)
                    logger.debug(f"Created index: {index[:50]}...")
                except Exception as e:
                    logger.warning(f"Index creation failed (may already exist): {e}")

        logger.info("Schema initialization complete")

    def clear_database(self):
        """Delete all nodes and relationships in the database."""
        logger.warning("Clearing entire database...")
        self.execute_write("MATCH (n) DETACH DELETE n")
        logger.info("Database cleared")

    def upsert_node(self, node: GraphNode) -> Dict:
        """
        Insert or update a node in the graph.

        Args:
            node: GraphNode to upsert

        Returns:
            Created/updated node data
        """
        query = get_node_merge_query(node)
        parameters = {"id": node.id, **node.properties}

        result = self.execute_write(query, parameters)
        if result:
            return dict(result["n"])
        return {}

    def upsert_nodes_batch(self, nodes: List[GraphNode], batch_size: int = 1000):
        """
        Batch insert/update multiple nodes.

        Args:
            nodes: List of GraphNodes to upsert
            batch_size: Number of nodes per batch
        """
        logger.info(f"Upserting {len(nodes)} nodes in batches of {batch_size}")

        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]
            batch_data = [{"id": n.id, **n.properties} for n in batch]

            # Group by node type for efficient batch processing
            node_types = {}
            for node in batch:
                label = node.label.value
                if label not in node_types:
                    node_types[label] = []
                node_types[label].append({"id": node.id, **node.properties})

            # Execute batch upsert for each node type
            for label, data in node_types.items():
                query = f"""
                UNWIND $batch AS node
                MERGE (n:{label} {{id: node.id}})
                SET n += node
                """
                self.execute_write(query, {"batch": data})

            logger.debug(f"Upserted batch {i // batch_size + 1}/{(len(nodes) + batch_size - 1) // batch_size}")

        logger.info(f"Successfully upserted {len(nodes)} nodes")

    def upsert_relationship(self, rel: GraphRelationship) -> Dict:
        """
        Insert or update a relationship in the graph.

        Args:
            rel: GraphRelationship to upsert

        Returns:
            Created/updated relationship data
        """
        query = get_relationship_merge_query(rel)
        parameters = {
            "source_id": rel.source_id,
            "target_id": rel.target_id,
            **rel.properties
        }

        result = self.execute_write(query, parameters)
        if result:
            return dict(result["r"])
        return {}

    def upsert_relationships_batch(self, relationships: List[GraphRelationship],
                                     batch_size: int = 1000):
        """
        Batch insert/update multiple relationships.

        Args:
            relationships: List of GraphRelationships to upsert
            batch_size: Number of relationships per batch
        """
        logger.info(f"Upserting {len(relationships)} relationships in batches of {batch_size}")

        for i in range(0, len(relationships), batch_size):
            batch = relationships[i:i + batch_size]

            # Group by relationship type
            rel_types = {}
            for rel in batch:
                label = rel.label.value
                if label not in rel_types:
                    rel_types[label] = []
                rel_types[label].append({
                    "source_id": rel.source_id,
                    "target_id": rel.target_id,
                    **rel.properties
                })

            # Execute batch upsert for each relationship type
            for label, data in rel_types.items():
                # Build properties string dynamically
                if data and data[0]:
                    prop_keys = [k for k in data[0].keys() if k not in ['source_id', 'target_id']]
                    props = ", ".join([f"{k}: rel.{k}" for k in prop_keys])
                    props_clause = f"{{{props}}}" if props else ""
                else:
                    props_clause = ""

                query = f"""
                UNWIND $batch AS rel
                MATCH (source {{id: rel.source_id}})
                MATCH (target {{id: rel.target_id}})
                MERGE (source)-[r:{label} {props_clause}]->(target)
                """
                self.execute_write(query, {"batch": data})

            logger.debug(f"Upserted batch {i // batch_size + 1}/{(len(relationships) + batch_size - 1) // batch_size}")

        logger.info(f"Successfully upserted {len(relationships)} relationships")

    def get_node_by_id(self, node_id: str) -> Optional[Dict]:
        """
        Retrieve a node by its ID.

        Args:
            node_id: Node ID

        Returns:
            Node properties or None
        """
        query = "MATCH (n {id: $id}) RETURN n"
        results = self.execute_query(query, {"id": node_id})
        if results:
            return dict(results[0]["n"])
        return None

    def get_function_callers(self, function_name: str, max_depth: int = 1) -> List[Dict]:
        """
        Find all functions that call a given function.

        Args:
            function_name: Name of the target function
            max_depth: Maximum call chain depth to traverse

        Returns:
            List of caller functions with path information
        """
        query = f"""
        MATCH (target:Function {{name: $func_name}})
        MATCH path = (caller:Function)-[:CALLS*1..{max_depth}]->(target)
        RETURN caller.name as caller,
               caller.file_path as file,
               length(path) as distance,
               [node in nodes(path) | node.name] as call_chain
        ORDER BY distance, caller
        """
        return self.execute_query(query, {"func_name": function_name})

    def get_function_callees(self, function_name: str, max_depth: int = 1) -> List[Dict]:
        """
        Find all functions called by a given function.

        Args:
            function_name: Name of the source function
            max_depth: Maximum call chain depth to traverse

        Returns:
            List of called functions with path information
        """
        query = f"""
        MATCH (source:Function {{name: $func_name}})
        MATCH path = (source)-[:CALLS*1..{max_depth}]->(callee:Function)
        RETURN callee.name as callee,
               callee.file_path as file,
               length(path) as distance,
               [node in nodes(path) | node.name] as call_chain
        ORDER BY distance, callee
        """
        return self.execute_query(query, {"func_name": function_name})

    def get_statistics(self) -> Dict[str, int]:
        """
        Get database statistics.

        Returns:
            Dictionary with node and relationship counts
        """
        stats = {}

        # Count nodes by type
        node_query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        """
        node_results = self.execute_query(node_query)
        for result in node_results:
            stats[f"{result['label']}_count"] = result['count']

        # Count relationships by type
        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        """
        rel_results = self.execute_query(rel_query)
        for result in rel_results:
            stats[f"{result['type']}_count"] = result['count']

        return stats


if __name__ == "__main__":
    # Example usage
    import os
    logging.basicConfig(level=logging.INFO)

    neo4j_url = os.getenv("NEO4J_URL", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")

    with Neo4jGraphStore(neo4j_url, neo4j_user, neo4j_password) as store:
        # Initialize schema
        store.initialize_schema()

        # Get statistics
        stats = store.get_statistics()
        print("\nDatabase Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
