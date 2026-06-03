"""
Tests for EfficiencyTracker
"""
import pytest
import time
from unittest.mock import Mock, MagicMock
from pr_agent.monitoring.efficiency_tracker import EfficiencyTracker


def test_efficiency_tracker_context_manager():
    """测试context manager基本功能"""
    mock_git_provider = Mock()
    mock_git_provider.get_diff_files.return_value = []

    tracker = EfficiencyTracker(1, mock_git_provider)

    with tracker as t:
        assert t.start_time is not None
        assert t.metrics is not None
        time.sleep(0.1)

    assert tracker.end_time is not None
    assert tracker.metrics['review_processing_time_seconds'] >= 0.1


def test_collect_pr_features():
    """测试PR特征收集"""
    mock_git_provider = Mock()
    mock_file1 = Mock()
    mock_file1.filename = 'src/main.py'
    mock_file1.patch = '+line1\n-line2\n+line3'

    mock_file2 = Mock()
    mock_file2.filename = 'src/utils.js'
    mock_file2.patch = '+line1\n+line2'

    mock_file3 = Mock()
    mock_file3.filename = 'tests/test_main.py'
    mock_file3.patch = '+line1'

    mock_git_provider.get_diff_files.return_value = [mock_file1, mock_file2, mock_file3]

    tracker = EfficiencyTracker(1, mock_git_provider)
    tracker._collect_pr_features()

    assert tracker.metrics['pr_files_count'] == 3
    assert tracker.metrics['pr_size_lines'] > 0
    assert 'Python' in tracker.metrics['pr_languages']
    assert 'JavaScript' in tracker.metrics['pr_languages']
    assert tracker.metrics['pr_complexity_score'] > 0


def test_track_api_call():
    """测试API调用追踪"""
    mock_git_provider = Mock()
    mock_git_provider.get_diff_files.return_value = []

    tracker = EfficiencyTracker(1, mock_git_provider)
    tracker.track_api_call(1000, 500, 0.05)

    assert tracker.metrics['tokens_prompt'] == 1000
    assert tracker.metrics['tokens_completion'] == 500
    assert tracker.metrics['api_calls_count'] == 1
    assert tracker.metrics['api_cost_usd'] == 0.05

    # 再次调用应该累加
    tracker.track_api_call(500, 250, 0.025)
    assert tracker.metrics['tokens_prompt'] == 1500
    assert tracker.metrics['api_calls_count'] == 2


def test_track_issues_found():
    """测试问题追踪"""
    mock_git_provider = Mock()
    mock_git_provider.get_diff_files.return_value = []

    tracker = EfficiencyTracker(1, mock_git_provider)

    issues = [
        {'severity': 'high', 'type': 'security'},
        {'severity': 'high', 'type': 'bug'},
        {'severity': 'medium', 'type': 'style'},
        {'severity': 'low', 'type': 'suggestion'}
    ]

    tracker.track_issues_found(issues)

    assert tracker.metrics['issues_found_total'] == 4
    assert tracker.metrics['issues_high_severity'] == 2
    assert tracker.metrics['issues_medium_severity'] == 1
    assert tracker.metrics['issues_low_severity'] == 1
    assert tracker.metrics['security_issues_found'] == 1


def test_track_code_suggestions():
    """测试代码建议追踪"""
    mock_git_provider = Mock()
    mock_git_provider.get_diff_files.return_value = []

    tracker = EfficiencyTracker(1, mock_git_provider)

    suggestions = [
        {'file': 'main.py', 'suggestion': 'Use list comprehension'},
        {'file': 'utils.py', 'suggestion': 'Extract method'}
    ]

    tracker.track_code_suggestions(suggestions)
    assert tracker.metrics['code_suggestions_count'] == 2


def test_set_review_metadata():
    """测试设置review元数据"""
    mock_git_provider = Mock()
    mock_git_provider.get_diff_files.return_value = []

    tracker = EfficiencyTracker(1, mock_git_provider)
    tracker.set_review_type('agentic')
    tracker.set_model('gpt-4')

    assert tracker.metrics['review_type'] == 'agentic'
    assert tracker.metrics['model_used'] == 'gpt-4'


def test_track_agentic_iteration():
    """测试agentic迭代追踪"""
    mock_git_provider = Mock()
    mock_git_provider.get_diff_files.return_value = []

    tracker = EfficiencyTracker(1, mock_git_provider)

    tracker.track_agentic_iteration()
    assert tracker.metrics['agentic_search_iterations'] == 1

    tracker.track_agentic_iteration()
    assert tracker.metrics['agentic_search_iterations'] == 2
