"""Unit tests for Module B: Graph Store (graph_store.py)."""

import pytest
from unittest.mock import MagicMock, patch, call
from neo4j.exceptions import ServiceUnavailable, AuthError

from src.module_b.graph_store import Neo4jGraphStore
from src.module_b.schema import FunctionGraphNode, GraphRelationship, RelationType


class TestNeo4jGraphStore:
    """Test cases for Neo4jGraphStore class."""

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_init_success(self, mock_driver_class):
        """Test successful initialization of graph store."""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.verify_connectivity.return_value = None

        store = Neo4jGraphStore(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="test_password"
        )

        assert store.uri == "bolt://localhost:7687"
        assert store.user == "neo4j"
        mock_driver_class.assert_called_once_with(
            "bolt://localhost:7687",
            auth=("neo4j", "test_password")
        )
        mock_driver.verify_connectivity.assert_called_once()

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_init_connection_failure(self, mock_driver_class):
        """Test initialization handles connection failures."""
        mock_driver_class.side_effect = ServiceUnavailable("Connection failed")

        with pytest.raises(ServiceUnavailable):
            Neo4jGraphStore(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="wrong"
            )

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_init_auth_failure(self, mock_driver_class):
        """Test initialization handles authentication failures."""
        mock_driver_class.side_effect = AuthError("Invalid credentials")

        with pytest.raises(AuthError):
            Neo4jGraphStore(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="wrong"
            )

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_close(self, mock_driver_class):
        """Test closing the graph store connection."""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver

        store = Neo4jGraphStore()
        store.close()

        mock_driver.close.assert_called_once()

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_context_manager(self, mock_driver_class):
        """Test using graph store as context manager."""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver

        with Neo4jGraphStore() as store:
            assert store is not None

        mock_driver.close.assert_called_once()

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_execute_query(self, mock_driver_class):
        """Test executing a Cypher query."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()

        # Mock the session context manager
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        # Mock query results
        mock_record1 = {"name": "func1", "count": 5}
        mock_record2 = {"name": "func2", "count": 10}
        mock_result.__iter__.return_value = iter([mock_record1, mock_record2])
        mock_session.run.return_value = mock_result

        mock_driver_class.return_value = mock_driver

        store = Neo4jGraphStore()
        results = store.execute_query(
            "MATCH (f:Function) RETURN f.name as name, f.count as count",
            parameters={"limit": 10}
        )

        assert len(results) == 2
        assert results[0] == mock_record1
        assert results[1] == mock_record2

        mock_session.run.assert_called_once()

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_execute_query_no_driver(self, mock_driver_class):
        """Test execute_query raises error when driver not initialized."""
        mock_driver_class.return_value = None

        store = Neo4jGraphStore()
        store._driver = None

        with pytest.raises(RuntimeError, match="Neo4j driver not initialized"):
            store.execute_query("MATCH (n) RETURN n")

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_execute_write(self, mock_driver_class):
        """Test executing a write transaction."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        mock_session.execute_write.return_value = {"nodes_created": 1}

        mock_driver_class.return_value = mock_driver

        store = Neo4jGraphStore()
        result = store.execute_write(
            "CREATE (f:Function {name: $name})",
            parameters={"name": "test_func"}
        )

        mock_session.execute_write.assert_called_once()

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_add_node(self, mock_driver_class):
        """Test adding a node to the graph."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        mock_driver_class.return_value = mock_driver

        store = Neo4jGraphStore()

        node = FunctionGraphNode(
            name="test_func",
            file_path="test.c",
            line_start=10,
            line_end=20,
            subsystem="test"
        )

        store.add_node(node)

        # Verify session.run or execute_write was called
        assert mock_session.run.called or mock_session.execute_write.called

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_add_relationship(self, mock_driver_class):
        """Test adding a relationship to the graph."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        mock_driver_class.return_value = mock_driver

        store = Neo4jGraphStore()

        rel = GraphRelationship(
            from_id="file.c::caller",
            to_id="file.c::callee",
            rel_type=RelationType.CALLS,
            properties={"call_line": 42}
        )

        store.add_relationship(rel)

        # Verify session was used
        assert mock_session.run.called or mock_session.execute_write.called

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_batch_add_nodes(self, mock_driver_class):
        """Test batch adding multiple nodes."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        mock_driver_class.return_value = mock_driver

        store = Neo4jGraphStore()

        nodes = [
            FunctionGraphNode(f"func{i}", "test.c", i*10, i*10+5, "test")
            for i in range(5)
        ]

        store.batch_add_nodes(nodes, batch_size=2)

        # Should have made multiple calls for batching
        call_count = mock_session.run.call_count + mock_session.execute_write.call_count
        assert call_count > 0

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_clear_graph(self, mock_driver_class):
        """Test clearing the entire graph."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        mock_driver_class.return_value = mock_driver

        store = Neo4jGraphStore()
        store.clear_graph()

        # Should execute a DELETE query
        assert mock_session.run.called or mock_session.execute_write.called

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_create_schema_constraints(self, mock_driver_class):
        """Test creating schema constraints."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        mock_driver_class.return_value = mock_driver

        store = Neo4jGraphStore()
        store.create_schema_constraints()

        # Should execute constraint creation queries
        assert mock_session.run.call_count > 0

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_create_schema_indexes(self, mock_driver_class):
        """Test creating schema indexes."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        mock_driver_class.return_value = mock_driver

        store = Neo4jGraphStore()
        store.create_schema_indexes()

        # Should execute index creation queries
        assert mock_session.run.call_count > 0

    @patch('src.module_b.graph_store.GraphDatabase.driver')
    def test_get_function_by_name(self, mock_driver_class):
        """Test querying for a function by name."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()

        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        mock_record = {"name": "test_func", "file_path": "test.c"}
        mock_result.__iter__.return_value = iter([mock_record])
        mock_session.run.return_value = mock_result

        mock_driver_class.return_value = mock_driver

        store = Neo4jGraphStore()
        results = store.execute_query(
            "MATCH (f:Function {name: $name}) RETURN f",
            parameters={"name": "test_func"}
        )

        assert len(results) == 1
        assert results[0]["name"] == "test_func"
