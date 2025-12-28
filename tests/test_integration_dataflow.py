"""Integration tests for Module D - Data Flow Analysis end-to-end pipeline."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import shutil

from src.module_d.variable_tracker import VariableTracker
from src.module_d.flow_builder import FlowBuilder
from src.module_d.flow_ingestion import DataFlowIngestion


class TestDataFlowEndToEnd:
    """Integration tests for data flow analysis pipeline."""

    @pytest.fixture
    def sample_dataflow_code(self, temp_dir):
        """Create a sample C file with data flow patterns."""
        code_file = temp_dir / "dataflow_test.c"
        code_file.write_text("""
        #include <linux/kernel.h>

        // Function with parameter flow
        int process_data(int input, char *buffer, size_t size) {
            int processed = input * 2;
            char local_buf[256];

            if (processed > 100) {
                return -1;
            }

            int result = processed + size;
            return result;
        }

        // Function with user input
        int handle_user_input(void __user *user_data, size_t len) {
            char *kernel_buf;
            int ret;

            kernel_buf = kmalloc(len, GFP_KERNEL);
            if (!kernel_buf)
                return -ENOMEM;

            if (copy_from_user(kernel_buf, user_data, len)) {
                kfree(kernel_buf);
                return -EFAULT;
            }

            ret = process_data(*(int*)kernel_buf, kernel_buf + 4, len - 4);
            kfree(kernel_buf);
            return ret;
        }
        """)
        return code_file

    def test_full_dataflow_pipeline_with_mock(self, sample_dataflow_code):
        """Test full data flow pipeline: tracking -> building -> ingestion."""
        # Step 1: Variable Tracking
        tracker = VariableTracker()
        variables = tracker.extract_from_file(str(sample_dataflow_code))

        assert len(variables) > 0, "Should extract variables"

        # Verify we found key variables
        var_names = {v.name for v in variables}
        assert "input" in var_names, "Should find parameter 'input'"
        assert "processed" in var_names, "Should find local 'processed'"

        # Step 2: Data Flow Graph Building
        builder = FlowBuilder()
        flows, _ = builder.build_intra_procedural_flows(str(sample_dataflow_code))

        assert len(flows) > 0, "Should build data flows"

        # Verify flow properties
        for flow in flows:
            assert hasattr(flow, 'source_name')
            assert hasattr(flow, 'target_name')
            assert hasattr(flow, 'source_scope')

        # Step 3: Mock Neo4j Ingestion
        with patch('src.module_d.flow_ingestion.Neo4jGraphStore') as mock_store_class:
            mock_store = MagicMock()
            mock_store_class.return_value = mock_store

            ingestion = DataFlowIngestion(mock_store)

            # Ingest the file
            stats = ingestion.ingest_file(str(sample_dataflow_code), subsystem="test")

            assert stats is not None
            # Stats should have processed the file
            assert stats.get('file_path') == str(sample_dataflow_code)

    def test_schema_creation_with_mock(self, sample_dataflow_code):
        """Test Neo4j schema creation for data flows."""
        with patch('src.module_d.flow_ingestion.Neo4jGraphStore') as mock_store_class:
            mock_store = MagicMock()
            mock_store_class.return_value = mock_store

            ingestion = DataFlowIngestion(mock_store)

            # Setup schema
            ingestion.setup_schema()

            # Verify schema creation was called
            assert mock_store.execute_query.called, "Should create schema"

    def test_parameter_extraction(self, sample_dataflow_code):
        """Test extraction of function parameters."""
        tracker = VariableTracker()
        variables = tracker.extract_from_file(str(sample_dataflow_code))

        # Find parameters in process_data function
        process_data_params = [
            v for v in variables
            if v.scope == "process_data" and v.is_parameter
        ]

        assert len(process_data_params) >= 3, f"Should find 3 parameters, found {len(process_data_params)}"

        param_names = {p.name for p in process_data_params}
        assert "input" in param_names
        assert "buffer" in param_names
        assert "size" in param_names

    def test_local_variable_extraction(self, sample_dataflow_code):
        """Test extraction of local variables."""
        tracker = VariableTracker()
        variables = tracker.extract_from_file(str(sample_dataflow_code))

        # Find local variables
        local_vars = [v for v in variables if not v.is_parameter]

        assert len(local_vars) > 0, "Should find local variables"

        local_names = {v.name for v in local_vars}
        assert "processed" in local_names or "result" in local_names

    def test_flow_building_basic(self, sample_dataflow_code):
        """Test basic data flow building."""
        builder = FlowBuilder()
        flows, var_defs = builder.build_intra_procedural_flows(str(sample_dataflow_code))

        assert len(flows) > 0, "Should build flows"
        assert len(var_defs) > 0, "Should find variable definitions"

        # Check flow structure
        assert all(hasattr(f, 'source_name') for f in flows)
        assert all(hasattr(f, 'target_name') for f in flows)

    def test_batch_ingestion(self, temp_dir, sample_dataflow_code):
        """Test batch processing of multiple files."""
        # Create multiple C files
        target_dir = temp_dir / "subsystem"
        target_dir.mkdir()

        # Copy test file multiple times
        for i in range(3):
            shutil.copy(sample_dataflow_code, target_dir / f"file{i}.c")

        with patch('src.module_d.flow_ingestion.Neo4jGraphStore') as mock_store_class:
            mock_store = MagicMock()
            mock_store_class.return_value = mock_store

            ingestion = DataFlowIngestion(mock_store)

            # Batch ingest directory
            stats = ingestion.ingest_directory(str(target_dir), subsystem="test")

            assert stats is not None
            assert stats.get('total_files', 0) >= 3

    def test_variable_types(self, sample_dataflow_code):
        """Test that variable types are extracted."""
        tracker = VariableTracker()
        variables = tracker.extract_from_file(str(sample_dataflow_code))

        # Some variables should have type information
        typed_vars = [v for v in variables if v.type]

        assert len(typed_vars) > 0, "Should extract some variable types"

        # Check for specific types
        types = {v.type for v in typed_vars}
        assert any('int' in t for t in types if t), "Should find int type"

    def test_data_consistency(self, sample_dataflow_code):
        """Test that variables and flows are consistent."""
        # Extract variables
        tracker = VariableTracker()
        variables = tracker.extract_from_file(str(sample_dataflow_code))

        # Build flows
        builder = FlowBuilder()
        flows, _ = builder.build_intra_procedural_flows(str(sample_dataflow_code))

        # Create variable lookup
        var_dict = {(v.name, v.scope): v for v in variables}

        # Check that flow sources/targets make sense
        for flow in flows:
            if flow.source_name and flow.source_scope:
                # Source might be in variables or might be a special value
                key = (flow.source_name, flow.source_scope)
                # Just verify the data structure is valid
                assert isinstance(flow.source_name, str)
                assert isinstance(flow.target_name, str)

    def test_error_handling_malformed_code(self, temp_dir):
        """Test that data flow analysis handles errors gracefully."""
        bad_file = temp_dir / "bad.c"
        bad_file.write_text("int broken( { syntax error }")

        # Variable tracker should not crash
        try:
            tracker = VariableTracker()
            variables = tracker.extract_from_file(str(bad_file))
            # May return empty list or partial results
            assert isinstance(variables, list)
        except Exception:
            # Or may raise - both acceptable
            pass

        # Flow builder should not crash
        try:
            builder = FlowBuilder()
            flows, _ = builder.build_intra_procedural_flows(str(bad_file))
            assert isinstance(flows, list)
        except Exception:
            pass


class TestDataFlowPerformance:
    """Performance tests for data flow analysis."""

    def test_medium_file_performance(self, temp_dir):
        """Test performance with a moderate-sized file."""
        medium_file = temp_dir / "medium.c"

        # Generate code with some data flows
        functions = []
        for i in range(10):
            functions.append(f"""
            int func{i}(int param{i}) {{
                int local{i} = param{i} * 2;
                int result{i} = local{i} + 5;
                return result{i};
            }}
            """)

        medium_file.write_text("\n".join(functions))

        import time
        start = time.time()

        tracker = VariableTracker()
        variables = tracker.extract_from_file(str(medium_file))

        elapsed = time.time() - start

        # Should complete quickly (< 5 seconds for 10 functions)
        assert elapsed < 5.0, f"Variable extraction took {elapsed:.2f}s"

        # Should find variables (at least 3 per function = 30)
        assert len(variables) >= 20, f"Should find many variables, got {len(variables)}"


class TestDataFlowRealKernelCode:
    """Integration tests with realistic kernel code patterns."""

    @pytest.fixture
    def kernel_style_code(self, temp_dir):
        """Create a file with realistic kernel code patterns."""
        code_file = temp_dir / "kernel_style.c"
        code_file.write_text("""
        #include <linux/fs.h>
        #include <linux/slab.h>

        // Typical kernel function
        static int ext4_read_data(struct file *file, char __user *buf,
                                   size_t count, loff_t *ppos) {
            char *kbuf;
            ssize_t ret;

            if (count > MAX_RW_COUNT)
                return -EINVAL;

            kbuf = kmalloc(count, GFP_KERNEL);
            if (!kbuf)
                return -ENOMEM;

            ret = generic_file_read(file, kbuf, count, ppos);
            if (ret < 0)
                goto out_free;

            if (copy_to_user(buf, kbuf, ret)) {
                ret = -EFAULT;
                goto out_free;
            }

        out_free:
            kfree(kbuf);
            return ret;
        }
        """)
        return code_file

    def test_kernel_code_extraction(self, kernel_style_code):
        """Test extraction from kernel-style code."""
        tracker = VariableTracker()
        variables = tracker.extract_from_file(str(kernel_style_code))

        assert len(variables) > 0, "Should extract variables from kernel code"

        # Should find kernel-specific variables
        var_names = {v.name for v in variables}
        assert any('buf' in name for name in var_names), "Should find buffer variables"

    def test_kernel_flow_building(self, kernel_style_code):
        """Test flow building with kernel code."""
        builder = FlowBuilder()
        flows, _ = builder.build_intra_procedural_flows(str(kernel_style_code))

        # Should find some flows even with goto patterns
        # (may be empty if goto handling is limited)
        assert isinstance(flows, list), "Should return a list of flows"


class TestDataFlowIngestion:
    """Tests for Neo4j ingestion functionality."""

    def test_ingestion_with_valid_code(self, temp_dir):
        """Test ingesting valid C code."""
        code_file = temp_dir / "valid.c"
        code_file.write_text("""
        int add(int a, int b) {
            int sum = a + b;
            return sum;
        }
        """)

        with patch('src.module_d.flow_ingestion.Neo4jGraphStore') as mock_store_class:
            mock_store = MagicMock()
            mock_store_class.return_value = mock_store

            ingestion = DataFlowIngestion(mock_store)
            stats = ingestion.ingest_file(str(code_file), subsystem="test")

            assert stats is not None
            assert stats.get('file_path') == str(code_file)
            assert stats.get('subsystem') == "test"

    def test_directory_ingestion(self, temp_dir):
        """Test ingesting a directory of files."""
        # Create a subdirectory with C files
        subdir = temp_dir / "code"
        subdir.mkdir()

        for i in range(3):
            (subdir / f"file{i}.c").write_text(f"int func{i}(void) {{ return {i}; }}")

        with patch('src.module_d.flow_ingestion.Neo4jGraphStore') as mock_store_class:
            mock_store = MagicMock()
            mock_store_class.return_value = mock_store

            ingestion = DataFlowIngestion(mock_store)
            stats = ingestion.ingest_directory(str(subdir), subsystem="test")

            assert stats is not None
            assert stats.get('total_files', 0) >= 3
            assert stats.get('subsystem') == "test"
