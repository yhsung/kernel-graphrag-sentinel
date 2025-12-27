"""
Module C: KUnit Parser
Parses KUnit test files to extract test cases and tested functions.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Set, Optional, Tuple
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.module_a.parser import CParser
from tree_sitter import Node

logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Represents a KUnit test case."""
    name: str
    file_path: str
    line_start: int
    line_end: int
    test_suite: str
    tested_functions: List[str]  # Functions called within this test


@dataclass
class TestSuite:
    """Represents a KUnit test suite."""
    name: str
    file_path: str
    test_cases: List[str]  # List of test case names


class KUnitParser:
    """Parses KUnit test files using tree-sitter."""

    def __init__(self):
        """Initialize the KUnit parser."""
        self.parser = CParser()

    def parse_test_file(self, test_file: str) -> Tuple[List[TestCase], List[TestSuite]]:
        """
        Parse a KUnit test file to extract test cases and suites.

        Args:
            test_file: Path to the KUnit test file

        Returns:
            Tuple of (test_cases, test_suites)
        """
        logger.info(f"Parsing KUnit test file: {test_file}")

        # Read file
        with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()

        # Parse C code
        root_node = self.parser.parse(code)

        # Extract test functions
        test_functions = self._find_test_functions(root_node, code)

        # Extract test cases with their tested functions
        test_cases = []
        for func_node, func_name in test_functions:
            tested_functions = self._extract_function_calls(func_node, code)

            # Filter out common KUnit macros and test helper functions
            tested_functions = self._filter_test_functions(tested_functions)

            test_case = TestCase(
                name=func_name,
                file_path=test_file,
                line_start=func_node.start_point[0] + 1,
                line_end=func_node.end_point[0] + 1,
                test_suite="",  # Will be filled when processing test suites
                tested_functions=tested_functions
            )
            test_cases.append(test_case)

        # Extract test suites
        test_suites = self._find_test_suites(root_node, code)

        # Link test cases to suites
        self._link_test_cases_to_suites(test_cases, test_suites)

        logger.info(f"Found {len(test_cases)} test cases in {len(test_suites)} suites")

        return test_cases, test_suites

    def _find_test_functions(self, root_node: Node, code: str) -> List[Tuple[Node, str]]:
        """
        Find all test functions in the AST.

        Test functions typically:
        - Start with 'test_' prefix
        - Have signature: void test_name(struct kunit *test)
        """
        test_functions = []

        def traverse(node):
            if node.type == 'function_definition':
                func_name = self._extract_function_name(node)
                if func_name and self._is_test_function(func_name, node, code):
                    test_functions.append((node, func_name))

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return test_functions

    def _extract_function_name(self, func_node: Node) -> Optional[str]:
        """Extract function name from a function_definition node."""
        # Look for function_declarator
        declarator = None
        for child in func_node.children:
            if child.type == 'function_declarator':
                declarator = child
                break

        if not declarator:
            return None

        # Find identifier in declarator
        for child in declarator.children:
            if child.type == 'identifier':
                return child.text.decode('utf8')
            elif child.type == 'pointer_declarator':
                # Handle pointer return types
                for subchild in child.children:
                    if subchild.type == 'function_declarator':
                        for subsubchild in subchild.children:
                            if subsubchild.type == 'identifier':
                                return subsubchild.text.decode('utf8')

        return None

    def _is_test_function(self, func_name: str, func_node: Node, code: str) -> bool:
        """
        Determine if a function is a KUnit test function.

        Criteria:
        - Has parameter of type 'struct kunit *' (primary indicator)
        - Name contains 'test' (secondary check)
        """
        # Check for 'struct kunit *' parameter (primary indicator)
        has_kunit_param = False
        for child in func_node.children:
            if child.type == 'function_declarator':
                for subchild in child.children:
                    if subchild.type == 'parameter_list':
                        param_text = code[subchild.start_byte:subchild.end_byte]
                        if 'struct kunit' in param_text:
                            has_kunit_param = True
                            break

        # If it has kunit parameter and name contains 'test', it's a test function
        if has_kunit_param and 'test' in func_name.lower():
            return True

        return False

    def _extract_function_calls(self, func_node: Node, code: str) -> List[str]:
        """Extract all function calls within a test function."""
        function_calls = []

        def traverse(node):
            if node.type == 'call_expression':
                # Get the function name
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = child.text.decode('utf8')
                        function_calls.append(func_name)
                        break
                    elif child.type == 'field_expression':
                        # Handle function pointers like sb->s_op->func()
                        # Extract the final function name
                        last_id = None
                        for subchild in child.children:
                            if subchild.type == 'identifier':
                                last_id = subchild.text.decode('utf8')
                        if last_id:
                            function_calls.append(last_id)

            for child in node.children:
                traverse(child)

        # Traverse the function body
        for child in func_node.children:
            if child.type == 'compound_statement':
                traverse(child)

        return function_calls

    def _filter_test_functions(self, function_calls: List[str]) -> List[str]:
        """
        Filter out KUnit macros and test helper functions.

        Keep only actual kernel functions being tested.
        """
        # KUnit macros and helpers to exclude
        kunit_keywords = {
            'KUNIT_EXPECT_EQ', 'KUNIT_EXPECT_NE', 'KUNIT_EXPECT_GT',
            'KUNIT_EXPECT_LT', 'KUNIT_EXPECT_GE', 'KUNIT_EXPECT_LE',
            'KUNIT_EXPECT_TRUE', 'KUNIT_EXPECT_FALSE', 'KUNIT_EXPECT_NULL',
            'KUNIT_EXPECT_NOT_NULL', 'KUNIT_EXPECT_PTR_EQ', 'KUNIT_EXPECT_PTR_NE',
            'KUNIT_EXPECT_EQ_MSG', 'KUNIT_EXPECT_NE_MSG', 'KUNIT_EXPECT_STREQ',
            'KUNIT_ASSERT_EQ', 'KUNIT_ASSERT_NE', 'KUNIT_ASSERT_GT',
            'KUNIT_ASSERT_LT', 'KUNIT_ASSERT_GE', 'KUNIT_ASSERT_LE',
            'KUNIT_ASSERT_TRUE', 'KUNIT_ASSERT_FALSE', 'KUNIT_ASSERT_NULL',
            'KUNIT_ASSERT_NOT_NULL', 'KUNIT_ASSERT_PTR_EQ', 'KUNIT_ASSERT_PTR_NE',
            'KUNIT_ASSERT_EQ_MSG', 'KUNIT_ASSERT_NOT_ERR_OR_NULL',
            'KUNIT_FAIL', 'KUNIT_SUCCEED',
            'kunit_kzalloc', 'kunit_kmalloc', 'kunit_kfree',
            'kunit_info', 'kunit_warn', 'kunit_err',
            'kunit_skip', 'kunit_activate_static_stub',
            # Common test helpers
            'get_bh', 'set_buffer_uptodate', 'set_bitmap_uptodate',
            'set_buffer_verified', 'mb_set_bits', 'mb_clear_bits',
            'mb_test_bit', 'mb_find_next_zero_bit', 'mb_find_next_bit',
            'memset', 'memcpy', 'strlen', 'strscpy', 'snprintf',
            'kmalloc', 'kzalloc', 'kfree', 'kcalloc',
            'cpu_to_le32', 'le32_to_cpu',
            # Generic helpers
            'INIT_LIST_HEAD', 'init_rwsem', 'inode_init_once',
        }

        # Filter out KUnit keywords and keep actual tested functions
        filtered = []
        seen = set()
        for func in function_calls:
            if func not in kunit_keywords and func not in seen:
                # Keep functions that look like kernel functions
                # (not starting with lowercase test_ or mbt_)
                if not func.startswith('test_') and not func.startswith('mbt_'):
                    filtered.append(func)
                    seen.add(func)

        return filtered

    def _find_test_suites(self, root_node: Node, code: str) -> List[TestSuite]:
        """
        Find test suite definitions in the AST.

        Test suites are defined as:
        struct kunit_suite suite_name = {
            .name = "suite_name",
            .test_cases = test_cases_array,
        };
        """
        test_suites = []

        def traverse(node):
            if node.type == 'declaration':
                # Check if it's a struct kunit_suite declaration
                decl_text = code[node.start_byte:node.end_byte]
                if 'struct kunit_suite' in decl_text:
                    suite_info = self._extract_suite_info(node, code)
                    if suite_info:
                        test_suites.append(suite_info)

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return test_suites

    def _extract_suite_info(self, decl_node: Node, code: str) -> Optional[TestSuite]:
        """Extract test suite information from a declaration node."""
        # Extract suite variable name
        suite_name = None
        for child in decl_node.children:
            if child.type == 'init_declarator':
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        suite_name = subchild.text.decode('utf8')
                        break

        if not suite_name:
            return None

        # Extract test cases array name from initializer
        # This is a simplified extraction - in reality, we'd need to
        # parse the .test_cases field and then find the array definition
        test_cases = []

        # For now, return the suite with empty test cases list
        # The actual test case mapping will be done through function analysis
        return TestSuite(
            name=suite_name,
            file_path="",  # Will be set by caller
            test_cases=test_cases
        )

    def _link_test_cases_to_suites(self, test_cases: List[TestCase],
                                     test_suites: List[TestSuite]):
        """
        Link test cases to their respective test suites.

        In KUnit, test cases are registered to suites via KUNIT_CASE macros.
        For simplicity, we'll assign all test cases in a file to the first suite
        in that file.
        """
        if not test_suites:
            return

        # Group test cases by file
        file_to_cases = {}
        for tc in test_cases:
            if tc.file_path not in file_to_cases:
                file_to_cases[tc.file_path] = []
            file_to_cases[tc.file_path].append(tc)

        # Assign test cases to first suite in each file
        for suite in test_suites:
            if suite.file_path in file_to_cases:
                suite.test_cases = [tc.name for tc in file_to_cases[suite.file_path]]
                # Update test cases with suite name
                for tc in file_to_cases[suite.file_path]:
                    tc.test_suite = suite.name


def find_kunit_test_files(subsystem_path: str) -> List[str]:
    """
    Find all KUnit test files in a subsystem directory.

    KUnit test files typically:
    - End with '-test.c' or '_test.c'
    - Or contain 'kunit' in the name

    Args:
        subsystem_path: Path to kernel subsystem directory

    Returns:
        List of paths to KUnit test files
    """
    test_files = []
    subsystem_dir = Path(subsystem_path)

    if not subsystem_dir.exists():
        logger.warning(f"Subsystem directory does not exist: {subsystem_path}")
        return test_files

    # Find test files
    for c_file in subsystem_dir.glob("*.c"):
        filename = c_file.name.lower()
        if filename.endswith('-test.c') or filename.endswith('_test.c') or 'kunit' in filename:
            test_files.append(str(c_file))

    logger.info(f"Found {len(test_files)} KUnit test files in {subsystem_path}")
    return test_files


if __name__ == "__main__":
    import os
    import json

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python kunit_parser.py <subsystem_path>")
        print("Example: python kunit_parser.py /workspaces/ubuntu/linux-6.13/fs/ext4")
        sys.exit(1)

    subsystem_path = sys.argv[1]

    # Find test files
    test_files = find_kunit_test_files(subsystem_path)

    if not test_files:
        print(f"No KUnit test files found in {subsystem_path}")
        sys.exit(0)

    # Parse each test file
    parser = KUnitParser()
    all_test_cases = []
    all_test_suites = []

    for test_file in test_files:
        print(f"\n=== Parsing {test_file} ===")
        test_cases, test_suites = parser.parse_test_file(test_file)

        # Update file_path in suites
        for suite in test_suites:
            suite.file_path = test_file

        all_test_cases.extend(test_cases)
        all_test_suites.extend(test_suites)

        print(f"Test cases: {len(test_cases)}")
        for tc in test_cases:
            print(f"  - {tc.name} (tests {len(tc.tested_functions)} functions)")
            for func in tc.tested_functions[:5]:  # Show first 5
                print(f"      → {func}")
            if len(tc.tested_functions) > 5:
                print(f"      ... and {len(tc.tested_functions) - 5} more")

    # Summary
    print(f"\n=== Summary ===")
    print(f"Total test files: {len(test_files)}")
    print(f"Total test cases: {len(all_test_cases)}")
    print(f"Total test suites: {len(all_test_suites)}")

    # Count unique tested functions
    all_tested_funcs = set()
    for tc in all_test_cases:
        all_tested_funcs.update(tc.tested_functions)
    print(f"Unique tested functions: {len(all_tested_funcs)}")
