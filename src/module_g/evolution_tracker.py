"""
EvolutionTracker: Track function evolution across commits

This module tracks how functions and files evolve across git history,
analyzing complexity trends and modification patterns.
"""

import re
import logging
from typing import List, Dict, Any
from datetime import datetime

from .git_extractor import GitExtractor
from .schema import FunctionVersion

logger = logging.getLogger(__name__)


class EvolutionTracker:
    """
    Track function evolution across git commits.

    Analyzes how functions change over time, tracking complexity,
    size, and test coverage trends.
    """

    def __init__(self, graph_store, git_extractor: GitExtractor):
        """
        Initialize the evolution tracker.

        Args:
            graph_store: Neo4j graph store instance
            git_extractor: GitExtractor instance
        """
        self.store = graph_store
        self.extractor = git_extractor

    def track_function_history(self, function_name: str) -> List[Dict[str, Any]]:
        """
        Track full modification history of a function.

        Args:
            function_name: Name of the function

        Returns:
            List of dicts with commit info and changes
        """
        logger.info(f"Tracking evolution of {function_name}")

        # Use git log -S to find all commits that added/removed this function
        try:
            import subprocess
            cmd = [
                'git', 'log',
                '--pretty=format:%H|%an|%ad|%s',
                '--date=iso',
                '-S', function_name,
                '--all'
            ]

            result = subprocess.run(
                cmd,
                cwd=str(self.extractor.repo_path),
                capture_output=True,
                text=True,
                check=True
            )

            output = result.stdout

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to track {function_name}: {e}")
            return []

        history = []
        for line in output.strip().split('\n'):
            if not line:
                continue

            parts = line.split('|')
            if len(parts) != 4:
                continue

            commit_hash, author, date, message = parts

            # Get file changes for this commit
            files = self.extractor.extract_commit_files(commit_hash)

            # Calculate complexity (simplified - would need AST for real complexity)
            complexity = self._estimate_complexity_from_message(message)

            history.append({
                'commit_hash': commit_hash[:8],
                'author': author,
                'date': date,
                'message': message,
                'files_changed': len(files),
                'complexity': complexity,
                'line_count': 0,  # Would need diff parsing
            })

        return history

    def calculate_complexity_trend(self, function_name: str) -> Dict[str, Any]:
        """
        Calculate complexity trend over time.

        Args:
            function_name: Name of the function

        Returns:
            Dict with trend analysis
        """
        history = self.track_function_history(function_name)

        if len(history) < 2:
            return {
                'commits_analyzed': len(history),
                'initial_complexity': history[0]['complexity'] if history else 0,
                'current_complexity': history[0]['complexity'] if history else 0,
                'complexity_change': 0,
                'trend': 'stable',
                'avg_complexity': sum(h['complexity'] for h in history) / len(history) if history else 0,
            }

        initial_complexity = history[-1]['complexity']
        current_complexity = history[0]['complexity']
        complexity_change = current_complexity - initial_complexity

        # Determine trend
        if complexity_change > 2:
            trend = 'increasing'
        elif complexity_change < -2:
            trend = 'decreasing'
        else:
            trend = 'stable'

        avg_complexity = sum(h['complexity'] for h in history) / len(history)

        return {
            'commits_analyzed': len(history),
            'initial_complexity': initial_complexity,
            'current_complexity': current_complexity,
            'complexity_change': complexity_change,
            'trend': trend,
            'avg_complexity': avg_complexity,
        }

    def _estimate_complexity_from_message(self, message: str) -> int:
        """
        Estimate complexity from commit message (heuristic).

        Args:
            message: Commit message

        Returns:
            Estimated complexity (1-10)
        """
        complexity = 3  # Base complexity

        # Keywords indicating increased complexity
        if any(word in message.lower() for word in ['refactor', 'cleanup', 'simplify']):
            complexity -= 1

        if any(word in message.lower() for word in ['add feature', 'implement', 'extend']):
            complexity += 1

        if any(word in message.lower() for word in ['fix', 'bug', 'error', 'leak']):
            complexity += 2

        if 'CVE' in message:
            complexity += 3

        return max(1, min(10, complexity))

    def get_commit_for_date(self, function_name: str, date: str) -> Optional[str]:
        """
        Find the state of a function at a specific date.

        Args:
            function_name: Name of the function
            date: Date in ISO format (YYYY-MM-DD)

        Returns:
            Commit hash at that date or None
        """
        history = self.track_function_history(function_name)

        for entry in history:
            entry_date = entry['date'].split(' ')[0]  # Extract YYYY-MM-DD
            if entry_date <= date:
                return entry['commit_hash']

        return None
