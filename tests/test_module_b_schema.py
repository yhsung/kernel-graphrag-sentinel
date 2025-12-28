"""Unit tests for Module B: Graph Schema (schema.py)."""

import pytest

from src.module_b.schema import (
    NodeType,
    RelationType,
    GraphNode,
    FunctionGraphNode,
    TestCaseGraphNode,
    FileGraphNode,
    SubsystemGraphNode,
    GraphRelationship,
    get_node_merge_query,
    get_relationship_merge_query,
)


class TestNodeType:
    """Test cases for NodeType enum."""

    def test_node_types_exist(self):
        """Test that all expected node types are defined."""
        assert NodeType.FUNCTION.value == "Function"
        assert NodeType.TEST_CASE.value == "TestCase"
        assert NodeType.STRUCT.value == "Struct"
        assert NodeType.FILE.value == "File"
        assert NodeType.SUBSYSTEM.value == "Subsystem"


class TestRelationType:
    """Test cases for RelationType enum."""

    def test_relation_types_exist(self):
        """Test that all expected relation types are defined."""
        assert RelationType.CALLS.value == "CALLS"
        assert RelationType.COVERS.value == "COVERS"
        assert RelationType.DEFINES.value == "DEFINES"
        assert RelationType.CONTAINS.value == "CONTAINS"
        assert RelationType.BELONGS_TO.value == "BELONGS_TO"


class TestFunctionGraphNode:
    """Test cases for FunctionGraphNode."""

    def test_create_function_node(self):
        """Test creating a function graph node."""
        node = FunctionGraphNode(
            name="test_func",
            file_path="/path/to/test.c",
            line_start=10,
            line_end=20,
            subsystem="test_subsystem",
            is_static=False
        )

        assert node.id == "/path/to/test.c::test_func"
        assert node.label == NodeType.FUNCTION
        assert node.properties["name"] == "test_func"
        assert node.properties["file_path"] == "/path/to/test.c"
        assert node.properties["line_start"] == 10
        assert node.properties["line_end"] == 20
        assert node.properties["subsystem"] == "test_subsystem"
        assert node.properties["is_static"] is False
        assert node.properties["node_type"] == "Function"

    def test_function_node_static(self):
        """Test creating a static function node."""
        node = FunctionGraphNode(
            name="static_func",
            file_path="test.c",
            line_start=5,
            line_end=10,
            subsystem="test",
            is_static=True
        )

        assert node.properties["is_static"] is True

    def test_function_node_id_uniqueness(self):
        """Test that function node IDs are unique per file and name."""
        node1 = FunctionGraphNode("func", "file1.c", 1, 10, "subsys")
        node2 = FunctionGraphNode("func", "file2.c", 1, 10, "subsys")
        node3 = FunctionGraphNode("other", "file1.c", 1, 10, "subsys")

        # Same name, different files = different IDs
        assert node1.id != node2.id

        # Different names, same file = different IDs
        assert node1.id != node3.id


class TestTestCaseGraphNode:
    """Test cases for TestCaseGraphNode."""

    def test_create_test_case_node(self):
        """Test creating a test case graph node."""
        node = TestCaseGraphNode(
            name="test_my_function",
            file_path="/path/to/test.c",
            test_suite="my_test_suite",
            line_start=50,
            line_end=60
        )

        assert node.id == "/path/to/test.c::test_my_function"
        assert node.label == NodeType.TEST_CASE
        assert node.properties["name"] == "test_my_function"
        assert node.properties["file_path"] == "/path/to/test.c"
        assert node.properties["test_suite"] == "my_test_suite"
        assert node.properties["line_start"] == 50
        assert node.properties["line_end"] == 60
        assert node.properties["node_type"] == "TestCase"

    def test_test_case_node_defaults(self):
        """Test test case node with default line numbers."""
        node = TestCaseGraphNode(
            name="test_foo",
            file_path="test.c",
            test_suite="foo_suite"
        )

        assert node.properties["line_start"] == 0
        assert node.properties["line_end"] == 0


class TestFileGraphNode:
    """Test cases for FileGraphNode."""

    def test_create_file_node(self):
        """Test creating a file graph node."""
        node = FileGraphNode(
            file_path="/kernel/fs/ext4/inode.c",
            subsystem="ext4",
            function_count=42,
            line_count=1500
        )

        assert node.id == "/kernel/fs/ext4/inode.c"
        assert node.label == NodeType.FILE
        assert node.properties["file_path"] == "/kernel/fs/ext4/inode.c"
        assert node.properties["subsystem"] == "ext4"
        assert node.properties["function_count"] == 42
        assert node.properties["line_count"] == 1500

    def test_file_node_defaults(self):
        """Test file node with default counts."""
        node = FileGraphNode(
            file_path="test.c",
            subsystem="test"
        )

        assert node.properties["function_count"] == 0
        assert node.properties["line_count"] == 0


class TestSubsystemGraphNode:
    """Test cases for SubsystemGraphNode."""

    def test_create_subsystem_node(self):
        """Test creating a subsystem graph node."""
        node = SubsystemGraphNode(
            name="ext4",
            description="Fourth Extended Filesystem",
            file_count=100
        )

        assert node.id == "ext4"
        assert node.label == NodeType.SUBSYSTEM
        assert node.properties["name"] == "ext4"
        assert node.properties["description"] == "Fourth Extended Filesystem"
        assert node.properties["file_count"] == 100


class TestGraphRelationship:
    """Test cases for GraphRelationship."""

    def test_create_calls_relationship(self):
        """Test creating a CALLS relationship."""
        rel = GraphRelationship(
            from_id="file.c::caller",
            to_id="file.c::callee",
            rel_type=RelationType.CALLS,
            properties={"call_line": 42}
        )

        assert rel.from_id == "file.c::caller"
        assert rel.to_id == "file.c::callee"
        assert rel.rel_type == RelationType.CALLS
        assert rel.properties["call_line"] == 42

    def test_create_covers_relationship(self):
        """Test creating a COVERS relationship (test -> function)."""
        rel = GraphRelationship(
            from_id="test.c::test_foo",
            to_id="code.c::foo",
            rel_type=RelationType.COVERS,
            properties={}
        )

        assert rel.rel_type == RelationType.COVERS
        assert rel.properties == {}


class TestQueryGeneration:
    """Test cases for Cypher query generation."""

    def test_get_node_merge_query_function(self):
        """Test generating MERGE query for function node."""
        node = FunctionGraphNode("func", "test.c", 1, 10, "subsys")
        query = get_node_merge_query(node)

        assert "MERGE" in query
        assert "Function" in query
        assert "name" in query
        assert "file_path" in query

    def test_get_relationship_merge_query(self):
        """Test generating MERGE query for relationship."""
        rel = GraphRelationship(
            from_id="a::func1",
            to_id="b::func2",
            rel_type=RelationType.CALLS,
            properties={"call_line": 10}
        )

        query = get_relationship_merge_query(rel)

        assert "MATCH" in query or "MERGE" in query
        assert "CALLS" in query

    def test_node_properties_escaping(self):
        """Test that node properties with special characters are handled."""
        node = FunctionGraphNode(
            name="func_with_'quote",
            file_path="/path/with spaces/file.c",
            line_start=1,
            line_end=10,
            subsystem="test"
        )

        # Should not raise an error
        query = get_node_merge_query(node)
        assert query is not None
        assert isinstance(query, str)
