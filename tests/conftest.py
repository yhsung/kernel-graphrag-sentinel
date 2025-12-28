"""Pytest configuration and shared fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, Mock

import pytest
from neo4j import GraphDatabase

from tests.fixtures import SAMPLE_CONFIG, SAMPLE_KERNEL_C, SAMPLE_KUNIT_TEST_C


@pytest.fixture
def sample_c_file() -> Path:
    """Provide path to sample C file."""
    return SAMPLE_KERNEL_C


@pytest.fixture
def sample_kunit_file() -> Path:
    """Provide path to sample KUnit test file."""
    return SAMPLE_KUNIT_TEST_C


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config(temp_dir: Path) -> dict:
    """Provide sample configuration."""
    config = SAMPLE_CONFIG.copy()
    config["kernel_source"] = str(temp_dir)
    config["subsystem_path"] = "tests/fixtures"
    return config


@pytest.fixture
def mock_neo4j_driver():
    """Provide a mock Neo4j driver."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = None

    # Mock basic query results
    result = MagicMock()
    result.data.return_value = []
    session.run.return_value = result

    return driver


@pytest.fixture
def mock_neo4j_session(mock_neo4j_driver):
    """Provide a mock Neo4j session."""
    return mock_neo4j_driver.session().__enter__()


@pytest.fixture
def mock_neo4j_graph_store():
    """Provide a mock Neo4jGraphStore."""
    store = MagicMock()
    store.execute_query.return_value = []
    store.get_statistics.return_value = {"functions": 0, "relationships": 0}
    return store


@pytest.fixture
def sample_function_data() -> dict:
    """Provide sample function data for testing."""
    return {
        "name": "test_function",
        "file_path": "test.c",
        "start_line": 10,
        "end_line": 20,
        "signature": "int test_function(int param)",
        "is_static": False,
    }


@pytest.fixture
def sample_call_data() -> dict:
    """Provide sample call relationship data."""
    return {
        "caller": "function_a",
        "callee": "function_b",
        "call_line": 15,
    }


@pytest.fixture
def sample_ast_node():
    """Provide a mock AST node from tree-sitter."""
    node = MagicMock()
    node.type = "function_definition"
    node.start_point = (10, 0)
    node.end_point = (20, 1)
    node.text = b"int test_function(int param) { return 0; }"

    # Mock child nodes
    declarator = MagicMock()
    declarator.type = "function_declarator"

    identifier = MagicMock()
    identifier.type = "identifier"
    identifier.text = b"test_function"

    declarator.child_by_field_name.return_value = identifier
    node.child_by_field_name.return_value = declarator

    return node


@pytest.fixture
def sample_parsed_functions() -> list:
    """Provide sample parsed function data."""
    return [
        {
            "name": "function_a",
            "file_path": "test.c",
            "start_line": 10,
            "end_line": 15,
            "calls": ["function_b", "function_c"],
        },
        {
            "name": "function_b",
            "file_path": "test.c",
            "start_line": 20,
            "end_line": 25,
            "calls": ["function_c"],
        },
        {
            "name": "function_c",
            "file_path": "test.c",
            "start_line": 30,
            "end_line": 35,
            "calls": [],
        },
    ]


@pytest.fixture
def sample_impact_analysis_result() -> dict:
    """Provide sample impact analysis result."""
    return {
        "target_function": "function_a",
        "direct_callers": ["top_function"],
        "indirect_callers": ["main_function"],
        "direct_callees": ["function_b", "function_c"],
        "indirect_callees": ["helper_function"],
        "total_impacted": 5,
        "max_call_depth": 3,
        "risk_level": "MEDIUM",
        "test_coverage": {
            "direct_tests": ["test_function_a"],
            "indirect_tests": ["test_top_function"],
            "total_tests": 2,
        },
    }


@pytest.fixture(autouse=True)
def reset_env_vars():
    """Reset environment variables between tests."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_openai_client():
    """Provide a mock OpenAI client."""
    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Mock LLM response"
    client.chat.completions.create.return_value = response
    return client


@pytest.fixture
def mock_anthropic_client():
    """Provide a mock Anthropic client."""
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock()]
    response.content[0].text = "Mock Claude response"
    client.messages.create.return_value = response
    return client


@pytest.fixture
def mock_gemini_client():
    """Provide a mock Google Gemini client."""
    client = MagicMock()
    model = MagicMock()
    response = MagicMock()
    response.text = "Mock Gemini response"
    model.generate_content.return_value = response
    client.models.generate_content.return_value = response
    return client
