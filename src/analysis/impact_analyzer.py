"""
Analysis Module: Impact Analyzer
Analyzes the impact of code changes using graph traversal queries.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.module_b.graph_store import Neo4jGraphStore
from src.analysis import queries

logger = logging.getLogger(__name__)


@dataclass
class ImpactResult:
    """Results of impact analysis for a function."""
    target_function: str
    target_file: str

    # Direct impacts
    direct_callers: List[Dict[str, Any]]
    direct_callees: List[Dict[str, Any]]

    # Indirect impacts (multi-hop)
    indirect_callers: List[Dict[str, Any]]
    indirect_callees: List[Dict[str, Any]]

    # Test coverage
    direct_tests: List[Dict[str, Any]]
    indirect_tests: List[Dict[str, Any]]

    # Call chains
    call_chains: List[Dict[str, Any]]

    # Statistics
    stats: Dict[str, int]


class ImpactAnalyzer:
    """Analyzes the impact of code changes using Neo4j graph traversal."""

    def __init__(self, graph_store: Neo4jGraphStore):
        """
        Initialize the impact analyzer.

        Args:
            graph_store: Neo4jGraphStore instance
        """
        self.graph_store = graph_store

    def analyze_function_impact(self, function_name: str,
                                  max_depth: int = 3,
                                  limit: int = 100) -> Optional[ImpactResult]:
        """
        Comprehensive impact analysis for a function.

        Args:
            function_name: Name of the function to analyze
            max_depth: Maximum depth for call chain traversal
            limit: Maximum number of results per category

        Returns:
            ImpactResult or None if function not found
        """
        logger.info(f"Analyzing impact for function: {function_name}")

        # Check if function exists
        func_results = self.graph_store.execute_query(
            queries.GET_FUNCTION_BY_NAME,
            {'func_name': function_name}
        )

        if not func_results:
            logger.warning(f"Function '{function_name}' not found in database")
            return None

        func_info = func_results[0]

        # Get direct callers
        direct_callers = self.get_direct_callers(function_name)

        # Get direct callees
        direct_callees = self.get_direct_callees(function_name)

        # Get indirect callers (multi-hop)
        indirect_callers = self.get_indirect_callers(function_name, max_depth, limit)

        # Get indirect callees (multi-hop)
        indirect_callees = self.get_indirect_callees(function_name, max_depth, limit)

        # Get test coverage
        direct_tests = self.get_covering_tests(function_name)
        indirect_tests = self.get_indirect_test_coverage(function_name, max_depth, limit)

        # Get call chains
        call_chains = self.get_impact_call_chains(function_name, max_depth, limit)

        # Calculate statistics
        stats = {
            'direct_caller_count': len(direct_callers),
            'direct_callee_count': len(direct_callees),
            'indirect_caller_count': len(indirect_callers),
            'indirect_callee_count': len(indirect_callees),
            'direct_test_count': len(direct_tests),
            'indirect_test_count': len(indirect_tests),
            'total_call_chains': len(call_chains),
            'max_depth_analyzed': max_depth,
        }

        result = ImpactResult(
            target_function=function_name,
            target_file=func_info.get('file_path', ''),
            direct_callers=direct_callers,
            direct_callees=direct_callees,
            indirect_callers=indirect_callers,
            indirect_callees=indirect_callees,
            direct_tests=direct_tests,
            indirect_tests=indirect_tests,
            call_chains=call_chains,
            stats=stats
        )

        logger.info(f"Impact analysis complete: {stats}")
        return result

    def get_direct_callers(self, function_name: str) -> List[Dict[str, Any]]:
        """Get functions that directly call the target function."""
        results = self.graph_store.execute_query(
            queries.GET_DIRECT_CALLERS,
            {'func_name': function_name}
        )
        return results

    def get_direct_callees(self, function_name: str) -> List[Dict[str, Any]]:
        """Get functions that are directly called by the target function."""
        results = self.graph_store.execute_query(
            queries.GET_DIRECT_CALLEES,
            {'func_name': function_name}
        )
        return results

    def get_indirect_callers(self, function_name: str, max_depth: int, limit: int) -> List[Dict[str, Any]]:
        """Get functions that indirectly call the target function (multi-hop)."""
        # Build query with literal max_depth (Neo4j doesn't allow params in pattern ranges)
        query = f"""
        MATCH (target:Function {{name: $func_name}})
        MATCH path = (caller:Function)-[:CALLS*1..{max_depth}]->(target)
        WHERE caller <> target
        RETURN caller.id as id, caller.name as name, caller.file_path as file_path,
               caller.subsystem as subsystem,
               length(path) as distance,
               [node in nodes(path) | node.name] as call_chain
        ORDER BY distance, caller.name
        LIMIT $limit
        """

        results = self.graph_store.execute_query(
            query,
            {'func_name': function_name, 'limit': limit}
        )

        # Filter out direct callers (distance > 1)
        indirect = [r for r in results if r['distance'] > 1]
        return indirect

    def get_indirect_callees(self, function_name: str, max_depth: int, limit: int) -> List[Dict[str, Any]]:
        """Get functions that are indirectly called by the target function (multi-hop)."""
        # Build query with literal max_depth
        query = f"""
        MATCH (source:Function {{name: $func_name}})
        MATCH path = (source)-[:CALLS*1..{max_depth}]->(callee:Function)
        WHERE source <> callee
        RETURN callee.id as id, callee.name as name, callee.file_path as file_path,
               callee.subsystem as subsystem,
               length(path) as distance,
               [node in nodes(path) | node.name] as call_chain
        ORDER BY distance, callee.name
        LIMIT $limit
        """

        results = self.graph_store.execute_query(
            query,
            {'func_name': function_name, 'limit': limit}
        )

        # Filter out direct callees (distance > 1)
        indirect = [r for r in results if r['distance'] > 1]
        return indirect

    def get_covering_tests(self, function_name: str) -> List[Dict[str, Any]]:
        """Get test cases that directly cover the target function."""
        results = self.graph_store.execute_query(
            queries.GET_COVERING_TESTS,
            {'func_name': function_name}
        )
        return results

    def get_indirect_test_coverage(self, function_name: str, max_depth: int, limit: int) -> List[Dict[str, Any]]:
        """Get test cases that indirectly cover the target function through callers."""
        # Build query with literal max_depth
        query = f"""
        MATCH (target:Function {{name: $func_name}})
        MATCH path = (caller:Function)-[:CALLS*1..{max_depth}]->(target)
        MATCH (test:TestCase)-[:COVERS]->(caller)
        WHERE caller <> target
        RETURN test.id as test_id, test.name as test_name,
               test.file_path as test_file,
               caller.name as via_function,
               length(path) as indirection_level
        ORDER BY indirection_level, test_name
        LIMIT $limit
        """

        results = self.graph_store.execute_query(
            query,
            {'func_name': function_name, 'limit': limit}
        )
        return results

    def get_impact_call_chains(self, function_name: str, max_depth: int, limit: int) -> List[Dict[str, Any]]:
        """Get all call chains leading to the target function with test coverage."""
        # Build query with literal max_depth
        query = f"""
        MATCH (target:Function {{name: $func_name}})
        MATCH path = (caller:Function)-[:CALLS*1..{max_depth}]->(target)
        WHERE caller <> target

        // Get test coverage for each caller
        OPTIONAL MATCH (test:TestCase)-[:COVERS]->(caller)

        RETURN
            [node in nodes(path) | node.name] as call_chain,
            length(path) as depth,
            caller.name as caller_name,
            caller.file_path as caller_file,
            caller.subsystem as caller_subsystem,
            collect(DISTINCT test.name) as covering_tests,
            count(DISTINCT test) as test_count
        ORDER BY depth, caller_name
        LIMIT $limit
        """

        results = self.graph_store.execute_query(
            query,
            {'func_name': function_name, 'limit': limit}
        )
        return results

    def format_impact_report(self, impact: ImpactResult, max_items: int = 10) -> str:
        """
        Format impact analysis results as a human-readable report.

        Args:
            impact: ImpactResult object
            max_items: Maximum number of items to show per category

        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"IMPACT ANALYSIS: {impact.target_function}")
        lines.append("=" * 80)
        lines.append(f"File: {impact.target_file}")
        lines.append("")

        # Statistics summary
        lines.append("SUMMARY")
        lines.append("-" * 80)
        stats = impact.stats
        lines.append(f"  Direct callers:       {stats['direct_caller_count']}")
        lines.append(f"  Indirect callers:     {stats['indirect_caller_count']}")
        lines.append(f"  Direct callees:       {stats['direct_callee_count']}")
        lines.append(f"  Indirect callees:     {stats['indirect_callee_count']}")
        lines.append(f"  Direct test coverage: {stats['direct_test_count']}")
        lines.append(f"  Indirect test coverage: {stats['indirect_test_count']}")
        lines.append(f"  Total call chains:    {stats['total_call_chains']}")
        lines.append("")

        # Direct callers
        if impact.direct_callers:
            lines.append("DIRECT CALLERS (functions that call this function)")
            lines.append("-" * 80)
            for i, caller in enumerate(impact.direct_callers[:max_items]):
                file_short = Path(caller['file_path']).name
                lines.append(f"  {i+1}. {caller['name']} ({file_short}:{caller.get('call_line', '?')})")
            if len(impact.direct_callers) > max_items:
                lines.append(f"  ... and {len(impact.direct_callers) - max_items} more")
            lines.append("")

        # Indirect callers (sample)
        if impact.indirect_callers:
            lines.append("INDIRECT CALLERS (multi-hop call chains)")
            lines.append("-" * 80)
            for i, caller in enumerate(impact.indirect_callers[:max_items]):
                file_short = Path(caller['file_path']).name
                chain = caller.get('call_chain', [])
                chain_str = " → ".join(chain) if chain else "N/A"
                lines.append(f"  {i+1}. {caller['name']} ({file_short}) [depth: {caller['distance']}]")
                lines.append(f"      Chain: {chain_str}")
            if len(impact.indirect_callers) > max_items:
                lines.append(f"  ... and {len(impact.indirect_callers) - max_items} more")
            lines.append("")

        # Test coverage
        if impact.direct_tests or impact.indirect_tests:
            lines.append("TEST COVERAGE")
            lines.append("-" * 80)

            if impact.direct_tests:
                lines.append("  Direct coverage:")
                for test in impact.direct_tests[:max_items]:
                    file_short = Path(test['file_path']).name
                    lines.append(f"    - {test['name']} ({file_short})")

            if impact.indirect_tests:
                lines.append("  Indirect coverage (via callers):")
                for test in impact.indirect_tests[:max_items]:
                    file_short = Path(test['test_file']).name if test.get('test_file') else 'unknown'
                    via = test.get('via_function', 'unknown')
                    level = test.get('indirection_level', '?')
                    lines.append(f"    - {test['test_name']} → {via} [depth: {level}]")

            if not impact.direct_tests and not impact.indirect_tests:
                lines.append("  ⚠️  NO TEST COVERAGE FOUND")
            lines.append("")

        # Risk assessment
        lines.append("RISK ASSESSMENT")
        lines.append("-" * 80)

        total_callers = stats['direct_caller_count'] + stats['indirect_caller_count']
        total_tests = stats['direct_test_count'] + stats['indirect_test_count']

        if total_callers == 0:
            risk = "LOW (no callers - isolated function)"
        elif total_tests == 0:
            if total_callers > 10:
                risk = "CRITICAL (widely used, no test coverage)"
            elif total_callers > 5:
                risk = "HIGH (moderately used, no test coverage)"
            else:
                risk = "MEDIUM (some usage, no test coverage)"
        elif total_tests < 2 and total_callers > 5:
            risk = "MEDIUM-HIGH (used often, limited test coverage)"
        else:
            risk = "LOW-MEDIUM (has test coverage)"

        lines.append(f"  Risk Level: {risk}")
        lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)


if __name__ == "__main__":
    import os

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python impact_analyzer.py <function_name> [max_depth]")
        print("Example: python impact_analyzer.py ext4_map_blocks 3")
        sys.exit(1)

    function_name = sys.argv[1]
    max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    neo4j_url = os.getenv("NEO4J_URL", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")

    with Neo4jGraphStore(neo4j_url, neo4j_user, neo4j_password) as store:
        analyzer = ImpactAnalyzer(store)

        # Analyze function impact
        impact = analyzer.analyze_function_impact(function_name, max_depth=max_depth)

        if impact:
            # Print report
            report = analyzer.format_impact_report(impact)
            print(report)
        else:
            print(f"Function '{function_name}' not found in database")
            sys.exit(1)
