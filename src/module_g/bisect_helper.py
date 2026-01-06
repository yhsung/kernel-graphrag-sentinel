"""
BisectHelper: Accelerate git bisect workflows

This module helps analyze code during git bisect to identify
bug-introducing commits more quickly.
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class BisectHelper:
    """
    Assist with git bisect workflows.

    Analyzes code at current bisect position to suggest verdict (good/bad)
    and identify potential bug sources.
    """

    def __init__(self, graph_store, kernel_root: str):
        """
        Initialize the bisect helper.

        Args:
            graph_store: Neo4j graph store instance
            kernel_root: Path to kernel source
        """
        self.store = graph_store
        self.kernel_root = kernel_root

    def analyze_bisect_state(
        self,
        bug_description: str,
        function_name: str = None
    ) -> Dict[str, Any]:
        """
        Analyze current state during git bisect.

        Args:
            bug_description: Description of the bug
            function_name: Optional function name to analyze

        Returns:
            Dict with analysis and verdict
        """
        logger.info(f"Analyzing bisect state: {bug_description}")

        # Extract function name from description if not provided
        if not function_name:
            function_name = self._extract_function_name(bug_description)

        if not function_name:
            return {
                'function_name': 'Unknown',
                'hypothesis': 'Could not identify function from bug description',
                'checkpoints': [],
                'verdict': 'NEEDS_MORE_INFO',
                'reason': 'Cannot determine function to analyze',
            }

        # Check if function exists in current revision
        function_exists = self._check_function_exists(function_name)

        # Analyze error paths if this is about error handling
        checkpoints = self._generate_checkpoints(function_name, bug_description)

        # Determine verdict
        all_passed = all(c['result'] for c in checkpoints)
        some_failed = any(not c['result'] for c in checkpoints)

        if not function_exists:
            verdict = 'MARK_AS_GOOD'  # Function doesn't exist, bug not present yet
            reason = f"Function {function_name} does not exist in current revision"
        elif some_failed:
            verdict = 'MARK_AS_BAD'
            reason = f"Function {function_name} has issues in current revision"
        else:
            verdict = 'MARK_AS_GOOD'
            reason = f"Function {function_name} appears healthy in current revision"

        return {
            'function_name': function_name,
            'hypothesis': self._generate_hypothesis(function_name, bug_description),
            'checkpoints': checkpoints,
            'verdict': verdict,
            'reason': reason,
        }

    def suggest_test_case(self, bug_description: str) -> str:
        """
        Suggest a test case to reproduce the bug.

        Args:
            bug_description: Bug description

        Returns:
            Test case suggestion
        """
        function_name = self._extract_function_name(bug_description)

        if not function_name:
            return "Unable to generate test case - unknown function"

        # Generate test case based on bug type
        if 'allocation' in bug_description.lower() and 'fail' in bug_description.lower():
            return f"""
Test Case: {function_name} allocation failure

Steps:
  1. Use fault injection to simulate allocation failure
  2. Call {function_name}()
  3. Verify error is returned (not success)
  4. Check for resource leaks (memory, locks)

Expected: Function returns error code cleanly
Bug: Function crashes or returns success incorrectly
"""

        elif 'leak' in bug_description.lower():
            return f"""
Test Case: {function_name} resource leak

Steps:
  1. Call {function_name}()
  2. Trigger early exit/error path
  3. Check resource cleanup with kmemleak or similar

Expected: All resources freed on all exit paths
Bug: Resources leaked on error paths
"""

        else:
            return f"""
Test Case: {function_name}

Steps:
  1. Call {function_name}()
  2. Trigger the bug condition: {bug_description}
  3. Verify behavior matches expected (not buggy behavior)

Expected: Normal operation or proper error handling
Bug: Incorrect behavior or crash
"""

    def _extract_function_name(self, bug_description: str) -> str:
        """Extract function name from bug description."""
        # Look for patterns like "ext4: writepage" or "ext4_writepages"
        patterns = [
            r'\b([a-z_]+_[a-z_]+)\(',  # function_name(
            r'([a-z]+): ([a-z_]+)',      # subsystem: function
        ]

        for pattern in patterns:
            match = re.search(pattern, bug_description.lower())
            if match:
                if match.lastindex == 1:
                    return match.group(1)
                else:
                    return f"{match.group(1)}_{match.group(2)}"

        return None

    def _check_function_exists(self, function_name: str) -> bool:
        """Check if function exists in current code."""
        query = """
        MATCH (f:Function {name: $function_name})
        RETURN count(f) > 0 as exists
        """

        try:
            results = self.store.execute_query(query, {'function_name': function_name})
            return results[0]['exists'] if results else False
        except:
            return False

    def _generate_checkpoints(
        self,
        function_name: str,
        bug_description: str
    ) -> List[Dict[str, Any]]:
        """Generate analysis checkpoints."""
        checkpoints = []

        # Checkpoint 1: Function exists
        checkpoints.append({
            'check': f"Does {function_name} exist?",
            'result': self._check_function_exists(function_name),
        })

        # Checkpoint 2: Has error paths (if error-related bug)
        if any(word in bug_description.lower() for word in ['error', 'fail', 'leak']):
            has_error_paths = self._check_has_error_paths(function_name)
            checkpoints.append({
                'check': f"Does {function_name} have error paths?",
                'result': has_error_paths,
            })

        return checkpoints

    def _check_has_error_paths(self, function_name: str) -> bool:
        """Check if function has error handling paths."""
        # Simplified: check for return statements in graph
        # Real implementation would use Module F
        return True

    def _generate_hypothesis(self, function_name: str, bug_description: str) -> str:
        """Generate hypothesis about the bug."""
        if 'leak' in bug_description.lower():
            return f"Bug occurs in {function_name} when resources not freed on error paths"
        elif 'crash' in bug_description.lower():
            return f"Bug occurs in {function_name} when handling invalid input"
        elif 'hang' in bug_description.lower():
            return f"Bug occurs in {function_name} waiting for condition that never occurs"
        else:
            return f"Bug occurs in {function_name}: {bug_description}"
