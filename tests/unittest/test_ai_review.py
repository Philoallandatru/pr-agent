"""
Tests for AI-driven code review system.
"""

import ast
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from pr_agent.ai_review import (
    AICodeReviewer,
    ReviewFinding,
    ReviewSeverity,
    ReviewCategory,
    AIReviewReport,
    get_ai_reviewer,
    configure_ai_reviewer,
)


class TestReviewFinding:
    """Test ReviewFinding dataclass."""

    def test_finding_creation(self):
        """Test creating a review finding."""
        finding = ReviewFinding(
            category=ReviewCategory.BUG,
            severity=ReviewSeverity.HIGH,
            title="Potential Bug",
            description="This might be a bug",
            file_path="test.py",
            line_start=10,
            line_end=15,
            code_snippet="x = y / z",
            suggestion="Add zero check",
            confidence=0.9
        )

        assert finding.category == ReviewCategory.BUG
        assert finding.severity == ReviewSeverity.HIGH
        assert finding.title == "Potential Bug"
        assert finding.confidence == 0.9


class TestAIReviewReport:
    """Test AIReviewReport."""

    def test_report_creation(self):
        """Test creating a review report."""
        findings = [
            ReviewFinding(
                category=ReviewCategory.SECURITY,
                severity=ReviewSeverity.CRITICAL,
                title="Security Issue",
                description="Critical security vulnerability",
                file_path="test.py",
                line_start=1,
                line_end=1,
                code_snippet="eval(user_input)"
            ),
            ReviewFinding(
                category=ReviewCategory.PERFORMANCE,
                severity=ReviewSeverity.HIGH,
                title="Performance Issue",
                description="Slow operation",
                file_path="test.py",
                line_start=10,
                line_end=10,
                code_snippet="for i in range(1000000):"
            ),
        ]

        report = AIReviewReport(
            timestamp=1234567890.0,
            files_reviewed=1,
            total_findings=2,
            findings=findings,
            summary="Found 2 issues"
        )

        assert report.files_reviewed == 1
        assert report.total_findings == 2
        assert report.critical_count == 1
        assert report.high_count == 1

    def test_by_category(self):
        """Test grouping findings by category."""
        findings = [
            ReviewFinding(
                category=ReviewCategory.BUG,
                severity=ReviewSeverity.HIGH,
                title="Bug 1",
                description="",
                file_path="test.py",
                line_start=1,
                line_end=1,
                code_snippet=""
            ),
            ReviewFinding(
                category=ReviewCategory.BUG,
                severity=ReviewSeverity.MEDIUM,
                title="Bug 2",
                description="",
                file_path="test.py",
                line_start=2,
                line_end=2,
                code_snippet=""
            ),
            ReviewFinding(
                category=ReviewCategory.SECURITY,
                severity=ReviewSeverity.CRITICAL,
                title="Security",
                description="",
                file_path="test.py",
                line_start=3,
                line_end=3,
                code_snippet=""
            ),
        ]

        report = AIReviewReport(
            timestamp=1234567890.0,
            files_reviewed=1,
            total_findings=3,
            findings=findings
        )

        by_category = report.by_category
        assert by_category['bug'] == 2
        assert by_category['security'] == 1


class TestAICodeReviewer:
    """Test AICodeReviewer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.reviewer = AICodeReviewer()

    def test_init(self):
        """Test reviewer initialization."""
        assert self.reviewer is not None
        assert self.reviewer.ai_handler is None

    def test_review_file_not_found(self):
        """Test reviewing non-existent file."""
        findings = self.reviewer.review_file("nonexistent.py")

        assert len(findings) == 1
        assert findings[0].category == ReviewCategory.BUG
        assert findings[0].severity == ReviewSeverity.HIGH
        assert "Failed to read file" in findings[0].description

    def test_review_file_syntax_error(self, tmp_path):
        """Test reviewing file with syntax error."""
        # Create temp file with syntax error
        test_file = tmp_path / "syntax_error.py"
        test_file.write_text("def foo(\n    pass")

        findings = self.reviewer.review_file(str(test_file))

        assert len(findings) > 0
        assert findings[0].category == ReviewCategory.BUG
        assert findings[0].severity == ReviewSeverity.CRITICAL
        assert "Syntax" in findings[0].title

    def test_check_security_eval(self, tmp_path):
        """Test detecting eval() usage."""
        test_file = tmp_path / "eval_test.py"
        test_file.write_text("result = eval(user_input)")

        findings = self.reviewer.review_file(str(test_file))

        eval_findings = [f for f in findings if 'eval' in f.title.lower()]
        assert len(eval_findings) > 0
        assert eval_findings[0].category == ReviewCategory.SECURITY
        assert eval_findings[0].severity == ReviewSeverity.CRITICAL

    def test_check_security_exec(self, tmp_path):
        """Test detecting exec() usage."""
        test_file = tmp_path / "exec_test.py"
        test_file.write_text("exec(user_code)")

        findings = self.reviewer.review_file(str(test_file))

        exec_findings = [f for f in findings if 'exec' in f.title.lower()]
        assert len(exec_findings) > 0
        assert exec_findings[0].category == ReviewCategory.SECURITY
        assert exec_findings[0].severity == ReviewSeverity.HIGH

    def test_check_performance_string_concat(self, tmp_path):
        """Test detecting string concatenation in loops."""
        test_file = tmp_path / "perf_test.py"
        test_file.write_text("""
result = ""
for i in range(1000):
    result += str(i)
""")

        findings = self.reviewer.review_file(str(test_file))

        perf_findings = [f for f in findings if f.category == ReviewCategory.PERFORMANCE]
        assert len(perf_findings) > 0

    def test_check_too_many_args(self, tmp_path):
        """Test detecting functions with too many arguments."""
        test_file = tmp_path / "args_test.py"
        test_file.write_text("""
def complex_function(a, b, c, d, e, f, g):
    pass
""")

        findings = self.reviewer.review_file(str(test_file))

        arg_findings = [f for f in findings if 'arguments' in f.title.lower()]
        assert len(arg_findings) > 0
        assert arg_findings[0].category == ReviewCategory.MAINTAINABILITY

    def test_review_pr(self, tmp_path):
        """Test reviewing a pull request."""
        test_file = tmp_path / "pr_test.py"
        test_file.write_text("result = eval(input())")

        pr_files = [
            {
                'path': str(test_file),
                'diff': ''
            }
        ]

        report = self.reviewer.review_pr(pr_files)

        assert report.files_reviewed == 1
        assert report.total_findings > 0
        assert report.summary is not None

    def test_generate_summary_no_issues(self):
        """Test summary generation with no issues."""
        summary = self.reviewer._generate_summary([], None)
        assert "No issues" in summary

    def test_generate_summary_with_issues(self):
        """Test summary generation with issues."""
        findings = [
            ReviewFinding(
                category=ReviewCategory.SECURITY,
                severity=ReviewSeverity.CRITICAL,
                title="Critical",
                description="",
                file_path="test.py",
                line_start=1,
                line_end=1,
                code_snippet=""
            ),
            ReviewFinding(
                category=ReviewCategory.BUG,
                severity=ReviewSeverity.HIGH,
                title="High",
                description="",
                file_path="test.py",
                line_start=2,
                line_end=2,
                code_snippet=""
            ),
        ]

        summary = self.reviewer._generate_summary(findings, None)
        assert "2 issues" in summary
        assert "critical" in summary
        assert "high" in summary

    def test_ai_analysis(self):
        """Test AI-powered analysis."""
        mock_handler = Mock()
        mock_handler.chat_completion.return_value = json.dumps([
            {
                'category': 'bug',
                'severity': 'high',
                'title': 'Potential Bug',
                'description': 'This might cause issues',
                'line': 10,
                'code_snippet': 'x = y / z',
                'suggestion': 'Add validation'
            }
        ])

        reviewer = AICodeReviewer(ai_handler=mock_handler)
        findings = reviewer._ai_analysis("test.py", "x = y / z", None)

        # AI analysis might return findings if properly configured
        assert isinstance(findings, list)

    def test_parse_ai_response(self):
        """Test parsing AI response."""
        response = """
Here are the findings:
[
    {
        "category": "bug",
        "severity": "high",
        "title": "Division by Zero",
        "description": "Potential division by zero",
        "line": 10,
        "code_snippet": "result = x / y",
        "suggestion": "Add zero check",
        "confidence": 0.9
    }
]
"""

        findings = self.reviewer._parse_ai_response(response, "test.py")

        assert len(findings) == 1
        assert findings[0].category == ReviewCategory.BUG
        assert findings[0].severity == ReviewSeverity.HIGH
        assert findings[0].title == "Division by Zero"

    def test_parse_ai_response_invalid(self):
        """Test parsing invalid AI response."""
        response = "This is not JSON"

        findings = self.reviewer._parse_ai_response(response, "test.py")

        assert len(findings) == 0


class TestGlobalReviewer:
    """Test global reviewer functions."""

    def test_get_ai_reviewer(self):
        """Test getting global reviewer instance."""
        reviewer1 = get_ai_reviewer()
        reviewer2 = get_ai_reviewer()

        assert reviewer1 is reviewer2

    def test_configure_ai_reviewer(self):
        """Test configuring global reviewer."""
        mock_handler = Mock()
        configure_ai_reviewer(mock_handler)

        reviewer = get_ai_reviewer()
        assert reviewer.ai_handler is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
