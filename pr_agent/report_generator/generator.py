"""
Code Review Report Generator

Generates comprehensive reports from review data in multiple formats.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import json


class ReportType(Enum):
    """Report type enumeration."""
    REVIEW_SUMMARY = "review_summary"
    QUALITY_TRENDS = "quality_trends"
    EFFICIENCY_ANALYSIS = "efficiency_analysis"
    ISSUE_DISTRIBUTION = "issue_distribution"
    TEAM_PERFORMANCE = "team_performance"
    INDIVIDUAL_PERFORMANCE = "individual_performance"


class ReportFormat(Enum):
    """Report output format."""
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"


@dataclass
class ReportConfig:
    """Report configuration."""
    report_id: str
    report_type: ReportType
    title: str
    description: str = ""
    format: ReportFormat = ReportFormat.HTML
    include_charts: bool = True
    include_raw_data: bool = False
    template_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChartData:
    """Chart data for visualization."""
    chart_id: str
    chart_type: str  # bar, line, pie, scatter
    title: str
    data: Dict[str, Any]
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportSection:
    """Report section."""
    section_id: str
    title: str
    content: str
    charts: List[ChartData] = field(default_factory=list)
    subsections: List['ReportSection'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedReport:
    """Generated report result."""
    report_id: str
    report_type: ReportType
    format: ReportFormat
    title: str
    generated_at: datetime
    file_path: Optional[str] = None
    content: Optional[str] = None
    sections: List[ReportSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReportGenerator:
    """Report generator system."""

    def __init__(self, output_dir: str = ".pr_agent/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.templates: Dict[str, Dict] = {}
        self.generated_reports: List[GeneratedReport] = []

    def register_template(self, template_id: str, template: Dict):
        """Register a report template."""
        self.templates[template_id] = template

    def generate_report(
        self,
        config: ReportConfig,
        data: Dict[str, Any],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> GeneratedReport:
        """Generate a report based on configuration and data."""

        # Build sections based on report type
        sections = self._build_sections(config.report_type, data, start_date, end_date)

        # Apply template if specified
        if config.template_id and config.template_id in self.templates:
            sections = self._apply_template(sections, self.templates[config.template_id])

        # Generate content in specified format
        content = self._generate_content(config, sections)

        # Save to file
        file_path = None
        if config.format != ReportFormat.JSON or config.include_raw_data:
            file_path = self._save_report(config, content)

        report = GeneratedReport(
            report_id=config.report_id,
            report_type=config.report_type,
            format=config.format,
            title=config.title,
            generated_at=datetime.now(timezone.utc),
            file_path=str(file_path) if file_path else None,
            content=content if config.format == ReportFormat.JSON else None,
            sections=sections,
            metadata=config.metadata
        )

        self.generated_reports.append(report)
        return report

    def _build_sections(
        self,
        report_type: ReportType,
        data: Dict[str, Any],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[ReportSection]:
        """Build report sections based on type."""

        if report_type == ReportType.REVIEW_SUMMARY:
            return self._build_review_summary_sections(data, start_date, end_date)
        elif report_type == ReportType.QUALITY_TRENDS:
            return self._build_quality_trends_sections(data, start_date, end_date)
        elif report_type == ReportType.EFFICIENCY_ANALYSIS:
            return self._build_efficiency_sections(data, start_date, end_date)
        elif report_type == ReportType.ISSUE_DISTRIBUTION:
            return self._build_issue_distribution_sections(data, start_date, end_date)
        elif report_type == ReportType.TEAM_PERFORMANCE:
            return self._build_team_performance_sections(data, start_date, end_date)
        elif report_type == ReportType.INDIVIDUAL_PERFORMANCE:
            return self._build_individual_performance_sections(data, start_date, end_date)
        else:
            return []

    def _build_review_summary_sections(
        self,
        data: Dict[str, Any],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[ReportSection]:
        """Build review summary sections."""
        sections = []

        # Overview section
        total_reviews = data.get('total_reviews', 0)
        avg_duration = data.get('avg_duration', 0)
        total_comments = data.get('total_comments', 0)

        overview_content = f"""
## Overview

- Total Reviews: {total_reviews}
- Average Duration: {avg_duration:.1f} hours
- Total Comments: {total_comments}
- Period: {start_date.strftime('%Y-%m-%d') if start_date else 'All time'} to {end_date.strftime('%Y-%m-%d') if end_date else 'Present'}
"""

        sections.append(ReportSection(
            section_id="overview",
            title="Overview",
            content=overview_content
        ))

        # Reviews by status
        if 'reviews_by_status' in data:
            chart = ChartData(
                chart_id="reviews_by_status",
                chart_type="pie",
                title="Reviews by Status",
                data=data['reviews_by_status']
            )
            sections.append(ReportSection(
                section_id="status",
                title="Review Status Distribution",
                content="Distribution of reviews by their current status.",
                charts=[chart]
            ))

        return sections

    def _build_quality_trends_sections(
        self,
        data: Dict[str, Any],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[ReportSection]:
        """Build quality trends sections."""
        sections = []

        # Quality score trends
        if 'quality_scores' in data:
            chart = ChartData(
                chart_id="quality_trends",
                chart_type="line",
                title="Quality Score Trends",
                data={
                    'labels': data['quality_scores'].get('dates', []),
                    'datasets': [{
                        'label': 'Quality Score',
                        'data': data['quality_scores'].get('scores', [])
                    }]
                }
            )
            sections.append(ReportSection(
                section_id="quality_trends",
                title="Quality Trends",
                content="Quality score trends over time.",
                charts=[chart]
            ))

        return sections

    def _build_efficiency_sections(
        self,
        data: Dict[str, Any],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[ReportSection]:
        """Build efficiency analysis sections."""
        sections = []

        # Time to first comment
        if 'time_to_first_comment' in data:
            avg_time = data['time_to_first_comment'].get('average', 0)
            content = f"Average time to first comment: {avg_time:.1f} hours"

            sections.append(ReportSection(
                section_id="first_comment",
                title="Time to First Comment",
                content=content
            ))

        # Review duration
        if 'review_duration' in data:
            chart = ChartData(
                chart_id="duration_distribution",
                chart_type="bar",
                title="Review Duration Distribution",
                data=data['review_duration']
            )
            sections.append(ReportSection(
                section_id="duration",
                title="Review Duration",
                content="Distribution of review durations.",
                charts=[chart]
            ))

        return sections

    def _build_issue_distribution_sections(
        self,
        data: Dict[str, Any],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[ReportSection]:
        """Build issue distribution sections."""
        sections = []

        # Issues by severity
        if 'issues_by_severity' in data:
            chart = ChartData(
                chart_id="issues_severity",
                chart_type="bar",
                title="Issues by Severity",
                data=data['issues_by_severity']
            )
            sections.append(ReportSection(
                section_id="severity",
                title="Issue Severity Distribution",
                content="Distribution of issues by severity level.",
                charts=[chart]
            ))

        # Issues by category
        if 'issues_by_category' in data:
            chart = ChartData(
                chart_id="issues_category",
                chart_type="pie",
                title="Issues by Category",
                data=data['issues_by_category']
            )
            sections.append(ReportSection(
                section_id="category",
                title="Issue Category Distribution",
                content="Distribution of issues by category.",
                charts=[chart]
            ))

        return sections

    def _build_team_performance_sections(
        self,
        data: Dict[str, Any],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[ReportSection]:
        """Build team performance sections."""
        sections = []

        # Team metrics
        if 'team_metrics' in data:
            metrics = data['team_metrics']
            content = f"""
## Team Metrics

- Total Team Members: {metrics.get('total_members', 0)}
- Total Reviews: {metrics.get('total_reviews', 0)}
- Average Reviews per Member: {metrics.get('avg_reviews_per_member', 0):.1f}
- Team Quality Score: {metrics.get('team_quality_score', 0):.1f}
"""
            sections.append(ReportSection(
                section_id="team_metrics",
                title="Team Metrics",
                content=content
            ))

        # Top reviewers
        if 'top_reviewers' in data:
            chart = ChartData(
                chart_id="top_reviewers",
                chart_type="bar",
                title="Top Reviewers",
                data=data['top_reviewers']
            )
            sections.append(ReportSection(
                section_id="top_reviewers",
                title="Top Reviewers",
                content="Most active reviewers in the team.",
                charts=[chart]
            ))

        return sections

    def _build_individual_performance_sections(
        self,
        data: Dict[str, Any],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[ReportSection]:
        """Build individual performance sections."""
        sections = []

        # Individual metrics
        if 'individual_metrics' in data:
            metrics = data['individual_metrics']
            content = f"""
## Individual Performance

- Total Reviews: {metrics.get('total_reviews', 0)}
- Average Quality Score: {metrics.get('avg_quality_score', 0):.1f}
- Total Comments: {metrics.get('total_comments', 0)}
- Issues Found: {metrics.get('issues_found', 0)}
- Average Response Time: {metrics.get('avg_response_time', 0):.1f} hours
"""
            sections.append(ReportSection(
                section_id="individual_metrics",
                title="Performance Metrics",
                content=content
            ))

        return sections

    def _apply_template(self, sections: List[ReportSection], template: Dict) -> List[ReportSection]:
        """Apply template to sections."""
        # Template application logic
        return sections

    def _generate_content(self, config: ReportConfig, sections: List[ReportSection]) -> str:
        """Generate content in specified format."""

        if config.format == ReportFormat.JSON:
            return self._generate_json(config, sections)
        elif config.format == ReportFormat.MARKDOWN:
            return self._generate_markdown(config, sections)
        elif config.format == ReportFormat.HTML:
            return self._generate_html(config, sections)
        elif config.format == ReportFormat.PDF:
            return self._generate_pdf(config, sections)
        else:
            return ""

    def _generate_json(self, config: ReportConfig, sections: List[ReportSection]) -> str:
        """Generate JSON report."""
        report_data = {
            'report_id': config.report_id,
            'title': config.title,
            'description': config.description,
            'type': config.report_type.value,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'sections': [
                {
                    'section_id': s.section_id,
                    'title': s.title,
                    'content': s.content,
                    'charts': [
                        {
                            'chart_id': c.chart_id,
                            'type': c.chart_type,
                            'title': c.title,
                            'data': c.data
                        }
                        for c in s.charts
                    ]
                }
                for s in sections
            ]
        }
        return json.dumps(report_data, indent=2)

    def _generate_markdown(self, config: ReportConfig, sections: List[ReportSection]) -> str:
        """Generate Markdown report."""
        lines = [
            f"# {config.title}",
            "",
            config.description,
            "",
            f"*Generated at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*",
            "",
            "---",
            ""
        ]

        for section in sections:
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")

            if section.charts:
                lines.append("### Charts")
                for chart in section.charts:
                    lines.append(f"- {chart.title} ({chart.chart_type})")
                lines.append("")

        return "\n".join(lines)

    def _generate_html(self, config: ReportConfig, sections: List[ReportSection]) -> str:
        """Generate HTML report."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{config.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
        .section {{ margin-bottom: 30px; }}
        .chart {{ margin: 20px 0; padding: 20px; background: #f5f5f5; border-radius: 5px; }}
        .metadata {{ color: #999; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>{config.title}</h1>
    <p>{config.description}</p>
    <p class="metadata">Generated at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    <hr>
"""

        for section in sections:
            html += f"""
    <div class="section">
        <h2>{section.title}</h2>
        <div>{section.content}</div>
"""

            if section.charts:
                for chart in section.charts:
                    html += f"""
        <div class="chart">
            <h3>{chart.title}</h3>
            <p>Chart Type: {chart.chart_type}</p>
            <pre>{json.dumps(chart.data, indent=2)}</pre>
        </div>
"""

            html += "    </div>\n"

        html += """
</body>
</html>
"""
        return html

    def _generate_pdf(self, config: ReportConfig, sections: List[ReportSection]) -> str:
        """Generate PDF report (placeholder - requires PDF library)."""
        # In a real implementation, this would use a library like reportlab or weasyprint
        return self._generate_html(config, sections)

    def _save_report(self, config: ReportConfig, content: str) -> Path:
        """Save report to file."""
        extension_map = {
            ReportFormat.JSON: 'json',
            ReportFormat.MARKDOWN: 'md',
            ReportFormat.HTML: 'html',
            ReportFormat.PDF: 'pdf'
        }

        extension = extension_map.get(config.format, 'txt')
        filename = f"{config.report_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.{extension}"
        file_path = self.output_dir / filename

        file_path.write_text(content, encoding='utf-8')
        return file_path

    def get_report(self, report_id: str) -> Optional[GeneratedReport]:
        """Get a generated report by ID."""
        for report in self.generated_reports:
            if report.report_id == report_id:
                return report
        return None

    def list_reports(
        self,
        report_type: Optional[ReportType] = None,
        format: Optional[ReportFormat] = None
    ) -> List[GeneratedReport]:
        """List generated reports with optional filters."""
        reports = self.generated_reports

        if report_type:
            reports = [r for r in reports if r.report_type == report_type]

        if format:
            reports = [r for r in reports if r.format == format]

        return reports

    def schedule_report(
        self,
        config: ReportConfig,
        schedule: str,  # cron expression
        data_source: str
    ) -> str:
        """Schedule a report for periodic generation."""
        # This would integrate with a scheduler system
        schedule_id = f"schedule_{config.report_id}_{datetime.now(timezone.utc).timestamp()}"
        return schedule_id
