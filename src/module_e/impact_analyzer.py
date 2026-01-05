"""
Module E: CVE Impact Analyzer
Analyzes the impact of CVEs using reachability analysis from the existing callgraph.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from src.module_b.graph_store import Neo4jGraphStore
from src.analysis.impact_analyzer import ImpactAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class CVEImpactResult:
    """
    Results of CVE impact analysis.

    Attributes:
        cve_id: CVE identifier
        affected_function: Vulnerable function
        file_path: Path to vulnerable file
        severity: Severity level
        cvss_score: CVSS score

        # Reachability analysis
        syscall_callers: Syscalls that can reach the vulnerable function
        all_callers: All functions that call the vulnerable function
        caller_count: Total number of callers

        # Downstream impact
        downstream_callees: Functions called by the vulnerable function
        downstream_count: Number of downstream functions

        # Test coverage
        test_coverage: Tests covering the vulnerable function
        caller_tests: Tests covering the callers
        has_test_coverage: Whether the function has test coverage

        # Risk assessment
        user_accessible: Whether accessible from user input
        risk_level: Computed risk level
    """
    cve_id: str
    affected_function: str
    file_path: str
    severity: str
    cvss_score: float

    syscall_callers: List[Dict[str, Any]]
    all_callers: List[Dict[str, Any]]
    caller_count: int

    downstream_callees: List[Dict[str, Any]]
    downstream_count: int

    test_coverage: List[Dict[str, Any]]
    caller_tests: List[Dict[str, Any]]
    has_test_coverage: bool

    user_accessible: bool
    risk_level: str

    # Reachable paths
    reachable_paths: List[Dict[str, Any]]


class CVEImpactAnalyzer:
    """
    Analyze CVE impact using existing callgraph infrastructure.
    """

    def __init__(self, graph_store: Neo4jGraphStore):
        """
        Initialize the CVE impact analyzer.

        Args:
            graph_store: Neo4jGraphStore instance
        """
        self.graph_store = graph_store
        self.impact_analyzer = ImpactAnalyzer(graph_store)

    def analyze_cve_impact(self, cve_id: str,
                          max_depth: int = 5,
                          limit: int = 100) -> Optional[CVEImpactResult]:
        """
        Comprehensive CVE impact analysis.

        Args:
            cve_id: CVE identifier
            max_depth: Maximum depth for call chain traversal
            limit: Maximum number of results per category

        Returns:
            CVEImpactResult or None if CVE not found
        """
        logger.info(f"Analyzing impact for CVE: {cve_id}")

        # Get CVE information
        cve_info = self._get_cve_info(cve_id)
        if not cve_info:
            logger.error(f"CVE {cve_id} not found in database")
            return None

        affected_function = cve_info['affected_function']

        # Use existing impact analyzer
        impact = self.impact_analyzer.analyze_function_impact(
            affected_function,
            max_depth=max_depth,
            limit=limit
        )

        if not impact:
            logger.warning(f"Function '{affected_function}' not found in callgraph")
            # Still return basic CVE info even if function not in callgraph
            return CVEImpactResult(
                cve_id=cve_id,
                affected_function=affected_function,
                file_path=cve_info.get('file_path', ''),
                severity=cve_info.get('severity', 'MEDIUM'),
                cvss_score=cve_info.get('cvss_score', 0.0),
                syscall_callers=[],
                all_callers=[],
                caller_count=0,
                downstream_callees=[],
                downstream_count=0,
                test_coverage=[],
                caller_tests=[],
                has_test_coverage=False,
                user_accessible=False,
                risk_level='UNKNOWN',
                reachable_paths=[]
            )

        # Extract syscall callers
        syscall_callers = self._get_syscall_callers(impact.indirect_callers,
                                                    impact.direct_callers)

        # Get downstream callees
        downstream_callees = impact.direct_callees + impact.indirect_callees

        # Get test coverage
        caller_tests = self._get_caller_tests(affected_function, max_depth)

        # Determine user accessibility
        user_accessible = len(syscall_callers) > 0

        # Compute risk level
        risk_level = self._compute_risk_level(
            cve_info.get('severity', 'MEDIUM'),
            cve_info.get('cvss_score', 0.0),
            user_accessible,
            impact.stats['direct_test_count'] + impact.stats['indirect_test_count'],
            impact.stats['direct_caller_count'] + impact.stats['indirect_caller_count']
        )

        # Build reachable paths
        reachable_paths = self._build_reachable_paths(syscall_callers)

        result = CVEImpactResult(
            cve_id=cve_id,
            affected_function=affected_function,
            file_path=impact.target_file,
            severity=cve_info.get('severity', 'MEDIUM'),
            cvss_score=cve_info.get('cvss_score', 0.0),
            syscall_callers=syscall_callers,
            all_callers=impact.direct_callers + impact.indirect_callers,
            caller_count=impact.stats['direct_caller_count'] + impact.stats['indirect_caller_count'],
            downstream_callees=downstream_callees,
            downstream_count=len(downstream_callees),
            test_coverage=impact.direct_tests,
            caller_tests=caller_tests,
            has_test_coverage=(impact.stats['direct_test_count'] > 0),
            user_accessible=user_accessible,
            risk_level=risk_level,
            reachable_paths=reachable_paths
        )

        logger.info(f"CVE impact analysis complete: risk={risk_level}, "
                   f"user_accessible={user_accessible}, callers={result.caller_count}")

        return result

    def _get_cve_info(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """Get CVE information from database."""
        query = """
        MATCH (c:CVE {id: $cve_id})
        RETURN c
        """

        results = self.graph_store.execute_query(query, {'cve_id': cve_id})

        if results:
            return results[0]['c']
        return None

    def _get_syscall_callers(self, indirect_callers: List[Dict[str, Any]],
                            direct_callers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter for syscall callers."""
        syscalls = []

        # Check direct callers
        for caller in direct_callers:
            if caller.get('name', '').startswith('sys_'):
                syscalls.append({
                    **caller,
                    'distance': 1
                })

        # Check indirect callers
        for caller in indirect_callers:
            if caller.get('name', '').startswith('sys_'):
                syscalls.append(caller)

        return syscalls

    def _get_caller_tests(self, function_name: str, max_depth: int) -> List[Dict[str, Any]]:
        """Get tests covering callers of the function."""
        query = f"""
        MATCH (target:Function {{name: $function_name}})
        MATCH path = (caller:Function)-[:CALLS*1..{max_depth}]->(target)
        MATCH (test:TestCase)-[:COVERS]->(caller)
        RETURN DISTINCT
            test.id as test_id,
            test.name as test_name,
            test.file_path as test_file,
            caller.name as via_function,
            length(path) as indirection_level
        ORDER BY test_name
        LIMIT 100
        """

        results = self.graph_store.execute_query(
            query,
            {'function_name': function_name}
        )

        return results

    def _compute_risk_level(self, severity: str, cvss_score: float,
                           user_accessible: bool, test_count: int,
                           caller_count: int) -> str:
        """
        Compute risk level based on multiple factors.

        Args:
            severity: CVE severity
            cvss_score: CVSS score
            user_accessible: Whether accessible from syscalls
            test_count: Number of tests
            caller_count: Number of callers

        Returns:
            Risk level string
        """
        # Start with CVSS-based severity
        if cvss_score >= 9.0 or severity == "CRITICAL":
            base_risk = "CRITICAL"
        elif cvss_score >= 7.0 or severity == "HIGH":
            base_risk = "HIGH"
        elif cvss_score >= 4.0 or severity == "MEDIUM":
            base_risk = "MEDIUM"
        else:
            base_risk = "LOW"

        # Adjust based on user accessibility
        if user_accessible:
            # Escalate risk if user-accessible
            if base_risk == "MEDIUM":
                base_risk = "HIGH"
            elif base_risk == "LOW":
                base_risk = "MEDIUM"

        # Adjust based on test coverage
        if test_count == 0 and caller_count > 5:
            # No tests and widely used = high risk
            if base_risk in ["MEDIUM", "LOW"]:
                base_risk = "HIGH"

        return base_risk

    def _build_reachable_paths(self, syscall_callers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build reachable path information."""
        paths = []

        for syscall in syscall_callers:
            paths.append({
                'syscall': syscall['name'],
                'distance': syscall.get('distance', 1),
                'file': syscall.get('file_path', ''),
                'reachable': True
            })

        return paths

    def format_impact_report(self, impact: CVEImpactResult) -> str:
        """
        Format CVE impact analysis as a human-readable report.

        Args:
            impact: CVEImpactResult object

        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"CVE IMPACT ANALYSIS: {impact.cve_id}")
        lines.append("=" * 80)
        lines.append(f"Severity: {impact.severity} (CVSS {impact.cvss_score})")
        lines.append("")

        # Affected function
        lines.append("AFFECTED FUNCTION")
        lines.append("-" * 80)
        lines.append(f"  {impact.affected_function} ({impact.file_path})")
        lines.append("")

        # Reachability from syscalls
        lines.append("REACHABLE FROM SYSCALLS")
        lines.append("-" * 80)
        if impact.syscall_callers:
            for syscall in impact.syscall_callers:
                path = syscall.get('call_chain', [])
                path_str = " → ".join(path) if path else syscall['name']
                lines.append(f"  ✓ {syscall['name']} ({syscall.get('distance', 1)} hops)")
                lines.append(f"    Path: {path_str}")
            lines.append(f"\n  User-accessible: YES")
        else:
            lines.append(f"  ✗ No direct syscall paths found")
            lines.append(f"  User-accessible: NO")
        lines.append("")

        # Downstream impact
        lines.append(f"DOWNSTREAM IMPACT ({impact.downstream_count} functions)")
        lines.append("-" * 80)
        if impact.downstream_callees:
            for i, callee in enumerate(impact.downstream_callees[:10]):
                lines.append(f"  {i+1}. {callee['name']} ({callee.get('file_path', '')})")
            if len(impact.downstream_callees) > 10:
                lines.append(f"  ... and {len(impact.downstream_callees) - 10} more")
        else:
            lines.append(f"  No downstream functions")
        lines.append("")

        # Test coverage
        lines.append("TEST COVERAGE")
        lines.append("-" * 80)
        if impact.test_coverage:
            lines.append(f"  Direct tests: {len(impact.test_coverage)}")
            for test in impact.test_coverage[:5]:
                lines.append(f"    - {test['name']}")
        else:
            lines.append(f"  ⚠️  NO direct test coverage")

        if impact.caller_tests:
            lines.append(f"  Caller tests: {len(impact.caller_tests)}")
            for test in impact.caller_tests[:5]:
                lines.append(f"    - {test['test_name']} → {test['via_function']}")
        else:
            lines.append(f"  ⚠️  NO caller test coverage")
        lines.append("")

        # Risk assessment
        lines.append("RISK ASSESSMENT")
        lines.append("-" * 80)
        lines.append(f"  Risk Level: {impact.risk_level}")
        lines.append(f"  User-accessible: {('YES - ' + str(len(impact.syscall_callers)) + ' syscalls') if impact.syscall_callers else 'NO'}")
        lines.append(f"  Test coverage: {('POOR' if not impact.has_test_coverage else 'GOOD')}")
        lines.append(f"  Downstream blast radius: {'LARGE (' + str(impact.downstream_count) + ' functions)' if impact.downstream_count > 10 else 'SMALL'}")
        lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def get_all_cves(self) -> List[Dict[str, Any]]:
        """Get all CVEs from database."""
        query = """
        MATCH (c:CVE)
        RETURN c
        ORDER BY c.cvss_score DESC
        """

        results = self.graph_store.execute_query(query, {})

        return [r['c'] for r in results]

    def get_cves_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """Get CVEs by severity level."""
        query = """
        MATCH (c:CVE {severity: $severity})
        RETURN c
        ORDER BY c.cvss_score DESC
        """

        results = self.graph_store.execute_query(query, {'severity': severity})

        return [r['c'] for r in results]


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python impact_analyzer.py <cve_id>")
        print("Example: python impact_analyzer.py CVE-2024-1234")
        sys.exit(1)

    cve_id = sys.argv[1]

    import os
    from src.config import Config

    config = Config.from_defaults()

    with Neo4jGraphStore(
        config.neo4j.url,
        config.neo4j.user,
        config.neo4j.password
    ) as store:
        analyzer = CVEImpactAnalyzer(store)

        # Analyze CVE impact
        impact = analyzer.analyze_cve_impact(cve_id)

        if impact:
            # Print report
            report = analyzer.format_impact_report(impact)
            print(report)
        else:
            print(f"CVE '{cve_id}' not found in database")
            sys.exit(1)
