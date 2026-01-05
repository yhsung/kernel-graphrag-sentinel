"""Unit tests for Module F: Log Extractor (log_extractor.py)."""

import pytest
from unittest.mock import MagicMock, patch

from src.module_f.log_extractor import LogExtractor
from src.module_f.schema import LogStatement, LogSeverity


class TestLogExtractor:
    """Test cases for LogExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create a LogExtractor instance for testing."""
        try:
            return LogExtractor()
        except ImportError:
            pytest.skip("tree-sitter or tree-sitter-c not installed")

    def test_extractor_initialization(self, extractor):
        """Test that LogExtractor initializes correctly."""
        assert extractor.parser is not None
        assert extractor.language is not None
        assert len(extractor.log_functions) > 0

    def test_extract_from_empty_code(self, extractor):
        """Test extracting from empty source code."""
        logs = extractor.extract_from_code("", "test.c")
        assert logs == []

    def test_extract_pr_err_log(self, extractor):
        """Test extracting a simple pr_err log statement."""
        source_code = """
        int test_function() {
            pr_err("This is an error: %d\\n", errno);
            return 0;
        }
        """
        logs = extractor.extract_from_code(source_code, "test.c")
        assert len(logs) >= 1
        log = logs[0]
        assert log.log_function == "pr_err"
        assert "error" in log.format_string.lower()
        assert log.severity == LogSeverity.ERR.value

    def test_extract_dev_err_log(self, extractor):
        """Test extracting a dev_err log statement."""
        source_code = """
        int test_function(struct device *dev) {
            dev_err(dev, "Device error: %d\\n", ret);
            return ret;
        }
        """
        logs = extractor.extract_from_code(source_code, "test.c")
        assert len(logs) >= 1
        log = logs[0]
        assert log.log_function == "dev_err"
        assert log.severity == LogSeverity.ERR.value

    def test_extract_printk_log(self, extractor):
        """Test extracting a printk log statement."""
        source_code = """
        int test_function() {
            printk(KERN_ERR "Printk error\\n");
            return 0;
        }
        """
        logs = extractor.extract_from_code(source_code, "test.c")
        assert len(logs) >= 1
        log = logs[0]
        assert log.log_function == "printk"

    def test_extract_multiple_logs(self, extractor):
        """Test extracting multiple log statements."""
        source_code = """
        int test_function() {
            pr_info("Starting operation\\n");
            pr_debug("Debug: value = %d\\n", x);
            pr_err("Operation failed\\n");
            return -1;
        }
        """
        logs = extractor.extract_from_code(source_code, "test.c")
        assert len(logs) >= 3

    def test_log_statement_properties(self, extractor):
        """Test that LogStatement objects have correct properties."""
        source_code = """
        int my_function() {
            pr_err("Error code: %d\\n", error);
            return error;
        }
        """
        logs = extractor.extract_from_code(source_code, "test.c")
        assert len(logs) >= 1
        log = logs[0]
        assert log.function == "my_function"
        assert log.file_path == "test.c"
        assert log.line_number > 0
        assert log.format_string
        assert log.log_function in [
            'printk', 'pr_emerg', 'pr_alert', 'pr_crit',
            'pr_err', 'pr_warn', 'pr_notice', 'pr_info', 'pr_debug',
            'dev_err', 'dev_warn', 'dev_info', 'dev_dbg',
        ]

    def test_filter_non_log_functions(self, extractor):
        """Test that non-log functions are not extracted."""
        source_code = """
        int test_function() {
            pr_err("Real log\\n");
            printf("Not a kernel log\\n");
            fprintf(stderr, "Also not a kernel log\\n");
            return 0;
        }
        """
        logs = extractor.extract_from_code(source_code, "test.c")
        # Should only find pr_err, not printf or fprintf
        assert all(log.log_function.startswith('pr_') or
                  log.log_function.startswith('dev_') or
                  log.log_function == 'printk'
                  for log in logs)

    def test_extract_with_format_args(self, extractor):
        """Test extracting logs with format arguments."""
        source_code = """
        int test_function() {
            pr_err("Failed to allocate: size=%d, flags=%x\\n", size, flags);
            return -ENOMEM;
        }
        """
        logs = extractor.extract_from_code(source_code, "test.c")
        assert len(logs) >= 1
        log = logs[0]
        assert "allocate" in log.format_string.lower() or "failed" in log.format_string.lower()


class TestLogStatement:
    """Test cases for LogStatement dataclass."""

    def test_create_log_statement(self):
        """Test creating a LogStatement."""
        log = LogStatement(
            id="test.c::123",
            function="test_func",
            file_path="test.c",
            line_number=123,
            log_function="pr_err",
            log_level="KERN_ERR",
            severity=3,
            format_string="Error occurred",
            arguments=["errno"],
        )
        assert log.id == "test.c::123"
        assert log.function == "test_func"
        assert log.line_number == 123
        assert log.log_function == "pr_err"
        assert log.format_string == "Error occurred"
        assert log.arguments == ["errno"]

    def test_log_statement_to_dict(self):
        """Test converting LogStatement to dictionary."""
        log = LogStatement(
            id="test.c::123",
            function="test_func",
            file_path="test.c",
            line_number=123,
            log_function="pr_err",
            log_level="KERN_ERR",
            severity=3,
            format_string="Error",
        )
        log_dict = log.to_dict()
        assert log_dict['id'] == "test.c::123"
        assert log_dict['function'] == "test_func"
        assert log_dict['line_number'] == 123
        assert log_dict['log_function'] == "pr_err"

    def test_log_statement_defaults(self):
        """Test LogStatement with default values."""
        log = LogStatement(
            id="test.c::1",
            function="test",
            file_path="test.c",
            line_number=1,
            log_function="pr_err",
            log_level="KERN_ERR",
            severity=3,
            format_string="Test",
        )
        assert log.arguments == []
        assert log.in_error_path is False
        assert log.error_condition is None


class TestLogSeverity:
    """Test cases for LogSeverity enum."""

    def test_severity_values(self):
        """Test that severity values are correct."""
        assert LogSeverity.EMERG.value == 0
        assert LogSeverity.ALERT.value == 1
        assert LogSeverity.CRIT.value == 2
        assert LogSeverity.ERR.value == 3
        assert LogSeverity.WARNING.value == 4
        assert LogSeverity.NOTICE.value == 5
        assert LogSeverity.INFO.value == 6
        assert LogSeverity.DEBUG.value == 7
