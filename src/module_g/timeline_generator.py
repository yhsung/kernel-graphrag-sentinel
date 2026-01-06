"""
TimelineGenerator: Generate visual timelines of code evolution

This module generates ASCII, Markdown, and Mermaid timeline visualizations
showing how functions and files have evolved over time.
"""

import logging
from typing import List

from .evolution_tracker import EvolutionTracker

logger = logging.getLogger(__name__)


class TimelineGenerator:
    """
    Generate visual timeline representations.

    Creates ASCII art, Markdown, and Mermaid diagrams showing function
    evolution over time.
    """

    def __init__(self, graph_store, evolution_tracker: EvolutionTracker):
        """
        Initialize the timeline generator.

        Args:
            graph_store: Neo4j graph store instance
            evolution_tracker: EvolutionTracker instance
        """
        self.store = graph_store
        self.tracker = evolution_tracker

    def generate_function_timeline(
        self,
        function_name: str,
        format: str = 'ascii'
    ) -> str:
        """
        Generate timeline of function modifications.

        Args:
            function_name: Name of the function
            format: 'ascii', 'markdown', or 'mermaid'

        Returns:
            Formatted timeline string
        """
        history = self.tracker.track_function_history(function_name)

        if format == 'ascii':
            return self._format_ascii_timeline(function_name, history)
        elif format == 'markdown':
            return self._format_markdown_timeline(function_name, history)
        elif format == 'mermaid':
            return self._format_mermaid_timeline(function_name, history)
        else:
            raise ValueError(f"Unknown format: {format}")

    def _format_ascii_timeline(
        self,
        function_name: str,
        history: List[dict]
    ) -> str:
        """
        Generate ASCII timeline visualization.

        Example:
            2019-03-20 │ Introduced (a1b2c3d4)
                       │ Lines: 45 | Complexity: 3
        """
        if not history:
            return f"No history found for {function_name}"

        lines = []
        lines.append(f"{function_name} - Evolution Timeline")
        lines.append("=" * 60)
        lines.append("")

        for entry in history:
            date = entry['date'].split(' ')[0]  # Extract YYYY-MM-DD
            commit_hash = entry['commit_hash']
            message = entry['message'][:60]

            lines.append(f"{date} │ {message} ({commit_hash})")
            lines.append(f"           │ Author: {entry['author']}")
            lines.append(f"           │ Complexity: {entry['complexity']}")

            if entry < history[-1]:  # Not the last entry
                lines.append("           │")

        return '\n'.join(lines)

    def _format_markdown_timeline(
        self,
        function_name: str,
        history: List[dict]
    ) -> str:
        """
        Generate Markdown timeline.

        Example:
            ## 2019-03-20 - Introduced
            - **Commit**: a1b2c3d4
            - **Author**: John Doe
            - **Message**: Add initial implementation
        """
        if not history:
            return f"# {function_name}\n\nNo history found."

        lines = []
        lines.append(f"# {function_name} - Evolution Timeline\n")

        for i, entry in enumerate(reversed(history), 1):
            date = entry['date'].split(' ')[0]
            lines.append(f"## {date} - {entry['message'][:50]}")
            lines.append(f"- **Commit**: {entry['commit_hash']}")
            lines.append(f"- **Author**: {entry['author']}")
            lines.append(f"- **Complexity**: {entry['complexity']}")
            lines.append("")

        return '\n'.join(lines)

    def _format_mermaid_timeline(
        self,
        function_name: str,
        history: List[dict]
    ) -> str:
        """
        Generate Mermaid timeline diagram.

        Example:
            timeline
                title {function_name} Evolution
                2019-03-20 : Introduced : a1b2c3d4
                2020-06-15 : Modified : b2c3d4e5
        """
        if not history:
            return f"timeline\n    title {function_name}\n    No history found"

        lines = ['timeline']
        lines.append(f"    title {function_name} Evolution")

        for entry in reversed(history):
            date = entry['date'].split(' ')[0]
            message = entry['message'][:30]
            commit_hash = entry['commit_hash']
            lines.append(f"    {date} : {message} : {commit_hash}")

        return '\n'.join(lines)

    def format_complexity_trend(self, function_name: str, trend: dict) -> str:
        """
        Format complexity trend analysis.

        Args:
            function_name: Name of the function
            trend: Trend analysis dict from EvolutionTracker

        Returns:
            Formatted trend string
        """
        lines = []
        lines.append("\nTrend Analysis:")
        lines.append(f"  Complexity: {trend['initial_complexity']} → {trend['current_complexity']}")
        lines.append(f"  Change: {trend['complexity_change']:+d}")
        lines.append(f"  Trend: {trend['trend'].upper()}")

        if trend['trend'] == 'increasing':
            lines.append("  ⚠️  Complexity increasing - consider refactoring")
        elif trend['trend'] == 'decreasing':
            lines.append("  ✓ Complexity decreasing - good maintenance")

        return '\n'.join(lines)
