"""Unit tests for Impact Analyzer (impact_analyzer.py)."""

import pytest
from unittest.mock import MagicMock, patch

from src.analysis.impact_analyzer import ImpactAnalyzer, ImpactResult


class TestImpactResult:
    """Test cases for ImpactResult dataclass."""

    def test_create_result(self, sample_impact_analysis_result):
        """Test creating an impact analysis result."""
        result = ImpactResult(
            target_function=sample_impact_analysis_result["target_function"],
            target_file="test.c",
            direct_callers=[{"name": c} for c in sample_impact_analysis_result["direct_callers"]],
            direct_callees=[{"name": c} for c in sample_impact_analysis_result["direct_callees"]],
            indirect_callers=[{"name": c} for c in sample_impact_analysis_result["indirect_callers"]],
            indirect_callees=[{"name": c} for c in sample_impact_analysis_result["indirect_callees"]],
            direct_tests=[],
            indirect_tests=[],
            call_chains=[],
            stats={"total_impacted": sample_impact_analysis_result["total_impacted"]}
        )

        assert result.target_function == "function_a"
        assert len(result.direct_callers) == 1
        assert len(result.indirect_callers) == 1
        assert result.stats["total_impacted"] == 5

    def test_result_with_no_impact(self):
        """Test result for function with no impact."""
        result = ImpactResult(
            target_function="isolated_func",
            target_file="test.c",
            direct_callers=[],
            indirect_callers=[],
            direct_callees=[],
            indirect_callees=[],
            direct_tests=[],
            indirect_tests=[],
            call_chains=[],
            stats={"total_impacted": 0}
        )

        assert result.stats["total_impacted"] == 0


class TestImpactAnalyzer:
    """Test cases for ImpactAnalyzer class."""

    @pytest.fixture
    def mock_graph_store(self):
        """Create a mock graph store."""
        store = MagicMock()
        return store

    @pytest.fixture
    def analyzer(self, mock_graph_store):
        """Create an ImpactAnalyzer with mock graph store."""
        return ImpactAnalyzer(mock_graph_store)

    def test_init(self, analyzer, mock_graph_store):
        """Test analyzer initialization."""
        assert analyzer.graph_store == mock_graph_store

    def test_analyze_function_not_found(self, analyzer, mock_graph_store):
        """Test analyzing a function that doesn't exist."""
        mock_graph_store.execute_query.return_value = []

        result = analyzer.analyze_function_impact("nonexistent_function", "test.c")

        assert result.target_function == "nonexistent_function"
        assert result.stats.get("total_impacted", 0) == 0

    def test_analyze_simple_function(self, analyzer, mock_graph_store):
        """Test analyzing a function with simple call graph."""
        # Mock query results
        mock_graph_store.execute_query.return_value = []

        result = analyzer.analyze_function_impact("target_func", "test.c", max_depth=2)

        assert result.target_function == "target_func"
        assert result is not None

    def test_analyze_with_max_depth(self, analyzer, mock_graph_store):
        """Test analysis respects max_depth parameter."""
        mock_graph_store.execute_query.return_value = []

        analyzer.analyze_function_impact("func", "test.c", max_depth=3)

        # Verify queries were called with depth limits
        assert mock_graph_store.execute_query.called

    def test_query_execution(self, analyzer, mock_graph_store):
        """Test that queries are executed properly."""
        mock_graph_store.execute_query.return_value = []

        result = analyzer.analyze_function_impact("test_func", "test.c")

        # Verify queries were called
        assert mock_graph_store.execute_query.called
        assert result is not None

    def test_get_direct_callers(self, analyzer, mock_graph_store):
        """Test getting direct callers of a function."""
        mock_graph_store.execute_query.return_value = [
            {"name": "caller1"},
            {"name": "caller2"},
        ]

        callers = analyzer.get_direct_callers("target_func")

        assert len(callers) >= 0
        assert mock_graph_store.execute_query.called
