"""Unit tests for Module F: Coverage Analyzer (coverage_analyzer.py)."""

import pytest

from src.module_f.coverage_analyzer import CoverageAnalyzer
from src.module_f.schema import ErrorPath, LogStatement


class TestErrorPathDetector:
    """Test cases for error path detection."""

    @pytest.fixture
    def detector(self):
        """Create an ErrorPathDetector for testing."""
        from src.module_f.error_path_detector import ErrorPathDetector
        try:
            return ErrorPathDetector()
        except ImportError:
            pytest.skip("tree-sitter or tree-sitter-c not installed")

    def test_find_return_error_codes(self, detector):
        """Test finding return statements with error codes."""
        source_code = """
        int test_function() {
            if (fail)
                return -ENOMEM;
            return 0;
        }
        """
        paths = detector.find_error_paths_in_code(source_code, "test.c", "test_function")
        assert "test_function" in paths
        error_paths = paths["test_function"]
        assert len(error_paths) >= 1
        assert error_paths[0].path_type == "return"
        assert error_paths[0].error_code == "-ENOMEM"

    def test_find_goto_error_labels(self, detector):
        """Test finding goto statements to error labels."""
        source_code = """
        int test_function() {
            if (fail)
                goto err_out;
            return 0;
        err_out:
            return -1;
        }
        """
        paths = detector.find_error_paths_in_code(source_code, "test.c", "test_function")
        assert "test_function" in paths
        error_paths = paths["test_function"]
        assert any(ep.path_type == "goto" and ep.goto_label == "err_out"
                  for ep in error_paths)

    def test_multiple_error_paths(self, detector):
        """Test finding multiple error paths in a function."""
        source_code = """
        int test_function() {
            if (fail1)
                return -ENOMEM;
            if (fail2)
                return -EIO;
            if (fail3)
                goto err;
            return 0;
        err:
            return -1;
        }
        """
        paths = detector.find_error_paths_in_code(source_code, "test.c", "test_function")
        error_paths = paths["test_function"]
        assert len(error_paths) >= 3


class TestCoverageAnalyzer:
    """Test cases for CoverageAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create a CoverageAnalyzer instance for testing."""
        try:
            return CoverageAnalyzer()
        except ImportError:
            pytest.skip("tree-sitter or tree-sitter-c not installed")

    def test_analyze_function_with_logs(self, analyzer):
        """Test analyzing a function with good log coverage."""
        source_code = """
        int test_function() {
            pr_err("Allocation failed\\n");
            return -ENOMEM;
        }
        """
        report = analyzer.analyze_function(source_code, "test_function", "test.c")
        assert report.function == "test_function"
        assert report.file_path == "test.c"
        assert report.total_paths >= 1
        assert report.coverage_percentage >= 0

    def test_analyze_function_without_logs(self, analyzer):
        """Test analyzing a function with no log coverage."""
        source_code = """
        int test_function() {
            return -ENOMEM;
        }
        """
        report = analyzer.analyze_function(source_code, "test_function", "test.c")
        assert report.total_paths >= 1
        assert report.logged_paths == 0
        assert report.coverage_percentage == 0.0

    def test_coverage_calculation(self, analyzer):
        """Test coverage percentage calculation."""
        source_code = """
        int test_function() {
            if (fail1) {
                pr_err("Error 1\\n");
                return -EIO;
            }
            if (fail2)
                return -ENOMEM;
            return 0;
        }
        """
        report = analyzer.analyze_function(source_code, "test_function", "test.c")
        total = report.total_paths
        logged = report.logged_paths
        expected_coverage = (logged / total * 100) if total > 0 else 100
        assert abs(report.coverage_percentage - expected_coverage) < 0.1

    def test_unlogged_paths_identified(self, analyzer):
        """Test that unlogged paths are correctly identified."""
        source_code = """
        int test_function() {
            if (fail1)
                return -EIO;
            if (fail2) {
                pr_err("Error 2\\n");
                return -ENOMEM;
            }
            return 0;
        }
        """
        report = analyzer.analyze_function(source_code, "test_function", "test.c")
        assert len(report.unlogged_paths) >= 1
        assert any(not ep.has_log for ep in report.unlogged_paths)

    def test_generate_suggestions(self, analyzer):
        """Test generating log placement suggestions."""
        source_code = """
        int test_function() {
            return -ENOMEM;
        }
        """
        report = analyzer.analyze_function(source_code, "test_function", "test.c")
        suggestions = analyzer.suggest_logs(report, source_code)
        if report.unlogged_paths:
            assert len(suggestions) > 0
            assert all(s.suggested_function for s in suggestions)
            assert all(s.suggested_message for s in suggestions)


class TestCoverageReport:
    """Test cases for CoverageReport dataclass."""

    def test_create_coverage_report(self):
        """Test creating a CoverageReport."""
        report = CoverageReport(
            function="test_func",
            file_path="test.c",
            total_paths=5,
            logged_paths=3,
            coverage_percentage=60.0,
        )
        assert report.function == "test_func"
        assert report.total_paths == 5
        assert report.logged_paths == 3
        assert report.coverage_percentage == 60.0

    def test_coverage_report_to_dict(self):
        """Test converting CoverageReport to dictionary."""
        error_path = ErrorPath(
            line_number=10,
            path_type="return",
            error_code="-ENOMEM",
        )
        report = CoverageReport(
            function="test_func",
            file_path="test.c",
            total_paths=1,
            logged_paths=1,
            coverage_percentage=100.0,
            error_paths=[error_path],
            unlogged_paths=[],
        )
        report_dict = report.to_dict()
        assert report_dict['function'] == "test_func"
        assert report_dict['total_paths'] == 1
        assert len(report_dict['error_paths']) == 1
        assert report_dict['error_paths'][0]['path_type'] == "return"


class TestErrorPath:
    """Test cases for ErrorPath dataclass."""

    def test_create_error_path_return(self):
        """Test creating an ErrorPath for return statement."""
        error_path = ErrorPath(
            line_number=100,
            path_type="return",
            error_code="-EIO",
        )
        assert error_path.line_number == 100
        assert error_path.path_type == "return"
        assert error_path.error_code == "-EIO"
        assert error_path.has_log is False

    def test_create_error_path_goto(self):
        """Test creating an ErrorPath for goto statement."""
        error_path = ErrorPath(
            line_number=200,
            path_type="goto",
            goto_label="err_out",
        )
        assert error_path.line_number == 200
        assert error_path.path_type == "goto"
        assert error_path.goto_label == "err_out"

    def test_error_path_with_log(self):
        """Test ErrorPath with associated log statement."""
        log = LogStatement(
            id="test.c::99",
            function="test_func",
            file_path="test.c",
            line_number=99,
            log_function="pr_err",
            log_level="KERN_ERR",
            severity=3,
            format_string="Error",
        )
        error_path = ErrorPath(
            line_number=100,
            path_type="return",
            error_code="-ENOMEM",
            has_log=True,
            log_statement=log,
        )
        assert error_path.has_log is True
        assert error_path.log_statement == log

    def test_error_path_to_dict(self):
        """Test converting ErrorPath to dictionary."""
        error_path = ErrorPath(
            line_number=100,
            path_type="return",
            error_code="-ENOMEM",
        )
        path_dict = error_path.to_dict()
        assert path_dict['line_number'] == 100
        assert path_dict['path_type'] == "return"
        assert path_dict['error_code'] == "-ENOMEM"
