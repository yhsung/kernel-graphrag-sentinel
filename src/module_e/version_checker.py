"""
Module E: Version Checker
Checks if CVE affects specific kernel versions.
"""

import logging
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass

from src.module_b.graph_store import Neo4jGraphStore

logger = logging.getLogger(__name__)


@dataclass
class VersionCheckResult:
    """
    Results of version compatibility check.

    Attributes:
        cve_id: CVE identifier
        kernel_version: Kernel version to check
        affected: Whether the kernel version is affected
        function_exists: Whether the vulnerable function exists
        patch_applied: Whether the fix patch is already applied
        can_backport: Whether the patch can be backported
        reason: Explanation of the result
    """
    cve_id: str
    kernel_version: str
    affected: bool
    function_exists: bool
    patch_applied: bool
    can_backport: bool
    reason: str


class VersionChecker:
    """
    Check CVE applicability to specific kernel versions.
    """

    def __init__(self, graph_store: Neo4jGraphStore, kernel_root: str):
        """
        Initialize the version checker.

        Args:
            graph_store: Neo4jGraphStore instance
            kernel_root: Path to kernel source tree
        """
        self.graph_store = graph_store
        self.kernel_root = Path(kernel_root)

    def check_cve_version(self, cve_id: str, kernel_version: str) -> Optional[VersionCheckResult]:
        """
        Check if CVE affects a specific kernel version.

        Args:
            cve_id: CVE identifier
            kernel_version: Kernel version (e.g., "5.15", "6.1")

        Returns:
            VersionCheckResult or None
        """
        logger.info(f"Checking CVE {cve_id} for kernel {kernel_version}")

        # Get CVE information
        cve_info = self._get_cve_info(cve_id)
        if not cve_info:
            logger.error(f"CVE {cve_id} not found")
            return None

        affected_function = cve_info.get('affected_function', '')
        fixed_commit = cve_info.get('fixed_commit', '')
        version_range = cve_info.get('kernel_version_affected', '')

        # Check if function exists in codebase
        function_exists = self._check_function_exists(affected_function)

        # Check if patch is already applied
        patch_applied = False
        if fixed_commit:
            patch_applied = self._check_patch_applied(fixed_commit)

        # Check if can backport
        can_backport = self._check_can_backport(fixed_commit, kernel_version)

        # Determine if affected
        affected = function_exists and not patch_applied

        # Build reason
        reason_parts = []
        if not function_exists:
            reason_parts.append(f"Function '{affected_function}' does not exist in {kernel_version}")
        elif patch_applied:
            reason_parts.append(f"Patch ({fixed_commit[:8]}) already applied")
        else:
            reason_parts.append(f"Function '{affected_function}' exists and is vulnerable")

        if version_range:
            reason_parts.append(f"CVE affects kernel versions {version_range}")

        reason = ". ".join(reason_parts)

        result = VersionCheckResult(
            cve_id=cve_id,
            kernel_version=kernel_version,
            affected=affected,
            function_exists=function_exists,
            patch_applied=patch_applied,
            can_backport=can_backport,
            reason=reason
        )

        logger.info(f"Version check complete: affected={affected}, "
                   f"function_exists={function_exists}, patch_applied={patch_applied}")

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

    def _check_function_exists(self, function_name: str) -> bool:
        """
        Check if function exists in the callgraph database.

        Args:
            function_name: Function name

        Returns:
            True if function exists
        """
        query = """
        MATCH (f:Function {name: $function_name})
        RETURN count(f) > 0 as exists
        """

        results = self.graph_store.execute_query(
            query,
            {'function_name': function_name}
        )

        return results[0]['exists'] if results else False

    def _check_patch_applied(self, commit_hash: str) -> bool:
        """
        Check if a patch (commit) is already applied.

        Args:
            commit_hash: Git commit hash

        Returns:
            True if patch is applied
        """
        if not self.kernel_root.exists():
            logger.warning(f"Kernel root {self.kernel_root} not accessible")
            return False

        try:
            # Check if commit exists in git history
            result = subprocess.run(
                ['git', 'cat-file', '-e', commit_hash],
                cwd=self.kernel_root,
                capture_output=True,
                timeout=5
            )

            return result.returncode == 0

        except Exception as e:
            logger.warning(f"Failed to check patch status: {e}")
            return False

    def _check_can_backport(self, commit_hash: str, kernel_version: str) -> bool:
        """
        Check if a patch can be backported to a kernel version.

        Args:
            commit_hash: Git commit hash
            kernel_version: Target kernel version

        Returns:
            True if can likely be backported
        """
        # For now, return True if patch exists
        # In a full implementation, you would:
        # 1. Check patch dependencies
        # 2. Check if function signatures match
        # 3. Check if related APIs exist
        # 4. Analyze patch complexity

        if not commit_hash:
            return False

        if not self.kernel_root.exists():
            return False

        try:
            # Simple check: does the commit exist?
            result = subprocess.run(
                ['git', 'cat-file', '-e', commit_hash],
                cwd=self.kernel_root,
                capture_output=True,
                timeout=5
            )

            return result.returncode == 0

        except Exception as e:
            logger.warning(f"Failed to check backport feasibility: {e}")
            return False

    def batch_check_cves(self, cve_ids: List[str],
                        kernel_version: str) -> List[VersionCheckResult]:
        """
        Check multiple CVEs against a kernel version.

        Args:
            cve_ids: List of CVE identifiers
            kernel_version: Kernel version

        Returns:
            List of VersionCheckResult objects
        """
        results = []

        for cve_id in cve_ids:
            try:
                result = self.check_cve_version(cve_id, kernel_version)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Failed to check {cve_id}: {e}")
                continue

        return results

    def format_version_report(self, result: VersionCheckResult) -> str:
        """
        Format version check result as a report.

        Args:
            result: VersionCheckResult object

        Returns:
            Formatted report
        """
        lines = []
        lines.append(f"CVE: {result.cve_id}")
        lines.append(f"Kernel Version: {result.kernel_version}")
        lines.append("")

        status = "✓ AFFECTS" if result.affected else "✗ NOT AFFECTED"
        lines.append(f"Status: {status}")
        lines.append("")

        lines.append("Details:")
        lines.append(f"  - Function exists: {result.function_exists}")
        lines.append(f"  - Patch applied: {result.patch_applied}")
        lines.append(f"  - Can backport: {result.can_backport}")
        lines.append("")

        lines.append(f"Reason: {result.reason}")

        return "\n".join(lines)


if __name__ == "__main__":
    import sys
    import os

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 3:
        print("Usage: python version_checker.py <cve_id> <kernel_version>")
        print("Example: python version_checker.py CVE-2024-1234 5.15")
        sys.exit(1)

    cve_id = sys.argv[1]
    kernel_version = sys.argv[2]
    kernel_root = os.getenv('KERNEL_ROOT', '/path/to/linux')

    from src.config import Config

    config = Config.from_defaults(kernel_root=kernel_root)

    with Neo4jGraphStore(
        config.neo4j.url,
        config.neo4j.user,
        config.neo4j.password
    ) as store:
        checker = VersionChecker(store, kernel_root)

        # Check version
        result = checker.check_cve_version(cve_id, kernel_version)

        if result:
            report = checker.format_version_report(result)
            print(report)
        else:
            print(f"Failed to check CVE {cve_id}")
            sys.exit(1)
