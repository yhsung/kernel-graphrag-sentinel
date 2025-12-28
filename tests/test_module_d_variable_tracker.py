"""Unit tests for Module D: Variable Tracker."""

import pytest
from pathlib import Path

from src.module_d.variable_tracker import (
    VariableTracker,
    VariableDefinition,
    VariableUse,
)


class TestVariableDefinition:
    """Test cases for VariableDefinition dataclass."""

    def test_create_variable_definition(self):
        """Test creating a variable definition."""
        var_def = VariableDefinition(
            name="inode",
            var_type="struct inode*",
            scope="ext4_iget",
            file_path="fs/ext4/inode.c",
            line_number=4520,
            is_parameter=True,
            is_pointer=True,
        )

        assert var_def.name == "inode"
        assert var_def.var_type == "struct inode*"
        assert var_def.scope == "ext4_iget"
        assert var_def.is_parameter is True
        assert var_def.is_pointer is True

    def test_variable_definition_defaults(self):
        """Test variable definition with default values."""
        var_def = VariableDefinition(
            name="x",
            var_type="int",
            scope="foo",
            file_path="test.c",
            line_number=10,
            is_parameter=False,
            is_pointer=False,
        )

        assert var_def.is_static is False
        assert var_def.initializer is None


class TestVariableUse:
    """Test cases for VariableUse dataclass."""

    def test_create_variable_use(self):
        """Test creating a variable use."""
        var_use = VariableUse(
            name="buffer",
            usage_type="argument",
            function="process_data",
            file_path="test.c",
            line_number=42,
            context="call",
        )

        assert var_use.name == "buffer"
        assert var_use.usage_type == "argument"
        assert var_use.function == "process_data"
        assert var_use.context == "call"


class TestVariableTracker:
    """Test cases for VariableTracker class."""

    def test_init(self):
        """Test tracker initialization."""
        tracker = VariableTracker()
        assert tracker.parser is not None

    def test_extract_from_sample_file(self, sample_c_file):
        """Test extracting variables from sample kernel C file."""
        tracker = VariableTracker()

        definitions, uses = tracker.extract_from_file(str(sample_c_file))

        # Should find variable definitions
        assert len(definitions) > 0

        # Should find variable uses
        assert len(uses) > 0

        # Check that we found some parameters
        params = [v for v in definitions if v.is_parameter]
        assert len(params) > 0

    def test_extract_function_parameters(self, temp_dir):
        """Test extracting function parameters."""
        tracker = VariableTracker()

        test_file = temp_dir / "params.c"
        test_file.write_text("""
        int process(int count, char *buffer, struct data *ptr) {
            return count;
        }
        """)

        definitions, _ = tracker.extract_from_file(str(test_file))

        # Should find 3 parameters
        params = [v for v in definitions if v.is_parameter]
        assert len(params) == 3

        # Check parameter names
        param_names = {p.name for p in params}
        assert "count" in param_names
        assert "buffer" in param_names
        assert "ptr" in param_names

        # Check pointer detection
        buffer_param = next(p for p in params if p.name == "buffer")
        assert buffer_param.is_pointer is True

        ptr_param = next(p for p in params if p.name == "ptr")
        assert ptr_param.is_pointer is True

    def test_extract_local_variables(self, temp_dir):
        """Test extracting local variable declarations."""
        tracker = VariableTracker()

        test_file = temp_dir / "locals.c"
        test_file.write_text("""
        int function(void) {
            int x = 10;
            char *str;
            struct data d;
            return x;
        }
        """)

        definitions, _ = tracker.extract_from_file(str(test_file))

        # Should find local variables (not parameters)
        locals_vars = [v for v in definitions if not v.is_parameter]
        assert len(locals_vars) >= 3

        # Check variable names
        var_names = {v.name for v in locals_vars}
        assert "x" in var_names
        assert "str" in var_names
        assert "d" in var_names

    def test_extract_global_variables(self, temp_dir):
        """Test extracting global variable declarations."""
        tracker = VariableTracker()

        test_file = temp_dir / "globals.c"
        test_file.write_text("""
        int global_counter = 0;
        static int file_local = 42;
        char *global_string;

        int function(void) {
            return global_counter;
        }
        """)

        definitions, _ = tracker.extract_from_file(str(test_file))

        # Should find global variables
        globals_vars = [v for v in definitions if v.scope == "global"]
        assert len(globals_vars) >= 3

        # Check static detection
        static_vars = [v for v in globals_vars if v.is_static]
        assert len(static_vars) >= 1

    def test_extract_variable_uses_assignment(self, temp_dir):
        """Test extracting variable uses in assignments."""
        tracker = VariableTracker()

        test_file = temp_dir / "uses.c"
        test_file.write_text("""
        int function(int a, int b) {
            int c = a + b;
            return c;
        }
        """)

        _, uses = tracker.extract_from_file(str(test_file))

        # Should find uses of a, b, c
        assert len(uses) > 0

        var_names = {u.name for u in uses}
        assert "a" in var_names
        assert "b" in var_names
        assert "c" in var_names

    def test_extract_variable_uses_function_call(self, temp_dir):
        """Test extracting variable uses in function calls."""
        tracker = VariableTracker()

        test_file = temp_dir / "calls.c"
        test_file.write_text("""
        int process(int data);

        int function(int x) {
            return process(x);
        }
        """)

        _, uses = tracker.extract_from_file(str(test_file))

        # Should find x used as argument
        arg_uses = [u for u in uses if u.usage_type == "argument"]
        assert len(arg_uses) > 0

        x_uses = [u for u in arg_uses if u.name == "x"]
        assert len(x_uses) > 0

    def test_extract_variable_uses_return(self, temp_dir):
        """Test extracting variable uses in return statements."""
        tracker = VariableTracker()

        test_file = temp_dir / "returns.c"
        test_file.write_text("""
        int function(int result) {
            return result;
        }
        """)

        _, uses = tracker.extract_from_file(str(test_file))

        # Should find result in return statement
        return_uses = [u for u in uses if u.usage_type == "return"]
        assert len(return_uses) > 0

        result_uses = [u for u in return_uses if u.name == "result"]
        assert len(result_uses) > 0

    def test_pointer_type_detection(self, temp_dir):
        """Test pointer type detection."""
        tracker = VariableTracker()

        test_file = temp_dir / "pointers.c"
        test_file.write_text("""
        void function(int *ptr, int value) {
            int *local_ptr;
            int local_val = 0;
        }
        """)

        definitions, _ = tracker.extract_from_file(str(test_file))

        # Find ptr parameter
        ptr_var = next((v for v in definitions if v.name == "ptr"), None)
        assert ptr_var is not None
        assert ptr_var.is_pointer is True

        # Find value parameter (not a pointer)
        value_var = next((v for v in definitions if v.name == "value"), None)
        assert value_var is not None
        assert value_var.is_pointer is False

        # Find local_ptr (pointer)
        local_ptr_var = next((v for v in definitions if v.name == "local_ptr"), None)
        assert local_ptr_var is not None
        assert local_ptr_var.is_pointer is True

    def test_initializer_extraction(self, temp_dir):
        """Test extracting variable initializers."""
        tracker = VariableTracker()

        test_file = temp_dir / "init.c"
        test_file.write_text("""
        void function(void) {
            int x = 42;
            char *str = "hello";
            int y;  // No initializer
        }
        """)

        definitions, _ = tracker.extract_from_file(str(test_file))

        # Find x with initializer
        x_var = next((v for v in definitions if v.name == "x"), None)
        assert x_var is not None
        assert x_var.initializer is not None
        assert "42" in x_var.initializer

        # Find y without initializer
        y_var = next((v for v in definitions if v.name == "y"), None)
        assert y_var is not None
        assert y_var.initializer is None

    def test_complex_expressions(self, temp_dir):
        """Test handling complex expressions."""
        tracker = VariableTracker()

        test_file = temp_dir / "complex.c"
        test_file.write_text("""
        int function(int a, int b, int c) {
            int result = a * b + c;
            return result;
        }
        """)

        _, uses = tracker.extract_from_file(str(test_file))

        # Should find a, b, c used in the expression
        var_names = {u.name for u in uses}
        assert "a" in var_names
        assert "b" in var_names
        assert "c" in var_names

    def test_struct_types(self, temp_dir):
        """Test extracting struct type variables."""
        tracker = VariableTracker()

        test_file = temp_dir / "structs.c"
        test_file.write_text("""
        struct data {
            int value;
        };

        int function(struct data *d) {
            struct data local;
            return d->value;
        }
        """)

        definitions, _ = tracker.extract_from_file(str(test_file))

        # Find struct parameter
        d_param = next((v for v in definitions if v.name == "d"), None)
        assert d_param is not None
        assert "struct" in d_param.var_type.lower()
        assert d_param.is_pointer is True

        # Find struct local
        local_var = next((v for v in definitions if v.name == "local"), None)
        assert local_var is not None
        assert "struct" in local_var.var_type.lower()

    def test_empty_file(self, temp_dir):
        """Test handling empty file."""
        tracker = VariableTracker()

        empty_file = temp_dir / "empty.c"
        empty_file.write_text("")

        definitions, uses = tracker.extract_from_file(str(empty_file))

        assert len(definitions) == 0
        assert len(uses) == 0

    def test_multiple_functions(self, temp_dir):
        """Test extracting from multiple functions."""
        tracker = VariableTracker()

        test_file = temp_dir / "multi.c"
        test_file.write_text("""
        int func1(int x) {
            return x * 2;
        }

        int func2(int y) {
            return y + 1;
        }
        """)

        definitions, _ = tracker.extract_from_file(str(test_file))

        # Should find parameters from both functions
        params = [v for v in definitions if v.is_parameter]
        assert len(params) == 2

        # Check scopes
        scopes = {p.scope for p in params}
        assert "func1" in scopes
        assert "func2" in scopes
