"""
Tests for code change impact analysis system.
"""

import pytest
import tempfile
import os
from pathlib import Path
from pr_agent.impact import (
    ImpactAnalyzer,
    ChangeType,
    RiskLevel,
)


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository structure."""
    # Create main module
    main_file = tmp_path / "main.py"
    main_file.write_text("""
import utils
import config

def main():
    utils.helper()
    config.load()
""")

    # Create utils module
    utils_file = tmp_path / "utils.py"
    utils_file.write_text("""
def helper():
    return "help"

def another_function():
    return 42
""")

    # Create config module
    config_file = tmp_path / "config.py"
    config_file.write_text("""
def load():
    return {}
""")

    # Create dependent module
    app_file = tmp_path / "app.py"
    app_file.write_text("""
import main

def run():
    main.main()
""")

    # Create test file
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_utils.py"
    test_file.write_text("""
import utils

def test_helper():
    assert utils.helper() == "help"
""")

    return tmp_path


class TestImpactAnalyzer:
    """Test ImpactAnalyzer."""

    def test_analyzer_creation(self, temp_repo):
        """Test analyzer creation."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        assert analyzer.repo_path == temp_repo

    def test_analyze_single_file(self, temp_repo):
        """Test analyzing single file change."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py"])

        assert len(result.changes) == 1
        assert result.changes[0].file_path == "utils.py"
        assert result.changes[0].change_type == ChangeType.MODIFIED

    def test_analyze_multiple_files(self, temp_repo):
        """Test analyzing multiple file changes."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py", "config.py"])

        assert len(result.changes) == 2
        assert {c.file_path for c in result.changes} == {"utils.py", "config.py"}

    def test_extract_definitions(self, temp_repo):
        """Test extracting function and class definitions."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py"])

        change = result.changes[0]
        assert "helper" in change.functions_changed
        assert "another_function" in change.functions_changed

    def test_find_impacted_files(self, temp_repo):
        """Test finding impacted files."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py"])

        # main.py imports utils.py, so it should be impacted
        impacted_paths = {f.file_path for f in result.impacted_files}
        assert "main.py" in impacted_paths

    def test_find_affected_tests(self, temp_repo):
        """Test finding affected tests."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py"], include_tests=True)

        # test_utils.py should be identified
        assert any("test_utils.py" in test for test in result.affected_tests)

    def test_dependency_graph(self, temp_repo):
        """Test building dependency graph."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["main.py"])

        # main.py depends on utils and config
        assert "main.py" in result.dependency_graph
        deps = result.dependency_graph["main.py"]
        assert any("utils.py" in d for d in deps)
        assert any("config.py" in d for d in deps)


class TestRiskAssessment:
    """Test risk assessment."""

    def test_low_risk_single_file(self, temp_repo):
        """Test low risk for single file change."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py"])

        assert result.risk_assessment.level in [RiskLevel.LOW, RiskLevel.MEDIUM]
        assert 0 <= result.risk_assessment.score <= 100

    def test_higher_risk_multiple_files(self, temp_repo):
        """Test higher risk for multiple file changes."""
        analyzer = ImpactAnalyzer(str(temp_repo))

        # Create more files to change
        for i in range(6):
            file_path = temp_repo / f"module{i}.py"
            file_path.write_text(f"def func{i}(): pass")

        changed_files = ["utils.py", "config.py"] + [f"module{i}.py" for i in range(6)]
        result = analyzer.analyze_changes(changed_files)

        # More files = higher risk
        assert result.risk_assessment.score > 10

    def test_risk_factors(self, temp_repo):
        """Test risk factors are identified."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py", "config.py", "main.py"])

        assert len(result.risk_assessment.factors) > 0
        assert len(result.risk_assessment.recommendations) > 0

    def test_core_file_risk(self, temp_repo):
        """Test higher risk for core files."""
        # Create __init__.py (core file)
        init_file = temp_repo / "__init__.py"
        init_file.write_text("")

        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["__init__.py"])

        # Core files should increase risk
        assert any("core" in factor.lower() for factor in result.risk_assessment.factors)


class TestVisualization:
    """Test impact visualization."""

    def test_text_visualization(self, temp_repo):
        """Test text visualization."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py"])

        text = analyzer.visualize_impact(result, output_format="text")

        assert "CODE CHANGE IMPACT ANALYSIS" in text
        assert "RISK ASSESSMENT" in text
        assert "utils.py" in text

    def test_dot_visualization(self, temp_repo):
        """Test DOT graph visualization."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py"])

        dot = analyzer.visualize_impact(result, output_format="dot")

        assert "digraph impact" in dot
        assert "utils.py" in dot

    def test_visualization_includes_impacted_files(self, temp_repo):
        """Test visualization includes impacted files."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py"])

        text = analyzer.visualize_impact(result, output_format="text")

        assert "IMPACTED FILES" in text
        assert "main.py" in text


class TestChangeTypes:
    """Test different change types."""

    def test_deleted_file(self, temp_repo):
        """Test handling deleted files."""
        analyzer = ImpactAnalyzer(str(temp_repo))

        # Analyze non-existent file (simulating deletion)
        result = analyzer.analyze_changes(["deleted.py"])

        assert len(result.changes) == 1
        assert result.changes[0].change_type == ChangeType.DELETED

    def test_modified_file(self, temp_repo):
        """Test handling modified files."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py"])

        assert result.changes[0].change_type == ChangeType.MODIFIED


class TestMetadata:
    """Test analysis metadata."""

    def test_metadata_present(self, temp_repo):
        """Test metadata is included in results."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py"])

        assert "total_changes" in result.metadata
        assert "total_impacted" in result.metadata
        assert "total_tests" in result.metadata
        assert result.metadata["total_changes"] == 1

    def test_analysis_time(self, temp_repo):
        """Test analysis time is recorded."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py"])

        assert result.analysis_time is not None


class TestDepthControl:
    """Test dependency depth control."""

    def test_max_depth_limit(self, temp_repo):
        """Test max depth limits analysis."""
        analyzer = ImpactAnalyzer(str(temp_repo))

        # Analyze with depth 1
        result1 = analyzer.analyze_changes(["utils.py"], max_depth=1)

        # Analyze with depth 3
        result2 = analyzer.analyze_changes(["utils.py"], max_depth=3)

        # Deeper analysis may find more impacted files
        assert len(result2.impacted_files) >= len(result1.impacted_files)

    def test_distance_tracking(self, temp_repo):
        """Test distance is tracked correctly."""
        analyzer = ImpactAnalyzer(str(temp_repo))
        result = analyzer.analyze_changes(["utils.py"], max_depth=2)

        # Check that distances are assigned
        for impacted in result.impacted_files:
            assert impacted.distance >= 1
            assert impacted.distance <= 2
