"""
AuthorAnalytics: Calculate code ownership metrics

This module analyzes git history to calculate code ownership
by author, identifying maintainers and contributors.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class AuthorAnalytics:
    """
    Analyze code ownership and contribution metrics.

    Identifies top contributors, ownership percentages, and
    maintainer information for subsystems and functions.
    """

    def __init__(self, graph_store):
        """
        Initialize the author analytics.

        Args:
            graph_store: Neo4j graph store instance
        """
        self.store = graph_store

    def get_subsystem_owners(self, subsystem: str) -> List[Dict[str, Any]]:
        """
        Get code ownership metrics for a subsystem.

        Args:
            subsystem: Subsystem name (e.g., "fs/ext4")

        Returns:
            List of dicts with author stats
        """
        # This would query the graph for GitAuthor nodes linked to files in subsystem
        # For now, return placeholder
        query = """
        MATCH (a:GitAuthor)-[r:AUTHORED_COMMIT]->(c:GitCommit)
        MATCH (c)-[m:MODIFIES_FILE]->(f:File)
        WHERE f.path STARTS WITH $subsystem
        RETURN a.name as author, a.email as email,
               count(c) as commits,
               sum(m.lines_added) as lines_added,
               sum(m.lines_removed) as lines_removed
        ORDER BY commits DESC
        LIMIT 20
        """

        try:
            results = self.store.execute_query(query, {'subsystem': subsystem})

            owners = []
            total_lines = sum(r.get('lines_added', 0) for r in results)

            for record in results:
                lines = record.get('lines_added', 0)
                ownership_pct = (lines / total_lines * 100) if total_lines > 0 else 0

                owners.append({
                    'author': record.get('author', 'Unknown'),
                    'email': record.get('email', ''),
                    'commits': record.get('commits', 0),
                    'lines_added': record.get('lines_added', 0),
                    'lines_removed': record.get('lines_removed', 0),
                    'ownership_pct': round(ownership_pct, 1),
                })

            return owners

        except Exception as e:
            logger.error(f"Failed to get subsystem owners: {e}")
            return []

    def get_function_owners(self, function_name: str) -> List[Dict[str, Any]]:
        """
        Get all authors who modified a function.

        Args:
            function_name: Name of the function

        Returns:
            List of dicts with author contributions
        """
        query = """
        MATCH (c:GitCommit)-[r:DEFINES_FUNCTION]->(f:Function {name: $function_name})
        RETURN c.author_name as author, c.author_email as email,
               c.author_date as last_modified,
               sum(r.lines_added) + sum(r.lines_removed) as total_changes
        ORDER BY last_modified DESC
        """

        try:
            results = self.store.execute_query(query, {'function_name': function_name})

            owners = []
            for record in results:
                owners.append({
                    'author': record.get('author', 'Unknown'),
                    'email': record.get('email', ''),
                    'last_modified': record.get('last_modified', ''),
                    'total_changes': record.get('total_changes', 0),
                })

            return owners

        except Exception as e:
            logger.error(f"Failed to get function owners: {e}")
            return []
