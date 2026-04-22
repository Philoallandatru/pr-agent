"""
Unit tests for code complexity visualization system.
"""

import tempfile
from pathlib import Path
import pytest

from pr_agent.visualization import (
    ComplexityVisualizer,
    FunctionNode,
    ModuleNode,
    get_complexity_visualizer,
    GRAPHVIZ_AVAILABLE,
)


@pytest.fixture
def temp_project():
    """Create temporary project directory with sample code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Create sample Python files
        (project_root / "module_a.py").write_text("""
def simple_function(x):
    return x + 1

def complex_function(x):
    if x > 0:
        if x > 10:
            if x > 20:
                return "high"
            return "medium"
        return "low"
    return "negative"

def caller_function():
    result = simple_function(5)
    return complex_function(result)
""")

        (project_root / "module_b.py").write_text("""
import module_a

def another_function(y):
    return module_a.simple_function(y * 2)

def loop_function(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item)
    return result
""")

        yield project_root


@pytest.fixture
def visualizer(temp_project):
    """Create complexity visualizer instance."""
    viz = ComplexityVisualizer(str(temp_project))
    viz.analyze_project()
    return viz


class TestFunctionNode:
    """Test FunctionNode class."""

    def test_function_node_creation(self):
        """Test creating a function node."""
        node = FunctionNode(
            name="test.func",
            module="test",
            complexity=5,
            line_number=10,
            calls=["other_func"],
            called_by=["caller"],
        )

        assert node.name == "test.func"
        assert node.complexity == 5
        assert "other_func" in node.calls
        assert "caller" in node.called_by


class TestModuleNode:
    """Test ModuleNode class."""

    def test_module_node_creation(self):
        """Test creating a module node."""
        node = ModuleNode(
            name="test_module",
            path="test/module.py",
            imports=["os", "sys"],
            complexity=20,
            function_count=5,
        )

        assert node.name == "test_module"
        assert node.complexity == 20
        assert node.function_count == 5
        assert "os" in node.imports


class TestComplexityVisualizer:
    """Test ComplexityVisualizer class."""

    def test_init(self, temp_project):
        """Test visualizer initialization."""
        viz = ComplexityVisualizer(str(temp_project))

        assert viz.project_root == temp_project
        assert isinstance(viz.functions, dict)
        assert isinstance(viz.modules, dict)

    def test_analyze_project(self, visualizer):
        """Test project analysis."""
        assert len(visualizer.modules) > 0
        assert len(visualizer.functions) > 0

    def test_analyze_finds_functions(self, visualizer):
        """Test that analysis finds functions."""
        func_names = [f.name for f in visualizer.functions.values()]

        assert any("simple_function" in name for name in func_names)
        assert any("complex_function" in name for name in func_names)

    def test_analyze_calculates_complexity(self, visualizer):
        """Test complexity calculation."""
        # Find complex_function
        complex_func = None
        for func in visualizer.functions.values():
            if "complex_function" in func.name:
                complex_func = func
                break

        assert complex_func is not None
        assert complex_func.complexity > 1  # Has multiple branches

    def test_analyze_finds_modules(self, visualizer):
        """Test that analysis finds modules."""
        module_names = [m.name for m in visualizer.modules.values()]

        assert any("module_a" in name for name in module_names)
        assert any("module_b" in name for name in module_names)

    def test_analyze_finds_imports(self, visualizer):
        """Test that analysis finds imports."""
        # Find module_b
        module_b = None
        for module in visualizer.modules.values():
            if "module_b" in module.name:
                module_b = module
                break

        assert module_b is not None
        assert any("module_a" in imp for imp in module_b.imports)

    def test_get_most_complex_functions(self, visualizer):
        """Test getting most complex functions."""
        complex_funcs = visualizer.get_most_complex_functions(limit=3)

        assert len(complex_funcs) <= 3
        assert all(isinstance(f, FunctionNode) for f in complex_funcs)

        # Should be sorted by complexity
        if len(complex_funcs) > 1:
            assert complex_funcs[0].complexity >= complex_funcs[1].complexity

    def test_get_most_complex_modules(self, visualizer):
        """Test getting most complex modules."""
        complex_modules = visualizer.get_most_complex_modules(limit=2)

        assert len(complex_modules) <= 2
        assert all(isinstance(m, ModuleNode) for m in complex_modules)

        # Should be sorted by complexity
        if len(complex_modules) > 1:
            assert complex_modules[0].complexity >= complex_modules[1].complexity

    def test_get_hotspots(self, visualizer):
        """Test getting complexity hotspots."""
        hotspots = visualizer.get_hotspots(complexity_threshold=1)

        assert isinstance(hotspots, list)
        # All hotspots should meet threshold
        assert all(h.complexity >= 1 for h in hotspots)

    def test_generate_json_report(self, visualizer, temp_project):
        """Test JSON report generation."""
        output_path = temp_project / "report.json"
        visualizer.generate_json_report(str(output_path))

        assert output_path.exists()

        import json
        with open(output_path) as f:
            report = json.load(f)

        assert "modules" in report
        assert "functions" in report
        assert "summary" in report
        assert report["summary"]["total_modules"] > 0
        assert report["summary"]["total_functions"] > 0

    @pytest.mark.skipif(not GRAPHVIZ_AVAILABLE, reason="graphviz not installed")
    def test_generate_complexity_heatmap(self, visualizer, temp_project):
        """Test complexity heatmap generation."""
        output_path = temp_project / "heatmap"
        result = visualizer.generate_complexity_heatmap(str(output_path), format="svg")

        assert result.endswith(".svg")
        assert Path(result).exists()

    @pytest.mark.skipif(not GRAPHVIZ_AVAILABLE, reason="graphviz not installed")
    def test_generate_dependency_graph(self, visualizer, temp_project):
        """Test dependency graph generation."""
        output_path = temp_project / "dependencies"
        result = visualizer.generate_dependency_graph(str(output_path), format="svg")

        assert result.endswith(".svg")
        assert Path(result).exists()

    @pytest.mark.skipif(not GRAPHVIZ_AVAILABLE, reason="graphviz not installed")
    def test_generate_call_graph(self, visualizer, temp_project):
        """Test call graph generation."""
        output_path = temp_project / "calls"
        result = visualizer.generate_call_graph(str(output_path), format="svg", max_depth=2)

        assert result.endswith(".svg")
        assert Path(result).exists()

    def test_complexity_color_mapping(self, visualizer):
        """Test complexity color mapping."""
        # Low complexity - green
        color_low = visualizer._get_complexity_color(3)
        assert color_low == "#90EE90"

        # Medium complexity - gold
        color_med = visualizer._get_complexity_color(8)
        assert color_med == "#FFD700"

        # High complexity - orange
        color_high = visualizer._get_complexity_color(15)
        assert color_high == "#FFA500"

        # Very high complexity - red
        color_very_high = visualizer._get_complexity_color(25)
        assert color_very_high == "#FF4500"


class TestGlobalVisualizer:
    """Test global visualizer singleton."""

    def test_get_complexity_visualizer(self, temp_project):
        """Test getting global visualizer."""
        from pr_agent.visualization.complexity import _visualizer
        import pr_agent.visualization.complexity as viz_module

        # Reset global
        viz_module._visualizer = None

        viz1 = get_complexity_visualizer(str(temp_project))
        viz2 = get_complexity_visualizer()

        assert viz1 is viz2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
