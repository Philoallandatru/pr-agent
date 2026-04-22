"""
Unit tests for quality gate system.
"""

import os
import tempfile
from pathlib import Path

import pytest

from pr_agent.quality import (
    CheckType,
    Severity,
    QualityGateConfig,
    QualityGate,
    ComplexityAnalyzer,
    SecurityScanner,
    StyleChecker,
    DocumentationChecker,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def quality_gate():
    """Create quality gate instance."""
    return QualityGate()


class TestComplexityAnalyzer:
    """Test complexity analyzer."""

    def test_high_complexity_function(self, temp_dir):
        """Test detection of high complexity function."""
        analyzer = ComplexityAnalyzer()

        # Create file with high complexity function
        test_file = temp_dir / "complex.py"
        test_file.write_text("""
def complex_function(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        if x > 50:
                            if x > 60:
                                if x > 70:
                                    if x > 80:
                                        if x > 90:
                                            return "very high"
                                        return "high"
                                    return "medium"
                                return "low"
                            return "very low"
                        return "negative"
                    return "zero"
                return "small"
            return "tiny"
        return "minimal"
    return "none"
""")

        issues = analyzer.analyze_file(str(test_file))

        # Should detect high complexity
        complexity_issues = [i for i in issues if i.check_type == CheckType.COMPLEXITY]
        assert len(complexity_issues) > 0
        assert any("complexity" in i.message.lower() for i in complexity_issues)

    def test_long_function(self, temp_dir):
        """Test detection of long function."""
        analyzer = ComplexityAnalyzer()

        # Create file with long function
        test_file = temp_dir / "long.py"
        lines = ["def long_function():"]
        lines.extend([f"    x = {i}" for i in range(60)])
        lines.append("    return x")
        test_file.write_text("\n".join(lines))

        issues = analyzer.analyze_file(str(test_file))

        # Should detect long function
        length_issues = [i for i in issues if "long" in i.message.lower()]
        assert len(length_issues) > 0

    def test_simple_function(self, temp_dir):
        """Test that simple function passes."""
        analyzer = ComplexityAnalyzer()

        test_file = temp_dir / "simple.py"
        test_file.write_text("""
def simple_function(x, y):
    return x + y
""")

        issues = analyzer.analyze_file(str(test_file))

        # Should have no complexity issues
        assert len(issues) == 0


class TestSecurityScanner:
    """Test security scanner."""

    def test_detect_api_key(self, temp_dir):
        """Test detection of API key."""
        scanner = SecurityScanner()

        test_file = temp_dir / "secrets.py"
        test_file.write_text("""
API_KEY = "sk-1234567890abcdef"
password = "secret123"
""")

        issues = scanner.scan_file(str(test_file))

        # Should detect secrets
        secret_issues = [i for i in issues if i.severity == Severity.CRITICAL]
        assert len(secret_issues) >= 2

    def test_detect_dangerous_function(self, temp_dir):
        """Test detection of dangerous function."""
        scanner = SecurityScanner()

        test_file = temp_dir / "dangerous.py"
        test_file.write_text("""
def run_code(code):
    return eval(code)
""")

        issues = scanner.scan_file(str(test_file))

        # Should detect eval usage
        eval_issues = [i for i in issues if "eval" in i.message.lower()]
        assert len(eval_issues) > 0
        assert eval_issues[0].severity == Severity.HIGH

    def test_safe_code(self, temp_dir):
        """Test that safe code passes."""
        scanner = SecurityScanner()

        test_file = temp_dir / "safe.py"
        test_file.write_text("""
def safe_function(x):
    return x * 2
""")

        issues = scanner.scan_file(str(test_file))

        # Should have no security issues
        assert len(issues) == 0


class TestStyleChecker:
    """Test style checker."""

    def test_long_line(self, temp_dir):
        """Test detection of long line."""
        checker = StyleChecker()

        test_file = temp_dir / "style.py"
        long_line = "x = " + "a" * 150
        test_file.write_text(long_line)

        issues = checker.check_file(str(test_file), max_line_length=120)

        # Should detect long line
        line_issues = [i for i in issues if "length" in i.message.lower()]
        assert len(line_issues) > 0

    def test_trailing_whitespace(self, temp_dir):
        """Test detection of trailing whitespace."""
        checker = StyleChecker()

        test_file = temp_dir / "whitespace.py"
        test_file.write_text("x = 1   \n")

        issues = checker.check_file(str(test_file))

        # Should detect trailing whitespace
        ws_issues = [i for i in issues if "whitespace" in i.message.lower()]
        assert len(ws_issues) > 0

    def test_clean_code(self, temp_dir):
        """Test that clean code passes."""
        checker = StyleChecker()

        test_file = temp_dir / "clean.py"
        test_file.write_text("x = 1\n")

        issues = checker.check_file(str(test_file))

        # Should have no style issues
        assert len(issues) == 0


class TestDocumentationChecker:
    """Test documentation checker."""

    def test_missing_docstring(self, temp_dir):
        """Test detection of missing docstring."""
        checker = DocumentationChecker()

        test_file = temp_dir / "nodoc.py"
        test_file.write_text("""
def public_function(x):
    return x * 2

class PublicClass:
    def method(self):
        pass
""")

        issues = checker.check_file(str(test_file))

        # Should detect missing docstrings
        doc_issues = [i for i in issues if i.check_type == CheckType.DOCUMENTATION]
        assert len(doc_issues) >= 2

    def test_with_docstring(self, temp_dir):
        """Test that documented code passes."""
        checker = DocumentationChecker()

        test_file = temp_dir / "documented.py"
        test_file.write_text('''
def public_function(x):
    """Multiply by 2."""
    return x * 2

class PublicClass:
    """A public class."""
    def method(self):
        """A method."""
        pass
''')

        issues = checker.check_file(str(test_file))

        # Should have no documentation issues
        assert len(issues) == 0

    def test_private_function_no_docstring(self, temp_dir):
        """Test that private functions don't require docstrings."""
        checker = DocumentationChecker()

        test_file = temp_dir / "private.py"
        test_file.write_text("""
def _private_function(x):
    return x * 2
""")

        issues = checker.check_file(str(test_file))

        # Should not require docstring for private function
        assert len(issues) == 0


class TestQualityGate:
    """Test quality gate."""

    def test_check_multiple_files(self, temp_dir, quality_gate):
        """Test checking multiple files."""
        # Create test files
        file1 = temp_dir / "file1.py"
        file1.write_text("x = 1\n")

        file2 = temp_dir / "file2.py"
        file2.write_text("API_KEY = 'secret'\n")

        report = quality_gate.check_files([str(file1), str(file2)])

        # Should have issues from file2
        assert report.metrics["files_checked"] == 2
        assert report.metrics["total_issues"] > 0
        assert not report.passed  # Should fail due to secret

    def test_quality_gate_config(self, temp_dir):
        """Test quality gate with custom config."""
        config = QualityGateConfig(
            block_on_critical=True,
            block_on_high=False,
            block_on_medium=False
        )
        gate = QualityGate(config)

        # Create file with high severity issue (not critical)
        test_file = temp_dir / "test.py"
        test_file.write_text("result = eval(user_input)\n")

        report = gate.check_files([str(test_file)])

        # Should pass because we only block on critical
        # eval is HIGH severity, not CRITICAL
        assert report.passed

    def test_blocking_issues(self, temp_dir, quality_gate):
        """Test identification of blocking issues."""
        test_file = temp_dir / "blocking.py"
        test_file.write_text("API_KEY = 'sk-secret123'\n")

        report = quality_gate.check_files([str(test_file)])

        blocking = report.get_blocking_issues(quality_gate.config)

        # Should have blocking issues (critical severity)
        assert len(blocking) > 0
        assert all(i.severity == Severity.CRITICAL for i in blocking)

    def test_metrics_calculation(self, temp_dir, quality_gate):
        """Test metrics calculation."""
        test_file = temp_dir / "metrics.py"
        test_file.write_text("""
API_KEY = 'secret'
x = eval('1+1')
def long_function():
    pass
""" + "\n" * 60)

        report = quality_gate.check_files([str(test_file)])

        # Should have metrics
        assert "files_checked" in report.metrics
        assert "total_issues" in report.metrics
        assert "by_severity" in report.metrics
        assert "by_type" in report.metrics

    def test_non_code_files_skipped(self, temp_dir, quality_gate):
        """Test that non-code files are skipped."""
        text_file = temp_dir / "readme.txt"
        text_file.write_text("This is a text file")

        report = quality_gate.check_files([str(text_file)])

        # Should skip non-code file
        assert report.metrics["total_issues"] == 0

    def test_report_filtering(self, temp_dir, quality_gate):
        """Test report filtering methods."""
        test_file = temp_dir / "filter.py"
        test_file.write_text("""
API_KEY = 'secret'
result = eval('code')
x = 1
""" + " " * 150)

        report = quality_gate.check_files([str(test_file)])

        # Test filtering by severity
        critical = report.get_issues_by_severity(Severity.CRITICAL)
        assert len(critical) > 0

        # Test filtering by type
        security = report.get_issues_by_type(CheckType.SECURITY)
        assert len(security) > 0


class TestQualityGateConfig:
    """Test quality gate configuration."""

    def test_default_config(self):
        """Test default configuration."""
        config = QualityGateConfig()

        assert config.max_cyclomatic_complexity == 10
        assert config.min_line_coverage == 80.0
        assert config.block_on_critical is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = QualityGateConfig(
            max_cyclomatic_complexity=15,
            min_line_coverage=90.0,
            block_on_medium=True
        )

        assert config.max_cyclomatic_complexity == 15
        assert config.min_line_coverage == 90.0
        assert config.block_on_medium is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
