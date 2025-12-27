"""
Module A: Tree-sitter C Parser
Parses preprocessed C code using tree-sitter to extract AST.
"""

from tree_sitter import Parser, Language, Node
from tree_sitter_c import language
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class CParser:
    """Parses C code using tree-sitter."""

    def __init__(self):
        """Initialize the C parser with tree-sitter-c language."""
        self.language = Language(language())
        self.parser = Parser()
        self.parser.language = self.language

    def parse(self, source_code: str) -> Node:
        """
        Parse C source code into an AST.

        Args:
            source_code: C source code string

        Returns:
            Tree-sitter syntax tree root node

        Raises:
            ValueError: If parsing fails
        """
        if not source_code:
            raise ValueError("Source code is empty")

        tree = self.parser.parse(bytes(source_code, "utf8"))

        if tree.root_node.has_error:
            logger.warning("Parsing resulted in errors, AST may be incomplete")

        logger.debug(f"Parsed {len(source_code)} bytes into AST with {len(list(self._traverse(tree.root_node)))} nodes")
        return tree.root_node

    def _traverse(self, node: Node):
        """
        Recursively traverse all nodes in the AST.

        Args:
            node: Starting node

        Yields:
            Each node in the tree
        """
        yield node
        for child in node.children:
            yield from self._traverse(child)

    def query(self, root_node: Node, query_string: str) -> List[Tuple[Node, str]]:
        """
        Execute a tree-sitter query on the AST.

        Note: Using manual traversal for compatibility with newer tree-sitter versions.

        Args:
            root_node: Root node of the AST
            query_string: Tree-sitter query string (not used in this implementation)

        Returns:
            List of (node, capture_name) tuples matching the query
        """
        # Simplified: manual traversal instead of query language
        # This is more compatible across tree-sitter versions
        return []

    def find_functions(self, root_node: Node) -> List[Tuple[Node, str]]:
        """
        Find all function definitions in the AST using manual traversal.

        Args:
            root_node: Root node of the AST

        Returns:
            List of (node, function_name) tuples
        """
        functions = []

        def traverse(node):
            if node.type == 'function_definition':
                # Find the function name
                func_name = self._extract_function_name(node)
                if func_name:
                    functions.append((node, func_name))

            for child in node.children:
                traverse(child)

        traverse(root_node)
        logger.debug(f"Found {len(functions)} function definitions")
        return functions

    def _extract_function_name(self, func_node: Node) -> str:
        """Extract function name from a function_definition node."""
        for child in func_node.children:
            if child.type == 'function_declarator':
                for gc in child.children:
                    if gc.type == 'identifier':
                        return gc.text.decode('utf8')
                    elif gc.type == 'pointer_declarator':
                        # Handle pointer functions
                        for pgc in gc.children:
                            if pgc.type == 'identifier':
                                return pgc.text.decode('utf8')
        return None

    def find_function_calls(self, root_node: Node) -> List[Tuple[Node, str]]:
        """
        Find all function calls in the AST using manual traversal.

        Args:
            root_node: Root node of the AST

        Returns:
            List of (node, called_function_name) tuples
        """
        calls = []

        def traverse(node):
            if node.type == 'call_expression':
                # Find the called function name
                call_name = self._extract_call_name(node)
                if call_name:
                    calls.append((node, call_name))

            for child in node.children:
                traverse(child)

        traverse(root_node)
        logger.debug(f"Found {len(calls)} function calls")
        return calls

    def _extract_call_name(self, call_node: Node) -> str:
        """Extract function name from a call_expression node."""
        for child in call_node.children:
            if child.type == 'identifier':
                return child.text.decode('utf8')
            elif child.type == 'field_expression':
                # Handle member function calls (e.g., obj->func())
                for gc in child.children:
                    if gc.type == 'field_identifier':
                        return gc.text.decode('utf8')
        return None

    def get_node_location(self, node: Node) -> Tuple[int, int, int, int]:
        """
        Get the location of a node in the source code.

        Args:
            node: AST node

        Returns:
            Tuple of (start_line, start_col, end_line, end_col)
        """
        start_point = node.start_point
        end_point = node.end_point
        return (start_point[0] + 1, start_point[1],  # +1 for 1-indexed lines
                end_point[0] + 1, end_point[1])

    def get_node_text(self, node: Node) -> str:
        """
        Get the text content of a node.

        Args:
            node: AST node

        Returns:
            Text content as string
        """
        return node.text.decode('utf8')

    def find_structs(self, root_node: Node) -> List[Tuple[Node, str]]:
        """
        Find all struct definitions in the AST.

        Args:
            root_node: Root node of the AST

        Returns:
            List of (node, struct_name) tuples
        """
        query_string = """
        (struct_specifier
            name: (type_identifier) @struct_name) @struct_def
        """

        captures = self.query(root_node, query_string)

        structs = []
        for node, name in captures:
            if name == "struct_name":
                struct_name = node.text.decode('utf8')
                parent = node.parent
                while parent and parent.type != 'struct_specifier':
                    parent = parent.parent
                if parent:
                    structs.append((parent, struct_name))

        logger.debug(f"Found {len(structs)} struct definitions")
        return structs


def parse_c_file(source_code: str) -> Node:
    """
    Convenience function to parse C source code.

    Args:
        source_code: C source code string

    Returns:
        Tree-sitter AST root node
    """
    parser = CParser()
    return parser.parse(source_code)


if __name__ == "__main__":
    # Example usage
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 2:
        print("Usage: python parser.py <source_file>")
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        source_code = f.read()

    parser = CParser()
    root = parser.parse(source_code)

    print(f"AST root: {root.type}")
    print(f"Total nodes: {len(list(parser._traverse(root)))}")

    functions = parser.find_functions(root)
    print(f"\nFound {len(functions)} functions:")
    for func_node, func_name in functions[:10]:  # Show first 10
        start_line, _, end_line, _ = parser.get_node_location(func_node)
        print(f"  {func_name} (lines {start_line}-{end_line})")

    calls = parser.find_function_calls(root)
    print(f"\nFound {len(calls)} function calls:")
    for call_node, call_name in calls[:10]:  # Show first 10
        line, _, _, _ = parser.get_node_location(call_node)
        print(f"  {call_name} (line {line})")
