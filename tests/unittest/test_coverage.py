"""
Unit tests for code coverage tracking system.
"""

import json
import tempfile
from pathlib import Path
import pytest

from pr_agent.coverage import (
    CoverageTracker,
    CoverageReport,
    FileCoverage,
    CoverageTrend,
    CoverageStatus,
    get_coverage_tracker,
)


@pytest.fixture
def temp_project():
    """Create temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def coverage_tracker(temp_project):
    """Create coverage tracker instance."""
    return CoverageTracker(str(temp_project))


@pytest.fixture
def sample_coverage_xml(temp_project):
    """Create sample coverage XML file."""
    xml_content = """<?xml version="1.0" ?>
<coverage version="7.0" timestamp="1640000000" lines-valid="100" lines-covered="85"
          line-rate="0.85" branches-valid="20" branches-covered="15" branch-rate="0.75">
    <packages>
        <package name="mypackage" line-rate="0.85" branch-rate="0.75">
            <classes>
                <class name="module.py" filename="mypackage/module.py" line-rate="0.85" branch-rate="0.75">
                    <lines>
                        <line number="1" hits="1"/>
                        <line number="2" hits="1"/>
                        <line number="3" hits="0"/>
                        <line number="4" hits="1"/>
                        <line number="5" hits="1" branch="true" condition-coverage="50% (1/2)"/>
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>
"""
    xml_path = temp_project / "coverage.xml"
    xml_path.write_text(xml_content)
    return xml_path


class TestFileCoverage:
    """Test FileCoverage class."""

    def test_line_coverage_percent(self):
        """Test line coverage percentage calculation."""
        fc = FileCoverage(
            file_path="test.py",
            line_rate=0.85,
            branch_rate=0.75,
            lines_covered=85,
            lines_valid=100,
            branches_covered=15,
            branches_valid=20,
        )
        assert fc.line_coverage_percent == 85.0

    def test_branch_coverage_percent(self):
        """Test branch coverage percentage calculation."""
        fc = FileCoverage(
            file_path="test.py",
            line_rate=0.85,
            branch_rate=0.75,
            lines_covered=85,
            lines_valid=100,
            branches_covered=15,
            branches_valid=20,
        )
        assert fc.branch_coverage_percent == 75.0

    def test_status_excellent(self):
        """Test excellent coverage status."""
        fc = FileCoverage(
            file_path="test.py",
            line_rate=0.95,
            branch_rate=0.90,
            lines_covered=95,
            lines_valid=100,
            branches_covered=18,
            branches_valid=20,
        )
        assert fc.status == CoverageStatus.EXCELLENT

    def test_status_good(self):
        """Test good coverage status."""
        fc = FileCoverage(
            file_path="test.py",
            line_rate=0.85,
            branch_rate=0.80,
            lines_covered=85,
            lines_valid=100,
            branches_covered=16,
            branches_valid=20,
        )
        assert fc.status == CoverageStatus.GOOD

    def test_status_fair(self):
        """Test fair coverage status."""
        fc = FileCoverage(
            file_path="test.py",
            line_rate=0.75,
            branch_rate=0.70,
            lines_covered=75,
            lines_valid=100,
            branches_covered=14,
            branches_valid=20,
        )
        assert fc.status == CoverageStatus.FAIR

    def test_status_poor(self):
        """Test poor coverage status."""
        fc = FileCoverage(
            file_path="test.py",
            line_rate=0.60,
            branch_rate=0.50,
            lines_covered=60,
            lines_valid=100,
            branches_covered=10,
            branches_valid=20,
        )
        assert fc.status == CoverageStatus.POOR


class TestCoverageReport:
    """Test CoverageReport class."""

    def test_line_coverage_percent(self):
        """Test overall line coverage percentage."""
        report = CoverageReport(
            timestamp=1640000000.0,
            line_rate=0.85,
            branch_rate=0.75,
            lines_covered=85,
            lines_valid=100,
            branches_covered=15,
            branches_valid=20,
        )
        assert report.line_coverage_percent == 85.0

    def test_branch_coverage_percent(self):
        """Test overall branch coverage percentage."""
        report = CoverageReport(
            timestamp=1640000000.0,
            line_rate=0.85,
            branch_rate=0.75,
            lines_covered=85,
            lines_valid=100,
            branches_covered=15,
            branches_valid=20,
        )
        assert report.branch_coverage_percent == 75.0

    def test_status(self):
        """Test overall coverage status."""
        report = CoverageReport(
            timestamp=1640000000.0,
            line_rate=0.85,
            branch_rate=0.75,
            lines_covered=85,
            lines_valid=100,
            branches_covered=15,
            branches_valid=20,
        )
        assert report.status == CoverageStatus.GOOD


class TestCoverageTrend:
    """Test CoverageTrend class."""

    def test_add_report(self):
        """Test adding report to trend."""
        trend = CoverageTrend()
        report = CoverageReport(
            timestamp=1640000000.0,
            line_rate=0.85,
            branch_rate=0.75,
            lines_covered=85,
            lines_valid=100,
            branches_covered=15,
            branches_valid=20,
        )

        trend.add_report(report)

        assert len(trend.timestamps) == 1
        assert trend.timestamps[0] == 1640000000.0
        assert trend.line_rates[0] == 0.85
        assert trend.branch_rates[0] == 0.75

    def test_get_change_no_data(self):
        """Test getting change with no data."""
        trend = CoverageTrend()
        line_change, branch_change = trend.get_change(7)

        assert line_change == 0.0
        assert branch_change == 0.0

    def test_get_change_with_data(self):
        """Test getting change with data."""
        import time
        trend = CoverageTrend()

        # Add old report
        old_report = CoverageReport(
            timestamp=time.time() - 86400 * 5,  # 5 days ago
            line_rate=0.80,
            branch_rate=0.70,
            lines_covered=80,
            lines_valid=100,
            branches_covered=14,
            branches_valid=20,
        )
        trend.add_report(old_report)

        # Add new report
        new_report = CoverageReport(
            timestamp=time.time(),
            line_rate=0.85,
            branch_rate=0.75,
            lines_covered=85,
            lines_valid=100,
            branches_covered=15,
            branches_valid=20,
        )
        trend.add_report(new_report)

        line_change, branch_change = trend.get_change(7)

        assert abs(line_change - 5.0) < 0.01  # 85% - 80%
        assert abs(branch_change - 5.0) < 0.01  # 75% - 70%


class TestCoverageTracker:
    """Test CoverageTracker class."""

    def test_init(self, temp_project):
        """Test tracker initialization."""
        tracker = CoverageTracker(str(temp_project))

        assert tracker.project_root == temp_project
        assert tracker.storage_dir.exists()
        assert isinstance(tracker.trend, CoverageTrend)

    def test_parse_coverage_xml(self, coverage_tracker, sample_coverage_xml):
        """Test parsing coverage XML."""
        report = coverage_tracker.parse_coverage_xml(str(sample_coverage_xml))

        assert report.line_rate == 0.85
        assert report.branch_rate == 0.75
        assert report.lines_covered == 85
        assert report.lines_valid == 100
        assert len(report.files) == 1

    def test_parse_coverage_xml_file_details(self, coverage_tracker, sample_coverage_xml):
        """Test parsing file-level coverage details."""
        report = coverage_tracker.parse_coverage_xml(str(sample_coverage_xml))

        file_cov = report.files["mypackage/module.py"]
        assert file_cov.file_path == "mypackage/module.py"
        assert file_cov.lines_valid == 5
        assert file_cov.lines_covered == 4
        assert 3 in file_cov.missing_lines

    def test_get_file_coverage_no_data(self, coverage_tracker):
        """Test getting file coverage with no data."""
        result = coverage_tracker.get_file_coverage("test.py")
        assert result is None

    def test_get_low_coverage_files_no_data(self, coverage_tracker):
        """Test getting low coverage files with no data."""
        result = coverage_tracker.get_low_coverage_files()
        assert result == []

    def test_generate_summary_no_data(self, coverage_tracker):
        """Test generating summary with no data."""
        summary = coverage_tracker.generate_summary()

        assert summary["status"] == "no_data"
        assert "message" in summary

    def test_save_and_load_report(self, coverage_tracker):
        """Test saving and loading report."""
        report = CoverageReport(
            timestamp=1640000000.0,
            line_rate=0.85,
            branch_rate=0.75,
            lines_covered=85,
            lines_valid=100,
            branches_covered=15,
            branches_valid=20,
        )

        coverage_tracker._save_report(report)
        loaded = coverage_tracker._load_report(1640000000.0)

        assert loaded is not None
        assert loaded.line_rate == 0.85
        assert loaded.branch_rate == 0.75

    def test_save_and_load_trend(self, coverage_tracker):
        """Test saving and loading trend."""
        report = CoverageReport(
            timestamp=1640000000.0,
            line_rate=0.85,
            branch_rate=0.75,
            lines_covered=85,
            lines_valid=100,
            branches_covered=15,
            branches_valid=20,
        )

        coverage_tracker._save_report(report)

        # Create new tracker to test loading
        new_tracker = CoverageTracker(str(coverage_tracker.project_root))

        assert len(new_tracker.trend.timestamps) == 1
        assert new_tracker.trend.line_rates[0] == 0.85


class TestGlobalCoverageTracker:
    """Test global coverage tracker."""

    def test_get_coverage_tracker(self, temp_project):
        """Test getting global coverage tracker."""
        from pr_agent.coverage.tracker import _coverage_tracker
        import pr_agent.coverage.tracker as tracker_module

        # Reset global
        tracker_module._coverage_tracker = None

        tracker1 = get_coverage_tracker(str(temp_project))
        tracker2 = get_coverage_tracker()

        assert tracker1 is tracker2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
