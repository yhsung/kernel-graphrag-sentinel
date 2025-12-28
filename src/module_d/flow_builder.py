"""
Module D: Flow Builder
Builds data flow graphs from variable definitions and uses.
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
from src.module_d.variable_tracker import VariableDefinition, VariableUse
from src.module_d.flow_schema import FlowType

logger = logging.getLogger(__name__)


@dataclass
class DataFlowEdge:
    """Represents data flowing from one variable to another within a function."""

    from_var: str  # Variable name
    to_var: str  # Variable name
    flow_type: FlowType
    function: str
    file_path: str
    line_number: int
    confidence: float = 1.0  # 0.0 to 1.0


@dataclass
class InterProcFlow:
    """Data flow between function calls (parameter passing and returns)."""

    caller_var: str
    caller_function: str
    callee_param: str
    callee_function: str
    argument_position: int
    file_path: str
    line_number: int


class FlowBuilder:
    """Builds data flow graphs from parsed C code."""

    def __init__(self):
        """Initialize the flow builder."""
        self.parser = CParser()

    def build_intra_procedural_flows(
        self, source_file: str
    ) -> Tuple[List[DataFlowEdge], Dict[str, List[str]]]:
        """
        Build data flow edges within each function (intra-procedural).

        Args:
            source_file: Path to C source file

        Returns:
            Tuple of (data_flow_edges, def_use_chains)
            def_use_chains: Dict mapping variable name to list of uses
        """
        logger.info(f"Building intra-procedural flows for {source_file}")

        # Read and parse file
        with open(source_file, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        root = self.parser.parse(code)

        all_flows = []
        all_def_use = {}

        # Process each function
        functions = self.parser.find_functions(root)

        for func_node, func_name in functions:
            flows, def_use = self._extract_function_flows(
                func_node, func_name, source_file, code
            )
            all_flows.extend(flows)
            all_def_use[func_name] = def_use

        logger.info(f"Built {len(all_flows)} intra-procedural flow edges")

        return all_flows, all_def_use

    def build_inter_procedural_flows(
        self, source_file: str, call_graph: Dict[str, List[str]]
    ) -> List[InterProcFlow]:
        """
        Build data flow edges across function boundaries (inter-procedural).

        Args:
            source_file: Path to C source file
            call_graph: Dict mapping function names to list of called functions

        Returns:
            List of inter-procedural flow edges
        """
        logger.info(f"Building inter-procedural flows for {source_file}")

        # Read and parse file
        with open(source_file, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        root = self.parser.parse(code)

        inter_flows = []

        # Process each function
        functions = self.parser.find_functions(root)

        for func_node, func_name in functions:
            flows = self._extract_call_flows(func_node, func_name, source_file, code)
            inter_flows.extend(flows)

        logger.info(f"Built {len(inter_flows)} inter-procedural flow edges")

        return inter_flows

    def _extract_function_flows(
        self, func_node: Node, func_name: str, file_path: str, code: str
    ) -> Tuple[List[DataFlowEdge], Dict[str, List[str]]]:
        """
        Extract data flow edges within a single function.

        Handles:
        - Assignments: a = b  →  FLOWS: b → a
        - Complex expressions: a = b + c  →  FLOWS: b → a, c → a
        - Return statements: return x  →  FLOWS: x → RETURN

        Returns:
            Tuple of (flow_edges, def_use_chains)
        """
        flows = []
        def_use_chains = {}

        # Find function body
        body = self._find_function_body(func_node)
        if not body:
            return flows, def_use_chains

        # Traverse body for assignments
        def traverse(node):
            # Assignment expression: left = right
            if node.type == "assignment_expression":
                flow_edges = self._handle_assignment(node, func_name, file_path, code)
                flows.extend(flow_edges)

            # Declaration with initializer: int x = value
            elif node.type == "init_declarator":
                flow_edge = self._handle_initializer(node, func_name, file_path, code)
                if flow_edge:
                    flows.append(flow_edge)

            # Return statement: return value
            elif node.type == "return_statement":
                flow_edges = self._handle_return(node, func_name, file_path, code)
                flows.extend(flow_edges)

            # Recursively traverse children
            for child in node.children:
                traverse(child)

        traverse(body)

        return flows, def_use_chains

    def _handle_assignment(
        self, assign_node: Node, func_name: str, file_path: str, code: str
    ) -> List[DataFlowEdge]:
        """
        Handle assignment expression: left = right

        Creates FLOWS edges: each variable on right → left variable
        """
        flows = []

        left = assign_node.child_by_field_name("left")
        right = assign_node.child_by_field_name("right")

        if not left or not right:
            return flows

        # Extract left side variable name
        left_var = self._extract_simple_variable_name(left, code)
        if not left_var:
            return flows

        # Extract all variables on right side
        right_vars = self._extract_all_variables(right, code)

        # Create flow edges: right_var → left_var
        for right_var in right_vars:
            flows.append(
                DataFlowEdge(
                    from_var=right_var,
                    to_var=left_var,
                    flow_type=FlowType.ASSIGNMENT,
                    function=func_name,
                    file_path=file_path,
                    line_number=assign_node.start_point[0] + 1,
                    confidence=1.0,
                )
            )

        return flows

    def _handle_initializer(
        self, init_decl_node: Node, func_name: str, file_path: str, code: str
    ) -> Optional[DataFlowEdge]:
        """
        Handle variable initialization: int x = value

        Creates FLOW edge: value → x
        """
        # Get declarator (variable name)
        declarator = init_decl_node.child_by_field_name("declarator")
        if not declarator:
            return None

        var_name = self._extract_simple_variable_name(declarator, code)
        if not var_name:
            return None

        # Get initializer value
        value = init_decl_node.child_by_field_name("value")
        if not value:
            return None

        # Extract variables from initializer
        init_vars = self._extract_all_variables(value, code)

        if init_vars:
            # For simplicity, take first variable (could be multiple)
            return DataFlowEdge(
                from_var=init_vars[0],
                to_var=var_name,
                flow_type=FlowType.ASSIGNMENT,
                function=func_name,
                file_path=file_path,
                line_number=init_decl_node.start_point[0] + 1,
                confidence=0.9 if len(init_vars) > 1 else 1.0,
            )

        return None

    def _handle_return(
        self, return_node: Node, func_name: str, file_path: str, code: str
    ) -> List[DataFlowEdge]:
        """
        Handle return statement: return value

        Creates FLOW edges: value_vars → RETURN
        """
        flows = []

        # Find return expression
        for child in return_node.children:
            if child.type != "return":
                # Extract variables from return expression
                ret_vars = self._extract_all_variables(child, code)

                for var in ret_vars:
                    flows.append(
                        DataFlowEdge(
                            from_var=var,
                            to_var="__RETURN__",  # Special marker for return value
                            flow_type=FlowType.RETURN,
                            function=func_name,
                            file_path=file_path,
                            line_number=return_node.start_point[0] + 1,
                            confidence=1.0,
                        )
                    )

        return flows

    def _extract_call_flows(
        self, func_node: Node, func_name: str, file_path: str, code: str
    ) -> List[InterProcFlow]:
        """
        Extract inter-procedural flows from function calls.

        Example:
        result = process_data(buffer, size);

        Creates flows:
        - buffer → process_data::param0
        - size → process_data::param1
        """
        flows = []

        # Find function body
        body = self._find_function_body(func_node)
        if not body:
            return flows

        # Traverse for call expressions
        def traverse(node):
            if node.type == "call_expression":
                call_flows = self._handle_call_expression(
                    node, func_name, file_path, code
                )
                flows.extend(call_flows)

            for child in node.children:
                traverse(child)

        traverse(body)

        return flows

    def _handle_call_expression(
        self, call_node: Node, caller_func: str, file_path: str, code: str
    ) -> List[InterProcFlow]:
        """Handle a function call expression to extract parameter flows."""
        flows = []

        # Get callee function name
        func_name_node = call_node.child_by_field_name("function")
        if not func_name_node:
            return flows

        callee_name = code[func_name_node.start_byte : func_name_node.end_byte]

        # Get arguments
        arg_list = call_node.child_by_field_name("arguments")
        if not arg_list:
            return flows

        # Process each argument
        arg_position = 0
        for child in arg_list.children:
            if child.type not in ["(", ")", ","]:
                # Extract variables from this argument
                arg_vars = self._extract_all_variables(child, code)

                for var in arg_vars:
                    flows.append(
                        InterProcFlow(
                            caller_var=var,
                            caller_function=caller_func,
                            callee_param=f"param{arg_position}",
                            callee_function=callee_name,
                            argument_position=arg_position,
                            file_path=file_path,
                            line_number=call_node.start_point[0] + 1,
                        )
                    )

                arg_position += 1

        return flows

    def _extract_all_variables(self, node: Node, code: str) -> List[str]:
        """
        Extract all variable identifiers from an expression.

        Recursively traverses the AST to find all identifiers.
        Filters out function names (simple heuristic).
        """
        variables = []

        def traverse(n):
            if n.type == "identifier":
                var_name = code[n.start_byte : n.end_byte]

                # Simple heuristic: skip if parent is a call_expression function
                parent = n.parent
                if parent and parent.type == "call_expression":
                    func_node = parent.child_by_field_name("function")
                    if func_node == n:
                        # This identifier is the function being called, skip it
                        return

                variables.append(var_name)

            for child in n.children:
                traverse(child)

        traverse(node)

        # Remove duplicates while preserving order
        seen = set()
        unique_vars = []
        for var in variables:
            if var not in seen:
                seen.add(var)
                unique_vars.append(var)

        return unique_vars

    def _extract_simple_variable_name(self, node: Node, code: str) -> Optional[str]:
        """
        Extract variable name from a simple node.

        Handles:
        - identifier
        - pointer dereference (*x)
        - array access (arr[i])
        - field access (s.field)
        """
        if node.type == "identifier":
            return code[node.start_byte : node.end_byte]

        # Pointer dereference
        if node.type == "pointer_expression":
            # Get the operand
            operand = node.child_by_field_name("argument")
            if operand:
                return self._extract_simple_variable_name(operand, code)

        # Array subscript
        if node.type == "subscript_expression":
            # Get the array name
            array_node = node.child_by_field_name("argument")
            if array_node and array_node.type == "identifier":
                return code[array_node.start_byte : array_node.end_byte]

        # Field access
        if node.type == "field_expression":
            # For now, return the full field access as variable name
            return code[node.start_byte : node.end_byte]

        return None

    def _find_function_body(self, func_node: Node) -> Optional[Node]:
        """Find function body (compound_statement)."""
        for child in func_node.children:
            if child.type == "compound_statement":
                return child
        return None
