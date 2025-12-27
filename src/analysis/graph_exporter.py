"""
Graph Export Module
Exports call graphs in various formats: DOT (Graphviz), Mermaid, JSON
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """Represents a node in the call graph."""
    name: str
    file: str
    subsystem: str
    node_type: str = "function"


@dataclass
class GraphEdge:
    """Represents an edge in the call graph."""
    source: str
    target: str
    depth: int
    edge_type: str = "calls"


class GraphExporter:
    """Export call graphs in various formats."""

    def __init__(self, graph_store):
        """
        Initialize graph exporter.

        Args:
            graph_store: Neo4j graph store instance
        """
        self.graph_store = graph_store

    def export_callgraph(self, function_name: str, max_depth: int = 3,
                        format: str = "mermaid", direction: str = "both") -> str:
        """
        Export call graph for a function.

        Args:
            function_name: Target function name
            max_depth: Maximum traversal depth
            format: Export format (mermaid, dot, json)
            direction: Graph direction (callers, callees, both)

        Returns:
            Formatted graph string
        """
        # Query graph data
        nodes, edges = self._query_graph_data(function_name, max_depth, direction)

        if not nodes:
            logger.warning(f"No graph data found for {function_name}")
            return f"# No graph data found for {function_name}"

        # Export in requested format
        if format == "mermaid":
            return self._export_mermaid(function_name, nodes, edges)
        elif format == "dot":
            return self._export_dot(function_name, nodes, edges)
        elif format == "json":
            return self._export_json(function_name, nodes, edges)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _query_graph_data(self, function_name: str, max_depth: int,
                         direction: str) -> tuple:
        """
        Query Neo4j for graph data.

        Returns:
            Tuple of (nodes, edges)
        """
        nodes = {}  # {name: GraphNode}
        edges = []  # List of GraphEdge

        # Get target function
        target_query = """
        MATCH (target:Function {name: $func_name})
        RETURN target.name as name, target.path as file,
               target.subsystem as subsystem
        LIMIT 1
        """
        result = self.graph_store.execute_query(
            target_query,
            {"func_name": function_name}
        )

        if not result:
            return {}, []

        target_data = result[0]
        nodes[function_name] = GraphNode(
            name=function_name,
            file=target_data.get("file", "unknown"),
            subsystem=target_data.get("subsystem", "unknown")
        )

        # Query callers if requested
        if direction in ["callers", "both"]:
            callers_query = """
            MATCH path = (caller:Function)-[:CALLS*1..{depth}]->(target:Function {{name: $func_name}})
            WITH caller, target, length(path) as depth
            RETURN DISTINCT
                caller.name as caller_name,
                caller.path as caller_file,
                caller.subsystem as caller_subsystem,
                target.name as target_name,
                depth
            ORDER BY depth, caller_name
            LIMIT 100
            """.format(depth=max_depth)

            callers_result = self.graph_store.execute_query(
                callers_query,
                {"func_name": function_name}
            )

            for record in callers_result:
                caller_name = record["caller_name"]
                if caller_name not in nodes:
                    nodes[caller_name] = GraphNode(
                        name=caller_name,
                        file=record.get("caller_file", "unknown"),
                        subsystem=record.get("caller_subsystem", "unknown")
                    )
                edges.append(GraphEdge(
                    source=caller_name,
                    target=record["target_name"],
                    depth=record["depth"]
                ))

        # Query callees if requested
        if direction in ["callees", "both"]:
            callees_query = """
            MATCH path = (target:Function {{name: $func_name}})-[:CALLS*1..{depth}]->(callee:Function)
            WITH target, callee, length(path) as depth
            RETURN DISTINCT
                target.name as target_name,
                callee.name as callee_name,
                callee.path as callee_file,
                callee.subsystem as callee_subsystem,
                depth
            ORDER BY depth, callee_name
            LIMIT 100
            """.format(depth=max_depth)

            callees_result = self.graph_store.execute_query(
                callees_query,
                {"func_name": function_name}
            )

            for record in callees_result:
                callee_name = record["callee_name"]
                if callee_name not in nodes:
                    nodes[callee_name] = GraphNode(
                        name=callee_name,
                        file=record.get("callee_file", "unknown"),
                        subsystem=record.get("callee_subsystem", "unknown")
                    )
                edges.append(GraphEdge(
                    source=record["target_name"],
                    target=callee_name,
                    depth=record["depth"]
                ))

        return nodes, edges

    def _export_mermaid(self, function_name: str, nodes: Dict[str, GraphNode],
                       edges: List[GraphEdge]) -> str:
        """Export as Mermaid diagram."""
        lines = ["```mermaid", "graph TD"]

        # Add nodes with styling
        for name, node in nodes.items():
            # Escape special characters
            safe_name = name.replace("-", "_").replace(".", "_")
            label = name

            # Style target node differently
            if name == function_name:
                lines.append(f'    {safe_name}["{label}"]')
                lines.append(f'    style {safe_name} fill:#f96,stroke:#333,stroke-width:4px')
            else:
                lines.append(f'    {safe_name}["{label}"]')

        # Add edges with labels
        edge_counts = {}
        for edge in edges:
            safe_source = edge.source.replace("-", "_").replace(".", "_")
            safe_target = edge.target.replace("-", "_").replace(".", "_")

            # Count multiple edges
            edge_key = (safe_source, safe_target)
            edge_counts[edge_key] = edge_counts.get(edge_key, 0) + 1

        for (source, target), count in edge_counts.items():
            if count > 1:
                lines.append(f'    {source} -->|{count}x calls| {target}')
            else:
                lines.append(f'    {source} --> {target}')

        lines.append("```")
        return "\n".join(lines)

    def _export_dot(self, function_name: str, nodes: Dict[str, GraphNode],
                   edges: List[GraphEdge]) -> str:
        """Export as Graphviz DOT format."""
        lines = [
            "digraph callgraph {",
            '    graph [rankdir=LR, fontname="Arial"];',
            '    node [shape=box, style=rounded, fontname="Arial"];',
            '    edge [fontname="Arial"];',
            ""
        ]

        # Add nodes
        for name, node in nodes.items():
            # Escape quotes
            safe_name = name.replace('"', '\\"')
            file_short = node.file.split('/')[-1] if node.file else "unknown"
            label = f"{name}\\n({file_short})"

            # Style target node
            if name == function_name:
                lines.append(f'    "{safe_name}" [label="{label}", fillcolor="#ff9966", style="rounded,filled", penwidth=3];')
            else:
                lines.append(f'    "{safe_name}" [label="{label}"];')

        lines.append("")

        # Add edges with counts
        edge_counts = {}
        for edge in edges:
            edge_key = (edge.source, edge.target)
            edge_counts[edge_key] = edge_counts.get(edge_key, 0) + 1

        for (source, target), count in edge_counts.items():
            safe_source = source.replace('"', '\\"')
            safe_target = target.replace('"', '\\"')
            if count > 1:
                lines.append(f'    "{safe_source}" -> "{safe_target}" [label="{count}x"];')
            else:
                lines.append(f'    "{safe_source}" -> "{safe_target}";')

        lines.append("}")
        return "\n".join(lines)

    def _export_json(self, function_name: str, nodes: Dict[str, GraphNode],
                    edges: List[GraphEdge]) -> str:
        """Export as JSON format."""
        graph_data = {
            "target_function": function_name,
            "nodes": [
                {
                    "id": node.name,
                    "label": node.name,
                    "file": node.file,
                    "subsystem": node.subsystem,
                    "is_target": node.name == function_name
                }
                for node in nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "depth": edge.depth,
                    "type": edge.edge_type
                }
                for edge in edges
            ],
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "unique_files": len(set(n.file for n in nodes.values())),
                "unique_subsystems": len(set(n.subsystem for n in nodes.values()))
            }
        }

        return json.dumps(graph_data, indent=2)

    def generate_mermaid_for_impact(self, impact_data: Dict[str, Any]) -> str:
        """
        Generate Mermaid diagram from impact analysis data.

        Args:
            impact_data: Impact analysis result dictionary

        Returns:
            Mermaid diagram string
        """
        function_name = impact_data.get("function", "unknown")
        direct_callers = impact_data.get("direct_callers", [])
        direct_callees = impact_data.get("direct_callees", [])

        lines = ["```mermaid", "graph TD"]

        # Target function (center)
        safe_target = function_name.replace("-", "_").replace(".", "_")
        lines.append(f'    {safe_target}["{function_name}"]')
        lines.append(f'    style {safe_target} fill:#f96,stroke:#333,stroke-width:4px')

        # Direct callers (above)
        for i, caller in enumerate(direct_callers[:10]):  # Limit to 10
            caller_name = caller.get("name", f"caller_{i}")
            safe_caller = caller_name.replace("-", "_").replace(".", "_")
            lines.append(f'    {safe_caller}["{caller_name}"]')
            lines.append(f'    {safe_caller} --> {safe_target}')

        # Direct callees (below)
        for i, callee in enumerate(direct_callees[:10]):  # Limit to 10
            callee_name = callee.get("name", f"callee_{i}")
            safe_callee = callee_name.replace("-", "_").replace(".", "_")
            lines.append(f'    {safe_callee}["{callee_name}"]')
            lines.append(f'    {safe_target} --> {safe_callee}')

        lines.append("```")
        return "\n".join(lines)
