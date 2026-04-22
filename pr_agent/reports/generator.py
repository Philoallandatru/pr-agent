"""
Code quality report generator.

Generates comprehensive reports in multiple formats (PDF, HTML, Markdown)
with quality metrics, trend charts, issue summaries, and recommendations.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum
import base64
from io import BytesIO


class ReportFormat(Enum):
    """Report output format."""
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"


class ReportSection(Enum):
    """Report sections."""
    SUMMARY = "summary"
    METRICS = "metrics"
    TRENDS = "trends"
    ISSUES = "issues"
    RECOMMENDATIONS = "recommendations"
    DETAILS = "details"


@dataclass
class QualityMetrics:
    """Quality metrics snapshot."""
    lines_of_code: int
    test_coverage: float
    complexity_score: float
    maintainability_index: float
    code_smells: int
    bugs: int
    vulnerabilities: int
    technical_debt_hours: float
    duplication_percentage: float


@dataclass
class TrendData:
    """Trend data point."""
    timestamp: str
    metric_name: str
    value: float


@dataclass
class Issue:
    """Code issue."""
    severity: str
    category: str
    file_path: str
    line_number: int
    message: str
    rule_id: Optional[str] = None


@dataclass
class Recommendation:
    """Improvement recommendation."""
    priority: str
    category: str
    title: str
    description: str
    estimated_effort: str
    impact: str


class ReportGenerator:
    """Generate code quality reports in multiple formats."""

    def __init__(self, output_dir: Path):
        """
        Initialize report generator.

        Args:
            output_dir: Directory for generated reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        repository: str,
        metrics: QualityMetrics,
        trends: List[TrendData],
        issues: List[Issue],
        recommendations: List[Recommendation],
        format: ReportFormat = ReportFormat.HTML,
        sections: Optional[List[ReportSection]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Generate a comprehensive quality report.

        Args:
            repository: Repository identifier
            metrics: Current quality metrics
            trends: Historical trend data
            issues: List of issues found
            recommendations: Improvement recommendations
            format: Output format
            sections: Sections to include (all if None)
            metadata: Additional metadata

        Returns:
            Path to generated report
        """
        if sections is None:
            sections = list(ReportSection)

        report_data = {
            "repository": repository,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": asdict(metrics),
            "trends": [asdict(t) for t in trends],
            "issues": [asdict(i) for i in issues],
            "recommendations": [asdict(r) for r in recommendations],
            "metadata": metadata or {}
        }

        if format == ReportFormat.JSON:
            return self._generate_json(report_data)
        elif format == ReportFormat.MARKDOWN:
            return self._generate_markdown(report_data, sections)
        elif format == ReportFormat.HTML:
            return self._generate_html(report_data, sections)
        elif format == ReportFormat.PDF:
            return self._generate_pdf(report_data, sections)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_json(self, data: Dict[str, Any]) -> Path:
        """Generate JSON report."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.json"
        output_path = self.output_dir / filename

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        return output_path

    def _generate_markdown(
        self,
        data: Dict[str, Any],
        sections: List[ReportSection]
    ) -> Path:
        """Generate Markdown report."""
        lines = []

        # Header
        lines.append(f"# Code Quality Report: {data['repository']}")
        lines.append(f"\n**Generated:** {data['generated_at']}\n")

        # Summary
        if ReportSection.SUMMARY in sections:
            lines.append("## Executive Summary\n")
            metrics = data['metrics']
            lines.append(f"- **Lines of Code:** {metrics['lines_of_code']:,}")
            lines.append(f"- **Test Coverage:** {metrics['test_coverage']:.1f}%")
            lines.append(f"- **Maintainability Index:** {metrics['maintainability_index']:.1f}/100")
            lines.append(f"- **Technical Debt:** {metrics['technical_debt_hours']:.1f} hours")
            # Only show issues count if ISSUES section is included AND there are issues
            if ReportSection.ISSUES in sections and data['issues']:
                lines.append(f"- **Issues Found:** {metrics['bugs'] + metrics['vulnerabilities'] + metrics['code_smells']}")
            lines.append("")

        # Metrics
        if ReportSection.METRICS in sections:
            lines.append("## Quality Metrics\n")
            metrics = data['metrics']
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| Lines of Code | {metrics['lines_of_code']:,} |")
            lines.append(f"| Test Coverage | {metrics['test_coverage']:.1f}% |")
            lines.append(f"| Complexity Score | {metrics['complexity_score']:.1f} |")
            lines.append(f"| Maintainability Index | {metrics['maintainability_index']:.1f}/100 |")
            lines.append(f"| Code Smells | {metrics['code_smells']} |")
            lines.append(f"| Bugs | {metrics['bugs']} |")
            lines.append(f"| Vulnerabilities | {metrics['vulnerabilities']} |")
            lines.append(f"| Technical Debt | {metrics['technical_debt_hours']:.1f} hours |")
            lines.append(f"| Code Duplication | {metrics['duplication_percentage']:.1f}% |")
            lines.append("")

        # Trends
        if ReportSection.TRENDS in sections and data['trends']:
            lines.append("## Quality Trends\n")
            lines.append("Recent quality metric trends:\n")

            # Group trends by metric
            trends_by_metric = {}
            for trend in data['trends']:
                metric = trend['metric_name']
                if metric not in trends_by_metric:
                    trends_by_metric[metric] = []
                trends_by_metric[metric].append(trend)

            for metric, trends in trends_by_metric.items():
                lines.append(f"### {metric}\n")
                if len(trends) >= 2:
                    first = trends[0]['value']
                    last = trends[-1]['value']
                    change = last - first
                    direction = "↑" if change > 0 else "↓" if change < 0 else "→"
                    lines.append(f"**Trend:** {direction} {abs(change):.2f} change over {len(trends)} data points\n")
                lines.append("")

        # Issues
        if ReportSection.ISSUES in sections and data['issues']:
            lines.append("## Issues Found\n")

            # Group by severity
            by_severity = {}
            for issue in data['issues']:
                severity = issue['severity']
                if severity not in by_severity:
                    by_severity[severity] = []
                by_severity[severity].append(issue)

            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if severity in by_severity:
                    issues = by_severity[severity]
                    lines.append(f"### {severity} ({len(issues)} issues)\n")
                    for issue in issues[:10]:  # Limit to 10 per severity
                        lines.append(f"- **{issue['category']}** in `{issue['file_path']}:{issue['line_number']}`")
                        lines.append(f"  {issue['message']}")
                    if len(issues) > 10:
                        lines.append(f"\n  *...and {len(issues) - 10} more*")
                    lines.append("")

        # Recommendations
        if ReportSection.RECOMMENDATIONS in sections and data['recommendations']:
            lines.append("## Recommendations\n")

            for rec in data['recommendations']:
                lines.append(f"### {rec['title']} ({rec['priority']} Priority)\n")
                lines.append(f"**Category:** {rec['category']}")
                lines.append(f"**Estimated Effort:** {rec['estimated_effort']}")
                lines.append(f"**Impact:** {rec['impact']}\n")
                lines.append(f"{rec['description']}\n")

        # Generate file
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.md"
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output_path

    def _generate_html(
        self,
        data: Dict[str, Any],
        sections: List[ReportSection]
    ) -> Path:
        """Generate HTML report."""
        html = []

        # HTML header
        html.append("<!DOCTYPE html>")
        html.append("<html lang='en'>")
        html.append("<head>")
        html.append("  <meta charset='UTF-8'>")
        html.append("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
        html.append(f"  <title>Code Quality Report - {data['repository']}</title>")
        html.append("  <style>")
        html.append(self._get_html_styles())
        html.append("  </style>")
        html.append("</head>")
        html.append("<body>")

        # Header
        html.append("  <div class='header'>")
        html.append(f"    <h1>Code Quality Report</h1>")
        html.append(f"    <h2>{data['repository']}</h2>")
        html.append(f"    <p class='timestamp'>Generated: {data['generated_at']}</p>")
        html.append("  </div>")

        html.append("  <div class='container'>")

        # Summary
        if ReportSection.SUMMARY in sections:
            metrics = data['metrics']
            html.append("    <section class='summary'>")
            html.append("      <h2>Executive Summary</h2>")
            html.append("      <div class='metrics-grid'>")
            html.append(f"        <div class='metric-card'><div class='metric-value'>{metrics['lines_of_code']:,}</div><div class='metric-label'>Lines of Code</div></div>")
            html.append(f"        <div class='metric-card'><div class='metric-value'>{metrics['test_coverage']:.1f}%</div><div class='metric-label'>Test Coverage</div></div>")
            html.append(f"        <div class='metric-card'><div class='metric-value'>{metrics['maintainability_index']:.1f}</div><div class='metric-label'>Maintainability</div></div>")
            html.append(f"        <div class='metric-card'><div class='metric-value'>{metrics['technical_debt_hours']:.1f}h</div><div class='metric-label'>Technical Debt</div></div>")
            html.append("      </div>")
            html.append("    </section>")

        # Metrics
        if ReportSection.METRICS in sections:
            metrics = data['metrics']
            html.append("    <section class='metrics'>")
            html.append("      <h2>Quality Metrics</h2>")
            html.append("      <table>")
            html.append("        <tr><th>Metric</th><th>Value</th></tr>")
            html.append(f"        <tr><td>Lines of Code</td><td>{metrics['lines_of_code']:,}</td></tr>")
            html.append(f"        <tr><td>Test Coverage</td><td>{metrics['test_coverage']:.1f}%</td></tr>")
            html.append(f"        <tr><td>Complexity Score</td><td>{metrics['complexity_score']:.1f}</td></tr>")
            html.append(f"        <tr><td>Maintainability Index</td><td>{metrics['maintainability_index']:.1f}/100</td></tr>")
            html.append(f"        <tr><td>Code Smells</td><td>{metrics['code_smells']}</td></tr>")
            html.append(f"        <tr><td>Bugs</td><td>{metrics['bugs']}</td></tr>")
            html.append(f"        <tr><td>Vulnerabilities</td><td class='severity-high'>{metrics['vulnerabilities']}</td></tr>")
            html.append(f"        <tr><td>Technical Debt</td><td>{metrics['technical_debt_hours']:.1f} hours</td></tr>")
            html.append(f"        <tr><td>Code Duplication</td><td>{metrics['duplication_percentage']:.1f}%</td></tr>")
            html.append("      </table>")
            html.append("    </section>")

        # Issues
        if ReportSection.ISSUES in sections and data['issues']:
            html.append("    <section class='issues'>")
            html.append("      <h2>Issues Found</h2>")

            by_severity = {}
            for issue in data['issues']:
                severity = issue['severity']
                if severity not in by_severity:
                    by_severity[severity] = []
                by_severity[severity].append(issue)

            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if severity in by_severity:
                    issues = by_severity[severity]
                    html.append(f"      <h3>{severity} ({len(issues)} issues)</h3>")
                    html.append("      <ul class='issue-list'>")
                    for issue in issues[:20]:
                        html.append(f"        <li class='severity-{severity.lower()}'>")
                        html.append(f"          <strong>{issue['category']}</strong> in <code>{issue['file_path']}:{issue['line_number']}</code>")
                        html.append(f"          <p>{issue['message']}</p>")
                        html.append("        </li>")
                    if len(issues) > 20:
                        html.append(f"        <li><em>...and {len(issues) - 20} more</em></li>")
                    html.append("      </ul>")

            html.append("    </section>")

        # Recommendations
        if ReportSection.RECOMMENDATIONS in sections and data['recommendations']:
            html.append("    <section class='recommendations'>")
            html.append("      <h2>Recommendations</h2>")
            for rec in data['recommendations']:
                html.append(f"      <div class='recommendation priority-{rec['priority'].lower()}'>")
                html.append(f"        <h3>{rec['title']}</h3>")
                html.append(f"        <div class='rec-meta'>")
                html.append(f"          <span class='badge'>{rec['priority']} Priority</span>")
                html.append(f"          <span class='badge'>{rec['category']}</span>")
                html.append(f"          <span class='badge'>Effort: {rec['estimated_effort']}</span>")
                html.append(f"          <span class='badge'>Impact: {rec['impact']}</span>")
                html.append(f"        </div>")
                html.append(f"        <p>{rec['description']}</p>")
                html.append("      </div>")
            html.append("    </section>")

        html.append("  </div>")
        html.append("</body>")
        html.append("</html>")

        # Generate file
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.html"
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html))

        return output_path

    def _generate_pdf(
        self,
        data: Dict[str, Any],
        sections: List[ReportSection]
    ) -> Path:
        """Generate PDF report (requires weasyprint)."""
        try:
            from weasyprint import HTML, CSS
        except ImportError:
            raise ImportError("weasyprint is required for PDF generation. Install with: pip install weasyprint")

        # Generate HTML first
        html_path = self._generate_html(data, sections)

        # Convert to PDF
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.pdf"
        output_path = self.output_dir / filename

        HTML(filename=str(html_path)).write_pdf(str(output_path))

        # Clean up temporary HTML
        html_path.unlink()

        return output_path

    def _get_html_styles(self) -> str:
        """Get CSS styles for HTML report."""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; text-align: center; }
        .header h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .header h2 { font-size: 1.5rem; font-weight: normal; opacity: 0.9; }
        .timestamp { margin-top: 1rem; opacity: 0.8; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        section { background: white; border-radius: 8px; padding: 2rem; margin-bottom: 2rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h2 { color: #667eea; margin-bottom: 1.5rem; font-size: 1.8rem; }
        h3 { color: #555; margin: 1.5rem 0 1rem; font-size: 1.3rem; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
        .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 8px; text-align: center; }
        .metric-value { font-size: 2.5rem; font-weight: bold; margin-bottom: 0.5rem; }
        .metric-label { font-size: 0.9rem; opacity: 0.9; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; color: #667eea; }
        tr:hover { background: #f8f9fa; }
        .severity-high { color: #dc3545; font-weight: bold; }
        .issue-list { list-style: none; }
        .issue-list li { padding: 1rem; margin-bottom: 0.5rem; border-left: 4px solid #ddd; background: #f8f9fa; }
        .severity-critical { border-left-color: #dc3545; }
        .severity-high { border-left-color: #fd7e14; }
        .severity-medium { border-left-color: #ffc107; }
        .severity-low { border-left-color: #28a745; }
        code { background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 3px; font-family: 'Courier New', monospace; }
        .recommendation { padding: 1.5rem; margin-bottom: 1rem; border-radius: 8px; border-left: 4px solid #667eea; background: #f8f9fa; }
        .priority-critical { border-left-color: #dc3545; }
        .priority-high { border-left-color: #fd7e14; }
        .priority-medium { border-left-color: #ffc107; }
        .priority-low { border-left-color: #28a745; }
        .rec-meta { margin: 0.5rem 0 1rem; }
        .badge { display: inline-block; padding: 0.25rem 0.75rem; margin-right: 0.5rem; background: #667eea; color: white; border-radius: 12px; font-size: 0.85rem; }
        """
