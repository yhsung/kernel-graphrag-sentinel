"""
LogSearch: Quick dmesg → code lookup

This module provides fast search functionality to find log statements
from error messages (e.g., from dmesg output).
"""

import re
import logging
from typing import List, Optional, Dict, Tuple
from difflib import SequenceMatcher

from .schema import LogStatement

logger = logging.getLogger(__name__)


class LogSearch:
    """
    Search log statements by message pattern.

    Provides fast dmesg → code lookup with fuzzy matching support.
    """

    def __init__(self):
        """Initialize the log search."""
        self.log_statements: List[LogStatement] = []
        self.index: Dict[str, List[LogStatement]] = {}

    def index_logs(self, log_statements: List[LogStatement]):
        """
        Build search index from log statements.

        Args:
            log_statements: List of LogStatement objects to index
        """
        self.log_statements = log_statements
        self.index = self._build_index(log_statements)
        logger.info(f"Indexed {len(log_statements)} log statements for search")

    def _build_index(self, log_statements: List[LogStatement]) -> Dict[str, List[LogStatement]]:
        """
        Build search index for fast lookups.

        Args:
            log_statements: List of LogStatement objects

        Returns:
            Dictionary mapping words to lists of LogStatement objects
        """
        index = {}

        for log in log_statements:
            # Extract words from format string
            words = self._extract_words(log.format_string)

            # Index each word
            for word in words:
                if word not in index:
                    index[word] = []
                index[word].append(log)

        return index

    def _extract_words(self, text: str) -> List[str]:
        """
        Extract searchable words from text.

        Args:
            text: Input text

        Returns:
            List of lowercase words (3+ characters)
        """
        # Remove format specifiers
        text = re.sub(r'%[a-zA-Z]+', '', text)

        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        return words

    def search(self, pattern: str, exact_match: bool = False) -> List[LogStatement]:
        """
        Search for logs matching a pattern.

        Args:
            pattern: Search pattern (text from dmesg or error message)
            exact_match: If True, only return exact matches

        Returns:
            List of matching LogStatement objects, sorted by relevance
        """
        if not pattern:
            return []

        # Normalize pattern
        pattern_normalized = pattern.lower().strip()

        # Try exact match first
        exact_matches = self._exact_match(pattern_normalized)
        if exact_matches:
            return exact_matches

        if exact_match:
            return []

        # Try substring match
        substring_matches = self._substring_match(pattern_normalized)
        if substring_matches:
            return substring_matches

        # Try word match
        word_matches = self._word_match(pattern_normalized)
        if word_matches:
            return word_matches

        # Try fuzzy match as last resort
        fuzzy_matches = self._fuzzy_match(pattern_normalized)
        return fuzzy_matches

    def _exact_match(self, pattern: str) -> List[LogStatement]:
        """
        Find exact format string matches.

        Args:
            pattern: Search pattern

        Returns:
            List of matching LogStatement objects
        """
        matches = []

        for log in self.log_statements:
            if log.format_string.lower().strip() == pattern:
                matches.append(log)

        return matches

    def _substring_match(self, pattern: str) -> List[LogStatement]:
        """
        Find substring matches in format strings.

        Args:
            pattern: Search pattern

        Returns:
            List of matching LogStatement objects, sorted by match position
        """
        matches = []

        for log in self.log_statements:
            if pattern in log.format_string.lower():
                # Calculate match score (earlier match = higher score)
                match_pos = log.format_string.lower().find(pattern)
                matches.append((log, match_pos))

        # Sort by match position (earlier is better)
        matches.sort(key=lambda x: x[1])

        return [log for log, _ in matches]

    def _word_match(self, pattern: str) -> List[LogStatement]:
        """
        Find logs containing words from pattern.

        Args:
            pattern: Search pattern

        Returns:
            List of matching LogStatement objects, sorted by relevance
        """
        # Extract words from pattern
        pattern_words = set(self._extract_words(pattern))

        if not pattern_words:
            return []

        # Score each log by number of matching words
        scored = []
        for log in self.log_statements:
            log_words = set(self._extract_words(log.format_string))
            matching_words = pattern_words & log_words

            if matching_words:
                score = len(matching_words) / len(pattern_words)
                scored.append((log, score))

        # Sort by score (descending)
        scored.sort(key=lambda x: x[1], reverse=True)

        # Return matches with at least 50% word overlap
        return [log for log, score in scored if score >= 0.5]

    def _fuzzy_match(self, pattern: str, min_similarity: float = 0.6) -> List[LogStatement]:
        """
        Find fuzzy matches using string similarity.

        Args:
            pattern: Search pattern
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of matching LogStatement objects, sorted by similarity
        """
        scored = []

        for log in self.log_statements:
            # Calculate similarity using SequenceMatcher
            similarity = SequenceMatcher(
                None,
                pattern,
                log.format_string.lower(),
            ).ratio()

            if similarity >= min_similarity:
                scored.append((log, similarity))

        # Sort by similarity (descending)
        scored.sort(key=lambda x: x[1], reverse=True)

        return [log for log, _ in scored]

    def find_by_function(self, function_name: str) -> List[LogStatement]:
        """
        Find all logs in a specific function.

        Args:
            function_name: Function name to search for

        Returns:
            List of LogStatement objects in the function
        """
        return [
            log for log in self.log_statements
            if log.function == function_name
        ]

    def find_by_file(self, file_path: str) -> List[LogStatement]:
        """
        Find all logs in a specific file.

        Args:
            file_path: File path to search for

        Returns:
            List of LogStatement objects in the file
        """
        return [
            log for log in self.log_statements
            if log.file_path == file_path
        ]

    def find_by_severity(self, severity: int) -> List[LogStatement]:
        """
        Find all logs with a specific severity level.

        Args:
            severity: Severity level (0-7)

        Returns:
            List of LogStatement objects with the severity
        """
        return [
            log for log in self.log_statements
            if log.severity == severity
        ]

    def print_search_results(self, matches: List[LogStatement], pattern: str):
        """
        Print search results in a human-readable format.

        Args:
            matches: List of matching LogStatement objects
            pattern: Original search pattern
        """
        if not matches:
            print(f"\n✓ No matches found for: {pattern}")
            return

        print(f"\n✓ Found {len(matches)} match(es) for: {pattern}\n")

        for i, log in enumerate(matches, 1):
            print(f"{i}. {log.file_path}:{log.line_number}")
            print(f"   Function: {log.function}")
            print(f"   Log function: {log.log_function}")
            print(f"   Log message: \"{log.format_string}\"")

            if log.arguments:
                print(f"   Arguments: {', '.join(log.arguments)}")

            if log.in_error_path and log.error_condition:
                print(f"   Error condition: {log.error_condition}")

            print(f"   Severity: {log.log_level} ({log.severity})")

            if i < len(matches):
                print()

    def get_context(self, log: LogStatement, context_lines: int = 3) -> str:
        """
        Get context lines around a log statement.

        Args:
            log: LogStatement to get context for
            context_lines: Number of lines before and after

        Returns:
            Context string with source code
        """
        try:
            from pathlib import Path

            # Read source file
            source_code = Path(log.file_path).read_text(encoding='utf-8', errors='ignore')
            lines = source_code.split('\n')

            # Get context range
            start = max(0, log.line_number - context_lines - 1)
            end = min(len(lines), log.line_number + context_lines)

            # Build context string
            context_lines_list = []
            for i in range(start, end):
                line_num = i + 1
                prefix = ">>> " if line_num == log.line_number else "    "
                context_lines_list.append(f"{prefix}{line_num:4d}: {lines[i]}")

            return '\n'.join(context_lines_list)

        except Exception as e:
            logger.warning(f"Failed to get context for {log.file_path}:{log.line_number}: {e}")
            return ""
