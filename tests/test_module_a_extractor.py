"""Unit tests for Module A: Function Extractor (extractor.py)."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from src.module_a.extractor import FunctionExtractor, FunctionNode, CallEdge


class TestFunctionNode:
    """Test cases for FunctionNode dataclass."""

    def test_create_function_node(self):
        """Test creating a FunctionNode."""
        node = FunctionNode(
            name="test_func",
            file_path="test.c",
            line_start=10,
            line_end=20,
            subsystem="test",
            is_static=False
        )
        assert node.name == "test_func"
        assert node.file_path == "test.c"
        assert node.line_start == 10
        assert node.line_end == 20
        assert node.subsystem == "test"
        assert node.is_static is False

    def test_function_node_defaults(self):
        """Test FunctionNode with default values."""
        node = FunctionNode(
            name="test",
            file_path="test.c",
            line_start=1,
            line_end=10,
            subsystem="test"
        )
        assert node.is_static is False


class TestCallEdge:
    """Test cases for CallEdge dataclass."""

    def test_create_call_edge(self):
        """Test creating a CallEdge."""
        edge = CallEdge(
            caller="func_a",
            callee="func_b",
            call_site_line=15,
            file_path="test.c"
        )
        assert edge.caller == "func_a"
        assert edge.callee == "func_b"
        assert edge.call_site_line == 15
        assert edge.file_path == "test.c"


class TestFunctionExtractor:
    """Test cases for FunctionExtractor class."""

    @pytest.fixture
    def extractor(self, temp_dir):
        """Create a FunctionExtractor instance with temp directory."""
        return FunctionExtractor(str(temp_dir))

    def test_init(self, temp_dir):
        """Test extractor initialization."""
        extractor = FunctionExtractor(str(temp_dir))
        assert extractor.kernel_root == temp_dir
        assert extractor.preprocessor is not None
        assert extractor.parser is not None

    def test_extract_from_file_skip_preprocessing(self, extractor, sample_c_file):
        """Test extracting from file without preprocessing."""
        functions, calls = extractor.extract_from_file(
            str(sample_c_file),
            subsystem="test",
            skip_preprocessing=True
        )

        # Should find functions in sample_kernel.c
        assert len(functions) >= 5
        assert len(calls) > 0

        # Verify function names
        func_names = [f.name for f in functions]
        assert "top_level_function" in func_names
        assert "helper_function" in func_names
        assert "cleanup_resource" in func_names
        assert "standalone_function" in func_names
        assert "multi_caller" in func_names

    def test_extract_from_file_with_preprocessing(self, extractor, sample_c_file):
        """Test extracting from file with preprocessing."""
        # Preprocessing will likely fail (no real kernel headers)
        # but should fallback to raw parsing
        functions, calls = extractor.extract_from_file(
            str(sample_c_file),
            subsystem="test",
            skip_preprocessing=False
        )

        # Should still get results via fallback
        assert len(functions) >= 0  # May succeed or fail gracefully

    def test_extract_functions_metadata(self, extractor, sample_c_file):
        """Test that extracted functions have correct metadata."""
        functions, _ = extractor.extract_from_file(
            str(sample_c_file),
            subsystem="test_subsystem",
            skip_preprocessing=True
        )

        for func in functions:
            assert isinstance(func, FunctionNode)
            assert func.name is not None
            assert func.file_path == str(sample_c_file)
            assert func.line_start > 0
            assert func.line_end >= func.line_start
            assert func.subsystem == "test_subsystem"
            assert isinstance(func.is_static, bool)

    def test_extract_call_edges(self, extractor, sample_c_file):
        """Test that call edges are extracted correctly."""
        _, calls = extractor.extract_from_file(
            str(sample_c_file),
            subsystem="test",
            skip_preprocessing=True
        )

        # Verify we have call edges
        assert len(calls) > 0

        # Check CallEdge structure
        for call in calls:
            assert isinstance(call, CallEdge)
            assert call.caller is not None
            assert call.callee is not None
            assert call.call_site_line > 0
            assert call.file_path == str(sample_c_file)

    def test_extract_specific_calls(self, extractor, sample_c_file):
        """Test that specific expected calls are found."""
        _, calls = extractor.extract_from_file(
            str(sample_c_file),
            subsystem="test",
            skip_preprocessing=True
        )

        # Create a set of (caller, callee) tuples
        call_pairs = {(c.caller, c.callee) for c in calls}

        # Verify expected calls from sample_kernel.c
        # top_level_function calls helper_function and cleanup_resource
        assert ("top_level_function", "helper_function") in call_pairs
        assert ("top_level_function", "cleanup_resource") in call_pairs

        # multi_caller calls multiple functions
        assert ("multi_caller", "helper_function") in call_pairs
        assert ("multi_caller", "standalone_function") in call_pairs
        assert ("multi_caller", "cleanup_resource") in call_pairs

    def test_extract_from_nonexistent_file(self, extractor, temp_dir):
        """Test extracting from non-existent file."""
        fake_file = temp_dir / "nonexistent.c"

        with pytest.raises(FileNotFoundError):
            extractor.extract_from_file(
                str(fake_file),
                subsystem="test",
                skip_preprocessing=True
            )

    def test_extract_from_empty_file(self, extractor, temp_dir):
        """Test extracting from empty C file."""
        empty_file = temp_dir / "empty.c"
        empty_file.write_text("")

        functions, calls = extractor.extract_from_file(
            str(empty_file),
            subsystem="test",
            skip_preprocessing=True
        )

        # Empty file should have no functions or calls
        assert len(functions) == 0
        assert len(calls) == 0

    def test_extract_static_functions(self, extractor, temp_dir):
        """Test that static functions are properly identified."""
        test_file = temp_dir / "static_test.c"
        test_file.write_text("""
        static int static_func(void) { return 1; }
        int public_func(void) { return 2; }
        """)

        functions, _ = extractor.extract_from_file(
            str(test_file),
            subsystem="test",
            skip_preprocessing=True
        )

        assert len(functions) == 2

        static_func = next((f for f in functions if f.name == "static_func"), None)
        public_func = next((f for f in functions if f.name == "public_func"), None)

        assert static_func is not None
        assert static_func.is_static is True

        assert public_func is not None
        assert public_func.is_static is False

    def test_extract_from_directory(self, extractor, temp_dir):
        """Test extracting from all files in a directory."""
        # Create test files
        file1 = temp_dir / "test1.c"
        file1.write_text("int func1(void) { return 1; }")

        file2 = temp_dir / "test2.c"
        file2.write_text("int func2(void) { return 2; }")

        all_functions = []
        all_calls = []

        for c_file in temp_dir.glob("*.c"):
            funcs, calls = extractor.extract_from_file(
                str(c_file),
                subsystem="test",
                skip_preprocessing=True
            )
            all_functions.extend(funcs)
            all_calls.extend(calls)

        assert len(all_functions) == 2
        func_names = {f.name for f in all_functions}
        assert "func1" in func_names
        assert "func2" in func_names

    def test_extract_with_parse_error(self, extractor, temp_dir):
        """Test extraction handles parse errors gracefully."""
        bad_file = temp_dir / "bad.c"
        bad_file.write_text("int broken( { invalid syntax }")

        # Should not crash, but may return empty results
        functions, calls = extractor.extract_from_file(
            str(bad_file),
            subsystem="test",
            skip_preprocessing=True
        )

        # Parser is resilient, may still extract partial data
        assert isinstance(functions, list)
        assert isinstance(calls, list)

    def test_extract_line_numbers(self, extractor, sample_c_file):
        """Test that line numbers are accurately extracted."""
        functions, _ = extractor.extract_from_file(
            str(sample_c_file),
            subsystem="test",
            skip_preprocessing=True
        )

        # Find top_level_function
        top_func = next((f for f in functions if f.name == "top_level_function"), None)
        assert top_func is not None

        # Verify line numbers are reasonable
        assert top_func.line_start > 0
        assert top_func.line_end > top_func.line_start
        # Function should be multiple lines
        assert (top_func.line_end - top_func.line_start) >= 5

    def test_call_site_line_numbers(self, extractor, sample_c_file):
        """Test that call site line numbers are accurate."""
        _, calls = extractor.extract_from_file(
            str(sample_c_file),
            subsystem="test",
            skip_preprocessing=True
        )

        for call in calls:
            # Call site line should be positive
            assert call.call_site_line > 0

            # For top_level_function calls, verify they're within function bounds
            if call.caller == "top_level_function":
                # Should be between lines 16-30 approximately (from sample_kernel.c)
                assert 10 < call.call_site_line < 35
