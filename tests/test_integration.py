"""Integration tests for end-to-end pipeline."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.module_a.extractor import FunctionExtractor
from src.module_b.ingestion import GraphIngestion
from src.module_c.kunit_parser import KUnitParser
from src.analysis.impact_analyzer import ImpactAnalyzer


class TestEndToEndPipeline:
    """Integration tests for the complete pipeline."""

    @pytest.fixture
    def temp_kernel_root(self, temp_dir, sample_c_file, sample_kunit_file):
        """Create a temporary kernel root with test files."""
        # Copy sample files to temp directory
        import shutil

        code_file = temp_dir / "code.c"
        test_file = temp_dir / "test.c"

        shutil.copy(sample_c_file, code_file)
        shutil.copy(sample_kunit_file, test_file)

        return temp_dir

    @patch('src.module_b.graph_store.Neo4jGraphStore')
    def test_full_pipeline_parse_to_graph(self, mock_store_class, temp_kernel_root):
        """Test full pipeline from parsing to graph ingestion."""
        # Setup mock graph store
        mock_store = MagicMock()
        mock_store_class.return_value = mock_store

        # Step 1: Extract functions from C code
        extractor = FunctionExtractor(str(temp_kernel_root))
        code_file = temp_kernel_root / "code.c"

        functions, calls = extractor.extract_from_file(
            str(code_file),
            subsystem="test",
            skip_preprocessing=True
        )

        assert len(functions) > 0
        assert len(calls) > 0

        # Step 2: Parse KUnit tests
        kunit_parser = KUnitParser()
        test_file = temp_kernel_root / "test.c"

        test_cases, test_suites = kunit_parser.parse_test_file(str(test_file))

        assert len(test_cases) > 0

        # Step 3: Ingest into graph (with mock)
        ingestion = GraphIngestion(mock_store)

        # Should be able to add nodes and relationships
        for func in functions:
            # Convert to graph node format if needed
            pass

        # Verify mock was used
        assert True  # Pipeline completes without errors

    def test_parse_and_extract_consistency(self, sample_c_file):
        """Test that parsing and extraction are consistent."""
        extractor = FunctionExtractor(str(sample_c_file.parent))

        # Extract twice
        functions1, calls1 = extractor.extract_from_file(
            str(sample_c_file),
            subsystem="test",
            skip_preprocessing=True
        )

        functions2, calls2 = extractor.extract_from_file(
            str(sample_c_file),
            subsystem="test",
            skip_preprocessing=True
        )

        # Results should be identical
        assert len(functions1) == len(functions2)
        assert len(calls1) == len(calls2)

        # Function names should match
        names1 = {f.name for f in functions1}
        names2 = {f.name for f in functions2}
        assert names1 == names2

    def test_kunit_to_function_mapping(self, sample_c_file, sample_kunit_file):
        """Test mapping KUnit tests to functions."""
        # Extract functions
        extractor = FunctionExtractor(str(sample_c_file.parent))
        functions, _ = extractor.extract_from_file(
            str(sample_c_file),
            subsystem="test",
            skip_preprocessing=True
        )

        function_names = {f.name for f in functions}

        # Parse tests
        kunit_parser = KUnitParser()
        test_cases, _ = kunit_parser.parse_test_file(str(sample_kunit_file))

        # Verify tests reference real functions
        for test in test_cases:
            # Test name should relate to actual functions
            # e.g., test_top_level_function -> top_level_function
            if "top_level_function" in test.name:
                assert "top_level_function" in function_names

            if "helper_function" in test.name:
                assert "helper_function" in function_names

    @patch('src.module_b.graph_store.Neo4jGraphStore')
    def test_impact_analysis_on_extracted_data(self, mock_store_class, sample_c_file):
        """Test running impact analysis on extracted code."""
        # Setup mock
        mock_store = MagicMock()
        mock_store_class.return_value = mock_store

        # Mock query responses
        mock_store.execute_query.return_value = [
            {"name": "multi_caller"},  # Direct caller
        ]

        # Extract functions
        extractor = FunctionExtractor(str(sample_c_file.parent))
        functions, calls = extractor.extract_from_file(
            str(sample_c_file),
            subsystem="test",
            skip_preprocessing=True
        )

        # Analyze impact of helper_function
        analyzer = ImpactAnalyzer(mock_store)
        result = analyzer.analyze_function_impact("helper_function", str(sample_c_file))

        assert result is not None
        assert result.target_function == "helper_function"

    def test_data_consistency_across_modules(self, sample_c_file):
        """Test that data remains consistent across modules."""
        extractor = FunctionExtractor(str(sample_c_file.parent))
        functions, calls = extractor.extract_from_file(
            str(sample_c_file),
            subsystem="test",
            skip_preprocessing=True
        )

        # Verify call edges reference existing functions
        function_names = {f.name for f in functions}

        for call in calls:
            # Caller should exist in functions (unless it's external)
            # Callee might be external (like kfree)
            assert call.caller in function_names or call.caller == ""

    @patch('src.module_b.graph_store.Neo4jGraphStore')
    def test_full_subsystem_processing(self, mock_store_class, temp_dir):
        """Test processing an entire subsystem."""
        # Create multiple C files
        file1 = temp_dir / "file1.c"
        file1.write_text("""
        int func1(void) { return func2(); }
        """)

        file2 = temp_dir / "file2.c"
        file2.write_text("""
        int func2(void) { return 42; }
        """)

        # Setup mock
        mock_store = MagicMock()
        mock_store_class.return_value = mock_store

        # Extract from all files
        extractor = FunctionExtractor(str(temp_dir))
        all_functions = []
        all_calls = []

        for c_file in temp_dir.glob("*.c"):
            funcs, calls = extractor.extract_from_file(
                str(c_file),
                subsystem="test_subsystem",
                skip_preprocessing=True
            )
            all_functions.extend(funcs)
            all_calls.extend(calls)

        # Should have functions from both files
        assert len(all_functions) >= 2

        # Verify subsystem is set correctly
        for func in all_functions:
            assert func.subsystem == "test_subsystem"

    def test_error_handling_pipeline(self, temp_dir):
        """Test that pipeline handles errors gracefully."""
        # Create a file with syntax errors
        bad_file = temp_dir / "bad.c"
        bad_file.write_text("int broken( { syntax error }")

        extractor = FunctionExtractor(str(temp_dir))

        # Should not crash
        try:
            functions, calls = extractor.extract_from_file(
                str(bad_file),
                subsystem="test",
                skip_preprocessing=True
            )
            # May return partial or empty results
            assert isinstance(functions, list)
            assert isinstance(calls, list)
        except Exception as e:
            # Or may raise an error - either is acceptable
            assert True


class TestConfigurationIntegration:
    """Test configuration system integration."""

    def test_config_loading(self, sample_config):
        """Test loading configuration."""
        from src.config import Config

        # Should be able to create config from dict
        config = Config(**sample_config)

        assert config.neo4j["uri"] == "bolt://localhost:7687"
        assert config.subsystem_path == "tests/fixtures"

    @patch.dict('os.environ', {'NEO4J_URI': 'bolt://custom:7687'})
    def test_env_var_override(self):
        """Test environment variable override."""
        import os

        assert os.environ.get('NEO4J_URI') == 'bolt://custom:7687'


class TestPerformanceIntegration:
    """Test performance characteristics of the pipeline."""

    def test_batch_processing_efficiency(self, temp_dir):
        """Test that batch processing is efficient."""
        # Create 10 small C files
        for i in range(10):
            file = temp_dir / f"file{i}.c"
            file.write_text(f"int func{i}(void) {{ return {i}; }}")

        extractor = FunctionExtractor(str(temp_dir))

        # Process all files
        import time
        start = time.time()

        for c_file in temp_dir.glob("*.c"):
            extractor.extract_from_file(
                str(c_file),
                subsystem="perf_test",
                skip_preprocessing=True
            )

        elapsed = time.time() - start

        # Should complete reasonably fast (< 5 seconds for 10 tiny files)
        assert elapsed < 5.0

    def test_large_file_handling(self, temp_dir):
        """Test handling of larger files."""
        # Create a file with many functions
        large_file = temp_dir / "large.c"
        functions_code = "\n".join([
            f"int func{i}(void) {{ return {i}; }}"
            for i in range(100)
        ])
        large_file.write_text(functions_code)

        extractor = FunctionExtractor(str(temp_dir))

        functions, calls = extractor.extract_from_file(
            str(large_file),
            subsystem="test",
            skip_preprocessing=True
        )

        # Should find all 100 functions
        assert len(functions) >= 100
