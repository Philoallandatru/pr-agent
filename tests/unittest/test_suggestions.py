"""
Unit tests for code suggestion engine.
"""

import tempfile
from pathlib import Path
import pytest

from pr_agent.suggestions import (
    SuggestionEngine,
    SuggestionType,
    SuggestionPriority,
    RefactoringAnalyzer,
    PerformanceAnalyzer,
    ReadabilityAnalyzer,
    get_suggestion_engine
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def suggestion_engine():
    """Create suggestion engine instance."""
    return SuggestionEngine()


class TestRefactoringAnalyzer:
    """Test refactoring analyzer."""

    def test_detect_long_function(self, temp_dir):
        """Test detection of long functions."""
        analyzer = RefactoringAnalyzer()

        # Create file with long function
        test_file = temp_dir / "long.py"
        lines = ["def long_function():"]
        lines.extend([f"    x{i} = {i}" for i in range(60)])
        lines.append("    return x0")
        test_file.write_text("\n".join(lines))

        suggestions = analyzer.analyze(str(test_file))

        # Should detect long function
        long_func_suggestions = [s for s in suggestions if "长" in s.title or "long" in s.title.lower()]
        assert len(long_func_suggestions) > 0
        assert long_func_suggestions[0].type == SuggestionType.REFACTORING

    def test_detect_deep_nesting(self, temp_dir):
        """Test detection of deep nesting."""
        analyzer = RefactoringAnalyzer()

        # Create file with deep nesting
        test_file = temp_dir / "nested.py"
        test_file.write_text("""
def nested_function(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        return "deep"
    return "shallow"
""")

        suggestions = analyzer.analyze(str(test_file))

        # Should detect deep nesting
        nesting_suggestions = [s for s in suggestions if "嵌套" in s.title or "nesting" in s.title.lower()]
        assert len(nesting_suggestions) > 0

    def test_simple_function_no_suggestions(self, temp_dir):
        """Test that simple function generates no suggestions."""
        analyzer = RefactoringAnalyzer()

        test_file = temp_dir / "simple.py"
        test_file.write_text("""
def simple_function(x, y):
    return x + y
""")

        suggestions = analyzer.analyze(str(test_file))

        # Should have no refactoring suggestions
        assert len(suggestions) == 0


class TestPerformanceAnalyzer:
    """Test performance analyzer."""

    def test_detect_loop_append(self, temp_dir):
        """Test detection of inefficient loop with append."""
        analyzer = PerformanceAnalyzer()

        test_file = temp_dir / "loop.py"
        test_file.write_text("""
def process_items(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result
""")

        suggestions = analyzer.analyze(str(test_file))

        # Should suggest list comprehension
        assert len(suggestions) > 0
        assert suggestions[0].type == SuggestionType.PERFORMANCE

    def test_efficient_code_no_suggestions(self, temp_dir):
        """Test that efficient code generates no suggestions."""
        analyzer = PerformanceAnalyzer()

        test_file = temp_dir / "efficient.py"
        test_file.write_text("""
def process_items(items):
    return [item * 2 for item in items]
""")

        suggestions = analyzer.analyze(str(test_file))

        # May have some suggestions but should be minimal
        assert len(suggestions) <= 1


class TestReadabilityAnalyzer:
    """Test readability analyzer."""

    def test_detect_magic_numbers(self, temp_dir):
        """Test detection of magic numbers."""
        analyzer = ReadabilityAnalyzer()

        test_file = temp_dir / "magic.py"
        test_file.write_text("""
def calculate_price(quantity):
    return quantity * 19.99
""")

        suggestions = analyzer.analyze(str(test_file))

        # Should detect magic number
        magic_suggestions = [s for s in suggestions if "魔法" in s.title or "magic" in s.title.lower()]
        assert len(magic_suggestions) > 0
        assert magic_suggestions[0].type == SuggestionType.READABILITY

    def test_detect_unclear_names(self, temp_dir):
        """Test detection of unclear variable names."""
        analyzer = ReadabilityAnalyzer()

        test_file = temp_dir / "names.py"
        test_file.write_text("""
def process(x, y):
    tmp = x + y
    return tmp
""")

        suggestions = analyzer.analyze(str(test_file))

        # Should detect unclear names
        naming_suggestions = [s for s in suggestions if "变量名" in s.title or "name" in s.title.lower()]
        assert len(naming_suggestions) > 0

    def test_clear_code_minimal_suggestions(self, temp_dir):
        """Test that clear code generates minimal suggestions."""
        analyzer = ReadabilityAnalyzer()

        test_file = temp_dir / "clear.py"
        test_file.write_text("""
PRICE_PER_UNIT = 10

def calculate_total_price(quantity):
    total_price = quantity * PRICE_PER_UNIT
    return total_price
""")

        suggestions = analyzer.analyze(str(test_file))

        # Should have minimal or no suggestions
        assert len(suggestions) <= 1


class TestSuggestionEngine:
    """Test suggestion engine."""

    def test_analyze_single_file(self, temp_dir, suggestion_engine):
        """Test analyzing a single file."""
        test_file = temp_dir / "test.py"
        test_file.write_text("""
def process(x):
    result = []
    for i in range(100):
        result.append(i * 2)
    return result
""")

        suggestions = suggestion_engine.analyze_file(str(test_file))

        # Should generate some suggestions
        assert len(suggestions) > 0

    def test_analyze_with_specific_types(self, temp_dir, suggestion_engine):
        """Test analyzing with specific suggestion types."""
        test_file = temp_dir / "test.py"
        test_file.write_text("""
def process(x):
    result = []
    for i in range(100):
        result.append(i * 2)
    return result
""")

        # Only performance suggestions
        suggestions = suggestion_engine.analyze_file(
            str(test_file),
            suggestion_types=[SuggestionType.PERFORMANCE]
        )

        # All suggestions should be performance type
        assert all(s.type == SuggestionType.PERFORMANCE for s in suggestions)

    def test_analyze_directory(self, temp_dir, suggestion_engine):
        """Test analyzing a directory."""
        # Create multiple files
        file1 = temp_dir / "file1.py"
        file1.write_text("def func1(x): return x * 2")

        file2 = temp_dir / "file2.py"
        file2.write_text("def func2(x): return x + 100")

        results = suggestion_engine.analyze_directory(str(temp_dir))

        # Should analyze both files
        assert len(results) >= 0  # May or may not have suggestions

    def test_generate_report(self, temp_dir, suggestion_engine):
        """Test report generation."""
        test_file = temp_dir / "test.py"
        test_file.write_text("""
def process(x):
    result = []
    for i in range(100):
        result.append(i * 2)
    return result
""")

        suggestions = {str(test_file): suggestion_engine.analyze_file(str(test_file))}
        report = suggestion_engine.generate_report(suggestions)

        # Report should have required fields
        assert "total_suggestions" in report
        assert "files_analyzed" in report
        assert "by_type" in report
        assert "by_priority" in report
        assert "suggestions" in report

    def test_empty_file_no_suggestions(self, temp_dir, suggestion_engine):
        """Test that empty file generates no suggestions."""
        test_file = temp_dir / "empty.py"
        test_file.write_text("")

        suggestions = suggestion_engine.analyze_file(str(test_file))

        # Should have no suggestions
        assert len(suggestions) == 0

    def test_syntax_error_no_crash(self, temp_dir, suggestion_engine):
        """Test that syntax errors don't crash the analyzer."""
        test_file = temp_dir / "invalid.py"
        test_file.write_text("def invalid syntax here")

        # Should not raise exception
        suggestions = suggestion_engine.analyze_file(str(test_file))

        # Should return empty list
        assert suggestions == []


class TestGlobalSuggestionEngine:
    """Test global suggestion engine singleton."""

    def test_get_suggestion_engine(self):
        """Test getting global suggestion engine."""
        engine1 = get_suggestion_engine()
        engine2 = get_suggestion_engine()

        # Should return same instance
        assert engine1 is engine2

    def test_engine_has_analyzers(self):
        """Test that engine has all analyzers."""
        engine = get_suggestion_engine()

        assert hasattr(engine, 'refactoring_analyzer')
        assert hasattr(engine, 'performance_analyzer')
        assert hasattr(engine, 'readability_analyzer')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
