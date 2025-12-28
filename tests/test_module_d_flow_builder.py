"""Unit tests for Module D: Flow Builder."""

import pytest
from pathlib import Path

from src.module_d.flow_builder import FlowBuilder, DataFlowEdge, InterProcFlow
from src.module_d.flow_schema import FlowType


class TestDataFlowEdge:
    """Test cases for DataFlowEdge dataclass."""

    def test_create_data_flow_edge(self):
        """Test creating a data flow edge."""
        edge = DataFlowEdge(
            from_var="a",
            to_var="b",
            flow_type=FlowType.ASSIGNMENT,
            function="foo",
            file_path="test.c",
            line_number=42,
            confidence=1.0,
        )

        assert edge.from_var == "a"
        assert edge.to_var == "b"
        assert edge.flow_type == FlowType.ASSIGNMENT
        assert edge.confidence == 1.0


class TestInterProcFlow:
    """Test cases for InterProcFlow dataclass."""

    def test_create_inter_proc_flow(self):
        """Test creating an inter-procedural flow."""
        flow = InterProcFlow(
            caller_var="buffer",
            caller_function="main",
            callee_param="param0",
            callee_function="process",
            argument_position=0,
            file_path="test.c",
            line_number=100,
        )

        assert flow.caller_var == "buffer"
        assert flow.callee_function == "process"
        assert flow.argument_position == 0


class TestFlowBuilder:
    """Test cases for FlowBuilder class."""

    def test_init(self):
        """Test flow builder initialization."""
        builder = FlowBuilder()
        assert builder.parser is not None

    def test_simple_assignment_flow(self, temp_dir):
        """Test extracting flow from simple assignment."""
        builder = FlowBuilder()

        test_file = temp_dir / "assign.c"
        test_file.write_text("""
        void function(void) {
            int a = 10;
            int b = a;
        }
        """)

        flows, _ = builder.build_intra_procedural_flows(str(test_file))

        # Should find flow: a → b
        assert len(flows) > 0

        a_to_b = [f for f in flows if f.from_var == "a" and f.to_var == "b"]
        assert len(a_to_b) > 0

        flow = a_to_b[0]
        assert flow.flow_type == FlowType.ASSIGNMENT

    def test_complex_assignment_flow(self, temp_dir):
        """Test extracting flow from complex assignment."""
        builder = FlowBuilder()

        test_file = temp_dir / "complex.c"
        test_file.write_text("""
        void function(void) {
            int a = 1;
            int b = 2;
            int c = a + b;
        }
        """)

        flows, _ = builder.build_intra_procedural_flows(str(test_file))

        # Should find flows: a → c, b → c
        c_flows = [f for f in flows if f.to_var == "c"]
        assert len(c_flows) >= 2

        from_vars = {f.from_var for f in c_flows}
        assert "a" in from_vars
        assert "b" in from_vars

    def test_return_flow(self, temp_dir):
        """Test extracting flow from return statement."""
        builder = FlowBuilder()

        test_file = temp_dir / "return.c"
        test_file.write_text("""
        int function(void) {
            int result = 42;
            return result;
        }
        """)

        flows, _ = builder.build_intra_procedural_flows(str(test_file))

        # Should find flow: result → __RETURN__
        return_flows = [f for f in flows if f.to_var == "__RETURN__"]
        assert len(return_flows) > 0

        result_flow = [f for f in return_flows if f.from_var == "result"]
        assert len(result_flow) > 0

        assert result_flow[0].flow_type == FlowType.RETURN

    def test_multiple_assignments_chain(self, temp_dir):
        """Test extracting chained assignments."""
        builder = FlowBuilder()

        test_file = temp_dir / "chain.c"
        test_file.write_text("""
        void function(void) {
            int a = 10;
            int b = a;
            int c = b;
        }
        """)

        flows, _ = builder.build_intra_procedural_flows(str(test_file))

        # Should find: a → b and b → c
        assert len(flows) >= 2

        a_to_b = [f for f in flows if f.from_var == "a" and f.to_var == "b"]
        assert len(a_to_b) > 0

        b_to_c = [f for f in flows if f.from_var == "b" and f.to_var == "c"]
        assert len(b_to_c) > 0

    def test_parameter_flow_simple(self, temp_dir):
        """Test extracting inter-procedural parameter flow."""
        builder = FlowBuilder()

        test_file = temp_dir / "call.c"
        test_file.write_text("""
        int process(int data);

        int function(void) {
            int x = 10;
            return process(x);
        }
        """)

        flows = builder.build_inter_procedural_flows(str(test_file), {})

        # Should find: x passed to process
        assert len(flows) > 0

        x_flows = [f for f in flows if f.caller_var == "x"]
        assert len(x_flows) > 0

        flow = x_flows[0]
        assert flow.callee_function == "process"
        assert flow.argument_position == 0

    def test_parameter_flow_multiple_args(self, temp_dir):
        """Test extracting flow with multiple arguments."""
        builder = FlowBuilder()

        test_file = temp_dir / "multi_args.c"
        test_file.write_text("""
        int process(int a, int b, int c);

        int function(void) {
            int x = 1;
            int y = 2;
            int z = 3;
            return process(x, y, z);
        }
        """)

        flows = builder.build_inter_procedural_flows(str(test_file), {})

        # Should find flows for x, y, z
        assert len(flows) >= 3

        # Check argument positions
        x_flow = next(f for f in flows if f.caller_var == "x")
        assert x_flow.argument_position == 0

        y_flow = next(f for f in flows if f.caller_var == "y")
        assert y_flow.argument_position == 1

        z_flow = next(f for f in flows if f.caller_var == "z")
        assert z_flow.argument_position == 2

    def test_no_flows_in_empty_function(self, temp_dir):
        """Test that empty function has no flows."""
        builder = FlowBuilder()

        test_file = temp_dir / "empty_func.c"
        test_file.write_text("""
        void function(void) {
            // Empty
        }
        """)

        flows, _ = builder.build_intra_procedural_flows(str(test_file))

        # Should find no flows
        assert len(flows) == 0

    def test_flow_with_sample_kernel_file(self, sample_c_file):
        """Test building flows from sample kernel C file."""
        builder = FlowBuilder()

        flows, def_use = builder.build_intra_procedural_flows(str(sample_c_file))

        # Should find flows in the sample file
        assert len(flows) > 0

        # Should track def-use for functions
        assert len(def_use) > 0

    def test_pointer_assignment_flow(self, temp_dir):
        """Test flow through pointer assignment."""
        builder = FlowBuilder()

        test_file = temp_dir / "pointer.c"
        test_file.write_text("""
        void function(void) {
            int x = 10;
            int *p = &x;
        }
        """)

        flows, _ = builder.build_intra_procedural_flows(str(test_file))

        # Should find flow: x → p (address-of is still a use)
        p_flows = [f for f in flows if f.to_var == "p"]
        assert len(p_flows) > 0

    def test_array_assignment_flow(self, temp_dir):
        """Test flow with array assignments."""
        builder = FlowBuilder()

        test_file = temp_dir / "array.c"
        test_file.write_text("""
        void function(void) {
            int arr[10];
            int x = 5;
            arr[0] = x;
        }
        """)

        flows, _ = builder.build_intra_procedural_flows(str(test_file))

        # Should find flow: x → arr (simplified)
        x_flows = [f for f in flows if f.from_var == "x"]
        assert len(x_flows) > 0

    def test_field_assignment_flow(self, temp_dir):
        """Test flow with struct field assignments."""
        builder = FlowBuilder()

        test_file = temp_dir / "struct.c"
        test_file.write_text("""
        struct data {
            int value;
        };

        void function(void) {
            struct data d;
            int x = 10;
            d.value = x;
        }
        """)

        flows, _ = builder.build_intra_procedural_flows(str(test_file))

        # Should find flow: x → d.value
        x_flows = [f for f in flows if f.from_var == "x"]
        assert len(x_flows) > 0

    def test_conditional_assignment_flow(self, temp_dir):
        """Test flow in conditional statements."""
        builder = FlowBuilder()

        test_file = temp_dir / "conditional.c"
        test_file.write_text("""
        void function(int condition) {
            int a = 10;
            int b;
            if (condition) {
                b = a;
            }
        }
        """)

        flows, _ = builder.build_intra_procedural_flows(str(test_file))

        # Should find flow: a → b (even inside if block)
        a_to_b = [f for f in flows if f.from_var == "a" and f.to_var == "b"]
        assert len(a_to_b) > 0

    def test_multiple_functions_separate_flows(self, temp_dir):
        """Test that flows from different functions are tracked separately."""
        builder = FlowBuilder()

        test_file = temp_dir / "multi_func.c"
        test_file.write_text("""
        void func1(void) {
            int a = 1;
            int b = a;
        }

        void func2(void) {
            int c = 2;
            int d = c;
        }
        """)

        flows, def_use = builder.build_intra_procedural_flows(str(test_file))

        # Should have flows from both functions
        assert len(flows) >= 2

        # Check that functions are distinguished
        func1_flows = [f for f in flows if f.function == "func1"]
        func2_flows = [f for f in flows if f.function == "func2"]

        assert len(func1_flows) > 0
        assert len(func2_flows) > 0

    def test_expression_with_function_call(self, temp_dir):
        """Test flow with function calls in expressions."""
        builder = FlowBuilder()

        test_file = temp_dir / "expr_call.c"
        test_file.write_text("""
        int get_value(void);

        void function(void) {
            int x = get_value();
            int y = x;
        }
        """)

        flows, _ = builder.build_intra_procedural_flows(str(test_file))

        # Should find flow: x → y
        # (get_value call won't create internal flow)
        x_to_y = [f for f in flows if f.from_var == "x" and f.to_var == "y"]
        assert len(x_to_y) > 0
