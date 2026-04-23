"""
Tests for Report Export System
"""

import io
import json
import pytest
from datetime import datetime
from pathlib import Path

from pr_agent.export import (
    ReportExporter,
    ExportFormat,
    ChartType,
    ChartData,
    ReportSection,
    ExportReport,
    get_exporter,
)


@pytest.fixture
def sample_report():
    """Create a sample report for testing"""
    chart1 = ChartData(
        type=ChartType.BAR,
        title="Reviews by Status",
        data={"Success": 45, "Failed": 5, "Pending": 10}
    )

    chart2 = ChartData(
        type=ChartType.LINE,
        title="Review Trends",
        data={"Week 1": 20, "Week 2": 25, "Week 3": 30, "Week 4": 35}
    )

    table1 = {
        "headers": ["Repository", "Reviews", "Success Rate"],
        "rows": [
            ["repo-1", 50, "90%"],
            ["repo-2", 30, "85%"],
            ["repo-3", 20, "95%"]
        ]
    }

    section1 = ReportSection(
        title="Overview",
        content="This section provides an overview of code review activities.",
        charts=[chart1],
        tables=[table1]
    )

    section2 = ReportSection(
        title="Trends",
        content="Analysis of review trends over time.",
        charts=[chart2]
    )

    subsection = ReportSection(
        title="Detailed Analysis",
        content="Detailed breakdown of review metrics."
    )
    section2.subsections.append(subsection)

    report = ExportReport(
        title="Code Review Report",
        subtitle="Q1 2024",
        author="Test User",
        date=datetime(2024, 3, 31, 12, 0),
        summary="This report summarizes code review activities for Q1 2024.",
        sections=[section1, section2],
        metadata={"version": "1.0", "department": "Engineering"}
    )

    return report


class TestReportExporter:
    """Test ReportExporter class"""

    def test_singleton_instance(self):
        """Test singleton pattern"""
        exporter1 = get_exporter()
        exporter2 = get_exporter()
        assert exporter1 is exporter2

    def test_get_available_formats(self):
        """Test getting available formats"""
        exporter = ReportExporter()
        formats = exporter.get_available_formats()

        # JSON, CSV, HTML should always be available
        assert ExportFormat.JSON in formats
        assert ExportFormat.CSV in formats
        assert ExportFormat.HTML in formats

    def test_is_format_available(self):
        """Test checking format availability"""
        exporter = ReportExporter()

        # These should always be available
        assert exporter.is_format_available(ExportFormat.JSON)
        assert exporter.is_format_available(ExportFormat.CSV)
        assert exporter.is_format_available(ExportFormat.HTML)


class TestJSONExport:
    """Test JSON export"""

    def test_export_json(self, sample_report, tmp_path):
        """Test JSON export"""
        exporter = ReportExporter()
        output_path = tmp_path / "report.json"

        data = exporter.export(sample_report, ExportFormat.JSON, str(output_path))

        assert data
        assert output_path.exists()

        # Parse and verify JSON
        json_data = json.loads(data)
        assert json_data['title'] == "Code Review Report"
        assert json_data['subtitle'] == "Q1 2024"
        assert json_data['author'] == "Test User"
        assert len(json_data['sections']) == 2

    def test_json_structure(self, sample_report):
        """Test JSON structure"""
        exporter = ReportExporter()
        data = exporter.export(sample_report, ExportFormat.JSON)

        json_data = json.loads(data)

        # Check sections
        assert 'sections' in json_data
        section = json_data['sections'][0]
        assert section['title'] == "Overview"
        assert 'charts' in section
        assert 'tables' in section

        # Check charts
        assert len(section['charts']) == 1
        chart = section['charts'][0]
        assert chart['type'] == ChartType.BAR
        assert chart['title'] == "Reviews by Status"
        assert 'data' in chart

        # Check tables
        assert len(section['tables']) == 1
        table = section['tables'][0]
        assert 'headers' in table
        assert 'rows' in table

    def test_json_metadata(self, sample_report):
        """Test JSON metadata"""
        exporter = ReportExporter()
        data = exporter.export(sample_report, ExportFormat.JSON)

        json_data = json.loads(data)
        assert 'metadata' in json_data
        assert json_data['metadata']['version'] == "1.0"
        assert json_data['metadata']['department'] == "Engineering"


class TestCSVExport:
    """Test CSV export"""

    def test_export_csv(self, sample_report, tmp_path):
        """Test CSV export"""
        exporter = ReportExporter()
        output_path = tmp_path / "report.csv"

        data = exporter.export(sample_report, ExportFormat.CSV, str(output_path))

        assert data
        assert output_path.exists()

        # Verify CSV content
        csv_text = data.decode('utf-8')
        assert "Code Review Report" in csv_text
        assert "Repository,Reviews,Success Rate" in csv_text

    def test_csv_tables(self, sample_report):
        """Test CSV table export"""
        exporter = ReportExporter()
        data = exporter.export(sample_report, ExportFormat.CSV)

        csv_text = data.decode('utf-8')

        # Check headers
        assert "Repository,Reviews,Success Rate" in csv_text

        # Check data rows
        assert "repo-1,50,90%" in csv_text
        assert "repo-2,30,85%" in csv_text
        assert "repo-3,20,95%" in csv_text


class TestHTMLExport:
    """Test HTML export"""

    def test_export_html(self, sample_report, tmp_path):
        """Test HTML export"""
        exporter = ReportExporter()
        output_path = tmp_path / "report.html"

        data = exporter.export(sample_report, ExportFormat.HTML, str(output_path))

        assert data
        assert output_path.exists()

        # Verify HTML content
        html_text = data.decode('utf-8')
        assert "<!DOCTYPE html>" in html_text
        assert "<html>" in html_text
        assert "Code Review Report" in html_text

    def test_html_structure(self, sample_report):
        """Test HTML structure"""
        exporter = ReportExporter()
        data = exporter.export(sample_report, ExportFormat.HTML)

        html_text = data.decode('utf-8')

        # Check title
        assert "<h1>Code Review Report</h1>" in html_text
        assert "<h2>Q1 2024</h2>" in html_text

        # Check sections
        assert "<h2>Overview</h2>" in html_text
        assert "<h2>Trends</h2>" in html_text

        # Check table
        assert "<table>" in html_text
        assert "<th>Repository</th>" in html_text
        assert "<td>repo-1</td>" in html_text

    def test_html_styling(self, sample_report):
        """Test HTML styling"""
        exporter = ReportExporter()
        data = exporter.export(sample_report, ExportFormat.HTML)

        html_text = data.decode('utf-8')

        # Check CSS
        assert "<style>" in html_text
        assert "font-family" in html_text
        assert "border-collapse" in html_text


class TestPDFExport:
    """Test PDF export (if available)"""

    def test_export_pdf(self, sample_report, tmp_path):
        """Test PDF export"""
        exporter = ReportExporter()

        if not exporter.is_format_available(ExportFormat.PDF):
            pytest.skip("PDF export not available (reportlab not installed)")

        output_path = tmp_path / "report.pdf"
        data = exporter.export(sample_report, ExportFormat.PDF, str(output_path))

        assert data
        assert output_path.exists()
        assert data.startswith(b'%PDF')  # PDF magic number

    def test_pdf_without_reportlab(self, sample_report):
        """Test PDF export fails gracefully without reportlab"""
        exporter = ReportExporter()

        if exporter.is_format_available(ExportFormat.PDF):
            pytest.skip("reportlab is installed")

        with pytest.raises(ValueError):
            exporter.export(sample_report, ExportFormat.PDF)


class TestExcelExport:
    """Test Excel export (if available)"""

    def test_export_excel(self, sample_report, tmp_path):
        """Test Excel export"""
        exporter = ReportExporter()

        if not exporter.is_format_available(ExportFormat.EXCEL):
            pytest.skip("Excel export not available (openpyxl not installed)")

        output_path = tmp_path / "report.xlsx"
        data = exporter.export(sample_report, ExportFormat.EXCEL, str(output_path))

        assert data
        assert output_path.exists()
        # Excel files start with PK (ZIP format)
        assert data.startswith(b'PK')

    def test_excel_without_openpyxl(self, sample_report):
        """Test Excel export fails gracefully without openpyxl"""
        exporter = ReportExporter()

        if exporter.is_format_available(ExportFormat.EXCEL):
            pytest.skip("openpyxl is installed")

        with pytest.raises(ValueError):
            exporter.export(sample_report, ExportFormat.EXCEL)


class TestWordExport:
    """Test Word export (if available)"""

    def test_export_word(self, sample_report, tmp_path):
        """Test Word export"""
        exporter = ReportExporter()

        if not exporter.is_format_available(ExportFormat.WORD):
            pytest.skip("Word export not available (python-docx not installed)")

        output_path = tmp_path / "report.docx"
        data = exporter.export(sample_report, ExportFormat.WORD, str(output_path))

        assert data
        assert output_path.exists()
        # Word files start with PK (ZIP format)
        assert data.startswith(b'PK')

    def test_word_without_python_docx(self, sample_report):
        """Test Word export fails gracefully without python-docx"""
        exporter = ReportExporter()

        if exporter.is_format_available(ExportFormat.WORD):
            pytest.skip("python-docx is installed")

        with pytest.raises(ValueError):
            exporter.export(sample_report, ExportFormat.WORD)


class TestChartData:
    """Test ChartData class"""

    def test_create_chart_data(self):
        """Test creating chart data"""
        chart = ChartData(
            type=ChartType.BAR,
            title="Test Chart",
            data={"A": 10, "B": 20}
        )

        assert chart.type == ChartType.BAR
        assert chart.title == "Test Chart"
        assert chart.data == {"A": 10, "B": 20}
        assert chart.labels is None
        assert chart.colors is None

    def test_chart_with_labels(self):
        """Test chart with custom labels"""
        chart = ChartData(
            type=ChartType.PIE,
            title="Test Pie",
            data={"A": 30, "B": 70},
            labels=["Category A", "Category B"]
        )

        assert chart.labels == ["Category A", "Category B"]

    def test_chart_with_colors(self):
        """Test chart with custom colors"""
        chart = ChartData(
            type=ChartType.LINE,
            title="Test Line",
            data={"X": 1, "Y": 2},
            colors=["#FF0000", "#00FF00"]
        )

        assert chart.colors == ["#FF0000", "#00FF00"]


class TestReportSection:
    """Test ReportSection class"""

    def test_create_section(self):
        """Test creating a section"""
        section = ReportSection(
            title="Test Section",
            content="Test content"
        )

        assert section.title == "Test Section"
        assert section.content == "Test content"
        assert len(section.charts) == 0
        assert len(section.tables) == 0
        assert len(section.subsections) == 0

    def test_section_with_charts(self):
        """Test section with charts"""
        chart = ChartData(
            type=ChartType.BAR,
            title="Test",
            data={"A": 1}
        )

        section = ReportSection(
            title="Test",
            content="Content",
            charts=[chart]
        )

        assert len(section.charts) == 1
        assert section.charts[0].title == "Test"

    def test_section_with_tables(self):
        """Test section with tables"""
        table = {
            "headers": ["Col1", "Col2"],
            "rows": [[1, 2], [3, 4]]
        }

        section = ReportSection(
            title="Test",
            content="Content",
            tables=[table]
        )

        assert len(section.tables) == 1
        assert section.tables[0]["headers"] == ["Col1", "Col2"]

    def test_nested_sections(self):
        """Test nested sections"""
        subsection = ReportSection(
            title="Subsection",
            content="Sub content"
        )

        section = ReportSection(
            title="Main Section",
            content="Main content",
            subsections=[subsection]
        )

        assert len(section.subsections) == 1
        assert section.subsections[0].title == "Subsection"


class TestExportReport:
    """Test ExportReport class"""

    def test_create_report(self):
        """Test creating a report"""
        report = ExportReport(
            title="Test Report",
            subtitle="Subtitle",
            author="Author",
            date=datetime(2024, 1, 1),
            summary="Summary"
        )

        assert report.title == "Test Report"
        assert report.subtitle == "Subtitle"
        assert report.author == "Author"
        assert report.date == datetime(2024, 1, 1)
        assert report.summary == "Summary"
        assert len(report.sections) == 0
        assert len(report.metadata) == 0

    def test_report_with_sections(self):
        """Test report with sections"""
        section = ReportSection(title="Section 1", content="Content")

        report = ExportReport(
            title="Test",
            sections=[section]
        )

        assert len(report.sections) == 1
        assert report.sections[0].title == "Section 1"

    def test_report_with_metadata(self):
        """Test report with metadata"""
        report = ExportReport(
            title="Test",
            metadata={"key": "value", "version": "1.0"}
        )

        assert report.metadata["key"] == "value"
        assert report.metadata["version"] == "1.0"


class TestExportFormats:
    """Test export format enumeration"""

    def test_format_values(self):
        """Test format enum values"""
        assert ExportFormat.PDF == "pdf"
        assert ExportFormat.EXCEL == "excel"
        assert ExportFormat.WORD == "word"
        assert ExportFormat.HTML == "html"
        assert ExportFormat.JSON == "json"
        assert ExportFormat.CSV == "csv"


class TestChartTypes:
    """Test chart type enumeration"""

    def test_chart_type_values(self):
        """Test chart type enum values"""
        assert ChartType.LINE == "line"
        assert ChartType.BAR == "bar"
        assert ChartType.PIE == "pie"
        assert ChartType.TABLE == "table"
