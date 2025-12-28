"""Test fixtures for kernel-graphrag-sentinel tests."""

import os
from pathlib import Path

# Fixture directory
FIXTURES_DIR = Path(__file__).parent

# Sample C files
SAMPLE_KERNEL_C = FIXTURES_DIR / "sample_kernel.c"
SAMPLE_KUNIT_TEST_C = FIXTURES_DIR / "sample_kunit_test.c"

# Expected parsed data for sample_kernel.c
EXPECTED_FUNCTIONS = [
    {
        "name": "top_level_function",
        "start_line": 16,
        "end_line": 30,
        "calls": ["helper_function", "cleanup_resource"],
    },
    {
        "name": "helper_function",
        "start_line": 39,
        "end_line": 45,
        "calls": [],
    },
    {
        "name": "cleanup_resource",
        "start_line": 52,
        "end_line": 56,
        "calls": ["kfree"],
    },
    {
        "name": "standalone_function",
        "start_line": 63,
        "end_line": 66,
        "calls": [],
    },
    {
        "name": "multi_caller",
        "start_line": 72,
        "end_line": 77,
        "calls": ["helper_function", "standalone_function", "cleanup_resource"],
    },
]

# Expected test cases from sample_kunit_test.c
EXPECTED_TEST_CASES = [
    {"name": "test_top_level_function_valid", "tested_functions": ["top_level_function"]},
    {"name": "test_top_level_function_invalid", "tested_functions": ["top_level_function"]},
    {"name": "test_standalone_function", "tested_functions": ["standalone_function"]},
    {"name": "test_helper_function", "tested_functions": ["helper_function"]},
]

# Sample configuration for testing
SAMPLE_CONFIG = {
    "neo4j": {
        "uri": "bolt://localhost:7687",
        "username": "neo4j",
        "password": "test_password",
    },
    "kernel_source": "/tmp/test_kernel_source",
    "subsystem_path": "tests/fixtures",
    "llm": {
        "provider": "openai",
        "model": "gpt-4",
        "temperature": 0.7,
    },
}
