"""
CommitAnalyzer: Analyze what changed in git commits

This module analyzes commit diffs to identify modified functions and
assess their impact using existing graph analysis tools.
"""

import re
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from .git_extractor import GitExtractor
from .schema import FileChange, FunctionChange

logger = logging.getLogger(__name__)


class CommitAnalyzer:
    """
    Analyze git commits to identify what changed and assess impact.

    Parses git diffs to find modified functions and links them to
    impact analysis using the existing graph database.
    """

    def __init__(self, graph_store, git_extractor: GitExtractor):
        """
        Initialize the commit analyzer.

        Args:
            graph_store: Neo4j graph store instance
            git_extractor: GitExtractor instance
        """
        self.store = graph_store
        self.extractor = git_extractor

    def analyze_commit(self, commit_hash: str) -> Dict[str, Any]:
        """
        Analyze changes in a commit.

        Args:
            commit_hash: Full or short commit hash

        Returns:
            Dict with commit info, files changed, functions modified, risk summary
        """
        logger.info(f"Analyzing commit {commit_hash}")

        # Get commit details
        commits = self.extractor.extract_commits(limit=1)
        commit = None
        for c in commits:
            if c.id.startswith(commit_hash) or c.hash_short == commit_hash:
                commit = c
                break

        if not commit:
            logger.error(f"Commit {commit_hash} not found")
            return {}

        # Get files changed
        file_changes = self.extractor.extract_commit_files(commit.id)

        # Parse diff to find modified functions
        functions_modified = self._parse_commit_diff(commit.id, file_changes)

        # For each function, get impact from graph
        for func_change in functions_modified:
            func_change['impact'] = self._get_function_impact(
                func_change['function_name']
            )
            func_change['test_coverage'] = self._get_function_test_coverage(
                func_change['function_name']
            )

        # Calculate risk summary
        risk_summary = self._calculate_risk_summary(functions_modified)

        return {
            'commit_info': {
                'hash': commit.hash_short,
                'title': commit.title,
                'message': commit.message,
                'author': commit.author_name,
                'date': commit.author_date,
                'branch': commit.branch,
                'files_changed': commit.files_changed,
                'insertions': commit.insertions,
                'deletions': commit.deletions,
            },
            'files_changed': [fc.to_dict() for fc in file_changes],
            'functions_modified': functions_modified,
            'risk_summary': risk_summary,
        }

    def _parse_commit_diff(
        self,
        commit_hash: str,
        file_changes: List[FileChange]
    ) -> List[Dict[str, Any]]:
        """
        Parse git diff to extract modified functions.

        Args:
            commit_hash: Commit hash
            file_changes: List of FileChange objects

        Returns:
            List of dicts with function change info
        """
        functions_modified = []

        for file_change in file_changes:
            # Skip deletions
            if file_change.change_type.value == 'deleted':
                continue

            # Get diff for this file
            diff_output = self._get_file_diff(commit_hash, file_change.file_path)

            # Extract function names from diff hunks
            functions_in_file = self._extract_functions_from_diff(
                diff_output,
                file_change.file_path
            )

            functions_modified.extend(functions_in_file)

        return functions_modified

    def _get_file_diff(self, commit_hash: str, file_path: str) -> str:
        """
        Get git diff output for a file.

        Args:
            commit_hash: Commit hash
            file_path: Path to the file

        Returns:
            Diff output as string
        """
        try:
            import subprocess
            cmd = ['git', 'show', f'{commit_hash}:{file_path}']
            result = subprocess.run(
                cmd,
                cwd=str(self.extractor.repo_path),
                capture_output=True,
                text=True,
                check=False  # File might not exist
            )

            return result.stdout

        except Exception as e:
            logger.warning(f"Failed to get diff for {file_path}: {e}")
            return ""

    def _extract_functions_from_diff(
        self,
        diff_output: str,
        file_path: str
    ) -> List[Dict[str, Any]]:
        """
        Extract function names from unified diff.

        Args:
            diff_output: Git diff output
            file_path: Path to the file

        Returns:
            List of function change dicts
        """
        functions = []

        # Look for function signatures in diff hunks
        # Format: @@ -line_start,count +line_start,count @@ function_name
        pattern = r'^@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s+@@\s*(?:\w+\s*)?(?:\*?\s*)?(\w+)\s*\('

        for line in diff_output.split('\n'):
            match = re.match(pattern, line)
            if match:
                function_name = match.group(2)

                # Filter out non-function names
                if self._is_valid_function_name(function_name):
                    functions.append({
                        'function_name': function_name,
                        'file_path': file_path,
                        'action': 'modified',
                        'lines_added': 0,  # Would need more parsing
                        'lines_removed': 0,
                    })

        return functions

    def _is_valid_function_name(self, name: str) -> bool:
        """
        Check if a name looks like a valid function name.

        Args:
            name: Function name candidate

        Returns:
            True if likely a function name
        """
        # Common C function patterns
        if not name or not name[0].isalpha():
            return False

        # Skip common false positives
        skip_list = ['if', 'for', 'while', 'switch', 'return', 'else', 'do']
        if name in skip_list:
            return False

        return True

    def _get_function_impact(self, function_name: str) -> Dict[str, Any]:
        """
        Get impact metrics for a function from the graph.

        Args:
            function_name: Name of the function

        Returns:
            Dict with impact metrics
        """
        try:
            # Query graph for function impact
            query = """
            MATCH (f:Function {name: $function_name})
            OPTIONAL MATCH (f)<-[r:CALLS]-(caller:Function)
            WITH f, count(caller) as callers
            OPTIONAL MATCH (f)-[r2:CALLS]->(callee:Function)
            WITH f, callers, count(callee) as callees
            OPTIONAL MATCH (f)<-[:CALLED_FROM]-(s:Syscall)
            RETURN f.name as function,
                   callers,
                   callees,
                   collect(s.name) as syscalls
            """

            result = self.store.execute_query(query, {'function_name': function_name})

            if result:
                record = result[0]
                return {
                    'callers': record.get('callers', 0),
                    'callees': record.get('callees', 0),
                    'syscall_paths': record.get('syscalls', []),
                }

        except Exception as e:
            logger.warning(f"Failed to get impact for {function_name}: {e}")

        return {
            'callers': 0,
            'callees': 0,
            'syscall_paths': [],
        }

    def _get_function_test_coverage(self, function_name: str) -> Dict[str, Any]:
        """
        Get test coverage for a function from the graph.

        Args:
            function_name: Name of the function

        Returns:
            Dict with test coverage metrics
        """
        try:
            query = """
            MATCH (f:Function {name: $function_name})
            OPTIONAL MATCH (f)<-[r:COVERS]-(t:TestCase)
            WITH f, count(t) as test_count
            OPTIONAL MATCH (f)<-[r2:COVERS]-(t2:TestCase)
            RETURN f.name as function,
                   test_count,
                   count(DISTINCT t2.name) as unique_tests
            """

            result = self.store.execute_query(query, {'function_name': function_name})

            if result:
                record = result[0]
                return {
                    'total_tests': record.get('test_count', 0),
                    'unique_tests': record.get('unique_tests', 0),
                }

        except Exception as e:
            logger.warning(f"Failed to get test coverage for {function_name}: {e}")

        return {
            'total_tests': 0,
            'unique_tests': 0,
        }

    def _calculate_risk_summary(
        self,
        functions_modified: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate risk summary for modified functions.

        Args:
            functions_modified: List of function change dicts

        Returns:
            Dict with risk summary
        """
        high_risk = []
        medium_risk = []
        low_risk = []

        for func in functions_modified:
            impact = func.get('impact', {})
            callers = impact.get('callers', 0)
            test_coverage = func.get('test_coverage', {})
            total_tests = test_coverage.get('total_tests', 0)

            # Calculate risk level
            # High risk: Many callers AND low test coverage
            # Low risk: Few callers OR high test coverage
            if callers >= 10 and total_tests == 0:
                risk_level = 'HIGH'
                high_risk.append(func)
            elif callers >= 5 and total_tests < 2:
                risk_level = 'MEDIUM'
                medium_risk.append(func)
            else:
                risk_level = 'LOW'
                low_risk.append(func)

            func['risk_level'] = risk_level

        # Generate recommendations
        recommendations = []
        if high_risk:
            recommendations.append(
                f"⚠️  High risk: {len(high_risk)} function(s) with many callers and no tests"
            )
        if medium_risk:
            recommendations.append(
                f"⚠️  Medium risk: {len(medium_risk)} function(s) need more testing"
            )
        if low_risk:
            recommendations.append(
                f"✓ Low risk: {len(low_risk)} function(s) safe to merge"
            )

        return {
            'high_risk_count': len(high_risk),
            'medium_risk_count': len(medium_risk),
            'low_risk_count': len(low_risk),
            'recommendations': recommendations,
        }
