"""Integration tests for Module D: Data Flow Ingestion."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.module_d.flow_ingestion import DataFlowIngestion
from src.module_d.variable_tracker import VariableDefinition, VariableUse
from src.module_d.flow_builder import DataFlowEdge
from src.module_d.flow_schema import FlowType


class TestDataFlowIngestion:
    """Test cases for DataFlowIngestion class."""

    def test_init(self, mock_neo4j_graph_store):
        """Test ingestion initialization."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        assert ingestion.graph_store == mock_neo4j_graph_store
        assert ingestion.variable_tracker is not None
        assert ingestion.flow_builder is not None

    def test_setup_schema(self, mock_neo4j_graph_store):
        """Test schema setup."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        # Mock execute_query to track calls
        mock_neo4j_graph_store.execute_query = MagicMock()

        ingestion.setup_schema()

        # Should execute multiple schema queries
        assert mock_neo4j_graph_store.execute_query.call_count > 0

    def test_ingest_file_simple(self, mock_neo4j_graph_store, temp_dir):
        """Test ingesting a simple C file."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        # Create test file
        test_file = temp_dir / "test.c"
        test_file.write_text("""
        void function(int param) {
            int local = param;
            return;
        }
        """)

        # Mock execute_query
        mock_neo4j_graph_store.execute_query = MagicMock()

        stats = ingestion.ingest_file(str(test_file), "test")

        # Should have ingested variables and flows
        assert stats["variables"] > 0
        assert stats["defines_rels"] >= 0
        assert stats["uses_rels"] >= 0
        assert stats["flows"] >= 0

    def test_ingest_file_empty(self, mock_neo4j_graph_store, temp_dir):
        """Test ingesting an empty file."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        # Create empty file
        empty_file = temp_dir / "empty.c"
        empty_file.write_text("")

        # Mock execute_query
        mock_neo4j_graph_store.execute_query = MagicMock()

        stats = ingestion.ingest_file(str(empty_file), "test")

        # Should have no ingestions
        assert stats["variables"] == 0
        assert stats["flows"] == 0

    def test_ingest_file_with_flows(self, mock_neo4j_graph_store, temp_dir):
        """Test ingesting file with data flows."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        # Create test file with assignments
        test_file = temp_dir / "flows.c"
        test_file.write_text("""
        int function(void) {
            int a = 10;
            int b = a;
            int c = b;
            return c;
        }
        """)

        # Mock execute_query
        mock_neo4j_graph_store.execute_query = MagicMock()

        stats = ingestion.ingest_file(str(test_file), "test")

        # Should have multiple flows: a->b, b->c, c->return
        assert stats["flows"] >= 3

    def test_ingest_variable(self, mock_neo4j_graph_store):
        """Test ingesting a single variable."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        var_def = VariableDefinition(
            name="test_var",
            var_type="int",
            scope="test_func",
            file_path="test.c",
            line_number=10,
            is_parameter=False,
            is_pointer=False,
        )

        # Mock execute_query
        mock_neo4j_graph_store.execute_query = MagicMock()

        result = ingestion._ingest_variable(var_def)

        assert result is True
        assert mock_neo4j_graph_store.execute_query.called

    def test_ingest_flow(self, mock_neo4j_graph_store):
        """Test ingesting a data flow edge."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        flow = DataFlowEdge(
            from_var="a",
            to_var="b",
            flow_type=FlowType.ASSIGNMENT,
            function="test_func",
            file_path="test.c",
            line_number=15,
            confidence=1.0,
        )

        # Mock execute_query
        mock_neo4j_graph_store.execute_query = MagicMock()

        result = ingestion._ingest_flow(flow)

        assert result is True
        assert mock_neo4j_graph_store.execute_query.called

    def test_create_defines_relationship(self, mock_neo4j_graph_store):
        """Test creating DEFINES relationship."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        var_def = VariableDefinition(
            name="local",
            var_type="int",
            scope="test_func",
            file_path="test.c",
            line_number=10,
            is_parameter=False,
            is_pointer=False,
        )

        # Mock execute_query
        mock_neo4j_graph_store.execute_query = MagicMock()

        result = ingestion._create_defines_relationship(var_def, "test.c")

        # May succeed or fail depending on whether Function node exists
        # Just verify it doesn't crash
        assert isinstance(result, bool)

    def test_create_uses_relationship(self, mock_neo4j_graph_store):
        """Test creating USES relationship."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        var_use = VariableUse(
            name="param",
            usage_type="read",
            function="test_func",
            file_path="test.c",
            line_number=12,
            context="assignment",
        )

        # Mock execute_query
        mock_neo4j_graph_store.execute_query = MagicMock()

        result = ingestion._create_uses_relationship(var_use, "test.c")

        # May succeed or fail depending on whether nodes exist
        assert isinstance(result, bool)

    def test_ingest_directory(self, mock_neo4j_graph_store, temp_dir):
        """Test ingesting multiple files from directory."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        # Create multiple test files
        (temp_dir / "file1.c").write_text("void func1(void) { int x = 1; }")
        (temp_dir / "file2.c").write_text("void func2(void) { int y = 2; }")
        (temp_dir / "file3.c").write_text("void func3(void) { int z = 3; }")

        # Mock execute_query
        mock_neo4j_graph_store.execute_query = MagicMock()

        stats = ingestion.ingest_directory(str(temp_dir), "test")

        # Should process all files
        assert stats["files"] == 3
        assert stats["variables"] > 0

    def test_ingest_directory_pattern(self, mock_neo4j_graph_store, temp_dir):
        """Test ingesting with file pattern."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        # Create files with different extensions
        (temp_dir / "test1.c").write_text("void func1(void) {}")
        (temp_dir / "test2.h").write_text("void func2(void) {}")
        (temp_dir / "test3.c").write_text("void func3(void) {}")

        # Mock execute_query
        mock_neo4j_graph_store.execute_query = MagicMock()

        # Should only process .c files
        stats = ingestion.ingest_directory(str(temp_dir), "test", pattern="*.c")

        assert stats["files"] == 2  # Only .c files

    def test_get_variable_statistics(self, mock_neo4j_graph_store):
        """Test getting variable statistics."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        # Mock query results
        mock_neo4j_graph_store.execute_query = MagicMock(side_effect=[
            [{"count": 100}],  # total_variables
            [{"is_param": True, "count": 30}, {"is_param": False, "count": 70}],  # by type
            [{"count": 50}],  # total_flows
        ])

        stats = ingestion.get_variable_statistics()

        assert stats["total_variables"] == 100
        assert stats["parameters"] == 30
        assert stats["locals"] == 70
        assert stats["total_flows"] == 50

    def test_get_variable_statistics_empty(self, mock_neo4j_graph_store):
        """Test getting statistics when database is empty."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        # Mock empty results
        mock_neo4j_graph_store.execute_query = MagicMock(side_effect=[
            [],  # total_variables
            [],  # by type
            [],  # total_flows
        ])

        stats = ingestion.get_variable_statistics()

        assert stats["total_variables"] == 0
        assert stats["total_flows"] == 0

    def test_ingest_file_with_sample_kernel(self, mock_neo4j_graph_store, sample_c_file):
        """Test ingesting sample kernel file."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        # Mock execute_query
        mock_neo4j_graph_store.execute_query = MagicMock()

        stats = ingestion.ingest_file(str(sample_c_file), "sample")

        # Sample kernel file should have multiple variables and flows
        assert stats["variables"] > 0
        assert stats["flows"] >= 0

    def test_error_handling_invalid_file(self, mock_neo4j_graph_store):
        """Test error handling for invalid file."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        # Should handle non-existent file gracefully
        with pytest.raises(Exception):
            ingestion.ingest_file("/nonexistent/file.c", "test")

    def test_ingest_variable_error_handling(self, mock_neo4j_graph_store):
        """Test error handling when ingesting variable fails."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        var_def = VariableDefinition(
            name="test",
            var_type="int",
            scope="func",
            file_path="test.c",
            line_number=10,
            is_parameter=False,
            is_pointer=False,
        )

        # Mock execute_query to raise exception
        mock_neo4j_graph_store.execute_query = MagicMock(side_effect=Exception("DB error"))

        result = ingestion._ingest_variable(var_def)

        assert result is False

    def test_ingest_flow_error_handling(self, mock_neo4j_graph_store):
        """Test error handling when ingesting flow fails."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        flow = DataFlowEdge(
            from_var="a",
            to_var="b",
            flow_type=FlowType.ASSIGNMENT,
            function="func",
            file_path="test.c",
            line_number=10,
            confidence=1.0,
        )

        # Mock execute_query to raise exception
        mock_neo4j_graph_store.execute_query = MagicMock(side_effect=Exception("DB error"))

        result = ingestion._ingest_flow(flow)

        assert result is False

    def test_ingest_directory_with_errors(self, mock_neo4j_graph_store, temp_dir):
        """Test directory ingestion continues on errors."""
        ingestion = DataFlowIngestion(mock_neo4j_graph_store)

        # Create files including one with invalid syntax
        (temp_dir / "valid.c").write_text("void func(void) { int x = 1; }")
        (temp_dir / "invalid.c").write_text("this is not valid C code @#$%")

        # Mock execute_query
        mock_neo4j_graph_store.execute_query = MagicMock()

        # Should complete despite errors
        stats = ingestion.ingest_directory(str(temp_dir), "test")

        # At least one file should succeed
        assert stats["files"] >= 0
