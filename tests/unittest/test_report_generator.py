"""Tests for report generator."""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import tempfile
import shutil

from pr_agent.report_generator import (
    ReportGenerator,
    ReportType,
    ReportFormat,
    ReportConfig,
    ReportSection,
    ChartData,
    GeneratedReport
)


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def generator(temp_output_dir):
    """Create report generator."""
    return ReportGenerator(output_dir=temp_output_dir)


@pytest.fixture
def sample_data():
    """Sample report data."""
    return {
        'total_reviews': 100,
        'avg_duration': 24.5,
        'total_comments': 450,
        'reviews_by_status': {
            'approved': 60,
            'changes_requested': 30,
            'pending': 10
        },
        'quality_scores': {
            'dates': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'scores': [85, 87, 90]
        },
        'time_to_first_comment': {
            'average': 2.5
        },
        'review_duration': {
            '0-4h': 20,
            '4-8h': 30,
            '8-24h': 35,
            '24h+': 15
        },
        'issues_by_severity': {
            'critical': 5,
            'high': 15,
            'medium': 30,
            'low': 50
        },
        'issues_by_category': {
            'security': 10,
            'performance': 20,
            'style': 40,
            'bugs': 30
        },
        'team_metrics': {
            'total_members': 10,
            'total_reviews': 100,
            'avg_reviews_per_member': 10.0,
            'team_quality_score': 85.5
        },
        'top_reviewers': {
            'alice': 25,
            'bob': 20,
            'charlie': 15
        },
        'individual_metrics': {
            'total_reviews': 25,
            'avg_quality_score': 88.5,
            'total_comments': 120,
            'issues_found': 45,
            'avg_response_time': 2.3
        }
    }


class TestReportConfig:
    """Test report configuration."""

    def test_create_config(self):
        """Test creating report config."""
        config = ReportConfig(
            report_id="test-1",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Test Report",
            description="Test description",
            format=ReportFormat.HTML
        )

        assert config.report_id == "test-1"
        assert config.report_type == ReportType.REVIEW_SUMMARY
        assert config.title == "Test Report"
        assert config.format == ReportFormat.HTML

    def test_default_values(self):
        """Test default configuration values."""
        config = ReportConfig(
            report_id="test-1",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Test Report"
        )

        assert config.format == ReportFormat.HTML
        assert config.include_charts is True
        assert config.include_raw_data is False


class TestChartData:
    """Test chart data."""

    def test_create_chart(self):
        """Test creating chart data."""
        chart = ChartData(
            chart_id="chart-1",
            chart_type="bar",
            title="Test Chart",
            data={'labels': ['A', 'B'], 'values': [10, 20]}
        )

        assert chart.chart_id == "chart-1"
        assert chart.chart_type == "bar"
        assert chart.title == "Test Chart"
        assert 'labels' in chart.data


class TestReportSection:
    """Test report section."""

    def test_create_section(self):
        """Test creating report section."""
        section = ReportSection(
            section_id="section-1",
            title="Test Section",
            content="Test content"
        )

        assert section.section_id == "section-1"
        assert section.title == "Test Section"
        assert section.content == "Test content"

    def test_section_with_charts(self):
        """Test section with charts."""
        chart = ChartData(
            chart_id="chart-1",
            chart_type="line",
            title="Test Chart",
            data={}
        )

        section = ReportSection(
            section_id="section-1",
            title="Test Section",
            content="Test content",
            charts=[chart]
        )

        assert len(section.charts) == 1
        assert section.charts[0].chart_id == "chart-1"


class TestReportGenerator:
    """Test report generator."""

    def test_create_generator(self, temp_output_dir):
        """Test creating generator."""
        generator = ReportGenerator(output_dir=temp_output_dir)
        assert generator.output_dir.exists()

    def test_register_template(self, generator):
        """Test registering template."""
        template = {'sections': ['overview', 'details']}
        generator.register_template("template-1", template)

        assert "template-1" in generator.templates
        assert generator.templates["template-1"] == template

    def test_generate_review_summary_json(self, generator, sample_data):
        """Test generating review summary in JSON format."""
        config = ReportConfig(
            report_id="report-1",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Review Summary",
            format=ReportFormat.JSON
        )

        report = generator.generate_report(config, sample_data)

        assert report.report_id == "report-1"
        assert report.report_type == ReportType.REVIEW_SUMMARY
        assert report.format == ReportFormat.JSON
        assert report.content is not None

        # Verify JSON is valid
        data = json.loads(report.content)
        assert data['title'] == "Review Summary"
        assert 'sections' in data

    def test_generate_review_summary_markdown(self, generator, sample_data):
        """Test generating review summary in Markdown format."""
        config = ReportConfig(
            report_id="report-2",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Review Summary",
            format=ReportFormat.MARKDOWN
        )

        report = generator.generate_report(config, sample_data)

        assert report.format == ReportFormat.MARKDOWN
        assert report.file_path is not None
        assert Path(report.file_path).exists()

        # Verify file content
        content = Path(report.file_path).read_text()
        assert "# Review Summary" in content
        assert "Total Reviews: 100" in content

    def test_generate_review_summary_html(self, generator, sample_data):
        """Test generating review summary in HTML format."""
        config = ReportConfig(
            report_id="report-3",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Review Summary",
            format=ReportFormat.HTML
        )

        report = generator.generate_report(config, sample_data)

        assert report.format == ReportFormat.HTML
        assert report.file_path is not None

        # Verify HTML content
        content = Path(report.file_path).read_text()
        assert "<html>" in content
        assert "<title>Review Summary</title>" in content
        assert "Total Reviews: 100" in content

    def test_generate_quality_trends(self, generator, sample_data):
        """Test generating quality trends report."""
        config = ReportConfig(
            report_id="report-4",
            report_type=ReportType.QUALITY_TRENDS,
            title="Quality Trends",
            format=ReportFormat.JSON
        )

        report = generator.generate_report(config, sample_data)

        assert report.report_type == ReportType.QUALITY_TRENDS
        data = json.loads(report.content)
        assert len(data['sections']) > 0

    def test_generate_efficiency_analysis(self, generator, sample_data):
        """Test generating efficiency analysis report."""
        config = ReportConfig(
            report_id="report-5",
            report_type=ReportType.EFFICIENCY_ANALYSIS,
            title="Efficiency Analysis",
            format=ReportFormat.JSON
        )

        report = generator.generate_report(config, sample_data)

        assert report.report_type == ReportType.EFFICIENCY_ANALYSIS
        data = json.loads(report.content)
        sections = data['sections']
        assert any(s['section_id'] == 'first_comment' for s in sections)

    def test_generate_issue_distribution(self, generator, sample_data):
        """Test generating issue distribution report."""
        config = ReportConfig(
            report_id="report-6",
            report_type=ReportType.ISSUE_DISTRIBUTION,
            title="Issue Distribution",
            format=ReportFormat.JSON
        )

        report = generator.generate_report(config, sample_data)

        assert report.report_type == ReportType.ISSUE_DISTRIBUTION
        data = json.loads(report.content)
        sections = data['sections']
        assert any(s['section_id'] == 'severity' for s in sections)

    def test_generate_team_performance(self, generator, sample_data):
        """Test generating team performance report."""
        config = ReportConfig(
            report_id="report-7",
            report_type=ReportType.TEAM_PERFORMANCE,
            title="Team Performance",
            format=ReportFormat.JSON
        )

        report = generator.generate_report(config, sample_data)

        assert report.report_type == ReportType.TEAM_PERFORMANCE
        data = json.loads(report.content)
        sections = data['sections']
        assert any(s['section_id'] == 'team_metrics' for s in sections)

    def test_generate_individual_performance(self, generator, sample_data):
        """Test generating individual performance report."""
        config = ReportConfig(
            report_id="report-8",
            report_type=ReportType.INDIVIDUAL_PERFORMANCE,
            title="Individual Performance",
            format=ReportFormat.JSON
        )

        report = generator.generate_report(config, sample_data)

        assert report.report_type == ReportType.INDIVIDUAL_PERFORMANCE
        data = json.loads(report.content)
        sections = data['sections']
        assert any(s['section_id'] == 'individual_metrics' for s in sections)

    def test_generate_with_date_range(self, generator, sample_data):
        """Test generating report with date range."""
        config = ReportConfig(
            report_id="report-9",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Review Summary",
            format=ReportFormat.MARKDOWN
        )

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        report = generator.generate_report(config, sample_data, start_date, end_date)

        content = Path(report.file_path).read_text()
        assert "2024-01-01" in content
        assert "2024-01-31" in content

    def test_get_report(self, generator, sample_data):
        """Test getting generated report."""
        config = ReportConfig(
            report_id="report-10",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Test Report",
            format=ReportFormat.JSON
        )

        generator.generate_report(config, sample_data)
        report = generator.get_report("report-10")

        assert report is not None
        assert report.report_id == "report-10"

    def test_get_nonexistent_report(self, generator):
        """Test getting nonexistent report."""
        report = generator.get_report("nonexistent")
        assert report is None

    def test_list_reports(self, generator, sample_data):
        """Test listing reports."""
        # Generate multiple reports
        for i in range(3):
            config = ReportConfig(
                report_id=f"report-{i}",
                report_type=ReportType.REVIEW_SUMMARY,
                title=f"Report {i}",
                format=ReportFormat.JSON
            )
            generator.generate_report(config, sample_data)

        reports = generator.list_reports()
        assert len(reports) == 3

    def test_list_reports_by_type(self, generator, sample_data):
        """Test listing reports by type."""
        # Generate reports of different types
        config1 = ReportConfig(
            report_id="report-1",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Summary",
            format=ReportFormat.JSON
        )
        generator.generate_report(config1, sample_data)

        config2 = ReportConfig(
            report_id="report-2",
            report_type=ReportType.QUALITY_TRENDS,
            title="Trends",
            format=ReportFormat.JSON
        )
        generator.generate_report(config2, sample_data)

        reports = generator.list_reports(report_type=ReportType.REVIEW_SUMMARY)
        assert len(reports) == 1
        assert reports[0].report_type == ReportType.REVIEW_SUMMARY

    def test_list_reports_by_format(self, generator, sample_data):
        """Test listing reports by format."""
        # Generate reports in different formats
        config1 = ReportConfig(
            report_id="report-1",
            report_type=ReportType.REVIEW_SUMMARY,
            title="JSON Report",
            format=ReportFormat.JSON
        )
        generator.generate_report(config1, sample_data)

        config2 = ReportConfig(
            report_id="report-2",
            report_type=ReportType.REVIEW_SUMMARY,
            title="HTML Report",
            format=ReportFormat.HTML
        )
        generator.generate_report(config2, sample_data)

        reports = generator.list_reports(format=ReportFormat.HTML)
        assert len(reports) == 1
        assert reports[0].format == ReportFormat.HTML

    def test_schedule_report(self, generator):
        """Test scheduling report."""
        config = ReportConfig(
            report_id="scheduled-1",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Scheduled Report",
            format=ReportFormat.JSON
        )

        schedule_id = generator.schedule_report(config, "0 0 * * *", "data_source")
        assert schedule_id is not None
        assert "schedule_" in schedule_id

    def test_report_with_charts(self, generator, sample_data):
        """Test report includes charts."""
        config = ReportConfig(
            report_id="report-charts",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Report with Charts",
            format=ReportFormat.JSON,
            include_charts=True
        )

        report = generator.generate_report(config, sample_data)
        data = json.loads(report.content)

        # Check that at least one section has charts
        has_charts = any(len(s.get('charts', [])) > 0 for s in data['sections'])
        assert has_charts

    def test_report_metadata(self, generator, sample_data):
        """Test report metadata."""
        config = ReportConfig(
            report_id="report-meta",
            report_type=ReportType.REVIEW_SUMMARY,
            title="Report with Metadata",
            format=ReportFormat.JSON,
            metadata={'author': 'test', 'version': '1.0'}
        )

        report = generator.generate_report(config, sample_data)
        assert report.metadata == {'author': 'test', 'version': '1.0'}
