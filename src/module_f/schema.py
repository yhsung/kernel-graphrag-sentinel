"""
Schema definitions for Module F: Log Coverage Analyzer

This module defines the data structures and schemas for log statements,
error paths, and coverage analysis.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class LogSeverity(Enum):
    """Kernel log severity levels (KERN_*)"""
    EMERG = 0   # KERN_EMERG - system is unusable
    ALERT = 1   # KERN_ALERT - action must be taken immediately
    CRIT = 2    # KERN_CRIT - critical conditions
    ERR = 3     # KERN_ERR - error conditions
    WARNING = 4 # KERN_WARNING - warning conditions
    NOTICE = 5  # KERN_NOTICE - normal but significant condition
    INFO = 6    # KERN_INFO - informational
    DEBUG = 7   # KERN_DEBUG - debug-level messages


class LogLevel(Enum):
    """Log level classification"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


# Core kernel logging functions (20 core functions)
CORE_LOG_FUNCTIONS = {
    # Core logging (8 severity levels)
    'printk',
    'pr_emerg',
    'pr_alert',
    'pr_crit',
    'pr_err',
    'pr_warn',
    'pr_notice',
    'pr_info',
    'pr_debug',

    # Device logging
    'dev_err',
    'dev_warn',
    'dev_info',
    'dev_dbg',

    # Common subsystem wrappers (ext4 as example)
    'ext4_error',
    'ext4_warning',
    'ext4_msg',
    'ext4_error_inode',
}


@dataclass
class LogStatement:
    """
    Represents a log statement in kernel code.

    Attributes:
        id: Unique identifier (file_path::line_number)
        function: Function name containing this log
        file_path: Source file path
        line_number: Line number in source file
        log_function: Name of logging function (pr_err, dev_err, etc.)
        log_level: KERN_* severity level
        severity: Numeric severity (0-7)
        format_string: Format string (e.g., "failed to allocate: %d")
        arguments: List of variable names used as arguments
        in_error_path: True if log is in an error handling path
        error_condition: Condition that triggers this log (if in error path)
    """
    id: str
    function: str
    file_path: str
    line_number: int
    log_function: str
    log_level: str
    severity: int
    format_string: str
    arguments: List[str] = field(default_factory=list)
    in_error_path: bool = False
    error_condition: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'function': self.function,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'log_function': self.log_function,
            'log_level': self.log_level,
            'severity': self.severity,
            'format_string': self.format_string,
            'arguments': self.arguments,
            'in_error_path': self.in_error_path,
            'error_condition': self.error_condition,
        }


@dataclass
class ErrorPath:
    """
    Represents an error return path in a function.

    Attributes:
        line_number: Line number of error return/goto
        path_type: Type of error path ('return' or 'goto')
        error_code: Error code being returned (e.g., -ENOMEM, -EIO)
        goto_label: Label for goto statements (if applicable)
        has_log: True if a log statement exists before this error path
        log_statement: LogStatement if has_log is True
    """
    line_number: int
    path_type: str  # 'return' or 'goto'
    error_code: Optional[str] = None
    goto_label: Optional[str] = None
    has_log: bool = False
    log_statement: Optional[LogStatement] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'line_number': self.line_number,
            'path_type': self.path_type,
            'error_code': self.error_code,
            'goto_label': self.goto_label,
            'has_log': self.has_log,
            'log_statement': self.log_statement.to_dict() if self.log_statement else None,
        }


@dataclass
class CoverageReport:
    """
    Coverage analysis report for a function.

    Attributes:
        function: Function name
        file_path: Source file path
        total_paths: Total number of error paths
        logged_paths: Number of error paths with logs
        coverage_percentage: Coverage as percentage (0-100)
        error_paths: List of all error paths
        unlogged_paths: List of error paths without logs (gaps)
    """
    function: str
    file_path: str
    total_paths: int
    logged_paths: int
    coverage_percentage: float
    error_paths: List[ErrorPath] = field(default_factory=list)
    unlogged_paths: List[ErrorPath] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'function': self.function,
            'file_path': self.file_path,
            'total_paths': self.total_paths,
            'logged_paths': self.logged_paths,
            'coverage_percentage': self.coverage_percentage,
            'error_paths': [ep.to_dict() for ep in self.error_paths],
            'unlogged_paths': [up.to_dict() for up in self.unlogged_paths],
        }


@dataclass
class LogSuggestion:
    """
    Suggested log statement for an unlogged error path.

    Attributes:
        line_number: Line number where log should be added
        error_path: The ErrorPath this suggestion is for
        suggested_function: Recommended log function (pr_err, dev_err, etc.)
        suggested_severity: Recommended severity level
        suggested_message: Suggested log message format string
        suggested_arguments: Suggested variable arguments
        code_snippet: Example code showing where to add the log
    """
    line_number: int
    error_path: ErrorPath
    suggested_function: str
    suggested_severity: str
    suggested_message: str
    suggested_arguments: List[str] = field(default_factory=list)
    code_snippet: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'line_number': self.line_number,
            'error_path': self.error_path.to_dict(),
            'suggested_function': self.suggested_function,
            'suggested_severity': self.suggested_severity,
            'suggested_message': self.suggested_message,
            'suggested_arguments': self.suggested_arguments,
            'code_snippet': self.code_snippet,
        }


@dataclass
class RedundantLog:
    """
    Information about redundant/duplicate log statements.

    Attributes:
        format_string: The duplicate log message
        occurrences: List of (function, line_number) where this appears
        call_chain_depth: Depth in call chain where redundancy occurs
        recommendation: Suggestion for consolidation
    """
    format_string: str
    occurrences: List[tuple]  # List of (function, line_number, log_function)
    call_chain_depth: int
    recommendation: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'format_string': self.format_string,
            'occurrences': [(func, line, log_func) for func, line, log_func in self.occurrences],
            'call_chain_depth': self.call_chain_depth,
            'recommendation': self.recommendation,
        }
