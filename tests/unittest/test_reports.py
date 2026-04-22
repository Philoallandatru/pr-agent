"""Tests for report generator."""

import json
import pytest
from pathlib import Path
from datetime import datetime, timezone

from pr_agent.reports import (
    ReportGenerator,
    ReportFormat,
    ReportSection,
    QualityMetrics,
    TrendData,
    Issue,
    Recommendation,
)


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_metrics():
    """Create sample quality metrics."""
    return QualityMetrics(
        lines_of_code=10000,
        test_coverage=85.5,
        complexity_score=12.3,
        maintainability_index=78.5,
        code_smells=15,
        bugs=3,
        vulnerabilities=1,
        technical_debt_hours=24.5,
        duplication_percentage=5.2
    )


@pytest.fixture
def sample_trends():
    """Create sample trend data."""
    return [
        TrendData(
            timestamp="2024-01-01T00:00:00Z",
            metric_name="test_coverage",
            value=80.0
        ),
        TrendData(
            timestamp="2024-01-02T00:00:00Z",
            metric_name="test_coverage",
            value=82.5
        ),
        TrendData(
            timestamp="2024-01-03T00:00:00Z",
            metric_name="test_coverage",
            value=85.5
        ),
    ]


@pytest.fixture
def sample_issues():
    """Create sample issues."""
    return [
        Issue(
            severity="HIGH",
            category="Security",
            file_path="src/auth.py",
            line_number=42,
            message="Potential SQL injection vulnerability",
            rule_id="SEC001"
        ),
        Issue(
            severity="MEDIUM",
            category="Code Smell",
            file_path="src/utils.py",
            line_number=15,
            message="Function too complex (complexity: 15)",
            rule_id="COMP001"
        ),
        Issue(
            severity="LOW",
            category="Style",
            file_path="src/main.py",
            line_number=8,
            message="Line too long (120 > 100)",
            rule_id="STYLE001"
        ),
    ]


@pytest.fixture
def sample_recommendations():
    """Create sample recommendations."""
    return [
        Recommendation(
            priority="HIGH",
            category="Testing",
            title="Increase test coverage",
            description="Add unit tests for critical authentication modules",
            estimated_effort="2-3 days",
            impact="High"
        ),
        Recommendation(
            priority="MEDIUM",
            category="Refactoring",
            title="Reduce code complexity",
            description="Refactor complex functions in utils.py",
            estimated_effort="1 day",
            impact="Medium"
        ),
    ]


@pytest.fixture
def report_generator(temp_output_dir):
    """Create report generator instance."""
    return ReportGenerator(output_dir=temp_output_dir)


class TestReportGenerator:
    """Test ReportGenerator class."""

    def test_initialization(self, temp_output_dir):
        """Test generator initialization."""
        generator = ReportGenerator(output_dir=temp_output_dir)
        assert generator.output_dir == temp_output_dir
        assert temp_output_dir.exists()

    def test_generate_json_report(
        self,
        report_generator,
        sample_metrics,
        sample_trends,
        sample_issues,
        sample_recommendations
    ):
        """Test JSON report generation."""
        output_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=sample_trends,
            issues=sample_issues,
            recommendations=sample_recommendations,
            format=ReportFormat.JSON
        )

        assert output_path.exists()
        assert output_path.suffix == ".json"

        # Verify content
        with open(output_path) as f:
            data = json.load(f)

        assert data["repository"] == "test/repo"
        assert "generated_at" in data
        assert data["metrics"]["lines_of_code"] == 10000
        assert data["metrics"]["test_coverage"] == 85.5
        assert len(data["trends"]) == 3
        assert len(data["issues"]) == 3
        assert len(data["recommendations"]) == 2

    def test_generate_markdown_report(
        self,
        report_generator,
        sample_metrics,
        sample_trends,
        sample_issues,
        sample_recommendations
    ):
        """Test Markdown report generation."""
        output_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=sample_trends,
            issues=sample_issues,
            recommendations=sample_recommendations,
            format=ReportFormat.MARKDOWN
        )

        assert output_path.exists()
        assert output_path.suffix == ".md"

        # Verify content
        content = output_path.read_text(encoding="utf-8")
        assert "# Code Quality Report: test/repo" in content
        assert "Executive Summary" in content
        assert "Quality Metrics" in content
        assert "Issues Found" in content
        assert "Recommendations" in content
        assert "10,000" in content  # LOC formatted
        assert "85.5%" in content  # Coverage

    def test_generate_html_report(
        self,
        report_generator,
        sample_metrics,
        sample_trends,
        sample_issues,
        sample_recommendations
    ):
        """Test HTML report generation."""
        output_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=sample_trends,
            issues=sample_issues,
            recommendations=sample_recommendations,
            format=ReportFormat.HTML
        )

        assert output_path.exists()
        assert output_path.suffix == ".html"

        # Verify content
        content = output_path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "Code Quality Report" in content
        assert "test/repo" in content
        assert "10,000" in content  # LOC
        assert "85.5%" in content  # Coverage
        assert "severity-high" in content  # Issue severity class

    def test_report_with_selected_sections(
        self,
        report_generator,
        sample_metrics,
        sample_trends,
        sample_issues,
        sample_recommendations
    ):
        """Test report with specific sections."""
        output_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=sample_trends,
            issues=sample_issues,
            recommendations=sample_recommendations,
            format=ReportFormat.MARKDOWN,
            sections=[ReportSection.SUMMARY, ReportSection.METRICS]
        )

        content = output_path.read_text(encoding="utf-8")
        assert "Executive Summary" in content
        assert "Quality Metrics" in content
        assert "Issues Found" not in content
        assert "Recommendations" not in content

    def test_report_with_metadata(
        self,
        report_generator,
        sample_metrics,
        sample_trends,
        sample_issues,
        sample_recommendations
    ):
        """Test report with custom metadata."""
        metadata = {
            "branch": "main",
            "commit": "abc123",
            "author": "test-user"
        }

        output_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=sample_trends,
            issues=sample_issues,
            recommendations=sample_recommendations,
            format=ReportFormat.JSON,
            metadata=metadata
        )

        with open(output_path) as f:
            data = json.load(f)

        assert data["metadata"]["branch"] == "main"
        assert data["metadata"]["commit"] == "abc123"
        assert data["metadata"]["author"] == "test-user"

    def test_empty_trends(
        self,
        report_generator,
        sample_metrics,
        sample_issues,
        sample_recommendations
    ):
        """Test report with no trend data."""
        output_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=[],
            issues=sample_issues,
            recommendations=sample_recommendations,
            format=ReportFormat.MARKDOWN
        )

        content = output_path.read_text(encoding="utf-8")
        assert "Quality Trends" not in content

    def test_empty_issues(
        self,
        report_generator,
        sample_metrics,
        sample_trends,
        sample_recommendations
    ):
        """Test report with no issues."""
        output_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=sample_trends,
            issues=[],
            recommendations=sample_recommendations,
            format=ReportFormat.MARKDOWN
        )

        content = output_path.read_text(encoding="utf-8")
        assert "Issues Found" not in content

    def test_empty_recommendations(
        self,
        report_generator,
        sample_metrics,
        sample_trends,
        sample_issues
    ):
        """Test report with no recommendations."""
        output_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=sample_trends,
            issues=sample_issues,
            recommendations=[],
            format=ReportFormat.MARKDOWN
        )

        content = output_path.read_text(encoding="utf-8")
        assert "Recommendations" not in content

    def test_multiple_reports(
        self,
        report_generator,
        sample_metrics,
        sample_trends,
        sample_issues,
        sample_recommendations
    ):
        """Test generating multiple reports."""
        # Generate JSON report
        json_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=sample_trends,
            issues=sample_issues,
            recommendations=sample_recommendations,
            format=ReportFormat.JSON
        )

        # Generate Markdown report
        md_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=sample_trends,
            issues=sample_issues,
            recommendations=sample_recommendations,
            format=ReportFormat.MARKDOWN
        )

        # Generate HTML report
        html_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=sample_trends,
            issues=sample_issues,
            recommendations=sample_recommendations,
            format=ReportFormat.HTML
        )

        assert json_path.exists()
        assert md_path.exists()
        assert html_path.exists()
        assert json_path != md_path != html_path

    def test_issue_severity_grouping(
        self,
        report_generator,
        sample_metrics,
        sample_trends,
        sample_recommendations
    ):
        """Test issues are grouped by severity."""
        issues = [
            Issue("CRITICAL", "Security", "file1.py", 1, "Critical issue"),
            Issue("HIGH", "Bug", "file2.py", 2, "High issue"),
            Issue("HIGH", "Bug", "file3.py", 3, "Another high issue"),
            Issue("MEDIUM", "Smell", "file4.py", 4, "Medium issue"),
            Issue("LOW", "Style", "file5.py", 5, "Low issue"),
        ]

        output_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=sample_trends,
            issues=issues,
            recommendations=sample_recommendations,
            format=ReportFormat.MARKDOWN
        )

        content = output_path.read_text(encoding="utf-8")
        assert "### CRITICAL (1 issues)" in content
        assert "### HIGH (2 issues)" in content
        assert "### MEDIUM (1 issues)" in content
        assert "### LOW (1 issues)" in content

    def test_large_issue_list_truncation(
        self,
        report_generator,
        sample_metrics,
        sample_trends,
        sample_recommendations
    ):
        """Test large issue lists are truncated."""
        # Create 25 issues
        issues = [
            Issue("HIGH", "Bug", f"file{i}.py", i, f"Issue {i}")
            for i in range(25)
        ]

        output_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=sample_trends,
            issues=issues,
            recommendations=sample_recommendations,
            format=ReportFormat.MARKDOWN
        )

        content = output_path.read_text(encoding="utf-8")
        # Should show "...and 15 more" for markdown (limit 10)
        assert "and 15 more" in content

    def test_html_styles_included(self, report_generator, sample_metrics):
        """Test HTML report includes CSS styles."""
        output_path = report_generator.generate_report(
            repository="test/repo",
            metrics=sample_metrics,
            trends=[],
            issues=[],
            recommendations=[],
            format=ReportFormat.HTML
        )

        content = output_path.read_text(encoding="utf-8")
        assert "<style>" in content
        assert "font-family" in content
        assert ".metric-card" in content
        assert ".severity-high" in content

    def test_invalid_format(
        self,
        report_generator,
        sample_metrics,
        sample_trends,
        sample_issues,
        sample_recommendations
    ):
        """Test error handling for invalid format."""
        # Create a mock invalid format by bypassing enum
        class InvalidFormat:
            def __eq__(self, other):
                return False

        with pytest.raises(ValueError, match="Unsupported format"):
            report_generator.generate_report(
                repository="test/repo",
                metrics=sample_metrics,
                trends=sample_trends,
                issues=sample_issues,
                recommendations=sample_recommendations,
                format=InvalidFormat()  # type: ignore
            )


class TestQualityMetrics:
    """Test QualityMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating quality metrics."""
        metrics = QualityMetrics(
            lines_of_code=1000,
            test_coverage=80.0,
            complexity_score=10.0,
            maintainability_index=75.0,
            code_smells=5,
            bugs=2,
            vulnerabilities=1,
            technical_debt_hours=10.0,
            duplication_percentage=3.0
        )

        assert metrics.lines_of_code == 1000
        assert metrics.test_coverage == 80.0
        assert metrics.bugs == 2


class TestTrendData:
    """Test TrendData dataclass."""

    def test_trend_creation(self):
        """Test creating trend data."""
        trend = TrendData(
            timestamp="2024-01-01T00:00:00Z",
            metric_name="coverage",
            value=85.5
        )

        assert trend.timestamp == "2024-01-01T00:00:00Z"
        assert trend.metric_name == "coverage"
        assert trend.value == 85.5


class TestIssue:
    """Test Issue dataclass."""

    def test_issue_creation(self):
        """Test creating an issue."""
        issue = Issue(
            severity="HIGH",
            category="Security",
            file_path="src/auth.py",
            line_number=42,
            message="SQL injection risk",
            rule_id="SEC001"
        )

        assert issue.severity == "HIGH"
        assert issue.category == "Security"
        assert issue.line_number == 42
        assert issue.rule_id == "SEC001"

    def test_issue_without_rule_id(self):
        """Test creating issue without rule ID."""
        issue = Issue(
            severity="LOW",
            category="Style",
            file_path="src/main.py",
            line_number=10,
            message="Line too long"
        )

        assert issue.rule_id is None


class TestRecommendation:
    """Test Recommendation dataclass."""

    def test_recommendation_creation(self):
        """Test creating a recommendation."""
        rec = Recommendation(
            priority="HIGH",
            category="Testing",
            title="Add tests",
            description="Increase test coverage",
            estimated_effort="2 days",
            impact="High"
        )

        assert rec.priority == "HIGH"
        assert rec.category == "Testing"
        assert rec.estimated_effort == "2 days"
