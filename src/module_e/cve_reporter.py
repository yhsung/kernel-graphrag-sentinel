"""
Module E: CVE Reporter
Generates markdown reports for CVE impact analysis.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from src.module_b.graph_store import Neo4jGraphStore
from src.module_e.impact_analyzer import CVEImpactAnalyzer, CVEImpactResult
from src.module_e.version_checker import VersionChecker, VersionCheckResult
from src.module_e.test_coverage import CVETestCoverage

logger = logging.getLogger(__name__)


class CVEReporter:
    """
    Generate comprehensive CVE impact reports.
    """

    def __init__(self, graph_store: Neo4jGraphStore, kernel_root: str):
        """
        Initialize the CVE reporter.

        Args:
            graph_store: Neo4jGraphStore instance
            kernel_root: Path to kernel source tree
        """
        self.graph_store = graph_store
        self.kernel_root = kernel_root

        # Initialize analyzers
        self.impact_analyzer = CVEImpactAnalyzer(graph_store)
        self.version_checker = VersionChecker(graph_store, kernel_root)
        self.test_coverage = CVETestCoverage(graph_store)

    def generate_cve_report(self, cve_id: str,
                           kernel_version: Optional[str] = None) -> Optional[str]:
        """
        Generate a comprehensive CVE impact report.

        Args:
            cve_id: CVE identifier
            kernel_version: Optional kernel version to check

        Returns:
            Markdown report or None
        """
        logger.info(f"Generating report for CVE: {cve_id}")

        # Analyze impact
        impact = self.impact_analyzer.analyze_cve_impact(cve_id)
        if not impact:
            logger.error(f"Failed to analyze impact for {cve_id}")
            return None

        # Analyze test coverage
        coverage = self.test_coverage.analyze_cve_test_coverage(cve_id)

        # Check version compatibility if requested
        version_check = None
        if kernel_version:
            version_check = self.version_checker.check_cve_version(cve_id, kernel_version)

        # Generate markdown report
        report = self._format_markdown_report(impact, coverage, version_check)

        return report

    def generate_backport_checklist(self, cve_ids: List[str],
                                   kernel_version: str,
                                   output_path: Optional[str] = None) -> str:
        """
        Generate a backport checklist for CVEs.

        Args:
            cve_ids: List of CVE identifiers
            kernel_version: Target kernel version
            output_path: Optional path to save report

        Returns:
            Markdown report
        """
        logger.info(f"Generating backport checklist for {len(cve_ids)} CVEs")

        lines = []
        lines.append(f"# CVE Backport Checklist: Kernel {kernel_version}")
        lines.append("")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Check each CVE
        affected_cves = []
        for cve_id in cve_ids:
            result = self.version_checker.check_cve_version(cve_id, kernel_version)
            if result and result.affected:
                affected_cves.append(result)

        lines.append(f"## Summary")
        lines.append("")
        lines.append(f"- Total CVEs checked: {len(cve_ids)}")
        lines.append(f"- CVEs affecting kernel {kernel_version}: {len(affected_cves)}")
        lines.append(f"- CVEs already fixed: {len(cve_ids) - len(affected_cves)}")
        lines.append("")

        if not affected_cves:
            lines.append("✓ **No CVEs to backport** - All CVEs are already fixed or not applicable.")
            return "\n".join(lines)

        # Generate checklist
        lines.append(f"## Backport Checklist")
        lines.append("")

        for i, result in enumerate(affected_cves, 1):
            lines.append(f"### {i}. {result.cve_id}")
            lines.append("")
            lines.append(f"- **Status**: ⚠️ AFFECTS kernel {kernel_version}")
            lines.append(f"- **Function**: {result.reason}")
            lines.append(f"- **Can backport**: {'Yes' if result.can_backport else 'No'}")
            lines.append("")
            lines.append(f"**Tasks:**")
            lines.append(f"- [ ] Review patch for {result.cve_id}")
            lines.append(f"- [ ] Apply patch to {kernel_version} branch")
            lines.append(f"- [ ] Test compilation")
            lines.append(f"- [ ] Run KUnit tests")
            lines.append(f"- [ ] Test with syscall fuzzing")
            lines.append("")

        # Add testing recommendations
        lines.append(f"## Testing Recommendations")
        lines.append("")
        lines.append("For each backported CVE:")
        lines.append("1. **Compilation**: Ensure kernel compiles without errors")
        lines.append("2. **KUnit tests**: Run `make run_tests` for affected subsystem")
        lines.append("3. **Syscall tests**: Test syscalls that reach vulnerable code")
        lines.append("4. **Fuzzing**: Run syzkaller on affected paths")
        lines.append("")

        report = "\n".join(lines)

        # Save to file if requested
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
            logger.info(f"Backport checklist saved to {output_path}")

        return report

    def generate_subsystem_report(self, subsystem: str,
                                 severity_filter: Optional[List[str]] = None) -> str:
        """
        Generate a report for all CVEs in a subsystem.

        Args:
            subsystem: Subsystem path (e.g., "fs/ext4")
            severity_filter: Optional list of severities to include

        Returns:
            Markdown report
        """
        logger.info(f"Generating subsystem report for: {subsystem}")

        # Get all CVEs
        all_cves = self.impact_analyzer.get_all_cves()

        # Filter by subsystem (if function file_path contains subsystem)
        filtered_cves = []
        for cve in all_cves:
            file_path = cve.get('file_path', '')
            if subsystem in file_path:
                # Filter by severity if requested
                if severity_filter and cve.get('severity') not in severity_filter:
                    continue
                filtered_cves.append(cve)

        lines = []
        lines.append(f"# CVE Impact Report: {subsystem}")
        lines.append("")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total CVEs analyzed: {len(filtered_cves)}")
        lines.append("")

        # Group by severity
        critical_cves = [c for c in filtered_cves if c.get('severity') == 'CRITICAL']
        high_cves = [c for c in filtered_cves if c.get('severity') == 'HIGH']
        medium_cves = [c for c in filtered_cves if c.get('severity') == 'MEDIUM']

        # Critical CVEs
        if critical_cves:
            lines.append("## Critical CVEs (Affecting Your Kernel)")
            lines.append("")

            for cve in critical_cves:
                lines.append(f"### {cve['id']} - {cve.get('vulnerability_type', 'Unknown').replace('_', ' ').title()}")
                lines.append("")
                lines.append(f"- **Severity**: CRITICAL (CVSS {cve.get('cvss_score', 0)})")
                lines.append(f"- **Function**: {cve.get('affected_function', 'Unknown')}")
                lines.append(f"- **File**: {cve.get('file_path', 'Unknown')}")
                lines.append(f"- **Description**: {cve.get('description', 'No description')[:200]}...")
                lines.append("")

        # High CVEs
        if high_cves:
            lines.append("## High CVEs")
            lines.append("")

            for cve in high_cves:
                lines.append(f"### {cve['id']}")
                lines.append("")
                lines.append(f"- **Severity**: HIGH (CVSS {cve.get('cvss_score', 0)})")
                lines.append(f"- **Function**: {cve.get('affected_function', 'Unknown')}")
                lines.append(f"- **File**: {cve.get('file_path', 'Unknown')}")
                lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Critical CVEs**: {len(critical_cves)}")
        lines.append(f"- **High CVEs**: {len(high_cves)}")
        lines.append(f"- **Medium CVEs**: {len(medium_cves)}")
        lines.append(f"- **Total CVEs**: {len(filtered_cves)}")
        lines.append("")

        return "\n".join(lines)

    def _format_markdown_report(self, impact: CVEImpactResult,
                               coverage: Optional[Dict[str, Any]] = None,
                               version_check: Optional[VersionCheckResult] = None) -> str:
        """Format a comprehensive markdown report."""

        lines = []
        lines.append(f"# CVE Impact Report: {impact.cve_id}")
        lines.append("")

        # Executive summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"- **Function**: {impact.affected_function}")
        lines.append(f"- **File**: {impact.file_path}")
        lines.append(f"- **Severity**: {impact.severity} (CVSS {impact.cvss_score})")
        lines.append(f"- **Risk Level**: {impact.risk_level}")
        lines.append(f"- **User-accessible**: {'YES' if impact.user_accessible else 'NO'}")
        lines.append("")

        # Affected paths
        lines.append("## Affected Paths")
        lines.append("")

        if impact.reachable_paths:
            for path in impact.reachable_paths:
                syscall = path['syscall']
                distance = path['distance']
                lines.append(f"- **{syscall}** ({distance} hop{'s' if distance > 1 else ''})")
                lines.append("")
        else:
            lines.append("No direct syscall paths found")
            lines.append("")

        # Downstream impact
        lines.append(f"## Downstream Impact ({impact.downstream_count} functions)")
        lines.append("")

        if impact.downstream_callees:
            lines.append("| Function | File |")
            lines.append("|----------|------|")
            for callee in impact.downstream_callees[:20]:
                file_short = Path(callee.get('file_path', '')).name
                lines.append(f"| {callee['name']} | {file_short} |")

            if len(impact.downstream_callees) > 20:
                lines.append(f"| ... and {len(impact.downstream_callees) - 20} more | |")
            lines.append("")

        # Test coverage
        if coverage:
            lines.append("## Test Coverage")
            lines.append("")
            lines.append(f"- **Direct tests**: {coverage['direct_test_count']}")
            lines.append(f"- **Caller tests**: {coverage['caller_test_count']}")
            lines.append(f"- **Coverage**: {coverage['coverage_percentage']:.1f}%")
            lines.append("")

            if coverage['test_gaps']:
                lines.append("**Test Gaps:**")
                lines.append("")
                for gap in coverage['test_gaps'][:5]:
                    lines.append(f"- ⚠️  {gap['suggestion']}")
                lines.append("")

        # Version check
        if version_check:
            lines.append("## Version Check")
            lines.append("")
            status = "✓ AFFECTS" if version_check.affected else "✗ NOT AFFECTED"
            lines.append(f"- **Status**: {status}")
            lines.append(f"- **Reason**: {version_check.reason}")
            lines.append("")

        # Recommendations
        lines.append("## Recommendations")
        lines.append("")

        if impact.risk_level in ['HIGH', 'CRITICAL']:
            lines.append("### Immediate Actions Required")
            lines.append("")
            lines.append("1. **Review the vulnerability**")
            lines.append("   - Understand the vulnerability type")
            lines.append("   - Identify affected code paths")
            lines.append("")

            lines.append("2. **Apply patch**")
            if version_check and version_check.can_backport:
                lines.append(f"   - Patch can be backported to your kernel version")
            else:
                lines.append(f"   - Check if patch exists for your kernel version")
            lines.append("")

            lines.append("3. **Test thoroughly**")
            lines.append("   - Test syscall entry points with malicious input")
            lines.append("   - Run KUnit tests for affected subsystem")
            lines.append("   - Consider fuzzing with syzkaller")
            lines.append("")

        if not impact.has_test_coverage:
            lines.append("### Testing Recommendations")
            lines.append("")
            lines.append("⚠️ **No test coverage detected**")
            lines.append("")
            lines.append("Recommended tests:")
            lines.append(f"- Add KUnit test for {impact.affected_function}")
            if impact.syscall_callers:
                lines.append("- Test syscall entry points:")
                for syscall in impact.syscall_callers[:3]:
                    lines.append(f"  - {syscall['name']}")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(f"*Generated by Kernel-GraphRAG Sentinel on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)


if __name__ == "__main__":
    import sys
    import os

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python cve_reporter.py <cve_id> [kernel_version] [output_file]")
        print("Example: python cve_reporter.py CVE-2024-1234 5.15 report.md")
        sys.exit(1)

    cve_id = sys.argv[1]
    kernel_version = sys.argv[2] if len(sys.argv) > 2 else None
    output_file = sys.argv[3] if len(sys.argv) > 3 else None

    kernel_root = os.getenv('KERNEL_ROOT', '/path/to/linux')

    from src.config import Config

    config = Config.from_defaults(kernel_root=kernel_root)

    with Neo4jGraphStore(
        config.neo4j.url,
        config.neo4j.user,
        config.neo4j.password
    ) as store:
        reporter = CVEReporter(store, kernel_root)

        # Generate report
        report = reporter.generate_cve_report(cve_id, kernel_version)

        if report:
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(report)
                print(f"Report saved to {output_file}")
            else:
                print(report)
        else:
            print(f"Failed to generate report for CVE {cve_id}")
            sys.exit(1)
