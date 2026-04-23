"""
Report Export Module

Provides multi-format export capabilities for code review reports.
"""

from pr_agent.export.exporter import (
    ReportExporter,
    ExportFormat,
    ChartType,
    ChartData,
    ReportSection,
    ExportReport,
    PDFExporter,
    ExcelExporter,
    WordExporter,
)

__all__ = [
    'ReportExporter',
    'ExportFormat',
    'ChartType',
    'ChartData',
    'ReportSection',
    'ExportReport',
    'PDFExporter',
    'ExcelExporter',
    'WordExporter',
]


# Singleton instance
_exporter_instance = None


def get_exporter() -> ReportExporter:
    """Get singleton exporter instance"""
    global _exporter_instance
    if _exporter_instance is None:
        _exporter_instance = ReportExporter()
    return _exporter_instance
