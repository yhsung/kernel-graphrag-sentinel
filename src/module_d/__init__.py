"""
Module D: Data Flow Analysis
Tracks how data flows through kernel code for security and impact analysis.
"""

from .variable_tracker import VariableTracker, VariableDefinition, VariableUse
from .flow_builder import FlowBuilder, DataFlowEdge, InterProcFlow
from .flow_schema import (
    VariableNode,
    DataSourceNode,
    FlowRelationship,
    get_variable_node_query,
    get_flow_relationship_query,
)

__all__ = [
    "VariableTracker",
    "VariableDefinition",
    "VariableUse",
    "FlowBuilder",
    "DataFlowEdge",
    "InterProcFlow",
    "VariableNode",
    "DataSourceNode",
    "FlowRelationship",
    "get_variable_node_query",
    "get_flow_relationship_query",
]
