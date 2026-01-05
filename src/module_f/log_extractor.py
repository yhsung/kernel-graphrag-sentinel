"""
LogExtractor: Extract log statements from kernel C code

This module uses tree-sitter to parse C code and extract log statements
that use the 20 core kernel logging functions.
"""

import re
import logging
from typing import List, Dict, Optional, Set
from pathlib import Path

try:
    from tree_sitter import Parser, Language, Node
    from tree_sitter_c import language
except ImportError:
    Parser = None
    Language = None
    Node = None

from .schema import (
    LogStatement,
    CORE_LOG_FUNCTIONS,
    LogSeverity,
)

logger = logging.getLogger(__name__)


# Map log functions to their severity levels
LOG_FUNCTION_SEVERITY = {
    'printk': None,  # printk has dynamic severity based on KERN_* prefix
    'pr_emerg': LogSeverity.EMERG.value,
    'pr_alert': LogSeverity.ALERT.value,
    'pr_crit': LogSeverity.CRIT.value,
    'pr_err': LogSeverity.ERR.value,
    'pr_warn': LogSeverity.WARNING.value,
    'pr_notice': LogSeverity.NOTICE.value,
    'pr_info': LogSeverity.INFO.value,
    'pr_debug': LogSeverity.DEBUG.value,
    'dev_err': LogSeverity.ERR.value,
    'dev_warn': LogSeverity.WARNING.value,
    'dev_info': LogSeverity.INFO.value,
    'dev_dbg': LogSeverity.DEBUG.value,
    'ext4_error': LogSeverity.ERR.value,
    'ext4_warning': LogSeverity.WARNING.value,
    'ext4_msg': None,  # depends on parameter
    'ext4_error_inode': LogSeverity.ERR.value,
}


class LogExtractor:
    """
    Extract log statements from kernel C code.

    Uses tree-sitter to parse C source files and extract calls to
    the 20 core kernel logging functions.
    """

    def __init__(self):
        """Initialize the log extractor with tree-sitter parser."""
        if Parser is None:
            raise ImportError("tree-sitter or tree-sitter-c is not installed")

        self.language = Language(language())
        self.parser = Parser()
        self.parser.language = self.language
        self.log_functions = CORE_LOG_FUNCTIONS

    def extract_from_file(self, file_path: str) -> List[LogStatement]:
        """
        Extract log statements from a C source file.

        Args:
            file_path: Path to the C source file

        Returns:
            List of LogStatement objects
        """
        source_code = Path(file_path).read_text(encoding='utf-8', errors='ignore')
        return self.extract_from_code(source_code, file_path)

    def extract_from_code(self, source_code: str, file_path: str = "<unknown>") -> List[LogStatement]:
        """
        Extract log statements from C source code string.

        Args:
            source_code: C source code as string
            file_path: File path for reference in LogStatement objects

        Returns:
            List of LogStatement objects
        """
        if not source_code:
            return []

        # Parse source code
        tree = self.parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node

        if root_node.has_error:
            logger.warning(f"Parsing errors in {file_path}, AST may be incomplete")

        # Find all log statements
        log_statements = []
        self._find_log_statements(root_node, source_code, file_path, log_statements)

        logger.info(f"Extracted {len(log_statements)} log statements from {file_path}")
        return log_statements

    def _find_log_statements(
        self,
        node: Node,
        source_code: str,
        file_path: str,
        log_statements: List[LogStatement],
        current_function: Optional[str] = None,
        parent_if_statement: bool = False,
    ):
        """
        Recursively traverse AST to find log statements.

        Args:
            node: Current AST node
            source_code: Source code string
            file_path: File path for reference
            log_statements: List to collect found log statements
            current_function: Name of current function being traversed
            parent_if_statement: True if parent node is an if statement (error path indicator)
        """
        # Track function context
        if node.type == 'function_definition':
            func_name = self._extract_function_name(node)
            # Recurse into function body
            for child in node.children:
                self._find_log_statements(child, source_code, file_path, log_statements, func_name, False)
            return

        # Track if statement context (error paths)
        is_if_statement = node.type == 'if_statement'

        # Check if this node is a call expression to a log function
        if node.type == 'call_expression':
            log_stmt = self._try_extract_log_statement(node, source_code, file_path, current_function, parent_if_statement)
            if log_stmt:
                log_statements.append(log_stmt)

        # Recurse into children
        for child in node.children:
            self._find_log_statements(
                child,
                source_code,
                file_path,
                log_statements,
                current_function,
                is_if_statement,
            )

    def _try_extract_log_statement(
        self,
        node: Node,
        source_code: str,
        file_path: str,
        function_name: Optional[str],
        in_error_path: bool,
    ) -> Optional[LogStatement]:
        """
        Try to extract a log statement from a call expression node.

        Args:
            node: Call expression node
            source_code: Source code string
            file_path: File path for reference
            function_name: Name of containing function
            in_error_path: Whether this is in an error path

        Returns:
            LogStatement if this is a log function call, None otherwise
        """
        # Get function name being called
        func_node = node.children[0] if node.children else None
        if not func_node:
            return None

        called_func = self._get_node_text(func_node, source_code)

        # Check if it's a core log function
        if called_func not in self.log_functions:
            return None

        # Extract log details
        line_number = node.start_point[0] + 1  # tree-sitter uses 0-indexed lines
        log_function = called_func

        # Get severity
        severity = LOG_FUNCTION_SEVERITY.get(called_func)
        log_level = self._get_log_level(node, source_code, called_func, severity)

        # Extract format string and arguments
        format_string, arguments = self._extract_format_and_args(node, source_code)

        # Check error condition
        error_condition = None
        if in_error_path:
            # Try to get parent if condition
            error_condition = self._get_error_condition(node, source_code)

        # Create log statement ID
        log_id = f"{file_path}::{line_number}"

        return LogStatement(
            id=log_id,
            function=function_name or "<unknown>",
            file_path=file_path,
            line_number=line_number,
            log_function=log_function,
            log_level=log_level,
            severity=severity if severity is not None else 3,  # Default to ERR
            format_string=format_string,
            arguments=arguments,
            in_error_path=in_error_path,
            error_condition=error_condition,
        )

    def _extract_function_name(self, func_node: Node) -> Optional[str]:
        """Extract function name from function definition node."""
        # Function name is typically the second child (after type)
        # Navigate to the declarator
        for child in func_node.children:
            if child.type == 'function_declarator':
                # The name should be in the declarator
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        return subchild.text.decode('utf-8')
        return None

    def _get_node_text(self, node: Node, source_code: str) -> str:
        """Get text content of a node."""
        start_byte = node.start_byte
        end_byte = node.end_byte
        return source_code[start_byte:end_byte]

    def _get_log_level(self, node: Node, source_code: str, log_function: str, default_severity: Optional[int]) -> str:
        """
        Extract log level from log function call.

        For printk, this looks at the first argument (KERN_* prefix).
        For other functions, uses the predefined severity mapping.
        """
        if log_function == 'printk':
            # First argument should be format string with KERN_* prefix
            args = self._get_arguments(node, source_code)
            if args:
                first_arg = args[0]
                # Check for KERN_* prefix
                if 'KERN_EMERG' in first_arg:
                    return 'KERN_EMERG'
                elif 'KERN_ALERT' in first_arg:
                    return 'KERN_ALERT'
                elif 'KERN_CRIT' in first_arg:
                    return 'KERN_CRIT'
                elif 'KERN_ERR' in first_arg:
                    return 'KERN_ERR'
                elif 'KERN_WARNING' in first_arg:
                    return 'KERN_WARNING'
                elif 'KERN_NOTICE' in first_arg:
                    return 'KERN_NOTICE'
                elif 'KERN_INFO' in first_arg:
                    return 'KERN_INFO'
                elif 'KERN_DEBUG' in first_arg:
                    return 'KERN_DEBUG'

        # Map severity to KERN_* constant
        if default_severity is not None:
            severity_map = {
                0: 'KERN_EMERG',
                1: 'KERN_ALERT',
                2: 'KERN_CRIT',
                3: 'KERN_ERR',
                4: 'KERN_WARNING',
                5: 'KERN_NOTICE',
                6: 'KERN_INFO',
                7: 'KERN_DEBUG',
            }
            return severity_map.get(default_severity, 'KERN_ERR')

        return 'KERN_ERR'  # Default

    def _extract_format_and_args(self, node: Node, source_code: str) -> tuple[str, List[str]]:
        """
        Extract format string and arguments from log function call.

        Returns:
            Tuple of (format_string, list_of_arguments)
        """
        arguments = self._get_arguments(node, source_code)
        if not arguments:
            return "", []

        # First argument is typically the format string
        # For printk, format string might be first arg
        # For pr_* functions, format string is the only/first arg
        # For dev_* functions, first arg is device, second is format string

        format_arg_idx = 0
        if node.children and node.children[0].type == 'identifier':
            func_name = self._get_node_text(node.children[0], source_code)
            if func_name.startswith('dev_'):
                format_arg_idx = 1  # Skip device argument

        if format_arg_idx >= len(arguments):
            return "", []

        format_string = arguments[format_arg_idx]
        args = arguments[format_arg_idx + 1:]

        # Extract variable names from arguments
        # This is simplified - real implementation would need more sophisticated parsing
        variable_names = []
        for arg in args:
            # Simple heuristic: extract identifiers
            identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', arg)
            variable_names.extend(identifiers)

        return format_string, variable_names

    def _get_arguments(self, node: Node, source_code: str) -> List[str]:
        """Extract argument list from call expression."""
        # Find argument_list child
        for child in node.children:
            if child.type == 'argument_list':
                args = []
                # Extract each argument
                for grandchild in child.children:
                    if grandchild.type == ',':
                        continue
                    if grandchild.type == 'identifier' or grandchild.type == 'string_literal' or grandchild.type == 'number_literal':
                        arg_text = self._get_node_text(grandchild, source_code).strip()
                        args.append(arg_text)
                    elif grandchild.type == 'call_expression':
                        # Handle nested function calls (simplified)
                        arg_text = self._get_node_text(grandchild, source_code).strip()
                        args.append(arg_text)
                return args
        return []

    def _get_error_condition(self, node: Node, source_code: str) -> Optional[str]:
        """
        Try to extract the error condition that leads to this log.

        This looks at the parent if statement condition.
        """
        # Walk up the tree to find parent if statement
        # This is simplified - real implementation would need parent pointers
        # For now, return None
        return None
