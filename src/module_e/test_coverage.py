"""
Module E: CVE Test Coverage Analyzer
Analyzes test coverage for CVEs using existing Module C infrastructure.
"""

import logging
from typing import List, Dict, Any, Optional

from src.module_b.graph_store import Neo4jGraphStore

logger = logging.getLogger(__name__)


class CVETestCoverage:
    """
    Analyze test coverage for CVE-affected functions.
    """

    def __init__(self, graph_store: Neo4jGraphStore):
        """
        Initialize the test coverage analyzer.

        Args:
            graph_store: Neo4jGraphStore instance
        """
        self.graph_store = graph_store

    def analyze_cve_test_coverage(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """
        Analyze test coverage for a CVE.

        Args:
            cve_id: CVE identifier

        Returns:
            Test coverage analysis or None
        """
        logger.info(f"Analyzing test coverage for CVE: {cve_id}")

        # Get CVE info
        cve_info = self._get_cve_info(cve_id)
        if not cve_info:
            logger.error(f"CVE {cve_id} not found")
            return None

        affected_function = cve_info.get('affected_function', '')

        # Get direct test coverage
        direct_tests = self._get_direct_tests(affected_function)

        # Get caller test coverage
        caller_tests = self._get_caller_tests(affected_function, max_depth=5)

        # Get callees test coverage
        callee_tests = self._get_callee_tests(affected_function, max_depth=3)

        # Compute coverage statistics
        total_tests = len(direct_tests) + len(caller_tests)
        coverage_percentage = self._compute_coverage_percentage(
            affected_function, direct_tests, caller_tests
        )

        # Identify test gaps
        test_gaps = self._identify_test_gaps(
            affected_function, direct_tests, caller_tests
        )

        analysis = {
            'cve_id': cve_id,
            'affected_function': affected_function,
            'direct_tests': direct_tests,
            'direct_test_count': len(direct_tests),
            'caller_tests': caller_tests,
            'caller_test_count': len(caller_tests),
            'callee_tests': callee_tests,
            'callee_test_count': len(callee_tests),
            'total_test_count': total_tests,
            'coverage_percentage': coverage_percentage,
            'test_gaps': test_gaps,
            'has_coverage': len(direct_tests) > 0
        }

        logger.info(f"Test coverage analysis complete: {total_tests} tests, "
                   f"{coverage_percentage}% coverage")

        return analysis

    def _get_cve_info(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """Get CVE information."""
        query = """
        MATCH (c:CVE {id: $cve_id})
        RETURN c
        """

        results = self.graph_store.execute_query(query, {'cve_id': cve_id})

        if results:
            return results[0]['c']
        return None

    def _get_direct_tests(self, function_name: str) -> List[Dict[str, Any]]:
        """Get tests directly covering the function."""
        query = """
        MATCH (f:Function {name: $function_name})
        MATCH (test:TestCase)-[:COVERS]->(f)
        RETURN test.id as test_id,
               test.name as test_name,
               test.file_path as test_file,
               test.test_suite as test_suite
        ORDER BY test_name
        """

        results = self.graph_store.execute_query(
            query,
            {'function_name': function_name}
        )

        return results

    def _get_caller_tests(self, function_name: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """Get tests covering callers of the function."""
        query = f"""
        MATCH (target:Function {{name: $function_name}})
        MATCH path = (caller:Function)-[:CALLS*1..{max_depth}]->(target)
        WHERE caller <> target
        MATCH (test:TestCase)-[:COVERS]->(caller)
        RETURN DISTINCT
            test.id as test_id,
            test.name as test_name,
            test.file_path as test_file,
            caller.name as caller_name,
            length(path) as indirection_level
        ORDER BY test_name
        """

        results = self.graph_store.execute_query(
            query,
            {'function_name': function_name}
        )

        return results

    def _get_callee_tests(self, function_name: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Get tests covering functions called by the target function."""
        query = f"""
        MATCH (source:Function {{name: $function_name}})
        MATCH path = (source)-[:CALLS*1..{max_depth}]->(callee:Function)
        WHERE source <> callee
        MATCH (test:TestCase)-[:COVERS]->(callee)
        RETURN DISTINCT
            test.id as test_id,
            test.name as test_name,
            test.file_path as test_file,
            callee.name as callee_name,
            length(path) as depth
        ORDER BY test_name
        """

        results = self.graph_store.execute_query(
            query,
            {'function_name': function_name}
        )

        return results

    def _compute_coverage_percentage(self, function_name: str,
                                    direct_tests: List[Dict[str, Any]],
                                    caller_tests: List[Dict[str, Any]]) -> float:
        """
        Compute test coverage percentage.

        This is a heuristic based on:
        - Direct tests (weighted 100%)
        - Caller tests (weighted 50% - indirect coverage)
        """
        # Get total callers
        caller_query = """
        MATCH (target:Function {name: $function_name})
        MATCH (caller:Function)-[:CALLS]->(target)
        RETURN count(DISTINCT caller) as total_callers
        """

        results = self.graph_store.execute_query(
            caller_query,
            {'function_name': function_name}
        )

        total_callers = results[0]['total_callers'] if results else 0

        if total_callers == 0:
            return 100.0 if len(direct_tests) > 0 else 0.0

        # Weighted coverage calculation
        direct_coverage = len(direct_tests) * 100
        caller_coverage = len(caller_tests) * 50

        # Normalize by number of callers + function itself
        max_coverage = (total_callers + 1) * 100

        actual_coverage = direct_coverage + caller_coverage

        return min(100.0, (actual_coverage / max_coverage) * 100)

    def _identify_test_gaps(self, function_name: str,
                           direct_tests: List[Dict[str, Any]],
                           caller_tests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify gaps in test coverage.

        Returns list of untested callers and suggestions.
        """
        gaps = []

        # Get callers without tests
        query = """
        MATCH (target:Function {name: $function_name})
        MATCH (caller:Function)-[:CALLS]->(target)
        WHERE NOT EXISTS {
            MATCH (test:TestCase)-[:COVERS]->(caller)
        }
        RETURN caller.id as caller_id,
               caller.name as caller_name,
               caller.file_path as caller_file
        ORDER BY caller_name
        LIMIT 20
        """

        results = self.graph_store.execute_query(
            query,
            {'function_name': function_name}
        )

        for result in results:
            gaps.append({
                'type': 'untested_caller',
                'function': result['caller_name'],
                'file': result['caller_file'],
                'suggestion': f"Add KUnit test for {result['caller_name']}"
            })

        # Suggest direct test if none exists
        if not direct_tests:
            gaps.append({
                'type': 'missing_direct_test',
                'function': function_name,
                'suggestion': f"Add KUnit test directly for {function_name}"
            })

        return gaps

    def format_coverage_report(self, analysis: Dict[str, Any]) -> str:
        """
        Format test coverage analysis as a report.

        Args:
            analysis: Test coverage analysis

        Returns:
            Formatted report
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"TEST COVERAGE ANALYSIS: {analysis['cve_id']}")
        lines.append("=" * 80)
        lines.append(f"Affected Function: {analysis['affected_function']}")
        lines.append("")

        # Coverage summary
        lines.append("COVERAGE SUMMARY")
        lines.append("-" * 80)
        lines.append(f"  Direct tests: {analysis['direct_test_count']}")
        lines.append(f"  Caller tests: {analysis['caller_test_count']}")
        lines.append(f"  Callee tests: {analysis['callee_test_count']}")
        lines.append(f"  Total tests: {analysis['total_test_count']}")
        lines.append(f"  Coverage: {analysis['coverage_percentage']:.1f}%")
        lines.append("")

        # Direct tests
        if analysis['direct_tests']:
            lines.append("DIRECT TESTS")
            lines.append("-" * 80)
            for test in analysis['direct_tests'][:10]:
                lines.append(f"  ✓ {test['test_name']} ({test.get('test_suite', 'N/A')})")
            if len(analysis['direct_tests']) > 10:
                lines.append(f"  ... and {len(analysis['direct_tests']) - 10} more")
            lines.append("")

        # Caller tests
        if analysis['caller_tests']:
            lines.append("CALLER TESTS (indirect coverage)")
            lines.append("-" * 80)
            for test in analysis['caller_tests'][:10]:
                lines.append(f"  ✓ {test['test_name']} → {test['caller_name']}")
            if len(analysis['caller_tests']) > 10:
                lines.append(f"  ... and {len(analysis['caller_tests']) - 10} more")
            lines.append("")

        # Test gaps
        if analysis['test_gaps']:
            lines.append("TEST GAPS")
            lines.append("-" * 80)
            for gap in analysis['test_gaps'][:10]:
                lines.append(f"  ⚠️  {gap['suggestion']}")
            if len(analysis['test_gaps']) > 10:
                lines.append(f"  ... and {len(analysis['test_gaps']) - 10} more")
            lines.append("")

        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)

        if analysis['direct_test_count'] == 0:
            lines.append("  1. Add KUnit test for vulnerable function")
            lines.append("  2. Test syscall entry points with malicious input")

        if analysis['coverage_percentage'] < 50:
            lines.append("  3. Increase test coverage for caller functions")

        lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)


if __name__ == "__main__":
    import sys
    import os

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python test_coverage.py <cve_id>")
        print("Example: python test_coverage.py CVE-2024-1234")
        sys.exit(1)

    cve_id = sys.argv[1]

    from src.config import Config

    config = Config.from_defaults()

    with Neo4jGraphStore(
        config.neo4j.url,
        config.neo4j.user,
        config.neo4j.password
    ) as store:
        analyzer = CVETestCoverage(store)

        # Analyze test coverage
        analysis = analyzer.analyze_cve_test_coverage(cve_id)

        if analysis:
            report = analyzer.format_coverage_report(analysis)
            print(report)
        else:
            print(f"Failed to analyze test coverage for CVE {cve_id}")
            sys.exit(1)
