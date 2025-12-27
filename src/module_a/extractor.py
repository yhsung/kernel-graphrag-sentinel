"""
Module A: Function and Call Extractor
Extracts functions and call relationships from parsed C code.
"""

from typing import List, Dict, Set, Tuple
from pathlib import Path
from dataclasses import dataclass
import logging

try:
    from .preprocessor import KernelPreprocessor
    from .parser import CParser
except ImportError:
    # Handle direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.module_a.preprocessor import KernelPreprocessor
    from src.module_a.parser import CParser

logger = logging.getLogger(__name__)


@dataclass
class FunctionNode:
    """Represents a function in the code."""
    name: str
    file_path: str
    line_start: int
    line_end: int
    subsystem: str
    is_static: bool = False


@dataclass
class CallEdge:
    """Represents a function call relationship."""
    caller: str  # Function name that makes the call
    callee: str  # Function name being called
    call_site_line: int
    file_path: str


class FunctionExtractor:
    """Extracts functions and call graphs from C source code."""

    def __init__(self, kernel_root: str):
        """
        Initialize the extractor.

        Args:
            kernel_root: Path to Linux kernel source root
        """
        self.kernel_root = Path(kernel_root)
        self.preprocessor = KernelPreprocessor(str(kernel_root))
        self.parser = CParser()

    def extract_from_file(self, source_file: str, subsystem: str, skip_preprocessing: bool = False) -> Tuple[List[FunctionNode], List[CallEdge]]:
        """
        Extract functions and calls from a single C file.

        Args:
            source_file: Path to C source file
            subsystem: Name of the subsystem (e.g., "ext4")
            skip_preprocessing: If True, parse raw C without preprocessing

        Returns:
            Tuple of (function_nodes, call_edges)
        """
        logger.info(f"Extracting from {source_file}")

        # Preprocess the file or read raw
        if skip_preprocessing:
            logger.info("Skipping preprocessing, parsing raw C code")
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
        else:
            try:
                code = self.preprocessor.preprocess_file(source_file)
            except Exception as e:
                logger.warning(f"Preprocessing failed for {source_file}, falling back to raw parsing: {e}")
                with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()

        # Parse the code
        try:
            root = self.parser.parse(code)
        except Exception as e:
            logger.error(f"Failed to parse {source_file}: {e}")
            return [], []

        # Extract functions
        function_nodes = self._extract_functions(root, source_file, subsystem)

        # Extract calls with context
        call_edges = self._extract_calls(root, source_file, function_nodes)

        logger.info(f"Extracted {len(function_nodes)} functions and {len(call_edges)} calls from {source_file}")
        return function_nodes, call_edges

    def _extract_functions(self, root, source_file: str, subsystem: str) -> List[FunctionNode]:
        """Extract function definitions from the AST."""
        functions = self.parser.find_functions(root)
        function_nodes = []

        for func_node, func_name in functions:
            start_line, _, end_line, _ = self.parser.get_node_location(func_node)

            # Check if function is static
            is_static = self._is_static_function(func_node)

            node = FunctionNode(
                name=func_name,
                file_path=source_file,
                line_start=start_line,
                line_end=end_line,
                subsystem=subsystem,
                is_static=is_static
            )
            function_nodes.append(node)

        return function_nodes

    def _is_static_function(self, func_node) -> bool:
        """Check if a function is declared as static."""
        # Look for 'static' storage class specifier
        func_text = self.parser.get_node_text(func_node)
        return 'static' in func_text.split('(')[0]  # Check before parameter list

    def _extract_calls(self, root, source_file: str, function_nodes: List[FunctionNode]) -> List[CallEdge]:
        """
        Extract function calls and determine which function they belong to.

        Args:
            root: AST root node
            source_file: Source file path
            function_nodes: List of functions in this file

        Returns:
            List of call edges
        """
        calls = self.parser.find_function_calls(root)
        call_edges = []

        # Build a mapping of line ranges to functions
        line_to_function = {}
        for func in function_nodes:
            for line in range(func.line_start, func.line_end + 1):
                line_to_function[line] = func.name

        # Map each call to its containing function
        for call_node, callee_name in calls:
            call_line, _, _, _ = self.parser.get_node_location(call_node)

            # Find which function this call is in
            caller_name = line_to_function.get(call_line)
            if not caller_name:
                logger.debug(f"Call to {callee_name} at line {call_line} is outside any function")
                continue

            edge = CallEdge(
                caller=caller_name,
                callee=callee_name,
                call_site_line=call_line,
                file_path=source_file
            )
            call_edges.append(edge)

        return call_edges

    def extract_from_subsystem(self, subsystem_path: str, skip_preprocessing: bool = True) -> Tuple[List[FunctionNode], List[CallEdge]]:
        """
        Extract functions and calls from all files in a subsystem.

        Args:
            subsystem_path: Relative path to subsystem (e.g., "fs/ext4")
            skip_preprocessing: If True, skip macro preprocessing (default for POC)

        Returns:
            Tuple of (all_functions, all_calls)
        """
        subsystem_dir = self.kernel_root / subsystem_path
        subsystem_name = Path(subsystem_path).name

        if not subsystem_dir.exists():
            raise ValueError(f"Subsystem directory does not exist: {subsystem_dir}")

        # Find all .c files (excluding test files)
        c_files = [
            f for f in subsystem_dir.glob("*.c")
            if not f.name.endswith("-test.c")
        ]

        logger.info(f"Processing {len(c_files)} C files in {subsystem_path}")

        all_functions = []
        all_calls = []

        for c_file in c_files:
            try:
                functions, calls = self.extract_from_file(str(c_file), subsystem_name, skip_preprocessing)
                all_functions.extend(functions)
                all_calls.extend(calls)
            except Exception as e:
                logger.warning(f"Failed to extract from {c_file}: {e}")
                continue

        logger.info(f"Extracted total: {len(all_functions)} functions, {len(all_calls)} call edges")
        return all_functions, all_calls

    def build_call_graph(self, functions: List[FunctionNode], calls: List[CallEdge]) -> Dict[str, Set[str]]:
        """
        Build a call graph from function nodes and call edges.

        Args:
            functions: List of function nodes
            calls: List of call edges

        Returns:
            Dictionary mapping function names to sets of called functions
        """
        call_graph = {func.name: set() for func in functions}

        for call in calls:
            if call.caller in call_graph:
                call_graph[call.caller].add(call.callee)
            else:
                # Caller might be an external function
                call_graph[call.caller] = {call.callee}

        return call_graph

    def get_statistics(self, functions: List[FunctionNode], calls: List[CallEdge]) -> Dict:
        """
        Get statistics about extracted code.

        Args:
            functions: List of function nodes
            calls: List of call edges

        Returns:
            Dictionary with statistics
        """
        files = {func.file_path for func in functions}
        static_funcs = [f for f in functions if f.is_static]

        call_graph = self.build_call_graph(functions, calls)
        called_functions = {call.callee for call in calls}
        uncalled_functions = [f.name for f in functions if f.name not in called_functions]

        return {
            "total_functions": len(functions),
            "static_functions": len(static_funcs),
            "exported_functions": len(functions) - len(static_funcs),
            "total_calls": len(calls),
            "unique_call_sites": len(set((c.caller, c.callee) for c in calls)),
            "files_processed": len(files),
            "uncalled_functions": len(uncalled_functions),
            "avg_calls_per_function": len(calls) / len(functions) if functions else 0,
        }


if __name__ == "__main__":
    # Example usage
    import sys
    import json

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python extractor.py <subsystem_path>")
        print("Example: python extractor.py fs/ext4")
        sys.exit(1)

    import os
    kernel_root = os.getenv("KERNEL_ROOT", "/workspaces/ubuntu/linux-6.13")
    subsystem_path = sys.argv[1]

    extractor = FunctionExtractor(kernel_root)
    functions, calls = extractor.extract_from_subsystem(subsystem_path)

    stats = extractor.get_statistics(functions, calls)

    print("\n=== Extraction Statistics ===")
    print(json.dumps(stats, indent=2))

    print("\n=== Sample Functions ===")
    for func in functions[:5]:
        print(f"{func.name} ({func.file_path}:{func.line_start}-{func.line_end})")

    print("\n=== Sample Calls ===")
    for call in calls[:10]:
        print(f"{call.caller} -> {call.callee} ({call.file_path}:{call.call_site_line})")
