"""Unit tests for Module A: C Parser (parser.py)."""

import pytest
from tree_sitter import Node

from src.module_a.parser import CParser


class TestCParser:
    """Test cases for CParser class."""

    def test_init(self):
        """Test parser initialization."""
        parser = CParser()
        assert parser.parser is not None
        assert parser.language is not None

    def test_parse_simple_function(self):
        """Test parsing a simple C function."""
        parser = CParser()
        code = """
        int main(void) {
            return 0;
        }
        """
        root = parser.parse(code)
        assert root is not None
        assert isinstance(root, Node)
        assert not root.has_error

    def test_parse_empty_code_raises_error(self):
        """Test that parsing empty code raises ValueError."""
        parser = CParser()
        with pytest.raises(ValueError, match="Source code is empty"):
            parser.parse("")

    def test_parse_with_errors(self):
        """Test parsing code with syntax errors."""
        parser = CParser()
        # Invalid C syntax
        code = "int function( { }"
        root = parser.parse(code)
        assert root is not None
        # Parser should still return a tree, even with errors

    def test_parse_kernel_style_function(self, sample_c_file):
        """Test parsing kernel-style C code."""
        parser = CParser()
        with open(sample_c_file, 'r') as f:
            code = f.read()

        root = parser.parse(code)
        assert root is not None
        assert not root.has_error

    def test_find_functions(self, sample_c_file):
        """Test finding function definitions in parsed code."""
        parser = CParser()
        with open(sample_c_file, 'r') as f:
            code = f.read()

        root = parser.parse(code)
        functions = parser.find_functions(root)

        # Should find all functions in sample_kernel.c
        assert len(functions) >= 5
        function_names = [name for _, name in functions]

        assert "top_level_function" in function_names
        assert "helper_function" in function_names
        assert "cleanup_resource" in function_names
        assert "standalone_function" in function_names
        assert "multi_caller" in function_names

    def test_find_functions_empty_file(self):
        """Test finding functions in code with no functions."""
        parser = CParser()
        code = """
        #define MAX_SIZE 100
        int global_var = 0;
        """
        root = parser.parse(code)
        functions = parser.find_functions(root)
        assert len(functions) == 0

    def test_extract_function_name(self):
        """Test extracting function name from AST node."""
        parser = CParser()
        code = """
        int test_function(int param) {
            return param * 2;
        }
        """
        root = parser.parse(code)
        functions = parser.find_functions(root)

        assert len(functions) == 1
        node, name = functions[0]
        assert name == "test_function"

    def test_find_call_expressions(self, sample_c_file):
        """Test finding call expressions in parsed code."""
        parser = CParser()
        with open(sample_c_file, 'r') as f:
            code = f.read()

        root = parser.parse(code)
        calls = parser.find_call_expressions(root)

        # Should find multiple function calls
        assert len(calls) > 0

        # Extract called function names
        call_names = [parser._extract_call_name(node) for node in calls]
        call_names = [name for name in call_names if name]

        # Verify expected calls exist
        assert "helper_function" in call_names
        assert "cleanup_resource" in call_names

    def test_traverse(self):
        """Test AST traversal."""
        parser = CParser()
        code = """
        int add(int a, int b) {
            return a + b;
        }
        """
        root = parser.parse(code)

        nodes = list(parser._traverse(root))
        assert len(nodes) > 1  # Should have multiple nodes
        assert nodes[0] == root  # First node should be root

    def test_parse_multiple_functions(self):
        """Test parsing file with multiple functions."""
        parser = CParser()
        code = """
        int func1(void) { return 1; }
        int func2(void) { return 2; }
        static int func3(void) { return 3; }
        """
        root = parser.parse(code)
        functions = parser.find_functions(root)

        assert len(functions) == 3
        names = [name for _, name in functions]
        assert "func1" in names
        assert "func2" in names
        assert "func3" in names

    def test_parse_with_includes(self):
        """Test parsing code with include directives."""
        parser = CParser()
        code = """
        #include <stdio.h>
        #include <stdlib.h>

        int main(void) {
            printf("Hello\\n");
            return 0;
        }
        """
        root = parser.parse(code)
        assert root is not None
        functions = parser.find_functions(root)
        assert len(functions) == 1

    def test_parse_with_macros(self):
        """Test parsing code with macro definitions."""
        parser = CParser()
        code = """
        #define MAX_VALUE 100
        #define MIN(a, b) ((a) < (b) ? (a) : (b))

        int get_value(void) {
            return MAX_VALUE;
        }
        """
        root = parser.parse(code)
        functions = parser.find_functions(root)
        assert len(functions) == 1

    def test_parse_static_functions(self):
        """Test parsing static functions."""
        parser = CParser()
        code = """
        static int helper(int x) {
            return x * 2;
        }

        int public_func(int y) {
            return helper(y);
        }
        """
        root = parser.parse(code)
        functions = parser.find_functions(root)
        assert len(functions) == 2

    def test_parse_function_pointers(self):
        """Test parsing code with function pointers."""
        parser = CParser()
        code = """
        typedef int (*callback_t)(int);

        int apply(callback_t func, int value) {
            return func(value);
        }
        """
        root = parser.parse(code)
        functions = parser.find_functions(root)
        assert len(functions) >= 1

    def test_parse_nested_calls(self):
        """Test parsing nested function calls."""
        parser = CParser()
        code = """
        int outer(int a) {
            return inner(middle(a));
        }
        """
        root = parser.parse(code)
        calls = parser.find_call_expressions(root)
        assert len(calls) >= 2  # Should find both inner() and middle()
