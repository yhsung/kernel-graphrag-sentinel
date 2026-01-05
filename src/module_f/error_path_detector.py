"""
ErrorPathDetector: Find error return paths in kernel C functions

This module uses tree-sitter to parse C functions and identify all error
return paths (return -ERRNO, goto err_label, etc.).
"""

import re
import logging
from typing import List, Optional, Set

try:
    from tree_sitter import Parser, Language, Node
    from tree_sitter_c import language
except ImportError:
    Parser = None
    Language = None
    Node = None

from .schema import ErrorPath

logger = logging.getLogger(__name__)


# Common error code patterns
ERROR_CODE_PATTERNS = [
    r'-E[A-Z]+',  # -ENOMEM, -EIO, -EINVAL, etc.
    r'-ERESTART[A-Z]*',  # -ERESTARTSYS, -ERESTARTNOHAND, etc.
    r'-E[A-Z0-9]+',  # Any error code
]


class ErrorPathDetector:
    """
    Detect error return paths in C functions.

    Identifies:
    - return statements with negative error codes
    - goto statements to error labels
    """

    def __init__(self):
        """Initialize the error path detector with tree-sitter parser."""
        if Parser is None:
            raise ImportError("tree-sitter or tree-sitter-c is not installed")

        self.language = Language(language())
        self.parser = Parser()
        self.parser.language = self.language

    def find_error_paths_in_file(self, file_path: str, function_name: Optional[str] = None) -> dict:
        """
        Find error paths for functions in a C source file.

        Args:
            file_path: Path to the C source file
            function_name: If specified, only analyze this function

        Returns:
            Dictionary mapping function names to lists of ErrorPath objects
        """
        from pathlib import Path
        source_code = Path(file_path).read_text(encoding='utf-8', errors='ignore')
        return self.find_error_paths_in_code(source_code, file_path, function_name)

    def find_error_paths_in_code(
        self,
        source_code: str,
        file_path: str = "<unknown>",
        function_name: Optional[str] = None,
    ) -> dict:
        """
        Find error paths for functions in C source code.

        Args:
            source_code: C source code as string
            file_path: File path for reference
            function_name: If specified, only analyze this function

        Returns:
            Dictionary mapping function names to lists of ErrorPath objects
        """
        if not source_code:
            return {}

        # Parse source code
        tree = self.parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node

        if root_node.has_error:
            logger.warning(f"Parsing errors in {file_path}, AST may be incomplete")

        # Find all functions
        all_error_paths = {}
        self._find_functions_and_paths(root_node, source_code, file_path, all_error_paths, function_name)

        return all_error_paths

    def _find_functions_and_paths(
        self,
        node: Node,
        source_code: str,
        file_path: str,
        all_error_paths: dict,
        target_function: Optional[str] = None,
    ):
        """
        Recursively find function definitions and their error paths.

        Args:
            node: Current AST node
            source_code: Source code string
            file_path: File path for reference
            all_error_paths: Dictionary to collect error paths per function
            target_function: If specified, only analyze this function
        """
        if node.type == 'function_definition':
            func_name = self._extract_function_name(node)

            # Skip if looking for specific function
            if target_function and func_name != target_function:
                return

            # Find error paths in this function
            error_paths = self._find_error_paths_in_function(node, source_code)

            if error_paths:
                all_error_paths[func_name] = error_paths
                logger.debug(f"Found {len(error_paths)} error paths in {func_name}")

            return  # Don't recurse into function body twice

        # Recurse into children
        for child in node.children:
            self._find_functions_and_paths(child, source_code, file_path, all_error_paths, target_function)

    def _find_error_paths_in_function(self, func_node: Node, source_code: str) -> List[ErrorPath]:
        """
        Find all error paths within a function.

        Args:
            func_node: Function definition node
            source_code: Source code string

        Returns:
            List of ErrorPath objects
        """
        error_paths = []

        # Traverse function body to find error return paths
        self._traverse_for_error_paths(func_node, source_code, error_paths)

        return error_paths

    def _traverse_for_error_paths(self, node: Node, source_code: str, error_paths: List[ErrorPath]):
        """
        Recursively traverse function body to find error paths.

        Args:
            node: Current AST node
            source_code: Source code string
            error_paths: List to collect error paths
        """
        # Check for return statement
        if node.type == 'return_statement':
            error_path = self._check_return_statement(node, source_code)
            if error_path:
                error_paths.append(error_path)

        # Check for goto statement
        elif node.type == 'goto_statement':
            error_path = self._check_goto_statement(node, source_code)
            if error_path:
                error_paths.append(error_path)

        # Recurse into children
        for child in node.children:
            self._traverse_for_error_paths(child, source_code, error_paths)

    def _check_return_statement(self, node: Node, source_code: str) -> Optional[ErrorPath]:
        """
        Check if a return statement is an error path.

        Args:
            node: Return statement node
            source_code: Source code string

        Returns:
            ErrorPath if this is an error return, None otherwise
        """
        line_number = node.start_point[0] + 1

        # Get return value
        return_value = self._get_node_text(node, source_code)

        # Check if it's an error code
        error_code = self._extract_error_code(return_value)

        if error_code:
            return ErrorPath(
                line_number=line_number,
                path_type='return',
                error_code=error_code,
                has_log=False,  # Will be determined later by CoverageAnalyzer
            )

        return None

    def _check_goto_statement(self, node: Node, source_code: str) -> Optional[ErrorPath]:
        """
        Check if a goto statement is an error path.

        Args:
            node: Goto statement node
            source_code: Source code string

        Returns:
            ErrorPath if this is an error goto, None otherwise
        """
        line_number = node.start_point[0] + 1
        goto_text = self._get_node_text(node, source_code)

        # Extract label name
        label_match = re.search(r'goto\s+(\w+)', goto_text)
        if not label_match:
            return None

        label = label_match.group(1)

        # Check if it's an error label (common patterns: err_, error_, fail_, out_, exit_)
        error_label_patterns = [
            r'^err',
            r'^error',
            r'^fail',
            r'^out',
            r'^exit',
            r'^cleanup',
            r'^undo',
        ]

        is_error_label = any(re.match(pattern, label, re.IGNORECASE) for pattern in error_label_patterns)

        if is_error_label:
            return ErrorPath(
                line_number=line_number,
                path_type='goto',
                goto_label=label,
                has_log=False,  # Will be determined later by CoverageAnalyzer
            )

        return None

    def _extract_error_code(self, return_value: str) -> Optional[str]:
        """
        Extract error code from return statement.

        Args:
            return_value: Return statement text

        Returns:
            Error code string (e.g., "-ENOMEM") if found, None otherwise
        """
        # Remove "return" keyword
        return_value = return_value.replace('return', '').strip()
        return_value = return_value.rstrip(';').strip()

        # Check for direct error code
        for pattern in ERROR_CODE_PATTERNS:
            if re.match(pattern, return_value):
                return return_value

        # Check for common error variable names
        error_vars = ['ret', 'err', 'error', 'rc', 'retval', 'result']
        for var in error_vars:
            if return_value == var or return_value.startswith(f'{var} '):
                return f'<{var}>'  # Indirect error code

        return None

    def _extract_function_name(self, func_node: Node) -> Optional[str]:
        """
        Extract function name from function definition node.

        Args:
            func_node: Function definition node

        Returns:
            Function name string or None
        """
        # Navigate to the declarator
        for child in func_node.children:
            if child.type == 'function_declarator':
                # The name should be in the declarator
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        return subchild.text.decode('utf-8')
        return None

    def _get_node_text(self, node: Node, source_code: str) -> str:
        """
        Get text content of a node.

        Args:
            node: AST node
            source_code: Source code string

        Returns:
            Text content of the node
        """
        start_byte = node.start_byte
        end_byte = node.end_byte
        return source_code[start_byte:end_byte]
