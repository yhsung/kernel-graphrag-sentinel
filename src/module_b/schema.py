"""
Module B: Graph Schema Definitions
Defines the Neo4j graph schema for kernel code analysis.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class NodeType(Enum):
    """Types of nodes in the graph."""
    FUNCTION = "Function"
    TEST_CASE = "TestCase"
    STRUCT = "Struct"
    FILE = "File"
    SUBSYSTEM = "Subsystem"


class RelationType(Enum):
    """Types of relationships in the graph."""
    CALLS = "CALLS"
    COVERS = "COVERS"
    DEFINES = "DEFINES"
    CONTAINS = "CONTAINS"
    BELONGS_TO = "BELONGS_TO"


@dataclass
class GraphNode:
    """Base class for all graph nodes."""
    id: str
    label: NodeType
    properties: Dict[str, Any]


@dataclass
class FunctionGraphNode(GraphNode):
    """Represents a function in the graph."""

    def __init__(self, name: str, file_path: str, line_start: int, line_end: int,
                 subsystem: str, is_static: bool = False):
        self.id = f"{file_path}::{name}"
        self.label = NodeType.FUNCTION
        self.properties = {
            "name": name,
            "file_path": file_path,
            "line_start": line_start,
            "line_end": line_end,
            "subsystem": subsystem,
            "is_static": is_static,
            "node_type": "Function"
        }


@dataclass
class TestCaseGraphNode(GraphNode):
    """Represents a KUnit test case in the graph."""

    def __init__(self, name: str, file_path: str, test_suite: str,
                 line_start: int = 0, line_end: int = 0):
        self.id = f"{file_path}::{name}"
        self.label = NodeType.TEST_CASE
        self.properties = {
            "name": name,
            "file_path": file_path,
            "test_suite": test_suite,
            "line_start": line_start,
            "line_end": line_end,
            "node_type": "TestCase"
        }


@dataclass
class FileGraphNode(GraphNode):
    """Represents a source file in the graph."""

    def __init__(self, file_path: str, subsystem: str,
                 function_count: int = 0, line_count: int = 0):
        self.id = file_path
        self.label = NodeType.FILE
        self.properties = {
            "path": file_path,
            "subsystem": subsystem,
            "function_count": function_count,
            "line_count": line_count,
            "node_type": "File"
        }


@dataclass
class SubsystemGraphNode(GraphNode):
    """Represents a kernel subsystem in the graph."""

    def __init__(self, name: str, path: str,
                 file_count: int = 0, function_count: int = 0):
        self.id = name
        self.label = NodeType.SUBSYSTEM
        self.properties = {
            "name": name,
            "path": path,
            "file_count": file_count,
            "function_count": function_count,
            "node_type": "Subsystem"
        }


@dataclass
class GraphRelationship:
    """Base class for all graph relationships."""
    label: RelationType
    source_id: str
    target_id: str
    properties: Dict[str, Any]


@dataclass
class CallsRelationship(GraphRelationship):
    """Represents a function call relationship."""

    def __init__(self, caller_id: str, callee_id: str,
                 call_site_line: int = 0, file_path: str = ""):
        self.label = RelationType.CALLS
        self.source_id = caller_id
        self.target_id = callee_id
        self.properties = {
            "call_site_line": call_site_line,
            "file_path": file_path,
            "relationship_type": "CALLS"
        }


@dataclass
class CoversRelationship(GraphRelationship):
    """Represents a test coverage relationship."""

    def __init__(self, test_id: str, function_id: str,
                 coverage_type: str = "direct"):
        self.label = RelationType.COVERS
        self.source_id = test_id
        self.target_id = function_id
        self.properties = {
            "coverage_type": coverage_type,  # direct, indirect, potential
            "relationship_type": "COVERS"
        }


@dataclass
class ContainsRelationship(GraphRelationship):
    """Represents a containment relationship (e.g., File contains Function)."""

    def __init__(self, container_id: str, contained_id: str):
        self.label = RelationType.CONTAINS
        self.source_id = container_id
        self.target_id = contained_id
        self.properties = {
            "relationship_type": "CONTAINS"
        }


@dataclass
class BelongsToRelationship(GraphRelationship):
    """Represents a belongs-to relationship (e.g., File belongs to Subsystem)."""

    def __init__(self, item_id: str, parent_id: str):
        self.label = RelationType.BELONGS_TO
        self.source_id = item_id
        self.target_id = parent_id
        self.properties = {
            "relationship_type": "BELONGS_TO"
        }


# Cypher query templates for schema creation
SCHEMA_CONSTRAINTS = """
// Create uniqueness constraints for node IDs
CREATE CONSTRAINT function_id IF NOT EXISTS FOR (f:Function) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT test_id IF NOT EXISTS FOR (t:TestCase) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT file_id IF NOT EXISTS FOR (f:File) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT subsystem_id IF NOT EXISTS FOR (s:Subsystem) REQUIRE s.id IS UNIQUE;

// Create indexes for frequently queried properties
CREATE INDEX function_name IF NOT EXISTS FOR (f:Function) ON (f.name);
CREATE INDEX function_subsystem IF NOT EXISTS FOR (f:Function) ON (f.subsystem);
CREATE INDEX test_name IF NOT EXISTS FOR (t:TestCase) ON (t.name);
CREATE INDEX file_path IF NOT EXISTS FOR (f:File) ON (f.path);
"""

SCHEMA_INDEXES = """
// Create composite indexes for complex queries
CREATE INDEX function_location IF NOT EXISTS FOR (f:Function) ON (f.file_path, f.line_start);
CREATE INDEX call_location IF NOT EXISTS FOR ()-[c:CALLS]->() ON (c.file_path, c.call_site_line);
"""


def get_node_merge_query(node: GraphNode) -> str:
    """
    Generate a Cypher MERGE query for a node.

    Args:
        node: GraphNode to merge

    Returns:
        Cypher query string
    """
    label = node.label.value
    props = ", ".join([f"{k}: ${k}" for k in node.properties.keys()])

    return f"""
    MERGE (n:{label} {{id: $id}})
    SET n += {{{props}}}
    RETURN n
    """


def get_relationship_merge_query(rel: GraphRelationship) -> str:
    """
    Generate a Cypher MERGE query for a relationship.

    Args:
        rel: GraphRelationship to merge

    Returns:
        Cypher query string
    """
    label = rel.label.value
    props = ", ".join([f"{k}: ${k}" for k in rel.properties.keys()]) if rel.properties else ""
    props_clause = f"{{{props}}}" if props else ""

    return f"""
    MATCH (source {{id: $source_id}})
    MATCH (target {{id: $target_id}})
    MERGE (source)-[r:{label} {props_clause}]->(target)
    RETURN r
    """


if __name__ == "__main__":
    # Example usage
    func_node = FunctionGraphNode(
        name="ext4_map_blocks",
        file_path="/workspaces/ubuntu/linux-6.13/fs/ext4/inode.c",
        line_start=100,
        line_end=250,
        subsystem="ext4",
        is_static=False
    )

    print(f"Function Node: {func_node.id}")
    print(f"Properties: {func_node.properties}")
    print(f"\nMerge Query:\n{get_node_merge_query(func_node)}")
