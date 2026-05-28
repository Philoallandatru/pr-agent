"""
Tests for efficiency metrics database operations
"""
import pytest
import sqlite3
from pr_agent.storage.database import Database


def test_efficiency_metrics_table_exists():
    """测试efficiency_metrics表是否被创建"""
    db = Database(":memory:")
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='efficiency_metrics'
    """)
    assert cursor.fetchone() is not None
    db.close()


def test_efficiency_metrics_indexes_exist():
    """测试索引是否被创建"""
    db = Database(":memory:")
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name='idx_efficiency_metrics_pr_review'
    """)
    assert cursor.fetchone() is not None

    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name='idx_efficiency_metrics_created_at'
    """)
    assert cursor.fetchone() is not None
    db.close()


def test_add_efficiency_metrics():
    """测试添加效率指标记录"""
    db = Database(":memory:")

    # 先创建一个repository和pr_review
    repo_id = db.add_repository("TEST", "repo")
    review_id = db.add_pr_review(
        repository_id=repo_id,
        pr_id=1,
        pr_title="Test PR",
        pr_author="test_user",
        pr_url="https://test.com/pr/1",
        commands_run=["review"]
    )

    # 添加效率指标
    metrics_id = db.add_efficiency_metrics(
        pr_review_id=review_id,
        metrics={
            'issues_found_total': 5,
            'issues_high_severity': 2,
            'pr_size_lines': 100,
            'pr_files_count': 3,
            'tokens_total': 1000,
            'api_cost_usd': 0.05,
            'review_processing_time_seconds': 30.5
        }
    )

    assert metrics_id > 0

    # 验证数据
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM efficiency_metrics WHERE id = ?", (metrics_id,))
    row = cursor.fetchone()
    assert row is not None
    assert dict(row)['issues_found_total'] == 5
    assert dict(row)['pr_size_lines'] == 100
    db.close()


def test_get_efficiency_metrics():
    """测试查询效率指标"""
    db = Database(":memory:")

    # 创建测试数据
    repo_id = db.add_repository("TEST", "repo")
    review_id = db.add_pr_review(
        repository_id=repo_id,
        pr_id=1,
        pr_title="Test PR",
        pr_author="test_user",
        pr_url="https://test.com/pr/1",
        commands_run=["review"]
    )

    db.add_efficiency_metrics(
        pr_review_id=review_id,
        metrics={'issues_found_total': 5, 'review_processing_time_seconds': 30.5}
    )

    # 查询
    metrics = db.get_efficiency_metrics(pr_review_id=review_id)
    assert len(metrics) == 1
    assert metrics[0]['issues_found_total'] == 5
    db.close()
