"""
CoverageAnalyzer: Calculate log coverage and identify gaps

This module analyzes error paths and log statements to determine
which error paths are logged and which are not (gaps).
"""

import logging
from typing import List, Dict, Optional

from .schema import (
    ErrorPath,
    LogStatement,
    CoverageReport,
    LogSuggestion,
)
from .log_extractor import LogExtractor
from .error_path_detector import ErrorPathDetector

logger = logging.getLogger(__name__)


class CoverageAnalyzer:
    """
    Analyze log coverage for error paths.

    Determines which error paths have log statements and which don't,
    calculates coverage percentage, and identifies gaps.
    """

    def __init__(self):
        """Initialize the coverage analyzer."""
        self.log_extractor = LogExtractor()
        self.error_detector = ErrorPathDetector()

    def analyze_function(
        self,
        source_code: str,
        function_name: str,
        file_path: str = "<unknown>",
    ) -> CoverageReport:
        """
        Analyze log coverage for a specific function.

        Args:
            source_code: C source code as string
            function_name: Name of function to analyze
            file_path: File path for reference

        Returns:
            CoverageReport object with analysis results
        """
        # Extract log statements
        log_statements = self.log_extractor.extract_from_code(source_code, file_path)

        # Filter logs for this function
        function_logs = [
            log for log in log_statements
            if log.function == function_name
        ]

        # Find error paths
        all_error_paths = self.error_detector.find_error_paths_in_code(
            source_code, file_path, function_name
        )

        error_paths = all_error_paths.get(function_name, [])

        # Match logs to error paths
        self._match_logs_to_paths(error_paths, function_logs)

        # Calculate coverage
        total_paths = len(error_paths)
        logged_paths = sum(1 for ep in error_paths if ep.has_log)
        coverage_percentage = (logged_paths / total_paths * 100) if total_paths > 0 else 100.0

        # Identify unlogged paths (gaps)
        unlogged_paths = [ep for ep in error_paths if not ep.has_log]

        logger.info(
            f"{function_name}: {coverage_percentage:.1f}% coverage "
            f"({logged_paths}/{total_paths} error paths logged)"
        )

        return CoverageReport(
            function=function_name,
            file_path=file_path,
            total_paths=total_paths,
            logged_paths=logged_paths,
            coverage_percentage=coverage_percentage,
            error_paths=error_paths,
            unlogged_paths=unlogged_paths,
        )

    def analyze_file(self, file_path: str) -> Dict[str, CoverageReport]:
        """
        Analyze log coverage for all functions in a file.

        Args:
            file_path: Path to C source file

        Returns:
            Dictionary mapping function names to CoverageReport objects
        """
        from pathlib import Path

        source_code = Path(file_path).read_text(encoding='utf-8', errors='ignore')

        # Get all functions with error paths
        all_error_paths = self.error_detector.find_error_paths_in_code(source_code, file_path)

        # Extract all log statements
        log_statements = self.log_extractor.extract_from_code(source_code, file_path)

        # Analyze each function
        reports = {}
        for func_name in all_error_paths.keys():
            report = self.analyze_function(source_code, func_name, file_path)
            reports[func_name] = report

        return reports

    def _match_logs_to_paths(self, error_paths: List[ErrorPath], log_statements: List[LogStatement]):
        """
        Match log statements to error paths.

        A log is considered to cover an error path if it appears
        before the error return/goto statement.

        Args:
            error_paths: List of error paths (modified in-place)
            log_statements: List of log statements in the function
        """
        # Sort both by line number
        error_paths_sorted = sorted(error_paths, key=lambda ep: ep.line_number)
        logs_sorted = sorted(log_statements, key=lambda log: log.line_number)

        # For each error path, check if there's a log before it
        for error_path in error_paths_sorted:
            # Find logs that appear before this error path
            preceding_logs = [
                log for log in logs_sorted
                if log.line_number < error_path.line_number
            ]

            if preceding_logs:
                # Use the closest log before the error path
                closest_log = max(preceding_logs, key=lambda log: log.line_number)
                error_path.has_log = True
                error_path.log_statement = closest_log

    def suggest_logs(self, report: CoverageReport, source_code: str) -> List[LogSuggestion]:
        """
        Generate log placement suggestions for unlogged error paths.

        Args:
            report: CoverageReport with unlogged paths
            source_code: Source code string for context

        Returns:
            List of LogSuggestion objects
        """
        suggestions = []

        for error_path in report.unlogged_paths:
            suggestion = self._generate_suggestion(error_path, source_code, report.file_path)
            if suggestion:
                suggestions.append(suggestion)

        return suggestions

    def _generate_suggestion(
        self,
        error_path: ErrorPath,
        source_code: str,
        file_path: str,
    ) -> Optional[LogSuggestion]:
        """
        Generate a log placement suggestion for an unlogged error path.

        Args:
            error_path: Unlogged error path
            source_code: Source code string for context
            file_path: File path for reference

        Returns:
            LogSuggestion object or None
        """
        # Determine log function and severity
        suggested_function = "pr_err"
        suggested_severity = "KERN_ERR"

        # Generate log message based on error type
        if error_path.path_type == 'return':
            error_code = error_path.error_code or "error"
            suggested_message = f"operation failed: {error_code}"
            suggested_arguments = []
        else:  # goto
            label = error_path.goto_label or "error"
            suggested_message = f"operation failed, going to {label}"
            suggested_arguments = []

        # Generate code snippet (simplified - would need more context in real implementation)
        code_snippet = f"    pr_err(\"{suggested_message}\\\\n\");"

        return LogSuggestion(
            line_number=error_path.line_number,
            error_path=error_path,
            suggested_function=suggested_function,
            suggested_severity=suggested_severity,
            suggested_message=suggested_message,
            suggested_arguments=suggested_arguments,
            code_snippet=code_snippet,
        )

    def print_coverage_report(self, report: CoverageReport, verbose: bool = True):
        """
        Print a human-readable coverage report.

        Args:
            report: CoverageReport to print
            verbose: If True, show detailed error path information
        """
        print(f"\n{report.function}: {report.coverage_percentage:.0f}% coverage "
              f"({report.logged_paths}/{report.total_paths} error paths logged)")

        if verbose and report.error_paths:
            print("\n  Error paths:")
            for ep in sorted(report.error_paths, key=lambda e: e.line_number):
                status = "✓" if ep.has_log else "✗"
                error_info = f"{ep.path_type}"

                if ep.path_type == 'return':
                    error_info += f" {ep.error_code or ''}"
                else:  # goto
                    error_info += f" {ep.goto_label}"

                status_text = "[LOGGED]" if ep.has_log else "[NOT LOGGED]"
                print(f"    {status} Line {ep.line_number}: {error_info} {status_text}")

                if ep.has_log and ep.log_statement:
                    print(f"       → {ep.log_statement.log_function}(..., "
                          f"\"{ep.log_statement.format_string}\")")

        if report.unlogged_paths:
            print(f"\n  {len(report.unlogged_paths)} unlogged error paths (gaps)")

    def print_suggestions(self, suggestions: List[LogSuggestion]):
        """
        Print log placement suggestions.

        Args:
            suggestions: List of LogSuggestion objects
        """
        if not suggestions:
            print("\n  No suggestions - all error paths are logged!")
            return

        print(f"\n  Suggestions for {len(suggestions)} unlogged paths:\n")

        for i, suggestion in enumerate(suggestions, 1):
            print(f"  Gap {i}: Line {suggestion.line_number}")
            print(f"    Error: {suggestion.error_path.path_type} "
                  f"{suggestion.error_path.error_code or suggestion.error_path.goto_label}")
            print(f"    Suggestion: Add {suggestion.suggested_function}() before error path")
            print(f"    Code:")
            print(f"      {suggestion.code_snippet}")
            print()
