"""
Module D: Data Flow Graph Schema
Extends Neo4j schema with variable and data flow relationships.
"""

from dataclasses import dataclass
from typing import Dict, Any
from enum import Enum


class FlowType(Enum):
    """Types of data flow relationships."""

    ASSIGNMENT = "assignment"  # x = y
    PARAMETER = "parameter"  # func(x) where x flows to param
    RETURN = "return"  # return x
    FIELD_ACCESS = "field_access"  # struct.field
    ARRAY_ACCESS = "array_access"  # arr[i]
    POINTER_DEREF = "pointer_deref"  # *ptr


class SourceType(Enum):
    """Types of data sources for taint analysis."""

    USER_INPUT = "USER_INPUT"  # copy_from_user, etc.
    FILE_IO = "FILE_IO"  # read, write
    NETWORK = "NETWORK"  # socket operations
    DEVICE = "DEVICE"  # device I/O
    KERNEL_PARAM = "KERNEL_PARAM"  # module parameters
    UNKNOWN = "UNKNOWN"


@dataclass
class VariableNode:
    """Represents a variable in the graph database."""

    name: str
    var_type: str
    scope: str  # function name or "global"
    file_path: str
    line_number: int
    is_parameter: bool
    is_pointer: bool
    is_static: bool = False

    def to_cypher_properties(self) -> Dict[str, Any]:
        """Convert to Cypher properties dict."""
        return {
            "name": self.name,
            "type": self.var_type,
            "scope": self.scope,
            "file": self.file_path,
            "line": self.line_number,
            "is_parameter": self.is_parameter,
            "is_pointer": self.is_pointer,
            "is_static": self.is_static,
            "node_type": "Variable",
        }

    @property
    def id(self) -> str:
        """Unique identifier for this variable."""
        return f"{self.file_path}::{self.scope}::{self.name}"


@dataclass
class DataSourceNode:
    """Represents a data source (for taint analysis)."""

    name: str
    source_type: SourceType
    function: str
    file_path: str
    line_number: int
    description: str = ""

    def to_cypher_properties(self) -> Dict[str, Any]:
        """Convert to Cypher properties dict."""
        return {
            "name": self.name,
            "source_type": self.source_type.value,
            "function": self.function,
            "file": self.file_path,
            "line": self.line_number,
            "description": self.description,
            "node_type": "DataSource",
        }

    @property
    def id(self) -> str:
        """Unique identifier for this data source."""
        return f"{self.file_path}::{self.function}::{self.name}"


@dataclass
class FlowRelationship:
    """Represents data flow from one variable to another."""

    from_id: str  # Source variable ID
    to_id: str  # Destination variable ID
    flow_type: FlowType
    line_number: int
    confidence: float = 1.0  # 0.0 to 1.0 (for uncertain flows)

    def to_cypher_properties(self) -> Dict[str, Any]:
        """Convert to Cypher properties dict."""
        return {
            "flow_type": self.flow_type.value,
            "line": self.line_number,
            "confidence": self.confidence,
        }


# Cypher query templates


def get_variable_node_query(var: VariableNode) -> str:
    """
    Generate Cypher query to create/merge a Variable node.

    Returns:
        Cypher MERGE query string
    """
    props = var.to_cypher_properties()

    props_str = ", ".join([f"{k}: ${k}" for k in props.keys()])

    query = f"""
    MERGE (v:Variable {{id: $id}})
    ON CREATE SET v = {{{props_str}}}
    ON MATCH SET v = {{{props_str}}}
    RETURN v
    """

    return query.strip()


def get_data_source_node_query(source: DataSourceNode) -> str:
    """
    Generate Cypher query to create/merge a DataSource node.

    Returns:
        Cypher MERGE query string
    """
    props = source.to_cypher_properties()

    props_str = ", ".join([f"{k}: ${k}" for k in props.keys()])

    query = f"""
    MERGE (s:DataSource {{id: $id}})
    ON CREATE SET s = {{{props_str}}}
    ON MATCH SET s = {{{props_str}}}
    RETURN s
    """

    return query.strip()


def get_flow_relationship_query(flow: FlowRelationship) -> str:
    """
    Generate Cypher query to create a FLOWS_TO relationship.

    Returns:
        Cypher MERGE query string
    """
    query = """
    MATCH (from:Variable {id: $from_id})
    MATCH (to:Variable {id: $to_id})
    MERGE (from)-[r:FLOWS_TO {line: $line}]->(to)
    ON CREATE SET r.flow_type = $flow_type,
                  r.confidence = $confidence
    ON MATCH SET r.flow_type = $flow_type,
                 r.confidence = $confidence
    RETURN r
    """

    return query.strip()


def get_defines_relationship_query(function_id: str, variable_id: str) -> str:
    """
    Generate Cypher query to link Function -> Variable (DEFINES).

    Args:
        function_id: Unique ID of function
        variable_id: Unique ID of variable

    Returns:
        Cypher MERGE query string
    """
    query = """
    MATCH (f:Function {id: $function_id})
    MATCH (v:Variable {id: $variable_id})
    MERGE (f)-[r:DEFINES]->(v)
    RETURN r
    """

    return query.strip()


def get_uses_relationship_query(function_id: str, variable_id: str, line: int) -> str:
    """
    Generate Cypher query to link Function -> Variable (USES).

    Args:
        function_id: Unique ID of function
        variable_id: Unique ID of variable
        line: Line number where variable is used

    Returns:
        Cypher MERGE query string
    """
    query = """
    MATCH (f:Function {id: $function_id})
    MATCH (v:Variable {id: $variable_id})
    MERGE (f)-[r:USES {line: $line}]->(v)
    RETURN r
    """

    return query.strip()


# Schema constraints and indexes

VARIABLE_CONSTRAINTS = [
    "CREATE CONSTRAINT variable_id_unique IF NOT EXISTS FOR (v:Variable) REQUIRE v.id IS UNIQUE",
]

VARIABLE_INDEXES = [
    "CREATE INDEX variable_name_idx IF NOT EXISTS FOR (v:Variable) ON (v.name)",
    "CREATE INDEX variable_scope_idx IF NOT EXISTS FOR (v:Variable) ON (v.scope)",
    "CREATE INDEX variable_file_idx IF NOT EXISTS FOR (v:Variable) ON (v.file)",
]

DATA_SOURCE_CONSTRAINTS = [
    "CREATE CONSTRAINT data_source_id_unique IF NOT EXISTS FOR (s:DataSource) REQUIRE s.id IS UNIQUE",
]

DATA_SOURCE_INDEXES = [
    "CREATE INDEX data_source_type_idx IF NOT EXISTS FOR (s:DataSource) ON (s.source_type)",
    "CREATE INDEX data_source_function_idx IF NOT EXISTS FOR (s:DataSource) ON (s.function)",
]


def get_schema_setup_queries() -> list[str]:
    """
    Get all Cypher queries needed to set up data flow schema.

    Returns:
        List of Cypher query strings for constraints and indexes
    """
    return (
        VARIABLE_CONSTRAINTS
        + VARIABLE_INDEXES
        + DATA_SOURCE_CONSTRAINTS
        + DATA_SOURCE_INDEXES
    )
