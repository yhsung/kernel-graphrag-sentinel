"""
Module D: Variable Tracker
Extracts variable definitions and uses from C code AST.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Set, Tuple, Optional
from tree_sitter import Node
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.module_a.parser import CParser

logger = logging.getLogger(__name__)


@dataclass
class VariableDefinition:
    """Represents a variable definition point in code."""

    name: str
    var_type: str  # int, char*, struct inode*, etc.
    scope: str  # function name or "global"
    file_path: str
    line_number: int
    is_parameter: bool
    is_pointer: bool
    is_static: bool = False
    initializer: Optional[str] = None  # Initial value if any


@dataclass
class VariableUse:
    """Represents a variable usage point in code."""

    name: str
    usage_type: str  # "read", "write", "argument", "return"
    function: str
    file_path: str
    line_number: int
    context: str  # "assignment", "condition", "call", etc.


class VariableTracker:
    """Tracks variable definitions and uses in C code."""

    def __init__(self):
        """Initialize the variable tracker."""
        self.parser = CParser()

    def extract_from_file(
        self, source_file: str
    ) -> Tuple[List[VariableDefinition], List[VariableUse]]:
        """
        Extract all variable definitions and uses from a C file.

        Args:
            source_file: Path to C source file

        Returns:
            Tuple of (variable_definitions, variable_uses)
        """
        logger.info(f"Extracting variables from {source_file}")

        # Read and parse file
        with open(source_file, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        root = self.parser.parse(code)

        # Extract global variables
        global_defs = self._extract_global_variables(root, source_file, code)

        # Extract from each function
        function_defs = []
        function_uses = []

        functions = self.parser.find_functions(root)

        for func_node, func_name in functions:
            # Extract function parameters
            params = self._extract_function_parameters(
                func_node, func_name, source_file, code
            )
            function_defs.extend(params)

            # Extract local variables
            locals_defs = self._extract_local_variables(
                func_node, func_name, source_file, code
            )
            function_defs.extend(locals_defs)

            # Extract variable uses
            uses = self._extract_variable_uses(func_node, func_name, source_file, code)
            function_uses.extend(uses)

        all_defs = global_defs + function_defs

        logger.info(
            f"Extracted {len(all_defs)} variable definitions and {len(function_uses)} uses"
        )

        return all_defs, function_uses

    def _extract_global_variables(
        self, root: Node, file_path: str, code: str
    ) -> List[VariableDefinition]:
        """Extract global variable declarations."""
        global_vars = []

        # Find top-level declarations
        for child in root.children:
            if child.type == "declaration":
                vars_in_decl = self._parse_declaration(child, "global", file_path, code)
                global_vars.extend(vars_in_decl)

        return global_vars

    def _extract_function_parameters(
        self, func_node: Node, func_name: str, file_path: str, code: str
    ) -> List[VariableDefinition]:
        """Extract function parameters as variable definitions."""
        parameters = []

        # Find parameter list
        param_list = self._find_parameter_list(func_node)
        if not param_list:
            return parameters

        # Parse each parameter
        for param_node in param_list.children:
            if param_node.type == "parameter_declaration":
                param_def = self._parse_parameter(
                    param_node, func_name, file_path, code
                )
                if param_def:
                    parameters.append(param_def)

        return parameters

    def _extract_local_variables(
        self, func_node: Node, func_name: str, file_path: str, code: str
    ) -> List[VariableDefinition]:
        """Extract local variable declarations within a function."""
        local_vars = []

        # Find function body
        body = self._find_function_body(func_node)
        if not body:
            return local_vars

        # Traverse body for declarations
        def traverse(node):
            if node.type == "declaration":
                vars_in_decl = self._parse_declaration(node, func_name, file_path, code)
                local_vars.extend(vars_in_decl)

            for child in node.children:
                traverse(child)

        traverse(body)

        return local_vars

    def _extract_variable_uses(
        self, func_node: Node, func_name: str, file_path: str, code: str
    ) -> List[VariableUse]:
        """Extract all variable uses within a function."""
        uses = []

        # Find function body
        body = self._find_function_body(func_node)
        if not body:
            return uses

        # Traverse for variable references
        def traverse(node, context="expression"):
            # Assignment left side = write
            if node.type == "assignment_expression":
                left = node.child_by_field_name("left")
                if left:
                    var_uses = self._extract_variables_from_node(
                        left, func_name, file_path, code, "write", "assignment"
                    )
                    uses.extend(var_uses)

                # Right side = read
                right = node.child_by_field_name("right")
                if right:
                    var_uses = self._extract_variables_from_node(
                        right, func_name, file_path, code, "read", "assignment"
                    )
                    uses.extend(var_uses)

            # Function call arguments = read
            elif node.type == "call_expression":
                for child in node.children:
                    if child.type == "argument_list":
                        for arg in child.children:
                            var_uses = self._extract_variables_from_node(
                                arg, func_name, file_path, code, "argument", "call"
                            )
                            uses.extend(var_uses)

            # Return statement = read
            elif node.type == "return_statement":
                for child in node.children:
                    var_uses = self._extract_variables_from_node(
                        child, func_name, file_path, code, "return", "return"
                    )
                    uses.extend(var_uses)

            # Continue traversal
            for child in node.children:
                traverse(child, context)

        traverse(body)

        return uses

    def _extract_variables_from_node(
        self,
        node: Node,
        function: str,
        file_path: str,
        code: str,
        usage_type: str,
        context: str,
    ) -> List[VariableUse]:
        """Extract all variable identifiers from an expression node."""
        variables = []

        def traverse(n):
            if n.type == "identifier":
                var_name = code[n.start_byte : n.end_byte]
                # Skip if it's a function name (simple heuristic)
                if not self._is_likely_function_call(n):
                    variables.append(
                        VariableUse(
                            name=var_name,
                            usage_type=usage_type,
                            function=function,
                            file_path=file_path,
                            line_number=n.start_point[0] + 1,
                            context=context,
                        )
                    )

            for child in n.children:
                traverse(child)

        traverse(node)
        return variables

    def _parse_declaration(
        self, decl_node: Node, scope: str, file_path: str, code: str
    ) -> List[VariableDefinition]:
        """Parse a variable declaration node."""
        variables = []

        # Get type specifiers
        var_type = self._extract_type(decl_node, code)
        is_static = self._is_static_declaration(decl_node, code)

        # Find declarators (actual variable names)
        for child in decl_node.children:
            if "declarator" in child.type:
                var_def = self._parse_declarator(
                    child, var_type, scope, file_path, code, is_static
                )
                if var_def:
                    variables.append(var_def)

        return variables

    def _parse_parameter(
        self, param_node: Node, func_name: str, file_path: str, code: str
    ) -> Optional[VariableDefinition]:
        """Parse a function parameter declaration."""
        var_type = self._extract_type(param_node, code)

        # Find declarator for parameter name
        declarator = None
        for child in param_node.children:
            if "declarator" in child.type:
                declarator = child
                break

        if not declarator:
            return None

        var_name = self._extract_variable_name(declarator, code)
        is_pointer = self._is_pointer_type(declarator, code)

        return VariableDefinition(
            name=var_name,
            var_type=var_type,
            scope=func_name,
            file_path=file_path,
            line_number=param_node.start_point[0] + 1,
            is_parameter=True,
            is_pointer=is_pointer,
        )

    def _parse_declarator(
        self,
        declarator_node: Node,
        var_type: str,
        scope: str,
        file_path: str,
        code: str,
        is_static: bool,
    ) -> Optional[VariableDefinition]:
        """Parse a declarator to extract variable name and properties."""
        var_name = self._extract_variable_name(declarator_node, code)
        if not var_name:
            return None

        is_pointer = self._is_pointer_type(declarator_node, code)

        # Check for initializer
        initializer = None
        parent = declarator_node.parent
        if parent and parent.type == "init_declarator":
            init_node = parent.child_by_field_name("value")
            if init_node:
                initializer = code[init_node.start_byte : init_node.end_byte]

        return VariableDefinition(
            name=var_name,
            var_type=var_type,
            scope=scope,
            file_path=file_path,
            line_number=declarator_node.start_point[0] + 1,
            is_parameter=False,
            is_pointer=is_pointer,
            is_static=is_static,
            initializer=initializer,
        )

    def _extract_type(self, node: Node, code: str) -> str:
        """Extract type from declaration node."""
        type_parts = []

        for child in node.children:
            if child.type in [
                "type_qualifier",
                "storage_class_specifier",
                "primitive_type",
                "struct_specifier",
                "type_identifier",
            ]:
                type_parts.append(code[child.start_byte : child.end_byte])

        return " ".join(type_parts) if type_parts else "unknown"

    def _extract_variable_name(self, declarator_node: Node, code: str) -> str:
        """Extract variable name from declarator."""
        # Handle different declarator types
        if declarator_node.type == "identifier":
            return code[declarator_node.start_byte : declarator_node.end_byte]

        # Pointer declarator
        if declarator_node.type == "pointer_declarator":
            # Find identifier within
            for child in declarator_node.children:
                name = self._extract_variable_name(child, code)
                if name:
                    return name

        # Array declarator
        if declarator_node.type == "array_declarator":
            declarator = declarator_node.child_by_field_name("declarator")
            if declarator:
                return self._extract_variable_name(declarator, code)

        # Function declarator (for function pointers)
        if declarator_node.type == "function_declarator":
            declarator = declarator_node.child_by_field_name("declarator")
            if declarator:
                return self._extract_variable_name(declarator, code)

        # Recursively search children
        for child in declarator_node.children:
            if child.type == "identifier":
                return code[child.start_byte : child.end_byte]
            name = self._extract_variable_name(child, code)
            if name:
                return name

        return ""

    def _is_pointer_type(self, declarator_node: Node, code: str) -> bool:
        """Check if declarator represents a pointer type."""
        if declarator_node.type == "pointer_declarator":
            return True

        # Check for * in type
        text = code[declarator_node.start_byte : declarator_node.end_byte]
        return "*" in text

    def _is_static_declaration(self, decl_node: Node, code: str) -> bool:
        """Check if declaration has static storage class."""
        for child in decl_node.children:
            if child.type == "storage_class_specifier":
                text = code[child.start_byte : child.end_byte]
                if text == "static":
                    return True
        return False

    def _is_likely_function_call(self, identifier_node: Node) -> bool:
        """Heuristic to check if identifier is a function being called."""
        # Check if parent is call_expression
        parent = identifier_node.parent
        if parent and parent.type == "call_expression":
            # Check if this identifier is the function name
            func_node = parent.child_by_field_name("function")
            return func_node == identifier_node
        return False

    def _find_parameter_list(self, func_node: Node) -> Optional[Node]:
        """Find parameter list in function definition."""
        # Look for function_declarator
        for child in func_node.children:
            if child.type == "function_declarator":
                param_list = child.child_by_field_name("parameters")
                return param_list

        return None

    def _find_function_body(self, func_node: Node) -> Optional[Node]:
        """Find function body (compound_statement)."""
        for child in func_node.children:
            if child.type == "compound_statement":
                return child
        return None
