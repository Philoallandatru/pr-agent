"""
Unit tests for code metrics analyzer.
"""

import pytest
from pathlib import Path
from pr_agent.metrics import (
    MetricsAnalyzer,
    get_metrics_analyzer,
    FileMetrics,
    ProjectMetrics,
    MetricType,
    Severity,
)


class TestMetricsAnalyzer:
    """Test MetricsAnalyzer class."""

    def test_analyze_simple_file(self, tmp_path):
        """Test analyzing a simple Python file."""
        test_file = tmp_path / "simple.py"
        test_file.write_text("""
def hello():
    print("Hello")

def world():
    print("World")
""")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(str(test_file))

        assert metrics.path == str(test_file)
        assert metrics.language == "python"
        assert metrics.loc > 0
        assert metrics.sloc > 0
        assert metrics.functions == 2
        assert metrics.complexity > 0

    def test_analyze_complex_file(self, tmp_path):
        """Test analyzing a complex Python file."""
        test_file = tmp_path / "complex.py"
        test_file.write_text("""
class Calculator:
    def add(self, a, b):
        if a > 0 and b > 0:
            return a + b
        elif a < 0 or b < 0:
            return 0
        else:
            return -1

    def divide(self, a, b):
        try:
            return a / b
        except ZeroDivisionError:
            return None
""")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(str(test_file))

        assert metrics.classes == 1
        assert metrics.functions == 2
        assert metrics.complexity > 5  # Multiple branches

    def test_analyze_with_comments(self, tmp_path):
        """Test analyzing file with comments."""
        test_file = tmp_path / "comments.py"
        test_file.write_text("""
# This is a comment
def func():
    # Another comment
    pass

# More comments
""")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(str(test_file))

        assert metrics.comments > 0
        assert metrics.sloc > 0
        assert metrics.blank >= 0

    def test_analyze_project(self, tmp_path):
        """Test analyzing entire project."""
        # Create test files
        (tmp_path / "file1.py").write_text("def func1(): pass")
        (tmp_path / "file2.py").write_text("def func2(): pass")
        (tmp_path / "file3.py").write_text("def func3(): pass")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_project(str(tmp_path))

        assert metrics.total_files == 3
        assert metrics.total_functions == 3
        assert metrics.total_loc > 0
        assert len(metrics.files) == 3

    def test_language_detection(self, tmp_path):
        """Test language detection."""
        analyzer = MetricsAnalyzer()

        py_file = tmp_path / "test.py"
        py_file.write_text("pass")
        metrics = analyzer.analyze_file(str(py_file))
        assert metrics.language == "python"

        js_file = tmp_path / "test.js"
        js_file.write_text("console.log('test');")
        metrics = analyzer.analyze_file(str(js_file))
        assert metrics.language == "javascript"

    def test_maintainability_calculation(self, tmp_path):
        """Test maintainability index calculation."""
        test_file = tmp_path / "maintainable.py"
        test_file.write_text("""
def simple_function():
    return 42
""")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(str(test_file))

        assert 0 <= metrics.maintainability <= 100
        assert metrics.maintainability > 50  # Simple code should be maintainable

    def test_complexity_thresholds(self, tmp_path):
        """Test complexity threshold detection."""
        test_file = tmp_path / "complex.py"
        # Create highly complex function
        branches = "\n".join([f"    if x == {i}: return {i}" for i in range(60)])
        test_file.write_text(f"""
def complex_function(x):
{branches}
    return -1
""")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(str(test_file))

        assert metrics.complexity > analyzer.complexity_thresholds[Severity.CRITICAL]
        assert any("complexity" in issue.lower() for issue in metrics.issues)

    def test_large_file_detection(self, tmp_path):
        """Test large file detection."""
        test_file = tmp_path / "large.py"
        # Create file with many lines
        lines = "\n".join([f"x{i} = {i}" for i in range(1100)])
        test_file.write_text(lines)

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(str(test_file))

        assert metrics.sloc > 1000
        assert any("large file" in issue.lower() for issue in metrics.issues)

    def test_skip_directories(self, tmp_path):
        """Test skipping certain directories."""
        # Create files in skip directories
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "test.py").write_text("pass")

        (tmp_path / "venv").mkdir()
        (tmp_path / "venv" / "test.py").write_text("pass")

        # Create normal file
        (tmp_path / "normal.py").write_text("pass")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_project(str(tmp_path))

        # Should only analyze normal.py
        assert metrics.total_files == 1

    def test_language_breakdown(self, tmp_path):
        """Test language breakdown."""
        (tmp_path / "file1.py").write_text("pass")
        (tmp_path / "file2.py").write_text("pass")
        (tmp_path / "file3.js").write_text("console.log('test');")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_project(str(tmp_path))

        assert metrics.language_breakdown["python"] == 2
        assert metrics.language_breakdown["javascript"] == 1

    def test_complexity_distribution(self, tmp_path):
        """Test complexity distribution."""
        # Low complexity
        (tmp_path / "low.py").write_text("def func(): pass")

        # Medium complexity
        medium_code = """
def func(x):
    if x > 0:
        if x < 10:
            if x % 2 == 0:
                return "even"
            else:
                return "odd"
    return "invalid"
"""
        (tmp_path / "medium.py").write_text(medium_code)

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_project(str(tmp_path))

        assert "low" in metrics.complexity_distribution
        assert "medium" in metrics.complexity_distribution

    def test_technical_debt_calculation(self, tmp_path):
        """Test technical debt calculation."""
        # Create file with issues
        test_file = tmp_path / "debt.py"
        branches = "\n".join([f"    if x == {i}: return {i}" for i in range(30)])
        test_file.write_text(f"""
def complex_function(x):
{branches}
    return -1
""")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_project(str(tmp_path))

        assert metrics.technical_debt_hours > 0

    def test_text_report_generation(self, tmp_path):
        """Test text report generation."""
        (tmp_path / "test.py").write_text("def func(): pass")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_project(str(tmp_path))
        report = analyzer.generate_report(metrics, format="text")

        assert "CODE METRICS REPORT" in report
        assert "SUMMARY" in report
        assert "Total Files" in report
        assert "LANGUAGE BREAKDOWN" in report

    def test_json_report_generation(self, tmp_path):
        """Test JSON report generation."""
        (tmp_path / "test.py").write_text("def func(): pass")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_project(str(tmp_path))
        report = analyzer.generate_report(metrics, format="json")

        import json
        data = json.loads(report)

        assert "summary" in data
        assert "language_breakdown" in data
        assert "files" in data

    def test_invalid_format(self, tmp_path):
        """Test invalid report format."""
        (tmp_path / "test.py").write_text("def func(): pass")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_project(str(tmp_path))

        with pytest.raises(ValueError, match="Unsupported format"):
            analyzer.generate_report(metrics, format="invalid")

    def test_nonexistent_project(self):
        """Test analyzing nonexistent project."""
        analyzer = MetricsAnalyzer()

        with pytest.raises(ValueError, match="not found"):
            analyzer.analyze_project("/nonexistent/path")

    def test_syntax_error_handling(self, tmp_path):
        """Test handling of syntax errors."""
        test_file = tmp_path / "invalid.py"
        test_file.write_text("def func( invalid syntax")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(str(test_file))

        assert any("syntax error" in issue.lower() for issue in metrics.issues)

    def test_empty_file(self, tmp_path):
        """Test analyzing empty file."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(str(test_file))

        assert metrics.loc == 1  # Empty file has 1 line
        assert metrics.sloc == 0
        assert metrics.maintainability == 100.0  # Empty file is "maintainable"

    def test_singleton_instance(self):
        """Test singleton instance."""
        analyzer1 = get_metrics_analyzer()
        analyzer2 = get_metrics_analyzer()

        assert analyzer1 is analyzer2

    def test_duplication_detection(self, tmp_path):
        """Test code duplication detection."""
        # Create files with duplicate code
        duplicate_code = """
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
"""

        (tmp_path / "file1.py").write_text(duplicate_code)
        (tmp_path / "file2.py").write_text(duplicate_code)

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_project(str(tmp_path))

        assert metrics.duplication_percentage > 0

    def test_generic_language_analysis(self, tmp_path):
        """Test analysis of non-Python files."""
        js_file = tmp_path / "test.js"
        js_file.write_text("""
// Comment
function test() {
    console.log('test');
}
""")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(str(js_file))

        assert metrics.language == "javascript"
        assert metrics.sloc > 0
        assert metrics.comments > 0

    def test_averages_calculation(self, tmp_path):
        """Test average metrics calculation."""
        (tmp_path / "file1.py").write_text("def func1(): pass")
        (tmp_path / "file2.py").write_text("def func2(): pass")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_project(str(tmp_path))

        assert metrics.avg_complexity > 0
        assert metrics.avg_maintainability > 0

    def test_file_patterns(self, tmp_path):
        """Test custom file patterns."""
        (tmp_path / "test.py").write_text("pass")
        (tmp_path / "test.txt").write_text("text")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_project(str(tmp_path), patterns=["*.py"])

        assert metrics.total_files == 1  # Only .py file

    def test_low_maintainability_detection(self, tmp_path):
        """Test low maintainability detection."""
        # Create complex file with low maintainability
        test_file = tmp_path / "unmaintainable.py"
        branches = "\n".join([f"    if x == {i}: y = {i}" for i in range(100)])
        lines = "\n".join([f"z{i} = {i}" for i in range(500)])
        test_file.write_text(f"""
def complex_function(x):
{branches}
    return x

{lines}
""")

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(str(test_file))

        assert metrics.maintainability < 65
        # Should contribute to technical debt


class TestFileMetrics:
    """Test FileMetrics dataclass."""

    def test_file_metrics_creation(self):
        """Test creating FileMetrics."""
        metrics = FileMetrics(
            path="/test/file.py",
            language="python",
            loc=100,
            sloc=80,
            comments=10,
            blank=10
        )

        assert metrics.path == "/test/file.py"
        assert metrics.language == "python"
        assert metrics.loc == 100
        assert metrics.sloc == 80


class TestProjectMetrics:
    """Test ProjectMetrics dataclass."""

    def test_project_metrics_creation(self):
        """Test creating ProjectMetrics."""
        metrics = ProjectMetrics(
            total_files=10,
            total_loc=1000,
            total_sloc=800
        )

        assert metrics.total_files == 10
        assert metrics.total_loc == 1000
        assert metrics.total_sloc == 800
        assert isinstance(metrics.timestamp, str)
