"""
Tests for estimation algorithms
"""
import pytest
from pr_agent.monitoring.estimation import (
    calculate_complexity_score,
    estimate_human_review_time,
    calculate_api_cost,
    calculate_dispersion
)


def test_calculate_complexity_score_simple():
    """测试简单PR的复杂度评分"""
    pr_features = {
        'files_count': 2,
        'size_lines': 50,
        'languages': ['Python'],
        'file_paths': ['src/main.py', 'src/utils.py']
    }
    score = calculate_complexity_score(pr_features)
    assert 0 <= score <= 1
    assert score < 0.3


def test_calculate_complexity_score_complex():
    """测试复杂PR的复杂度评分"""
    pr_features = {
        'files_count': 25,
        'size_lines': 1500,
        'languages': ['Python', 'JavaScript', 'TypeScript', 'Go'],
        'file_paths': [
            'backend/api/users.py',
            'backend/api/auth.py',
            'frontend/components/Login.tsx',
            'frontend/utils/api.ts',
            'services/worker/main.go'
        ]
    }
    score = calculate_complexity_score(pr_features)
    assert 0 <= score <= 1
    assert score > 0.6


def test_estimate_human_review_time_small():
    """测试小型PR的时间估算"""
    pr_features = {
        'files_count': 2,
        'size_lines': 50,
        'languages': ['Python'],
        'complexity_score': 0.2
    }
    time_minutes = estimate_human_review_time(pr_features)
    assert 10 <= time_minutes <= 30


def test_estimate_human_review_time_large():
    """测试大型PR的时间估算"""
    pr_features = {
        'files_count': 20,
        'size_lines': 1000,
        'languages': ['Python', 'JavaScript', 'Go'],
        'complexity_score': 0.8
    }
    time_minutes = estimate_human_review_time(pr_features)
    assert 60 <= time_minutes <= 240


def test_estimate_human_review_time_capped():
    """测试时间估算上限"""
    pr_features = {
        'files_count': 100,
        'size_lines': 10000,
        'languages': ['Python', 'JavaScript', 'Go', 'Rust', 'C++'],
        'complexity_score': 1.0
    }
    time_minutes = estimate_human_review_time(pr_features)
    assert time_minutes == 240


def test_calculate_api_cost_gpt4():
    """测试GPT-4成本计算"""
    cost = calculate_api_cost('gpt-4', 1000, 500)
    expected = (1000 / 1000) * 0.03 + (500 / 1000) * 0.06
    assert abs(cost - expected) < 0.001


def test_calculate_api_cost_claude_opus():
    """测试Claude Opus成本计算"""
    cost = calculate_api_cost('claude-opus', 2000, 1000)
    expected = (2000 / 1000) * 0.015 + (1000 / 1000) * 0.075
    assert abs(cost - expected) < 0.001


def test_calculate_api_cost_unknown_model():
    """测试未知模型返回0"""
    cost = calculate_api_cost('unknown-model', 1000, 500)
    assert cost == 0.0


def test_calculate_dispersion_single_directory():
    """测试单目录的分散度"""
    file_paths = ['src/main.py', 'src/utils.py', 'src/config.py']
    dispersion = calculate_dispersion(file_paths)
    assert 0 <= dispersion <= 1
    assert dispersion < 0.8


def test_calculate_dispersion_multiple_directories():
    """测试多目录的分散度"""
    file_paths = [
        'backend/api/users.py',
        'frontend/components/Login.tsx',
        'services/worker/main.go',
        'docs/README.md'
    ]
    dispersion = calculate_dispersion(file_paths)
    assert 0 <= dispersion <= 1
    assert dispersion > 0.5
