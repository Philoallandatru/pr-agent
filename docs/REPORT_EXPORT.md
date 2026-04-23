# Report Export System

The Report Export System provides comprehensive functionality for exporting code review reports in multiple formats.

## Features

- **Multiple Export Formats**: PDF, Excel, Word, HTML, JSON, CSV
- **Rich Content Support**: Charts, tables, nested sections
- **Customizable Templates**: Flexible report structure
- **High-Quality Output**: Professional formatting and styling
- **Batch Export**: Export multiple reports at once

## Export Formats

### PDF Export
- Professional PDF documents with charts and tables
- Requires: `reportlab`, `matplotlib`
- Best for: Formal reports, presentations

### Excel Export
- Structured spreadsheets with multiple sheets
- Requires: `openpyxl`, `matplotlib`
- Best for: Data analysis, sharing with stakeholders

### Word Export
- Editable Word documents (.docx)
- Requires: `python-docx`, `matplotlib`
- Best for: Collaborative editing, customization

### HTML Export
- Responsive web pages with embedded charts
- No additional requirements
- Best for: Web viewing, email sharing

### JSON Export
- Structured data format
- No additional requirements
- Best for: API integration, data processing

### CSV Export
- Simple tabular data
- No additional requirements
- Best for: Data import, spreadsheet tools

## Installation

### Basic Installation
```bash
pip install pr-agent
```

### Full Installation (All Formats)
```bash
pip install pr-agent[export]
# or
pip install reportlab openpyxl python-docx matplotlib
```

## Usage

### Python API

#### Basic Export
```python
from pr_agent.export import (
    get_exporter,
    ExportReport,
    ReportSection,
    ChartData,
    ChartType,
    ExportFormat
)
from datetime import datetime

# Create report
report = ExportReport(
    title="Code Review Report",
    subtitle="Q1 2024",
    author="John Doe",
    date=datetime.now(),
    summary="Summary of code review activities for Q1 2024."
)

# Add section with chart
chart = ChartData(
    type=ChartType.BAR,
    title="Reviews by Status",
    data={"Success": 45, "Failed": 5, "Pending": 10}
)

section = ReportSection(
    title="Overview",
    content="This section provides an overview.",
    charts=[chart]
)

report.sections.append(section)

# Export to PDF
exporter = get_exporter()
pdf_data = exporter.export(report, ExportFormat.PDF, "report.pdf")
```

#### Export with Tables
```python
# Add table to section
table = {
    "headers": ["Repository", "Reviews", "Success Rate"],
    "rows": [
        ["repo-1", 50, "90%"],
        ["repo-2", 30, "85%"],
        ["repo-3", 20, "95%"]
    ]
}

section = ReportSection(
    title="Repository Statistics",
    content="Review statistics by repository.",
    tables=[table]
)

report.sections.append(section)
```

#### Multiple Chart Types
```python
# Line chart
line_chart = ChartData(
    type=ChartType.LINE,
    title="Review Trends",
    data={"Week 1": 20, "Week 2": 25, "Week 3": 30, "Week 4": 35}
)

# Pie chart
pie_chart = ChartData(
    type=ChartType.PIE,
    title="Issue Distribution",
    data={"Critical": 5, "High": 15, "Medium": 30, "Low": 50},
    colors=["#FF0000", "#FF8800", "#FFFF00", "#00FF00"]
)

section = ReportSection(
    title="Analysis",
    content="Detailed analysis with multiple charts.",
    charts=[line_chart, pie_chart]
)
```

#### Nested Sections
```python
# Create subsections
subsection1 = ReportSection(
    title="Performance Metrics",
    content="Performance analysis details."
)

subsection2 = ReportSection(
    title="Quality Metrics",
    content="Quality analysis details."
)

main_section = ReportSection(
    title="Detailed Analysis",
    content="Comprehensive analysis of all metrics.",
    subsections=[subsection1, subsection2]
)

report.sections.append(main_section)
```

### REST API

#### Export Report
```bash
POST /api/export/report
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Code Review Report",
  "subtitle": "Q1 2024",
  "author": "John Doe",
  "summary": "Summary of code review activities.",
  "format": "pdf",
  "sections": [
    {
      "title": "Overview",
      "content": "This section provides an overview.",
      "charts": [
        {
          "type": "bar",
          "title": "Reviews by Status",
          "data": {
            "Success": 45,
            "Failed": 5,
            "Pending": 10
          }
        }
      ],
      "tables": [
        {
          "headers": ["Repository", "Reviews", "Success Rate"],
          "rows": [
            ["repo-1", 50, "90%"],
            ["repo-2", 30, "85%"]
          ]
        }
      ]
    }
  ],
  "metadata": {
    "version": "1.0",
    "department": "Engineering"
  }
}
```

Response:
```json
{
  "format": "pdf",
  "data": "<base64-encoded-pdf-data>",
  "filename": "report.pdf"
}
```

#### Get Available Formats
```bash
GET /api/export/formats
Authorization: Bearer <token>
```

Response:
```json
{
  "formats": [
    {
      "value": "pdf",
      "label": "PDF",
      "available": true
    },
    {
      "value": "excel",
      "label": "EXCEL",
      "available": true
    },
    {
      "value": "word",
      "label": "WORD",
      "available": true
    },
    {
      "value": "html",
      "label": "HTML",
      "available": true
    },
    {
      "value": "json",
      "label": "JSON",
      "available": true
    },
    {
      "value": "csv",
      "label": "CSV",
      "available": true
    }
  ]
}
```

#### Get Chart Types
```bash
GET /api/export/chart-types
Authorization: Bearer <token>
```

Response:
```json
{
  "chart_types": [
    {"value": "line", "label": "Line"},
    {"value": "bar", "label": "Bar"},
    {"value": "pie", "label": "Pie"},
    {"value": "table", "label": "Table"}
  ]
}
```

## Report Structure

### ExportReport
Main report container with metadata and sections.

**Fields:**
- `title` (str): Report title
- `subtitle` (str, optional): Report subtitle
- `author` (str, optional): Report author
- `date` (datetime, optional): Report date
- `summary` (str, optional): Executive summary
- `sections` (List[ReportSection]): Report sections
- `metadata` (Dict, optional): Additional metadata

### ReportSection
Individual section with content, charts, and tables.

**Fields:**
- `title` (str): Section title
- `content` (str, optional): Section content
- `charts` (List[ChartData], optional): Charts to include
- `tables` (List[Dict], optional): Tables to include
- `subsections` (List[ReportSection], optional): Nested subsections

### ChartData
Chart configuration and data.

**Fields:**
- `type` (ChartType): Chart type (LINE, BAR, PIE, TABLE)
- `title` (str): Chart title
- `data` (Dict): Chart data (key-value pairs)
- `labels` (List[str], optional): Custom labels
- `colors` (List[str], optional): Custom colors (hex codes)

## Advanced Features

### Custom Styling
```python
# Customize chart colors
chart = ChartData(
    type=ChartType.BAR,
    title="Custom Colors",
    data={"A": 10, "B": 20, "C": 30},
    colors=["#FF6384", "#36A2EB", "#FFCE56"]
)
```

### Batch Export
```python
# Export multiple formats at once
formats = [ExportFormat.PDF, ExportFormat.HTML, ExportFormat.JSON]

for fmt in formats:
    filename = f"report.{fmt.value}"
    exporter.export(report, fmt, filename)
```

### Check Format Availability
```python
exporter = get_exporter()

# Check if PDF export is available
if exporter.is_format_available(ExportFormat.PDF):
    pdf_data = exporter.export(report, ExportFormat.PDF)
else:
    print("PDF export requires reportlab package")
```

### Get Available Formats
```python
exporter = get_exporter()
available_formats = exporter.get_available_formats()

print(f"Available formats: {[f.value for f in available_formats]}")
```

## Best Practices

### 1. Structure Your Reports
- Use clear section titles
- Organize content hierarchically
- Include executive summary

### 2. Choose Appropriate Charts
- Bar charts for comparisons
- Line charts for trends
- Pie charts for distributions
- Tables for detailed data

### 3. Optimize Performance
- Limit chart data points (< 50 per chart)
- Use appropriate formats for use case
- Cache frequently generated reports

### 4. Handle Errors Gracefully
```python
try:
    data = exporter.export(report, ExportFormat.PDF)
except ValueError as e:
    # Format not available
    print(f"Export failed: {e}")
    # Fallback to HTML
    data = exporter.export(report, ExportFormat.HTML)
```

### 5. Validate Data
```python
# Ensure data is properly formatted
assert isinstance(report.title, str)
assert len(report.sections) > 0
assert all(isinstance(s, ReportSection) for s in report.sections)
```

## Troubleshooting

### PDF Export Issues
**Problem**: PDF export fails with "reportlab not found"
**Solution**: Install reportlab: `pip install reportlab matplotlib`

### Excel Export Issues
**Problem**: Excel export fails with "openpyxl not found"
**Solution**: Install openpyxl: `pip install openpyxl matplotlib`

### Word Export Issues
**Problem**: Word export fails with "python-docx not found"
**Solution**: Install python-docx: `pip install python-docx matplotlib`

### Chart Rendering Issues
**Problem**: Charts not appearing in exported reports
**Solution**: Ensure matplotlib is installed: `pip install matplotlib`

### Memory Issues
**Problem**: Large reports cause memory errors
**Solution**: 
- Reduce chart data points
- Export in smaller batches
- Use streaming for large datasets

## Examples

### Complete Report Example
```python
from pr_agent.export import *
from datetime import datetime

# Create comprehensive report
report = ExportReport(
    title="Q1 2024 Code Review Report",
    subtitle="Engineering Department",
    author="Tech Lead",
    date=datetime(2024, 3, 31),
    summary="This report summarizes code review activities for Q1 2024.",
    metadata={"version": "1.0", "confidential": False}
)

# Overview section
overview_chart = ChartData(
    type=ChartType.BAR,
    title="Reviews by Status",
    data={"Approved": 120, "Changes Requested": 30, "Pending": 15}
)

overview_table = {
    "headers": ["Metric", "Value", "Change"],
    "rows": [
        ["Total Reviews", "165", "+15%"],
        ["Avg Review Time", "2.5 hours", "-10%"],
        ["Success Rate", "92%", "+3%"]
    ]
}

overview = ReportSection(
    title="Executive Overview",
    content="Q1 showed strong improvement in review efficiency.",
    charts=[overview_chart],
    tables=[overview_table]
)

# Trends section
trends_chart = ChartData(
    type=ChartType.LINE,
    title="Monthly Review Trends",
    data={"January": 50, "February": 55, "March": 60}
)

trends = ReportSection(
    title="Trends Analysis",
    content="Review volume increased steadily throughout Q1.",
    charts=[trends_chart]
)

# Add sections
report.sections.extend([overview, trends])

# Export to multiple formats
exporter = get_exporter()
exporter.export(report, ExportFormat.PDF, "q1_report.pdf")
exporter.export(report, ExportFormat.HTML, "q1_report.html")
exporter.export(report, ExportFormat.JSON, "q1_report.json")
```

## API Reference

See the [API documentation](API_REFERENCE.md) for complete API details.

## Related Documentation

- [Dashboard System](DASHBOARD.md)
- [Metrics Collection](METRICS_COLLECTION.md)
- [Report Generation](REPORT_GENERATOR.md)
- [API Reference](API_REFERENCE.md)
