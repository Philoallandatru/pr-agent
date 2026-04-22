"""
Integration tests for code review report generation system.

Tests report generation with realistic data scenarios.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import shutil
import json

from pr_agent.report_generator import (
    ReportGenerator,
    ReportType,
    ReportFormat,
    ReportConfig
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def report_generator(temp_dir):
    """Create report generator."""
    return ReportGenerator(output_dir=temp_dir)


class TestReportGeneration:
    """Test comprehensive report generation scenarios."""

    def test_complete_review_summary_workflow(self, report_generator):
        """Test complete workflow for review summary report."""

        # Simulate collected metrics data
        data = {
            'total_reviews': 150,
            'avg_duration': 18.5,
            'total_comments': 680,
            'reviews_by_status': {
                'approved': 90,
                'changes_requested': 45,
                'pending': 15
            }
        }

        # Generate JSON report
        json_config = ReportConfig(
            report_id="summary-json",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Monthly Review Summary",
            description="Comprehensive review activity for January 2024",
            format=ReportFormat.JSON,
            include_charts=True
        )

        json_report = report_generator.generate_report(json_config, data)
        assert json_report is not None
        assert json_report.content is not None

        # Verify JSON structure
        content = json.loads(json_report.content)
        assert content['title'] == "Monthly Review Summary"
        assert len(content['sections']) > 0

        # Generate HTML report
        html_config = ReportConfig(
            report_id="summary-html",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Monthly Review Summary",
            format=ReportFormat.HTML
        )

        html_report = report_generator.generate_report(html_config, data)
        assert html_report.file_path is not None
        assert Path(html_report.file_path).exists()

        # Generate Markdown report
        md_config = ReportConfig(
            report_id="summary-md",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Monthly Review Summary",
            format=ReportFormat.MARKDOWN
        )

        md_report = report_generator.generate_report(md_config, data)
        assert md_report.file_path is not None

        # Verify all reports are listed
        reports = report_generator.list_reports()
        assert len(reports) == 3

    def test_quality_trends_analysis(self, report_generator):
        """Test quality trends report generation."""

        data = {
            'quality_scores': {
                'dates': [
                    '2024-01-01', '2024-01-08', '2024-01-15',
                    '2024-01-22', '2024-01-29'
                ],
                'scores': [82, 85, 87, 89, 91]
            }
        }

        config = ReportConfig(
            report_id="quality-trends",
            report_type=ReportType.QUALITY_TRENDS,
            title="Q1 Quality Trends",
            format=ReportFormat.HTML,
            include_charts=True
        )

        report = report_generator.generate_report(config, data)
        assert report is not None

        # Verify HTML contains chart data
        content = Path(report.file_path).read_text()
        assert "Quality Trends" in content
        assert "2024-01-01" in content

    def test_efficiency_metrics_report(self, report_generator):
        """Test efficiency analysis report."""

        data = {
            'time_to_first_comment': {
                'average': 2.5,
                'median': 2.0,
                'p90': 4.5
            },
            'review_duration': {
                '0-4h': 25,
                '4-8h': 35,
                '8-24h': 30,
                '24h+': 10
            }
        }

        config = ReportConfig(
            report_id="efficiency",
            report_type=ReportType.EFFICIENCY_ANALYSIS,
            title="Review Efficiency Analysis",
            format=ReportFormat.JSON
        )

        report = report_generator.generate_report(config, data)
        content = json.loads(report.content)

        assert len(content['sections']) > 0
        assert any('first_comment' in s['section_id'] for s in content['sections'])

    def test_issue_distribution_report(self, report_generator):
        """Test issue distribution report."""

        data = {
            'issues_by_severity': {
                'critical': 8,
                'high': 22,
                'medium': 45,
                'low': 75
            },
            'issues_by_category': {
                'security': 15,
                'performance': 28,
                'style': 52,
                'bugs': 55
            }
        }

        config = ReportConfig(
            report_id="issues",
            report_type=ReportType.ISSUE_DISTRIBUTION,
            title="Issue Distribution Report",
            format=ReportFormat.HTML,
            include_charts=True
        )

        report = report_generator.generate_report(config, data)
        assert report.file_path is not None

        content = Path(report.file_path).read_text()
        assert "Issue Distribution" in content

    def test_team_performance_report(self, report_generator):
        """Test team performance report."""

        data = {
            'team_metrics': {
                'total_members': 12,
                'total_reviews': 150,
                'avg_reviews_per_member': 12.5,
                'team_quality_score': 87.3
            },
            'top_reviewers': {
                'alice': 32,
                'bob': 28,
                'charlie': 24,
                'david': 20,
                'eve': 18
            }
        }

        config = ReportConfig(
            report_id="team",
            report_type=ReportType.TEAM_PERFORMANCE,
            title="Team Performance Report",
            format=ReportFormat.MARKDOWN
        )

        report = report_generator.generate_report(config, data)
        assert report.file_path is not None

        content = Path(report.file_path).read_text()
        assert "Team Performance" in content
        assert "Total Team Members: 12" in content

    def test_individual_performance_report(self, report_generator):
        """Test individual performance report."""

        data = {
            'individual_metrics': {
                'total_reviews': 32,
                'avg_quality_score': 89.5,
                'total_comments': 156,
                'issues_found': 68,
                'avg_response_time': 1.8
            }
        }

        config = ReportConfig(
            report_id="individual",
            report_type=ReportType.INDIVIDUAL_PERFORMANCE,
            title="Alice's Performance Report",
            format=ReportFormat.HTML
        )

        report = report_generator.generate_report(config, data)
        assert report.file_path is not None

        content = Path(report.file_path).read_text()
        assert "Alice's Performance" in content
        assert "Total Reviews: 32" in content


class TestReportFormats:
    """Test different report formats."""

    def test_json_format_structure(self, report_generator):
        """Test JSON format structure."""
        data = {'total_reviews': 100}

        config = ReportConfig(
            report_id="json-test",
            report_type=ReportType.REVIEW_SUMMARY,
            title="JSON Test",
            format=ReportFormat.JSON
        )

        report = report_generator.generate_report(config, data)
        content = json.loads(report.content)

        assert 'report_id' in content
        assert 'title' in content
        assert 'sections' in content
        assert isinstance(content['sections'], list)

    def test_markdown_format_structure(self, report_generator):
        """Test Markdown format structure."""
        data = {'total_reviews': 100}

        config = ReportConfig(
            report_id="md-test",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Markdown Test",
            format=ReportFormat.MARKDOWN
        )

        report = report_generator.generate_report(config, data)
        content = Path(report.file_path).read_text()

        assert "# Markdown Test" in content
        assert "Generated at:" in content

    def test_html_format_structure(self, report_generator):
        """Test HTML format structure."""
        data = {'total_reviews': 100}

        config = ReportConfig(
            report_id="html-test",
            report_type=ReportType.REVIEW_SUMMARY,
            title="HTML Test",
            format=ReportFormat.HTML
        )

        report = report_generator.generate_report(config, data)
        content = Path(report.file_path).read_text()

        assert "<!DOCTYPE html>" in content
        assert "<title>HTML Test</title>" in content
        assert "</html>" in content


class TestReportManagement:
    """Test report management features."""

    def test_report_retrieval(self, report_generator):
        """Test retrieving generated reports."""
        data = {'total_reviews': 50}

        config = ReportConfig(
            report_id="retrieve-test",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Retrieve Test",
            format=ReportFormat.JSON
        )

        report_generator.generate_report(config, data)

        # Retrieve by ID
        report = report_generator.get_report("retrieve-test")
        assert report is not None
        assert report.report_id == "retrieve-test"
        assert report.title == "Retrieve Test"

    def test_report_filtering(self, report_generator):
        """Test filtering reports."""
        # Generate multiple reports
        for i in range(3):
            config = ReportConfig(
                report_id=f"filter-{i}",
                report_type=ReportType.REVIEW_SUMMARY if i % 2 == 0 else ReportType.QUALITY_TRENDS,
                title=f"Report {i}",
                format=ReportFormat.JSON if i % 2 == 0 else ReportFormat.HTML
            )
            report_generator.generate_report(config, {'total_reviews': 10})

        # Filter by type
        summaries = report_generator.list_reports(report_type=ReportType.REVIEW_SUMMARY)
        assert len(summaries) == 2

        # Filter by format
        json_reports = report_generator.list_reports(format=ReportFormat.JSON)
        assert len(json_reports) == 2

    def test_report_metadata(self, report_generator):
        """Test report metadata."""
        data = {'total_reviews': 50}

        config = ReportConfig(
            report_id="metadata-test",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Metadata Test",
            format=ReportFormat.JSON,
            metadata={
                'author': 'system',
                'version': '1.0',
                'tags': ['monthly', 'summary']
            }
        )

        report = report_generator.generate_report(config, data)
        assert report.metadata['author'] == 'system'
        assert report.metadata['version'] == '1.0'


class TestReportPerformance:
    """Test report generation performance."""

    def test_large_dataset_performance(self, report_generator):
        """Test performance with large dataset."""
        # Simulate large dataset
        data = {
            'total_reviews': 1000,
            'avg_duration': 15.5,
            'total_comments': 4500,
            'reviews_by_status': {
                'approved': 600,
                'changes_requested': 300,
                'pending': 100
            },
            'quality_scores': {
                'dates': [f"2024-01-{i:02d}" for i in range(1, 32)],
                'scores': [80 + (i % 20) for i in range(31)]
            }
        }

        config = ReportConfig(
            report_id="large-dataset",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Large Dataset Report",
            format=ReportFormat.HTML,
            include_charts=True
        )

        import time
        start_time = time.time()
        report = report_generator.generate_report(config, data)
        generation_time = time.time() - start_time

        assert report is not None
        assert generation_time < 5.0  # Should complete in under 5 seconds

    def test_multiple_reports_generation(self, report_generator):
        """Test generating multiple reports."""
        data = {'total_reviews': 50}

        import time
        start_time = time.time()

        for i in range(10):
            config = ReportConfig(
                report_id=f"multi-{i}",
                report_type=ReportType.REVIEW_SUMMARY,
                title=f"Report {i}",
                format=ReportFormat.JSON
            )
            report_generator.generate_report(config, data)

        generation_time = time.time() - start_time

        assert generation_time < 10.0  # 10 reports in under 10 seconds
        assert len(report_generator.list_reports()) == 10


class TestReportWithDateRanges:
    """Test reports with date ranges."""

    def test_date_range_in_report(self, report_generator):
        """Test date range inclusion in report."""
        data = {'total_reviews': 50}

        config = ReportConfig(
            report_id="date-range",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Date Range Report",
            format=ReportFormat.MARKDOWN
        )

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        report = report_generator.generate_report(config, data, start_date, end_date)
        content = Path(report.file_path).read_text()

        assert "2024-01-01" in content
        assert "2024-01-31" in content

    def test_multiple_time_periods(self, report_generator):
        """Test reports for multiple time periods."""
        data = {'total_reviews': 50}

        periods = [
            ("week1", datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 1, 7, tzinfo=timezone.utc)),
            ("week2", datetime(2024, 1, 8, tzinfo=timezone.utc), datetime(2024, 1, 14, tzinfo=timezone.utc)),
            ("week3", datetime(2024, 1, 15, tzinfo=timezone.utc), datetime(2024, 1, 21, tzinfo=timezone.utc)),
        ]

        for period_id, start, end in periods:
            config = ReportConfig(
                report_id=f"period-{period_id}",
                report_type=ReportType.REVIEW_SUMMARY,
                title=f"Report for {period_id}",
                format=ReportFormat.JSON
            )
            report = report_generator.generate_report(config, data, start, end)
            assert report is not None

        reports = report_generator.list_reports()
        assert len(reports) == 3
