"""
Module F: Log Coverage Analyzer

This module provides functionality to:
- Extract log statements from kernel C code
- Detect error paths and calculate coverage
- Identify unlogged error paths (gaps)
- Suggest log placements
- Detect redundant/duplicate logs
- Quick dmesg → code lookup
- Generate coverage reports

Core Components:
- LogExtractor: Extract log statements from C code
- ErrorPathDetector: Find error return paths
- CoverageAnalyzer: Calculate coverage and identify gaps
- RedundantDetector: Find duplicate/redundant logs
- LogSearch: dmesg → code lookup
- LogReporter: Generate coverage reports
"""

from .schema import (
    LogStatement,
    ErrorPath,
    CoverageReport,
    LogSuggestion,
    RedundantLog,
    LogSeverity,
    LogLevel,
    CORE_LOG_FUNCTIONS,
)

__version__ = "0.1.0"

__all__ = [
    "LogStatement",
    "ErrorPath",
    "CoverageReport",
    "LogSuggestion",
    "RedundantLog",
    "LogSeverity",
    "LogLevel",
    "CORE_LOG_FUNCTIONS",
]
