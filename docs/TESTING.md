# Testing Guide

## Overview

Kernel-GraphRAG Sentinel includes a comprehensive test suite covering unit tests, integration tests, and fixtures for C code parsing, graph operations, and impact analysis.

## Test Statistics (v0.1.0)

- **Total Tests**: 94
- **Passing Tests**: 61 (65%)
- **Code Coverage**: 30% overall
  - Module A (C Parser): 54% coverage
  - Module B (Neo4j Graph): 33% coverage
  - Module C (KUnit Mapper): 66% coverage
  - Analysis Module: 30% coverage

## Test Structure

```
tests/
├── conftest.py                          # Pytest configuration and shared fixtures
├── fixtures/                            # Test data
│   ├── sample_kernel.c                 # Sample C code with 5 functions
│   ├── sample_kunit_test.c             # Sample KUnit test file
│   └── __init__.py                     # Expected data constants
├── test_module_a_parser.py             # Unit tests for C parser (17 tests)
├── test_module_a_extractor.py          # Unit tests for function extractor (16 tests)
├── test_module_b_schema.py             # Unit tests for graph schema (11 tests)
├── test_module_b_graph_store.py        # Unit tests for Neo4j operations (16 tests)
├── test_module_c_kunit_parser.py       # Unit tests for KUnit parser (13 tests)
├── test_analysis_impact_analyzer.py    # Unit tests for impact analyzer (8 tests)
└── test_integration.py                 # End-to-end integration tests (13 tests)
```

## Running Tests

### Prerequisites

```bash
# Activate virtual environment
source /workspaces/ubuntu/.env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test Modules

```bash
# Module A (C Parser)
pytest tests/test_module_a_parser.py
pytest tests/test_module_a_extractor.py

# Module B (Neo4j Graph)
pytest tests/test_module_b_schema.py
pytest tests/test_module_b_graph_store.py

# Module C (KUnit Mapper)
pytest tests/test_module_c_kunit_parser.py

# Impact Analysis
pytest tests/test_analysis_impact_analyzer.py

# Integration Tests
pytest tests/test_integration.py
```

### Run with Coverage

```bash
# Full coverage report
pytest tests/ --cov=src --cov-report=term-missing

# HTML coverage report
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html in browser

# Module-specific coverage
pytest tests/test_module_a_extractor.py --cov=src/module_a --cov-report=term
```

### Run with Verbose Output

```bash
pytest tests/ -v          # Verbose test names
pytest tests/ -vv         # Extra verbose with details
pytest tests/ -s          # Show print statements
```

## Test Fixtures

### Sample C Code (`fixtures/sample_kernel.c`)

Provides realistic kernel-style C code with:
- 5 functions (top_level_function, helper_function, cleanup_resource, standalone_function, multi_caller)
- Function call relationships
- Static and exported functions
- Error handling patterns

### Sample KUnit Tests (`fixtures/sample_kunit_test.c`)

Provides KUnit test examples:
- 4 test cases
- 1 test suite (sample_tests)
- KUNIT_EXPECT assertions

### Mock Objects (conftest.py)

- `mock_neo4j_driver`: Mock Neo4j driver for graph operations
- `mock_neo4j_session`: Mock Neo4j session
- `mock_openai_client`: Mock OpenAI client for LLM tests
- `mock_anthropic_client`: Mock Anthropic Claude client
- `mock_gemini_client`: Mock Google Gemini client
- `temp_dir`: Temporary directory for file operations
- `sample_config`: Sample configuration dictionary

## Test Coverage by Module

### Module A: C Parser (54% coverage)

**Covered:**
- Basic C parsing with tree-sitter
- Function definition extraction
- Function call identification
- Static function detection
- Line number extraction
- Error handling for malformed code

**Not Covered:**
- Advanced macro expansion
- Inline assembly handling
- Complex preprocessor directives

### Module B: Neo4j Graph (33% coverage)

**Covered:**
- Graph schema definitions (71% for schema.py)
- Node and relationship creation
- Mock graph operations
- Connection handling

**Not Covered:**
- Batch operations
- Schema migration
- Index creation
- Constraint enforcement
- Real Neo4j integration (mocked only)

### Module C: KUnit Mapper (66% coverage)

**Covered:**
- KUnit test file parsing
- Test case extraction
- Test suite identification
- Function call detection in tests

**Not Covered:**
- Complex test macros
- Parameterized tests
- Test module registration

### Analysis Module (30% coverage)

**Covered:**
- Impact analysis data structures
- Basic analyzer initialization
- Mock query execution

**Not Covered:**
- Risk level calculation
- Call chain traversal
- Test coverage correlation
- Graph visualization generation
- LLM report generation

## Known Test Limitations

### 1. No Real Neo4j Tests

All Neo4j tests use mocks. To test with real Neo4j:
- Install and run Neo4j locally
- Update test configuration
- Create separate integration test suite

### 2. Limited Integration Tests

Current integration tests use mocks. Future improvements:
- Real database integration
- Full pipeline tests on actual kernel code
- Performance benchmarking

### 3. LLM Testing

LLM tests are currently mocked. Real LLM testing requires:
- API keys configured
- Network access
- Cost considerations for API calls

## Continuous Integration

### GitHub Actions (Future)

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Test Development Guidelines

### Writing New Tests

1. **Follow naming conventions**: `test_<module>_<class>_<method>.py`
2. **Use fixtures**: Reuse conftest.py fixtures for common setup
3. **Mock external dependencies**: Neo4j, LLMs, file I/O when possible
4. **Test edge cases**: Empty inputs, invalid data, error conditions
5. **Document test purpose**: Clear docstrings explaining what is tested

### Example Test Structure

```python
def test_feature_name(fixture1, fixture2):
    """Test that feature works correctly with valid input."""
    # Arrange
    input_data = prepare_input()

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result.status == "success"
    assert len(result.items) > 0
```

## Coverage Goals

### v0.1.0 (Current)
- Overall: 30% ✓
- Module A: 54% ✓
- Module B: 33% ✓
- Module C: 66% ✓

### v0.2.0 (Target)
- Overall: 60%
- All core modules: 70%+
- Integration tests with real Neo4j
- LLM integration tests

### v1.0 (Target)
- Overall: 80%+
- Critical paths: 100%
- Full integration test suite
- Performance regression tests

## Troubleshooting

### Tests Failing Locally

```bash
# Check Python version (requires 3.12+)
python --version

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Clear pytest cache
pytest --cache-clear tests/
```

### Import Errors

```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH=/workspaces/ubuntu/kernel-graphrag-sentinel:$PYTHONPATH

# Or run from project root
cd /workspaces/ubuntu/kernel-graphrag-sentinel
pytest tests/
```

### Slow Tests

```bash
# Run only fast tests (skip integration)
pytest tests/ -m "not slow"

# Run in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest tests/ -n auto
```

## Contributing

When adding new features:
1. Write tests first (TDD approach recommended)
2. Ensure new code has ≥50% coverage
3. Run full test suite before submitting PR
4. Update this documentation if test structure changes

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Plugin](https://pytest-cov.readthedocs.io/)
- [Tree-sitter Testing](https://tree-sitter.github.io/tree-sitter/)
- [Neo4j Python Driver Testing](https://neo4j.com/docs/api/python-driver/)
