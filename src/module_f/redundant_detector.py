"""
RedundantDetector: Find redundant and duplicate log statements

This module identifies duplicate log messages in call chains and
flags potential log pollution.
"""

import logging
from typing import List, Dict, Set, Tuple
from collections import defaultdict

from .schema import (
    LogStatement,
    RedundantLog,
)

logger = logging.getLogger(__name__)


class RedundantDetector:
    """
    Detect redundant and duplicate log statements.

    Identifies:
    - Same log message appearing multiple times in call chain
    - Duplicate log messages in same function
    - Potential log pollution (too many logs in one function)
    """

    def __init__(self, max_logs_per_function: int = 10):
        """
        Initialize the redundant log detector.

        Args:
            max_logs_per_function: Flag warning if function has more logs than this
        """
        self.max_logs_per_function = max_logs_per_function

    def find_redundant_logs(self, log_statements: List[LogStatement]) -> List[RedundantLog]:
        """
        Find redundant log statements.

        Args:
            log_statements: List of LogStatement objects to analyze

        Returns:
            List of RedundantLog objects
        """
        redundant_logs = []

        # Group by format string (case-insensitive, normalized)
        format_groups = self._group_by_format_string(log_statements)

        # Find duplicates
        for format_string, logs in format_groups.items():
            if len(logs) > 1:
                # Check if they're in the same call chain
                redundant_log = self._analyze_redundancy(format_string, logs)
                if redundant_log:
                    redundant_logs.append(redundant_log)

        # Check for log pollution
        pollution_warnings = self._detect_log_pollution(log_statements)
        redundant_logs.extend(pollution_warnings)

        return redundant_logs

    def _group_by_format_string(self, log_statements: List[LogStatement]) -> Dict[str, List[LogStatement]]:
        """
        Group log statements by format string.

        Args:
            log_statements: List of LogStatement objects

        Returns:
            Dictionary mapping format strings to lists of LogStatement objects
        """
        groups = defaultdict(list)

        for log in log_statements:
            # Normalize format string for grouping
            normalized = self._normalize_format_string(log.format_string)
            groups[normalized].append(log)

        return groups

    def _normalize_format_string(self, format_string: str) -> str:
        """
        Normalize format string for comparison.

        Removes whitespace variations and normalizes format specifiers.

        Args:
            format_string: Original format string

        Returns:
            Normalized format string
        """
        # Remove leading/trailing whitespace
        normalized = format_string.strip()

        # Remove quotes
        normalized = normalized.strip('"').strip("'")

        # Collapse multiple spaces
        import re
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized

    def _analyze_redundancy(self, format_string: str, logs: List[LogStatement]) -> Optional[RedundantLog]:
        """
        Analyze if logs with same format string are redundant.

        Args:
            format_string: The format string
            logs: List of LogStatement objects with this format string

        Returns:
            RedundantLog object if redundancy detected, None otherwise
        """
        if len(logs) <= 1:
            return None

        # Create occurrences list
        occurrences = [
            (log.function, log.line_number, log.log_function)
            for log in logs
        ]

        # Determine call chain depth
        # This is simplified - real implementation would use graph analysis
        call_chain_depth = len(set(func for func, _, _ in occurrences))

        # Generate recommendation
        recommendation = self._generate_recommendation(format_string, logs, call_chain_depth)

        return RedundantLog(
            format_string=format_string,
            occurrences=occurrences,
            call_chain_depth=call_chain_depth,
            recommendation=recommendation,
        )

    def _generate_recommendation(
        self,
        format_string: str,
        logs: List[LogStatement],
        call_chain_depth: int,
    ) -> str:
        """
        Generate recommendation for handling redundant logs.

        Args:
            format_string: The duplicate format string
            logs: List of duplicate logs
            call_chain_depth: Number of unique functions in call chain

        Returns:
            Recommendation string
        """
        if call_chain_depth == 1:
            # All in same function
            func = logs[0].function
            return (f"Duplicate log '{format_string}' appears {len(logs)} times "
                   f"in the same function ({func}). Consider removing duplicates.")

        else:
            # In call chain
            top_function = self._find_top_function(logs)
            return (f"Log '{format_string}' appears {len(logs)} times across "
                   f"{call_chain_depth} functions in the call chain. "
                   f"Consider consolidating to top-level caller ({top_function}) "
                   f"and removing from lower-level functions.")

    def _find_top_function(self, logs: List[LogStatement]) -> str:
        """
        Find the top-level function in a set of logs.

        This is heuristic - real implementation would use call graph analysis.

        Args:
            logs: List of LogStatement objects

        Returns:
            Name of likely top-level function
        """
        # Simple heuristic: function with most logs is likely top-level
        func_counts = defaultdict(int)
        for log in logs:
            func_counts[log.function] += 1

        return max(func_counts.items(), key=lambda x: x[1])[0]

    def _detect_log_pollution(self, log_statements: List[LogStatement]) -> List[RedundantLog]:
        """
        Detect functions with too many logs (log pollution).

        Args:
            log_statements: List of LogStatement objects

        Returns:
            List of RedundantLog objects for polluted functions
        """
        polluted = []

        # Group by function
        func_logs = defaultdict(list)
        for log in log_statements:
            func_logs[log.function].append(log)

        # Check each function
        for func, logs in func_logs.items():
            if len(logs) > self.max_logs_per_function:
                # Create a RedundantLog for this pollution
                occurrences = [(log.function, log.line_number, log.log_function) for log in logs]

                polluted.append(
                    RedundantLog(
                        format_string=f"<{len(logs)} logs in function>",
                        occurrences=occurrences,
                        call_chain_depth=1,
                        recommendation=(f"Function '{func}' has {len(logs)} log statements, "
                                     f"which may indicate log pollution. "
                                     f"Consider reducing to essential logs only "
                                     f"(threshold: {self.max_logs_per_function})."),
                    )
                )

        return polluted

    def print_redundancy_report(self, redundant_logs: List[RedundantLog]):
        """
        Print a human-readable redundancy report.

        Args:
            redundant_logs: List of RedundantLog objects
        """
        if not redundant_logs:
            print("\n  ✓ No redundant logs detected")
            return

        print(f"\n  ⚠️  Found {len(redundant_logs)} redundancy issues:\n")

        for i, redundant in enumerate(redundant_logs, 1):
            print(f"  {i}. {redundant.format_string}")
            print(f"     Appears {len(redundant.occurrences)} times:")

            for func, line, log_func in redundant.occurrences[:5]:  # Show first 5
                print(f"       - {func}:{line} ({log_func})")

            if len(redundant.occurrences) > 5:
                print(f"       ... and {len(redundant.occurrences) - 5} more")

            print(f"     → {redundant.recommendation}")
            print()
