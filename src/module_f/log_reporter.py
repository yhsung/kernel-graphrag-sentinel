"""
LogReporter: Generate coverage reports

This module generates comprehensive coverage reports in various formats.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from .schema import (
    CoverageReport,
    LogSuggestion,
    RedundantLog,
    LogStatement,
)

logger = logging.getLogger(__name__)


class LogReporter:
    """
    Generate log coverage reports.

    Supports multiple formats:
    - Markdown (default)
    - JSON (machine-readable)
    - Plain text (console output)
    """

    def __init__(self):
        """Initialize the log reporter."""
        pass

    def generate_markdown_report(
        self,
        coverage_reports: Dict[str, CoverageReport],
        suggestions: Optional[Dict[str, List[LogSuggestion]]] = None,
        redundant_logs: Optional[List[RedundantLog]] = None,
        title: str = "Log Coverage Report",
    ) -> str:
        """
        Generate a Markdown coverage report.

        Args:
            coverage_reports: Dictionary of function → CoverageReport
            suggestions: Optional dictionary of function → LogSuggestion list
            redundant_logs: Optional list of RedundantLog objects
            title: Report title

        Returns:
            Markdown report as string
        """
        lines = []
        lines.append(f"# {title}\n")
        lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Summary statistics
        total_functions = len(coverage_reports)
        total_error_paths = sum(r.total_paths for r in coverage_reports.values())
        total_logged_paths = sum(r.logged_paths for r in coverage_reports.values())
        overall_coverage = (total_logged_paths / total_error_paths * 100) if total_error_paths > 0 else 0

        lines.append("## Summary\n")
        lines.append(f"- **Total functions analyzed**: {total_functions}")
        lines.append(f"- **Total error paths**: {total_error_paths}")
        lines.append(f"- **Logged paths**: {total_logged_paths}")
        lines.append(f"- **Overall coverage**: {overall_coverage:.1f}%\n")

        # Critical gaps (sorted by impact)
        critical_gaps = self._find_critical_gaps(coverage_reports)
        if critical_gaps:
            lines.append("## Critical Gaps (High Priority)\n")
            lines.append("Functions with lowest coverage and highest impact:\n")

            for func_name, report in critical_gaps[:10]:  # Top 10
                impact = self._calculate_impact(report)
                lines.append(f"### {func_name}")
                lines.append(f"- **Coverage**: {report.coverage_percentage:.0f}% "
                           f"({report.logged_paths}/{report.total_paths} logged)")
                lines.append(f"- **Impact**: {impact}")
                lines.append(f"- **File**: {report.file_path}")
                lines.append(f"- **Action**: Add {len(report.unlogged_paths)} error log(s)\n")

        # Detailed function reports
        if coverage_reports:
            lines.append("## Detailed Function Reports\n")

            # Sort by coverage percentage (ascending - worst first)
            sorted_reports = sorted(
                coverage_reports.items(),
                key=lambda x: x[1].coverage_percentage,
            )

            for func_name, report in sorted_reports:
                lines.append(f"### {func_name}")
                lines.append(f"**File**: {report.file_path}  \n")
                lines.append(f"**Coverage**: {report.coverage_percentage:.0f}% "
                           f"({report.logged_paths}/{report.total_paths} paths logged)\n")

                if report.unlogged_paths:
                    lines.append(f"**Unlogged paths** ({len(report.unlogged_paths)}):")
                    for gap in report.unlogged_paths:
                        error_info = f"{gap.path_type}"
                        if gap.path_type == 'return' and gap.error_code:
                            error_info += f" {gap.error_code}"
                        elif gap.path_type == 'goto' and gap.goto_label:
                            error_info += f" {gap.goto_label}"

                        lines.append(f"  - Line {gap.line_number}: {error_info}")

                    lines.append("")

        # Suggestions section
        if suggestions:
            lines.append("## Suggested Log Placements\n")

            for func_name, func_suggestions in suggestions.items():
                if not func_suggestions:
                    continue

                lines.append(f"### {func_name}\n")

                for i, suggestion in enumerate(func_suggestions, 1):
                    lines.append(f"{i}. Line {suggestion.line_number}")
                    lines.append(f"   - Add: `{suggestion.suggested_function}(..., "
                               f"\"{suggestion.suggested_message}\\n\")`")

                    if suggestion.code_snippet:
                        lines.append(f"   - Code: `{suggestion.code_snippet}`")

                    lines.append("")

        # Redundancy section
        if redundant_logs:
            lines.append("## Redundant Logs\n")

            for redundant in redundant_logs:
                lines.append(f"### \"{redundant.format_string}\"")
                lines.append(f"**Occurrences**: {len(redundant.occurrences)}  \n")
                lines.append(f"**Call chain depth**: {redundant.call_chain_depth}  \n")
                lines.append(f"**Recommendation**: {redundant.recommendation}\n")

                lines.append("**Locations**:")
                for func, line, log_func in redundant.occurrences[:10]:  # Show first 10
                    lines.append(f"  - {func}:{line} ({log_func})")

                if len(redundant.occurrences) > 10:
                    lines.append(f"  - ... and {len(redundant.occurrences) - 10} more")

                lines.append("")

        # Recommendations section
        lines.append("## Recommendations\n")

        recommendations = self._generate_recommendations(coverage_reports, redundant_logs)
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")

        return '\n'.join(lines)

    def generate_json_report(
        self,
        coverage_reports: Dict[str, CoverageReport],
        suggestions: Optional[Dict[str, List[LogSuggestion]]] = None,
        redundant_logs: Optional[List[RedundantLog]] = None,
    ) -> dict:
        """
        Generate a JSON coverage report.

        Args:
            coverage_reports: Dictionary of function → CoverageReport
            suggestions: Optional dictionary of function → LogSuggestion list
            redundant_logs: Optional list of RedundantLog objects

        Returns:
            Dictionary suitable for JSON serialization
        """
        import json

        report = {
            'generated': datetime.now().isoformat(),
            'summary': {
                'total_functions': len(coverage_reports),
                'total_error_paths': sum(r.total_paths for r in coverage_reports.values()),
                'logged_paths': sum(r.logged_paths for r in coverage_reports.values()),
                'overall_coverage': (sum(r.logged_paths for r in coverage_reports.values()) /
                                    sum(r.total_paths for r in coverage_reports.values()) * 100)
                                   if coverage_reports else 0,
            },
            'functions': {},
        }

        # Add function reports
        for func_name, cov_report in coverage_reports.items():
            report['functions'][func_name] = cov_report.to_dict()

        # Add suggestions
        if suggestions:
            report['suggestions'] = {
                func_name: [s.to_dict() for s in suggs]
                for func_name, suggs in suggestions.items()
                if suggs
            }

        # Add redundant logs
        if redundant_logs:
            report['redundant_logs'] = [rl.to_dict() for rl in redundant_logs]

        # Add recommendations
        report['recommendations'] = self._generate_recommendations(
            coverage_reports,
            redundant_logs,
        )

        return report

    def save_report(self, report: str, output_path: str):
        """
        Save report to file.

        Args:
            report: Report content (string)
            output_path: Path to save the report
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(report, encoding='utf-8')
        logger.info(f"Report saved to {output_path}")

    def _find_critical_gaps(
        self,
        coverage_reports: Dict[str, CoverageReport],
    ) -> List[tuple]:
        """
        Find functions with critical coverage gaps.

        Args:
            coverage_reports: Dictionary of function → CoverageReport

        Returns:
            List of (function_name, report) tuples, sorted by severity
        """
        # Filter to functions with unlogged paths
        gaps = [
            (func_name, report)
            for func_name, report in coverage_reports.items()
            if report.unlogged_paths
        ]

        # Sort by: coverage percentage (lower first), then total paths (higher first)
        gaps.sort(key=lambda x: (x[1].coverage_percentage, -x[1].total_paths))

        return gaps

    def _calculate_impact(self, report: CoverageReport) -> str:
        """
        Calculate impact level of coverage gaps.

        Args:
            report: CoverageReport object

        Returns:
            Impact level string (HIGH, MEDIUM, LOW)
        """
        # Simple heuristic based on number of error paths
        if report.total_paths >= 10:
            return "HIGH"
        elif report.total_paths >= 5:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_recommendations(
        self,
        coverage_reports: Dict[str, CoverageReport],
        redundant_logs: Optional[List[RedundantLog]] = None,
    ) -> List[str]:
        """
        Generate actionable recommendations.

        Args:
            coverage_reports: Dictionary of function → CoverageReport
            redundant_logs: Optional list of RedundantLog objects

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Find critical gaps
        critical_gaps = self._find_critical_gaps(coverage_reports)

        if critical_gaps:
            top_gaps = critical_gaps[:5]
            for func_name, report in top_gaps:
                recommendations.append(
                    f"Add error logs to {func_name} (currently {report.coverage_percentage:.0f}% coverage, "
                    f"{len(report.unlogged_paths)} gaps)"
                )

        # Redundancy recommendations
        if redundant_logs:
            for redundant in redundant_logs[:3]:
                recommendations.append(redundant.recommendation)

        # General recommendations
        if not recommendations:
            recommendations.append("Excellent logging coverage! No immediate actions needed.")
        else:
            recommendations.append("Review and address high-priority gaps first.")
            recommendations.append("Aim for >80% coverage on functions called from syscalls.")

        return recommendations
