"""
Code coverage tracking and analysis system.

Integrates with coverage.py and pytest-cov to track test coverage,
analyze trends, and generate reports.
"""

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET


class CoverageFormat(str, Enum):
    """Coverage report format."""
    XML = "xml"
    JSON = "json"
    HTML = "html"
    LCOV = "lcov"


class CoverageStatus(str, Enum):
    """Coverage status."""
    EXCELLENT = "excellent"  # >= 90%
    GOOD = "good"  # >= 80%
    FAIR = "fair"  # >= 70%
    POOR = "poor"  # < 70%


@dataclass
class FileCoverage:
    """Coverage data for a single file."""
    file_path: str
    line_rate: float  # 0.0 - 1.0
    branch_rate: float  # 0.0 - 1.0
    lines_covered: int
    lines_valid: int
    branches_covered: int
    branches_valid: int
    missing_lines: List[int] = field(default_factory=list)

    @property
    def line_coverage_percent(self) -> float:
        """Get line coverage percentage."""
        return self.line_rate * 100

    @property
    def branch_coverage_percent(self) -> float:
        """Get branch coverage percentage."""
        return self.branch_rate * 100

    @property
    def status(self) -> CoverageStatus:
        """Get coverage status."""
        percent = self.line_coverage_percent
        if percent >= 90:
            return CoverageStatus.EXCELLENT
        elif percent >= 80:
            return CoverageStatus.GOOD
        elif percent >= 70:
            return CoverageStatus.FAIR
        else:
            return CoverageStatus.POOR


@dataclass
class CoverageReport:
    """Complete coverage report."""
    timestamp: float
    line_rate: float
    branch_rate: float
    lines_covered: int
    lines_valid: int
    branches_covered: int
    branches_valid: int
    files: Dict[str, FileCoverage] = field(default_factory=dict)

    @property
    def line_coverage_percent(self) -> float:
        """Get overall line coverage percentage."""
        return self.line_rate * 100

    @property
    def branch_coverage_percent(self) -> float:
        """Get overall branch coverage percentage."""
        return self.branch_rate * 100

    @property
    def status(self) -> CoverageStatus:
        """Get overall coverage status."""
        percent = self.line_coverage_percent
        if percent >= 90:
            return CoverageStatus.EXCELLENT
        elif percent >= 80:
            return CoverageStatus.GOOD
        elif percent >= 70:
            return CoverageStatus.FAIR
        else:
            return CoverageStatus.POOR


@dataclass
class CoverageTrend:
    """Coverage trend over time."""
    timestamps: List[float] = field(default_factory=list)
    line_rates: List[float] = field(default_factory=list)
    branch_rates: List[float] = field(default_factory=list)

    def add_report(self, report: CoverageReport):
        """Add a report to the trend."""
        self.timestamps.append(report.timestamp)
        self.line_rates.append(report.line_rate)
        self.branch_rates.append(report.branch_rate)

    def get_change(self, days: int = 7) -> Tuple[float, float]:
        """Get coverage change over the last N days."""
        if len(self.timestamps) < 2:
            return 0.0, 0.0

        cutoff = time.time() - (days * 86400)
        recent_indices = [i for i, ts in enumerate(self.timestamps) if ts >= cutoff]

        if not recent_indices:
            return 0.0, 0.0

        first_idx = recent_indices[0]
        last_idx = recent_indices[-1]

        line_change = (self.line_rates[last_idx] - self.line_rates[first_idx]) * 100
        branch_change = (self.branch_rates[last_idx] - self.branch_rates[first_idx]) * 100

        return line_change, branch_change


class CoverageTracker:
    """Track and analyze code coverage."""

    def __init__(self, project_root: str, storage_dir: Optional[str] = None):
        """
        Initialize coverage tracker.

        Args:
            project_root: Root directory of the project
            storage_dir: Directory to store coverage data (default: .coverage_data)
        """
        self.project_root = Path(project_root)
        self.storage_dir = Path(storage_dir or self.project_root / ".coverage_data")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = self.storage_dir / "history.json"
        self.trend = self._load_trend()

    def run_coverage(
        self,
        test_command: Optional[str] = None,
        source_dirs: Optional[List[str]] = None
    ) -> CoverageReport:
        """
        Run tests with coverage and generate report.

        Args:
            test_command: Custom test command (default: pytest)
            source_dirs: Source directories to measure (default: current dir)

        Returns:
            Coverage report
        """
        # Default test command
        if test_command is None:
            test_command = "pytest"

        # Build coverage command
        cmd = ["coverage", "run", "-m"]

        if source_dirs:
            for src_dir in source_dirs:
                cmd.extend(["--source", src_dir])

        cmd.extend(test_command.split())

        # Run tests with coverage
        try:
            subprocess.run(
                cmd,
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Coverage run failed: {e.stderr}")

        # Generate XML report
        xml_path = self.storage_dir / "coverage.xml"
        subprocess.run(
            ["coverage", "xml", "-o", str(xml_path)],
            cwd=self.project_root,
            check=True,
            capture_output=True
        )

        # Parse and return report
        report = self.parse_coverage_xml(str(xml_path))

        # Save to history
        self._save_report(report)

        return report

    def parse_coverage_xml(self, xml_path: str) -> CoverageReport:
        """
        Parse coverage XML report.

        Args:
            xml_path: Path to coverage.xml file

        Returns:
            Coverage report
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Parse overall coverage
        line_rate = float(root.get("line-rate", 0))
        branch_rate = float(root.get("branch-rate", 0))
        lines_covered = int(root.get("lines-covered", 0))
        lines_valid = int(root.get("lines-valid", 0))
        branches_covered = int(root.get("branches-covered", 0))
        branches_valid = int(root.get("branches-valid", 0))

        report = CoverageReport(
            timestamp=time.time(),
            line_rate=line_rate,
            branch_rate=branch_rate,
            lines_covered=lines_covered,
            lines_valid=lines_valid,
            branches_covered=branches_covered,
            branches_valid=branches_valid,
        )

        # Parse file-level coverage
        for package in root.findall(".//package"):
            for cls in package.findall("classes/class"):
                filename = cls.get("filename", "")

                # Get line coverage
                lines = cls.findall("lines/line")
                lines_covered_count = sum(1 for line in lines if int(line.get("hits", 0)) > 0)
                lines_valid_count = len(lines)

                # Get missing lines
                missing_lines = [
                    int(line.get("number"))
                    for line in lines
                    if int(line.get("hits", 0)) == 0
                ]

                # Calculate rates
                file_line_rate = lines_covered_count / lines_valid_count if lines_valid_count > 0 else 0

                # Branch coverage (if available)
                branches = [line for line in lines if line.get("branch") == "true"]
                branches_valid_count = len(branches)
                branches_covered_count = sum(
                    1 for line in branches
                    if line.get("condition-coverage", "0%").split()[0] != "0%"
                )
                file_branch_rate = branches_covered_count / branches_valid_count if branches_valid_count > 0 else 0

                file_coverage = FileCoverage(
                    file_path=filename,
                    line_rate=file_line_rate,
                    branch_rate=file_branch_rate,
                    lines_covered=lines_covered_count,
                    lines_valid=lines_valid_count,
                    branches_covered=branches_covered_count,
                    branches_valid=branches_valid_count,
                    missing_lines=missing_lines,
                )

                report.files[filename] = file_coverage

        return report

    def get_file_coverage(self, file_path: str) -> Optional[FileCoverage]:
        """
        Get coverage for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            File coverage or None if not found
        """
        if not self.trend.timestamps:
            return None

        # Get latest report
        latest_report = self._load_report(self.trend.timestamps[-1])
        if not latest_report:
            return None

        return latest_report.files.get(file_path)

    def get_trend(self, days: int = 30) -> CoverageTrend:
        """
        Get coverage trend for the last N days.

        Args:
            days: Number of days to include

        Returns:
            Coverage trend
        """
        cutoff = time.time() - (days * 86400)

        trend = CoverageTrend()
        for timestamp in self.trend.timestamps:
            if timestamp >= cutoff:
                report = self._load_report(timestamp)
                if report:
                    trend.add_report(report)

        return trend

    def get_low_coverage_files(self, threshold: float = 70.0) -> List[FileCoverage]:
        """
        Get files with coverage below threshold.

        Args:
            threshold: Coverage threshold percentage

        Returns:
            List of files with low coverage
        """
        if not self.trend.timestamps:
            return []

        latest_report = self._load_report(self.trend.timestamps[-1])
        if not latest_report:
            return []

        return [
            file_cov
            for file_cov in latest_report.files.values()
            if file_cov.line_coverage_percent < threshold
        ]

    def generate_summary(self) -> Dict:
        """
        Generate coverage summary.

        Returns:
            Summary dictionary
        """
        if not self.trend.timestamps:
            return {
                "status": "no_data",
                "message": "No coverage data available"
            }

        latest_report = self._load_report(self.trend.timestamps[-1])
        if not latest_report:
            return {
                "status": "error",
                "message": "Failed to load latest report"
            }

        # Get trend changes
        line_change_7d, branch_change_7d = self.trend.get_change(7)
        line_change_30d, branch_change_30d = self.trend.get_change(30)

        # Get low coverage files
        low_coverage = self.get_low_coverage_files(70.0)

        return {
            "status": latest_report.status.value,
            "timestamp": latest_report.timestamp,
            "line_coverage": {
                "percent": latest_report.line_coverage_percent,
                "covered": latest_report.lines_covered,
                "total": latest_report.lines_valid,
                "change_7d": line_change_7d,
                "change_30d": line_change_30d,
            },
            "branch_coverage": {
                "percent": latest_report.branch_coverage_percent,
                "covered": latest_report.branches_covered,
                "total": latest_report.branches_valid,
                "change_7d": branch_change_7d,
                "change_30d": branch_change_30d,
            },
            "files": {
                "total": len(latest_report.files),
                "low_coverage": len(low_coverage),
            },
            "low_coverage_files": [
                {
                    "path": fc.file_path,
                    "coverage": fc.line_coverage_percent,
                    "missing_lines": len(fc.missing_lines),
                }
                for fc in sorted(low_coverage, key=lambda x: x.line_coverage_percent)[:10]
            ]
        }

    def _save_report(self, report: CoverageReport):
        """Save coverage report to storage."""
        # Save report data
        report_file = self.storage_dir / f"report_{int(report.timestamp)}.json"
        with open(report_file, "w") as f:
            json.dump({
                "timestamp": report.timestamp,
                "line_rate": report.line_rate,
                "branch_rate": report.branch_rate,
                "lines_covered": report.lines_covered,
                "lines_valid": report.lines_valid,
                "branches_covered": report.branches_covered,
                "branches_valid": report.branches_valid,
                "files": {
                    path: {
                        "file_path": fc.file_path,
                        "line_rate": fc.line_rate,
                        "branch_rate": fc.branch_rate,
                        "lines_covered": fc.lines_covered,
                        "lines_valid": fc.lines_valid,
                        "branches_covered": fc.branches_covered,
                        "branches_valid": fc.branches_valid,
                        "missing_lines": fc.missing_lines,
                    }
                    for path, fc in report.files.items()
                }
            }, f, indent=2)

        # Update trend
        self.trend.add_report(report)
        self._save_trend()

    def _load_report(self, timestamp: float) -> Optional[CoverageReport]:
        """Load coverage report from storage."""
        report_file = self.storage_dir / f"report_{int(timestamp)}.json"
        if not report_file.exists():
            return None

        with open(report_file) as f:
            data = json.load(f)

        report = CoverageReport(
            timestamp=data["timestamp"],
            line_rate=data["line_rate"],
            branch_rate=data["branch_rate"],
            lines_covered=data["lines_covered"],
            lines_valid=data["lines_valid"],
            branches_covered=data["branches_covered"],
            branches_valid=data["branches_valid"],
        )

        for path, file_data in data.get("files", {}).items():
            report.files[path] = FileCoverage(**file_data)

        return report

    def _load_trend(self) -> CoverageTrend:
        """Load coverage trend from storage."""
        if not self.history_file.exists():
            return CoverageTrend()

        with open(self.history_file) as f:
            data = json.load(f)

        return CoverageTrend(
            timestamps=data.get("timestamps", []),
            line_rates=data.get("line_rates", []),
            branch_rates=data.get("branch_rates", []),
        )

    def _save_trend(self):
        """Save coverage trend to storage."""
        with open(self.history_file, "w") as f:
            json.dump({
                "timestamps": self.trend.timestamps,
                "line_rates": self.trend.line_rates,
                "branch_rates": self.trend.branch_rates,
            }, f, indent=2)


# Global coverage tracker instance
_coverage_tracker: Optional[CoverageTracker] = None


def get_coverage_tracker(project_root: Optional[str] = None) -> CoverageTracker:
    """
    Get global coverage tracker instance.

    Args:
        project_root: Project root directory (required on first call)

    Returns:
        Coverage tracker instance
    """
    global _coverage_tracker

    if _coverage_tracker is None:
        if project_root is None:
            project_root = os.getcwd()
        _coverage_tracker = CoverageTracker(project_root)

    return _coverage_tracker


def configure_coverage_tracker(project_root: str, storage_dir: Optional[str] = None):
    """
    Configure global coverage tracker.

    Args:
        project_root: Project root directory
        storage_dir: Storage directory for coverage data
    """
    global _coverage_tracker
    _coverage_tracker = CoverageTracker(project_root, storage_dir)
