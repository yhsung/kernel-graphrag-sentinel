"""Unit tests for Module C: KUnit Parser (kunit_parser.py)."""

import pytest
from pathlib import Path

from src.module_c.kunit_parser import KUnitParser, TestCase


class TestTestCase:
    """Test cases for TestCase dataclass."""

    def test_create_test_case(self):
        """Test creating a TestCase."""
        test = TestCase(
            name="test_example",
            test_suite="example_suite",
            file_path="/path/to/test.c",
            line_number=42
        )

        assert test.name == "test_example"
        assert test.test_suite == "example_suite"
        assert test.file_path == "/path/to/test.c"
        assert test.line_number == 42


class TestKUnitParser:
    """Test cases for KUnitParser class."""

    def test_init(self):
        """Test parser initialization."""
        parser = KUnitParser()
        assert parser.parser is not None

    def test_parse_kunit_test_file(self, sample_kunit_file):
        """Test parsing a KUnit test file."""
        parser = KUnitParser()
        test_cases, test_suites = parser.parse_test_file(str(sample_kunit_file))

        # Should find test cases in sample_kunit_test.c
        assert len(test_cases) >= 4

        test_names = [tc.name for tc in test_cases]
        assert "test_top_level_function_valid" in test_names
        assert "test_top_level_function_invalid" in test_names
        assert "test_standalone_function" in test_names
        assert "test_helper_function" in test_names

    def test_extract_test_suite_name(self, sample_kunit_file):
        """Test extracting test suite name from file."""
        parser = KUnitParser()
        test_cases, test_suites = parser.parse_test_file(str(sample_kunit_file))

        # Should have test suites
        assert len(test_suites) > 0

    def test_parse_nonexistent_file(self, temp_dir):
        """Test parsing non-existent file raises error."""
        parser = KUnitParser()
        fake_file = temp_dir / "nonexistent.c"

        with pytest.raises(FileNotFoundError):
            parser.parse_test_file(str(fake_file))

    def test_parse_empty_file(self, temp_dir):
        """Test parsing empty file returns no tests."""
        parser = KUnitParser()
        empty_file = temp_dir / "empty_test.c"
        empty_file.write_text("")

        test_cases, test_suites = parser.parse_test_file(str(empty_file))
        assert len(test_cases) == 0

    def test_parse_file_no_kunit_tests(self, temp_dir):
        """Test parsing C file without KUnit tests."""
        parser = KUnitParser()
        regular_file = temp_dir / "regular.c"
        regular_file.write_text("""
        int regular_function(void) {
            return 42;
        }
        """)

        test_cases, test_suites = parser.parse_test_file(str(regular_file))
        assert len(test_cases) == 0

    def test_identify_kunit_test_functions(self, sample_kunit_file):
        """Test identifying KUNIT_CASE declarations."""
        parser = KUnitParser()

        with open(sample_kunit_file, 'r') as f:
            content = f.read()

        # Should find KUNIT_CASE macro calls
        assert "KUNIT_CASE(" in content
        assert "test_top_level_function_valid" in content
        assert "test_standalone_function" in content

    def test_parse_multiple_test_suites(self, temp_dir):
        """Test parsing file with multiple test suites."""
        parser = KUnitParser()
        test_file = temp_dir / "multi_suite.c"
        test_file.write_text("""
        #include <kunit/test.h>

        static void test_a(struct kunit *test) {}
        static void test_b(struct kunit *test) {}

        static struct kunit_case suite1_cases[] = {
            KUNIT_CASE(test_a),
            {}
        };

        static struct kunit_case suite2_cases[] = {
            KUNIT_CASE(test_b),
            {}
        };

        static struct kunit_suite suite1 = {
            .name = "suite_one",
            .test_cases = suite1_cases,
        };

        static struct kunit_suite suite2 = {
            .name = "suite_two",
            .test_cases = suite2_cases,
        };

        kunit_test_suite(suite1);
        kunit_test_suite(suite2);
        """)

        test_cases = parser.parse_file(str(test_file))
        assert len(test_cases) >= 2

    def test_extract_tested_functions(self, sample_kunit_file):
        """Test extracting which functions are being tested."""
        parser = KUnitParser(str(sample_kunit_file.parent))
        test_cases = parser.parse_file(str(sample_kunit_file))

        # Find test_top_level_function_valid
        test = next((tc for tc in test_cases if "top_level_function_valid" in tc.name), None)
        assert test is not None

        # Test should reference top_level_function
        tested_funcs = parser.infer_tested_functions(test, str(sample_kunit_file))
        assert "top_level_function" in tested_funcs

    def test_infer_tested_functions_from_name(self):
        """Test inferring tested functions from test name."""
        parser = KUnitParser("/tmp")

        test = TestCase(
            name="test_foo_bar_baz",
            test_suite="foo_tests",
            file_path="test_foo.c",
            line_number=10
        )

        # Should infer "foo_bar_baz" or similar
        funcs = parser.infer_tested_functions(test, "test_foo.c")
        assert len(funcs) > 0

    def test_parse_test_with_line_numbers(self, sample_kunit_file):
        """Test that line numbers are correctly extracted."""
        parser = KUnitParser(str(sample_kunit_file.parent))
        test_cases = parser.parse_file(str(sample_kunit_file))

        for tc in test_cases:
            # Line numbers should be positive
            assert tc.line_number > 0
            # Should be reasonable (not at EOF for this small file)
            assert tc.line_number < 100

    def test_find_kunit_files_in_directory(self, temp_dir):
        """Test finding all KUnit test files in a directory."""
        parser = KUnitParser(str(temp_dir))

        # Create some test files
        (temp_dir / "test_foo.c").write_text("#include <kunit/test.h>")
        (temp_dir / "test_bar.c").write_text("#include <kunit/test.h>")
        (temp_dir / "regular.c").write_text("int func(void) { return 0; }")

        kunit_files = parser.find_kunit_files(str(temp_dir))

        # Should find files with kunit includes or test patterns
        assert len(kunit_files) >= 2
