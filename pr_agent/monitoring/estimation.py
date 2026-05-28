"""
Estimation algorithms for AI efficiency metrics

Provides algorithms for calculating:
- PR complexity scores
- Human review time estimates
- API cost calculations
"""
from typing import Dict, List
from pathlib import Path


def calculate_dispersion(file_paths: List[str]) -> float:
    """
    计算文件修改的分散度（0-1）
    基于文件路径的目录多样性
    """
    if not file_paths:
        return 0.0

    # 提取所有唯一的目录
    directories = set()
    for path in file_paths:
        parts = Path(path).parts
        # 添加所有父目录
        for i in range(len(parts)):
            directories.add('/'.join(parts[:i+1]))

    # 归一化：目录数量相对于文件数量
    # 如果每个文件在不同目录，分散度高
    dispersion = len(directories) / (len(file_paths) * 2)
    return min(dispersion, 1.0)


def calculate_complexity_score(pr_features: Dict) -> float:
    """
    计算PR复杂度评分（0-1）

    考虑因素：
    - 文件数量（权重：0.3）
    - 代码行数（权重：0.3）
    - 语言多样性（权重：0.2）
    - 修改分散度（权重：0.2）
    """
    # 文件数量评分（归一化到0-1）
    file_score = min(pr_features['files_count'] / 20, 1.0)

    # 代码行数评分（归一化到0-1）
    line_score = min(pr_features['size_lines'] / 1000, 1.0)

    # 语言多样性评分
    language_score = min(len(pr_features['languages']) / 5, 1.0)

    # 修改分散度评分
    dispersion_score = calculate_dispersion(pr_features.get('file_paths', []))

    complexity = (
        file_score * 0.3 +
        line_score * 0.3 +
        language_score * 0.2 +
        dispersion_score * 0.2
    )

    return complexity


def estimate_human_review_time(pr_features: Dict) -> float:
    """
    估算人工审查所需时间（分钟）

    基于经验公式：
    - 基础时间：10分钟
    - 文件因素：每个文件 +2分钟
    - 行数因素：每100行 +5分钟
    - 复杂度因素：complexity_score * 20分钟
    - 语言多样性：每种额外语言 +3分钟
    """
    base_time = 10

    file_time = pr_features['files_count'] * 2
    line_time = (pr_features['size_lines'] / 100) * 5
    complexity_time = pr_features['complexity_score'] * 20
    language_time = max(0, (len(pr_features['languages']) - 1) * 3)

    total_time = base_time + file_time + line_time + complexity_time + language_time

    # 上限：4小时
    return min(total_time, 240)


def calculate_api_cost(model: str, tokens_prompt: int, tokens_completion: int) -> float:
    """
    计算API调用成本（美元）

    定价（2026年5月）：
    - GPT-4: $0.03/1K prompt tokens, $0.06/1K completion tokens
    - GPT-4-turbo: $0.01/1K prompt tokens, $0.03/1K completion tokens
    - Claude Opus: $0.015/1K prompt tokens, $0.075/1K completion tokens
    - Claude Sonnet: $0.003/1K prompt tokens, $0.015/1K completion tokens
    """
    pricing = {
        'gpt-4': (0.03, 0.06),
        'gpt-4-turbo': (0.01, 0.03),
        'claude-opus': (0.015, 0.075),
        'claude-sonnet': (0.003, 0.015),
    }

    if model not in pricing:
        return 0.0

    prompt_price, completion_price = pricing[model]

    cost = (
        (tokens_prompt / 1000) * prompt_price +
        (tokens_completion / 1000) * completion_price
    )

    return cost
